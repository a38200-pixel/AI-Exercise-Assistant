"""Squat과 Stretch 운동 규칙. Squat은 RepTracker(무릎각 시계열)가 있으면 그 결과로, 없으면 stable 라벨 전이로 센다."""

from typing import Any

from src.rep_tracker import RepFrame, RepResult, RepTracker


IDLE_MODE = "idle"
SQUAT_MODE = "squat"
STRETCH_MODE = "stretch"
SUPPORTED_MODES = (IDLE_MODE, SQUAT_MODE, STRETCH_MODE)

SQUAT_WAITING_STAND = "WAITING_STAND"
SQUAT_WAITING_SQUAT = "WAITING_SQUAT"
SQUAT_WAITING_RETURN_STAND = "WAITING_RETURN_STAND"


class ExerciseCounter:
    def __init__(self, rep_tracker: RepTracker | None = None) -> None:
        """rep_tracker가 있으면 squat 모드의 count는 RepTracker가 확정한 반복만 센다(v0.2.0).
        없으면 v0.1.x처럼 stable 라벨의 stand → squat → stand 전이로 센다."""
        self.exercise_mode = IDLE_MODE
        self.last_stable_pose: str | None = None
        self._rep_tracker = rep_tracker
        self.last_rep_result: RepResult | None = None

        self.squat_count = 0
        self.squat_state = SQUAT_WAITING_STAND

        self.total_stretch_seconds = 0.0
        self.stretch_start_time: float | None = None

    @property
    def uses_rep_tracker(self) -> bool:
        return self._rep_tracker is not None

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

    def update(
        self,
        stable_pose: str | None,
        current_time: float,
        rep_frame: RepFrame | None = None,
    ) -> None:
        """Raw pose가 아닌 smoothing을 통과한 stable pose만 입력받는다. rep_frame은 RepTracker용 기하 입력이다."""
        self.last_stable_pose = stable_pose

        if self.exercise_mode == SQUAT_MODE:
            if self._rep_tracker is not None:
                self._update_squat_reps(stable_pose, rep_frame, current_time)
            else:
                self._update_squat(stable_pose)
        elif self.exercise_mode == STRETCH_MODE:
            self._update_stretch(stable_pose, current_time)

    def reset_current_exercise(self, current_time: float) -> None:
        """현재 선택된 운동 기록과 진행 상태만 초기화한다."""
        if self.exercise_mode == SQUAT_MODE:
            self.squat_count = 0
            self.squat_state = SQUAT_WAITING_STAND
            self._reset_rep_tracker()
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
        self._reset_rep_tracker()
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
            exercise_state = self._rep_tracker.state if self._rep_tracker is not None else self.squat_state
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
            # RepTracker가 있을 때만 의미가 있다(Phase 3 화면 안내·점수용).
            "rep_guidance": self._rep_tracker.guidance if self._rep_tracker is not None else None,
            # squat 모드에서 BodyLock이 오래 잡히지 않을 때의 안내 사유("not_side" / "full_body_invalid") 또는 None.
            "rep_notice": (
                self._rep_tracker.notice
                if self._rep_tracker is not None and self.exercise_mode == SQUAT_MODE
                else None
            ),
            "last_rep": self.last_rep_result,
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

    def rep_diagnostics(self) -> dict[str, Any] | None:
        """로그용 진단 정보: RepTracker 상태, 안내 사유, 마지막 호출 이후의 이벤트(rep_end, rep_merge_suspect).
        RepTracker를 쓰지 않거나 squat 모드가 아니면 None. 호출하면 이벤트가 비워진다."""
        if self._rep_tracker is None or self.exercise_mode != SQUAT_MODE:
            return None
        return {
            "state": self._rep_tracker.state,
            "notice": self._rep_tracker.notice,
            "events": self._rep_tracker.pop_events(),
        }

    def _update_squat_reps(self, stable_pose: str | None, rep_frame: RepFrame | None, current_time: float) -> None:
        """RepTracker가 확정한 반복만 센다. 탈락·중단된 반복은 last_rep_result에만 남는다."""
        assert self._rep_tracker is not None
        frame = rep_frame if rep_frame is not None else RepFrame.missing(current_time)
        result = self._rep_tracker.update(frame, stable_pose)
        if result is None:
            return
        self.last_rep_result = result
        if result.counted:
            self.squat_count += 1

    def _reset_rep_tracker(self) -> None:
        self.last_rep_result = None
        if self._rep_tracker is not None:
            self._rep_tracker.reset()

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
        self._reset_rep_tracker()
        self.stretch_start_time = None
