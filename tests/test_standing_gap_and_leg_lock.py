"""두 버그 수정(기본 동작): ① 잠금 유지 중 짧은 사람 없음이 STANDING을 지우지 않는다, ② 잠근 다리가 무효여도 반대 다리로 갱신하고
다리 선택에 히스테리시스를 둔다. 합성 시퀀스로 놓침 길이별(0.12초, 0.3초, 1.0초, 상한 초과) 거동과 반복 중 고정을 검증한다."""

import pytest

import config.settings as settings
from src.geometry_tracker import GeometryTracker
from src.pose_geometry import landmarks_to_array, select_near_leg
from src.rep_tracker import RepFrame, RepTracker, STATE_STANDING, STATE_WAITING_LOCK, track_primary_person
from test_pose_geometry import FRAME, build_landmarks
from test_rep_tracker import counted, rep_curve, run
from test_sequence_logger import CROP_S, STANDING_POSE, make_person, squatting, standing

REST = 1.5  # rep_curve의 처음 서 있는 시간(초). 이 뒤에 1.2초 동안 내려간다(175도 -> 70도)
GAP_LIMIT = settings.REP_STANDING_MAX_GAP_SECONDS


def with_dropout(start, length):
    """start부터 length초 동안 사람을 놓친 반복 한 번. 잠금은 유지된다."""
    return rep_curve(blank=(start, length))


# ---------------------------------------------------------------- ① 서 있는 중 놓침


def test_the_limit_is_the_same_one_and_a_half_seconds_as_the_in_rep_tolerance() -> None:
    assert GAP_LIMIT == settings.REP_MAX_GAP_SECONDS == 1.5 < settings.BODY_LOCK_MISSING_RELEASE_SECONDS


@pytest.mark.parametrize("length", [0.12, 0.3, 1.0])
def test_a_short_dropout_at_the_start_of_the_descent_no_longer_loses_the_rep(length) -> None:
    frames = with_dropout(REST - 0.05, length)  # 마지막 서 있는 프레임을 덮고, 다시 보일 때는 이미 내려가는 중(0.12초는 아직 160도 이상일 수 있다)
    results = run(RepTracker(), frames)
    assert len(counted(results)) == 1
    assert results[0].hip_drop_norm > settings.REP_MIN_HIP_DROP  # 서 있던 기준값이 지워지지 않았다


@pytest.mark.parametrize("length", [0.3, 1.0])
def test_the_old_behaviour_is_reachable_with_a_zero_limit_and_loses_the_rep(length) -> None:
    results = run(RepTracker(standing_max_gap_seconds=0.0), with_dropout(REST - 0.05, length))
    assert counted(results) == []  # 수정 전 동작(다시 보인 첫 프레임이 160도 미만이라 STANDING으로 못 돌아간다)


def test_the_first_frame_back_can_already_be_far_into_the_descent() -> None:
    frames = with_dropout(REST - 0.05, 1.0)
    first_back = next(f for f, _ in frames if f.present and f.timestamp > REST + 0.9)
    assert first_back.knee_smoothed < settings.REP_DESCENT_KNEE_ANGLE  # 이미 하강 기준 아래에서 다시 보인다
    assert len(counted(run(RepTracker(), frames))) == 1


def test_a_dropout_over_the_limit_resets_as_before() -> None:
    results = run(RepTracker(), with_dropout(REST - 0.05, GAP_LIMIT + 0.1))
    assert counted(results) == []  # 상한을 넘기면 기존처럼 WAITING_LOCK으로 초기화(보이지 않은 하강은 센 수 없다)


def test_the_state_stays_standing_through_the_gap_and_resets_after_the_limit() -> None:
    tracker = RepTracker()
    start = REST - 0.05
    states = []
    for frame, label in with_dropout(start, GAP_LIMIT + 0.5):
        tracker.update(frame, label)
        if not frame.present:
            states.append((frame.timestamp - start, tracker.state))
    inside = [state for t, state in states if t <= GAP_LIMIT - 0.1]
    outside = [state for t, state in states if t > GAP_LIMIT + 0.1]
    assert inside and set(inside) == {STATE_STANDING}
    assert outside and set(outside) == {STATE_WAITING_LOCK}


def test_a_dropout_without_the_lock_resets_even_when_short() -> None:
    frames = rep_curve(blank=(REST - 0.05, 0.3))
    unlocked = [(RepFrame.missing(f.timestamp, locked=False) if not f.present else f, label) for f, label in frames]
    assert counted(run(RepTracker(), unlocked)) == []


def test_missing_frames_default_to_an_unlocked_reset() -> None:
    assert RepFrame.missing(1.0).locked is False
    assert RepFrame.missing(1.0, locked=True).locked is True


def test_a_dropout_while_waiting_for_the_lock_changes_nothing() -> None:
    tracker = RepTracker()
    tracker.update(RepFrame.missing(0.0, locked=True), None)
    assert tracker.state == STATE_WAITING_LOCK


def test_an_in_rep_dropout_uses_the_same_limit_and_aborts_after_it() -> None:
    inside = run(RepTracker(), rep_curve(blank=(REST + 0.4, GAP_LIMIT - 0.2)))
    assert len(counted(inside)) == 1  # 반복 중 놓침도 같은 상한까지 보간한다
    outside = run(RepTracker(), rep_curve(blank=(REST + 0.6, GAP_LIMIT + 0.4)))
    assert counted(outside) == [] and any("tracking_lost" in r.reasons for r in outside)


def test_the_pipeline_passes_the_lock_state_into_missing_frames() -> None:
    tracker = GeometryTracker()
    standing(tracker, 0.0)
    assert standing(tracker, 0.5).lock.locked
    _, lock, rep_frame = track_primary_person(tracker, None, FRAME, 0.6)
    assert lock.locked and rep_frame.locked and not rep_frame.present
    _, lock, rep_frame = track_primary_person(tracker, None, FRAME, 0.6 + settings.BODY_LOCK_MISSING_RELEASE_SECONDS + 0.1)
    assert not lock.locked and not rep_frame.locked


# ---------------------------------------------------------------- ② 다리 선택 히스테리시스와 잠금 교착

RIGHT_VISIBLE = {f"right_{j}": 1.0 for j in ("hip", "knee", "ankle", "heel", "foot_index")}
LEFT_HIDDEN = {f"left_{j}": 0.1 for j in ("knee", "ankle", "heel", "foot_index")}
LEFT_VISIBLE = {f"left_{j}": 1.0 for j in ("hip", "knee", "ankle", "heel", "foot_index")}
RIGHT_HIDDEN = {f"right_{j}": 0.1 for j in ("knee", "ankle", "heel", "foot_index")}


def lock_on_left(**options):
    tracker = GeometryTracker(**options)
    standing(tracker, 0.0, visibility={**LEFT_VISIBLE, **RIGHT_HIDDEN})
    assert standing(tracker, 0.5, visibility={**LEFT_VISIBLE, **RIGHT_HIDDEN}).lock.leg == "left"
    return tracker


def far_leg_only(tracker, seconds, start=1.0, step=0.05):
    """잠근 왼쪽 다리는 가려지고 오른쪽 다리만 보이는 상태로 서 있는다. 마지막 프레임 결과와 잠금 다리 이력을 돌려준다."""
    legs, last = [], None
    for i in range(int(seconds / step)):
        last = standing(tracker, start + i * step, visibility={**RIGHT_VISIBLE, **LEFT_HIDDEN})
        legs.append(last.lock.leg)
    return last, legs


def test_before_the_fix_a_locked_leg_that_became_invisible_blocks_the_refresh_forever() -> None:
    tracker = lock_on_left(other_leg_refresh=False, leg_switch_margin=0.0)
    last, legs = far_leg_only(tracker, 3.0)
    assert set(legs) == {"left"} and last.knee_angle_smoothed is None and not last.geometry.full_body.valid


def test_the_lock_moves_to_the_visible_leg_when_the_locked_leg_is_invalid_and_the_person_stands() -> None:
    tracker = lock_on_left()
    last, legs = far_leg_only(tracker, 3.0)
    assert legs[-1] == "right" and "right" in legs[:20]  # 1초 안에 바뀐다
    assert last.geometry.full_body.valid and last.knee_angle_smoothed is not None  # 반복 추적에 쓸 수 있는 상태로 돌아온다


def test_the_leg_does_not_change_while_the_locked_leg_is_valid() -> None:
    tracker = lock_on_left()
    legs = [standing(tracker, 1.0 + i * 0.05, visibility={**LEFT_VISIBLE, **RIGHT_HIDDEN}).lock.leg for i in range(40)]
    assert set(legs) == {"left"}


def test_the_leg_is_frozen_during_a_rep_until_standing_is_confirmed_on_the_other_leg() -> None:
    tracker = lock_on_left()
    for i in range(21):
        last = squatting(tracker, 1.0 + i * 0.05, visibility={**LEFT_VISIBLE, **RIGHT_HIDDEN})  # 내려가는 중
    assert last.knee_angle_smoothed < settings.REP_DESCENT_KNEE_ANGLE
    # 이제 왼쪽 다리가 가려지고 오른쪽 다리가 곧게 보이는 프레임이 이어진다
    quick = standing(tracker, 2.1, visibility={**RIGHT_VISIBLE, **LEFT_HIDDEN})
    assert quick.lock.leg == "left"  # 반복 중에는 고정: 서 있음이 확인되기 전에는 바꾸지 않는다
    last = quick
    for i in range(1, 20):
        last = standing(tracker, 2.1 + i * 0.05, visibility={**RIGHT_VISIBLE, **LEFT_HIDDEN})
    assert last.lock.leg == "right"  # 0.5초 이상 서 있음이 이어지면 갱신된다


def _array(left, right):
    visibility = {f"left_{j}": left for j in ("hip", "knee", "ankle")}
    visibility.update({f"right_{j}": right for j in ("hip", "knee", "ankle")})
    return landmarks_to_array(build_landmarks(STANDING_POSE, CROP_S, visibility, default_visibility=1.0))


def test_select_near_leg_hysteresis_only_switches_when_the_difference_exceeds_the_margin() -> None:
    assert select_near_leg(_array(0.9, 1.0)) == "right"  # 기본(히스테리시스 없음)은 높은 쪽
    assert select_near_leg(_array(0.9, 1.0), previous="left", margin=0.5) == "left"  # 합 차이 0.3 < 0.5: 유지
    assert select_near_leg(_array(0.5, 1.0), previous="left", margin=0.5) == "right"  # 합 차이 1.5 > 0.5: 바뀐다
    assert select_near_leg(_array(1.0, 1.0), previous="right", margin=0.3) == "right"


def test_similar_visibilities_no_longer_flip_the_leg_every_frame() -> None:
    def run_flips(tracker):
        flips, previous = 0, None
        for i in range(60):
            wobble = 0.03 if i % 2 else -0.03  # 두 다리 가시성이 프레임마다 근소하게(관절 3개 합 차이 0.18, 기준 0.3 안쪽) 엇갈린다
            visibility = {f"left_{j}": 0.9 + wobble for j in ("hip", "knee", "ankle", "heel", "foot_index")}
            visibility.update({f"right_{j}": 0.9 - wobble for j in ("hip", "knee", "ankle", "heel", "foot_index")})
            leg = standing(tracker, i * 0.05, visibility=visibility).geometry_now.leg
            flips += previous is not None and leg != previous
            previous = leg
        return flips

    assert run_flips(GeometryTracker(leg_switch_margin=0.0, other_leg_refresh=False)) >= 50
    assert run_flips(GeometryTracker()) <= 1


def test_the_defaults_are_the_fixed_behaviour() -> None:
    assert settings.LEG_SWITCH_VISIBILITY_MARGIN == 0.3
    tracker = GeometryTracker()
    assert tracker._leg_margin == settings.LEG_SWITCH_VISIBILITY_MARGIN and tracker._other_leg_refresh is True
    assert track_primary_person(tracker, make_person(), FRAME, 0.0)[2].present
