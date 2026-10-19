"""연속 세트 기준선(2026-10-19 실측 2개)과 저FPS 재생: 기본 설정에서 10/10을 세고, 프레임을 솎아내도(6 FPS까지) 유지되며,
알려진 약점(내려가기 직전 서 있는 프레임을 덮는 '사람 없음')을 현재 동작 그대로 고정한다."""

import json
from pathlib import Path

import pytest

from scripts.analysis import replay_flags as rf
from scripts.analysis.continuous_set_analysis import baseline_reps, inject_dropout

FIXTURES = Path(__file__).parent / "fixtures" / "rep_sessions"
CONTINUOUS = ["c10", "c10_fast"]
PRESETS = ["off", "baseline", "return155", "light", "raw", "grace0.6", "all"]


@pytest.mark.parametrize("session", CONTINUOUS)
def test_the_continuous_set_baselines_are_counted_exactly_by_default(session) -> None:
    payload = rf.load_fixture(session)
    assert payload["actual_squats"] == 10
    result = rf.replay(payload, rf.PRESETS["off"])
    assert result.counted == 10 and result.rejected == {} and result.merge_suspects == 0


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("session", CONTINUOUS)
def test_the_candidate_flags_keep_the_continuous_baselines_at_ten(session, preset) -> None:
    assert rf.replay(rf.load_fixture(session), rf.PRESETS[preset]).counted == 10


@pytest.mark.parametrize("session", CONTINUOUS)
def test_the_knee_returns_close_to_straight_between_the_reps_of_the_baselines(session) -> None:
    payload = rf.load_fixture(session)
    base = baseline_reps(payload)
    frames = payload["frames"]
    for (_, end), (start, _) in zip(base, base[1:]):
        peak = max(f["knee_smoothed"] for f in frames if end <= f["t"] <= start and f["knee_smoothed"] is not None)
        assert peak > 170.0  # 이 기준선은 반복 사이에 완전히 선다(봉우리가 160도에 닿는지는 문제가 아니었다)


def test_the_fixtures_carry_no_face_or_landmark_arrays() -> None:
    for session in CONTINUOUS:
        text = (FIXTURES / f"session_{session}.json").read_text(encoding="utf-8")
        payload = json.loads(text)
        assert set(payload) == {"session", "source", "note", "actual_squats", "columns", "rows"}
        assert "landmarks" not in text and "knee_raw" in payload["columns"]


# ---------------------------------------------------------------- 프레임 솎아내기


def test_decimation_keeps_original_timestamps_and_approximates_the_target_rate() -> None:
    frames = rf.load_fixture("c10")["frames"]
    original = {f["t"] for f in frames}
    duration = frames[-1]["t"] - frames[0]["t"]
    for fps in (12, 10, 8, 6, 5):
        kept = rf.decimate(frames, fps)
        assert {f["t"] for f in kept} <= original  # 새 시각을 만들지 않는다
        assert [f["t"] for f in kept] == sorted(f["t"] for f in kept)
        rate = (len(kept) - 1) / duration
        assert fps * 0.85 <= rate <= fps * 1.05
        assert kept == rf.decimate(frames, fps)  # 결정적이다


def test_decimating_to_the_native_rate_or_above_keeps_nearly_everything() -> None:
    frames = rf.load_fixture("c10")["frames"]
    assert len(rf.decimate(frames, 100)) == len(frames)


def test_the_low_fps_replay_smooths_only_the_kept_frames() -> None:
    payload = rf.load_fixture("c10")
    full = rf.replay(payload, rf.PRESETS["off"])
    resmoothed = rf.replay(payload, rf.PRESETS["off"], fps=100)  # 솎아내지 않고 원본 무릎각을 다시 평활해도 같은 결과
    assert resmoothed.counted == full.counted == 10 and resmoothed.frames == full.frames
    assert rf.replay(payload, rf.PRESETS["off"], fps=6).frames < full.frames / 2


@pytest.mark.parametrize("preset", ["off", "light", "return155", "all"])
@pytest.mark.parametrize("fps", [12, 10, 8, 6])
@pytest.mark.parametrize("session", CONTINUOUS)
def test_the_continuous_baselines_survive_down_to_six_fps(session, fps, preset) -> None:
    assert rf.replay(rf.load_fixture(session), rf.PRESETS[preset], fps=fps).counted == 10


# ---------------------------------------------------------------- 알려진 약점(현재 동작을 고정, 고칠 때 의도적으로 바꾼다)


@pytest.mark.parametrize("session", CONTINUOUS)
def test_known_limitation_a_dropout_covering_the_last_standing_frame_loses_the_rep(session) -> None:
    """서 있다가 내려가기 시작하는 순간 사람 없음 프레임이 마지막 서 있는 프레임(무릎각 160도 이상)을 덮으면, 사람이 다시 보일 때
    이미 160도 아래라 STANDING으로 돌아가지 못해 그 반복이 시작되지 않는다. 대응안을 구현하면 이 테스트를 의도적으로 바꾼다."""
    payload = rf.load_fixture(session)
    base = baseline_reps(payload)
    rest = len(base) - 1

    def counted_after_first(offset, length):
        result = rf.replay(inject_dropout(payload, base, length, offset), rf.PRESETS["off"])
        return sum(1 for r in result.results if r.counted and any(r.t_start < e and r.t_end > s for s, e in base[1:]))

    assert counted_after_first(-0.9, 0.12) == rest  # 서 있는 동안의 짧은 놓침은 문제가 없다
    assert counted_after_first(-0.3, 0.3) == rest  # 놓친 뒤에도 160도 이상 프레임이 남으면 STANDING으로 복귀한다
    assert counted_after_first(0.0, 0.3) == 0  # 마지막 서 있는 프레임을 덮으면 그 반복을 못 센다
