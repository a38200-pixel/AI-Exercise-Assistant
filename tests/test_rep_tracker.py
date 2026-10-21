"""RepTracker: 합성 시퀀스로 상태기계와 확정 조건을, 실측 로그에서 뽑은 fixture로 회귀를 검증한다."""

import json
import math
from pathlib import Path

import pytest

from src.exercise_counter import SQUAT_MODE, STRETCH_MODE, ExerciseCounter
from src.geometry_tracker import BodyLockPolicy, GeometryTracker
from src.rep_tracker import (
    NOTICE_FULL_BODY_INVALID,
    NOTICE_NOT_SIDE,
    REASON_FEET_APART,
    REASON_FEET_APART_BOTTOM,
    REASON_HIP_SHIFT,
    REASON_LOCK_LOST,
    REASON_OTHER_EXERCISE,
    REASON_SHALLOW_HIP_DROP,
    REASON_TOO_SHORT,
    REASON_TRACKING_LOST,
    STATE_IN_REP,
    STATE_STANDING,
    STATE_WAITING_LOCK,
    RepFrame,
    RepMeasures,
    RepTracker,
    measure_frame,
    track_primary_person,
)
from test_pose_geometry import build_landmarks
from test_sequence_logger import CROP_S, PERSON_S, RIGHT_LEG_HIDDEN, STANDING_POSE, make_person

FPS = 30
BASE_HIP_Y = 150.0
LEG_LENGTH = 160.0
FIXTURES = Path(__file__).parent / "fixtures" / "rep_sessions"


# ---------------------------------------------------------------- 합성 시퀀스


def make_frame(t, knee, *, hip_y=BASE_HIP_Y, ankle_gap=3.0, locked=True, present=True, hip_x=float("nan")):
    if not present:
        return RepFrame.missing(t, locked=locked)  # 놓쳐도 잠금은 유지된다(짧은 놓침)
    return RepFrame(
        timestamp=t,
        present=True,
        knee_smoothed=knee,
        locked=locked,
        leg="left",
        facing="right",
        torso_signed=45.0,
        shin_signed=28.0,
        measures=RepMeasures(hip_y=hip_y, heel_y=318.0, leg_length=LEG_LENGTH, ankle_gap=ankle_gap, hip_x=hip_x),
    )


def rep_curve(
    start=0.0,
    *,
    rest_before=1.5,
    down=1.2,
    hold=0.5,
    up=1.2,
    rest_after=1.5,
    bottom=70.0,
    hip_drop=0.55,
    ankle_gap_norm=0.02,
    bottom_ankle_gap_norm=None,
    hip_shift_norm=None,
    label="squat",
    locked=True,
    blank=None,
):
    """서 있음 → 내려감 → 최저점 유지 → 올라옴 → 서 있음 한 번. blank=(시작 초, 길이 초)는 그 구간을 사람 없음으로 만든다.

    bottom_ankle_gap_norm: 최저점에서의 양발 간격(다리 길이 비). 주지 않으면 서 있을 때와 같다.
    hip_shift_norm: 최저점에서 엉덩이 x가 서 있을 때보다 가로로 옮겨 간 양(다리 길이 비). 주지 않으면 엉덩이 x를 모른다(NaN)."""
    frames = []
    total = rest_before + down + hold + up + rest_after
    for index in range(int(total * FPS)):
        s = index / FPS
        if s < rest_before:
            knee = 175.0
        elif s < rest_before + down:
            knee = 175.0 - (175.0 - bottom) * (s - rest_before) / down
        elif s < rest_before + down + hold:
            knee = bottom
        elif s < rest_before + down + hold + up:
            knee = bottom + (175.0 - bottom) * (s - rest_before - down - hold) / up
        else:
            knee = 175.0
        depth = (175.0 - knee) / (175.0 - bottom)
        hip_y = BASE_HIP_Y + hip_drop * LEG_LENGTH * depth
        present = not (blank is not None and blank[0] <= s < blank[0] + blank[1])
        gap_norm = ankle_gap_norm if bottom_ankle_gap_norm is None else ankle_gap_norm + (bottom_ankle_gap_norm - ankle_gap_norm) * depth
        # 서 있을 때(무릎각 160 이상)는 x가 그대로이고 최저점에서 hip_shift_norm만큼 옮겨 간다(측정 이동 폭이 입력과 같도록 160도에서 시작).
        hip_depth = min(1.0, max(0.0, (160.0 - knee) / (160.0 - bottom)))
        hip_x = float("nan") if hip_shift_norm is None else 200.0 + hip_shift_norm * LEG_LENGTH * hip_depth
        frame = make_frame(
            start + s, knee, hip_y=hip_y, ankle_gap=gap_norm * LEG_LENGTH, locked=locked, present=present, hip_x=hip_x
        )
        # 사람이 없는 구간의 stable 라벨은 파이프라인과 같이 None이다.
        frames.append((frame, None if not present else ("stand" if knee >= 160 else label)))
    return frames


def run(tracker, frames):
    results = []
    for frame, label in frames:
        result = tracker.update(frame, label)
        if result is not None:
            results.append(result)
    return results


def counted(results):
    return [r for r in results if r.counted]


# ---------------------------------------------------------------- 상태기계와 확정 조건


def test_a_clean_squat_is_counted_with_its_measurements() -> None:
    tracker = RepTracker()
    results = run(tracker, rep_curve())

    assert len(results) == 1 and results[0].counted and results[0].reasons == ()
    rep = results[0]
    assert rep.min_knee_angle == pytest.approx(70.0, abs=0.5)
    assert rep.hip_drop_norm == pytest.approx(0.55, abs=0.03)
    assert rep.ankle_gap_norm == pytest.approx(0.02, abs=0.005)
    assert 2.0 < rep.total_seconds < 3.2
    assert rep.descent_seconds > 0.5 and rep.bottom_dwell_seconds > 0.3 and rep.ascent_seconds > 0.5
    assert rep.leg == "left" and rep.facing == "right"
    assert rep.torso_signed_at_bottom == pytest.approx(45.0) and rep.shin_signed_at_bottom == pytest.approx(28.0)
    assert rep.label_seconds["squat"] > 0 and rep.other_exercise_ratio == pytest.approx(0.0)
    assert tracker.state == STATE_STANDING and tracker.last_result is rep


def test_consecutive_squats_are_each_counted() -> None:
    tracker = RepTracker()
    frames = rep_curve(0.0, rest_after=0.0)
    frames += rep_curve(frames[-1][0].timestamp + 1 / FPS, rest_before=1.0)
    assert len(counted(run(tracker, frames))) == 2


def test_the_knee_must_go_below_the_descent_angle_not_just_leave_standing() -> None:
    tracker = RepTracker()
    assert run(tracker, rep_curve(bottom=155.0)) == []  # 150도 미만으로 내려가지 않으면 반복이 아니다
    assert tracker.state == STATE_STANDING


def test_a_rep_shorter_than_one_second_is_rejected() -> None:
    results = run(RepTracker(), rep_curve(down=0.3, hold=0.0, up=0.3))
    assert len(results) == 1 and not results[0].counted
    assert REASON_TOO_SHORT in results[0].reasons


def test_a_rep_without_enough_hip_drop_is_rejected() -> None:
    results = run(RepTracker(), rep_curve(hip_drop=0.10))
    assert results[0].reasons == (REASON_SHALLOW_HIP_DROP,)


def test_a_rep_that_starts_with_the_feet_far_apart_is_rejected() -> None:
    results = run(RepTracker(), rep_curve(ankle_gap_norm=0.55, bottom_ankle_gap_norm=0.02))
    assert results[0].reasons == (REASON_FEET_APART,)


def test_the_standing_gap_limit_is_a_boundary_at_0_25() -> None:
    assert run(RepTracker(), rep_curve(ankle_gap_norm=0.24, bottom_ankle_gap_norm=0.02))[0].counted
    assert run(RepTracker(), rep_curve(ankle_gap_norm=0.26, bottom_ankle_gap_norm=0.02))[0].reasons == (REASON_FEET_APART,)


def test_a_rep_whose_feet_are_apart_at_the_bottom_is_rejected_even_if_they_start_together() -> None:
    # 발을 먼저 내딛는 런지: 서 있을 때 간격(기준 창)은 좁게 잡혔지만 최저점에서는 크게 벌어져 있다(P01 런지 14.3초: 0.24 대 1.11).
    results = run(RepTracker(), rep_curve(ankle_gap_norm=0.05, bottom_ankle_gap_norm=1.1))
    assert results[0].reasons == (REASON_FEET_APART_BOTTOM,)
    assert results[0].ankle_gap_bottom_norm == pytest.approx(1.1, abs=0.02)


def test_the_bottom_gap_limit_is_a_boundary_at_0_40() -> None:
    assert run(RepTracker(), rep_curve(bottom_ankle_gap_norm=0.38))[0].counted
    assert run(RepTracker(), rep_curve(bottom_ankle_gap_norm=0.42))[0].reasons == (REASON_FEET_APART_BOTTOM,)


def test_a_small_bottom_gap_like_a_real_squat_is_counted() -> None:
    result = run(RepTracker(), rep_curve(bottom_ankle_gap_norm=0.16))[0]  # 실측 스쿼트 최대(본인 0.16)
    assert result.counted and result.ankle_gap_bottom_norm == pytest.approx(0.16, abs=0.01)


def test_the_hip_shift_limit_is_a_boundary_at_0_70() -> None:
    assert run(RepTracker(), rep_curve(hip_shift_norm=0.68))[0].counted
    far = run(RepTracker(), rep_curve(hip_shift_norm=0.72))[0]
    assert far.reasons == (REASON_HIP_SHIFT,) and far.hip_shift_norm == pytest.approx(0.72, abs=0.02)


def test_a_real_squat_hip_shift_is_counted_and_a_walk_away_is_rejected() -> None:
    assert run(RepTracker(), rep_curve(hip_shift_norm=0.34))[0].counted  # 실측 스쿼트 최대
    assert REASON_HIP_SHIFT in run(RepTracker(), rep_curve(hip_shift_norm=1.18))[0].reasons  # 자리를 뜨는 동작(c10 80.1초)


def test_an_unknown_hip_x_skips_the_hip_shift_condition() -> None:
    result = run(RepTracker(), rep_curve())[0]  # 엉덩이 x를 모르는 입력(옛 fixture)
    assert result.counted and math.isnan(result.hip_shift_norm)


def test_the_hip_shift_is_judged_when_the_rep_ends_and_does_not_unlock_the_rep_midway() -> None:
    tracker = RepTracker()
    frames = rep_curve(hip_shift_norm=1.18)
    states = []
    for frame, label in frames:
        tracker.update(frame, label)
        states.append(tracker.state)
    assert STATE_IN_REP in states and states[-1] == STATE_STANDING  # 반복은 끝까지 진행되고, 끝날 때 탈락한다
    assert tracker.last_result.reasons == (REASON_HIP_SHIFT,)


def test_a_rep_dominated_by_other_exercise_labels_is_counted_and_the_ratio_is_only_recorded() -> None:
    # ML 라벨 비율은 확정 조건이 아니다(기록만): 비율이 1.00이어도 기하 조건을 통과하면 확정한다.
    result = run(RepTracker(), rep_curve(label="walk"))[0]
    assert result.counted and result.reasons == ()
    assert result.other_exercise_ratio > 0.4


def test_giving_an_explicit_ml_limit_makes_it_a_condition_again() -> None:
    results = run(RepTracker(other_max_ratio=0.40), rep_curve(label="walk"))
    assert results[0].reasons == (REASON_OTHER_EXERCISE,)
    assert results[0].other_exercise_ratio > 0.4


@pytest.mark.parametrize("label", ["jump", "sit", "bendover", "stretch"])
def test_labels_that_real_squats_get_misclassified_as_do_not_reject_a_rep(label) -> None:
    # jump·sit·bendover는 실제 스쿼트가 오분류되는 라벨이고 stretch는 배제 목록에 넣지 않기로 했다.
    results = run(RepTracker(), rep_curve(label=label))
    assert results[0].counted and results[0].other_exercise_ratio == pytest.approx(0.0)


def test_a_chair_sit_down_is_counted_as_a_squat_known_limitation() -> None:
    # 의자·박스 앉았다 일어나기는 스쿼트와 동작이 같아 걸러내지 않는다(RELEASE.md의 한계).
    results = run(RepTracker(), rep_curve(bottom=80.0, hip_drop=0.43, down=1.6, hold=2.4, up=1.6, label="sit"))
    assert len(counted(results)) == 1


def test_nothing_is_counted_while_the_body_lock_is_not_held() -> None:
    tracker = RepTracker()
    assert run(tracker, rep_curve(locked=False)) == []
    assert tracker.state == STATE_WAITING_LOCK and tracker.guidance == "need_side_standing"


def test_losing_the_lock_in_the_middle_of_a_rep_aborts_it() -> None:
    tracker = RepTracker()
    frames = rep_curve()
    cut = int(2.2 * FPS)  # 내려가는 중
    frames = frames[:cut] + [(make_frame(f.timestamp, f.knee_smoothed, locked=False), label) for f, label in frames[cut:]]
    results = run(tracker, frames)
    assert len(results) == 1 and results[0].reasons == (REASON_LOCK_LOST,) and not results[0].counted
    assert tracker.state == STATE_WAITING_LOCK


def test_a_long_gap_without_a_knee_angle_aborts_the_rep() -> None:
    results = run(RepTracker(), rep_curve(hold=2.5, blank=(2.8, 2.0)))  # 최저점 근처에서 2초 동안 사람 없음
    assert results[0].reasons == (REASON_TRACKING_LOST,) and not results[0].counted


def test_a_short_gap_does_not_break_the_rep() -> None:
    results = run(RepTracker(), rep_curve(hold=1.5, blank=(2.9, 1.0)))  # 1초 공백은 견딘다
    assert len(results) == 1 and results[0].counted
    assert results[0].pose_missing_ratio > 0.0  # 놓친 시간은 비율로 남는다


def test_an_invalid_body_frame_counts_toward_the_gap_too() -> None:
    frames = rep_curve(hold=2.5)
    start, stop = int(2.8 * FPS), int(4.8 * FPS)
    frames = [
        (make_frame(f.timestamp, None) if start <= index < stop else f, label)
        for index, (f, label) in enumerate(frames)
    ]
    assert run(RepTracker(), frames)[0].reasons == (REASON_TRACKING_LOST,)


def test_reset_discards_the_rep_in_progress() -> None:
    tracker = RepTracker()
    frames = rep_curve()
    run(tracker, frames[: int(2.4 * FPS)])
    assert tracker.state == STATE_IN_REP and tracker.guidance == "in_rep"
    tracker.reset()
    assert tracker.state == STATE_WAITING_LOCK and tracker.last_result is None
    assert len(counted(run(tracker, rep_curve(start=10.0)))) == 1  # 처음부터 다시 센다


def test_the_hysteresis_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        RepTracker(standing_angle=150.0, descent_angle=160.0)


# ---------------------------------------------------------------- ExerciseCounter 연결


def test_squat_count_only_follows_confirmed_reps() -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    for frame, label in rep_curve():
        counter.update(label, frame.timestamp, frame)
    assert counter.squat_count == 1 and counter.last_rep_result.counted

    # 라벨만으로는 세지 않는다: rep_frame 없이 stand → squat → stand를 넣어도 그대로다.
    for label in ("stand", "squat", "stand"):
        counter.update(label, 99.0)
    assert counter.squat_count == 1


def test_rejected_reps_are_kept_but_not_counted() -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    for frame, label in rep_curve(hip_drop=0.10):
        counter.update(label, frame.timestamp, frame)
    assert counter.squat_count == 0
    assert counter.last_rep_result.reasons == (REASON_SHALLOW_HIP_DROP,)


def test_status_reports_the_rep_state_and_guidance() -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    status = counter.get_status(0.0)
    assert status["state"] == STATE_WAITING_LOCK and status["rep_guidance"] == "need_side_standing"
    assert status["last_rep"] is None

    legacy = ExerciseCounter()  # RepTracker 없이는 v0.1.x 동작과 상태 이름을 유지한다
    legacy.set_mode(SQUAT_MODE, 0.0)
    assert legacy.get_status(0.0)["state"] == "WAITING_STAND" and legacy.get_status(0.0)["rep_guidance"] is None


def test_resets_and_mode_changes_clear_the_rep_tracker() -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    frames = rep_curve()
    for frame, label in frames[: int(2.4 * FPS)]:
        counter.update(label, frame.timestamp, frame)
    assert counter.get_status(3.0)["state"] == STATE_IN_REP

    counter.reset_current_exercise(3.0)
    assert counter.get_status(3.0)["state"] == STATE_WAITING_LOCK and counter.squat_count == 0

    for frame, label in frames[: int(2.4 * FPS)]:
        counter.update(label, frame.timestamp, frame)
    counter.set_mode(STRETCH_MODE, 4.0)
    counter.set_mode(SQUAT_MODE, 5.0)
    assert counter.get_status(5.0)["state"] == STATE_WAITING_LOCK

    for frame, label in frames[: int(2.4 * FPS)]:
        counter.update(label, frame.timestamp, frame)
    counter.reset_all_exercises()
    assert counter.get_status(6.0)["state"] == STATE_WAITING_LOCK


def test_stretch_mode_does_not_use_the_rep_tracker() -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(STRETCH_MODE, 0.0)
    counter.update("stretch", 1.0)
    counter.update("stand", 3.0)
    assert counter.get_status(3.0)["stretch_seconds"] == pytest.approx(2.0)
    assert counter.squat_count == 0


# ---------------------------------------------------------------- landmark → RepFrame


def test_measure_frame_returns_frame_pixel_coordinates_of_the_locked_leg() -> None:
    landmarks = build_landmarks(STANDING_POSE, CROP_S, {"nose": 0.99, **RIGHT_LEG_HIDDEN})
    measures = measure_frame(landmarks, CROP_S, "left")
    assert measures.hip_y == pytest.approx(150.0, abs=0.01)  # crop 원점을 더한 프레임 좌표
    assert measures.heel_y == pytest.approx(318.0, abs=0.01)
    assert measures.leg_length == pytest.approx(160.0, abs=0.01)  # 엉덩이(150)~무릎(230)~발목(310)
    assert measures.ankle_gap == pytest.approx(3.0, abs=0.01)  # 왼쪽 200, 오른쪽 203


def test_track_primary_person_builds_the_rep_input_and_the_lock() -> None:
    tracker = GeometryTracker()
    person = make_person()
    tracked, lock, frame = track_primary_person(tracker, person, (640, 480), 0.0)
    assert tracked is not None and frame.present and frame.locked is False  # 측면이 0.5초 이어지기 전
    tracked, lock, frame = track_primary_person(tracker, person, (640, 480), 0.5)
    assert lock.locked and frame.locked and frame.leg == "left" and frame.facing == "right"
    assert frame.knee_smoothed == pytest.approx(180.0, abs=1e-6)
    assert frame.measures.leg_length == pytest.approx(160.0, abs=0.01)


def test_track_primary_person_treats_nobody_and_broken_landmarks_as_missing() -> None:
    tracker = GeometryTracker()
    tracked, lock, frame = track_primary_person(tracker, None, (640, 480), 0.0)
    assert tracked is None and frame.present is False and lock.locked is False

    broken = {**make_person(), "landmarks": ["not", "landmarks"]}
    tracked, lock, frame = track_primary_person(tracker, broken, (640, 480), 0.1)  # 예외 없이 놓침으로 처리
    assert tracked is None and frame.present is False


# ---------------------------------------------------------------- 실측 로그 회귀(field_test_1, tests/fixtures/rep_sessions)


# 기하 조건(1차)과 ML 조건(2차)이 각각 혼자서도 제 일을 하는지 보기 위해 한쪽을 끈 설정.
GEOMETRY_ONLY = {"other_max_ratio": 2.0}  # ML 조건을 끈다(비율은 최대 1이라 탈락하지 않는다)
# 기하 조건을 모두 끄고 ML 조건만 명시적으로 켠다(ML 조건은 기본이 아니다).
ML_ONLY = {
    "min_seconds": 0.0, "min_hip_drop": -10.0, "max_ankle_gap": 10.0, "max_ankle_gap_bottom": None, "max_hip_shift": None,
    "other_max_ratio": 0.40,
}


def simulate(session: str, events_out: list | None = None, **tracker_options):
    """fixture의 신호(평활 무릎각, 프레임별 측면 판정·전신 유효)를 새 BodyLockPolicy와 RepTracker에 그대로 넣어 재생한다.

    잠금은 fixture에 기록된 옛 임시 정책의 값이 아니라 BodyLockPolicy가 다시 정한다. 반환: (fixture, 반복 결과, 프레임별
    (시각, 잠금 여부, 안내 사유) 타임라인, BodyLockPolicy 결정 이벤트 [(시각, 결정)]).
    """
    payload = json.loads((FIXTURES / f"session_{session}.json").read_text(encoding="utf-8"))
    columns = payload["columns"]
    policy = BodyLockPolicy()
    tracker = RepTracker(**tracker_options)
    results, timeline, events = [], [], []
    leg = facing = None
    for row in payload["rows"]:
        values = dict(zip(columns, row))
        t = values["t"]
        if values["present"]:
            knee = values["knee_smoothed"]
            decision = policy.step(
                t,
                standing=knee is not None and knee >= 160.0,
                side_now=bool(values["side_now"]),
                lockable=bool(values["valid"]) and values["facing_now"] is not None,
            )
            if decision in ("acquire", "refresh"):
                leg, facing = values["leg_now"], values["facing_now"]
            measures = (
                RepMeasures(
                    values["hip_y"], values["heel_y"], values["leg_length"], values["ankle_gap"],
                    float("nan") if values.get("hip_x") is None else values["hip_x"],
                )
                if values["hip_y"] is not None
                else None
            )
            frame = RepFrame(
                t, True, knee, policy.locked, leg, facing, values["torso_signed"], values["shin_signed"], measures,
                side_now=bool(values["side_now"]), body_valid=bool(values["valid"]),
            )
        else:
            decision = policy.missing(t)
            frame = RepFrame.missing(t, locked=policy.locked)
        if decision in ("acquire", "release_view", "release_missing"):
            events.append((t, decision))
        result = tracker.update(frame, values["label"])
        if result is not None:
            results.append(result)
        if events_out is not None:
            events_out.extend(tracker.pop_events())
        timeline.append((t, policy.locked, tracker.notice))
    return payload, results, timeline, events


def replay(session: str, **tracker_options):
    payload, results, _, _ = simulate(session, **tracker_options)
    return payload, results


@pytest.mark.parametrize(
    ("session", "actual"),
    [("1", 10), ("2", 8), ("3", 8), ("4", 8), ("5", 8)],
    ids=["side-parallel", "side-deep", "side-shallow", "side-torso-lean", "side-heel-lift"],
)
def test_side_squat_sessions_are_counted_exactly(session, actual) -> None:
    payload, results = replay(session)
    assert payload["actual_squats"] == actual
    assert len(counted(results)) == actual
    # 탈락한 것은 세션 앞뒤의 이동 구간(짧은 굴곡)뿐이다.
    assert all(REASON_TOO_SHORT in r.reasons for r in results if not r.counted)


@pytest.mark.parametrize("session", ["8a", "8c"])
def test_walking_and_lunge_are_never_counted(session) -> None:
    payload, results = replay(session)
    assert payload["actual_squats"] == 0
    assert counted(results) == []
    assert results  # 후보는 있었고 모두 조건에서 걸러졌다


def test_walking_candidates_are_rejected_for_being_short() -> None:
    _, results = replay("8a")
    assert all(REASON_TOO_SHORT in r.reasons for r in results)


def test_the_lunge_is_rejected_because_the_feet_start_apart() -> None:
    _, results = replay("8c")
    assert all(REASON_FEET_APART in r.reasons for r in results)
    assert all(r.ankle_gap_norm > 0.5 for r in results)


def test_the_walk_away_after_the_continuous_set_is_rejected_only_by_the_hip_shift_condition() -> None:
    # c10(본인, 실제 10회)의 세트 후 자리를 뜨는 동작(80.1초)은 기하 조건을 통과하고 ML 라벨 비율(1.00)로만 막혀 있었다.
    # 이 데이터는 엉덩이 이동 상한(0.70)을 정하는 데 쓴 것이라 이 테스트는 검증이 아니라 회귀 확인이다(표본 1건).
    payload, results = replay("c10")
    assert len(counted(results)) == payload["actual_squats"] == 10
    walk_away = [r for r in results if REASON_HIP_SHIFT in r.reasons]
    assert len(walk_away) == 1 and walk_away[0].t_start == pytest.approx(80.1, abs=0.2) and walk_away[0].hip_shift_norm > 1.0
    _, without_hip_shift = replay("c10", max_hip_shift=None)
    assert len(counted(without_hip_shift)) == 11  # ML 조건을 뺀 대가: 이 조건이 없으면 11회로 센다


@pytest.mark.parametrize(
    ("session", "actual"),
    [("1", 10), ("2", 8), ("3", 8), ("4", 8), ("5", 8), ("c10", 10), ("c10_fast", 10), ("8a", 0), ("8c", 0), ("6", 0), ("7", 0)],
)
def test_the_default_conditions_keep_the_regression_counts_of_every_fixture(session, actual) -> None:
    # 재생 결과(2026-10-19 조합 재생)와 같은 횟수. 사선(6)·정면(7)은 측면이 아니라 0, 의자(8b)는 알려진 한계로 3.
    _, results = replay(session)
    assert len(counted(results)) == actual


def test_the_fixtures_carry_the_hip_x_column_for_the_hip_shift_condition() -> None:
    payload = json.loads((FIXTURES / "session_1.json").read_text(encoding="utf-8"))
    assert payload["columns"][-1] == "hip_x" and any(row[-1] is not None for row in payload["rows"])


def test_sitting_on_a_chair_is_counted_known_limitation() -> None:
    payload, results = replay("8b")
    assert payload["actual_squats"] is None
    assert len(counted(results)) == 3  # 동작 3번 모두 스쿼트로 센다


def test_reversed_facing_gives_the_same_signed_angles_as_the_normal_side_view() -> None:
    # 세션 9(반대 방향)는 사용자가 횟수를 확신하지 못해 횟수 검증에서 제외하고, 부호 있는 각도 검증에만 쓴다.
    payload, reps = replay("9")
    assert payload["actual_squats"] is None
    assert reps and all(r.facing == "right" for r in reps)  # 세션 1~5는 left
    assert all(r.torso_signed_at_bottom > 30.0 and r.shin_signed_at_bottom > 15.0 for r in reps)  # 앞으로 숙이면 양수
    _, normal = replay("1")
    assert all(r.facing == "left" for r in normal)
    assert min(r.torso_signed_at_bottom for r in reps) > 0.8 * min(r.torso_signed_at_bottom for r in counted(normal))


def test_fixtures_contain_no_face_landmarks_or_raw_landmark_arrays() -> None:
    for path in FIXTURES.glob("session_*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert set(payload) == {"session", "source", "note", "actual_squats", "columns", "rows"}
        assert "landmarks" not in path.read_text(encoding="utf-8")
        assert all(len(row) == len(payload["columns"]) for row in payload["rows"])


@pytest.mark.parametrize(
    ("session", "actual"),
    [("1", 10), ("2", 8), ("3", 8), ("4", 8), ("5", 8), ("8a", 0), ("8c", 0)],
    ids=["s1", "s2", "s3", "s4", "s5", "walk", "lunge"],
)
def test_geometry_conditions_alone_are_enough_without_the_ml_condition(session, actual) -> None:
    # 기하 조건이 1차 수단이다: 라벨(ML)을 쓰지 않아도 정상 반복은 모두 세고 걷기·런지는 세지 않는다.
    _, results = replay(session, **GEOMETRY_ONLY)
    assert len(counted(results)) == actual


@pytest.mark.parametrize("session", ["8a", "8c"])
def test_the_ml_condition_alone_also_rejects_walking_and_lunge(session) -> None:
    # ML 조건은 2차 방어선이다: 기하 조건이 모두 꺼져도 걷기·런지는 walk 라벨 비율로 걸러진다.
    _, results = replay(session, **ML_ONLY)
    assert counted(results) == []
    assert all(REASON_OTHER_EXERCISE in r.reasons for r in results)


def test_the_new_lock_policy_already_keeps_session_start_and_end_dips_out() -> None:
    # 세션 1 시작(자리 잡기)과 세션 2 끝(돌아섬)의 짧은 굴곡은 잠금이 없는 구간이라 후보로 잡히지도 않는다.
    # (이전 임시 정책의 로그 잠금값으로 재생하면 이 둘이 후보가 되어 길이 조건이 걸러 냈다.)
    for session in ("1", "2"):
        _, results = replay(session, **GEOMETRY_ONLY, min_seconds=0.0, min_hip_drop=-10.0)
        assert all(r.total_seconds >= 1.0 for r in results)


def test_duration_and_hip_drop_each_alone_reject_walking_and_the_end_dip_but_neither_missing_lets_them_in() -> None:
    # 세션 5 끝의 0.23초 굴곡과 걷기 후보(8a)는 길이 또는 엉덩이 하강 중 하나만 있어도 걸러진다(서로 겹쳐서 보호).
    for options in ({"min_seconds": 0.0}, {"min_hip_drop": -10.0}):
        assert len(counted(replay("5", **GEOMETRY_ONLY, **options)[1])) == 8
        assert counted(replay("8a", **GEOMETRY_ONLY, **options)[1]) == []
    # 둘 다 없으면(ML도 끈 상태) 그 굴곡들이 반복으로 샌다.
    both_off = {**GEOMETRY_ONLY, "min_seconds": 0.0, "min_hip_drop": -10.0}
    assert len(counted(replay("5", **both_off)[1])) == 9
    assert len(counted(replay("8a", **both_off)[1])) > 0


def test_the_ankle_gap_is_the_only_geometry_condition_that_rejects_the_lunge() -> None:
    _, without = replay("8c", **GEOMETRY_ONLY, max_ankle_gap=10.0)
    assert len(counted(without)) == 3  # 길이·엉덩이 하강량은 런지를 못 거른다
