# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir specification for the FitRoute AI Client."""

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    copy_metadata,
)


APP_NAME = "FitRouteAIClient"
REPOSITORY_ROOT = Path(SPECPATH).resolve().parents[1]

model_datas = [
    (str(REPOSITORY_ROOT / "models" / "detector" / "yolo26n.engine"), "models/detector"),
    (
        str(REPOSITORY_ROOT / "models" / "pose" / "pose_landmarker_full.task"),
        "models/pose",
    ),
    (
        str(REPOSITORY_ROOT / "models" / "classifier" / "model_weights.xgb"),
        "models/classifier",
    ),
    (
        str(REPOSITORY_ROOT / "models" / "classifier" / "classes.json"),
        "models/classifier",
    ),
]

# MediaPipe loads this DLL via a package-relative importlib.resources path.
mediapipe_binaries = collect_dynamic_libs("mediapipe")
mediapipe_datas = [
    item
    for item in collect_data_files("mediapipe")
    if Path(item[0]).suffix.lower() not in {".dll", ".pyd"}
]

# XGBoost locates xgboost/lib/xgboost.dll dynamically; no bundled hook exists.
xgboost_binaries = collect_dynamic_libs("xgboost")
xgboost_datas = [
    item
    for item in collect_data_files("xgboost")
    if Path(item[0]).suffix.lower() not in {".dll", ".pyd"}
]

hiddenimports = [
    "certifi",
    "mediapipe.tasks",
    "mediapipe.tasks.python",
    "mediapipe.tasks.python.core",
    "mediapipe.tasks.python.core.base_options",
    "mediapipe.tasks.python.vision",
    "mediapipe.tasks.python.vision.core",
    "mediapipe.tasks.python.vision.core.vision_task_running_mode",
    "mediapipe.tasks.python.vision.pose_landmarker",
    "tensorrt",
    "tensorrt_bindings",
    "tensorrt_libs",
    "ultralytics.nn.backends.tensorrt",
    "xgboost",
    "xgboost.sklearn",
]

datas = model_datas + mediapipe_datas + xgboost_datas
for distribution_name in ("ultralytics", "mediapipe", "xgboost", "httpx"):
    datas += copy_metadata(distribution_name)

a = Analysis(
    [str(REPOSITORY_ROOT / "src" / "main.py")],
    pathex=[str(REPOSITORY_ROOT)],
    binaries=mediapipe_binaries + xgboost_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={"matplotlib": {"backends": "Agg"}},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt6",
        "pygame",
        "IPython",
        "jupyter",
        "black",
        "pytest",
        "tkinter",
        "_tkinter",
    ],
    noarchive=False,
    optimize=0,
)

# Binary dependency analysis can discover another TensorRT installation from
# the developer PATH and copy its DLLs to _internal's top level. Keep only the
# wheel-owned copies under tensorrt_libs; an isolated frozen diagnostic proved
# that these are sufficient and prevents a clean PC dependency on C:\TensorRT.
external_tensorrt_duplicates = {
    "nvinfer_11.dll",
    "nvinfer_plugin_11.dll",
    "nvonnxparser_11.dll",
}
a.binaries = [
    entry
    for entry in a.binaries
    if entry[0].lower() not in external_tensorrt_duplicates
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

# PyInstaller 6 places Analysis datas under _internal. Move only the external
# model tree beside the executable because src.paths intentionally resolves it
# from sys.executable.parent. All Python/native runtime remains in _internal.
dist_application = Path(DISTPATH).resolve() / APP_NAME
internal_models = dist_application / "_internal" / "models"
public_models = dist_application / "models"
if internal_models.is_dir():
    if public_models.exists():
        raise RuntimeError(f"Refusing to replace existing model tree: {public_models}")
    internal_models.replace(public_models)

expected_models = [
    public_models / "detector" / "yolo26n.engine",
    public_models / "pose" / "pose_landmarker_full.task",
    public_models / "classifier" / "model_weights.xgb",
    public_models / "classifier" / "classes.json",
]
missing_models = [str(path) for path in expected_models if not path.is_file()]
if missing_models:
    raise RuntimeError("Packaged model resource(s) missing: " + ", ".join(missing_models))
