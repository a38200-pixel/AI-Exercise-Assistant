"""field_test_1 분석용 공통 함수: 세션 파일 매칭, 프레임 배열화, 오프라인 반복 구간 추출, 반복별 지표.

로그 원본은 읽기만 한다. 실행은 scripts/analysis/field_test_1_analysis.py가 한다.
모든 각도는 로그의 landmark(crop 정규화)를 프레임 픽셀로 되돌려 계산한다. crop은 프레임마다 달라지므로
`crop_bbox`로 복원해야 프레임 사이를 비교할 수 있다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# 실측 일정표(사용자 제공). 세션 id -> 시작 시각 hh:mm, 설명, 실제 횟수, 기록 당시 v0.1.x 화면 카운트(None = 미기록)
PLAN: list[dict[str, Any]] = [
    {"id": "0", "hhmm": "13:55", "what": "시험, 측면 정상", "actual": 6, "screen": None, "use": False},
    {"id": "1(무효)", "hhmm": "14:03", "what": "측면 정상, 횟수 착오로 중단", "actual": None, "screen": None, "use": False},
    {"id": "1", "hhmm": "14:05", "what": "측면 정상(평행)", "actual": 10, "screen": None, "use": True},
    {"id": "2", "hhmm": "14:08", "what": "측면 깊게(deep)", "actual": 8, "screen": 7, "use": True},
    {"id": "3", "hhmm": "14:10", "what": "측면 얕음", "actual": 8, "screen": 5, "use": True},
    {"id": "4", "hhmm": "14:12", "what": "측면 상체 숙임", "actual": 8, "screen": 7, "use": True},
    {"id": "5", "hhmm": "14:14", "what": "측면 뒤꿈치 들림", "actual": 8, "screen": None, "use": True},
    {"id": "6", "hhmm": "14:17", "what": "사선 정상", "actual": 5, "screen": None, "use": True},
    {"id": "7", "hhmm": "14:19", "what": "정면 정상", "actual": 5, "screen": 2, "use": True},
    {"id": "8a", "hhmm": "14:21", "what": "제자리 걷기 15초(스쿼트 아님)", "actual": 0, "screen": 0, "use": True},
    {"id": "8b", "hhmm": "14:23", "what": "의자 앉았다 일어나기(스쿼트 아님)", "actual": 0, "screen": 2, "use": True, "motions": 3},
    {"id": "8c", "hhmm": "14:25", "what": "런지 스트레칭(스쿼트 아님)", "actual": 0, "screen": 1, "use": True, "motions": 3},
    {"id": "9", "hhmm": "14:27", "what": "측면 반대 방향 정상", "actual": 5, "screen": None, "use": True},
]
SIDE_SQUAT_IDS = ("1", "2", "3", "4", "5", "9")  # 측면, 스쿼트
NON_SQUAT_IDS = ("8a", "8b", "8c")

STANDING_ANGLE = 160.0  # 임시 반복 규칙: 서 있음(올라옴) 기준
DESCENT_ANGLE = 150.0  # 임시 반복 규칙: 내려감 기준
MAX_INTERP_GAP_S = 1.5  # 전신 무효로 평활 무릎각이 비는 구간을 이 시간까지는 선형 보간(세션 2의 올라오는 끝 1.25초 공백 때문)
BOTTOM_PLATEAU_DEG = 10.0  # 최저점 체류: 평활 무릎각이 (최저 + 이 값) 이하인 시간

LABELS = ("stand", "squat", "stretch", "sit", "bendover", "walk", "run", "jump", "lying", "None")
NAMES = (
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right", "left_shoulder", "right_shoulder", "left_elbow",
    "right_elbow", "left_wrist", "right_wrist", "left_pinky", "right_pinky", "left_index", "right_index",
    "left_thumb", "right_thumb", "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle",
    "left_heel", "right_heel", "left_foot_index", "right_foot_index",
)
IDX = {name: i for i, name in enumerate(NAMES)}


# ---------------------------------------------------------------- 파일 매칭


@dataclass
class SessionFile:
    plan_id: str
    path: Path
    started_at: datetime
    delta_s: float  # 파일 시작 시각 - 일정표 시각(초)
    metadata: dict[str, Any]
    use: bool
    what: str
    actual: int | None
    screen: int | None
    motions: int | None = None


def match_sessions(directory: Path) -> list[SessionFile]:
    """파일 이름이 아니라 헤더의 started_at으로 일정표와 최적 매칭(시각 차이 합 최소)한다."""
    from scipy.optimize import linear_sum_assignment

    files = sorted(directory.glob("session_*.jsonl"))
    headers = []
    for path in files:
        with path.open("r", encoding="utf-8") as handle:
            headers.append(json.loads(handle.readline()))
    started = [datetime.fromisoformat(h["started_at"]) for h in headers]
    day = started[0].date()
    planned = [
        datetime.combine(day, datetime.strptime(item["hhmm"], "%H:%M").time(), tzinfo=started[0].tzinfo)
        for item in PLAN
    ]
    cost = np.array([[abs((p - s).total_seconds()) for s in started] for p in planned])
    rows, cols = linear_sum_assignment(cost)
    result = []
    for row, col in zip(rows, cols):
        item = PLAN[row]
        result.append(
            SessionFile(
                plan_id=item["id"], path=files[col], started_at=started[col],
                delta_s=(started[col] - planned[row]).total_seconds(),
                metadata=headers[col]["metadata"], use=item["use"], what=item["what"],
                actual=item["actual"], screen=item["screen"], motions=item.get("motions"),
            )
        )
    order = {item["id"]: n for n, item in enumerate(PLAN)}
    return sorted(result, key=lambda s: order[s.plan_id])


# ---------------------------------------------------------------- 프레임 배열


@dataclass
class Session:
    info: SessionFile
    header: dict[str, Any]
    end: dict[str, Any] | None
    n: int
    t: np.ndarray
    person: np.ndarray
    valid: np.ndarray
    locked: np.ndarray
    lock_view_side: np.ndarray  # 잠금 시점의 시점 판정(잠금 없으면 False)
    lock_leg: np.ndarray
    lock_facing: np.ndarray
    geo_leg: np.ndarray
    geo_facing: np.ndarray
    leg_now: np.ndarray
    facing_now: np.ndarray
    standing_flag: np.ndarray
    knee: np.ndarray
    knee_s: np.ndarray
    torso: np.ndarray
    shin: np.ndarray
    torso_signed: np.ndarray
    shin_signed: np.ndarray
    view_side_now: np.ndarray  # 이 프레임 (a)+(c) 판정(view.is_side)
    sig_a: np.ndarray
    sig_b: np.ndarray
    sig_c: np.ndarray
    stable: np.ndarray
    raw: np.ndarray
    display: np.ndarray
    pts: np.ndarray  # (N, 33, 2) 프레임 픽셀. landmark 없으면 NaN
    vis: np.ndarray  # (N, 33)
    lock_event: np.ndarray
    frame_i: np.ndarray
    reasons: list[list[str]] = field(default_factory=list)
    view_reasons: list[list[str]] = field(default_factory=list)


def _f(value: Any) -> float:
    return float("nan") if value is None else float(value)


def load_session(info: SessionFile) -> Session:
    header: dict[str, Any] | None = None
    end = None
    frames: list[dict[str, Any]] = []
    with info.path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            kind = record["type"]
            if kind == "session":
                header = record
            elif kind == "frame":
                frames.append(record)
            elif kind == "end":
                end = record
    assert header is not None
    n = len(frames)

    def col(fn, dtype=float):
        return np.array([fn(fr) for fr in frames], dtype=dtype)

    def g(fr, key):
        geo = fr.get("geometry")
        return None if geo is None else geo.get(key)

    pts = np.full((n, 33, 2), np.nan)
    vis = np.full((n, 33), np.nan)
    for k, fr in enumerate(frames):
        rows, crop = fr.get("landmarks"), fr.get("crop_bbox")
        if rows is None or crop is None:
            continue
        w, h = crop[2] - crop[0], crop[3] - crop[1]
        for j, row in enumerate(rows):
            if row[0] is None:
                continue
            pts[k, j, 0] = crop[0] + row[0] * w
            pts[k, j, 1] = crop[1] + row[1] * h
            vis[k, j] = _f(row[3])

    def lock(fr, key):
        return (fr.get("lock") or {}).get(key)

    def view(fr, key):
        v = fr.get("view")
        return None if v is None else v.get(key)

    return Session(
        info=info, header=header, end=end, n=n,
        t=col(lambda fr: fr["t"]),
        person=col(lambda fr: bool(fr.get("person")), bool),
        valid=col(lambda fr: bool((fr.get("full_body") or {}).get("valid")), bool),
        locked=col(lambda fr: bool(lock(fr, "locked")), bool),
        lock_view_side=col(lambda fr: bool(lock(fr, "view_is_side")), bool),
        lock_leg=col(lambda fr: lock(fr, "leg"), object),
        lock_facing=col(lambda fr: lock(fr, "facing"), object),
        geo_leg=col(lambda fr: g(fr, "leg"), object),
        geo_facing=col(lambda fr: g(fr, "facing"), object),
        leg_now=col(lambda fr: g(fr, "leg_now"), object),
        facing_now=col(lambda fr: g(fr, "facing_now"), object),
        standing_flag=col(lambda fr: bool(g(fr, "standing")), bool),
        knee=col(lambda fr: _f(g(fr, "knee"))),
        knee_s=col(lambda fr: _f(g(fr, "knee_smoothed"))),
        torso=col(lambda fr: _f(g(fr, "torso"))),
        shin=col(lambda fr: _f(g(fr, "shin"))),
        torso_signed=col(lambda fr: _f(g(fr, "torso_signed"))),
        shin_signed=col(lambda fr: _f(g(fr, "shin_signed"))),
        view_side_now=col(lambda fr: bool(view(fr, "is_side")), bool),
        sig_a=col(lambda fr: _f(view(fr, "shoulder_ratio"))),
        sig_b=col(lambda fr: _f(view(fr, "hip_yaw_deg"))),
        sig_c=col(lambda fr: _f(view(fr, "nose_visibility"))),
        stable=col(lambda fr: (fr.get("labels") or {}).get("stable"), object),
        raw=col(lambda fr: (fr.get("labels") or {}).get("raw"), object),
        display=col(lambda fr: (fr.get("labels") or {}).get("display"), object),
        pts=pts, vis=vis,
        lock_event=col(lambda fr: lock(fr, "event"), object),
        frame_i=col(lambda fr: fr["i"], float),
        reasons=[list((fr.get("full_body") or {}).get("reasons") or []) for fr in frames],
        view_reasons=[list((fr.get("view") or {}).get("reasons") or []) for fr in frames],
    )


# ---------------------------------------------------------------- 보조


def interpolate_short_gaps(t: np.ndarray, x: np.ndarray, max_gap: float) -> np.ndarray:
    """NaN 구간 중 양쪽에 값이 있고 길이가 max_gap초 이하인 구간만 선형 보간한다."""
    out = x.copy()
    idx = np.where(~np.isnan(x))[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if b - a > 1 and t[b] - t[a] <= max_gap:
            out[a + 1 : b] = np.interp(t[a + 1 : b], [t[a], t[b]], [x[a], x[b]])
    return out


def angle_between(vertex: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """(N,2) 배열 세 개로 vertex에서의 사이각(도). 계산 불가는 NaN."""
    a, b = p1 - vertex, p2 - vertex
    cross = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    dot = (a * b).sum(axis=1)
    return np.degrees(np.arctan2(np.abs(cross), dot))


def leg_points(s: Session, leg: str) -> dict[str, np.ndarray]:
    return {j: s.pts[:, IDX[f"{leg}_{j}"], :] for j in ("shoulder", "hip", "knee", "ankle", "heel", "foot_index")}


def knee_angle_leg(s: Session, leg: str) -> np.ndarray:
    p = leg_points(s, leg)
    return angle_between(p["knee"], p["hip"], p["ankle"])


def leg_length(s: Session, leg: str) -> np.ndarray:
    p = leg_points(s, leg)
    return np.linalg.norm(p["hip"] - p["knee"], axis=1) + np.linalg.norm(p["knee"] - p["ankle"], axis=1)


def rolling_median(x: np.ndarray, window: int = 3) -> np.ndarray:
    half = window // 2
    out = x.copy()
    for i in range(len(x)):
        seg = x[max(0, i - half) : i + half + 1]
        seg = seg[~np.isnan(seg)]
        out[i] = np.median(seg) if len(seg) else np.nan
    return out


def _med(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    return float(np.median(x)) if len(x) else float("nan")


# ---------------------------------------------------------------- 반복 구간 추출 (오프라인, 임시 규칙)


@dataclass
class RepSpan:
    start: int  # 내려가기 직전 마지막 '서 있음(>=160)' 프레임
    end: int  # 다시 160 이상이 된 첫 프레임 (aborted면 값이 끊기기 직전 프레임)
    bottom: int  # 평활 무릎각 최저 프레임
    aborted: bool = False  # 전신 무효가 길게 이어져 끝까지 못 본 반복


def extract_reps(
    t: np.ndarray,
    knee_s: np.ndarray,
    *,
    stand_angle: float = STANDING_ANGLE,
    descent_angle: float = DESCENT_ANGLE,
    max_gap: float = MAX_INTERP_GAP_S,
) -> tuple[list[RepSpan], np.ndarray]:
    """평활 무릎각 히스테리시스: stand_angle 이상을 본 뒤 descent_angle 미만으로 내려갔다가 stand_angle 이상으로
    돌아오면 반복 1회. 시작은 반드시 '서 있음'을 본 뒤여야 하므로 세션 앞에서 이미 내려간 구간과 끝에서 서지
    못한 구간은 자연히 빠진다. 전신 무효로 값이 max_gap초보다 길게 비면 진행 중인 반복은 aborted로 기록한다.
    """
    k = interpolate_short_gaps(t, knee_s, max_gap)
    reps: list[RepSpan] = []
    state, last_stand, start = "unknown", -1, -1
    for i, v in enumerate(k):
        if np.isnan(v):
            if state == "in_rep":
                bottom = start + int(np.nanargmin(k[start:i]))
                reps.append(RepSpan(start, i - 1, bottom, aborted=True))
            state = "unknown"
            continue
        if state == "unknown":
            if v >= stand_angle:
                state, last_stand = "stand", i
        elif state == "stand":
            if v >= stand_angle:
                last_stand = i
            elif v < descent_angle:
                state, start = "in_rep", last_stand
        elif state == "in_rep" and v >= stand_angle:
            bottom = start + int(np.nanargmin(k[start : i + 1]))
            reps.append(RepSpan(start, i, bottom))
            state, last_stand = "stand", i
    return reps, k


# ---------------------------------------------------------------- 반복별 지표


def rep_metrics(s: Session, span: RepSpan, k: np.ndarray, rep_no: int) -> dict[str, Any]:
    t = s.t
    i0, i1, ib = span.start, span.end, span.bottom
    leg = s.geo_leg[i0] if s.geo_leg[i0] is not None else s.lock_leg[i0]
    other = "right" if leg == "left" else "left"
    p = leg_points(s, leg)

    # 서 있을 때 기준: 내려가기 직전 1.0초 동안 평활 무릎각 >= 160 이고 전신 유효인 프레임의 중앙값
    pre = [j for j in range(i0, -1, -1) if t[j] >= t[i0] - 1.0]
    pre = [j for j in pre if (not np.isnan(k[j])) and k[j] >= STANDING_ANGLE and s.valid[j]]
    heel_y = rolling_median(p["heel"][:, 1], 3)
    base_heel = _med(heel_y[pre]) if pre else float("nan")
    base_hip = _med(p["hip"][pre, 1]) if pre else float("nan")
    base_len = _med(leg_length(s, leg)[pre]) if pre else float("nan")

    seg = slice(i0, i1 + 1)
    heel_rise = base_heel - np.nanmin(heel_y[seg])  # 발뒤꿈치가 올라가면 y가 작아진다
    # 보조 정의(한 프레임 튐에 덜 민감): 구간 하위 10% 값, 최저점 ±5프레임 중앙값, 발 기울기 변화(도, + = 발끝이 더 아래)
    heel_rise_p10 = base_heel - float(np.nanpercentile(heel_y[seg], 10))
    wide = slice(max(i0, ib - 5), min(i1, ib + 5) + 1)
    heel_rise_bottom = base_heel - _med(heel_y[wide])
    toe = p["foot_index"]

    def foot_pitch(idx) -> float:
        v = toe[idx] - p["heel"][idx]
        return _med(np.degrees(np.arctan2(v[:, 1], np.abs(v[:, 0]))))

    pitch_delta = foot_pitch(wide) - (foot_pitch(pre) if pre else float("nan"))

    # 양발 간격(프레임 x 픽셀, 다리 길이로 정규화): 런지·걷기는 크고, 두 발을 모으고 하는 스쿼트는 작다
    ankle_gap = np.abs(s.pts[:, IDX["left_ankle"], 0] - s.pts[:, IDX["right_ankle"], 0])
    gap_start = _med(ankle_gap[pre]) / base_len if pre else float("nan")
    gap_bottom = _med(ankle_gap[max(i0, ib - 2) : min(i1, ib + 2) + 1]) / base_len
    near = slice(max(i0, ib - 2), min(i1, ib + 2) + 1)  # 최저점 ±2프레임 중앙값으로 순간 노이즈를 줄인다
    hip_y_b, knee_y_b = _med(p["hip"][near, 1]), _med(p["knee"][near, 1])
    torso_b, shin_b = _med(s.torso_signed[near]), _med(s.shin_signed[near])
    torso_u, shin_u = _med(s.torso[near]), _med(s.shin[near])
    hip_drop = hip_y_b - base_hip  # 엉덩이가 내려가면 y가 커진다

    left_k, right_k = knee_angle_leg(s, "left"), knee_angle_leg(s, "right")
    chosen_k, other_k = (left_k, right_k) if leg == "left" else (right_k, left_k)
    other_cols = [IDX[f"{other}_{j}"] for j in ("hip", "knee", "ankle")]
    other_vis = float(np.nanmean(s.vis[i0 : i1 + 1][:, other_cols]))

    plateau = np.nan_to_num(k, nan=999.0) <= k[ib] + BOTTOM_PLATEAU_DEG
    a = ib
    while a - 1 >= i0 and plateau[a - 1]:
        a -= 1
    b = ib
    while b + 1 <= i1 and plateau[b + 1]:
        b += 1

    dt = np.append(np.diff(t), 0.0)
    dt[dt > 0.5] = 0.0
    phase_of = np.full(s.n, "", dtype=object)
    phase_of[i0:a] = "descent"
    phase_of[a : b + 1] = "bottom"
    phase_of[b + 1 : i1 + 1] = "ascent"
    label_s = {ph: {lab: 0.0 for lab in LABELS} for ph in ("descent", "bottom", "ascent", "all")}
    for j in range(i0, i1 + 1):
        lab = str(s.stable[j]) if s.stable[j] is not None else "None"
        label_s[phase_of[j]][lab] += float(dt[j])
        label_s["all"][lab] += float(dt[j])

    def nanmin(x):
        return float(np.nanmin(x)) if not np.all(np.isnan(x)) else float("nan")

    return {
        "session": s.info.plan_id, "rep": rep_no, "aborted": span.aborted,
        "t_start": float(t[i0]), "t_bottom": float(t[ib]), "t_end": float(t[i1]), "leg": leg, "facing": s.geo_facing[ib],
        "min_knee_smoothed": float(k[ib]), "min_knee_raw": nanmin(s.knee[seg]),
        "hip_y_minus_knee_y_px": hip_y_b - knee_y_b,  # >0: 엉덩이가 무릎보다 아래(평행 이상)
        "hip_below_knee_norm": (hip_y_b - knee_y_b) / base_len,
        "torso_signed_deg": torso_b, "shin_signed_deg": shin_b,
        "torso_minus_shin_signed_deg": torso_b - shin_b, "abs_torso_minus_shin_signed_deg": abs(torso_b - shin_b),
        "torso_unsigned_deg": torso_u, "shin_unsigned_deg": shin_u,
        "abs_torso_minus_shin_unsigned_deg": abs(torso_u - shin_u),
        "heel_rise_px": heel_rise, "heel_rise_norm": heel_rise / base_len,
        "heel_rise_p10_px": heel_rise_p10, "heel_rise_bottom_px": heel_rise_bottom,
        "heel_rise_bottom_norm": heel_rise_bottom / base_len, "foot_pitch_delta_deg": pitch_delta,
        "ankle_gap_start_norm": gap_start, "ankle_gap_bottom_norm": gap_bottom,
        "hip_drop_px": hip_drop, "hip_drop_norm": hip_drop / base_len,
        "leg_length_px": base_len, "standing_hip_y": base_hip, "standing_heel_y": base_heel,
        "chosen_knee_min": nanmin(chosen_k[seg]), "other_knee_min": nanmin(other_k[seg]),
        "left_knee_at_bottom": _med(left_k[near]), "right_knee_at_bottom": _med(right_k[near]),
        "knee_lr_diff_at_bottom": abs(_med(left_k[near]) - _med(right_k[near])),
        "other_leg_visibility": other_vis,
        "t_descent": float(t[a] - t[i0]), "t_bottom_dwell": float(t[b] - t[a]), "t_ascent": float(t[i1] - t[b]),
        "t_total": float(t[i1] - t[i0]), "valid_share": float(s.valid[seg].mean()),
        **{f"label_{ph}_{lab}": round(label_s[ph][lab], 4) for ph in label_s for lab in LABELS},
        "stable_at_start": s.stable[i0], "lock_view_side_at_start": bool(s.lock_view_side[i0]),
        "view_side_now_at_start": bool(s.view_side_now[i0]),
        "sig_a_start": s.sig_a[i0], "sig_b_start": s.sig_b[i0], "sig_c_start": s.sig_c[i0],
        "i_start": i0, "i_bottom": ib, "i_end": i1,
    }
