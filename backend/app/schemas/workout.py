"""Workout API의 request/response validation schema."""

from datetime import date, datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, model_validator


class WorkoutSessionCreate(BaseModel):
    workout_date: date
    started_at: AwareDatetime
    ended_at: AwareDatetime
    workout_seconds: float = Field(ge=0)
    squat_count: int = Field(ge=0)
    stretch_seconds: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_time_order(self) -> "WorkoutSessionCreate":
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must be greater than or equal to started_at")
        return self


class WorkoutSessionCreatedResponse(BaseModel):
    id: UUID


class WorkoutSessionResponse(BaseModel):
    id: UUID
    workout_date: date
    started_at: datetime
    ended_at: datetime
    workout_seconds: float
    squat_count: int
    stretch_seconds: float


class DailyWorkoutSummaryResponse(BaseModel):
    workout_date: date
    squat_count: int
    stretch_seconds: float
    workout_seconds: float
    session_count: int

