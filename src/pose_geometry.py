"""Pose landmark 기하 계산: 종횡비 보정 각도, 전신 가시성 검사, 측면 시점 판별, 평활화.

모든 각도는 crop의 픽셀 좌표에서 계산한다. MediaPipe의 x, y는 crop 크기 기준 0~1 값이라
crop의 가로세로 비가 다르면 정규화 좌표 그대로는 각도가 왜곡된다. crop은 YOLO bbox가
바뀔 때마다 달라지므로 보정 계수는 매 프레임 해당 프레임의 crop w, h로 구한다.
"""

import math
from dataclasses import dataclass
from typing import Any, Literal, Protocol, Sequence

import numpy as np

from config.settings import (
    FRAME_BORDER_TOLERANCE_PX,
    MIN_LANDMARK_VISIBILITY,
    ONE_EURO_BETA,
    ONE_EURO_D_CUTOFF,
    ONE_EURO_MIN_CUTOFF,
    SIDE_VIEW_MAX_SHOULDER_RATIO,
    SIDE_VIEW_MIN_NOSE_VISIBILITY,
)
from src.pose_classifier import LANDMARK_NAMES


Leg = Literal["left", "right"]
# 사용자가 보는 방향. 이미지 기준 left = -x 쪽, right = +x 쪽.
Facing = Literal["left", "right"]
BBox = tuple[int, int, int, int]

LANDMARK_INDEX = {name: index for index, name in enumerate(LANDMARK_NAMES)}
# 전신 가시성 검사에 쓰는 한쪽 다리의 관절. 발 위치(heel, foot_index)까지 포함한다.
LEG_JOINTS = ("hip", "knee", "ankle", "heel", "foot_index")
_EPSILON = 1e-9


# ---------------------------------------------------------------- landmark 변환


def _landmark_row(landmark: Any, visibility_required: bool) -> tuple[float, float, float, float]:
    if all(hasattr(landmark, name) for name in ("x", "y", "z")):
        values = (landmark.x, landmark.y, landmark.z, getattr(landmark, "visibility", None))
    else:
        values = tuple(landmark)
        if len(values) == 3:
            values = (*values, None)
        elif len(values) < 3:
            raise ValueError("Each landmark must provide at least x, y, and z.")
        values = values[:4]

    x, y, z, visibility = values
    if visibility is None:
        if visibility_required:
            raise ValueError("Each landmark must provide visibility.")
        visibility = 1.0
    return float(x), float(y), float(z), float(visibility)


def landmarks_to_array(
    landmarks: Sequence[Any],
    *,
    visibility_required: bool = True,
) -> np.ndarray:
    """Landmark 33개를 (33, 4) [x, y, z, visibility] 배열로 바꾼다.

    world landmarks처럼 visibility가 없을 수 있는 입력은 visibility_required=False로
    넘기면 1.0으로 채운다. 이미지 landmark는 visibility가 필수다.
    """
    if len(landmarks) != len(LANDMARK_NAMES):
        raise ValueError(f"Expected {len(LANDMARK_NAMES)} landmarks, received {len(landmarks)}.")

    array = np.asarray(
        [_landmark_row(landmark, visibility_required) for landmark in landmarks],
        dtype=np.float64,
    )
    if not np.isfinite(array).all():
        raise ValueError("Landmarks contain NaN or infinite values.")
    return array


def to_pixel_points(landmarks: np.ndarray, crop_width: float, crop_height: float) -> np.ndarray:
    """정규화된 (x, y)를 crop 픽셀 좌표로 바꾼다. 종횡비 보정은 여기서 이루어진다."""
    if crop_width <= 0 or crop_height <= 0:
        raise ValueError(f"Crop size must be positive: {crop_width}x{crop_height}")
    return landmarks[:, :2] * np.array([crop_width, crop_height], dtype=np.float64)


# ---------------------------------------------------------------- 각도


def joint_angle(vertex: np.ndarray, first: np.ndarray, second: np.ndarray) -> float | None:
    """vertex에서 first, second를 잇는 두 선분 사이각(0~180도). 길이 0인 선분이면 None."""
    first_vector = np.asarray(first, dtype=np.float64) - vertex
    second_vector = np.asarray(second, dtype=np.float64) - vertex
    if np.linalg.norm(first_vector) < _EPSILON or np.linalg.norm(second_vector) < _EPSILON:
        return None
    cross = first_vector[0] * second_vector[1] - first_vector[1] * second_vector[0]
    dot = float(first_vector @ second_vector)
    return math.degrees(math.atan2(abs(cross), dot))


def angle_from_vertical(origin: np.ndarray, target: np.ndarray) -> float | None:
    """origin→target 벡터가 위쪽 수직과 이루는 각(0~180도). 0이 수직, 방향(좌우)은 구분하지 않는다."""
    delta_x = float(target[0] - origin[0])
    delta_y = float(target[1] - origin[1])
    if math.hypot(delta_x, delta_y) < _EPSILON:
        return None
    # 이미지 좌표는 y가 아래로 증가하므로 위쪽 벡터는 delta_y < 0이다.
    return math.degrees(math.atan2(abs(delta_x), -delta_y))


def signed_angle_from_vertical(
    origin: np.ndarray,
    target: np.ndarray,
    facing: Facing | None,
) -> float | None:
    """origin→target 벡터의 수직 대비 각도. 사용자가 보는 방향(facing)으로 기울면 양수.

    facing이 right이면 이미지의 +x가 앞, left이면 -x가 앞이다. 범위는 -180~180도.
    facing을 모르거나 길이가 0이면 None.
    """
    if facing is None:
        return None
    delta_x = float(target[0] - origin[0])
    delta_y = float(target[1] - origin[1])
    if math.hypot(delta_x, delta_y) < _EPSILON:
        return None
    forward = 1.0 if facing == "right" else -1.0
    return math.degrees(math.atan2(forward * delta_x, -delta_y))


def _joint(points: np.ndarray, leg: Leg, joint: str) -> np.ndarray:
    return points[LANDMARK_INDEX[f"{leg}_{joint}"]]


def facing_direction(points: np.ndarray, leg: Leg) -> Facing | None:
    """선택한 다리의 heel→foot_index가 향하는 이미지 x 방향으로 사용자가 보는 방향을 정한다.

    발끝이 뒤꿈치와 같은 x에 있으면(정면·후면에 가까움) 방향을 정할 수 없어 None.
    """
    delta_x = float(_joint(points, leg, "foot_index")[0] - _joint(points, leg, "heel")[0])
    if abs(delta_x) < _EPSILON:
        return None
    return "right" if delta_x > 0 else "left"


def knee_angle(points: np.ndarray, leg: Leg) -> float | None:
    """무릎각: hip-knee-ankle 사이각."""
    return joint_angle(_joint(points, leg, "knee"), _joint(points, leg, "hip"), _joint(points, leg, "ankle"))


def torso_angle(points: np.ndarray, leg: Leg) -> float | None:
    """몸통각: hip→shoulder 선분이 수직과 이루는 각 (0 = 곧게 선 상태)."""
    return angle_from_vertical(_joint(points, leg, "hip"), _joint(points, leg, "shoulder"))


def shin_angle(points: np.ndarray, leg: Leg) -> float | None:
    """정강이각: ankle→knee 선분이 수직과 이루는 각 (0 = 정강이가 수직)."""
    return angle_from_vertical(_joint(points, leg, "ankle"), _joint(points, leg, "knee"))


def signed_torso_angle(points: np.ndarray, leg: Leg, facing: Facing | None) -> float | None:
    """부호 있는 몸통각: 어깨가 엉덩이보다 앞(facing 쪽)에 있으면 양수 = 앞으로 숙임."""
    return signed_angle_from_vertical(_joint(points, leg, "hip"), _joint(points, leg, "shoulder"), facing)


def signed_shin_angle(points: np.ndarray, leg: Leg, facing: Facing | None) -> float | None:
    """부호 있는 정강이각: 무릎이 발목보다 앞(facing 쪽)에 있으면 양수 = 무릎이 앞으로 나감."""
    return signed_angle_from_vertical(_joint(points, leg, "ankle"), _joint(points, leg, "knee"), facing)


def select_near_leg(landmarks: np.ndarray) -> Leg:
    """hip, knee, ankle visibility 합이 큰 쪽 다리를 고른다. 같으면 왼쪽."""
    scores = {
        leg: sum(landmarks[LANDMARK_INDEX[f"{leg}_{joint}"], 3] for joint in ("hip", "knee", "ankle"))
        for leg in ("left", "right")
    }
    return "left" if scores["left"] >= scores["right"] else "right"


# ---------------------------------------------------------------- 전신 가시성


@dataclass(frozen=True)
class FullBodyCheck:
    """각도를 신뢰해도 되는지의 판정.

    무효면 reasons에 사유 코드가 들어간다. notes는 유효 여부에 영향을 주지 않는 참고 정보다
    (예: 머리가 화면 위로 잘린 경우의 `bbox_touches_frame:top`).
    """

    valid: bool
    reasons: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def check_full_body(
    landmarks: np.ndarray,
    leg: Leg,
    person_bbox: BBox,
    frame_size: tuple[int, int],
    *,
    min_visibility: float = MIN_LANDMARK_VISIBILITY,
    border_tolerance: int = FRAME_BORDER_TOLERANCE_PX,
) -> FullBodyCheck:
    """사용하는 쪽 어깨~발끝이 모두 믿을 만할 때만 유효로 판정한다.

    조건: 사용하는 다리의 hip/knee/ankle/heel/foot_index가 crop 안이고 visibility가 충분하며,
    같은 쪽 shoulder의 visibility가 충분하고, YOLO bbox가 프레임의 하단·좌·우 경계에 닿지 않을 것.
    다리가 프레임에서 잘리면 MediaPipe가 다리를 추정해 crop 밖 좌표를 내므로 이런 프레임의
    각도는 쓰지 않는다. 상단 접촉은 무효 사유가 아니다: 머리가 화면 위로 잘리는 일은 흔하고
    스쿼트 판정에는 어깨~발끝만 필요하다(상단 접촉은 notes에만 남긴다).
    person_bbox는 padding 전 원래 YOLO bbox다.
    """
    reasons: list[str] = []
    notes: list[str] = []
    for joint in LEG_JOINTS:
        name = f"{leg}_{joint}"
        x, y, _, visibility = landmarks[LANDMARK_INDEX[name]]
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            reasons.append(f"outside_crop:{name}")
        if visibility < min_visibility:
            reasons.append(f"low_visibility:{name}")

    shoulder_name = f"{leg}_shoulder"
    if landmarks[LANDMARK_INDEX[shoulder_name], 3] < min_visibility:
        reasons.append(f"low_visibility:{shoulder_name}")

    x1, y1, x2, y2 = person_bbox
    frame_width, frame_height = frame_size
    if x1 <= border_tolerance:
        reasons.append("bbox_touches_frame:left")
    if x2 >= frame_width - border_tolerance:
        reasons.append("bbox_touches_frame:right")
    if y2 >= frame_height - border_tolerance:
        reasons.append("bbox_touches_frame:bottom")
    if y1 <= border_tolerance:
        notes.append("bbox_touches_frame:top")

    return FullBodyCheck(valid=not reasons, reasons=tuple(reasons), notes=tuple(notes))


# ---------------------------------------------------------------- 측면 시점 판별


@dataclass(frozen=True)
class ViewSignals:
    """시점 판별에 쓰는 신호. 판정에 쓰이지 않는 신호도 로그를 위해 항상 계산한다."""

    shoulder_ratio: float | None  # (a) 어깨 좌우 간격 ÷ 몸통 길이 (픽셀 보정 후). 0에 가까울수록 측면
    hip_yaw_deg: float | None  # (b) world 좌우 hip 벡터 기반 yaw. 0 = 정면/후면, 90 = 측면. 기록만
    nose_visibility: float  # (c) 코 visibility. 뒷모습이면 낮다


@dataclass(frozen=True)
class ViewJudgement:
    """측면 판정. reasons가 비어 있으면 측면이다."""

    reasons: tuple[str, ...] = ()

    @property
    def is_side(self) -> bool:
        return not self.reasons


class ViewClassifier(Protocol):
    """측면 판별 방식. 신호를 받아 판정만 하므로 다른 방식으로 교체할 수 있다."""

    def classify(self, signals: ViewSignals) -> ViewJudgement: ...


class ShoulderNoseViewClassifier:
    """(a) 어깨 비율 + (c) 코 visibility로 판정한다. (b) yaw는 판정에 쓰지 않는다."""

    def __init__(
        self,
        max_shoulder_ratio: float = SIDE_VIEW_MAX_SHOULDER_RATIO,
        min_nose_visibility: float = SIDE_VIEW_MIN_NOSE_VISIBILITY,
    ) -> None:
        self.max_shoulder_ratio = max_shoulder_ratio
        self.min_nose_visibility = min_nose_visibility

    def classify(self, signals: ViewSignals) -> ViewJudgement:
        reasons: list[str] = []
        if signals.shoulder_ratio is None:
            reasons.append("shoulder_ratio_unavailable")
        elif signals.shoulder_ratio > self.max_shoulder_ratio:
            reasons.append("shoulders_wide")
        if signals.nose_visibility < self.min_nose_visibility:
            reasons.append("nose_hidden")
        return ViewJudgement(reasons=tuple(reasons))


def compute_view_signals(
    landmarks: np.ndarray,
    pixel_points: np.ndarray,
    world_landmarks: np.ndarray | None = None,
) -> ViewSignals:
    """시점 판별 신호 (a)(b)(c)를 모두 계산한다.

    (a)는 Phase 0 분석과 같이 visibility로 걸러내지 않는다. 측면 샘플에서 먼 쪽 어깨의
    visibility가 낮은 경우가 흔하므로 여기서 걸러내면 측면을 놓친다.
    """
    left_shoulder = pixel_points[LANDMARK_INDEX["left_shoulder"]]
    right_shoulder = pixel_points[LANDMARK_INDEX["right_shoulder"]]
    left_hip = pixel_points[LANDMARK_INDEX["left_hip"]]
    right_hip = pixel_points[LANDMARK_INDEX["right_hip"]]
    torso_length = float(np.linalg.norm((left_shoulder + right_shoulder) / 2 - (left_hip + right_hip) / 2))
    shoulder_ratio = (
        abs(float(left_shoulder[0] - right_shoulder[0])) / torso_length
        if torso_length > _EPSILON
        else None
    )

    hip_yaw_deg = None
    if world_landmarks is not None:
        hip_vector = world_landmarks[LANDMARK_INDEX["right_hip"], :3] - world_landmarks[LANDMARK_INDEX["left_hip"], :3]
        lateral, depth = abs(float(hip_vector[0])), abs(float(hip_vector[2]))
        if lateral > _EPSILON or depth > _EPSILON:
            # 좌우 부호는 world 좌표계 방향에 의존하므로 절댓값으로 방향과 무관한 각도만 쓴다.
            hip_yaw_deg = math.degrees(math.atan2(depth, lateral))

    return ViewSignals(
        shoulder_ratio=shoulder_ratio,
        hip_yaw_deg=hip_yaw_deg,
        nose_visibility=float(landmarks[LANDMARK_INDEX["nose"], 3]),
    )


# ---------------------------------------------------------------- 프레임 분석


@dataclass(frozen=True)
class FrameGeometry:
    """한 프레임의 기하 결과. 각도는 항상 계산하고, 신뢰 여부는 full_body가 알려준다.

    torso_angle/shin_angle은 방향 없는 0~180도 값, *_signed는 facing 쪽으로 기울면 양수인 값이다.
    facing을 정할 수 없으면 *_signed는 None.
    """

    leg: Leg
    facing: Facing | None
    knee_angle: float | None
    torso_angle: float | None
    shin_angle: float | None
    torso_angle_signed: float | None
    shin_angle_signed: float | None
    full_body: FullBodyCheck
    view_signals: ViewSignals
    view: ViewJudgement


_DEFAULT_VIEW_CLASSIFIER = ShoulderNoseViewClassifier()


def analyze_frame(
    landmarks: Sequence[Any],
    *,
    crop_bbox: BBox,
    person_bbox: BBox,
    frame_size: tuple[int, int],
    world_landmarks: Sequence[Any] | None = None,
    leg: Leg | None = None,
    facing: Facing | None = None,
    view_classifier: ViewClassifier | None = None,
    min_visibility: float = MIN_LANDMARK_VISIBILITY,
    border_tolerance: int = FRAME_BORDER_TOLERANCE_PX,
) -> FrameGeometry:
    """한 프레임의 landmark에서 각도, 전신 유효 여부, 시점 신호와 판정을 계산한다.

    crop_bbox는 MediaPipe에 넣은 padded crop, person_bbox는 padding 전 YOLO bbox,
    frame_size는 (width, height). leg와 facing을 주면 그 값을 쓰고(반복 중 고정), 없으면
    이 프레임에서 가까운 쪽 다리를 visibility로 고르고 facing은 그 다리의 heel→foot_index로 정한다.
    """
    if leg not in (None, "left", "right"):
        raise ValueError(f"Unsupported leg: {leg}")
    if facing not in (None, "left", "right"):
        raise ValueError(f"Unsupported facing: {facing}")

    array = landmarks_to_array(landmarks)
    world_array = (
        landmarks_to_array(world_landmarks, visibility_required=False)
        if world_landmarks is not None
        else None
    )
    crop_width = crop_bbox[2] - crop_bbox[0]
    crop_height = crop_bbox[3] - crop_bbox[1]
    pixel_points = to_pixel_points(array, crop_width, crop_height)

    chosen_leg: Leg = leg if leg is not None else select_near_leg(array)
    chosen_facing = facing if facing is not None else facing_direction(pixel_points, chosen_leg)
    signals = compute_view_signals(array, pixel_points, world_array)
    classifier = view_classifier if view_classifier is not None else _DEFAULT_VIEW_CLASSIFIER

    return FrameGeometry(
        leg=chosen_leg,
        facing=chosen_facing,
        knee_angle=knee_angle(pixel_points, chosen_leg),
        torso_angle=torso_angle(pixel_points, chosen_leg),
        shin_angle=shin_angle(pixel_points, chosen_leg),
        torso_angle_signed=signed_torso_angle(pixel_points, chosen_leg, chosen_facing),
        shin_angle_signed=signed_shin_angle(pixel_points, chosen_leg, chosen_facing),
        full_body=check_full_body(
            array,
            chosen_leg,
            person_bbox,
            frame_size,
            min_visibility=min_visibility,
            border_tolerance=border_tolerance,
        ),
        view_signals=signals,
        view=classifier.classify(signals),
    )


# ---------------------------------------------------------------- 반복 중 고정


class BodyLock:
    """STANDING에서 판별한 다리, 보는 방향(facing), 시점을 반복이 끝날 때까지 고정한다.

    잠그는 시점(STANDING)은 호출하는 쪽(RepTracker)이 정한다. 전신이 유효하지 않은 프레임이나
    facing을 정할 수 없는 프레임에서는 다리 선택과 시점 판별이 믿을 수 없으므로 잠그지 않는다.
    """

    def __init__(self) -> None:
        self._leg: Leg | None = None
        self._facing: Facing | None = None
        self._view: ViewJudgement | None = None

    @property
    def is_locked(self) -> bool:
        return self._leg is not None

    @property
    def leg(self) -> Leg:
        if self._leg is None:
            raise RuntimeError("BodyLock is not acquired.")
        return self._leg

    @property
    def facing(self) -> Facing:
        if self._facing is None:
            raise RuntimeError("BodyLock is not acquired.")
        return self._facing

    @property
    def view(self) -> ViewJudgement:
        if self._view is None:
            raise RuntimeError("BodyLock is not acquired.")
        return self._view

    def acquire(self, geometry: FrameGeometry) -> bool:
        """이 프레임의 다리·facing·시점을 고정한다. 이미 잠겼거나 전신 무효, facing 불명이면 False."""
        if self.is_locked or not geometry.full_body.valid or geometry.facing is None:
            return False
        self._leg = geometry.leg
        self._facing = geometry.facing
        self._view = geometry.view
        return True

    def release(self) -> None:
        self._leg = None
        self._facing = None
        self._view = None

    def quality_enabled(self, geometry: FrameGeometry) -> bool:
        """이 프레임에서 품질 판정을 해도 되는가: 잠금 시점이 측면이고 현재 프레임 전신이 유효."""
        return self.is_locked and self.view.is_side and geometry.full_body.valid


# ---------------------------------------------------------------- 평활화


class OneEuroFilter:
    """연속 신호용 One Euro filter. 이산 라벨용 PredictionSmoother와는 별개다.

    모든 계산은 프레임 수가 아니라 타임스탬프(초) 간격으로 하므로 불규칙한 프레임 간격에서도
    평활화 정도가 일정하다. 느린 움직임은 강하게 거르고 빠른 움직임은 지연을 줄인다.
    """

    def __init__(
        self,
        min_cutoff: float = ONE_EURO_MIN_CUTOFF,
        beta: float = ONE_EURO_BETA,
        d_cutoff: float = ONE_EURO_D_CUTOFF,
    ) -> None:
        if min_cutoff <= 0 or d_cutoff <= 0:
            raise ValueError("min_cutoff and d_cutoff must be positive.")
        if beta < 0:
            raise ValueError("beta must be non-negative.")
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self) -> None:
        self._timestamp: float | None = None
        self._value: float | None = None
        self._derivative = 0.0

    @staticmethod
    def _smoothing_factor(elapsed: float, cutoff: float) -> float:
        rate = 2.0 * math.pi * cutoff * elapsed
        return rate / (rate + 1.0)

    def __call__(self, value: float, timestamp: float) -> float:
        if self._timestamp is None or self._value is None:
            self._timestamp = float(timestamp)
            self._value = float(value)
            return self._value

        elapsed = float(timestamp) - self._timestamp
        if elapsed <= 0:
            # 같은 시각이거나 역행한 타임스탬프는 상태를 바꾸지 않는다.
            return self._value

        derivative = (float(value) - self._value) / elapsed
        derivative_factor = self._smoothing_factor(elapsed, self.d_cutoff)
        self._derivative += derivative_factor * (derivative - self._derivative)

        cutoff = self.min_cutoff + self.beta * abs(self._derivative)
        factor = self._smoothing_factor(elapsed, cutoff)
        self._value += factor * (float(value) - self._value)
        self._timestamp = float(timestamp)
        return self._value
