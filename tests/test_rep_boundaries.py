"""반복 경계: 휴지 없는 연속 세트에서 기본 동작(알려진 약점 포함), 제거한 기본 꺼짐 플래그 4개가 실제로 없어졌는지,
fixture 재생 스크립트가 일반 시뮬레이션과 같은 결과를 내는지 검증한다.

(2026-10-20에 세트 단위 서 있는 기준 높이, 복귀 각도, 반복 경계 신호(light/raw), 잠금 해제 유예를 제거했다. 그 플래그들을 켜서 연속 세트 누락을
고치는지 보던 테스트는 함께 지웠다. 제거 근거는 docs/versions/v0.2.0/DEVLOG.md.)"""

import math

import pytest

import config.settings as settings
from src.geometry_tracker import BodyLockPolicy, GeometryTracker
from src.rep_tracker import RepFrame, RepMeasures, RepTracker
from test_rep_tracker import BASE_HIP_Y, FPS, LEG_LENGTH, counted, run, simulate

from scripts.analysis import replay_flags


# ---------------------------------------------------------------- 합성 연속 세트


def continuous_set(n, *, top, bottom=85.0, period=2.0, lead=4.0, tail=2.0, top_hip_drop=0.0, bottom_hip_drop=0.30):
    """휴지 없는 연속 스쿼트 n회. 처음 lead초는 완전히 선 채 서 있다(knee 175, 엉덩이 기준 높이).

    top: 반복 사이 무릎각 봉우리, top_hip_drop: 봉우리에서 엉덩이가 기준 높이보다 낮은 정도(다리 길이 비, 완전히 못 서는 세트).
    """
    frames = []

    def add(t, knee, drop):
        frame = RepFrame(
            t, True, knee, True, "left", "right", 45.0, 28.0,
            RepMeasures(hip_y=BASE_HIP_Y + drop * LEG_LENGTH, heel_y=318.0, leg_length=LEG_LENGTH, ankle_gap=3.0),
        )
        frames.append((frame, "stand" if knee >= 160 else "squat"))

    for index in range(int(lead * FPS)):
        add(index / FPS, 175.0, 0.0)
    for index in range(int(n * period * FPS) + 1):
        s = index / FPS
        phase = (math.cos(2.0 * math.pi * s / period) + 1.0) / 2.0  # 1 = 봉우리, 0 = 바닥
        add(lead + s, bottom + (top - bottom) * phase, bottom_hip_drop + (top_hip_drop - bottom_hip_drop) * phase)
    last = lead + n * period
    for index in range(1, int(tail * FPS) + 1):
        add(last + index / FPS, 175.0, 0.0)
    return frames


def count(frames, **options):
    return len(counted(run(RepTracker(**options), frames)))


# ---------------------------------------------------------------- 기본 동작


def test_a_set_whose_knee_reaches_the_standing_angle_between_the_reps_is_counted_rep_by_rep() -> None:
    assert count(continuous_set(7, top=172.0)) == 7  # 실측 연속 세트(봉우리 172~180도)가 이 경우다


def test_a_set_whose_knee_never_reaches_the_standing_angle_merges_reps_by_default() -> None:
    # 알려진 한계: 봉우리가 160도에 못 미치는 세트는 한 반복으로 합쳐진다. 이를 풀어 주던 후보 플래그(복귀 각도 155도 등)는 제거했다.
    # 실측 연속 세트 5개(본인 c10, c10_fast, try2, try3과 P01, P02)는 모두 봉우리가 160도 위라 이 약점에 걸리지 않았다.
    assert count(continuous_set(7, top=158.0)) == 1


# ---------------------------------------------------------------- 제거한 플래그가 정말 없다


def test_the_removed_flag_constants_are_gone_from_the_settings() -> None:
    for name in (
        "REP_SET_BASELINE_ENABLED", "REP_SET_BASELINE_WINDOW_SECONDS", "REP_SET_BASELINE_MIN_SAMPLES", "REP_SET_BASELINE_HIP_PERCENTILE",
        "REP_RETURN_KNEE_ANGLE", "REP_BOUNDARY_SIGNAL", "REP_BOUNDARY_LIGHT_MIN_CUTOFF", "BODY_LOCK_RELEASE_GRACE_SECONDS",
    ):
        assert not hasattr(settings, name), name


@pytest.mark.parametrize("option", ["return_angle", "set_baseline", "set_baseline_window_seconds", "set_baseline_min_samples"])
def test_rep_tracker_no_longer_accepts_the_removed_options(option) -> None:
    with pytest.raises(TypeError):
        RepTracker(**{option: 1})


@pytest.mark.parametrize("option", ["boundary_signal", "boundary_light_min_cutoff", "release_grace_seconds"])
def test_geometry_tracker_no_longer_accepts_the_removed_options(option) -> None:
    with pytest.raises(TypeError):
        GeometryTracker(**{option: 1})


def test_body_lock_policy_no_longer_accepts_a_release_grace() -> None:
    with pytest.raises(TypeError):
        BodyLockPolicy(release_grace_seconds=0.6)


def test_the_rep_frame_carries_no_boundary_signal() -> None:
    assert not hasattr(RepFrame(1.0, True, 150.0), "boundary_knee")
    with pytest.raises(TypeError):
        RepFrame(1.0, True, 150.0, True, knee_boundary=158.0)


# ---------------------------------------------------------------- 재생 스크립트


def test_the_replay_script_matches_the_regular_fixture_simulation() -> None:
    for session in ("1", "2", "3", "4", "5", "8b"):
        _, results, _, _ = simulate(session)
        scripted = replay_flags.replay(replay_flags.load_fixture(session))
        assert scripted.counted == len(counted(results))


def test_fixtures_carry_the_raw_knee_for_the_low_fps_resmoothing() -> None:
    payload = replay_flags.load_fixture("2")
    assert "knee_raw" in payload["columns"]
    assert any(frame["knee_raw"] is not None for frame in payload["frames"])


def test_the_replay_table_prints_one_row_per_session() -> None:
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    done = subprocess.run(
        [sys.executable, "-m", "scripts.analysis.replay_flags", "--sessions", "1", "8a", "--markdown"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    assert "| 1 | 10/10 |" in done.stdout and "| 8a | 0/0 |" in done.stdout
