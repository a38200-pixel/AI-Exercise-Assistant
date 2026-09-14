"""Registry와 Camera를 실행하지 않고 Desktop Launcher 경계를 검증한다."""

import base64
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from desktop_launcher.launcher import (
    LaunchRequest,
    LauncherConfig,
    LauncherError,
    build_ai_command,
    launch_ai_client,
    load_config,
    launcher_root,
    parse_launch_url,
    resolve_ai_client_executable,
    validate_supabase_anon_key,
)
from desktop_launcher.register_protocol import protocol_command


@pytest.fixture(autouse=True)
def disable_launcher_file_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("desktop_launcher.launcher.log_launcher_event", lambda _message: None)


def test_valid_squat_protocol_is_accepted() -> None:
    assert parse_launch_url("fitroute://start?exercise=squat") == LaunchRequest("start", "squat")


@pytest.mark.parametrize(
    "url",
    (
        "fitroute://start?exercise=burpee",
        "fitroute://start?exercise=../../calc.exe",
        "fitroute://evil?command=start&exercise=squat",
        "fitroute://start/path?exercise=squat",
        "fitroute://start?exercise=squat&extra=value",
        "https://start?exercise=squat",
        "not-a-url",
    ),
)
def test_untrusted_protocol_inputs_are_rejected(url: str) -> None:
    with pytest.raises(LauncherError):
        parse_launch_url(url)


def fake_config() -> LauncherConfig:
    return LauncherConfig(
        ai_client_executable=Path("C:/FitRoute/ai_client/FitRouteAIClient.exe"),
        api_base_url="https://fitroute-api.onrender.com",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="publishable-key",
    )


def test_command_is_an_argument_list_and_never_uses_shell() -> None:
    config = fake_config()
    request = parse_launch_url("fitroute://start?exercise=squat")
    process = Mock()
    process.wait.return_value = 0
    popen = Mock(return_value=process)
    token_provider = Mock(return_value="current-access-token")
    mutex = Mock()
    mutex.acquire.return_value = True

    assert launch_ai_client(
        config,
        request,
        access_token_provider=token_provider,
        popen_factory=popen,
        mutex=mutex,
    ) == 0
    command = build_ai_command(config, request, auto_start_session=True)
    assert command == [
        str(config.ai_client_executable),
        "--exercise",
        "squat",
        "--auto-start-session",
    ]
    child_environment = popen.call_args.kwargs["env"]
    assert "current-access-token" not in command
    assert child_environment["FITROUTE_ACCESS_TOKEN"] == "current-access-token"
    assert child_environment["FITROUTE_API_BASE_URL"] == config.api_base_url
    assert popen.call_args.args == (command,)
    assert popen.call_args.kwargs["cwd"] == str(config.ai_client_executable.parent)
    assert popen.call_args.kwargs["shell"] is False
    token_provider.assert_called_once_with()
    mutex.release.assert_called_once_with()


def test_existing_camera_mutex_prevents_duplicate_process() -> None:
    mutex = Mock()
    mutex.acquire.return_value = False
    popen = Mock()
    token_provider = Mock(return_value="token")

    assert launch_ai_client(
        fake_config(),
        LaunchRequest("start", "squat"),
        access_token_provider=token_provider,
        popen_factory=popen,
        mutex=mutex,
    ) == 0
    popen.assert_not_called()
    token_provider.assert_not_called()


def test_canceled_login_does_not_launch_client() -> None:
    mutex = Mock()
    mutex.acquire.return_value = True
    popen = Mock()

    assert launch_ai_client(
        fake_config(),
        LaunchRequest("start", "squat"),
        access_token_provider=Mock(return_value=None),
        popen_factory=popen,
        mutex=mutex,
    ) == 0
    popen.assert_not_called()
    mutex.release.assert_called_once_with()


def test_relative_ai_client_path_uses_launcher_root() -> None:
    launcher_dir = Path("C:/FitRoute")
    assert resolve_ai_client_executable(
        Path("ai_client/FitRouteAIClient.exe"),
        base_dir=launcher_dir,
    ) == (launcher_dir / "ai_client/FitRouteAIClient.exe").resolve()


def test_explicit_ai_client_path_is_supported() -> None:
    executable = Path("D:/FitRouteBuild/FitRouteAIClient.exe")
    assert resolve_ai_client_executable(executable, base_dir=Path("C:/FitRoute")) == executable.resolve()


def test_frozen_launcher_root_uses_executable_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("desktop_launcher.launcher.sys.frozen", True, raising=False)
    monkeypatch.setattr("desktop_launcher.launcher.sys.executable", "C:/FitRoute/FitRouteLauncher.exe")
    assert launcher_root() == Path("C:/FitRoute").resolve()


def test_missing_ai_client_executable_fails_without_python_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_json = json.dumps(
        {
            "ai_client_executable": "ai_client/FitRouteAIClient.exe",
            "api_base_url": "https://fitroute-api.onrender.com",
            "supabase_url": "https://project.supabase.co",
            "supabase_anon_key": "publishable-key",
        }
    )
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: config_json)
    monkeypatch.setattr(Path, "is_file", lambda _self: False)
    monkeypatch.setattr("desktop_launcher.launcher.launcher_root", lambda: Path("C:/FitRoute"))
    with pytest.raises(LauncherError, match="executable was not found"):
        load_config(Path("C:/FitRoute/config.json"))


def test_config_loads_existing_relative_ai_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher_dir = Path("C:/FitRoute")
    ai_client = launcher_dir / "ai_client" / "FitRouteAIClient.exe"
    config_json = json.dumps(
        {
            "ai_client_executable": "ai_client/FitRouteAIClient.exe",
            "api_base_url": "https://fitroute-api.onrender.com/",
            "supabase_url": "https://project.supabase.co",
            "supabase_anon_key": "publishable-key",
        }
    )
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: config_json)
    monkeypatch.setattr(Path, "is_file", lambda _self: True)
    monkeypatch.setattr("desktop_launcher.launcher.launcher_root", lambda: launcher_dir)

    config = load_config(launcher_dir / "config.json")

    assert config.ai_client_executable == ai_client.resolve()
    assert config.api_base_url == "https://fitroute-api.onrender.com"


def test_registry_command_quotes_executable_and_url_placeholder() -> None:
    launcher = Path("C:/FitRoute/FitRoute Launcher.exe")
    assert protocol_command(launcher) == f'"{launcher.resolve()}" "%1"'


@pytest.mark.parametrize("key", ("sb_secret_not-allowed", ""))
def test_service_role_or_empty_supabase_key_is_rejected(key: str) -> None:
    with pytest.raises(LauncherError):
        validate_supabase_anon_key(key)


def test_publishable_supabase_key_is_accepted() -> None:
    assert validate_supabase_anon_key("sb_publishable_example") == "sb_publishable_example"


def test_legacy_service_role_jwt_is_rejected() -> None:
    payload = base64.urlsafe_b64encode(json.dumps({"role": "service_role"}).encode()).decode().rstrip("=")
    with pytest.raises(LauncherError):
        validate_supabase_anon_key(f"header.{payload}.signature")
