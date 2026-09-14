"""Camera-free tests for runtime diagnostic CLI dispatch."""

import sys

import src.main as main_module


def test_parse_runtime_diagnostic_flag() -> None:
    arguments = main_module.parse_arguments(["--diagnose-runtime"])

    assert arguments.diagnose_runtime is True
    assert arguments.auto_start_session is False


def test_main_dispatches_diagnostic_before_camera(
    monkeypatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--diagnose-runtime"])
    monkeypatch.setattr(main_module, "run_runtime_diagnostic", lambda: 17)

    class CameraMustNotBeCreated:
        def __init__(self) -> None:
            raise AssertionError("Camera was created during runtime diagnostics")

    monkeypatch.setattr(main_module, "Camera", CameraMustNotBeCreated)

    assert main_module.main() == 17
