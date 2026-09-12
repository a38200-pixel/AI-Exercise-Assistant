"""카메라와 AI 모델 없이 PredictionSmoother 상태 전이를 검증한다."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import MISSING_POSE_TOLERANCE_FRAMES
from src.prediction_smoother import PredictionSmoother


def make_stable_stand(smoother: PredictionSmoother) -> None:
    for _ in range(3):
        state = smoother.update("stand", 0.90)
    assert state["stable_label"] == "stand"


def test_initial_stand_requires_three_frames() -> None:
    smoother = PredictionSmoother()
    assert smoother.update("stand", 0.90)["stable_label"] is None
    assert smoother.update("stand", 0.91)["stable_label"] is None
    state = smoother.update("stand", 0.92)
    assert state["stable_label"] == "stand"


def test_single_squat_does_not_replace_stand() -> None:
    smoother = PredictionSmoother()
    make_stable_stand(smoother)
    assert smoother.update("squat", 0.80)["stable_label"] == "stand"
    state = smoother.update("stand", 0.93)
    assert state["stable_label"] == "stand"
    assert state["candidate_label"] is None


def test_three_squats_replace_stand() -> None:
    smoother = PredictionSmoother()
    make_stable_stand(smoother)
    smoother.update("squat", 0.80)
    smoother.update("squat", 0.82)
    state = smoother.update("squat", 0.84)
    assert state["stable_label"] == "squat"
    assert abs(state["stable_confidence"] - 0.82) < 1e-9


def test_jump_requires_two_frames() -> None:
    smoother = PredictionSmoother()
    make_stable_stand(smoother)
    assert smoother.update("jump", 0.85)["stable_label"] == "stand"
    state = smoother.update("jump", 0.87)
    assert state["stable_label"] == "jump"
    assert abs(state["stable_confidence"] - 0.86) < 1e-9


def test_alternating_predictions_do_not_become_stable() -> None:
    smoother = PredictionSmoother()
    sequence = ("stand", "squat", "stand", "squat", "stand", "squat")
    for label in sequence:
        state = smoother.update(label, 0.80)
    assert state["stable_label"] is None


def test_short_missing_sequence_keeps_stand() -> None:
    smoother = PredictionSmoother()
    make_stable_stand(smoother)
    smoother.update_missing()
    state = smoother.update_missing()
    assert state["stable_label"] == "stand"


def test_missing_tolerance_exceeded_clears_stable() -> None:
    smoother = PredictionSmoother()
    make_stable_stand(smoother)
    for _ in range(MISSING_POSE_TOLERANCE_FRAMES + 1):
        state = smoother.update_missing()
    assert state["stable_label"] is None
    assert state["stable_confidence"] == 0.0


def main() -> None:
    tests = (
        test_initial_stand_requires_three_frames,
        test_single_squat_does_not_replace_stand,
        test_three_squats_replace_stand,
        test_jump_requires_two_frames,
        test_alternating_predictions_do_not_become_stable,
        test_short_missing_sequence_keeps_stand,
        test_missing_tolerance_exceeded_clears_stable,
    )

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\nPrediction smoothing tests passed: {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()

