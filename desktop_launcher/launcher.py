"""Validate a fitroute:// URL and launch the existing AI client safely."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit


PROTOCOL_SCHEME = "fitroute"
ALLOWED_COMMANDS = frozenset({"start"})
ALLOWED_EXERCISES = frozenset({"squat"})
MUTEX_NAME = "Local\\FitRouteAIClientCamera"
ERROR_ALREADY_EXISTS = 183


class LauncherError(ValueError):
    """안전하게 사용자에게 설명할 수 있는 Launcher 오류."""


@dataclass(frozen=True)
class LaunchRequest:
    command: str
    exercise: str


@dataclass(frozen=True)
class LauncherConfig:
    python_executable: Path
    project_root: Path
    entry_script: Path


def parse_launch_url(url: str) -> LaunchRequest:
    """Custom URL을 고정된 command/exercise whitelist로 검증한다."""
    if not isinstance(url, str) or not url or len(url) > 512:
        raise LauncherError("Invalid FitRoute URL.")

    try:
        parsed = urlsplit(url)
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise LauncherError("Invalid FitRoute URL.") from exc

    command = parsed.netloc.lower()
    if parsed.scheme.lower() != PROTOCOL_SCHEME:
        raise LauncherError("Unsupported protocol.")
    if command not in ALLOWED_COMMANDS or parsed.path not in ("", "/"):
        raise LauncherError("Unsupported FitRoute command.")
    if parsed.fragment or set(query) != {"exercise"} or len(query["exercise"]) != 1:
        raise LauncherError("Invalid FitRoute parameters.")

    exercise = query["exercise"][0].lower()
    if exercise not in ALLOWED_EXERCISES:
        raise LauncherError("Unsupported exercise.")
    return LaunchRequest(command=command, exercise=exercise)


def default_config_path() -> Path:
    base_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return base_dir / "config.json"


def resolve_entry_script(project_root: Path, entry_value: Path) -> Path:
    if entry_value.is_absolute():
        raise LauncherError("entry_script must be relative to project_root.")
    entry_script = (project_root / entry_value).resolve()
    try:
        entry_script.relative_to(project_root)
    except ValueError as exc:
        raise LauncherError("entry_script must stay inside project_root.") from exc
    return entry_script


def load_config(config_path: Path) -> LauncherConfig:
    """설치 시 생성된 trusted local config를 읽고 실행 경계를 검증한다."""
    try:
        raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8-sig"))
        python_executable = Path(os.path.expandvars(str(raw["python_executable"]))).expanduser().resolve()
        project_root = Path(os.path.expandvars(str(raw["project_root"]))).expanduser().resolve()
        entry_value = Path(str(raw.get("entry_script", "src/main.py")))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise LauncherError("Launcher config is missing or invalid.") from exc

    entry_script = resolve_entry_script(project_root, entry_value)

    if not python_executable.is_file():
        raise LauncherError("Configured Python executable was not found.")
    if not project_root.is_dir() or not entry_script.is_file():
        raise LauncherError("Configured FitRoute project was not found.")
    return LauncherConfig(python_executable, project_root, entry_script)


def build_ai_command(config: LauncherConfig, request: LaunchRequest) -> list[str]:
    """사용자 URL 문자열을 조합하지 않고 검증된 값만 argument list로 만든다."""
    if request.command != "start" or request.exercise not in ALLOWED_EXERCISES:
        raise LauncherError("Launch request was not accepted.")
    return [
        str(config.python_executable),
        str(config.entry_script),
        "--exercise",
        request.exercise,
    ]


class WindowsNamedMutex:
    """Launcher가 AI process 종료까지 보유하는 Current User named mutex."""

    def __init__(self, name: str = MUTEX_NAME) -> None:
        self.name = name
        self.handle: int | None = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        kernel32 = ctypes.windll.kernel32
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        create_mutex.restype = wintypes.HANDLE
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        handle = create_mutex(None, False, self.name)
        if not handle:
            raise OSError("Could not create FitRoute launcher mutex.")
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            close_handle(handle)
            return False
        self.handle = handle
        return True

    def release(self) -> None:
        if os.name == "nt" and self.handle is not None:
            close_handle = ctypes.windll.kernel32.CloseHandle
            close_handle.argtypes = (wintypes.HANDLE,)
            close_handle.restype = wintypes.BOOL
            close_handle(self.handle)
            self.handle = None


def launch_ai_client(
    config: LauncherConfig,
    request: LaunchRequest,
    *,
    popen_factory: Callable[..., Any] | None = None,
    mutex: WindowsNamedMutex | None = None,
) -> int:
    """shell 없이 AI client를 실행하고 종료까지 mutex를 유지한다."""
    active_mutex = mutex or WindowsNamedMutex()
    if not active_mutex.acquire():
        return 0

    try:
        command = build_ai_command(config, request)
        process_factory = popen_factory or subprocess.Popen
        process = process_factory(
            command,
            cwd=str(config.project_root),
            shell=False,
        )
        return int(process.wait())
    finally:
        active_mutex.release()


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Validated fitroute:// URL supplied by Windows")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the argument list without launching the camera")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        request = parse_launch_url(arguments.url)
        config = load_config((arguments.config or default_config_path()).resolve())
        if arguments.dry_run:
            print(json.dumps(build_ai_command(config, request), ensure_ascii=False))
            return 0
        return launch_ai_client(config, request)
    except (LauncherError, OSError, subprocess.SubprocessError) as exc:
        print(f"FitRoute Launcher: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
