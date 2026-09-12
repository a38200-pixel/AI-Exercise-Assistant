"""sleep이나 카메라 없이 WorkoutSession의 시간과 summary를 검증한다."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.exercise_counter import STRETCH_MODE, ExerciseCounter
from src.workout_session import WorkoutSession


KOREA_TIMEZONE = timezone(timedelta(hours=9))
SESSION_START_DATETIME = datetime(2026, 9, 12, 14, 30, 10, tzinfo=KOREA_TIMEZONE)
SESSION_END_DATETIME = datetime(2026, 9, 12, 14, 31, 50, tzinfo=KOREA_TIMEZONE)


def test_session_start_resets_exercise_records() -> None:
    counter = ExerciseCounter()
    counter.squat_count = 8
    counter.total_stretch_seconds = 12.5
    session = WorkoutSession()

    started = session.start(counter, 100.0, SESSION_START_DATETIME)

    assert started is True
    assert session.is_active is True
    assert counter.squat_count == 0
    assert counter.total_stretch_seconds == 0.0


def test_session_duration_uses_perf_counter_value() -> None:
    counter = ExerciseCounter()
    session = WorkoutSession()
    session.start(counter, 100.0, SESSION_START_DATETIME)
    assert session.get_elapsed_seconds(130.0) == 30.0
    assert session.update(130.0) == 30.0


def test_double_start_keeps_original_start() -> None:
    counter = ExerciseCounter()
    session = WorkoutSession()
    session.start(counter, 100.0, SESSION_START_DATETIME)

    second_start = session.start(counter, 110.0, SESSION_END_DATETIME)

    assert second_start is False
    assert session.session_start_perf == 100.0
    assert session.session_start_datetime == SESSION_START_DATETIME


def test_session_summary_contains_numeric_exercise_results() -> None:
    counter = ExerciseCounter()
    session = WorkoutSession()
    session.start(counter, 100.0, SESSION_START_DATETIME)
    counter.squat_count = 20
    counter.total_stretch_seconds = 45.0

    summary = session.end(counter, 200.0, SESSION_END_DATETIME)

    assert summary is not None
    assert summary["workout_seconds"] == 100.0
    assert summary["squat_count"] == 20
    assert summary["stretch_seconds"] == 45.0
    assert isinstance(summary["workout_seconds"], float)
    assert isinstance(summary["squat_count"], int)
    assert isinstance(summary["stretch_seconds"], float)
    assert summary["workout_date"] == "2026-09-12"
    assert summary["started_at"].endswith("+09:00")
    assert summary["ended_at"].endswith("+09:00")


def test_end_without_start_returns_none() -> None:
    counter = ExerciseCounter()
    session = WorkoutSession()
    assert session.end(counter, 100.0, SESSION_END_DATETIME) is None
    assert session.last_summary is None


def test_session_end_finishes_active_stretch() -> None:
    counter = ExerciseCounter()
    counter.set_mode(STRETCH_MODE, 100.0)
    session = WorkoutSession()
    session.start(counter, 100.0, SESSION_START_DATETIME)
    counter.update("stretch", 120.0)

    summary = session.end(counter, 130.0, SESSION_END_DATETIME)

    assert summary is not None
    assert summary["stretch_seconds"] == 10.0
    assert counter.stretch_start_time is None


def test_new_session_does_not_inherit_exercise_records() -> None:
    counter = ExerciseCounter()
    session = WorkoutSession()
    session.start(counter, 100.0, SESSION_START_DATETIME)
    counter.squat_count = 20
    counter.total_stretch_seconds = 60.0
    session.end(counter, 200.0, SESSION_END_DATETIME)

    next_start_datetime = datetime(2026, 9, 12, 15, 0, 0, tzinfo=KOREA_TIMEZONE)
    session.start(counter, 300.0, next_start_datetime)

    assert counter.squat_count == 0
    assert counter.total_stretch_seconds == 0.0


def test_workout_date_uses_start_date_across_midnight() -> None:
    counter = ExerciseCounter()
    session = WorkoutSession()
    start_datetime = datetime(2026, 9, 12, 23, 50, 0, tzinfo=KOREA_TIMEZONE)
    end_datetime = datetime(2026, 9, 13, 0, 10, 0, tzinfo=KOREA_TIMEZONE)
    session.start(counter, 100.0, start_datetime)

    summary = session.end(counter, 1300.0, end_datetime)

    assert summary is not None
    assert summary["workout_date"] == "2026-09-12"


def main() -> None:
    tests = (
        test_session_start_resets_exercise_records,
        test_session_duration_uses_perf_counter_value,
        test_double_start_keeps_original_start,
        test_session_summary_contains_numeric_exercise_results,
        test_end_without_start_returns_none,
        test_session_end_finishes_active_stretch,
        test_new_session_does_not_inherit_exercise_records,
        test_workout_date_uses_start_date_across_midnight,
    )

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\nWorkout session tests passed: {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()

