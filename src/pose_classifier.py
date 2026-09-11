"""Load and run the existing 132-feature XGBoost pose classifier."""

import json
from typing import Any, Sequence

import numpy as np

from config.settings import CLASSES_PATH, XGBOOST_MODEL_PATH


class PoseClassifier:
    FEATURE_COUNT = 33 * 4

    def __init__(self) -> None:
        missing = [
            str(path)
            for path in (XGBOOST_MODEL_PATH, CLASSES_PATH)
            if not path.is_file()
        ]
        if missing:
            raise FileNotFoundError(
                "Required pose classifier file(s) not found:\n- "
                + "\n- ".join(missing)
                + "\nCopy the existing files to models/classifier/."
            )

        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError(
                "XGBoost is not installed. Run: pip install -r requirements.txt"
            ) from exc

        with CLASSES_PATH.open("r", encoding="utf-8") as classes_file:
            self.classes = json.load(classes_file)
        if not isinstance(self.classes, list) or not all(
            isinstance(label, str) for label in self.classes
        ):
            raise ValueError("classes.json must contain a JSON list of labels.")

        self.model = XGBClassifier()
        self.model.load_model(str(XGBOOST_MODEL_PATH))

    @staticmethod
    def _landmark_values(landmark: Any) -> tuple[float, float, float, float]:
        if isinstance(landmark, dict):
            return tuple(float(landmark[name]) for name in ("x", "y", "z", "visibility"))
        if all(hasattr(landmark, name) for name in ("x", "y", "z", "visibility")):
            return (
                float(landmark.x),
                float(landmark.y),
                float(landmark.z),
                float(landmark.visibility),
            )
        values = tuple(float(value) for value in landmark)
        if len(values) < 4:
            raise ValueError("Each landmark must provide x, y, z, and visibility.")
        return values[:4]

    def classify(self, landmarks: Sequence[Any]) -> dict[str, Any]:
        if len(landmarks) != 33:
            raise ValueError(f"Expected 33 landmarks, received {len(landmarks)}.")

        features = np.asarray(
            [value for landmark in landmarks for value in self._landmark_values(landmark)],
            dtype=np.float32,
        ).reshape(1, self.FEATURE_COUNT)

        probabilities = np.asarray(self.model.predict_proba(features))[0]
        probability_index = int(np.argmax(probabilities))
        model_classes = getattr(self.model, "classes_", None)
        class_id = (
            int(model_classes[probability_index])
            if model_classes is not None
            else probability_index
        )
        if not 0 <= class_id < len(self.classes):
            raise ValueError(f"Predicted class id {class_id} is absent from classes.json.")

        return {
            "class_id": class_id,
            "label": self.classes[class_id],
            "confidence": float(probabilities[probability_index]),
        }

