"""Load and run the existing 132-feature XGBoost pose classifier."""

import json
from typing import Any, Sequence

import numpy as np

from config.settings import CLASSES_PATH, XGBOOST_MODEL_PATH


LANDMARK_NAMES = (
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)
LANDMARK_VALUE_NAMES = ("x", "y", "z", "visibility")
EXPECTED_CLASSES = (
    "squat",
    "run",
    "sit",
    "stretch",
    "walk",
    "jump",
    "bendover",
    "stand",
    "lying",
)
EXPECTED_FEATURE_NAMES = tuple(
    f"{landmark_name}_{value_name}"
    for landmark_name in LANDMARK_NAMES
    for value_name in LANDMARK_VALUE_NAMES
)


class PoseClassifier:
    LANDMARK_COUNT = len(LANDMARK_NAMES)
    FEATURE_COUNT = LANDMARK_COUNT * len(LANDMARK_VALUE_NAMES)

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
        if tuple(self.classes) != EXPECTED_CLASSES:
            raise ValueError(
                "classes.json does not match the expected 9-class training order:\n"
                + ", ".join(EXPECTED_CLASSES)
            )

        self.model = XGBClassifier()
        self.model.load_model(str(XGBOOST_MODEL_PATH))

        model_feature_count = int(self.model.get_booster().num_features())
        if model_feature_count != self.FEATURE_COUNT:
            raise ValueError(
                f"Expected features: {self.FEATURE_COUNT}\n"
                f"Model features: {model_feature_count}"
            )

        model_feature_names = self.model.get_booster().feature_names
        if (
            model_feature_names is not None
            and tuple(model_feature_names) != EXPECTED_FEATURE_NAMES
        ):
            raise ValueError(
                "The XGBoost model feature order does not match the expected "
                "MediaPipe x, y, z, visibility order."
            )

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

    def create_features(self, landmarks: Sequence[Any]) -> np.ndarray:
        """MediaPipe 순서를 유지해 각 점의 x, y, z, visibility를 펼친다."""
        if len(landmarks) != self.LANDMARK_COUNT:
            raise ValueError(
                f"Expected {self.LANDMARK_COUNT} landmarks, received {len(landmarks)}."
            )

        feature_values: list[float] = []
        for landmark in landmarks:
            landmark_values = self._landmark_values(landmark)
            feature_values.extend(landmark_values)

        if len(feature_values) != self.FEATURE_COUNT:
            raise ValueError(
                f"Expected features: {self.FEATURE_COUNT}\n"
                f"Created features: {len(feature_values)}"
            )

        features = np.asarray(feature_values, dtype=np.float32).reshape(1, -1)
        if not np.isfinite(features).all():
            raise ValueError("Pose features contain NaN or infinite values.")

        return features

    def classify(self, landmarks: Sequence[Any]) -> dict[str, Any]:
        features = self.create_features(landmarks)

        # predict()를 중복 호출하지 않고 확률 1회로 class와 confidence를 구한다.
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
