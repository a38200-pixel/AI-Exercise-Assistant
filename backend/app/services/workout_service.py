"""Supabase workout query와 atomic RPC 호출을 담당한다."""

from datetime import date
from typing import Any

from backend.app.schemas.workout import WorkoutSessionCreate


DAILY_SUMMARY_COLUMNS = (
    "workout_date,squat_count,stretch_seconds,workout_seconds,session_count"
)
SESSION_COLUMNS = (
    "id,workout_date,started_at,ended_at,workout_seconds,"
    "squat_count,stretch_seconds"
)


class WorkoutServiceError(RuntimeError):
    """DB 내부 세부사항을 HTTP 응답과 분리하기 위한 service 오류."""


def create_workout_session(client: Any, workout: WorkoutSessionCreate) -> dict[str, Any]:
    payload = {
        "p_workout_date": workout.workout_date.isoformat(),
        "p_started_at": workout.started_at.isoformat(),
        "p_ended_at": workout.ended_at.isoformat(),
        "p_workout_seconds": workout.workout_seconds,
        "p_squat_count": workout.squat_count,
        "p_stretch_seconds": workout.stretch_seconds,
    }
    response = client.rpc("record_workout_session", payload).execute()
    session_id = _first_value(response.data)
    if session_id is None:
        raise WorkoutServiceError("Workout RPC returned no session id.")
    return {"id": session_id}


def get_today_summary(client: Any, user_id: str, today: date) -> dict[str, Any]:
    summary = get_daily_summary(client, user_id, today)
    if summary is not None:
        return summary
    return _empty_daily_summary(today)


def get_daily_summaries(
    client: Any,
    user_id: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    response = (
        client.table("daily_workout_summary")
        .select(DAILY_SUMMARY_COLUMNS)
        .eq("user_id", user_id)
        .gte("workout_date", start_date.isoformat())
        .lte("workout_date", end_date.isoformat())
        .order("workout_date", desc=True)
        .execute()
    )
    return list(response.data or [])


def get_daily_summary(
    client: Any,
    user_id: str,
    workout_date: date,
) -> dict[str, Any] | None:
    response = (
        client.table("daily_workout_summary")
        .select(DAILY_SUMMARY_COLUMNS)
        .eq("user_id", user_id)
        .eq("workout_date", workout_date.isoformat())
        .limit(1)
        .execute()
    )
    rows = list(response.data or [])
    return rows[0] if rows else None


def get_sessions_by_date(
    client: Any,
    user_id: str,
    workout_date: date,
) -> list[dict[str, Any]]:
    response = (
        client.table("workout_sessions")
        .select(SESSION_COLUMNS)
        .eq("user_id", user_id)
        .eq("workout_date", workout_date.isoformat())
        .order("started_at", desc=False)
        .execute()
    )
    return list(response.data or [])


def _empty_daily_summary(workout_date: date) -> dict[str, Any]:
    return {
        "workout_date": workout_date.isoformat(),
        "squat_count": 0,
        "stretch_seconds": 0.0,
        "workout_seconds": 0.0,
        "session_count": 0,
    }


def _first_value(data: Any) -> Any:
    if isinstance(data, list):
        if not data:
            return None
        first_item = data[0]
        if isinstance(first_item, dict):
            return first_item.get("record_workout_session") or first_item.get("id")
        return first_item
    if isinstance(data, dict):
        return data.get("record_workout_session") or data.get("id")
    return data

