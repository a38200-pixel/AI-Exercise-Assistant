"""Supabase Auth access token을 검증하는 FastAPI dependency."""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.config import Settings, get_settings
from backend.app.core.supabase_client import create_user_supabase_client


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    supabase: Any


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    """Bearer JWT를 Supabase에서 검증하고 사용자별 DB client를 반환한다."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = credentials.credentials
    try:
        # client는 요청마다 생성되므로 다른 사용자의 token과 섞이지 않는다.
        client = create_user_supabase_client(access_token, settings)
        auth_response = client.auth.get_user(access_token)
        user = auth_response.user
        if user is None:
            raise ValueError("Supabase returned no user.")
    except Exception as exc:
        # Token, key, 내부 Supabase 오류를 HTTP response에 노출하지 않는다.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return CurrentUser(
        id=str(user.id),
        email=getattr(user, "email", None),
        supabase=client,
    )

