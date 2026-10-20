"""Workout Session의 시간과 운동 결과 summary를 관리한다."""

import json
import logging
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import config.settings as settings
from src.exercise_counter import ExerciseCounter
from src.paths import get_workout_log_dir
from src.rep_tracker import RepResult

LOCAL_RECORD_SCHEMA_VERSION = 1
logger = logging.getLogger(__name__)


class WorkoutSession:
    def __init__(self, log_dir: Path | None = None, save_local_record: bool = True) -> None:
        """log_dir을 주지 않으면 src.paths.get_workout_log_dir()(개발: data/workout_logs/, 패키징: %LOCALAPPDATA%/FitRoute/workout_logs)를 쓴다.
        세션이 끝날 때 저장하며, 저장 실패는 세션 종료와 서버 업로드를 막지 않는다."""
        self._log_dir = log_dir
        self._save_local_record = save_local_record
        self.last_record_path: Path | None = None
        self.last_save_error: str | None = None
        # 현재 Workout Session이 진행 중인지 나타낸다.
        self.is_active = False

        # 경과시간 계산 전용 monotonic 시각이다.
        self.session_start_perf: float | None = None

        # 사용자 표시와 향후 DB 저장에 사용할 timezone-aware 실제 시각이다.
        self.session_start_datetime: datetime | None = None
        self.session_end_datetime: datetime | None = None

        # 가장 최근에 정상 종료된 세션의 API 전달용 결과를 보존한다.
        self.last_summary: dict[str, Any] | None = None

        # 가장 최근 세션의 로컬 기록: 반복별 결과(확정·탈락, 자세 점수의 항목별 판정·점수·worst_item). **서버로 업로드하지 않는다**
        # (last_summary와 업로드 형식은 그대로). 0.2.0은 화면과 이 로컬 기록에만 둔다.
        self.last_local_record: dict[str, Any] | None = None

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
        self.last_local_record = None
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
        self.last_local_record = self._build_local_record(summary, exercise_counter)
        self._write_local_record(self.last_local_record)
        return summary

    def _build_local_record(self, summary: dict[str, Any], exercise_counter: ExerciseCounter) -> dict[str, Any]:
        reps, number = [], 0
        for index, result in enumerate(exercise_counter.rep_history, start=1):
            if result.counted:
                number += 1
            reps.append(rep_record(result, index, number if result.counted else None, self.session_start_perf))
        return {
            "schema_version": LOCAL_RECORD_SCHEMA_VERSION,
            **summary,  # 서버로 업로드하는 summary와 같은 필드·값
            "reps": reps,
            "settings": _decision_settings(),
        }

    def _write_local_record(self, record: dict[str, Any]) -> None:
        """세션별 JSON(workout_<시작시각>.json)을 저장한다. 어떤 오류도 밖으로 내보내지 않는다(세션 종료와 업로드가 먼저다)."""
        self.last_record_path = None
        self.last_save_error = None
        if not self._save_local_record:
            return
        try:
            directory = Path(self._log_dir) if self._log_dir is not None else get_workout_log_dir()
            directory.mkdir(parents=True, exist_ok=True)
            stamp = self.session_start_datetime.strftime("%Y%m%d_%H%M%S")
            path = directory / f"workout_{stamp}.json"
            serial = 1
            while path.exists():  # 같은 초에 끝난 세션이 앞의 파일을 덮어쓰지 않게 한다
                serial += 1
                path = directory / f"workout_{stamp}_{serial}.json"
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            os.replace(temporary, path)
            self.last_record_path = path
        except Exception as exc:  # noqa: BLE001 - 저장 실패가 운동 기록 종료·업로드를 막으면 안 된다
            self.last_save_error = repr(exc)
            logger.warning("Could not save the local workout record: %r", exc)
            print(f"[Local] Could not save the workout record: {exc}")

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


def _number(value: float | None) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), 3)


def rep_record(result: RepResult, index: int, rep_number: int | None, session_start: float | None) -> dict[str, Any]:
    """반복 후보 하나의 로컬 기록. index는 세션 안의 후보 순번, rep_number는 확정된 반복의 순번(탈락·중단이면 None)."""
    posture = result.posture
    return {
        "index": index,
        "rep_number": rep_number,
        "counted": result.counted,
        "reasons": list(result.reasons),
        "seconds_from_start": _number(result.t_start - session_start) if session_start is not None else None,
        "total_seconds": _number(result.total_seconds),
        "min_knee_angle": _number(result.min_knee_angle),
        "hip_drop_norm": _number(result.hip_drop_norm),
        "posture": None
        if posture is None
        else {
            "total_score": _number(posture.total_score),
            "worst_item": posture.worst_item,
            "capped": posture.capped,
            "item_status": dict(posture.item_status),
            "item_scores": {key: _number(value) for key, value in posture.item_scores.items()},
            "measures": {key: _number(value) for key, value in posture.measures.items()},
        },
    }


def _decision_settings() -> dict[str, Any]:
    """기록 시점의 판정 기준(임계값은 2차 실측 뒤 바뀔 수 있어, 점수를 나중에 해석할 수 있게 함께 남긴다)."""
    names = (
        "REP_MIN_SECONDS", "REP_MIN_HIP_DROP", "REP_MAX_ANKLE_GAP", "REP_MAX_ANKLE_GAP_BOTTOM", "REP_MAX_HIP_SHIFT",
        "REP_OTHER_EXERCISE_MAX_RATIO",
        "POSTURE_DEPTH_NORMAL_MAX", "POSTURE_DEPTH_CORRECT_MIN", "POSTURE_DEPTH_ZERO_AT",
        "POSTURE_TORSO_SHIN_NORMAL_MAX", "POSTURE_TORSO_SHIN_CORRECT_MIN",
        "POSTURE_WEIGHT_DEPTH", "POSTURE_WEIGHT_TORSO_SHIN", "POSTURE_SCORE_CAP_WITH_CORRECTION",
    )
    return {name: getattr(settings, name) for name in names}
