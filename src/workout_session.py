"""Workout Session의 시간과 운동 결과 summary를 관리한다."""

from datetime import datetime
from typing import Any

from src.exercise_counter import ExerciseCounter


class WorkoutSession:
    def __init__(self) -> None:
        # 현재 Workout Session이 진행 중인지 나타낸다.
        self.is_active = False

        # 경과시간 계산 전용 monotonic 시각이다.
        self.session_start_perf: float | None = None

        # 사용자 표시와 향후 DB 저장에 사용할 timezone-aware 실제 시각이다.
        self.session_start_datetime: datetime | None = None
        self.session_end_datetime: datetime | None = None

        # 가장 최근에 정상 종료된 세션의 API 전달용 결과를 보존한다.
        self.last_summary: dict[str, Any] | None = None

    def start(
        self,
        exercise_counter: ExerciseCounter,
        current_time: float,
        current_datetime: datetime | None = None,
    ) -> bool:
        """새 세션을 시작하고 운동 기록을 0부터 준비한다."""
        if self.is_active:
            print("Workout session already active.")
            return False

        started_at = self._get_aware_datetime(current_datetime)
        exercise_counter.reset_all_exercises()

        self.is_active = True
        self.session_start_perf = float(current_time)
        self.session_start_datetime = started_at
        self.session_end_datetime = None
        return True

    def update(self, current_time: float) -> float:
        """프레임마다 호출해도 상태를 바꾸지 않고 현재 경과시간만 반환한다."""
        return self.get_elapsed_seconds(current_time)

    def end(
        self,
        exercise_counter: ExerciseCounter,
        current_time: float,
        current_datetime: datetime | None = None,
    ) -> dict[str, Any] | None:
        """진행 중 운동을 마감하고 DB 전달에 적합한 summary를 생성한다."""
        if not self.is_active:
            print("No active workout session.")
            return None

        if self.session_start_perf is None or self.session_start_datetime is None:
            raise RuntimeError("Active workout session has no start timestamp.")

        ended_at = self._get_aware_datetime(current_datetime)
        workout_seconds = max(0.0, float(current_time) - self.session_start_perf)

        # Stretch 자세로 종료하더라도 종료 시각까지의 구간을 결과에 포함한다.
        exercise_counter.finish_active_exercise(float(current_time))

        # 자정을 지나 종료해도 workout_date는 세션을 시작한 local date를 사용한다.
        summary = {
            "workout_date": self.session_start_datetime.date().isoformat(),
            "started_at": self.session_start_datetime.isoformat(timespec="seconds"),
            "ended_at": ended_at.isoformat(timespec="seconds"),
            "workout_seconds": workout_seconds,
            "squat_count": int(exercise_counter.squat_count),
            "stretch_seconds": float(exercise_counter.total_stretch_seconds),
        }

        self.is_active = False
        self.session_end_datetime = ended_at
        self.last_summary = summary
        return summary

    def get_elapsed_seconds(self, current_time: float) -> float:
        if not self.is_active or self.session_start_perf is None:
            return 0.0
        return max(0.0, float(current_time) - self.session_start_perf)

    def get_status(self, current_time: float) -> dict[str, Any]:
        return {
            "status": "ACTIVE" if self.is_active else "READY",
            "elapsed_seconds": self.get_elapsed_seconds(current_time),
        }

    @staticmethod
    def _get_aware_datetime(value: datetime | None) -> datetime:
        actual_datetime = value if value is not None else datetime.now().astimezone()
        if actual_datetime.tzinfo is None or actual_datetime.utcoffset() is None:
            raise ValueError("Workout session datetime must include timezone information.")
        return actual_datetime

