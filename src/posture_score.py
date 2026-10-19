"""자세 점수(표시용): 반복 한 번의 측정값에서 항목별 판정과 총점을 계산하는 순수 함수.

판정 항목은 두 개뿐이다.
- depth: 최저점 무릎각(작을수록 깊다). 정상 <= POSTURE_DEPTH_NORMAL_MAX, 교정 >= POSTURE_DEPTH_CORRECT_MIN.
- torso_shin: 최저점의 |몸통각 - 정강이각|(둘 다 앞으로 숙이면 양수인 부호 있는 각도). 정상 <= POSTURE_TORSO_SHIN_NORMAL_MAX,
  교정 >= POSTURE_TORSO_SHIN_CORRECT_MIN. 절대 몸통각은 쓰지 않는다.
뒤꿈치(heel)와 템포(하강·상승 시간)는 판정·점수에 쓰지 않는다(원자료는 RepResult에만 남긴다).

점수 규칙: 항목 점수는 정상 경계 이내 100, 교정 경계 이상 0, 사이는 선형. 총점은 판정된 항목의 가중 평균(가중치는 설정)이고,
교정 항목이 하나라도 있으면 POSTURE_SCORE_CAP_WITH_CORRECTION을 넘지 못한다. **depth가 교정이면 torso_shin은 판정하지 않고
기록만 한다**(얕은 반복의 이중 감점 방지). worst_item은 가중 감점(가중치 x (100 - 점수))이 가장 큰 항목이다.

이 모듈은 어디에도 연결되어 있지 않다(RepTracker·화면 연결은 Phase 3의 후속 작업). 명칭은 코드·화면·문서 모두 "자세 점수"로 쓴다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from config.settings import (
    POSTURE_DEPTH_CORRECT_MIN,
    POSTURE_DEPTH_NORMAL_MAX,
    POSTURE_SCORE_CAP_WITH_CORRECTION,
    POSTURE_TORSO_SHIN_CORRECT_MIN,
    POSTURE_TORSO_SHIN_NORMAL_MAX,
    POSTURE_WEIGHT_DEPTH,
    POSTURE_WEIGHT_TORSO_SHIN,
)

SCORE_LABEL = "자세 점수"

ITEM_DEPTH = "depth"
ITEM_TORSO_SHIN = "torso_shin"
ITEMS = (ITEM_DEPTH, ITEM_TORSO_SHIN)  # worst_item 동점일 때의 우선순위이기도 하다

STATUS_NORMAL = "normal"  # 정상
STATUS_CAUTION = "caution"  # 주의
STATUS_CORRECT = "correct"  # 교정
STATUS_RECORDED_ONLY = "recorded_only"  # 측정값은 있으나 판정하지 않음(depth가 교정일 때의 torso_shin)
STATUS_UNAVAILABLE = "unavailable"  # 측정값이 없음

FEEDBACK_TEXT = {
    ITEM_DEPTH: "더 깊게 앉아보세요",
    ITEM_TORSO_SHIN: "상체를 조금 더 세워보세요",
}


@dataclass(frozen=True)
class ItemLimits:
    """항목 하나의 경계: value <= normal_max면 정상(100점), value >= correct_min이면 교정(0점)."""

    normal_max: float
    correct_min: float

    def __post_init__(self) -> None:
        if not self.normal_max < self.correct_min:
            raise ValueError("normal_max must be below correct_min.")

    def score(self, value: float) -> float:
        if value <= self.normal_max:
            return 100.0
        if value >= self.correct_min:
            return 0.0
        return 100.0 * (self.correct_min - value) / (self.correct_min - self.normal_max)

    def status(self, value: float) -> str:
        if value <= self.normal_max:
            return STATUS_NORMAL
        if value >= self.correct_min:
            return STATUS_CORRECT
        return STATUS_CAUTION


DEFAULT_LIMITS = {
    ITEM_DEPTH: ItemLimits(POSTURE_DEPTH_NORMAL_MAX, POSTURE_DEPTH_CORRECT_MIN),
    ITEM_TORSO_SHIN: ItemLimits(POSTURE_TORSO_SHIN_NORMAL_MAX, POSTURE_TORSO_SHIN_CORRECT_MIN),
}
DEFAULT_WEIGHTS = {ITEM_DEPTH: POSTURE_WEIGHT_DEPTH, ITEM_TORSO_SHIN: POSTURE_WEIGHT_TORSO_SHIN}


@dataclass(frozen=True)
class PostureScore:
    """반복 한 번의 자세 점수. 점수를 계산할 수 없으면 total_score는 None이다."""

    total_score: float | None
    item_scores: dict[str, float | None]  # 판정하지 않은 항목은 None
    item_status: dict[str, str]
    worst_item: str | None  # 감점이 없으면 None
    capped: bool  # 교정 항목 때문에 총점 상한이 적용됐는가
    measures: dict[str, float | None] = field(default_factory=dict)  # depth: 최저 무릎각, torso_shin: |몸통각 - 정강이각|


def torso_shin_difference(torso_signed: float | None, shin_signed: float | None) -> float | None:
    """최저점의 |몸통각 - 정강이각|. 어느 쪽이든 없으면 None."""
    if _missing(torso_signed) or _missing(shin_signed):
        return None
    return abs(float(torso_signed) - float(shin_signed))


def score_posture(
    min_knee_angle: float | None,
    torso_signed: float | None,
    shin_signed: float | None,
    *,
    limits: dict[str, ItemLimits] | None = None,
    weights: dict[str, float] | None = None,
    cap: float = POSTURE_SCORE_CAP_WITH_CORRECTION,
) -> PostureScore:
    """반복 한 번의 측정값(최저점 무릎각, 최저점의 부호 있는 몸통각·정강이각)으로 자세 점수를 계산한다."""
    limits = limits or DEFAULT_LIMITS
    weights = weights or DEFAULT_WEIGHTS
    measures: dict[str, float | None] = {
        ITEM_DEPTH: None if _missing(min_knee_angle) else float(min_knee_angle),
        ITEM_TORSO_SHIN: torso_shin_difference(torso_signed, shin_signed),
    }

    status: dict[str, str] = {}
    scores: dict[str, float | None] = {}
    for item in ITEMS:
        value = measures[item]
        if value is None:
            status[item], scores[item] = STATUS_UNAVAILABLE, None
        else:
            status[item], scores[item] = limits[item].status(value), limits[item].score(value)

    if status[ITEM_DEPTH] == STATUS_CORRECT and measures[ITEM_TORSO_SHIN] is not None:
        # 얕은 반복은 depth로만 감점한다. torso_shin은 값만 남기고 판정·점수에서 뺀다.
        status[ITEM_TORSO_SHIN], scores[ITEM_TORSO_SHIN] = STATUS_RECORDED_ONLY, None

    judged = [item for item in ITEMS if scores[item] is not None]
    if not judged:
        return PostureScore(None, scores, status, None, False, measures)

    weight_sum = sum(weights[item] for item in judged)
    if weight_sum <= 0:
        raise ValueError("The weights of the judged items must add up to a positive number.")
    total = sum(weights[item] * scores[item] for item in judged) / weight_sum

    capped = any(status[item] == STATUS_CORRECT for item in judged) and total > cap
    if capped:
        total = cap

    deductions = {item: weights[item] / weight_sum * (100.0 - scores[item]) for item in judged}
    worst = max(judged, key=lambda item: deductions[item])  # 동점이면 ITEMS 순서(depth 먼저)
    return PostureScore(total, scores, status, worst if deductions[worst] > 0 else None, capped, measures)


def feedback_line(score: PostureScore) -> str | None:
    """반복 종료 시 한 줄: "78점 · 더 깊게 앉아보세요". 점수가 없으면 None(안내 문구만 보이는 경우), 감점이 없으면 점수만."""
    if score.total_score is None:
        return None
    text = f"{round(score.total_score)}점"
    if score.worst_item is not None:
        text += f" · {FEEDBACK_TEXT[score.worst_item]}"
    return text


def _missing(value: float | None) -> bool:
    return value is None or math.isnan(value)
