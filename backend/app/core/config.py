"""환경변수에서 Backend 설정을 읽는다."""

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    supabase_url: str = Field(min_length=1)
    supabase_anon_key: str = Field(min_length=1)
    frontend_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        validation_alias=AliasChoices("FRONTEND_ORIGINS", "FRONTEND_ORIGIN"),
    )
    log_level: str = "info"

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def parse_frontend_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("frontend_origins")
    @classmethod
    def validate_frontend_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("At least one frontend origin is required.")
        normalized: list[str] = []
        for origin in origins:
            if origin == "*":
                raise ValueError("Wildcard CORS origins are not allowed.")
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(f"Invalid frontend origin: {origin}")
            clean_origin = f"{parsed.scheme}://{parsed.netloc}"
            if clean_origin not in normalized:
                normalized.append(clean_origin)
        return normalized


@lru_cache
def get_settings() -> Settings:
    """프로세스 설정은 캐시하되 사용자 인증 상태는 포함하지 않는다."""
    return Settings()
