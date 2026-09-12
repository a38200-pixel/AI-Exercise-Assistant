"""요청 단위 Supabase client 생성 함수."""

from typing import Any

from backend.app.core.config import Settings


def create_supabase_client(settings: Settings) -> Any:
    """인증 상태를 공유하지 않는 새 anon client를 생성한다."""
    from supabase import create_client
    from supabase.client import ClientOptions

    options = ClientOptions(
        auto_refresh_token=False,
        persist_session=False,
    )
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=options,
    )


def create_user_supabase_client(access_token: str, settings: Settings) -> Any:
    """사용자 JWT가 RLS의 auth.uid()로 전달되는 request 전용 client를 만든다."""
    client = create_supabase_client(settings)
    client.postgrest.auth(access_token)
    return client

