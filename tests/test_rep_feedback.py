"""Phase 3 화면 연결: RepResult의 자세 점수, 표시 규칙(점수 한 줄, 점수 범위 안내, 얕음 안내), 그리기, 로컬 기록, USE_REP_TRACKER=False."""

import json

import numpy as np
import pytest

import config.settings as settings
import src.main as main_module
from src.exercise_counter import SQUAT_MODE, STRETCH_MODE, ExerciseCounter
from src.main import compose_workout_ui, create_exercise_counter
from src.posture_score import STATUS_CAUTION, STATUS_CORRECT, STATUS_NORMAL
from src.rep_feedback import (
    INTRO_TEXT,
    KIND_INTRO,
    KIND_SCORE,
    KIND_SHALLOW,
    SHALLOW_TEXT,
    FeedbackLine,
    RepFeedback,
)
from src.rep_tracker import NOTICE_NOT_SIDE, RepTracker
from src.workout_session import WorkoutSession
from test_rep_tracker import counted, rep_curve, run


def results_of(**curve):
    return run(RepTracker(), rep_curve(**curve))


# ---------------------------------------------------------------- RepResult의 자세 점수


def test_a_counted_rep_carries_its_posture_score_and_a_rejected_one_does_not() -> None:
    good = counted(results_of())[0]
    assert good.posture is not None and good.posture.total_score == pytest.approx(100.0)
    assert good.posture.item_status == {"depth": STATUS_NORMAL, "torso_shin": STATUS_NORMAL}  # 몸통 45 - 정강이 28 = 17
    shallow_hip = run(RepTracker(), rep_curve(hip_drop=0.05))[0]
    assert not shallow_hip.counted and shallow_hip.posture is None


def test_the_judgement_follows_the_item_limits_just_below_and_above() -> None:
    at_limit = counted(results_of(bottom=80.0))[0].posture
    over_limit = counted(results_of(bottom=81.0))[0].posture
    assert at_limit.item_status["depth"] == STATUS_NORMAL and at_limit.total_score == pytest.approx(100.0)
    assert over_limit.item_status["depth"] == STATUS_CAUTION and over_limit.total_score < 100.0
    assert over_limit.worst_item == "depth"
    deep_correct = counted(results_of(bottom=96.0))[0].posture
    assert deep_correct.item_status["depth"] == STATUS_CORRECT and deep_correct.item_status["torso_shin"] == "recorded_only"


def test_the_rep_end_event_logs_the_posture_score_as_json() -> None:
    tracker = RepTracker()
    run(tracker, rep_curve(bottom=90.0))
    event = [e for e in tracker.pop_events() if e["kind"] == "rep_end"][0]
    assert event["counted"] and event["posture"]["worst_item"] == "depth"
    assert event["posture"]["item_status"]["depth"] == STATUS_CAUTION
    json.dumps(event, allow_nan=False)
    rejected = RepTracker()
    run(rejected, rep_curve(hip_drop=0.05))
    assert [e for e in rejected.pop_events() if e["kind"] == "rep_end"][0]["posture"] is None


# ---------------------------------------------------------------- 표시 규칙 (RepFeedback)


def status_for(result, guidance="ready", mode=SQUAT_MODE):
    return {"mode": mode, "rep_guidance": guidance, "last_rep": result}


def test_a_counted_rep_shows_the_score_with_the_worst_item_feedback_and_the_small_tag() -> None:
    feedback = RepFeedback()
    rep = counted(results_of(bottom=90.0))[0]
    line = feedback.update(status_for(rep), 10.0)
    assert line.kind == KIND_SCORE
    assert line.korean == f"{round(rep.posture.total_score)}점 · 더 깊게 앉아보세요"
    assert line.tag_korean == "깊이·상체" and "DEPTH" in line.tag_english
    assert "SQUAT DEEPER" in line.english


def test_a_perfect_rep_shows_only_the_score() -> None:
    line = RepFeedback().update(status_for(counted(results_of())[0]), 0.0)
    assert line.korean == "100점" and line.english == "100 PTS"


def test_the_score_line_disappears_after_the_display_time_and_does_not_come_back() -> None:
    feedback = RepFeedback()
    rep = counted(results_of())[0]
    assert feedback.update(status_for(rep), 0.0) is not None
    assert feedback.update(status_for(rep), settings.REP_SCORE_DISPLAY_SECONDS - 0.1) is not None
    assert feedback.update(status_for(rep), settings.REP_SCORE_DISPLAY_SECONDS + 0.1) is None
    assert feedback.update(status_for(rep), settings.REP_SCORE_DISPLAY_SECONDS + 5.0) is None  # 같은 결과로 다시 뜨지 않는다


def test_a_new_rep_replaces_the_line_and_restarts_the_timer() -> None:
    feedback = RepFeedback()
    shallow, good = counted(results_of(bottom=90.0))[0], counted(results_of())[0]
    feedback.update(status_for(shallow), 0.0)
    line = feedback.update(status_for(good), 2.0)
    assert line.korean == "100점"
    assert feedback.update(status_for(good), 2.0 + settings.REP_SCORE_DISPLAY_SECONDS - 0.1) is not None


def test_the_hip_drop_rejection_shows_the_deeper_hint_and_only_then() -> None:
    feedback = RepFeedback()
    only_shallow = run(RepTracker(), rep_curve(hip_drop=0.05))[0]
    assert only_shallow.reasons == ("shallow_hip_drop",)
    line = feedback.update(status_for(only_shallow), 0.0)
    assert (line.kind, line.korean) == (KIND_SHALLOW, SHALLOW_TEXT[0]) and line.korean == "더 깊게 앉아야 1회로 셉니다"
    assert feedback.update(status_for(only_shallow), settings.REP_SHALLOW_HINT_DISPLAY_SECONDS + 0.1) is None


@pytest.mark.parametrize(
    "curve",
    [
        {"hip_drop": 0.05, "down": 0.3, "hold": 0.0, "up": 0.3},  # 너무 짧음 + 얕음(걷다가 굽힌 것처럼): 사유가 둘 이상이면 안내하지 않는다
        {"ankle_gap_norm": 0.6},  # 양발이 벌어짐
        {"bottom_ankle_gap_norm": 1.1},  # 최저점에서 양발이 벌어짐(런지 걸음)
        {"hip_shift_norm": 1.2},  # 엉덩이가 가로로 크게 이동(자리를 뜨는 동작)
    ],
    ids=["short-and-shallow", "feet-apart", "feet-apart-bottom", "hip-shift"],
)
def test_other_rejection_reasons_show_nothing(curve) -> None:
    rejected = run(RepTracker(), rep_curve(**curve))[0]
    assert not rejected.counted and rejected.reasons != ("shallow_hip_drop",)
    assert RepFeedback().update(status_for(rejected), 0.0) is None


def test_the_score_range_notice_appears_once_when_standing_with_the_lock_and_again_only_after_a_reset() -> None:
    feedback = RepFeedback()
    assert feedback.update(status_for(None, guidance="need_side_standing"), 0.0) is None  # 아직 잠금이 안 걸렸다
    line = feedback.update(status_for(None, guidance="ready"), 1.0)
    assert (line.kind, line.korean) == (KIND_INTRO, INTRO_TEXT[0]) and "자세 점수" in line.korean and "깊이와 상체 정렬만" in line.korean
    assert feedback.update(status_for(None), 1.0 + settings.POSTURE_SCORE_INTRO_DISPLAY_SECONDS + 0.1) is None
    assert feedback.update(status_for(None), 30.0) is None  # 세션당 한 번
    feedback.reset()
    assert feedback.update(status_for(None), 31.0).kind == KIND_INTRO  # 새 세션에서는 다시 한 번


def test_nothing_is_shown_outside_squat_mode_or_without_a_rep_tracker() -> None:
    feedback = RepFeedback()
    rep = counted(results_of())[0]
    assert feedback.update(status_for(rep, mode=STRETCH_MODE), 0.0) is None
    assert feedback.update({"mode": SQUAT_MODE, "rep_guidance": None, "last_rep": None}, 0.0) is None


def test_display_times_are_settings_constants() -> None:
    assert settings.REP_SCORE_DISPLAY_SECONDS > 0 and settings.REP_SHALLOW_HINT_DISPLAY_SECONDS > 0
    assert settings.POSTURE_SCORE_INTRO_DISPLAY_SECONDS > 0


def test_with_use_rep_tracker_off_no_score_or_hint_is_ever_shown(monkeypatch) -> None:
    monkeypatch.setattr(settings, "USE_REP_TRACKER", False)
    counter = create_exercise_counter()
    assert not counter.uses_rep_tracker
    counter.set_mode(SQUAT_MODE, 0.0)
    feedback = RepFeedback()
    shown = []
    for label in ("stand", "squat", "stand", "squat", "stand"):  # v0.1.x 방식: 라벨 전이로 센다
        counter.update(label, 1.0)
        shown.append(feedback.update(counter.get_status(1.0), 1.0))
    assert counter.squat_count == 2  # 카운트는 그대로 되지만
    assert all(line is None for line in shown)  # 점수·안내는 나오지 않는다
    assert counter.get_status(0.0)["last_rep"] is None and counter.rep_history == []


# ---------------------------------------------------------------- 그리기


def hud(feedback=None, notice=None):
    frame = np.full((480, 640, 3), 90, dtype=np.uint8)
    status = {"mode": "squat", "squat_count": 3}
    session = {"status": "ACTIVE", "elapsed_seconds": 65}
    return compose_workout_ui(frame, status, session, "READY", "STAND", 0.9, True, notice, feedback)


@pytest.fixture
def fresh_caches():
    caches = (main_module._korean_font, main_module._feedback_text_layer, main_module._notice_text_layer)  # 테스트가 바꿔치기해도 원래 캐시를 비운다
    for cached in caches:
        cached.cache_clear()
    yield
    for cached in caches:
        cached.cache_clear()


SCORE_LINE = FeedbackLine(KIND_SCORE, "78점 · 더 깊게 앉아보세요", "78 PTS - SQUAT DEEPER", "깊이·상체", "DEPTH+TORSO")


def changed_region(a, b):
    rows, cols = np.where(np.any(a != b, axis=2))
    return rows.min(), rows.max(), cols.min(), cols.max()


def test_the_feedback_line_is_drawn_only_in_the_band_at_the_bottom_of_the_video(fresh_caches) -> None:
    top, bottom, left, right = changed_region(hud(), hud(SCORE_LINE))
    assert top >= 64 + 480 - 70 and bottom <= 64 + 480 and left >= 12 and right <= 640 - 12


def test_the_small_gray_tag_is_drawn_on_the_right_of_the_band(fresh_caches) -> None:
    with_tag, without_tag = hud(SCORE_LINE), hud(FeedbackLine(KIND_SCORE, SCORE_LINE.korean, SCORE_LINE.english))
    rows, cols = np.where(np.any(with_tag != without_tag, axis=2))
    assert len(cols) > 0 and cols.min() > 640 * 0.7  # 가운데 정렬된 점수 문구보다 오른쪽 가장자리 쪽


def test_a_lock_notice_takes_the_place_of_the_feedback_line(fresh_caches) -> None:
    assert np.array_equal(hud(SCORE_LINE, NOTICE_NOT_SIDE), hud(None, NOTICE_NOT_SIDE))


def test_the_feedback_text_is_rendered_once_and_then_only_composited(fresh_caches) -> None:
    for _ in range(4):
        hud(SCORE_LINE)
    info = main_module._feedback_text_layer.cache_info()
    assert info.misses == 1 and info.hits == 3
    hud(FeedbackLine(KIND_SHALLOW, *SHALLOW_TEXT))
    assert main_module._feedback_text_layer.cache_info().misses == 2


def test_the_korean_font_sizes_do_not_evict_each_other(fresh_caches) -> None:
    hud(SCORE_LINE)
    hud(SCORE_LINE)
    info = main_module._korean_font.cache_info()
    assert info.currsize >= 2 and info.hits >= 1  # 22와 16 두 크기를 함께 캐시한다


def test_without_a_korean_font_the_feedback_falls_back_to_english(monkeypatch, fresh_caches) -> None:
    korean = hud(SCORE_LINE)
    monkeypatch.setattr(main_module, "_korean_font", lambda *args, **kwargs: None)
    english = hud(SCORE_LINE)
    assert not np.array_equal(english, hud()) and not np.array_equal(english, korean)


def test_the_three_kinds_use_different_colors() -> None:
    assert len(set(main_module.FEEDBACK_COLORS.values())) == 3


# ---------------------------------------------------------------- 로컬 기록

UPLOAD_KEYS = {"workout_date", "started_at", "ended_at", "workout_seconds", "squat_count", "stretch_seconds"}


def session_with_reps():
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    session = WorkoutSession()
    assert session.start(counter, 0.0)
    clock = 0.0
    for curve in ({}, {"hip_drop": 0.05}, {"bottom": 92.0}):  # 확정, 얕음 탈락, 확정(주의)
        for frame, label in rep_curve(start=clock, **curve):
            counter.update(label, frame.timestamp, frame)
        clock += 6.0
    summary = session.end(counter, clock)
    return session, counter, summary


def test_the_session_keeps_per_rep_results_in_a_local_record() -> None:
    session, counter, summary = session_with_reps()
    record = session.last_local_record
    assert [r["counted"] for r in record["reps"]] == [True, False, True]
    assert [r["rep_number"] for r in record["reps"]] == [1, None, 2]
    first_rep, rejected, third = record["reps"]
    assert first_rep["posture"]["total_score"] == pytest.approx(100.0) and first_rep["posture"]["worst_item"] is None
    assert first_rep["posture"]["item_status"] == {"depth": "normal", "torso_shin": "normal"}
    assert rejected["posture"] is None and rejected["reasons"] == ["shallow_hip_drop"]
    assert third["posture"]["worst_item"] == "depth" and third["posture"]["item_status"]["depth"] == "caution"
    assert third["posture"]["item_scores"]["depth"] < 100.0 and record["squat_count"] == summary["squat_count"] == 2
    assert first_rep["seconds_from_start"] == pytest.approx(counter.rep_history[0].t_start, abs=0.05)
    json.dumps(record, allow_nan=False)  # 로컬에 저장할 수 있는 형태(NaN 없음)


def test_the_upload_summary_is_unchanged_by_the_local_record() -> None:
    session, _, summary = session_with_reps()
    assert set(summary) == UPLOAD_KEYS == set(session.last_summary)
    assert "reps" not in summary and "posture" not in json.dumps(summary)


def test_a_new_session_clears_the_previous_local_record_and_history() -> None:
    session, counter, _ = session_with_reps()
    assert session.last_local_record is not None
    assert session.start(counter, 100.0)
    assert session.last_local_record is None and counter.rep_history == []


def test_stopping_without_reps_gives_an_empty_record() -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    session = WorkoutSession()
    session.start(counter, 0.0)
    session.end(counter, 5.0)
    assert session.last_local_record["reps"] == [] and session.last_local_record["squat_count"] == 0


def test_the_v01x_counter_leaves_an_empty_rep_record() -> None:
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    session = WorkoutSession()
    session.start(counter, 0.0)
    for label in ("stand", "squat", "stand"):
        counter.update(label, 1.0)
    session.end(counter, 5.0)
    assert counter.squat_count == 1 and session.last_local_record["reps"] == []
