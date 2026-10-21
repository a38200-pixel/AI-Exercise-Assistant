"""MediaPipe Tasks pose landmark extraction for a person crop."""

from typing import Any, NamedTuple

import cv2
import numpy as np

from config.settings import (
    MIN_POSE_DETECTION_CONFIDENCE,
    MIN_POSE_PRESENCE_CONFIDENCE,
    POSE_MODEL_PATH,
)


class PoseExtraction(NamedTuple):
    """한 사람 crop의 Pose 결과.

    landmarks는 crop 기준 정규화 landmark 33개로 XGBoost 입력에 그대로 쓰이며, 이전 버전의
    extract()가 반환하던 값과 같은 객체다. world_landmarks는 미터 단위 3D 좌표(시점 yaw 등
    진단용)이고 분류기 입력에는 쓰이지 않는다. MediaPipe가 주지 않으면 None.
    """

    landmarks: list[Any]
    world_landmarks: list[Any] | None


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

    def extract(self, person_crop: np.ndarray) -> PoseExtraction | None:
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

        # world landmarks는 진단용이다. 없거나 개수가 맞지 않으면 None으로 두고 분류에는 영향을 주지 않는다.
        world_landmarks = None
        world_results = getattr(result, "pose_world_landmarks", None)
        if world_results and len(world_results[0]) == self.LANDMARK_COUNT:
            world_landmarks = world_results[0]

        return PoseExtraction(landmarks=landmarks, world_landmarks=world_landmarks)

    def close(self) -> None:
        self.landmarker.close()
