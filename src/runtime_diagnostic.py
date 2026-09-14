"""Safe frozen-runtime diagnostics that never open the camera or network."""

from __future__ import annotations

import sys

from config.settings import (
    CLASSES_PATH,
    POSE_MODEL_PATH,
    PROJECT_ROOT,
    XGBOOST_MODEL_PATH,
    YOLO_ENGINE_PATH,
)


MODEL_PATHS = (
    YOLO_ENGINE_PATH,
    POSE_MODEL_PATH,
    XGBOOST_MODEL_PATH,
    CLASSES_PATH,
)


def run_runtime_diagnostic() -> int:
    """Validate packaged imports and resources without inference or I/O writes."""
    failures: list[str] = []
    print(f"Frozen: {'YES' if getattr(sys, 'frozen', False) else 'NO'}")
    print(f"App root: {PROJECT_ROOT}")

    for model_path in MODEL_PATHS:
        exists = model_path.is_file()
        print(f"Model: {model_path} ({'OK' if exists else 'MISSING'})")
        if not exists:
            failures.append(f"missing model resource: {model_path}")

    try:
        import cv2

        gui_ok = callable(getattr(cv2, "imshow", None))
        msmf_ok = hasattr(cv2, "CAP_MSMF")
        print(
            f"OpenCV: {'OK' if gui_ok and msmf_ok else 'FAIL'} "
            f"({cv2.__version__}, GUI={gui_ok}, MSMF={msmf_ok})"
        )
        if not gui_ok or not msmf_ok:
            failures.append("OpenCV GUI or MSMF support is unavailable")
    except Exception as exc:  # pragma: no cover - only in a broken bundle
        print(f"OpenCV: FAIL ({exc})")
        failures.append(f"OpenCV import failed: {exc}")

    try:
        import torch

        cuda_ok = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "NONE"
        print(
            f"CUDA: {'OK' if cuda_ok else 'FAIL'} "
            f"({torch.version.cuda}, {gpu_name})"
        )
        if not cuda_ok:
            failures.append("torch.cuda.is_available() is False")
    except Exception as exc:  # pragma: no cover - only in a broken bundle
        print(f"CUDA: FAIL ({exc})")
        failures.append(f"PyTorch import failed: {exc}")

    import_checks = (
        ("TensorRT", "import tensorrt as module"),
        (
            "MediaPipe",
            "import mediapipe as module; "
            "from mediapipe.tasks import python; "
            "from mediapipe.tasks.python import vision",
        ),
        ("Ultralytics", "import ultralytics as module; from ultralytics import YOLO"),
        ("HTTPX", "import httpx as module"),
    )
    for label, statement in import_checks:
        namespace: dict[str, object] = {}
        try:
            exec(statement, namespace)
            module = namespace["module"]
            module_version = getattr(module, "__version__", "unknown")
            print(f"{label}: OK ({module_version})")
        except Exception as exc:  # pragma: no cover - only in a broken bundle
            print(f"{label}: FAIL ({exc})")
            failures.append(f"{label} import failed: {exc}")

    try:
        from src.pose_classifier import PoseClassifier

        classifier = PoseClassifier()
        print(
            "XGBoost: OK "
            f"({len(classifier.classes)} classes, "
            f"{classifier.model.get_booster().num_features()} features)"
        )
    except Exception as exc:  # pragma: no cover - only in a broken bundle
        print(f"XGBoost: FAIL ({exc})")
        failures.append(f"XGBoost model load failed: {exc}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("RUNTIME DIAGNOSTIC FAIL")
        return 1

    print("RUNTIME DIAGNOSTIC PASS")
    return 0
