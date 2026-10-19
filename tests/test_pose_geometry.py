"""카메라와 모델 없이 합성 landmark로 각도, 전신 가시성, 시점 판별, 평활화를 검증한다."""

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pose_geometry import (
    LANDMARK_INDEX,
    BodyLock,
    OneEuroFilter,
    ShoulderNoseViewClassifier,
    ViewJudgement,
    analyze_frame,
    joint_angle,
    landmarks_to_array,
)
from src.pose_classifier import LANDMARK_NAMES


FRAME = (640, 480)
PERSON = (90, 90, 270, 320)  # padding 전 YOLO bbox. 프레임 경계와 멀다.
CROP_A = (50, 50, 350, 400)  # 300 x 350
CROP_B = (0, 60, 600, 360)  # 600 x 300. A와 가로세로 비가 크게 다르다.

# 측면 스쿼트 자세(픽셀 좌표). 왼쪽 다리 기준 몸통각 45도, 정강이각 atan(30/100)도, 무릎각은 아래 식과 같다.
# 직각처럼 수평·수직 선분만 쓰면 가로세로 비를 바꿔도 각이 변하지 않아 보정 누락을 못 잡으므로,
# 정강이를 비스듬하게 두었다.
SIDE_POSE = {
    "nose": (200, 100),
    "left_shoulder": (180, 120),
    "right_shoulder": (184, 121),
    "left_hip": (100, 200),
    "right_hip": (104, 201),
    "left_knee": (200, 200),
    "right_knee": (204, 201),
    "left_ankle": (230, 300),
    "right_ankle": (234, 301),
    "left_heel": (220, 310),
    "right_heel": (224, 311),
    "left_foot_index": (290, 310),
    "right_foot_index": (294, 311),
}
# 무릎에서 hip 방향 (-100, 0), ankle 방향 (30, 100): 외적 크기 10000, 내적 -3000
EXPECTED_KNEE_ANGLE = math.degrees(math.atan2(10000, -3000))
EXPECTED_SHIN_ANGLE = math.degrees(math.atan2(30, 100))
EXPECTED_TORSO_ANGLE = 45.0
FRONT_POSE = {
    **SIDE_POSE,
    "left_shoulder": (120, 120),
    "right_shoulder": (280, 120),
    "left_hip": (130, 200),
    "right_hip": (270, 200),
}
# 오른쪽 다리는 가려진 것처럼 visibility를 낮춰 가까운 쪽 다리가 왼쪽이 되게 한다.
RIGHT_LEG_HIDDEN = {f"right_{joint}": 0.4 for joint in ("hip", "knee", "ankle")}
LEFT_LEG_HIDDEN = {f"left_{joint}": 0.4 for joint in ("hip", "knee", "ankle")}


def build_landmarks(pose, crop=CROP_A, visibility=None, default_visibility=1.0):
    """프레임 픽셀 좌표 자세를 crop 기준 정규화 landmark 33개로 바꾼다."""
    x1, y1, x2, y2 = crop
    width, height = x2 - x1, y2 - y1
    visibility = visibility or {}
    landmarks = [
        SimpleNamespace(x=0.5, y=0.5, z=0.0, visibility=default_visibility)
        for _ in LANDMARK_NAMES
    ]
    for name, (x, y) in pose.items():
        landmarks[LANDMARK_INDEX[name]] = SimpleNamespace(
            x=(x - x1) / width,
            y=(y - y1) / height,
            z=0.0,
            visibility=visibility.get(name, default_visibility),
        )
    return landmarks


def mirror(pose, axis=400):
    """자세를 x=axis/2 기준으로 좌우 반전한다(같은 사람이 반대 방향을 보는 경우)."""
    return {name: (axis - x, y) for name, (x, y) in pose.items()}


def build_world(left_hip, right_hip):
    world = [SimpleNamespace(x=0.0, y=0.0, z=0.0, visibility=1.0) for _ in LANDMARK_NAMES]
    world[LANDMARK_INDEX["left_hip"]] = SimpleNamespace(
        x=left_hip[0], y=left_hip[1], z=left_hip[2], visibility=1.0
    )
    world[LANDMARK_INDEX["right_hip"]] = SimpleNamespace(
        x=right_hip[0], y=right_hip[1], z=right_hip[2], visibility=1.0
    )
    return world


def analyze(
    pose=SIDE_POSE,
    crop=CROP_A,
    person=PERSON,
    visibility=None,
    nose_visibility=0.99,
    **kwargs,
):
    visibility = {"nose": nose_visibility, **RIGHT_LEG_HIDDEN, **(visibility or {})}
    return analyze_frame(
        build_landmarks(pose, crop, visibility),
        crop_bbox=crop,
        person_bbox=person,
        frame_size=FRAME,
        **kwargs,
    )


# ---------------------------------------------------------------- 각도와 종횡비 보정


def test_angles_match_known_geometry() -> None:
    geometry = analyze()
    assert geometry.leg == "left"
    assert geometry.knee_angle == pytest.approx(EXPECTED_KNEE_ANGLE, abs=1e-9)
    assert geometry.shin_angle == pytest.approx(EXPECTED_SHIN_ANGLE, abs=1e-9)
    assert geometry.torso_angle == pytest.approx(EXPECTED_TORSO_ANGLE, abs=1e-9)


def test_same_pose_gives_same_angles_for_different_crop_aspect_ratios() -> None:
    geometry_a = analyze(crop=CROP_A)
    geometry_b = analyze(crop=CROP_B)

    assert geometry_a.knee_angle == pytest.approx(EXPECTED_KNEE_ANGLE, abs=1e-9)
    assert geometry_b.knee_angle == pytest.approx(EXPECTED_KNEE_ANGLE, abs=1e-9)
    assert geometry_a.shin_angle == pytest.approx(EXPECTED_SHIN_ANGLE, abs=1e-9)
    assert geometry_b.shin_angle == pytest.approx(EXPECTED_SHIN_ANGLE, abs=1e-9)
    assert geometry_a.knee_angle == pytest.approx(geometry_b.knee_angle, abs=1e-9)
    assert geometry_a.torso_angle == pytest.approx(geometry_b.torso_angle, abs=1e-9)
    assert geometry_a.shin_angle == pytest.approx(geometry_b.shin_angle, abs=1e-9)
    assert geometry_a.view_signals.shoulder_ratio == pytest.approx(
        geometry_b.view_signals.shoulder_ratio, abs=1e-9
    )


def test_normalized_coordinates_would_distort_angles() -> None:
    """위 테스트가 종횡비 보정 누락을 실제로 잡아내는지 확인한다(보정 없이 계산하면 각도가 달라진다)."""
    naive_angles = []
    for crop in (CROP_A, CROP_B):
        array = landmarks_to_array(build_landmarks(SIDE_POSE, crop))
        points = array[:, :2]  # 픽셀 보정 없이 정규화 좌표 그대로
        naive_angles.append(
            joint_angle(
                points[LANDMARK_INDEX["left_knee"]],
                points[LANDMARK_INDEX["left_hip"]],
                points[LANDMARK_INDEX["left_ankle"]],
            )
        )
    assert abs(naive_angles[0] - naive_angles[1]) > 5.0
    # 보정하지 않은 값은 실제 각도와도 크게 다르다.
    assert abs(naive_angles[1] - EXPECTED_KNEE_ANGLE) > 5.0


def test_facing_follows_the_heel_to_toe_direction_of_the_selected_leg() -> None:
    assert analyze().facing == "right"  # heel x=220 → foot_index x=290
    assert analyze(mirror(SIDE_POSE)).facing == "left"


def test_signed_angles_are_positive_when_leaning_forward() -> None:
    geometry = analyze()  # 오른쪽을 보고, 어깨가 엉덩이보다 앞, 무릎은 발목보다 뒤
    assert geometry.torso_angle_signed == pytest.approx(EXPECTED_TORSO_ANGLE, abs=1e-9)
    assert geometry.shin_angle_signed == pytest.approx(-EXPECTED_SHIN_ANGLE, abs=1e-9)

    # 무릎이 발목보다 앞으로 나가면 정강이각이 양수다.
    knee_forward = {
        **SIDE_POSE,
        "left_ankle": (170, 300),
        "left_heel": (160, 310),
        "left_foot_index": (230, 310),
    }
    assert analyze(knee_forward).shin_angle_signed == pytest.approx(EXPECTED_SHIN_ANGLE, abs=1e-9)

    # 상체를 뒤로 젖히면 몸통각이 음수다.
    leaning_back = {**SIDE_POSE, "left_shoulder": (20, 120), "right_shoulder": (24, 121)}
    assert analyze(leaning_back).torso_angle_signed == pytest.approx(-EXPECTED_TORSO_ANGLE, abs=1e-9)


def test_unsigned_angles_are_kept_alongside_the_signed_ones() -> None:
    for pose in (SIDE_POSE, mirror(SIDE_POSE)):
        geometry = analyze(pose)
        assert geometry.torso_angle == pytest.approx(EXPECTED_TORSO_ANGLE, abs=1e-9)
        assert geometry.shin_angle == pytest.approx(EXPECTED_SHIN_ANGLE, abs=1e-9)
        assert abs(geometry.torso_angle_signed) == pytest.approx(geometry.torso_angle, abs=1e-9)
        assert abs(geometry.shin_angle_signed) == pytest.approx(geometry.shin_angle, abs=1e-9)


@pytest.mark.parametrize("crop", [CROP_A, CROP_B])
def test_mirrored_pose_gives_the_same_signed_angles(crop) -> None:
    original = analyze(SIDE_POSE, crop=crop)
    flipped = analyze(mirror(SIDE_POSE), crop=crop)

    assert original.facing != flipped.facing
    assert flipped.torso_angle_signed == pytest.approx(original.torso_angle_signed, abs=1e-9)
    assert flipped.shin_angle_signed == pytest.approx(original.shin_angle_signed, abs=1e-9)
    assert flipped.knee_angle == pytest.approx(original.knee_angle, abs=1e-9)
    assert flipped.torso_angle == pytest.approx(original.torso_angle, abs=1e-9)


def test_unknown_facing_leaves_only_the_signed_angles_unset() -> None:
    pose = {**SIDE_POSE, "left_foot_index": SIDE_POSE["left_heel"]}  # 발끝과 뒤꿈치가 같은 x
    geometry = analyze(pose)
    assert geometry.facing is None
    assert geometry.torso_angle_signed is None
    assert geometry.shin_angle_signed is None
    assert geometry.torso_angle == pytest.approx(EXPECTED_TORSO_ANGLE, abs=1e-9)  # 무부호 값은 그대로


def test_degenerate_segment_returns_none() -> None:
    pose = {**SIDE_POSE, "left_hip": SIDE_POSE["left_knee"]}  # hip과 knee가 같은 점
    geometry = analyze(pose)
    assert geometry.knee_angle is None


def test_invalid_crop_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        analyze_frame(
            build_landmarks(SIDE_POSE),
            crop_bbox=(50, 50, 50, 400),
            person_bbox=PERSON,
            frame_size=FRAME,
        )


def test_wrong_landmark_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        analyze_frame(
            build_landmarks(SIDE_POSE)[:32],
            crop_bbox=CROP_A,
            person_bbox=PERSON,
            frame_size=FRAME,
        )


# ---------------------------------------------------------------- 가까운 쪽 다리와 고정


def test_near_leg_is_the_more_visible_side() -> None:
    right_visible = {
        **{f"right_{j}": 1.0 for j in ("hip", "knee", "ankle")},
        **LEFT_LEG_HIDDEN,
    }
    assert analyze(visibility=right_visible).leg == "right"
    assert analyze().leg == "left"
    # 가시성이 같으면 왼쪽
    assert analyze(visibility={f"right_{j}": 1.0 for j in ("hip", "knee", "ankle")}).leg == "left"


def test_body_lock_keeps_leg_and_view_during_rep() -> None:
    lock = BodyLock()
    standing = analyze()
    assert lock.acquire(standing) is True
    assert lock.leg == "left"
    assert lock.view.is_side

    # 반복 중 오른쪽 다리가 더 잘 보이게 되어도 잠근 다리를 계속 쓴다.
    swapped = {
        **{f"right_{j}": 1.0 for j in ("hip", "knee", "ankle")},
        **LEFT_LEG_HIDDEN,
    }
    assert analyze(visibility=swapped).leg == "right"  # 고정하지 않으면 바뀐다
    assert analyze(visibility=swapped, leg=lock.leg).leg == "left"

    # 이미 잠겼으면 다른 프레임으로 다시 잠글 수 없다.
    assert lock.acquire(analyze(visibility=swapped)) is False
    assert lock.leg == "left"

    lock.release()
    assert lock.is_locked is False
    assert lock.acquire(analyze(visibility=swapped)) is True
    assert lock.leg == "right"


def test_body_lock_keeps_facing_and_the_signed_angles_stay_consistent() -> None:
    lock = BodyLock()
    assert lock.acquire(analyze()) is True
    assert lock.facing == "right"

    # 반복 중 발끝 landmark가 흔들려 heel→foot_index 방향이 뒤집힌 프레임
    flipped_toe = {**SIDE_POSE, "left_foot_index": (200, 310)}
    assert analyze(flipped_toe).facing == "left"  # 고정하지 않으면 방향이 바뀌어 부호가 뒤집힌다
    assert analyze(flipped_toe).torso_angle_signed == pytest.approx(-EXPECTED_TORSO_ANGLE, abs=1e-9)

    locked = analyze(flipped_toe, leg=lock.leg, facing=lock.facing)
    assert locked.facing == "right"
    assert locked.torso_angle_signed == pytest.approx(EXPECTED_TORSO_ANGLE, abs=1e-9)

    lock.release()
    with pytest.raises(RuntimeError):
        _ = lock.facing


def test_body_lock_refuses_when_facing_cannot_be_determined() -> None:
    lock = BodyLock()
    geometry = analyze({**SIDE_POSE, "left_foot_index": SIDE_POSE["left_heel"]})
    assert geometry.full_body.valid is True and geometry.facing is None
    assert lock.acquire(geometry) is False
    assert lock.is_locked is False


def test_body_lock_refuses_invalid_full_body() -> None:
    lock = BodyLock()
    invalid = analyze(person=(90, 90, 270, 480))  # bbox 하단이 프레임에 닿음
    assert invalid.full_body.valid is False
    assert lock.acquire(invalid) is False
    assert lock.is_locked is False
    with pytest.raises(RuntimeError):
        _ = lock.leg


def test_quality_is_enabled_only_for_locked_side_view_with_valid_body() -> None:
    lock = BodyLock()
    assert lock.quality_enabled(analyze()) is False  # 잠기지 않음

    lock.acquire(analyze())
    assert lock.quality_enabled(analyze()) is True
    assert lock.quality_enabled(analyze(person=(90, 90, 270, 480))) is False  # 현재 프레임 전신 무효

    front_lock = BodyLock()
    front_lock.acquire(analyze(FRONT_POSE))
    assert front_lock.is_locked and not front_lock.view.is_side
    assert front_lock.quality_enabled(analyze(FRONT_POSE)) is False  # 잠금 시점이 측면 아님


# ---------------------------------------------------------------- 전신 가시성


def test_baseline_is_a_valid_full_body() -> None:
    check = analyze().full_body
    assert check.valid is True
    assert check.reasons == ()


def test_ankle_outside_crop_is_invalid() -> None:
    crop = (50, 50, 350, 290)  # ankle y=300이 crop 아래로 나간다
    geometry = analyze(crop=crop)
    assert geometry.full_body.valid is False
    assert "outside_crop:left_ankle" in geometry.full_body.reasons


def test_foot_index_outside_crop_is_invalid() -> None:
    crop = (50, 50, 250, 400)  # foot_index x=260이 crop 오른쪽으로 나간다
    geometry = analyze(crop=crop)
    assert geometry.full_body.valid is False
    assert "outside_crop:left_foot_index" in geometry.full_body.reasons


@pytest.mark.parametrize(
    ("person", "side"),
    [
        ((90, 90, 270, 480), "bottom"),  # 프레임 높이 480에 닿음
        ((90, 90, 270, 479), "bottom"),  # 허용 오차 1px 이내
        ((0, 90, 270, 320), "left"),
        ((90, 90, 640, 320), "right"),
    ],
)
def test_bbox_touching_frame_border_is_invalid(person, side) -> None:
    geometry = analyze(person=person)
    assert geometry.full_body.valid is False
    assert f"bbox_touches_frame:{side}" in geometry.full_body.reasons


def test_bbox_just_inside_tolerance_is_valid() -> None:
    assert analyze(person=(90, 90, 270, 478)).full_body.valid is True


def test_head_cut_off_at_the_top_is_still_valid_when_shoulder_to_foot_is_visible() -> None:
    """머리가 화면 위로 잘려도(bbox 상단 접촉) 어깨~발끝이 모두 유효하면 유효하다."""
    for top in (0, 1):  # 경계 위, 허용 오차 1px
        check = analyze(person=(90, top, 270, 320)).full_body
        assert check.valid is True
        assert check.reasons == ()
        assert check.notes == ("bbox_touches_frame:top",)  # 무효 사유가 아닌 참고 정보로만 남는다
    assert analyze().full_body.notes == ()


def test_top_contact_does_not_hide_other_invalid_reasons() -> None:
    check = analyze(person=(90, 0, 270, 480)).full_body  # 상단과 하단 모두 접촉
    assert check.valid is False
    assert check.reasons == ("bbox_touches_frame:bottom",)
    assert check.notes == ("bbox_touches_frame:top",)


def test_low_shoulder_visibility_is_invalid() -> None:
    check = analyze(visibility={"left_shoulder": 0.2}).full_body
    assert check.valid is False
    assert check.reasons == ("low_visibility:left_shoulder",)


def test_only_the_used_side_shoulder_is_checked() -> None:
    # 사용하는 왼쪽 어깨가 보이면 반대쪽(먼 쪽) 어깨가 가려져도 유효하다.
    assert analyze(visibility={"right_shoulder": 0.1}).full_body.valid is True


def test_low_visibility_on_heel_is_invalid() -> None:
    geometry = analyze(visibility={"left_heel": 0.2})
    assert geometry.full_body.valid is False
    assert "low_visibility:left_heel" in geometry.full_body.reasons


def test_only_the_used_leg_is_checked() -> None:
    # 반대쪽 다리의 foot_index가 crop 밖이어도 사용하는 왼쪽 다리가 멀쩡하면 유효하다.
    crop = (50, 50, 292, 400)  # left_foot_index x=290은 안, right_foot_index x=294는 밖
    assert analyze(crop=crop).full_body.valid is True


# ---------------------------------------------------------------- 시점 판별


def test_side_view_is_accepted() -> None:
    geometry = analyze()
    assert geometry.view.is_side
    assert geometry.view_signals.shoulder_ratio == pytest.approx(4 / np.hypot(80, 80), abs=1e-9)


def test_front_view_is_rejected_by_shoulder_ratio() -> None:
    geometry = analyze(FRONT_POSE)
    assert not geometry.view.is_side
    assert geometry.view.reasons == ("shoulders_wide",)
    assert geometry.view_signals.shoulder_ratio == pytest.approx(2.0, abs=1e-9)


def test_back_view_is_rejected_by_hidden_nose_even_when_shoulders_overlap() -> None:
    geometry = analyze(SIDE_POSE, nose_visibility=0.1)
    assert not geometry.view.is_side
    assert geometry.view.reasons == ("nose_hidden",)


def test_shoulder_ratio_unavailable_is_not_side() -> None:
    collapsed = {name: (200, 200) for name in SIDE_POSE}  # 몸통 길이 0
    geometry = analyze(collapsed)
    assert geometry.view_signals.shoulder_ratio is None
    assert "shoulder_ratio_unavailable" in geometry.view.reasons


def test_hip_yaw_is_recorded_but_does_not_affect_the_judgement() -> None:
    side_world = build_world((0.0, 0.0, -0.1), (0.0, 0.0, 0.1))
    front_world = build_world((0.1, 0.0, 0.0), (-0.1, 0.0, 0.0))
    diagonal_world = build_world((0.1, 0.0, -0.1), (-0.1, 0.0, 0.1))

    assert analyze(world_landmarks=side_world).view_signals.hip_yaw_deg == pytest.approx(90.0)
    assert analyze(world_landmarks=front_world).view_signals.hip_yaw_deg == pytest.approx(0.0)
    assert analyze(world_landmarks=diagonal_world).view_signals.hip_yaw_deg == pytest.approx(45.0)

    # (a)(c)가 측면이면 yaw가 정면(0도)이어도 측면 판정이 유지된다.
    assert analyze(world_landmarks=front_world).view.is_side
    # (a)가 정면이면 yaw가 측면(90도)이어도 측면이 아니다.
    assert not analyze(FRONT_POSE, world_landmarks=side_world).view.is_side


def test_missing_world_landmarks_leave_yaw_unset() -> None:
    assert analyze().view_signals.hip_yaw_deg is None
    coincident = build_world((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    assert analyze(world_landmarks=coincident).view_signals.hip_yaw_deg is None


def test_view_classifier_can_be_replaced() -> None:
    class AlwaysRejects:
        def classify(self, signals):
            return ViewJudgement(reasons=("custom_rule",))

    geometry = analyze(view_classifier=AlwaysRejects())
    assert geometry.view.reasons == ("custom_rule",)

    stricter = ShoulderNoseViewClassifier(max_shoulder_ratio=0.01)
    assert not analyze(view_classifier=stricter).view.is_side


# ---------------------------------------------------------------- One Euro filter


def test_one_euro_first_sample_passes_through_and_constant_stays() -> None:
    smoother = OneEuroFilter()
    assert smoother(123.0, 0.0) == 123.0
    for step in range(1, 30):
        assert smoother(123.0, step / 30) == pytest.approx(123.0, abs=1e-9)


def test_one_euro_reduces_noise_on_a_steady_signal() -> None:
    rng = np.random.default_rng(0)
    noisy = 100.0 + rng.normal(0.0, 3.0, 300)
    smoother = OneEuroFilter()
    filtered = np.array([smoother(value, index / 30) for index, value in enumerate(noisy)])
    assert np.std(filtered[30:]) < 0.6 * np.std(noisy[30:])


def test_one_euro_follows_a_step_to_the_new_level() -> None:
    smoother = OneEuroFilter()
    for index in range(10):
        smoother(0.0, index / 30)
    value = 0.0
    for index in range(10, 130):
        value = smoother(100.0, index / 30)
    assert value == pytest.approx(100.0, abs=1.0)


def test_one_euro_depends_on_timestamps_not_on_frame_count() -> None:
    def response_at(rate_hz: float, horizon: float = 0.5) -> float:
        smoother = OneEuroFilter()
        smoother(0.0, 0.0)
        value = 0.0
        for index in range(1, int(round(horizon * rate_hz)) + 1):
            value = smoother(100.0, index / rate_hz)
        return value

    assert response_at(30.0) == pytest.approx(response_at(120.0), abs=8.0)


def test_one_euro_handles_irregular_frame_intervals() -> None:
    rng = np.random.default_rng(1)
    timestamps = np.cumsum(rng.uniform(0.01, 0.08, 200))
    smoother = OneEuroFilter()
    smoother(0.0, 0.0)
    outputs = [smoother(100.0, float(t)) for t in timestamps]
    assert all(b >= a - 1e-9 for a, b in zip(outputs, outputs[1:]))  # 입력이 일정하면 단조 수렴
    assert outputs[-1] == pytest.approx(100.0, abs=1.0)


def test_one_euro_ignores_duplicate_or_regressed_timestamps() -> None:
    clean = OneEuroFilter()
    noisy = OneEuroFilter()
    for filter_ in (clean, noisy):
        filter_(10.0, 0.0)
        filter_(20.0, 0.1)
    assert noisy(1000.0, 0.1) == clean._value  # 같은 시각
    assert noisy(-50.0, 0.05) == clean._value  # 역행한 시각
    assert noisy(20.0, 0.2) == pytest.approx(clean(20.0, 0.2))


def test_one_euro_beta_reduces_lag_on_fast_motion() -> None:
    def lag(beta: float) -> float:
        smoother = OneEuroFilter(min_cutoff=1.0, beta=beta, d_cutoff=1.0)
        value = 0.0
        truth = 0.0
        for index in range(31):
            truth = 100.0 * index / 30  # 100도/초로 올라가는 신호
            value = smoother(truth, index / 30)
        return truth - value

    assert lag(0.02) < lag(0.0)


def test_one_euro_reset_forgets_history() -> None:
    smoother = OneEuroFilter()
    smoother(10.0, 0.0)
    smoother(50.0, 0.1)
    smoother.reset()
    assert smoother(70.0, 5.0) == 70.0


def test_one_euro_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        OneEuroFilter(min_cutoff=0.0)
    with pytest.raises(ValueError):
        OneEuroFilter(d_cutoff=-1.0)
    with pytest.raises(ValueError):
        OneEuroFilter(beta=-0.1)
