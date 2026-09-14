"""Run authenticated smoke tests against a running Workout API."""

from __future__ import annotations

import argparse
import base64
import binascii
from datetime import date, datetime, time, timedelta, timezone
from getpass import getpass
import json
import os
from pathlib import Path
import sys
import time as system_time
from typing import Any
from urllib.parse import urlparse

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import get_settings


KOREA_TIMEZONE = timezone(timedelta(hours=9))
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("FITROUTE_API_BASE_URL", DEFAULT_API_BASE_URL),
        help=(
            "Workout API base URL. CLI value overrides FITROUTE_API_BASE_URL "
            f"(default: {DEFAULT_API_BASE_URL})."
        ),
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=datetime.now(KOREA_TIMEZONE).date(),
        help="Workout date in YYYY-MM-DD format (default: today in Korea)",
    )
    parser.add_argument(
        "--one-session",
        action="store_true",
        help="Post only the first sample instead of both accumulation samples",
    )
    return parser.parse_args(argv)


def sample_payloads(workout_date: date) -> list[dict[str, Any]]:
    first_start = datetime.combine(workout_date, time(16, 30), KOREA_TIMEZONE)
    second_start = datetime.combine(workout_date, time(16, 45), KOREA_TIMEZONE)
    return [
        {
            "workout_date": workout_date.isoformat(),
            "started_at": first_start.isoformat(),
            "ended_at": (first_start + timedelta(minutes=10)).isoformat(),
            "workout_seconds": 600.0,
            "squat_count": 20,
            "stretch_seconds": 120.0,
        },
        {
            "workout_date": workout_date.isoformat(),
            "started_at": second_start.isoformat(),
            "ended_at": (second_start + timedelta(minutes=4)).isoformat(),
            "workout_seconds": 240.0,
            "squat_count": 15,
            "stretch_seconds": 90.0,
        },
    ]


def show(label: str, response: httpx.Response) -> Any:
    print(f"\n[{response.request.method}] {label}: {response.status_code}")
    try:
        body = response.json()
    except ValueError:
        body = response.text
    print(body)
    response.raise_for_status()
    return body


def normalize_and_validate_token(raw_token: str) -> str:
    token = raw_token.strip().strip('"').strip("'")
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if token.startswith(("sb_publishable_", "sb_secret_")):
        raise ValueError(
            "This is a Supabase API key, not a logged-in user's Access Token."
        )

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("The Access Token must be a three-part JWT.")
    try:
        encoded_payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(encoded_payload))
    except (binascii.Error, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("The Access Token contains an invalid JWT payload.") from exc

    if claims.get("role") != "authenticated" or not claims.get("sub"):
        raise ValueError(
            "This JWT is not a logged-in user's token (role=authenticated is required)."
        )
    expires_at = claims.get("exp")
    if not isinstance(expires_at, (int, float)):
        raise ValueError("The Access Token has no valid expiration time.")
    if expires_at <= system_time.time():
        expired_at = datetime.fromtimestamp(expires_at, timezone.utc).isoformat()
        raise ValueError(f"The Access Token expired at {expired_at}.")

    issuer_host = urlparse(str(claims.get("iss", ""))).hostname
    project_host = urlparse(get_settings().supabase_url).hostname
    if issuer_host and project_host and issuer_host != project_host:
        raise ValueError(
            "The Access Token belongs to a different Supabase project than backend/.env."
        )
    return token


def main() -> int:
    args = parse_args()
    raw_token = getpass("Supabase Access Token (hidden): ")
    if not raw_token.strip():
        print("Access token is required.")
        return 2
    try:
        token = normalize_and_validate_token(raw_token)
    except ValueError as exc:
        print(f"Access token rejected before API call: {exc}")
        return 2

    base_url = args.base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    workout_date = args.date
    payloads = sample_payloads(workout_date)
    if args.one_session:
        payloads = payloads[:1]

    try:
        with httpx.Client(base_url=base_url, headers=headers, timeout=15) as client:
            show("/health", client.get("/health"))
            before = show(
                f"/api/workouts/daily/{workout_date}",
                client.get(f"/api/workouts/daily/{workout_date}"),
            )

            for index, payload in enumerate(payloads, start=1):
                show(
                    f"/api/workouts (sample {index})",
                    client.post("/api/workouts", json=payload),
                )

            after = show(
                f"/api/workouts/daily/{workout_date}",
                client.get(f"/api/workouts/daily/{workout_date}"),
            )
            sessions = show(
                f"/api/workouts/sessions/{workout_date}",
                client.get(f"/api/workouts/sessions/{workout_date}"),
            )
            show(
                "/api/workouts/daily",
                client.get(
                    "/api/workouts/daily",
                    params={"start_date": workout_date, "end_date": workout_date},
                ),
            )
            if workout_date == datetime.now(KOREA_TIMEZONE).date():
                show("/api/workouts/today", client.get("/api/workouts/today"))

        expected = {
            "squat_count": sum(item["squat_count"] for item in payloads),
            "stretch_seconds": sum(item["stretch_seconds"] for item in payloads),
            "workout_seconds": sum(item["workout_seconds"] for item in payloads),
            "session_count": len(payloads),
        }
        deltas = {key: after[key] - before[key] for key in expected}
        if deltas != expected:
            print(f"\nFAILED: expected summary delta {expected}, got {deltas}")
            return 1
        if len(sessions) < after["session_count"]:
            print("\nFAILED: session list is shorter than the daily session count.")
            return 1
        print(f"\nPASS: atomic summary delta is correct: {deltas}")
        return 0
    except httpx.HTTPError as exc:
        print(f"\nAPI test failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
