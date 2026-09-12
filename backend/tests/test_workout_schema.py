"""Workout Pydantic schema validation tests."""

import unittest
from datetime import date, datetime, timedelta, timezone

from pydantic import ValidationError

from backend.app.schemas.workout import WorkoutSessionCreate


KOREA_TIMEZONE = timezone(timedelta(hours=9))


def valid_payload() -> dict:
    return {
        "workout_date": date(2026, 9, 12),
        "started_at": datetime(2026, 9, 12, 14, 30, tzinfo=KOREA_TIMEZONE),
        "ended_at": datetime(2026, 9, 12, 14, 42, tzinfo=KOREA_TIMEZONE),
        "workout_seconds": 720.0,
        "squat_count": 20,
        "stretch_seconds": 120.0,
    }


class WorkoutSchemaTests(unittest.TestCase):
    def test_valid_workout(self) -> None:
        workout = WorkoutSessionCreate(**valid_payload())
        self.assertEqual(workout.squat_count, 20)

    def test_negative_workout_seconds_fails(self) -> None:
        payload = valid_payload()
        payload["workout_seconds"] = -1
        with self.assertRaises(ValidationError):
            WorkoutSessionCreate(**payload)

    def test_negative_squat_count_fails(self) -> None:
        payload = valid_payload()
        payload["squat_count"] = -1
        with self.assertRaises(ValidationError):
            WorkoutSessionCreate(**payload)

    def test_negative_stretch_seconds_fails(self) -> None:
        payload = valid_payload()
        payload["stretch_seconds"] = -1
        with self.assertRaises(ValidationError):
            WorkoutSessionCreate(**payload)

    def test_end_before_start_fails(self) -> None:
        payload = valid_payload()
        payload["ended_at"] = datetime(2026, 9, 12, 14, 0, tzinfo=KOREA_TIMEZONE)
        with self.assertRaises(ValidationError):
            WorkoutSessionCreate(**payload)

    def test_timezone_naive_datetime_fails(self) -> None:
        payload = valid_payload()
        payload["started_at"] = datetime(2026, 9, 12, 14, 30)
        with self.assertRaises(ValidationError):
            WorkoutSessionCreate(**payload)

    def test_timezone_aware_datetime_passes(self) -> None:
        workout = WorkoutSessionCreate(**valid_payload())
        self.assertIsNotNone(workout.started_at.utcoffset())
        self.assertIsNotNone(workout.ended_at.utcoffset())


if __name__ == "__main__":
    unittest.main()

