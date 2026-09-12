"""Tests for safe access-token preflight checks in the integration script."""

from __future__ import annotations

import base64
import json
import time
import unittest

from backend.app.core.config import get_settings
from backend.scripts.test_workout_api import normalize_and_validate_token


def encode_segment(value: dict) -> str:
    raw = json.dumps(value).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def token_with(**overrides: object) -> str:
    claims = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "role": "authenticated",
        "exp": time.time() + 3600,
        "iss": get_settings().supabase_url.rstrip("/") + "/auth/v1",
    }
    claims.update(overrides)
    return f"{encode_segment({'alg': 'RS256'})}.{encode_segment(claims)}.signature"


class WorkoutTestScriptTokenTests(unittest.TestCase):
    def test_accepts_user_token_and_removes_bearer_prefix(self) -> None:
        token = token_with()
        self.assertEqual(normalize_and_validate_token(f"Bearer {token}"), token)

    def test_rejects_publishable_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "API key"):
            normalize_and_validate_token("sb_publishable_example")

    def test_rejects_expired_token(self) -> None:
        with self.assertRaisesRegex(ValueError, "expired"):
            normalize_and_validate_token(token_with(exp=time.time() - 1))

    def test_rejects_non_user_jwt(self) -> None:
        with self.assertRaisesRegex(ValueError, "logged-in user's token"):
            normalize_and_validate_token(token_with(role="anon"))

    def test_rejects_token_from_another_project(self) -> None:
        with self.assertRaisesRegex(ValueError, "different Supabase project"):
            normalize_and_validate_token(
                token_with(iss="https://different.supabase.co/auth/v1")
            )


if __name__ == "__main__":
    unittest.main()
