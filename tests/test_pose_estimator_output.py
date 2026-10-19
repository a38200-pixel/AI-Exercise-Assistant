"""PoseEstimator가 world landmarks를 추가로 반환해도 XGBoost 입력이 변하지 않음을 검증한다.

MediaPipe 모델 없이 가짜 landmarker로 실행한다. 변경 전 extract()는 pose_landmarks[0]을 그대로
반환했고 분류기는 그 값에서 132개 feature를 만들었다. 지금도 같은 객체가 같은 feature를
만들어야 한다.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pose_classifier import PoseClassifier
from src.pose_estimator import PoseEstimator, PoseExtraction


CROP = np.zeros((20, 10, 3), dtype=np.uint8)


def make_landmarks(seed: int, count: int = 33):
    rng = np.random.default_rng(seed)
    return [
        SimpleNamespace(
            x=float(rng.uniform(-0.5, 1.5)),
            y=float(rng.uniform(-0.5, 1.5)),
            z=float(rng.uniform(-1.0, 1.0)),
            visibility=float(rng.uniform(0.0, 1.0)),
        )
        for _ in range(count)
    ]


class FakeLandmarker:
    def __init__(self, result) -> None:
        self.result = result

    def detect(self, image):
        return self.result


def make_estimator(result) -> PoseEstimator:
    """모델 파일과 mediapipe 없이 extract()만 실행할 수 있는 PoseEstimator."""
    estimator = PoseEstimator.__new__(PoseEstimator)
    estimator._mp = SimpleNamespace(
        Image=lambda image_format, data: SimpleNamespace(data=data),
        ImageFormat=SimpleNamespace(SRGB="SRGB"),
    )
    estimator.landmarker = FakeLandmarker(result)
    return estimator


def classifier_features(landmarks) -> np.ndarray:
    classifier = PoseClassifier.__new__(PoseClassifier)  # 모델을 읽지 않고 feature 생성만 사용
    return classifier.create_features(landmarks)


def legacy_features(landmarks) -> np.ndarray:
    """변경 전 입력: 각 landmark의 x, y, z, visibility를 MediaPipe 순서대로 펼친 132개 값."""
    rows = [[lm.x, lm.y, lm.z, lm.visibility] for lm in landmarks]
    return np.asarray(rows, dtype=np.float32).reshape(1, -1)


def test_extract_returns_the_same_landmark_objects_as_before() -> None:
    landmarks, world = make_landmarks(1), make_landmarks(2)
    result = SimpleNamespace(pose_landmarks=[landmarks], pose_world_landmarks=[world])

    extraction = make_estimator(result).extract(CROP)

    assert isinstance(extraction, PoseExtraction)
    assert extraction.landmarks is landmarks  # 변경 전과 같은 객체
    assert extraction.world_landmarks is world


def test_classifier_input_is_identical_to_the_pre_change_input() -> None:
    landmarks = make_landmarks(1)
    result = SimpleNamespace(pose_landmarks=[landmarks], pose_world_landmarks=[make_landmarks(2)])

    features = classifier_features(make_estimator(result).extract(CROP).landmarks)

    assert features.shape == (1, 132)
    assert features.dtype == np.float32
    assert np.array_equal(features, legacy_features(landmarks))


def test_classifier_input_does_not_depend_on_world_landmarks() -> None:
    landmarks = make_landmarks(1)
    with_world_a = SimpleNamespace(pose_landmarks=[landmarks], pose_world_landmarks=[make_landmarks(2)])
    with_world_b = SimpleNamespace(pose_landmarks=[landmarks], pose_world_landmarks=[make_landmarks(3)])
    without_world = SimpleNamespace(pose_landmarks=[landmarks], pose_world_landmarks=[])

    features = [
        classifier_features(make_estimator(result).extract(CROP).landmarks)
        for result in (with_world_a, with_world_b, without_world)
    ]

    assert np.array_equal(features[0], features[1])
    assert np.array_equal(features[0], features[2])


def test_missing_or_malformed_world_landmarks_leave_landmarks_untouched() -> None:
    landmarks = make_landmarks(1)
    cases = (
        SimpleNamespace(pose_landmarks=[landmarks], pose_world_landmarks=[]),
        SimpleNamespace(pose_landmarks=[landmarks], pose_world_landmarks=None),
        SimpleNamespace(pose_landmarks=[landmarks]),  # 속성 자체가 없는 결과
        SimpleNamespace(pose_landmarks=[landmarks], pose_world_landmarks=[make_landmarks(2, count=30)]),
    )
    for result in cases:
        extraction = make_estimator(result).extract(CROP)
        assert extraction is not None
        assert extraction.landmarks is landmarks
        assert extraction.world_landmarks is None


def test_no_pose_or_wrong_landmark_count_returns_none() -> None:
    world = [make_landmarks(2)]
    assert make_estimator(SimpleNamespace(pose_landmarks=[], pose_world_landmarks=world)).extract(CROP) is None
    wrong_count = SimpleNamespace(pose_landmarks=[make_landmarks(1, count=32)], pose_world_landmarks=world)
    assert make_estimator(wrong_count).extract(CROP) is None
    empty_crop = np.zeros((0, 0, 3), np.uint8)
    assert make_estimator(SimpleNamespace(pose_landmarks=[], pose_world_landmarks=[])).extract(empty_crop) is None
