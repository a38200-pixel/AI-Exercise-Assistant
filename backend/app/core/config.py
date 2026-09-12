"""환경변수에서 Backend 설정을 읽는다."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = Field(min_length=1)
    supabase_anon_key: str = Field(min_length=1)
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """프로세스 설정은 캐시하되 사용자 인증 상태는 포함하지 않는다."""
    return Settings()

