"""Stable pose를 사용하는 Squat과 Stretch 운동 규칙."""

from typing import Any


IDLE_MODE = "idle"
SQUAT_MODE = "squat"
STRETCH_MODE = "stretch"
SUPPORTED_MODES = (IDLE_MODE, SQUAT_MODE, STRETCH_MODE)

SQUAT_WAITING_STAND = "WAITING_STAND"
SQUAT_WAITING_SQUAT = "WAITING_SQUAT"
SQUAT_WAITING_RETURN_STAND = "WAITING_RETURN_STAND"


class ExerciseCounter:
    def __init__(self) -> None:
        self.exercise_mode = IDLE_MODE
        self.last_stable_pose: str | None = None

        self.squat_count = 0
        self.squat_state = SQUAT_WAITING_STAND

        self.total_stretch_seconds = 0.0
        self.stretch_start_time: float | None = None

    def set_mode(self, mode: str, current_time: float) -> None:
        """운동 모드를 바꾸되 이미 완료된 count와 누적 시간은 보존한다."""
        if mode not in SUPPORTED_MODES:
            raise ValueError(f"Unsupported exercise mode: {mode}")
        if mode == self.exercise_mode:
            return

        # Stretch 도중 모드를 바꾸면 변경 시각까지의 시간을 먼저 누적한다.
        if self.exercise_mode == STRETCH_MODE:
            self._finish_stretch(current_time)

        self.exercise_mode = mode
        self._reset_progress_states()

    def update(self, stable_pose: str | None, current_time: float) -> None:
        """Raw pose가 아닌 smoothing을 통과한 stable pose만 입력받는다."""
        self.last_stable_pose = stable_pose

        if self.exercise_mode == SQUAT_MODE:
            self._update_squat(stable_pose)
        elif self.exercise_mode == STRETCH_MODE:
            self._update_stretch(stable_pose, current_time)

    def reset_current_exercise(self, current_time: float) -> None:
        """현재 선택된 운동 기록과 진행 상태만 초기화한다."""
        if self.exercise_mode == SQUAT_MODE:
            self.squat_count = 0
            self.squat_state = SQUAT_WAITING_STAND
        elif self.exercise_mode == STRETCH_MODE:
            self.total_stretch_seconds = 0.0
            if self.last_stable_pose == "stretch":
                self.stretch_start_time = current_time
            else:
                self.stretch_start_time = None

    def reset_all_exercises(self) -> None:
        """새 Workout Session을 위해 Squat과 Stretch 기록을 모두 초기화한다."""
        self.squat_count = 0
        self.squat_state = SQUAT_WAITING_STAND
        self.total_stretch_seconds = 0.0
        self.stretch_start_time = None

    def finish_active_exercise(self, current_time: float) -> None:
        """진행 중인 Stretch 구간을 현재 시각까지 한 번만 누적한다."""
        self._finish_stretch(current_time)

    def get_status(self, current_time: float) -> dict[str, Any]:
        """화면 표시에 필요한 현재 운동 상태를 반환한다."""
        stretch_seconds = self.total_stretch_seconds
        if self.stretch_start_time is not None:
            stretch_seconds += current_time - self.stretch_start_time

        if self.exercise_mode == SQUAT_MODE:
            exercise_state = self.squat_state
        elif self.exercise_mode == STRETCH_MODE:
            exercise_state = (
                "STRETCHING" if self.stretch_start_time is not None else "WAITING_STRETCH"
            )
        else:
            exercise_state = "IDLE"

        return {
            "mode": self.exercise_mode,
            "stable_pose": self.last_stable_pose,
            "state": exercise_state,
            "squat_count": self.squat_count,
            "stretch_seconds": stretch_seconds,
        }

    def _update_squat(self, stable_pose: str | None) -> None:
        # 반드시 stand를 먼저 확인해야 squat -> stand 시작 오작동을 막을 수 있다.
        if self.squat_state == SQUAT_WAITING_STAND:
            if stable_pose == "stand":
                self.squat_state = SQUAT_WAITING_SQUAT
            return

        # 준비된 stand 이후 squat 자세가 나올 때까지 기다린다.
        if self.squat_state == SQUAT_WAITING_SQUAT:
            if stable_pose == "squat":
                self.squat_state = SQUAT_WAITING_RETURN_STAND
            return

        # squat 이후 다시 stand가 되었을 때에만 정확히 한 번 증가한다.
        if self.squat_state == SQUAT_WAITING_RETURN_STAND:
            if stable_pose == "stand":
                self.squat_count += 1
                self.squat_state = SQUAT_WAITING_SQUAT

    def _update_stretch(self, stable_pose: str | None, current_time: float) -> None:
        if stable_pose == "stretch":
            # stretch로 처음 전환된 시각만 저장하고, 유지 프레임에서는 바꾸지 않는다.
            if self.stretch_start_time is None:
                self.stretch_start_time = current_time
            return

        self._finish_stretch(current_time)

    def _finish_stretch(self, current_time: float) -> None:
        if self.stretch_start_time is None:
            return

        self.total_stretch_seconds += current_time - self.stretch_start_time
        self.stretch_start_time = None

    def _reset_progress_states(self) -> None:
        self.squat_state = SQUAT_WAITING_STAND
        self.stretch_start_time = None
