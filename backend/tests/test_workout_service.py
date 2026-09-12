"""실제 Supabase 연결 없이 query와 RPC 구조를 검증한다."""

import unittest
from datetime import date, datetime, timedelta, timezone
from typing import Any

from backend.app.schemas.workout import WorkoutSessionCreate
from backend.app.services import workout_service


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    def __init__(self, client: "FakeClient", source: str, data: Any) -> None:
        self.client = client
        self.source = source
        self.data = data

    def _record(self, method: str, *args: Any, **kwargs: Any) -> "FakeQuery":
        self.client.calls.append((self.source, method, args, kwargs))
        return self

    def select(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self._record("select", *args, **kwargs)

    def eq(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self._record("eq", *args, **kwargs)

    def gte(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self._record("gte", *args, **kwargs)

    def lte(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self._record("lte", *args, **kwargs)

    def order(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self._record("order", *args, **kwargs)

    def limit(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self._record("limit", *args, **kwargs)

    def execute(self) -> FakeResponse:
        self._record("execute")
        return FakeResponse(self.data)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.table_data: dict[str, Any] = {}
        self.rpc_data: Any = None

    def table(self, table_name: str) -> FakeQuery:
        self.calls.append((table_name, "table", (), {}))
        return FakeQuery(self, table_name, self.table_data.get(table_name, []))

    def rpc(self, function_name: str, payload: dict) -> FakeQuery:
        self.calls.append((function_name, "rpc", (payload,), {}))
        return FakeQuery(self, function_name, self.rpc_data)


class WorkoutServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.user_id = "11111111-1111-1111-1111-111111111111"
        self.workout_date = date(2026, 9, 12)

    def test_create_calls_atomic_rpc_with_matching_payload(self) -> None:
        korea_timezone = timezone(timedelta(hours=9))
        workout = WorkoutSessionCreate(
            workout_date=self.workout_date,
            started_at=datetime(2026, 9, 12, 10, 0, tzinfo=korea_timezone),
            ended_at=datetime(2026, 9, 12, 10, 5, tzinfo=korea_timezone),
            workout_seconds=300,
            squat_count=10,
            stretch_seconds=60,
        )
        self.client.rpc_data = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

        result = workout_service.create_workout_session(self.client, workout)

        rpc_call = self.client.calls[0]
        self.assertEqual(rpc_call[0], "record_workout_session")
        payload = rpc_call[2][0]
        self.assertNotIn("user_id", payload)
        self.assertEqual(payload["p_squat_count"], 10)
        self.assertEqual(result["id"], self.client.rpc_data)

    def test_daily_summary_query_is_user_scoped(self) -> None:
        self.client.table_data["daily_workout_summary"] = []
        result = workout_service.get_today_summary(
            self.client,
            self.user_id,
            self.workout_date,
        )

        self.assertEqual(result["session_count"], 0)
        self.assertIn(
            ("daily_workout_summary", "eq", ("user_id", self.user_id), {}),
            self.client.calls,
        )
        self.assertIn(
            (
                "daily_workout_summary",
                "eq",
                ("workout_date", "2026-09-12"),
                {},
            ),
            self.client.calls,
        )

    def test_daily_range_query_has_dates_and_descending_order(self) -> None:
        workout_service.get_daily_summaries(
            self.client,
            self.user_id,
            date(2026, 9, 1),
            date(2026, 9, 30),
        )
        self.assertIn(
            ("daily_workout_summary", "gte", ("workout_date", "2026-09-01"), {}),
            self.client.calls,
        )
        self.assertIn(
            ("daily_workout_summary", "lte", ("workout_date", "2026-09-30"), {}),
            self.client.calls,
        )
        self.assertIn(
            ("daily_workout_summary", "order", ("workout_date",), {"desc": True}),
            self.client.calls,
        )

    def test_session_query_is_user_and_date_scoped(self) -> None:
        workout_service.get_sessions_by_date(
            self.client,
            self.user_id,
            self.workout_date,
        )
        self.assertIn(
            ("workout_sessions", "eq", ("user_id", self.user_id), {}),
            self.client.calls,
        )
        self.assertIn(
            ("workout_sessions", "eq", ("workout_date", "2026-09-12"), {}),
            self.client.calls,
        )
        self.assertIn(
            ("workout_sessions", "order", ("started_at",), {"desc": False}),
            self.client.calls,
        )


if __name__ == "__main__":
    unittest.main()

