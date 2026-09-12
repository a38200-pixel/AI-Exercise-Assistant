"""인증된 사용자의 Workout REST endpoints."""

from datetime import date
from typing import Annotated

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
            date.today(),
        )
    except Exception as exc:
        raise _database_error() from exc


@router.get("/daily", response_model=list[DailyWorkoutSummaryResponse])
def read_daily_summaries(
    current_user: AuthenticatedUser,
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
) -> list[dict]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be greater than or equal to start_date.",
        )
    try:
        return workout_service.get_daily_summaries(
            current_user.supabase,
            current_user.id,
            start_date,
            end_date,
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

