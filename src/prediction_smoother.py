"""연속 프레임 확인 방식의 자세 예측 안정화."""

from typing import Any

from config.settings import (
    DEFAULT_STABLE_FRAMES,
    MISSING_POSE_TOLERANCE_FRAMES,
    POSE_STABLE_FRAMES,
)


class PredictionSmoother:
    def __init__(self) -> None:
        # stable: 시스템이 최종적으로 인정하고 있는 현재 자세
        self.stable_label: str | None = None
        self.stable_confidence = 0.0

        # candidate: stable과 다른 자세가 연속으로 들어오는지 확인하는 상태
        self.candidate_label: str | None = None
        self.candidate_count = 0
        self.candidate_confidences: list[float] = []

        # MediaPipe가 자세를 연속으로 놓친 프레임 수
        self.missing_count = 0

    def get_required_frames(self, label: str) -> int:
        """자세별 연속 확인 횟수를 반환한다."""
        return POSE_STABLE_FRAMES.get(label, DEFAULT_STABLE_FRAMES)

    def update(self, label: str, confidence: float) -> dict[str, Any]:
        """Raw prediction을 받아 candidate를 거쳐 stable prediction을 갱신한다."""
        self.missing_count = 0

        # 이미 안정화된 자세와 같으면 새로운 후보가 필요 없다.
        if label == self.stable_label:
            self.stable_confidence = float(confidence)
            self._reset_candidate()
            return self._current_state()

        # 직전 후보와 같아야 연속 프레임으로 인정한다.
        if label == self.candidate_label:
            self.candidate_count += 1
            self.candidate_confidences.append(float(confidence))
        else:
            self.candidate_label = label
            self.candidate_count = 1
            self.candidate_confidences = [float(confidence)]

        required_count = self.get_required_frames(label)
        if self.candidate_count >= required_count:
            self.stable_label = self.candidate_label
            self.stable_confidence = sum(self.candidate_confidences) / len(
                self.candidate_confidences
            )
            self._reset_candidate()

        return self._current_state()

    def update_missing(self) -> dict[str, Any]:
        """Pose 미검출이 잠깐 발생해도 허용 범위 동안 stable 자세를 유지한다."""
        self.missing_count += 1

        # 미검출 프레임은 후보 자세의 연속 검출로 볼 수 없으므로 후보를 지운다.
        self._reset_candidate()

        if self.missing_count > MISSING_POSE_TOLERANCE_FRAMES:
            self.stable_label = None
            self.stable_confidence = 0.0

        return self._current_state()

    def reset(self) -> None:
        """stable, candidate, missing 상태를 모두 초기화한다."""
        self.stable_label = None
        self.stable_confidence = 0.0
        self.missing_count = 0
        self._reset_candidate()

    def _reset_candidate(self) -> None:
        self.candidate_label = None
        self.candidate_count = 0
        self.candidate_confidences = []

    def _current_state(self) -> dict[str, Any]:
        required_count = 0
        if self.candidate_label is not None:
            required_count = self.get_required_frames(self.candidate_label)

        return {
            "stable_label": self.stable_label,
            "stable_confidence": self.stable_confidence,
            "candidate_label": self.candidate_label,
            "candidate_count": self.candidate_count,
            "required_count": required_count,
            "missing_count": self.missing_count,
        }

