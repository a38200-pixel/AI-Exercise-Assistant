"""Production-oriented environment parsing tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


BASE_SETTINGS = {
    "supabase_url": "https://example.supabase.co",
    "supabase_anon_key": "publishable-key",
}


def test_frontend_origins_parse_comma_separated_values() -> None:
    settings = Settings(
        **BASE_SETTINGS,
        frontend_origins="http://localhost:5173, https://fitroute.example.com/",
        _env_file=None,
    )

    assert settings.frontend_origins == [
        "http://localhost:5173",
        "https://fitroute.example.com",
    ]


def test_legacy_frontend_origin_environment_variable_is_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRONTEND_ORIGINS", raising=False)
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173")

    settings = Settings(**BASE_SETTINGS, _env_file=None)

    assert settings.frontend_origins == ["http://127.0.0.1:5173"]


@pytest.mark.parametrize(
    "origin",
    ["*", "fitroute.example.com", "https://fitroute.example.com/dashboard"],
)
def test_unsafe_or_invalid_origins_are_rejected(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE_SETTINGS, frontend_origins=origin, _env_file=None)
