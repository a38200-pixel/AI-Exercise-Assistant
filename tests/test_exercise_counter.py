"""카메라 없이 Stable Pose sequence로 운동 상태 머신을 검증한다."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.exercise_counter import (
    SQUAT_MODE,
    STRETCH_MODE,
    ExerciseCounter,
)


def send_sequence(
    counter: ExerciseCounter,
    poses: tuple[str, ...],
    start_time: float = 0.0,
) -> None:
    for frame_offset, stable_pose in enumerate(poses):
        current_time = start_time + frame_offset
        counter.update(stable_pose, current_time)


def test_squat_complete_sequence() -> None:
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    send_sequence(counter, ("stand", "squat", "stand"))
    assert counter.squat_count == 1


def test_squat_held_down_counts_once() -> None:
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    send_sequence(counter, ("stand", "squat", "squat", "squat", "stand"))
    assert counter.squat_count == 1


def test_squat_cannot_start_without_stand() -> None:
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    send_sequence(counter, ("squat", "stand"))
    assert counter.squat_count == 0


def test_two_squats() -> None:
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    send_sequence(counter, ("stand", "squat", "stand", "squat", "stand"))
    assert counter.squat_count == 2


def test_stretch_accumulates_real_time() -> None:
    counter = ExerciseCounter()
    counter.set_mode(STRETCH_MODE, 0.0)
    counter.update("stretch", 0.0)
    counter.update("stretch", 5.0)
    counter.update("stand", 10.0)
    assert abs(counter.total_stretch_seconds - 10.0) < 1e-9

    counter.update("stretch", 20.0)
    counter.update("stand", 25.0)
    assert abs(counter.total_stretch_seconds - 15.0) < 1e-9


def test_mode_change_finishes_active_stretch() -> None:
    counter = ExerciseCounter()
    counter.set_mode(STRETCH_MODE, 0.0)
    counter.update("stretch", 2.0)
    counter.set_mode(SQUAT_MODE, 7.0)
    assert abs(counter.total_stretch_seconds - 5.0) < 1e-9


def test_reset_only_changes_current_exercise() -> None:
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    send_sequence(counter, ("stand", "squat", "stand"))
    counter.set_mode(STRETCH_MODE, 3.0)
    counter.update("stretch", 4.0)
    counter.update("stand", 9.0)
    counter.reset_current_exercise(10.0)
    assert counter.total_stretch_seconds == 0.0
    assert counter.squat_count == 1


def main() -> None:
    tests = (
        test_squat_complete_sequence,
        test_squat_held_down_counts_once,
        test_squat_cannot_start_without_stand,
        test_two_squats,
        test_stretch_accumulates_real_time,
        test_mode_change_finishes_active_stretch,
        test_reset_only_changes_current_exercise,
    )

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\nExercise counter tests passed: {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()
