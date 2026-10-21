"""키 입력 이벤트(event kind "key"): 카운트·세션에 영향을 주는 키만, 누르기 전 모드와 화면 카운트와 함께 남고, 형식 버전은 2 그대로다."""

import json
from pathlib import Path

from src.exercise_counter import SQUAT_MODE, STRETCH_MODE, ExerciseCounter
from src.geometry_tracker import GeometryTracker
from src.main import handle_keyboard_input
from src.sequence_logger import FORMAT_VERSION, SequenceLogger, SequenceRecorder, session_metadata
from src.workout_session import WorkoutSession


class FakeUploader:
    pending_summary = None

    def submit(self, summary):
        return True

    def retry(self):
        return False


def read_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def press(char, counter, session, calls, uploader=None, now=10.0):
    return handle_keyboard_input(
        ord(char) if isinstance(char, str) else char,
        counter, session, uploader or FakeUploader(), now,
        key_logger=lambda key, t, **details: calls.append((key, t, details)),
    )


def make(tmp_path):
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    return counter, WorkoutSession(log_dir=tmp_path)


def test_reset_is_reported_with_the_count_before_the_reset(tmp_path) -> None:
    counter, session = make(tmp_path)
    counter.squat_count = 4
    calls = []
    press("r", counter, session, calls, now=12.5)
    assert counter.squat_count == 0  # 동작은 그대로다
    assert calls == [("reset", 12.5, {"mode": SQUAT_MODE, "squat_count": 4})]


def test_mode_keys_report_the_target_mode_and_the_previous_mode(tmp_path) -> None:
    counter, session = make(tmp_path)
    calls = []
    press("2", counter, session, calls)
    assert counter.exercise_mode == STRETCH_MODE
    assert calls[0][0] == "mode" and calls[0][2]["to"] == STRETCH_MODE and calls[0][2]["mode"] == SQUAT_MODE


def test_session_start_is_reported_because_it_clears_the_screen_count(tmp_path) -> None:
    counter, session = make(tmp_path)
    counter.squat_count = 3
    calls = []
    press("s", counter, session, calls)
    assert session.is_active and counter.squat_count == 0
    assert calls == [("session_start", 10.0, {"mode": SQUAT_MODE, "squat_count": 3, "applied": True})]
    press("s", counter, session, calls)  # 이미 진행 중이면 시작되지 않는다
    assert calls[1][2]["applied"] is False


def test_session_start_blocked_by_a_pending_upload_is_reported_as_not_applied(tmp_path) -> None:
    counter, session = make(tmp_path)
    uploader = FakeUploader()
    uploader.pending_summary = {"squat_count": 1}
    calls = []
    press("s", counter, session, calls, uploader)
    assert not session.is_active and calls[0][2]["applied"] is False


def test_session_end_and_quit_are_reported(tmp_path) -> None:
    counter, session = make(tmp_path)
    session.start(counter, 0.0)
    calls = []
    press("e", counter, session, calls)
    assert calls[0][0] == "session_end" and calls[0][2]["applied"] is True
    assert press("q", counter, session, calls) is True
    assert calls[1][0] == "quit" and calls[1][2]["session_active"] is False
    assert press(27, counter, session, calls) is True and calls[2][0] == "quit"


def test_keys_that_do_not_touch_the_count_or_the_session_are_not_reported(tmp_path) -> None:
    counter, session = make(tmp_path)
    calls = []
    press("p", counter, session, calls)  # 업로드 재시도
    press("x", counter, session, calls)  # 아무 기능 없는 키
    assert calls == []


def test_without_a_logger_the_keys_still_work(tmp_path) -> None:
    counter, session = make(tmp_path)
    counter.squat_count = 2
    assert handle_keyboard_input(ord("r"), counter, session, FakeUploader(), 1.0) is False
    assert counter.squat_count == 0


def test_the_event_line_is_written_as_a_key_event_and_the_format_version_stays_at_2(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata("normal", "side"), flush_interval=0.05)
    logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker())
    counter, session = make(tmp_path / "workouts")
    counter.squat_count = 5
    handle_keyboard_input(ord("r"), counter, session, FakeUploader(), logger._start_perf + 3.25, key_logger=recorder.log_key)
    recorder.close()
    records = read_records(logger.path)
    assert records[0]["format_version"] == FORMAT_VERSION == 2
    key_events = [r for r in records if r["type"] == "event" and r["kind"] == "key"]
    assert len(key_events) == 1
    assert key_events[0]["key"] == "reset" and key_events[0]["t"] == 3.25
    assert key_events[0]["mode"] == SQUAT_MODE and key_events[0]["squat_count"] == 5
    assert records[-1]["type"] == "end" and records[-1]["events_written"] == 1


def test_a_failing_logger_does_not_break_key_handling(tmp_path) -> None:
    class Broken:
        def log_event(self, event):
            raise RuntimeError("disk gone")

        def to_session_time(self, t):
            return t

    recorder = SequenceRecorder.__new__(SequenceRecorder)
    recorder.logger = Broken()
    assert recorder.log_key("reset", 1.0) is False
    counter, session = make(tmp_path)
    counter.squat_count = 1
    handle_keyboard_input(ord("r"), counter, session, FakeUploader(), 1.0, key_logger=recorder.log_key)
    assert counter.squat_count == 0
