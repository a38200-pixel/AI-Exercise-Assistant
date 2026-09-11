"""Print runtime package, CUDA, GPU, and expected model-file status."""

import importlib
import platform
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    CLASSES_PATH,
    POSE_MODEL_PATH,
    XGBOOST_MODEL_PATH,
    YOLO_ENGINE_PATH,
    YOLO_PT_PATH,
)


def package_version(module_name: str) -> str:
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return "NOT INSTALLED"
    return str(getattr(module, "__version__", "unknown"))


def main() -> None:
    try:
        import torch
    except ImportError:
        torch = None

    cuda_available = bool(torch and torch.cuda.is_available())
    cuda_version = str(torch.version.cuda) if torch else "N/A"
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else "N/A"

    print("========================================")
    print("AI Exercise Assistant Environment")
    print("========================================")
    print(f"Python:      {platform.python_version()}")
    print(f"PyTorch:     {package_version('torch')}")
    print(f"CUDA:        {'AVAILABLE' if cuda_available else 'NOT AVAILABLE'} ({cuda_version})")
    print(f"GPU:         {gpu_name}")
    print(f"OpenCV:      {package_version('cv2')}")
    print(f"Ultralytics: {package_version('ultralytics')}")
    print(f"MediaPipe:   {package_version('mediapipe')}")
    print(f"XGBoost:     {package_version('xgboost')}")
    print("\nModels:\n")

    models = (
        ("YOLO PT", YOLO_PT_PATH),
        ("YOLO TensorRT", YOLO_ENGINE_PATH),
        ("MediaPipe Pose", POSE_MODEL_PATH),
        ("XGBoost", XGBOOST_MODEL_PATH),
        ("Classes", CLASSES_PATH),
    )
    for name, path in models:
        print(f"{name:<16}: {'FOUND' if path.is_file() else 'MISSING'}")


if __name__ == "__main__":
    main()

