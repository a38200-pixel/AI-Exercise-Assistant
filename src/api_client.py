"""Small synchronous HTTP client for uploading completed workout sessions."""

from __future__ import annotations

import os
from typing import Any, Mapping

import httpx


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 10.0


class WorkoutApiError(RuntimeError):
    """A safe, user-facing Workout API failure."""


class WorkoutAuthenticationError(WorkoutApiError):
    """The supplied user access token is invalid or expired."""


class WorkoutValidationError(WorkoutApiError):
    """The workout summary was rejected by API validation."""


class WorkoutServerError(WorkoutApiError):
    """The API returned an unexpected or server-side response."""


class WorkoutConnectionError(WorkoutApiError):
    """The API could not be reached before the timeout."""


class WorkoutApiClient:
    def __init__(
        self,
        base_url: str,
        access_token: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not access_token.strip():
            raise ValueError("access_token must not be empty")
        self.base_url = base_url.rstrip("/")
        self._access_token = access_token.strip()
        self.timeout = timeout

    def save_workout_session(self, summary: Mapping[str, Any]) -> str:
        """POST an unchanged WorkoutSession summary and return its session id."""
        try:
            response = httpx.post(
                f"{self.base_url}/api/workouts",
                headers={"Authorization": f"Bearer {self._access_token}"},
                json=dict(summary),
                timeout=self.timeout,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise WorkoutConnectionError("Could not connect to FitRoute API.") from exc
        except httpx.RequestError as exc:
            raise WorkoutConnectionError("Could not connect to FitRoute API.") from exc

        if response.status_code == 401:
            raise WorkoutAuthenticationError(
                "Authentication failed. Please refresh FITROUTE_ACCESS_TOKEN."
            )
        if response.status_code == 422:
            raise WorkoutValidationError("Workout data validation failed.")
        if response.status_code >= 500:
            raise WorkoutServerError("Workout API server error.")
        if response.status_code != 201:
            raise WorkoutServerError("Workout API returned an unexpected response.")

        try:
            session_id = response.json().get("id")
        except (ValueError, AttributeError) as exc:
            raise WorkoutServerError("Workout API returned an invalid response.") from exc
        if not isinstance(session_id, str) or not session_id:
            raise WorkoutServerError("Workout API returned no session id.")
        return session_id


def create_api_client_from_environment() -> WorkoutApiClient | None:
    """Create an enabled client without persisting or printing its access token."""
    access_token = os.getenv("FITROUTE_ACCESS_TOKEN", "").strip()
    if not access_token:
        return None
    base_url = os.getenv("FITROUTE_API_BASE_URL", DEFAULT_API_BASE_URL).strip()
    return WorkoutApiClient(base_url or DEFAULT_API_BASE_URL, access_token)


class WorkoutUploader:
    """Keep one failed summary pending until it is saved successfully."""

    def __init__(self, api_client: WorkoutApiClient | None) -> None:
        self.api_client = api_client
        self.pending_summary: dict[str, Any] | None = None
        self.last_saved_session_id: str | None = None
        self.cloud_status = "READY" if api_client is not None else "DISABLED"

    def submit(self, summary: Mapping[str, Any]) -> bool:
        if self.api_client is None:
            self.cloud_status = "DISABLED"
            print("[Cloud] Upload disabled. FITROUTE_ACCESS_TOKEN is not configured.")
            return False
        if self.pending_summary is not None:
            self.cloud_status = "FAILED"
            print("[Cloud] A previous workout is still pending. Press P to retry it first.")
            return False
        self.pending_summary = dict(summary)
        return self._upload_pending()

    def retry(self) -> bool:
        if self.pending_summary is None:
            print("[Cloud] No pending workout to save.")
            return False
        if self.api_client is None:
            self.cloud_status = "DISABLED"
            print("[Cloud] Upload disabled. FITROUTE_ACCESS_TOKEN is not configured.")
            return False
        print("[Cloud] Retrying previous workout save...")
        return self._upload_pending()

    def _upload_pending(self) -> bool:
        if self.pending_summary is None or self.api_client is None:
            return False
        self.cloud_status = "SAVING"
        print("[Cloud] Uploading workout...")
        try:
            session_id = self.api_client.save_workout_session(self.pending_summary)
        except WorkoutApiError as exc:
            self.cloud_status = "FAILED"
            print(f"[Cloud] {exc}")
            print("[Cloud] Workout session completed, but server save failed.")
            print("[Cloud] Press P to retry the previous workout save.")
            return False
        except Exception:
            self.cloud_status = "FAILED"
            print("[Cloud] Unexpected upload failure.")
            print("[Cloud] Workout session completed, but server save failed.")
            print("[Cloud] Press P to retry the previous workout save.")
            return False

        self.last_saved_session_id = session_id
        self.pending_summary = None
        self.cloud_status = "SAVED"
        print("[Cloud] Workout saved successfully.")
        print(f"[Cloud] Session ID: {session_id}")
        return True
