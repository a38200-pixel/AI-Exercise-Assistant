"""RepTracker: 평활 무릎각 시계열로 스쿼트 반복을 나누고, 기하 조건(+ML 2차 조건)을 만족한 반복만 확정한다.

반복: 평활 무릎각이 STANDING_KNEE_ANGLE 이상이던 뒤 REP_DESCENT_KNEE_ANGLE 미만으로 내려갔다가 다시
STANDING_KNEE_ANGLE 이상이 되면 1회다(히스테리시스). 시작은 반드시 잠긴 상태의 STANDING이어야 한다. BodyLock은
GeometryTracker가 정책(측면이 유지될 때만 잠금, 서 있는 중 측면이 아니면 해제, 반복 중 고정)대로 관리하고,
RepTracker는 그 결과를 쓴다. 그래서 측면이 아니면 반복을 세지 않는다(측면 전용).

확정 조건(모두 field_test_1 실측 기반 초기값, config/settings.py):
- 1차 기하: 반복 길이 >= REP_MIN_SECONDS, 엉덩이 하강량 >= REP_MIN_HIP_DROP(서 있을 때 대비, 다리 길이 비),
  서 있을 때 양발 간격 <= REP_MAX_ANKLE_GAP(다리 길이 비, 측면 전용).
- 2차 ML: 반복 구간의 stable 라벨 시간 중 REP_OTHER_EXERCISE_LABELS의 비율 <= REP_OTHER_EXERCISE_MAX_RATIO.
- 일부러 넣지 않은 것: 몸통 숙임 하한(몸통을 세우는 스쿼트를 탈락시킴), sit 비율(sit은 실제 스쿼트가 오분류되는 라벨),
  최저점 체류(여유 없음), 좌우 무릎 차이(반대 방향에서 먼 쪽 다리가 불안정). 의자·박스 앉았다 일어나기는 걸러지지
  않고 스쿼트로 센다(알려진 한계).
탈락한 반복은 RepResult(counted=False, reasons=...)로 남기고 개수에 넣지 않는다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from config.settings import (
    REP_BASELINE_SECONDS,
    REP_BOTTOM_PLATEAU_DEGREES,
    REP_DESCENT_KNEE_ANGLE,
    REP_MAX_ANKLE_GAP,
    REP_MAX_GAP_SECONDS,
    REP_MERGE_DROP_DEGREES,
    REP_MERGE_RISE_DEGREES,
    REP_MIN_HIP_DROP,
    LOCK_GUIDANCE_DELAY_SECONDS,
    REP_MIN_SECONDS,
    REP_OTHER_EXERCISE_LABELS,
    REP_OTHER_EXERCISE_MAX_RATIO,
    REP_RETURN_KNEE_ANGLE,
    REP_SET_BASELINE_ENABLED,
    REP_SET_BASELINE_HIP_PERCENTILE,
    REP_SET_BASELINE_MIN_SAMPLES,
    REP_SET_BASELINE_WINDOW_SECONDS,
    REP_STANDING_MAX_GAP_SECONDS,
    STANDING_KNEE_ANGLE,
)
from src.geometry_tracker import GeometryTracker, LockState, TrackedFrame
from src.posture_score import PostureScore, score_posture
from src.pose_geometry import LANDMARK_INDEX, landmarks_to_array, to_pixel_points


STATE_WAITING_LOCK = "WAITING_LOCK"  # 측면으로 서서 BodyLock이 걸리기를 기다림
STATE_STANDING = "STANDING"  # 잠긴 채 서 있음(다음 반복 대기)
STATE_IN_REP = "IN_REP"  # 내려갔다가 올라오는 중

# 안내 사유 코드(BodyLock이 오래 잡히지 않을 때). 문구는 UI가 정한다.
NOTICE_NOT_SIDE = "not_side"
NOTICE_FULL_BODY_INVALID = "full_body_invalid"

# 탈락 사유 코드
REASON_TOO_SHORT = "too_short"
REASON_SHALLOW_HIP_DROP = "shallow_hip_drop"
REASON_FEET_APART = "feet_apart"
REASON_OTHER_EXERCISE = "other_exercise"
REASON_NO_BASELINE = "no_baseline"
REASON_TRACKING_LOST = "tracking_lost"
REASON_LOCK_LOST = "lock_lost"

_MAX_LABEL_STEP_SECONDS = 0.5  # 이보다 긴 프레임 공백은 라벨 시간에 넣지 않는다
_NAN = float("nan")
_LABEL_NONE = "None"


# ---------------------------------------------------------------- 입력


@dataclass(frozen=True)
class RepMeasures:
    """한 프레임의 판정용 좌표(프레임 픽셀). crop이 프레임마다 달라 crop 원점을 더해 프레임 좌표로 바꾼 값이다."""

    hip_y: float
    heel_y: float
    leg_length: float  # |엉덩이-무릎| + |무릎-발목|
    ankle_gap: float  # |왼쪽 발목 x - 오른쪽 발목 x|


def measure_frame(landmarks: Sequence[Any], crop_bbox: Sequence[int], leg: str) -> RepMeasures:
    """잠근 다리 기준 판정용 좌표를 구한다. 얼굴 landmark는 쓰지 않는다."""
    points = landmarks_to_array(landmarks)
    crop_width, crop_height = crop_bbox[2] - crop_bbox[0], crop_bbox[3] - crop_bbox[1]
    pixels = to_pixel_points(points, crop_width, crop_height)

    def at(name: str) -> np.ndarray:
        return pixels[LANDMARK_INDEX[name]]

    hip, knee, ankle = at(f"{leg}_hip"), at(f"{leg}_knee"), at(f"{leg}_ankle")
    return RepMeasures(
        hip_y=float(crop_bbox[1] + hip[1]),
        heel_y=float(crop_bbox[1] + at(f"{leg}_heel")[1]),
        leg_length=float(np.linalg.norm(hip - knee) + np.linalg.norm(knee - ankle)),
        ankle_gap=float(abs(at("left_ankle")[0] - at("right_ankle")[0])),
    )


@dataclass(frozen=True)
class RepFrame:
    """RepTracker가 한 프레임에서 쓰는 값만 모은 입력. knee_smoothed가 None이면 전신 무효(각도를 믿지 못함)."""

    timestamp: float
    present: bool = False  # 사람과 Pose가 있는 프레임인가
    knee_smoothed: float | None = None
    locked: bool = False
    leg: str | None = None
    facing: str | None = None
    torso_signed: float | None = None
    shin_signed: float | None = None
    measures: RepMeasures | None = None
    side_now: bool | None = None  # 이 프레임만 본 측면 판정(안내 사유용)
    body_valid: bool | None = None  # 이 프레임의 전신 유효 여부(안내 사유용)
    knee_boundary: float | None = None  # 반복 경계 판정용 무릎각(REP_BOUNDARY_SIGNAL). None이면 knee_smoothed를 쓴다

    @property
    def boundary_knee(self) -> float | None:
        return self.knee_boundary if self.knee_boundary is not None else self.knee_smoothed

    @classmethod
    def missing(cls, timestamp: float, locked: bool = False) -> "RepFrame":
        """사람·Pose를 놓친 프레임. locked는 BodyLock이 아직 유지되고 있는지(놓침이 짧으면 잠금은 유지된다). 모르면 False(= 초기화)."""
        return cls(timestamp=timestamp, locked=locked)

    @classmethod
    def from_tracked(cls, tracked: TrackedFrame, measures: RepMeasures | None, timestamp: float) -> "RepFrame":
        geometry = tracked.geometry
        return cls(
            timestamp=timestamp,
            present=True,
            knee_smoothed=tracked.knee_angle_smoothed,
            locked=tracked.lock.locked,
            leg=tracked.lock.leg,
            facing=tracked.lock.facing,
            torso_signed=geometry.torso_angle_signed,
            shin_signed=geometry.shin_angle_signed,
            measures=measures,
            side_now=tracked.geometry_now.view.is_side,
            body_valid=tracked.geometry_now.full_body.valid,
            knee_boundary=tracked.knee_angle_boundary,
        )


def track_primary_person(
    tracker: GeometryTracker,
    primary_person: dict[str, Any] | None,
    frame_size: tuple[int, int],
    timestamp: float,
) -> tuple[TrackedFrame | None, LockState, RepFrame]:
    """주 사용자 한 명의 한 프레임을 기하 분석하고 RepTracker 입력까지 만든다.

    landmark가 없으면(사람·Pose를 놓침) 놓침 프레임으로 처리한다. 기하 계산이 실패해도(landmark 형식 오류)
    운동 기록이 멈추지 않도록 놓침 프레임으로 처리한다.
    """
    if primary_person is not None and primary_person.get("landmarks") is not None:
        try:
            tracked = tracker.update(
                primary_person["landmarks"],
                crop_bbox=primary_person["padded_bbox"],
                person_bbox=primary_person["bbox"],
                frame_size=frame_size,
                world_landmarks=primary_person.get("world_landmarks"),
                timestamp=timestamp,
            )
            measures = measure_frame(primary_person["landmarks"], primary_person["padded_bbox"], tracked.geometry.leg)
        except (ValueError, IndexError, KeyError):
            pass
        else:
            return tracked, tracked.lock, RepFrame.from_tracked(tracked, measures, timestamp)
    lock_state = tracker.update_missing(timestamp)
    return None, lock_state, RepFrame.missing(timestamp, locked=lock_state.locked)


# ---------------------------------------------------------------- 출력


@dataclass(frozen=True)
class RepResult:
    """반복 한 번의 결과. 값을 알 수 없으면 NaN. counted=False면 reasons에 탈락 사유가 있다.

    heel_rise_*, torso/shin_signed_at_bottom은 Phase 3 판정(또는 원자료 기록)을 위한 값이며 확정 조건에는 쓰이지 않는다.
    """

    counted: bool
    reasons: tuple[str, ...]
    t_start: float  # 내려가기 직전 마지막 '서 있음' 시각
    t_end: float  # 다시 서 있음으로 돌아온 시각(중단이면 중단 시각)
    t_bottom: float = _NAN
    leg: str | None = None
    facing: str | None = None
    min_knee_angle: float = _NAN
    hip_drop_norm: float = _NAN  # (최저점 엉덩이 y - 서 있을 때 엉덩이 y) / 다리 길이
    ankle_gap_norm: float = _NAN  # 서 있을 때 양발 간격 / 다리 길이
    descent_seconds: float = _NAN
    bottom_dwell_seconds: float = _NAN
    ascent_seconds: float = _NAN
    total_seconds: float = _NAN
    torso_signed_at_bottom: float = _NAN
    shin_signed_at_bottom: float = _NAN
    heel_rise_bottom_px: float = _NAN
    heel_rise_bottom_norm: float = _NAN
    other_exercise_ratio: float = _NAN
    pose_missing_ratio: float = _NAN
    label_seconds: dict[str, float] = field(default_factory=dict)
    # 확정된 반복의 자세 점수(깊이, 상체 정렬). 탈락·중단된 반복은 None. 표시와 로컬 기록용이며 카운트에는 쓰이지 않는다.
    posture: PostureScore | None = None


# ---------------------------------------------------------------- RepTracker


@dataclass
class _Sample:
    t: float
    knee: float  # 평활 무릎각, 무효면 NaN
    hip_y: float
    heel_y: float
    torso: float
    shin: float
    label: str


@dataclass
class _Baseline:
    hip_y: float
    heel_y: float
    leg_length: float
    ankle_gap: float


def _median(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=float)
    array = array[~np.isnan(array)]
    return float(np.median(array)) if len(array) else _NAN


def _percentile(values: Sequence[float], percentile: float) -> float:
    """NaN을 뺀 분위수. percentile=50이면 중앙값이다. 엉덩이 y는 작을수록 높으므로 낮은 분위수가 '높이 선' 쪽이다."""
    array = np.asarray(values, dtype=float)
    array = array[~np.isnan(array)]
    return float(np.percentile(array, percentile)) if len(array) else _NAN


def _posture_event(score: PostureScore | None) -> dict[str, Any] | None:
    """로그용 자세 점수(확정된 반복만). JSON에 쓸 수 있게 NaN/None을 정리한다."""
    if score is None:
        return None
    return {
        "total": _json_number(score.total_score),
        "worst_item": score.worst_item,
        "capped": score.capped,
        "item_status": dict(score.item_status),
        "item_scores": {k: _json_number(v) for k, v in score.item_scores.items()},
        "measures": {k: _json_number(v) for k, v in score.measures.items()},
    }


def _or_nan(value: float | None) -> float:
    return _NAN if value is None else float(value)


def _json_number(value: float | None) -> float | None:
    """로그용: NaN은 JSON으로 쓸 수 없으므로 None으로 바꾼다."""
    if value is None or math.isnan(value):
        return None
    return round(float(value), 4)


class RepTracker:
    def __init__(
        self,
        *,
        standing_angle: float = STANDING_KNEE_ANGLE,
        descent_angle: float = REP_DESCENT_KNEE_ANGLE,
        max_gap_seconds: float = REP_MAX_GAP_SECONDS,
        min_seconds: float = REP_MIN_SECONDS,
        min_hip_drop: float = REP_MIN_HIP_DROP,
        max_ankle_gap: float = REP_MAX_ANKLE_GAP,
        other_labels: Sequence[str] = REP_OTHER_EXERCISE_LABELS,
        other_max_ratio: float = REP_OTHER_EXERCISE_MAX_RATIO,
        baseline_seconds: float = REP_BASELINE_SECONDS,
        plateau_degrees: float = REP_BOTTOM_PLATEAU_DEGREES,
        notice_delay_seconds: float = LOCK_GUIDANCE_DELAY_SECONDS,
        merge_rise_degrees: float = REP_MERGE_RISE_DEGREES,
        merge_drop_degrees: float = REP_MERGE_DROP_DEGREES,
        standing_max_gap_seconds: float = REP_STANDING_MAX_GAP_SECONDS,
        return_angle: float | None = REP_RETURN_KNEE_ANGLE,
        set_baseline: bool = REP_SET_BASELINE_ENABLED,
        set_baseline_window_seconds: float = REP_SET_BASELINE_WINDOW_SECONDS,
        set_baseline_min_samples: int = REP_SET_BASELINE_MIN_SAMPLES,
    ) -> None:
        if descent_angle >= standing_angle:
            raise ValueError("descent_angle must be below standing_angle (hysteresis).")
        if return_angle is not None and not descent_angle < return_angle <= standing_angle:
            raise ValueError("return_angle must be above descent_angle and not above standing_angle.")
        self._standing_angle = standing_angle
        self._descent_angle = descent_angle
        # 복귀 각도를 낮추면 끝나는 프레임의 엉덩이가 더 낮으므로, 기준 높이는 세트 단위로 잡아야 한다(함께 켠다).
        self._return_angle = standing_angle if return_angle is None else return_angle
        self._set_baseline = bool(set_baseline) or self._return_angle < standing_angle
        self._set_window = set_baseline_window_seconds
        self._set_min_samples = set_baseline_min_samples
        self._max_gap = max_gap_seconds
        self._standing_max_gap = standing_max_gap_seconds
        self._min_seconds = min_seconds
        self._min_hip_drop = min_hip_drop
        self._max_ankle_gap = max_ankle_gap
        self._other_labels = frozenset(other_labels)
        self._other_max_ratio = other_max_ratio
        self._baseline_seconds = baseline_seconds
        self._plateau = plateau_degrees
        self._notice_delay = notice_delay_seconds
        self._merge_rise = merge_rise_degrees
        self._merge_drop = merge_drop_degrees
        self.last_result: RepResult | None = None
        self.reset()

    # -- 상태

    @property
    def state(self) -> str:
        return self._state

    @property
    def guidance(self) -> str:
        """화면 안내용 코드(문구는 UI가 정한다)."""
        return {STATE_WAITING_LOCK: "need_side_standing", STATE_STANDING: "ready", STATE_IN_REP: "in_rep"}[self._state]

    @property
    def notice(self) -> str | None:
        """BodyLock이 LOCK_GUIDANCE_DELAY_SECONDS 넘게 잡히지 않을 때의 사유(NOTICE_*). 잠금이 잡히면 None."""
        return self._notice

    def reset(self) -> None:
        """모드 변경·새 세션·리셋 시 진행 중인 반복과 기준값을 버린다."""
        self._events: list[dict[str, Any]] = []  # 진단 이벤트(로그용). pop_events()로 가져간다.
        self._extrema: dict[str, float] = {}
        self._merge_count = 0
        self._unlocked_since: float | None = None
        self._last_present = 0.0
        self._notice_reasons: list[tuple[float, str | None]] = []
        self._notice: str | None = None
        self._state = STATE_WAITING_LOCK
        self._baseline_samples: list[tuple[float, RepMeasures]] = []
        self._set_samples: list[tuple[float, RepMeasures]] = []  # 세트 단위 기준 높이용(잠금이 유지되는 동안의 완전히 선 프레임)
        self._last_stand: _Sample | None = None
        self._idle_seen_t = 0.0  # 서 있는 중(STANDING) 마지막으로 사람이 보이고 잠겨 있던 시각(놓침 길이를 재는 기준)
        self._samples: list[_Sample] = []
        self._baseline: _Baseline | None = None
        self._leg: str | None = None
        self._facing: str | None = None
        self._last_valid_t = 0.0
        self.last_result = None

    # -- 갱신

    def update(self, frame: RepFrame, stable_label: str | None) -> RepResult | None:
        """한 프레임을 넣는다. 반복이 끝나거나(확정·탈락) 중단되면 그 RepResult를, 아니면 None을 돌려준다."""
        self._update_notice(frame)
        if self._state == STATE_IN_REP:
            result = self._update_in_rep(frame, stable_label)
        else:
            result = self._update_idle(frame, stable_label)
        if result is not None:
            self.last_result = result
            self._events.append(self._rep_event(result))
        return result

    def pop_events(self) -> list[dict[str, Any]]:
        """마지막 호출 이후에 쌓인 진단 이벤트를 비우며 돌려준다. 시각은 update()에 넣은 timestamp와 같은 기준이다.

        rep_end: 반복 후보가 끝날 때마다(확정·탈락·중단) 측정값, 기준값, 탈락 사유.
        rep_merge_suspect: 반복 중 무릎각이 올라왔다가 STANDING 복귀 각도에 닿지 못한 채 다시 내려간 지점.
        이 이벤트는 로그용이며 카운트에는 영향이 없다.
        """
        events, self._events = self._events, []
        return events

    def _rep_event(self, result: RepResult) -> dict[str, Any]:
        return {
            "kind": "rep_end",
            "counted": result.counted,
            "reasons": list(result.reasons),
            "timeout": REASON_TRACKING_LOST in result.reasons,  # 무릎각이 max_gap초 넘게 비어 중단(반복 길이 상한은 없다)
            "t": result.t_end,
            "t_start": result.t_start,
            "t_bottom": _json_number(result.t_bottom),
            "t_end": result.t_end,
            "min_knee": _json_number(result.min_knee_angle),
            "total_seconds": _json_number(result.total_seconds),
            "hip_drop_norm": _json_number(result.hip_drop_norm),
            "ankle_gap_norm": _json_number(result.ankle_gap_norm),
            "other_exercise_ratio": _json_number(result.other_exercise_ratio),
            "pose_missing_ratio": _json_number(result.pose_missing_ratio),
            "label_seconds": result.label_seconds,
            "merge_suspects": self._merge_count,
            "posture": _posture_event(result.posture),
            "limits": {
                "min_seconds": self._min_seconds,
                "min_hip_drop": self._min_hip_drop,
                "max_ankle_gap": self._max_ankle_gap,
                "other_max_ratio": self._other_max_ratio,
                "standing_angle": self._standing_angle,
            },
        }

    def _track_merge(self, timestamp: float, knee: float) -> None:
        """반복 중 '올라왔다가 STANDING 복귀 각도에 닿지 못하고 다시 내려감'을 찾는다(반복 두 개가 하나로 합쳐졌을 가능성)."""
        ex = self._extrema
        if knee < ex["min_k"]:
            ex.update(min_k=knee, min_t=timestamp, peak_k=knee, peak_t=timestamp)  # 새 최저점: 올라온 기록을 지운다
        elif knee > ex["peak_k"]:
            ex.update(peak_k=knee, peak_t=timestamp)
        rise, drop = ex["peak_k"] - ex["min_k"], ex["peak_k"] - knee
        if rise >= self._merge_rise and drop >= self._merge_drop:
            self._merge_count += 1
            self._events.append(
                {
                    "kind": "rep_merge_suspect",
                    "t": timestamp,
                    "t_min": ex["min_t"],
                    "t_peak": ex["peak_t"],
                    "min_knee": round(ex["min_k"], 4),
                    "peak_knee": round(ex["peak_k"], 4),  # 올라온 최대 무릎각
                    "rise_degrees": round(rise, 4),
                    "drop_degrees": round(drop, 4),
                    "standing_angle": self._standing_angle,
                    "peak_shortfall": round(self._standing_angle - ex["peak_k"], 4),  # STANDING 복귀 각도까지 모자란 각도
                    "rep_t_start": self._samples[0].t,
                }
            )
            ex.update(min_k=knee, min_t=timestamp, peak_k=knee, peak_t=timestamp)

    def _update_notice(self, frame: RepFrame) -> None:
        """잠금이 안 잡힌 시간이 지연 시간을 넘으면, 그 사이 가장 많았던 사유를 안내 사유로 삼는다."""
        t = frame.timestamp
        if frame.present and frame.locked:
            self._unlocked_since = None
            self._notice_reasons = []
            self._notice = None
            return
        if not frame.present:
            # 사람이 없는 프레임은 사유가 아니다. 오래 없으면(자리를 떠남) 처음부터 센다.
            if self._unlocked_since is not None and t - self._last_present > self._notice_delay:
                self._unlocked_since = None
                self._notice_reasons = []
            self._notice = None if self._unlocked_since is None else self._notice
            return
        self._last_present = t
        if self._unlocked_since is None:
            self._unlocked_since = t
        reason = None
        if frame.body_valid is False:
            reason = NOTICE_FULL_BODY_INVALID
        elif frame.side_now is False:
            reason = NOTICE_NOT_SIDE
        self._notice_reasons.append((t, reason))
        cutoff = t - self._notice_delay
        self._notice_reasons = [(rt, r) for rt, r in self._notice_reasons if rt >= cutoff]
        if t - self._unlocked_since < self._notice_delay:
            self._notice = None
            return
        counts: dict[str | None, int] = {}
        for _, r in self._notice_reasons:
            counts[r] = counts.get(r, 0) + 1
        top = max(counts, key=lambda key: counts[key])
        self._notice = top  # 가장 많은 것이 "사유 없음"(측면이고 전신 유효)이면 None

    def _sample(self, frame: RepFrame, label: str | None) -> _Sample:
        measures = frame.measures
        return _Sample(
            t=frame.timestamp,
            knee=_or_nan(frame.knee_smoothed),
            hip_y=measures.hip_y if measures else _NAN,
            heel_y=measures.heel_y if measures else _NAN,
            torso=_or_nan(frame.torso_signed),
            shin=_or_nan(frame.shin_signed),
            label=label if label is not None else _LABEL_NONE,
        )

    def _update_idle(self, frame: RepFrame, label: str | None) -> RepResult | None:
        """STANDING 이외(WAITING_LOCK 포함)의 프레임 처리.

        놓침(사람·Pose 없음) 처리 규칙: 잠금이 유지되는 STANDING에서 놓친 시간이 REP_STANDING_MAX_GAP_SECONDS 이하이면 상태와 서 있던
        기준값을 그대로 둔다. 다시 보인 첫 프레임이 이미 내려가는 중(< 하강 기준)이어도 직전이 STANDING이므로 반복을 시작한다.
        넘기거나 잠금이 풀렸으면 WAITING_LOCK으로 초기화한다. IN_REP 중 놓침은 _update_in_rep이 REP_MAX_GAP_SECONDS(같은 1.5초 기본값)까지
        보간하고 넘으면 중단(tracking_lost)한다. 두 규칙의 기준은 모두 '마지막으로 유효했던 시각'으로부터의 경과 시간이다.
        """
        if (
            not frame.present
            and frame.locked
            and self._state == STATE_STANDING
            and self._last_stand is not None
            and frame.timestamp - self._idle_seen_t <= self._standing_max_gap
        ):
            return None
        if not (frame.present and frame.locked):
            self._state = STATE_WAITING_LOCK
            self._baseline_samples.clear()
            self._set_samples.clear()
            self._last_stand = None
            return None
        self._idle_seen_t = frame.timestamp
        knee = frame.boundary_knee
        if self._state == STATE_WAITING_LOCK:
            if knee is None or knee < self._standing_angle:
                return None
            self._state = STATE_STANDING
        if knee is None:
            return None
        if knee >= self._standing_angle:
            self._note_standing(frame, label)
        elif knee < self._descent_angle and self._last_stand is not None:
            self._start_rep(frame, label)
        return None

    def _note_standing(self, frame: RepFrame, label: str | None) -> None:
        self._last_stand = self._sample(frame, label)
        if frame.measures is not None:
            self._baseline_samples.append((frame.timestamp, frame.measures))
        cutoff = frame.timestamp - self._baseline_seconds
        self._baseline_samples = [(t, m) for t, m in self._baseline_samples if t >= cutoff]
        if self._set_baseline and frame.measures is not None and (frame.knee_smoothed or 0.0) >= self._standing_angle:
            self._set_samples.append((frame.timestamp, frame.measures))
            set_cutoff = frame.timestamp - self._set_window
            self._set_samples = [(t, m) for t, m in self._set_samples if t >= set_cutoff]

    def _start_rep(self, frame: RepFrame, label: str | None) -> None:
        stand = self._last_stand
        assert stand is not None
        measures = [m for _, m in self._baseline_samples]
        hip_percentile = 50.0
        if self._set_baseline and len(self._set_samples) >= self._set_min_samples:
            measures = [m for _, m in self._set_samples]  # 세트 단위 기준 높이(부족하면 직전 1초로 되돌아간다)
            hip_percentile = REP_SET_BASELINE_HIP_PERCENTILE
        self._baseline = (
            _Baseline(
                hip_y=_percentile([m.hip_y for m in measures], hip_percentile),
                heel_y=_median([m.heel_y for m in measures]),
                leg_length=_median([m.leg_length for m in measures]),
                ankle_gap=_median([m.ankle_gap for m in measures]),
            )
            if measures
            else None
        )
        self._leg, self._facing = frame.leg, frame.facing
        self._samples = [stand, self._sample(frame, label)]
        self._last_valid_t = frame.timestamp
        self._merge_count = 0
        knee = float(frame.boundary_knee)
        self._extrema = {"min_k": knee, "min_t": frame.timestamp, "peak_k": knee, "peak_t": frame.timestamp}
        self._state = STATE_IN_REP

    def _update_in_rep(self, frame: RepFrame, label: str | None) -> RepResult | None:
        timestamp = frame.timestamp
        if frame.present and not frame.locked:
            return self._abort(timestamp, REASON_LOCK_LOST)
        self._samples.append(self._sample(frame, label))
        knee = frame.boundary_knee if frame.present else None
        if knee is None:
            if timestamp - self._last_valid_t > self._max_gap:
                return self._abort(timestamp, REASON_TRACKING_LOST)
            return None
        self._last_valid_t = timestamp
        if knee >= self._return_angle:
            return self._complete(frame)
        self._track_merge(timestamp, knee)
        return None

    def _abort(self, timestamp: float, reason: str) -> RepResult:
        knees = np.array([s.knee for s in self._samples])
        result = RepResult(
            counted=False,
            reasons=(reason,),
            t_start=self._samples[0].t,
            t_end=timestamp,
            leg=self._leg,
            facing=self._facing,
            min_knee_angle=float(np.nanmin(knees)) if not np.all(np.isnan(knees)) else _NAN,
        )
        self._back_to_waiting()
        return result

    def _back_to_waiting(self) -> None:
        self._state = STATE_WAITING_LOCK
        self._samples = []
        self._baseline = None
        self._baseline_samples.clear()
        self._set_samples.clear()
        self._last_stand = None

    def _complete(self, frame: RepFrame) -> RepResult:
        samples = self._samples
        times = np.array([s.t for s in samples])
        knees = np.array([s.knee for s in samples])
        bottom = int(np.nanargmin(knees))

        near = slice(max(0, bottom - 2), bottom + 3)
        wide = slice(max(0, bottom - 5), bottom + 6)
        hip_bottom = _median([s.hip_y for s in samples[near]])
        heel_bottom = _median([s.heel_y for s in samples[wide]])
        torso_bottom = _median([s.torso for s in samples[near]])
        shin_bottom = _median([s.shin for s in samples[near]])

        base = self._baseline
        usable_base = base is not None and base.leg_length > 0 and not math.isnan(base.hip_y)
        hip_drop = (hip_bottom - base.hip_y) / base.leg_length if usable_base and not math.isnan(hip_bottom) else _NAN
        ankle_gap = base.ankle_gap / base.leg_length if usable_base and not math.isnan(base.ankle_gap) else _NAN
        heel_rise = base.heel_y - heel_bottom if usable_base and not math.isnan(base.heel_y) else _NAN

        plateau = np.nan_to_num(knees, nan=999.0) <= knees[bottom] + self._plateau
        first = bottom
        while first - 1 >= 0 and plateau[first - 1]:
            first -= 1
        last = bottom
        while last + 1 < len(samples) and plateau[last + 1]:
            last += 1

        # 라벨 시간: 각 프레임이 다음 프레임까지 차지한 시간(긴 공백은 제외)
        steps = np.append(np.diff(times), 0.0)
        steps[steps > _MAX_LABEL_STEP_SECONDS] = 0.0
        label_seconds: dict[str, float] = {}
        for sample, step in zip(samples, steps):
            label_seconds[sample.label] = label_seconds.get(sample.label, 0.0) + float(step)
        missing_seconds = label_seconds.get(_LABEL_NONE, 0.0)
        total_label_seconds = sum(label_seconds.values())
        seen_seconds = total_label_seconds - missing_seconds
        other_seconds = sum(v for k, v in label_seconds.items() if k in self._other_labels)
        other_ratio = other_seconds / seen_seconds if seen_seconds > 0 else 0.0

        t_start, t_end = float(times[0]), float(times[-1])
        total = t_end - t_start
        reasons: list[str] = []
        if not usable_base or math.isnan(hip_drop):
            reasons.append(REASON_NO_BASELINE)
        if total < self._min_seconds:
            reasons.append(REASON_TOO_SHORT)
        if not math.isnan(hip_drop) and hip_drop < self._min_hip_drop:
            reasons.append(REASON_SHALLOW_HIP_DROP)
        if not math.isnan(ankle_gap) and ankle_gap > self._max_ankle_gap:
            reasons.append(REASON_FEET_APART)
        if other_ratio > self._other_max_ratio:
            reasons.append(REASON_OTHER_EXERCISE)

        result = RepResult(
            counted=not reasons,
            reasons=tuple(reasons),
            t_start=t_start,
            t_end=t_end,
            t_bottom=float(times[bottom]),
            leg=self._leg,
            facing=self._facing,
            min_knee_angle=float(knees[bottom]),
            hip_drop_norm=hip_drop,
            ankle_gap_norm=ankle_gap,
            descent_seconds=float(times[first] - t_start),
            bottom_dwell_seconds=float(times[last] - times[first]),
            ascent_seconds=float(t_end - times[last]),
            total_seconds=total,
            torso_signed_at_bottom=torso_bottom,
            shin_signed_at_bottom=shin_bottom,
            heel_rise_bottom_px=heel_rise,
            heel_rise_bottom_norm=heel_rise / base.leg_length if usable_base and not math.isnan(heel_rise) else _NAN,
            other_exercise_ratio=other_ratio,
            pose_missing_ratio=missing_seconds / total_label_seconds if total_label_seconds > 0 else 0.0,
            label_seconds={k: round(v, 4) for k, v in label_seconds.items()},
            posture=(
                score_posture(float(knees[bottom]), torso_bottom, shin_bottom) if not reasons else None
            ),
        )

        # 서 있음으로 돌아왔으므로 다음 반복의 기준값을 지금부터 다시 모은다.
        self._state = STATE_STANDING
        self._samples = []
        self._baseline = None
        self._baseline_samples = []
        self._last_stand = None
        self._idle_seen_t = frame.timestamp
        self._note_standing(frame, samples[-1].label)
        return result
