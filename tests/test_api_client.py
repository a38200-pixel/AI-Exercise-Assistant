"""Workout API client and pending retry tests without a live server."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from src.exercise_counter import ExerciseCounter
from src.main import handle_keyboard_input
from src.api_client import (
    WorkoutApiClient,
    WorkoutAuthenticationError,
    WorkoutConnectionError,
    WorkoutServerError,
    WorkoutUploader,
    WorkoutValidationError,
)
from src.workout_session import WorkoutSession


SUMMARY = {
    "workout_date": "2026-09-13",
    "started_at": "2026-09-13T13:30:00+09:00",
    "ended_at": "2026-09-13T13:42:30+09:00",
    "workout_seconds": 750.0,
    "squat_count": 25,
    "stretch_seconds": 180.0,
}


def client() -> WorkoutApiClient:
    return WorkoutApiClient("http://127.0.0.1:8001/", "user-access-token")


def response(status_code: int, body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=body or {},
        request=httpx.Request("POST", "http://127.0.0.1:8001/api/workouts"),
    )


def test_201_returns_session_id_and_preserves_summary_fields() -> None:
    with patch("src.api_client.httpx.post", return_value=response(201, {"id": "session-id"})) as post:
        session_id = client().save_workout_session(SUMMARY)

    assert session_id == "session-id"
    assert post.call_args.kwargs["json"] == SUMMARY
    assert post.call_args.kwargs["timeout"] == 10.0
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer user-access-token"


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, WorkoutAuthenticationError),
        (422, WorkoutValidationError),
        (500, WorkoutServerError),
    ],
)
def test_known_api_errors(status_code: int, error_type: type[Exception]) -> None:
    with patch("src.api_client.httpx.post", return_value=response(status_code)):
        with pytest.raises(error_type):
            client().save_workout_session(SUMMARY)


def test_timeout_is_safe_connection_error() -> None:
    request = httpx.Request("POST", "http://127.0.0.1:8001/api/workouts")
    with patch("src.api_client.httpx.post", side_effect=httpx.ReadTimeout("timeout", request=request)):
        with pytest.raises(WorkoutConnectionError, match="Could not connect"):
            client().save_workout_session(SUMMARY)


def test_connection_failure_is_safe_connection_error() -> None:
    request = httpx.Request("POST", "http://127.0.0.1:8001/api/workouts")
    with patch("src.api_client.httpx.post", side_effect=httpx.ConnectError("offline", request=request)):
        with pytest.raises(WorkoutConnectionError, match="Could not connect"):
            client().save_workout_session(SUMMARY)


class SequencedApiClient:
    def __init__(self, results: list[str | Exception]) -> None:
        self.results = results
        self.calls = 0
        self.summaries: list[dict] = []

    def save_workout_session(self, summary: dict) -> str:
        self.summaries.append(dict(summary))
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


def test_failed_upload_keeps_pending_summary() -> None:
    fake = SequencedApiClient([WorkoutConnectionError("offline")])
    uploader = WorkoutUploader(fake)  # type: ignore[arg-type]

    assert uploader.submit(SUMMARY) is False
    assert uploader.pending_summary == SUMMARY
    assert uploader.cloud_status == "FAILED"
    assert fake.summaries == [SUMMARY]


def test_success_clears_pending_and_prevents_duplicate_retry() -> None:
    fake = SequencedApiClient(["saved-id"])
    uploader = WorkoutUploader(fake)  # type: ignore[arg-type]

    assert uploader.submit(SUMMARY) is True
    assert uploader.pending_summary is None
    assert uploader.last_saved_session_id == "saved-id"
    assert uploader.retry() is False
    assert fake.calls == 1


def test_retry_success_clears_failed_pending_summary() -> None:
    fake = SequencedApiClient([WorkoutConnectionError("offline"), "retry-id"])
    uploader = WorkoutUploader(fake)  # type: ignore[arg-type]

    assert uploader.submit(SUMMARY) is False
    assert uploader.retry() is True
    assert uploader.pending_summary is None
    assert uploader.last_saved_session_id == "retry-id"
    assert fake.calls == 2


def test_disabled_uploader_does_not_crash_or_create_retry_duplicate() -> None:
    uploader = WorkoutUploader(None)

    assert uploader.submit(SUMMARY) is False
    assert uploader.pending_summary is None
    assert uploader.cloud_status == "DISABLED"


@pytest.mark.parametrize(("key", "should_quit"), [(ord("E"), False), (ord("Q"), True), (27, True)])
def test_end_and_quit_keys_finalize_and_upload_once(key: int, should_quit: bool) -> None:
    counter = ExerciseCounter()
    session = WorkoutSession()
    session.start(counter, 100.0)
    counter.squat_count = 3
    fake = SequencedApiClient(["keyboard-id"])
    uploader = WorkoutUploader(fake)  # type: ignore[arg-type]

    result = handle_keyboard_input(key, counter, session, uploader, 110.0)

    assert result is should_quit
    assert session.is_active is False
    assert fake.calls == 1
    assert uploader.pending_summary is None


def test_p_key_retries_only_the_pending_summary() -> None:
    fake = SequencedApiClient([WorkoutConnectionError("offline"), "retry-id"])
    uploader = WorkoutUploader(fake)  # type: ignore[arg-type]
    assert uploader.submit(SUMMARY) is False

    result = handle_keyboard_input(
        ord("P"),
        ExerciseCounter(),
        WorkoutSession(),
        uploader,
        100.0,
    )

    assert result is False
    assert uploader.pending_summary is None
    assert fake.calls == 2


def test_failed_end_keeps_workout_last_summary_and_pending_summary() -> None:
    counter = ExerciseCounter()
    session = WorkoutSession()
    session.start(counter, 100.0)
    fake = SequencedApiClient([WorkoutConnectionError("offline")])
    uploader = WorkoutUploader(fake)  # type: ignore[arg-type]

    handle_keyboard_input(ord("E"), counter, session, uploader, 115.0)

    assert session.last_summary is not None
    assert uploader.pending_summary == session.last_summary
    assert uploader.cloud_status == "FAILED"
