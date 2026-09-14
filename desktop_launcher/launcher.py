"""Validate a fitroute:// URL and launch the existing AI client safely."""

from __future__ import annotations

import argparse
import base64
import binascii
import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit


class _NullStream:
    """Minimal text stream for PyInstaller's noconsole mode."""

    encoding = "utf-8"

    def write(self, value: str) -> int:
        return len(value)

    def flush(self) -> None:
        return None


if sys.stdout is None:
    sys.stdout = _NullStream()  # type: ignore[assignment]
if sys.stderr is None:
    sys.stderr = _NullStream()  # type: ignore[assignment]


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desktop_launcher.desktop_auth import (
    CredentialStoreError,
    SupabaseDesktopAuth,
    WindowsCredentialStore,
    acquire_access_token,
    logout_desktop,
    show_login_dialog,
)


PROTOCOL_SCHEME = "fitroute"
ALLOWED_COMMANDS = frozenset({"start"})
ALLOWED_EXERCISES = frozenset({"squat"})
MUTEX_NAME = "Local\\FitRouteAIClientCamera"
ERROR_ALREADY_EXISTS = 183


class LauncherError(ValueError):
    """안전하게 사용자에게 설명할 수 있는 Launcher 오류."""


def log_launcher_event(message: str) -> None:
    """Write non-sensitive lifecycle events beside the launcher."""
    line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}"
    try:
        with (launcher_root() / "launcher.log").open("a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except OSError:
        pass
    if sys.stdout is not None:
        print(message)


@dataclass(frozen=True)
class LaunchRequest:
    command: str
    exercise: str


@dataclass(frozen=True)
class LauncherConfig:
    ai_client_executable: Path
    api_base_url: str
    supabase_url: str
    supabase_anon_key: str


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


def launcher_root() -> Path:
    """Return the directory that contains the frozen launcher or source launcher."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def default_config_path() -> Path:
    return launcher_root() / "config.json"


def resolve_ai_client_executable(value: object, *, base_dir: Path | None = None) -> Path:
    """Resolve an explicit path or an install-relative AI Client path."""
    raw_path = str(value).strip()
    if not raw_path:
        raise LauncherError("ai_client_executable is missing.")
    executable = Path(os.path.expandvars(raw_path)).expanduser()
    if not executable.is_absolute():
        executable = (base_dir or launcher_root()) / executable
    return executable.resolve()


def validate_service_url(value: object, field_name: str, *, https_only: bool = False) -> str:
    url = str(value).strip().rstrip("/")
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise LauncherError(f"{field_name} is invalid.") from exc
    allowed_schemes = {"https"} if https_only else {"http", "https"}
    if (
        parsed.scheme not in allowed_schemes
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise LauncherError(f"{field_name} is invalid.")
    return url


def validate_supabase_anon_key(value: object) -> str:
    key = str(value).strip()
    if not key:
        raise LauncherError("supabase_anon_key is missing.")
    if key.startswith("sb_secret_"):
        raise LauncherError("A Supabase service role/secret key is not allowed.")

    # Legacy JWT anon/service_role keys는 payload의 role만 확인해 잘못된 설정을 차단한다.
    parts = key.split(".")
    if len(parts) == 3:
        try:
            payload_bytes = base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
            payload = {}
        if payload.get("role") == "service_role":
            raise LauncherError("A Supabase service role/secret key is not allowed.")
    return key


def load_config(config_path: Path) -> LauncherConfig:
    """설치 시 생성된 trusted local config를 읽고 실행 경계를 검증한다."""
    try:
        raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8-sig"))
        ai_client_executable = resolve_ai_client_executable(raw["ai_client_executable"])
        api_base_url = validate_service_url(raw["api_base_url"], "api_base_url")
        supabase_url = validate_service_url(raw["supabase_url"], "supabase_url", https_only=True)
        supabase_anon_key = validate_supabase_anon_key(raw["supabase_anon_key"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise LauncherError("Launcher config is missing or invalid.") from exc

    if not ai_client_executable.is_file():
        raise LauncherError("FitRoute AI Client executable was not found.")
    return LauncherConfig(
        ai_client_executable,
        api_base_url,
        supabase_url,
        supabase_anon_key,
    )


def build_ai_command(
    config: LauncherConfig,
    request: LaunchRequest,
    *,
    auto_start_session: bool = False,
) -> list[str]:
    """사용자 URL 문자열을 조합하지 않고 검증된 값만 argument list로 만든다."""
    if request.command != "start" or request.exercise not in ALLOWED_EXERCISES:
        raise LauncherError("Launch request was not accepted.")
    command = [
        str(config.ai_client_executable),
        "--exercise",
        request.exercise,
    ]
    if auto_start_session:
        command.append("--auto-start-session")
    return command


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
    access_token_provider: Callable[[], str | None],
    popen_factory: Callable[..., Any] | None = None,
    mutex: WindowsNamedMutex | None = None,
) -> int:
    """중복을 막고 인증한 뒤 token을 child environment에만 넣어 실행한다."""
    active_mutex = mutex or WindowsNamedMutex()
    if not active_mutex.acquire():
        return 0

    try:
        access_token = access_token_provider()
        if not access_token:
            return 0
        command = build_ai_command(config, request, auto_start_session=True)
        child_environment = os.environ.copy()
        child_environment["FITROUTE_ACCESS_TOKEN"] = access_token
        child_environment["FITROUTE_API_BASE_URL"] = config.api_base_url
        process_factory = popen_factory or subprocess.Popen
        log_launcher_event("Desktop auth success.")
        log_launcher_event(f"AI Client executable resolved: {config.ai_client_executable}")
        log_launcher_event("AI Client executable exists: YES")
        log_launcher_event("Access token present: YES")
        log_launcher_event("API base URL present: YES")
        log_launcher_event("Launching frozen AI client.")
        log_launcher_event("Auto start session: YES")
        process = process_factory(
            command,
            cwd=str(config.ai_client_executable.parent),
            env=child_environment,
            shell=False,
        )
        if getattr(process, "pid", None) is not None:
            log_launcher_event(f"Child process PID: {process.pid}")
        exit_code = int(process.wait())
        log_launcher_event(f"Child exit code: {exit_code}")
        return exit_code
    finally:
        active_mutex.release()


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", help="Validated fitroute:// URL supplied by Windows")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the argument list without launching the camera")
    parser.add_argument("--logout", action="store_true", help="Remove the saved Desktop refresh credential")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        log_launcher_event("Launcher started.")
        if arguments.logout:
            logout_desktop(WindowsCredentialStore())
            return 0
        if not arguments.url:
            raise LauncherError("A fitroute:// URL is required.")
        request = parse_launch_url(arguments.url)
        log_launcher_event("Protocol validated.")
        config = load_config((arguments.config or default_config_path()).resolve())
        if arguments.dry_run:
            print(json.dumps(build_ai_command(config, request, auto_start_session=True), ensure_ascii=False))
            return 0
        desktop_auth = SupabaseDesktopAuth(config.supabase_url, config.supabase_anon_key)
        credential_store = WindowsCredentialStore()
        return launch_ai_client(
            config,
            request,
            access_token_provider=lambda: acquire_access_token(
                desktop_auth,
                credential_store,
                show_login_dialog,
            ),
        )
    except (LauncherError, CredentialStoreError, OSError, subprocess.SubprocessError) as exc:
        print(f"FitRoute Launcher: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
