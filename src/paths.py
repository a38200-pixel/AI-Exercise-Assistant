"""개발 실행과 frozen 실행에서 공통으로 사용하는 resource 경로."""

import sys
from pathlib import Path


def get_app_root() -> Path:
    """Repository 또는 설치된 AI Client의 최상위 경로를 반환한다."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_model_path(*relative_parts: str) -> Path:
    """애플리케이션 root 옆 models 디렉터리의 경로를 반환한다."""
    return get_app_root().joinpath("models", *relative_parts)
