"""Validate the clean FitRoute AI Client build environment without a camera."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import subprocess
import sys


EXPECTED_ENVIRONMENT = "fitroute_build"
EXPECTED_OPENCV_DISTRIBUTION = "opencv-contrib-python"
EXPECTED_OPENCV_DISTRIBUTION_VERSION = "5.0.0.93"
OPENCV_DISTRIBUTIONS = (
    "opencv-python",
    "opencv-python-headless",
    "opencv-contrib-python",
    "opencv-contrib-python-headless",
)
ALLOWED_PIP_CHECK_EXCEPTION = (
    "ultralytics 8.4.70 requires opencv-python, which is not installed."
)


def get_installed_versions(distributions: tuple[str, ...]) -> dict[str, str]:
    """Return only distributions that are installed in the current Python."""
    installed: dict[str, str] = {}
    for distribution in distributions:
        try:
            installed[distribution] = version(distribution)
        except PackageNotFoundError:
            continue
    return installed


def classify_pip_check(
    returncode: int,
    output: str,
    opencv_distributions: dict[str, str],
) -> tuple[int, list[str]]:
    """Return the allowed exception count and every unexpected conflict."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    expected_opencv = {
        EXPECTED_OPENCV_DISTRIBUTION: EXPECTED_OPENCV_DISTRIBUTION_VERSION
    }

    if returncode == 0:
        return 0, []
    if (
        lines == [ALLOWED_PIP_CHECK_EXCEPTION]
        and opencv_distributions == expected_opencv
    ):
        return 1, []
    return 0, lines or [f"pip check exited with code {returncode} without output"]


def main() -> int:
    failures: list[str] = []
    environment_name = Path(sys.prefix).name
    print(f"Python executable: {sys.executable}")
    print(f"Python environment: {environment_name}")
    if environment_name.casefold() != EXPECTED_ENVIRONMENT.casefold():
        failures.append(
            f"expected environment {EXPECTED_ENVIRONMENT}, got {environment_name}"
        )

    opencv_distributions = get_installed_versions(OPENCV_DISTRIBUTIONS)
    opencv_summary = ", ".join(
        f"{name} {installed_version}"
        for name, installed_version in opencv_distributions.items()
    ) or "NONE"
    print(f"OpenCV distribution: {opencv_summary}")
    duplicate_opencv = len(opencv_distributions) > 1
    print(f"Duplicate OpenCV wheels: {'YES' if duplicate_opencv else 'NO'}")
    if opencv_distributions != {
        EXPECTED_OPENCV_DISTRIBUTION: EXPECTED_OPENCV_DISTRIBUTION_VERSION
    }:
        failures.append(
            "expected only opencv-contrib-python 5.0.0.93 to be installed"
        )

    try:
        import cv2

        gui_ok = cv2.__version__ == "5.0.0" and callable(getattr(cv2, "imshow", None))
        msmf_ok = hasattr(cv2, "CAP_MSMF")
        print(f"OpenCV module version: {cv2.__version__}")
        print(f"OpenCV GUI: {'OK' if gui_ok else 'FAIL'}")
        print(f"MSMF: {'OK' if msmf_ok else 'FAIL'}")
        if not gui_ok:
            failures.append("OpenCV GUI/version validation failed")
        if not msmf_ok:
            failures.append("OpenCV CAP_MSMF is unavailable")
    except Exception as exc:  # pragma: no cover - exercised only in broken envs
        failures.append(f"OpenCV import failed: {exc}")
        print("OpenCV GUI: FAIL")
        print("MSMF: FAIL")

    try:
        import torch

        cuda_ok = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "NONE"
        print(f"CUDA: {'OK' if cuda_ok else 'FAIL'} ({torch.version.cuda})")
        print(f"GPU: {gpu_name}")
        if not cuda_ok:
            failures.append("torch.cuda.is_available() is False")
    except Exception as exc:  # pragma: no cover - exercised only in broken envs
        failures.append(f"PyTorch/CUDA import failed: {exc}")
        print("CUDA: FAIL")

    import_results: list[tuple[str, bool, str]] = []
    imports = (
        ("TensorRT", "import tensorrt as module"),
        ("MediaPipe", "import mediapipe as module; from mediapipe.tasks import python"),
        ("XGBoost", "import xgboost as module"),
        ("Ultralytics", "import ultralytics as module; from ultralytics import YOLO"),
        ("HTTPX", "import httpx as module"),
    )
    for label, statement in imports:
        namespace: dict[str, object] = {}
        try:
            exec(statement, namespace)
            module = namespace["module"]
            module_version = str(getattr(module, "__version__", "unknown"))
            import_results.append((label, True, module_version))
        except Exception as exc:  # pragma: no cover - exercised only in broken envs
            import_results.append((label, False, str(exc)))
            failures.append(f"{label} import failed: {exc}")

    for label, ok, detail in import_results:
        print(f"{label}: {'OK' if ok else 'FAIL'} ({detail})")

    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    pip_check_output = "\n".join(
        part.strip() for part in (pip_check.stdout, pip_check.stderr) if part.strip()
    )
    print("pip check raw result:")
    print(pip_check_output or "No broken requirements found.")
    allowed_count, unexpected_conflicts = classify_pip_check(
        pip_check.returncode,
        pip_check_output,
        opencv_distributions,
    )
    print(f"Known metadata exception: {'ALLOWED' if allowed_count else 'NONE'}")
    print(f"Allowed metadata exceptions: {allowed_count}")
    print(f"Unexpected dependency conflicts: {len(unexpected_conflicts)}")
    failures.extend(
        f"unexpected dependency conflict: {conflict}"
        for conflict in unexpected_conflicts
    )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("BUILD ENVIRONMENT INVALID")
        return 1

    print("BUILD ENVIRONMENT VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
