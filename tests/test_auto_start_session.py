"""Camera 없이 Launcher auto-start와 기존 manual session 호환성을 검증한다."""

from src.api_client import WorkoutUploader
from src.exercise_counter import SQUAT_MODE, ExerciseCounter
from src.main import (
    auto_start_session_when_ready,
    handle_keyboard_input,
    parse_arguments,
)
from src.workout_session import WorkoutSession


def test_manual_cli_keeps_session_ready() -> None:
    arguments = parse_arguments(["--exercise", "squat"])
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    session = WorkoutSession()

    completed = auto_start_session_when_ready(
        arguments.auto_start_session,
        False,
        counter,
        session,
        10.0,
    )
    assert completed is False
    assert session.is_active is False


def test_launcher_flag_starts_session_after_ready() -> None:
    arguments = parse_arguments(["--exercise", "squat", "--auto-start-session"])
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    session = WorkoutSession()

    completed = auto_start_session_when_ready(
        arguments.auto_start_session,
        False,
        counter,
        session,
        10.0,
    )
    assert completed is True
    assert session.is_active is True
    assert session.get_status(10.0)["status"] == "ACTIVE"
    assert session.get_status(10.0)["elapsed_seconds"] == 0.0


def test_s_key_does_not_restart_auto_started_session() -> None:
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    session = WorkoutSession()
    assert session.start(counter, 10.0) is True
    original_start = session.session_start_perf

    should_quit = handle_keyboard_input(
        ord("S"),
        counter,
        session,
        WorkoutUploader(None),
        20.0,
    )
    assert should_quit is False
    assert session.session_start_perf == original_start
    assert session.get_elapsed_seconds(20.0) == 10.0
