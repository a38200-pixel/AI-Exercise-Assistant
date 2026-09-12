"""FastAPI authentication and request validation tests without cloud writes."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

from backend.app.dependencies.auth import CurrentUser, get_current_user  # noqa: E402
from backend.app.main import app  # noqa: E402


class WorkoutApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_missing_token_returns_401(self) -> None:
        response = self.client.get("/api/workouts/today")
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_returns_401(self) -> None:
        with patch(
            "backend.app.dependencies.auth.create_user_supabase_client",
            side_effect=RuntimeError("invalid token"),
        ):
            response = self.client.get(
                "/api/workouts/today",
                headers={"Authorization": "Bearer invalid"},
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid or expired access token.")

    def test_negative_workout_payload_returns_422(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            id="11111111-1111-1111-1111-111111111111",
            email="user@example.invalid",
            supabase=object(),
        )
        response = self.client.post(
            "/api/workouts",
            json={
                "workout_date": "2026-09-12",
                "started_at": "2026-09-12T16:30:00+09:00",
                "ended_at": "2026-09-12T16:40:00+09:00",
                "workout_seconds": 600,
                "squat_count": -1,
                "stretch_seconds": 120,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_daily_range_is_optional(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            id="11111111-1111-1111-1111-111111111111",
            email="user@example.invalid",
            supabase=object(),
        )
        with patch(
            "backend.app.routers.workouts.workout_service.get_daily_summaries",
            return_value=[],
        ) as get_summaries:
            response = self.client.get("/api/workouts/daily")
        self.assertEqual(response.status_code, 200)
        start_date = get_summaries.call_args.args[2]
        end_date = get_summaries.call_args.args[3]
        self.assertEqual((end_date - start_date).days, 30)

    def test_reversed_daily_range_returns_422(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            id="11111111-1111-1111-1111-111111111111",
            email=None,
            supabase=object(),
        )
        response = self.client.get(
            "/api/workouts/daily",
            params={"start_date": "2026-09-12", "end_date": "2026-09-01"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
