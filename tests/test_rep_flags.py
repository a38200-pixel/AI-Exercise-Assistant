"""대응안 후보 플래그(기본 꺼짐): 꺼진 기본 동작이 바뀌지 않았는지, 켰을 때 연속 세트의 누락을 합성 시퀀스로 고치는지,
fixture 회귀가 유지되는지, 재생 스크립트가 같은 결과를 내는지 검증한다."""

import math

import pytest

import config.settings as settings
from src.geometry_tracker import BOUNDARY_SIGNALS, BodyLockPolicy, GeometryTracker
from src.rep_tracker import RepFrame, RepMeasures, RepTracker
from test_rep_tracker import BASE_HIP_Y, FPS, LEG_LENGTH, counted, run, simulate
from test_sequence_logger import front_standing, locked_tracker, squatting, standing

from scripts.analysis import replay_flags


# ---------------------------------------------------------------- 합성 연속 세트


def continuous_set(
    n,
    *,
    top,
    bottom=85.0,
    period=2.0,
    lead=4.0,
    tail=2.0,
    top_hip_drop=0.0,
    bottom_hip_drop=0.30,
    boundary_top=None,
):
    """휴지 없는 연속 스쿼트 n회. 처음 lead초는 완전히 선 채 서 있다(knee 175, 엉덩이 기준 높이).

    top: 반복 사이 무릎각 봉우리, top_hip_drop: 봉우리에서 엉덩이가 기준 높이보다 낮은 정도(다리 길이 비, 완전히 못 서는 세트),
    boundary_top: 주면 반복 경계용 신호(knee_boundary)의 봉우리 값(평활 전 원본이 더 높게 올라온다는 가정).
    """
    frames = []

    def add(t, knee, drop, boundary=None):
        frame = RepFrame(
            t, True, knee, True, "left", "right", 45.0, 28.0,
            RepMeasures(hip_y=BASE_HIP_Y + drop * LEG_LENGTH, heel_y=318.0, leg_length=LEG_LENGTH, ankle_gap=3.0),
            knee_boundary=boundary,
        )
        frames.append((frame, "stand" if knee >= 160 else "squat"))

    for index in range(int(lead * FPS)):
        add(index / FPS, 175.0, 0.0)
    for index in range(int(n * period * FPS) + 1):
        s = index / FPS
        phase = (math.cos(2.0 * math.pi * s / period) + 1.0) / 2.0  # 1 = 봉우리, 0 = 바닥
        knee = bottom + (top - bottom) * phase
        drop = bottom_hip_drop + (top_hip_drop - bottom_hip_drop) * phase
        boundary = None if boundary_top is None else bottom + (boundary_top - bottom) * phase
        add(lead + s, knee, drop, boundary)
    last = lead + n * period
    for index in range(1, int(tail * FPS) + 1):
        add(last + index / FPS, 175.0, 0.0)
    return frames


def count(frames, **options):
    return len(counted(run(RepTracker(**options), frames)))


# ---------------------------------------------------------------- 기본값은 꺼짐


def test_every_candidate_flag_is_off_by_default() -> None:
    assert settings.REP_SET_BASELINE_ENABLED is False
    assert settings.REP_RETURN_KNEE_ANGLE is None
    assert settings.REP_BOUNDARY_SIGNAL == "smoothed"
    assert settings.BODY_LOCK_RELEASE_GRACE_SECONDS == 0.0


def test_a_default_tracker_behaves_like_one_with_the_flags_spelled_out_as_off() -> None:
    frames = continuous_set(7, top=170.0, top_hip_drop=0.12)
    explicit = dict(return_angle=None, set_baseline=False)
    assert count(frames) == count(frames, **explicit) == 1  # 휴지 없는 세트에서 기본 동작은 첫 반복만 센다(알려진 문제)


# ---------------------------------------------------------------- 복귀 각도 조정(가설 1)


def test_a_set_whose_knee_never_reaches_the_standing_angle_merges_reps_by_default() -> None:
    frames = continuous_set(7, top=158.0)
    assert count(frames) == 1  # 봉우리가 160도에 못 미쳐 7회가 한 반복으로 합쳐진다
    assert count(frames, return_angle=155.0) == 7


def test_the_return_angle_flag_forces_the_set_baseline_with_it() -> None:
    # 봉우리에서 엉덩이가 0.12 낮은 세트. 복귀를 낮추면 기준 높이가 더 낮아져 하강량이 모자라므로 세트 기준 높이가 함께 켜져야 한다.
    frames = continuous_set(7, top=158.0, top_hip_drop=0.12)
    assert count(frames, return_angle=155.0) == 7


@pytest.mark.parametrize("value", [150.0, 140.0, 161.0])
def test_the_return_angle_must_lie_between_the_descent_and_standing_angles(value) -> None:
    with pytest.raises(ValueError):
        RepTracker(return_angle=value)


# ---------------------------------------------------------------- 세트 단위 기준 높이(가설 4)


def test_the_set_baseline_keeps_the_standing_height_when_the_set_never_stands_fully() -> None:
    frames = continuous_set(7, top=170.0, top_hip_drop=0.12)
    assert count(frames) == 1  # 기준이 봉우리의 낮은 엉덩이로 잡혀 하강량 0.18 < 0.20
    assert count(frames, set_baseline=True) == 7


def test_the_set_baseline_falls_back_to_the_last_second_without_enough_standing_frames() -> None:
    frames = continuous_set(7, top=170.0, top_hip_drop=0.12)
    assert count(frames, set_baseline=True, set_baseline_min_samples=10**6) == 1


def test_the_set_baseline_does_not_let_shallow_reps_through() -> None:
    frames = continuous_set(7, top=170.0, top_hip_drop=0.0, bottom_hip_drop=0.10)  # 하강 0.10 < 0.20
    assert count(frames, set_baseline=True) == 0


def test_the_set_baseline_is_dropped_when_the_lock_is_lost() -> None:
    tracker = RepTracker(set_baseline=True)
    run(tracker, continuous_set(2, top=170.0))
    assert tracker._set_samples
    unlocked = RepFrame(99.0, True, 175.0, False, None, None, None, None, None)
    tracker.update(unlocked, "stand")
    assert tracker._set_samples == []


# ---------------------------------------------------------------- 반복 경계 신호(가설 5)


def test_boundary_signal_falls_back_to_the_smoothed_knee_when_not_supplied() -> None:
    frame = RepFrame(1.0, True, 150.0, True)
    assert frame.boundary_knee == 150.0
    assert RepFrame(1.0, True, 150.0, True, knee_boundary=158.0).boundary_knee == 158.0
    assert RepFrame.missing(1.0).boundary_knee is None


def test_a_boundary_signal_that_reaches_the_standing_angle_separates_reps_the_smoothed_one_merges() -> None:
    smoothed_only = continuous_set(7, top=159.0)
    boundary = continuous_set(7, top=159.0, boundary_top=165.0)
    assert count(smoothed_only) == 1
    assert count(boundary) == 7


@pytest.mark.parametrize("mode", ["light", "raw"])
def test_the_geometry_tracker_builds_the_boundary_signal_for_each_mode(mode) -> None:
    default, other = GeometryTracker(), GeometryTracker(boundary_signal=mode)
    for tracker in (default, other):
        standing(tracker, 0.0)
    slow = squatting(default, 0.05)
    fast = squatting(other, 0.05)
    assert slow.knee_angle_boundary == slow.knee_angle_smoothed  # 기본은 평활값 그대로
    raw = fast.geometry.knee_angle
    assert fast.knee_angle_smoothed == pytest.approx(slow.knee_angle_smoothed)  # 평활값 자체는 바뀌지 않는다
    assert abs(fast.knee_angle_boundary - raw) < abs(fast.knee_angle_smoothed - raw)  # 경계 신호가 원본에 더 가깝다
    if mode == "raw":
        assert fast.knee_angle_boundary == pytest.approx(raw)


def test_unknown_boundary_signals_are_rejected() -> None:
    assert set(BOUNDARY_SIGNALS) == {"smoothed", "light", "raw"}
    with pytest.raises(ValueError):
        GeometryTracker(boundary_signal="median")


# ---------------------------------------------------------------- 잠금 해제 유예(가설 2)


def test_the_release_grace_postpones_the_release_by_that_many_seconds() -> None:
    plain, graced = locked_tracker(), locked_tracker(release_grace_seconds=0.6)
    for tracker in (plain, graced):
        front_standing(tracker, 1.0)
        front_standing(tracker, 1.3)
    assert front_standing(plain, 1.45).lock.event == "released_view"
    assert front_standing(graced, 1.45).lock.locked is True
    assert front_standing(graced, 1.95).lock.locked is True  # 0.95초 연속: 0.4 + 0.6 미만
    assert front_standing(graced, 2.05).lock.event == "released_view"


def test_a_short_non_side_blip_does_not_release_with_the_grace() -> None:
    policy = BodyLockPolicy(release_grace_seconds=0.6)
    policy.step(0.0, standing=True, side_now=True, lockable=True)
    assert policy.step(0.5, standing=True, side_now=True, lockable=True) == "acquire"
    assert policy.step(0.6, standing=True, side_now=False, lockable=True) is None
    assert policy.step(1.2, standing=True, side_now=False, lockable=True) is None  # 0.6초 비측면: 기본이면 이미 풀렸다
    assert policy.step(1.3, standing=True, side_now=True, lockable=True) == "refresh"


# ---------------------------------------------------------------- fixture 회귀와 재생 스크립트


FLAGGED = ["baseline", "return155", "light", "raw", "grace0.6", "all"]


@pytest.mark.parametrize("preset", FLAGGED)
@pytest.mark.parametrize("session", ["1", "2", "3", "4", "5"])
def test_side_squat_fixtures_keep_their_exact_counts_with_each_flag_on(session, preset) -> None:
    payload = replay_flags.load_fixture(session)
    result = replay_flags.replay(payload, replay_flags.PRESETS[preset])
    assert result.counted == payload["actual_squats"]


@pytest.mark.parametrize("preset", FLAGGED)
@pytest.mark.parametrize("session", ["6", "7", "8a"])
def test_non_squats_and_non_side_fixtures_still_count_nothing_with_each_flag_on(session, preset) -> None:
    result = replay_flags.replay(replay_flags.load_fixture(session), replay_flags.PRESETS[preset])
    assert result.counted == 0


@pytest.mark.parametrize("preset", ["light", "raw", "grace0.6"])
def test_the_lunge_stretch_is_still_not_counted_with_the_flags_that_keep_the_standing_baseline(preset) -> None:
    result = replay_flags.replay(replay_flags.load_fixture("8c"), replay_flags.PRESETS[preset])
    assert result.counted == 0  # 서 있을 때 양발 간격(0.55)이 그대로라 feet_apart로 걸러진다


@pytest.mark.parametrize("preset", ["baseline", "return155", "all"])
def test_known_gap_the_set_baseline_flags_let_the_lunge_stretch_through_now_that_the_ml_condition_is_gone(preset) -> None:
    # 알려진 한계(2026-10-19): 세트 단위 기준(baseline, return155, all)은 서 있을 때 양발 간격 기준을 0.03~0.05로 낮춰 feet_apart가 사라지고,
    # 이전에는 ML 라벨 비율(0.48~0.55)이 마지막 방어선이었다. ML 조건을 뺀 뒤 1차 스트레치 런지(8c) 3개가 세어진다(최저점 간격 0.13~0.35,
    # 엉덩이 이동 0.09~0.14라 새 기하 조건에도 안 걸린다). 이 플래그들은 기본 꺼짐이며 켜기 전에 이 점을 다시 확인해야 한다.
    result = replay_flags.replay(replay_flags.load_fixture("8c"), replay_flags.PRESETS[preset])
    assert result.counted == 3


def test_the_replay_script_with_flags_off_matches_the_regular_fixture_simulation() -> None:
    for session in ("1", "2", "3", "4", "5", "8b"):
        _, results, _, _ = simulate(session)
        scripted = replay_flags.replay(replay_flags.load_fixture(session), replay_flags.PRESETS["off"])
        assert scripted.counted == len(counted(results))


def test_fixtures_carry_the_raw_knee_for_the_boundary_signal_replay() -> None:
    payload = replay_flags.load_fixture("2")
    assert "knee_raw" in payload["columns"]
    assert any(frame["knee_raw"] is not None for frame in payload["frames"])


def test_the_replay_matrix_prints_one_column_per_preset() -> None:
    payloads = [replay_flags.load_fixture("1"), replay_flags.load_fixture("8a")]
    table = replay_flags.matrix(payloads, replay_flags.PRESETS, markdown=True)
    assert "| 세션(노트) | off | baseline | return155 | light | raw | grace0.6 | all |" in table
    assert "10/10" in table
