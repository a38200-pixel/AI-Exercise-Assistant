"""인증된 사용자의 Workout REST endpoints."""

from datetime import date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.dependencies.auth import CurrentUser, get_current_user
from backend.app.schemas.workout import (
    DailyWorkoutSummaryResponse,
    WorkoutSessionCreate,
    WorkoutSessionCreatedResponse,
    WorkoutSessionResponse,
)
from backend.app.services import workout_service


router = APIRouter(prefix="/api/workouts", tags=["workouts"])
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
KOREA_TIMEZONE = ZoneInfo("Asia/Seoul")


def _today_in_korea() -> date:
    return datetime.now(KOREA_TIMEZONE).date()


@router.post("", response_model=WorkoutSessionCreatedResponse, status_code=201)
def create_workout(
    workout: WorkoutSessionCreate,
    current_user: AuthenticatedUser,
) -> dict:
    try:
        return workout_service.create_workout_session(current_user.supabase, workout)
    except Exception as exc:
        raise _database_error() from exc


@router.get("/today", response_model=DailyWorkoutSummaryResponse)
def read_today_summary(current_user: AuthenticatedUser) -> dict:
    try:
        return workout_service.get_today_summary(
            current_user.supabase,
            current_user.id,
            _today_in_korea(),
        )
    except Exception as exc:
        raise _database_error() from exc


@router.get("/daily", response_model=list[DailyWorkoutSummaryResponse])
def read_daily_summaries(
    current_user: AuthenticatedUser,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> list[dict]:
    # A query without a range returns the most recent 31 calendar days in Korea.
    range_end = end_date or _today_in_korea()
    range_start = start_date or (range_end - timedelta(days=30))
    if range_end < range_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_date must be greater than or equal to start_date.",
        )
    try:
        return workout_service.get_daily_summaries(
            current_user.supabase,
            current_user.id,
            range_start,
            range_end,
        )
    except Exception as exc:
        raise _database_error() from exc


@router.get("/daily/{workout_date}", response_model=DailyWorkoutSummaryResponse)
def read_daily_summary(workout_date: date, current_user: AuthenticatedUser) -> dict:
    try:
        summary = workout_service.get_daily_summary(
            current_user.supabase,
            current_user.id,
            workout_date,
        )
    except Exception as exc:
        raise _database_error() from exc

    if summary is None:
        return {
            "workout_date": workout_date,
            "squat_count": 0,
            "stretch_seconds": 0.0,
            "workout_seconds": 0.0,
            "session_count": 0,
        }
    return summary


@router.get(
    "/sessions/{workout_date}",
    response_model=list[WorkoutSessionResponse],
)
def read_sessions(workout_date: date, current_user: AuthenticatedUser) -> list[dict]:
    try:
        return workout_service.get_sessions_by_date(
            current_user.supabase,
            current_user.id,
            workout_date,
        )
    except Exception as exc:
        raise _database_error() from exc


def _database_error() -> HTTPException:
    """DB key, token, query 세부내용을 client response에 포함하지 않는다."""
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Workout database operation failed.",
    )
