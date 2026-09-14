"""Registry와 Camera를 실행하지 않고 Desktop Launcher 경계를 검증한다."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from desktop_launcher.launcher import (
    LaunchRequest,
    LauncherConfig,
    LauncherError,
    build_ai_command,
    launch_ai_client,
    parse_launch_url,
    resolve_entry_script,
)
from desktop_launcher.register_protocol import protocol_command


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
    project_root = Path("C:/FitRoute/project")
    return LauncherConfig(
        python_executable=Path("C:/FitRoute/vision_ai/python.exe"),
        project_root=project_root,
        entry_script=project_root / "src/main.py",
    )


def test_command_is_an_argument_list_and_never_uses_shell() -> None:
    config = fake_config()
    request = parse_launch_url("fitroute://start?exercise=squat")
    process = Mock()
    process.wait.return_value = 0
    popen = Mock(return_value=process)
    mutex = Mock()
    mutex.acquire.return_value = True

    assert launch_ai_client(config, request, popen_factory=popen, mutex=mutex) == 0
    command = build_ai_command(config, request)
    assert command == [str(config.python_executable), str(config.entry_script), "--exercise", "squat"]
    popen.assert_called_once_with(command, cwd=str(config.project_root), shell=False)
    mutex.release.assert_called_once_with()


def test_existing_camera_mutex_prevents_duplicate_process() -> None:
    mutex = Mock()
    mutex.acquire.return_value = False
    popen = Mock()

    assert launch_ai_client(
        fake_config(),
        LaunchRequest("start", "squat"),
        popen_factory=popen,
        mutex=mutex,
    ) == 0
    popen.assert_not_called()


def test_config_cannot_escape_project_root() -> None:
    project_root = Path("C:/FitRoute/project").resolve()
    with pytest.raises(LauncherError, match="inside project_root"):
        resolve_entry_script(project_root, Path("../outside.py"))


def test_registry_command_quotes_executable_and_url_placeholder() -> None:
    launcher = Path("C:/FitRoute/FitRoute Launcher.exe")
    assert protocol_command(launcher) == f'"{launcher.resolve()}" "%1"'
