"""YOLO26n person detection with TensorRT-first model selection."""

from pathlib import Path
from typing import Any

from config.settings import (
    YOLO_CONFIDENCE,
    YOLO_DEVICE,
    YOLO_ENGINE_PATH,
    YOLO_IMAGE_SIZE,
    YOLO_MAX_DET,
    YOLO_PERSON_CLASS_ID,
    YOLO_PT_PATH,
)


class PersonDetector:
    def __init__(self) -> None:
        model_path, backend = self._select_model()

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "Ultralytics is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self.model = YOLO(str(model_path), task="detect")
        self.model_path = model_path
        self.backend = backend

    @staticmethod
    def _select_model() -> tuple[Path, str]:
        if YOLO_ENGINE_PATH.is_file():
            return YOLO_ENGINE_PATH, "TensorRT"
        if YOLO_PT_PATH.is_file():
            return YOLO_PT_PATH, "PyTorch"

        raise FileNotFoundError(
            "TensorRT model not found and no PyTorch fallback is available.\n"
            "Run:\n\n"
            "python scripts/export_yolo26n_tensorrt.py"
        )

    def detect(self, frame: Any) -> list[dict[str, Any]]:
        predict_args: dict[str, Any] = {
            "source": frame,
            "classes": [YOLO_PERSON_CLASS_ID],
            "conf": YOLO_CONFIDENCE,
            "imgsz": YOLO_IMAGE_SIZE,
            "max_det": YOLO_MAX_DET,
            "verbose": False,
        }
        # TensorRT engines already encode their target device. Supplying a
        # device again is version-dependent in Ultralytics, so only the .pt
        # backend receives it explicitly.
        if self.backend == "PyTorch":
            predict_args["device"] = YOLO_DEVICE

        results = self.model.predict(**predict_args)
        detections: list[dict[str, Any]] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for coordinates, confidence in zip(boxes.xyxy, boxes.conf):
                x1, y1, x2, y2 = coordinates.detach().cpu().tolist()
                detections.append(
                    {
                        "bbox": (int(x1), int(y1), int(x2), int(y2)),
                        "confidence": float(confidence.detach().cpu().item()),
                    }
                )

        return detections

