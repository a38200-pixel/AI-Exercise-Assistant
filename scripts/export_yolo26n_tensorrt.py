"""Prepare YOLO26n and export a static-batch TensorRT FP16 engine."""

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DETECTOR_MODEL_DIR, YOLO_ENGINE_PATH, YOLO_PT_PATH


def _resolve_export_path(export_result: object) -> Path:
    candidate = Path(str(export_result)).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    if not candidate.is_file():
        raise FileNotFoundError(
            f"Ultralytics reported an export path that does not exist: {candidate}"
        )
    return candidate


def main() -> None:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "Ultralytics is not installed. Run: pip install -r requirements.txt"
        ) from exc

    DETECTOR_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if YOLO_PT_PATH.is_file():
        model = YOLO(str(YOLO_PT_PATH), task="detect")
    else:
        print("yolo26n.pt not found; asking Ultralytics to download the official model.")
        model = YOLO("yolo26n.pt", task="detect")
        downloaded_path = Path(str(getattr(model, "ckpt_path", "yolo26n.pt"))).resolve()
        if not downloaded_path.is_file():
            raise FileNotFoundError(
                "Ultralytics loaded YOLO26n but its downloaded .pt path could not be located."
            )
        shutil.copy2(downloaded_path, YOLO_PT_PATH)
        model = YOLO(str(YOLO_PT_PATH), task="detect")

    export_result = model.export(
        format="engine",
        imgsz=640,
        half=True,
        device=0,
        batch=1,
    )
    exported_path = _resolve_export_path(export_result)

    if exported_path.resolve() != YOLO_ENGINE_PATH.resolve():
        if YOLO_ENGINE_PATH.exists():
            YOLO_ENGINE_PATH.unlink()
        shutil.move(str(exported_path), str(YOLO_ENGINE_PATH))

    if not YOLO_ENGINE_PATH.is_file():
        raise FileNotFoundError(f"TensorRT export was not created: {YOLO_ENGINE_PATH}")

    print("\n========================================")
    print("TensorRT Export Completed")
    print("========================================")
    print(f"PyTorch: {YOLO_PT_PATH}")
    print(f"TensorRT: {YOLO_ENGINE_PATH}")


if __name__ == "__main__":
    main()

