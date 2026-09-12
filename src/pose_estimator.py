"""MediaPipe Tasks pose landmark extraction for a person crop."""

from typing import Any

import cv2
import numpy as np

from config.settings import (
    MIN_POSE_DETECTION_CONFIDENCE,
    MIN_POSE_PRESENCE_CONFIDENCE,
    POSE_MODEL_PATH,
)


class PoseEstimator:
    LANDMARK_COUNT = 33

    def __init__(self) -> None:
        if not POSE_MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"MediaPipe pose model not found: {POSE_MODEL_PATH}\n"
                "Copy pose_landmarker_full.task to models/pose/."
            )

        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
        except ImportError as exc:
            raise RuntimeError(
                "MediaPipe is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self._mp = mp
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(POSE_MODEL_PATH)),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=MIN_POSE_DETECTION_CONFIDENCE,
            min_pose_presence_confidence=MIN_POSE_PRESENCE_CONFIDENCE,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    def extract(self, person_crop: np.ndarray) -> list[Any] | None:
        if person_crop is None or person_crop.size == 0:
            return None

        # OpenCV의 BGR crop을 MediaPipe가 사용하는 연속 RGB 배열로 변환한다.
        rgb = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(image)

        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks[0]
        if len(landmarks) != self.LANDMARK_COUNT:
            return None

        return landmarks

    def close(self) -> None:
        self.landmarker.close()
