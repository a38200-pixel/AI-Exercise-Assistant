"""자세 점수(순수 함수): 경계값 직전/직후, 교정 항목의 총점 상한, worst_item 선택, depth 교정 시 torso_shin 기록만, 결측 처리."""

import inspect
import math
from pathlib import Path

import pytest

import config.settings as settings
from src import posture_score
from src.posture_score import (
    ITEM_DEPTH,
    ITEM_TORSO_SHIN,
    STATUS_CAUTION,
    STATUS_CORRECT,
    STATUS_NORMAL,
    STATUS_RECORDED_ONLY,
    STATUS_UNAVAILABLE,
    ItemLimits,
    feedback_line,
    score_posture,
    torso_shin_difference,
)


def posture(depth, difference=10.0, **kwargs):
    """depth(최저 무릎각)와 |몸통각 - 정강이각|(difference)를 직접 지정한다."""
    return score_posture(depth, 30.0 + difference, 30.0, **kwargs)


# ---------------------------------------------------------------- 설정값과 명칭


def test_the_default_limits_and_weights_come_from_the_settings() -> None:
    assert (settings.POSTURE_DEPTH_NORMAL_MAX, settings.POSTURE_DEPTH_CORRECT_MIN) == (80.0, 95.0)
    assert (settings.POSTURE_TORSO_SHIN_NORMAL_MAX, settings.POSTURE_TORSO_SHIN_CORRECT_MIN) == (25.0, 35.0)
    assert settings.POSTURE_WEIGHT_DEPTH + settings.POSTURE_WEIGHT_TORSO_SHIN == pytest.approx(1.0)
    assert 0.0 < settings.POSTURE_SCORE_CAP_WITH_CORRECTION < 100.0


def test_the_score_is_called_the_posture_score_and_never_accuracy() -> None:
    assert posture_score.SCORE_LABEL == "자세 점수"
    source = Path(posture_score.__file__).read_text(encoding="utf-8")
    assert "정확도" not in source and "accuracy" not in source.lower()
    assert "정확도" not in str(posture_score.FEEDBACK_TEXT)


def test_only_depth_and_torso_shin_are_judged_and_tempo_or_heel_are_not_inputs() -> None:
    assert posture_score.ITEMS == (ITEM_DEPTH, ITEM_TORSO_SHIN)
    parameters = set(inspect.signature(score_posture).parameters)
    assert parameters == {"min_knee_angle", "torso_signed", "shin_signed", "limits", "weights", "cap"}


def test_limits_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        ItemLimits(95.0, 80.0)
    with pytest.raises(ValueError):
        ItemLimits(80.0, 80.0)


# ---------------------------------------------------------------- 경계값 직전/직후

DEPTH_CASES = [
    (60.0, STATUS_NORMAL, 100.0),
    (80.0, STATUS_NORMAL, 100.0),  # 정상 경계 위
    (80.01, STATUS_CAUTION, None),  # 직후
    (87.5, STATUS_CAUTION, 50.0),  # 선형 중간
    (94.99, STATUS_CAUTION, None),  # 교정 직전
    (95.0, STATUS_CORRECT, 0.0),  # 교정 경계 위
    (120.0, STATUS_CORRECT, 0.0),
]


@pytest.mark.parametrize(("depth", "status", "score"), DEPTH_CASES)
def test_depth_status_and_score_around_the_limits(depth, status, score) -> None:
    result = posture(depth)
    assert result.item_status[ITEM_DEPTH] == status
    if score is not None:
        assert result.item_scores[ITEM_DEPTH] == pytest.approx(score)
    elif status == STATUS_CAUTION:
        assert 0.0 < result.item_scores[ITEM_DEPTH] < 100.0


TORSO_SHIN_CASES = [
    (0.0, STATUS_NORMAL, 100.0),
    (25.0, STATUS_NORMAL, 100.0),
    (25.01, STATUS_CAUTION, None),
    (30.0, STATUS_CAUTION, 50.0),
    (34.99, STATUS_CAUTION, None),
    (35.0, STATUS_CORRECT, 0.0),
    (60.0, STATUS_CORRECT, 0.0),
]


@pytest.mark.parametrize(("difference", "status", "score"), TORSO_SHIN_CASES)
def test_torso_shin_status_and_score_around_the_limits(difference, status, score) -> None:
    result = posture(70.0, difference)  # depth는 정상(70도)
    assert result.item_status[ITEM_TORSO_SHIN] == status
    if score is not None:
        assert result.item_scores[ITEM_TORSO_SHIN] == pytest.approx(score)
    elif status == STATUS_CAUTION:
        assert 0.0 < result.item_scores[ITEM_TORSO_SHIN] < 100.0


def test_the_score_falls_monotonically_as_the_measure_gets_worse() -> None:
    depth_scores = [posture(d).item_scores[ITEM_DEPTH] for d in range(70, 100)]
    torso_scores = [posture(70.0, d).item_scores[ITEM_TORSO_SHIN] for d in range(0, 45)]
    assert depth_scores == sorted(depth_scores, reverse=True)
    assert torso_scores == sorted(torso_scores, reverse=True)


def test_torso_shin_uses_the_difference_not_the_absolute_torso_angle() -> None:
    upright = score_posture(70.0, 80.0, 70.0)  # 몸통 80도로 많이 숙였지만 정강이도 70도: 차이 10도
    assert upright.measures[ITEM_TORSO_SHIN] == pytest.approx(10.0)
    assert upright.item_status[ITEM_TORSO_SHIN] == STATUS_NORMAL
    assert score_posture(70.0, 10.0, 40.0).measures[ITEM_TORSO_SHIN] == pytest.approx(30.0)  # 부호가 반대여도 절대 차이
    assert torso_shin_difference(None, 5.0) is None


# ---------------------------------------------------------------- 총점, 상한, depth 교정 시 torso_shin


def test_a_perfect_rep_scores_100_with_no_worst_item() -> None:
    result = posture(75.0, 10.0)
    assert result.total_score == pytest.approx(100.0)
    assert result.worst_item is None and result.capped is False


def test_the_total_is_the_weighted_average_of_the_item_scores() -> None:
    result = posture(87.5, 30.0)  # 두 항목 모두 50점
    assert result.total_score == pytest.approx(50.0)
    result = posture(87.5, 10.0)  # depth 50점, torso_shin 100점, 가중치 같음
    assert result.total_score == pytest.approx(75.0)
    weighted = posture(87.5, 10.0, weights={ITEM_DEPTH: 0.8, ITEM_TORSO_SHIN: 0.2})
    assert weighted.total_score == pytest.approx(0.8 * 50.0 + 0.2 * 100.0)


def test_depth_in_the_correct_range_leaves_torso_shin_recorded_but_not_judged() -> None:
    result = posture(110.0, 50.0)  # 얕고 몸통도 많이 숙임
    assert result.item_status[ITEM_DEPTH] == STATUS_CORRECT
    assert result.item_status[ITEM_TORSO_SHIN] == STATUS_RECORDED_ONLY
    assert result.item_scores[ITEM_TORSO_SHIN] is None
    assert result.measures[ITEM_TORSO_SHIN] == pytest.approx(50.0)  # 값은 남는다
    assert result.worst_item == ITEM_DEPTH
    assert result.total_score == pytest.approx(0.0)  # depth 하나로만 계산한다


def test_a_shallow_rep_is_not_penalised_twice_for_the_lean() -> None:
    lean, upright = posture(110.0, 50.0), posture(110.0, 5.0)
    assert lean.total_score == pytest.approx(upright.total_score)
    assert lean.worst_item == upright.worst_item == ITEM_DEPTH


def test_a_correct_item_caps_the_total_even_when_the_weights_would_allow_more() -> None:
    tilted = {ITEM_DEPTH: 0.9, ITEM_TORSO_SHIN: 0.1}
    result = posture(70.0, 40.0, weights=tilted)  # depth 100점, torso_shin 교정(0점): 가중 평균 90
    assert result.item_status[ITEM_TORSO_SHIN] == STATUS_CORRECT
    assert result.total_score == pytest.approx(settings.POSTURE_SCORE_CAP_WITH_CORRECTION)
    assert result.capped is True
    assert posture(70.0, 40.0, weights=tilted, cap=30.0).total_score == pytest.approx(30.0)


def test_the_cap_does_not_apply_without_a_correct_item() -> None:
    tilted = {ITEM_DEPTH: 0.9, ITEM_TORSO_SHIN: 0.1}
    result = posture(70.0, 30.0, weights=tilted, cap=40.0)  # torso_shin은 주의(50점): 가중 평균 95
    assert result.total_score == pytest.approx(95.0)
    assert result.capped is False


def test_with_the_default_weights_a_correct_item_cannot_pass_the_natural_maximum() -> None:
    result = posture(70.0, 40.0)
    assert result.total_score == pytest.approx(50.0)
    assert result.total_score <= settings.POSTURE_SCORE_CAP_WITH_CORRECTION


# ---------------------------------------------------------------- worst_item


@pytest.mark.parametrize(
    ("depth", "difference", "worst"),
    [
        (90.0, 10.0, ITEM_DEPTH),  # depth만 감점
        (70.0, 32.0, ITEM_TORSO_SHIN),  # torso_shin만 감점
        (87.5, 26.0, ITEM_DEPTH),  # depth 50점 vs torso_shin 90점
        (82.0, 32.0, ITEM_TORSO_SHIN),  # depth 약 87점 vs torso_shin 30점
    ],
)
def test_worst_item_is_the_item_with_the_largest_deduction(depth, difference, worst) -> None:
    result = posture(depth, difference)
    assert result.worst_item == worst
    deductions = {i: 100.0 - result.item_scores[i] for i in (ITEM_DEPTH, ITEM_TORSO_SHIN)}
    assert deductions[worst] == max(deductions.values())


def test_a_tie_goes_to_depth_and_the_weights_can_change_the_winner() -> None:
    assert posture(87.5, 30.0).worst_item == ITEM_DEPTH  # 둘 다 50점: 동점은 depth
    heavy_torso = posture(87.5, 30.0, weights={ITEM_DEPTH: 0.2, ITEM_TORSO_SHIN: 0.8})
    assert heavy_torso.worst_item == ITEM_TORSO_SHIN  # 가중 감점이 더 큰 쪽


# ---------------------------------------------------------------- 결측


def test_a_missing_torso_or_shin_is_unavailable_and_the_total_uses_depth_alone() -> None:
    for torso, shin in ((None, 30.0), (40.0, None), (math.nan, 30.0)):
        result = score_posture(87.5, torso, shin)
        assert result.item_status[ITEM_TORSO_SHIN] == STATUS_UNAVAILABLE
        assert result.item_scores[ITEM_TORSO_SHIN] is None
        assert result.total_score == pytest.approx(50.0)
        assert result.worst_item == ITEM_DEPTH


def test_a_missing_depth_leaves_only_torso_shin() -> None:
    result = score_posture(None, 60.0, 30.0)  # 차이 30도: 50점
    assert result.item_status[ITEM_DEPTH] == STATUS_UNAVAILABLE
    assert result.total_score == pytest.approx(50.0)
    assert result.worst_item == ITEM_TORSO_SHIN


def test_without_any_measure_there_is_no_score() -> None:
    result = score_posture(math.nan, None, None)
    assert result.total_score is None and result.worst_item is None and result.capped is False
    assert feedback_line(result) is None


# ---------------------------------------------------------------- 한 줄 피드백


def test_the_feedback_line_shows_the_score_and_the_advice_for_the_worst_item() -> None:
    result = score_posture(86.6, 40.0, 30.0)  # depth 약 56점, torso_shin 100점
    assert result.total_score == pytest.approx(78.0, abs=0.1)
    assert feedback_line(result) == "78점 · 더 깊게 앉아보세요"
    lean = posture(70.0, 32.0)  # depth 100점, torso_shin 30점 -> 65점
    assert feedback_line(lean) == "65점 · 상체를 조금 더 세워보세요"


def test_a_perfect_rep_shows_only_the_score() -> None:
    assert feedback_line(posture(75.0, 10.0)) == "100점"
