"""개발 실행과 frozen 실행에서 공통으로 사용하는 resource 경로."""

import os
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


def get_workout_log_dir() -> Path:
    """로컬 운동 기록(세션별 JSON)을 저장하는 디렉터리.

    개발 실행은 저장소의 data/workout_logs/, 패키징(frozen) 실행은 설치 폴더(Program Files 등)에 쓸 수 없을 수 있으므로
    사용자별 %LOCALAPPDATA%/FitRoute/workout_logs를 쓴다. 디렉터리는 만들지 않는다(저장할 때 만든다).
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / "FitRoute" / "workout_logs"
    return get_app_root() / "data" / "workout_logs"
