"""AI Client의 개발/frozen resource 경로를 검증한다."""

from pathlib import Path
import sys

import config.settings as settings
import src.paths as paths


def test_development_app_root_is_repository_root(monkeypatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)

    expected_root = Path(paths.__file__).resolve().parents[1]
    assert paths.get_app_root() == expected_root


def test_frozen_app_root_uses_executable_directory(monkeypatch) -> None:
    executable = Path("C:/Program Files/FitRoute/FitRouteAIClient.exe")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert paths.get_app_root() == executable.parent.resolve()


def test_all_frozen_model_paths_are_beside_executable(monkeypatch) -> None:
    app_root = Path("C:/Program Files/FitRoute").resolve()
    monkeypatch.setattr(paths, "get_app_root", lambda: app_root)

    assert paths.get_model_path("detector", "yolo26n.engine") == (
        app_root / "models" / "detector" / "yolo26n.engine"
    )
    assert paths.get_model_path("pose", "pose_landmarker_full.task") == (
        app_root / "models" / "pose" / "pose_landmarker_full.task"
    )
    assert paths.get_model_path("classifier", "model_weights.xgb") == (
        app_root / "models" / "classifier" / "model_weights.xgb"
    )
    assert paths.get_model_path("classifier", "classes.json") == (
        app_root / "models" / "classifier" / "classes.json"
    )


def test_development_model_files_exist_at_configured_paths() -> None:
    expected_paths = {
        settings.YOLO_ENGINE_PATH: ("detector", "yolo26n.engine"),
        settings.POSE_MODEL_PATH: ("pose", "pose_landmarker_full.task"),
        settings.XGBOOST_MODEL_PATH: ("classifier", "model_weights.xgb"),
        settings.CLASSES_PATH: ("classifier", "classes.json"),
    }

    for model_path, relative_parts in expected_paths.items():
        assert model_path == settings.MODEL_DIR.joinpath(*relative_parts)
        assert model_path.is_file()
