"""'세트 중간 누락'(실시간 확인: 연속 7회 중 4·5번째 누락) 진단을 위한 기존 실측 로그(fixture) 점검과 대응안 영향 시뮬레이션.

입력: tests/fixtures/rep_sessions/session_*.json (field_test_1에서 뽑은 판정용 값. 로그 원본·얼굴 좌표 없음).
출력: docs/versions/v0.2.0/analysis/field_test_1/midset/ (CSV, 그래프). 제품 코드는 바꾸지 않는다(대응안은 시뮬레이션만).

실행(저장소 루트에서): python scripts/analysis/midset_diagnosis.py

1. 반복 사이 무릎각 최대값(복귀 각도 160°까지 올라왔는가), 2. 세트 중간 잠금 해제 여부, 3. 정상 반복의 ML 비율 여유,
4. 대응안별 회귀 영향(복귀 각도 낮추기, 봉우리 기반 경계, 잠금 유예, Y 완화).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.signal import find_peaks  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.geometry_tracker import BodyLockPolicy  # noqa: E402
from src.rep_tracker import RepFrame, RepMeasures, RepTracker  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "rep_sessions"
OUT_DIR = ROOT / "docs" / "versions" / "v0.2.0" / "analysis" / "field_test_1" / "midset"
SQUAT_SESSIONS = ("1", "2", "3", "4", "5")
ALL_SESSIONS = ("1", "2", "3", "4", "5", "6", "7", "8a", "8b", "8c", "9")
ML_OFF = {"other_max_ratio": 2.0}
GEOMETRY_OFF = {"min_seconds": 0.0, "min_hip_drop": -10.0, "max_ankle_gap": 10.0}
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)


def load(session: str) -> dict:
    payload = json.loads((FIXTURES / f"session_{session}.json").read_text(encoding="utf-8"))
    columns = payload["columns"]
    payload["frames"] = [dict(zip(columns, row)) for row in payload["rows"]]
    return payload


def simulate(session: str, *, policy_options: dict | None = None, **tracker_options):
    """fixture의 신호를 BodyLockPolicy와 RepTracker에 넣어 재생한다(tests/test_rep_tracker.py의 simulate와 같은 방식)."""
    payload = load(session)
    policy, tracker = BodyLockPolicy(**(policy_options or {})), RepTracker(**tracker_options)
    results, events, timeline, lock_events = [], [], [], []
    leg = facing = None
    for v in payload["frames"]:
        t = v["t"]
        if v["present"]:
            knee = v["knee_smoothed"]
            decision = policy.step(
                t, standing=knee is not None and knee >= 160.0, side_now=bool(v["side_now"]),
                lockable=bool(v["valid"]) and v["facing_now"] is not None,
            )
            if decision in ("acquire", "refresh"):
                leg, facing = v["leg_now"], v["facing_now"]
            measures = (
                RepMeasures(v["hip_y"], v["heel_y"], v["leg_length"], v["ankle_gap"], float("nan") if v.get("hip_x") is None else v["hip_x"])
                if v["hip_y"] is not None
                else None
            )
            frame = RepFrame(t, True, knee, policy.locked, leg, facing, v["torso_signed"], v["shin_signed"], measures,
                             side_now=bool(v["side_now"]), body_valid=bool(v["valid"]))
        else:
            decision = policy.missing(t)
            frame = RepFrame.missing(t)
        if decision in ("acquire", "release_view", "release_missing"):
            detail = policy.last_release if decision != "acquire" else policy.last_acquire
            lock_events.append({"t": t, "decision": decision, **(detail or {})})
        result = tracker.update(frame, v["label"])
        if result is not None:
            results.append(result)
        events.extend(tracker.pop_events())
        timeline.append((t, policy.locked))
    return payload, results, events, lock_events, timeline


def counted(results) -> list:
    return [r for r in results if r.counted]


# ---------------------------------------------------------------- 1. 반복 사이 무릎각 최대값


def stage_peaks() -> pd.DataFrame:
    rows = []
    for session in SQUAT_SESSIONS:
        payload, results, _, _, _ = simulate(session)
        t = np.array([f["t"] for f in payload["frames"]])
        knee = np.array([np.nan if f["knee_smoothed"] is None else f["knee_smoothed"] for f in payload["frames"]])
        reps = counted(results)
        for i, rep in enumerate(reps):
            stop = reps[i + 1].t_bottom if i + 1 < len(reps) else rep.t_end + 3.0
            window = (t > rep.t_bottom) & (t <= stop)
            k = knee[window]
            dt = np.append(np.diff(t[window]), 0.0)
            dt[dt > 0.5] = 0.0
            valid = ~np.isnan(k)
            rows.append(
                {
                    "session": session, "rep_order": i + 1, "last_rep": i + 1 == len(reps), "t_bottom": rep.t_bottom,
                    "peak_smoothed": float(np.nanmax(k)), "margin_to_160": float(np.nanmax(k) - 160.0),
                    "seconds_at_or_above_160": float(dt[valid & (k >= 160.0)].sum()),
                    "standing_gap_to_next_s": (reps[i + 1].t_start - rep.t_end) if i + 1 < len(reps) else np.nan,
                    "rep_total_s": rep.total_seconds, "descent_s": rep.descent_seconds, "ascent_s": rep.ascent_seconds,
                }
            )
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "peaks_between_reps.csv", index=False, encoding="utf-8-sig")
    return table


def peaks_summary(table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    between = table[~table.last_rep]  # 마지막 반복은 뒤에 쉬는 구간이 붙어 비교에서 뺀다
    for session, g in between.groupby("session"):
        rho, p = spearmanr(g.rep_order, g.peak_smoothed) if len(g) > 2 else (np.nan, np.nan)
        half = len(g) // 2
        rows.append(
            {"session": session, "n_between": len(g), "peak_min": g.peak_smoothed.min(), "peak_median": g.peak_smoothed.median(),
             "peak_max": g.peak_smoothed.max(), "closest_to_160_margin": g.margin_to_160.min(),
             "first_half_mean": g.peak_smoothed.iloc[:half].mean(), "second_half_mean": g.peak_smoothed.iloc[half:].mean(),
             "spearman_peak_vs_order": rho, "spearman_p": p,
             "gap_first_half_mean_s": g.standing_gap_to_next_s.iloc[:half].mean(),
             "gap_second_half_mean_s": g.standing_gap_to_next_s.iloc[half:].mean(),
             "hold_ge160_min_s": g.seconds_at_or_above_160.min()}
        )
    pooled_rho, pooled_p = spearmanr(between.rep_order, between.peak_smoothed)
    rows.append({"session": "ALL", "n_between": len(between), "peak_min": between.peak_smoothed.min(),
                 "peak_median": between.peak_smoothed.median(), "peak_max": between.peak_smoothed.max(),
                 "closest_to_160_margin": between.margin_to_160.min(), "spearman_peak_vs_order": pooled_rho,
                 "spearman_p": pooled_p, "hold_ge160_min_s": between.seconds_at_or_above_160.min()})
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_DIR / "peaks_summary.csv", index=False, encoding="utf-8-sig")
    return summary


def plot_peaks(table: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.8))
    palette = {"1": "#0072B2", "2": "#56B4E9", "3": "#E69F00", "4": "#D55E00", "5": "#009E73"}
    for session, g in table.groupby("session"):
        ax1.plot(g.rep_order, g.peak_smoothed, marker="o", color=palette[session], label=f"session {session}")
        ax2.plot(g.rep_order[:-1], g.standing_gap_to_next_s[:-1], marker="o", color=palette[session], label=f"session {session}")
    ax1.axhline(160, color="#444444", linestyle="--", linewidth=1)
    ax1.text(0.6, 160.4, "return angle 160", fontsize=8)
    ax1.set_xlabel("rep order within the set")
    ax1.set_ylabel("max smoothed knee angle after the rep's bottom (deg)")
    ax1.set_title("How high the knee came back between reps", fontsize=10, loc="left")
    ax1.legend(fontsize=8)
    ax2.set_xlabel("rep order within the set")
    ax2.set_ylabel("standing time between reps (s)")
    ax2.set_title("Pause at the top (rep end to next rep start)", fontsize=10, loc="left")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "peaks_by_order.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 2. 세트 중간 잠금 해제


def stage_lock_gaps() -> pd.DataFrame:
    rows = []
    for session in SQUAT_SESSIONS + ("9",):
        payload, results, _, lock_events, timeline = simulate(session)
        reps = counted(results)
        first_start, last_end = reps[0].t_start, reps[-1].t_end
        releases = [e for e in lock_events if e["decision"] != "acquire"]
        for e in releases:
            nxt = next((a for a in lock_events if a["decision"] == "acquire" and a["t"] > e["t"]), None)
            rows.append(
                {"session": session, "release_t": e["t"], "reason": e.get("reason"), "nonside_or_missing_seconds": e.get("seconds"),
                 "reacquired_after_s": (nxt["t"] - e["t"]) if nxt else np.nan,
                 "inside_set": first_start <= e["t"] <= last_end, "set_window": f"{first_start:.1f}-{last_end:.1f}"}
            )
        if not releases:
            rows.append({"session": session, "release_t": np.nan, "reason": "(none)", "inside_set": False,
                         "set_window": f"{first_start:.1f}-{last_end:.1f}"})
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "lock_releases.csv", index=False, encoding="utf-8-sig")
    return table


# ---------------------------------------------------------------- 3. 정상 반복의 ML 비율


def stage_ml_ratio() -> pd.DataFrame:
    rows = []
    for session in SQUAT_SESSIONS + ("9",):
        _, results, _, _, _ = simulate(session, **GEOMETRY_OFF, other_max_ratio=2.0)  # 조건을 모두 꺼서 후보 전체의 비율을 본다
        reps = [r for r in results if r.total_seconds >= 1.0]
        for i, r in enumerate(reps):
            shares = r.label_seconds
            seen = sum(v for k, v in shares.items() if k != "None") or 1.0
            rows.append({"session": session, "rep_order": i + 1, "ratio": r.other_exercise_ratio,
                         "margin_to_040": 0.40 - r.other_exercise_ratio,
                         **{f"share_{lab}": shares.get(lab, 0.0) / seen
                            for lab in ("walk", "run", "lying", "jump", "bendover", "sit", "squat", "stand")}})
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "ml_ratio_per_rep.csv", index=False, encoding="utf-8-sig")
    return table


# ---------------------------------------------------------------- 4. 대응안 시뮬레이션


def count_row(label: str, **options) -> dict:
    row = {"variant": label}
    for session in ALL_SESSIONS:
        _, results, _, _, _ = simulate(session, policy_options=options.get("policy"), **options.get("tracker", {}))
        row[session] = len(counted(results))
    return row


def stage_variants() -> dict[str, pd.DataFrame]:
    actual = {"variant": "actual (user)", "1": 10, "2": 8, "3": 8, "4": 8, "5": 8, "6": 5, "7": 5, "8a": 0, "8b": "chair", "8c": 0, "9": "5-6?"}
    # 가설 1: 복귀 각도 낮추기(내려감 각도는 복귀보다 낮아야 하므로 함께 낮춘다). 잠금 정책의 STANDING(160)은 그대로.
    return_rows = [actual] + [
        count_row(f"return {a:g} / descent {d:g}", tracker={"standing_angle": a, "descent_angle": d})
        for a, d in ((160, 150), (155, 150), (150, 140), (145, 135), (140, 130))
    ]
    # 가설 2: 잠금 해제 유예
    policy_rows = [actual] + [
        count_row(f"release non-side after {s:g} s", policy={"release_nonside_seconds": s}) for s in (0.4, 0.8, 1.2, 2.0)
    ] + [count_row("missing release after 4 s", policy={"missing_release_seconds": 4.0})]
    # 가설 3: ML 비율 Y 완화 / ML을 쓰지 않음(기하만)
    ml_rows = [actual] + [count_row(f"Y = {y:g}", tracker={"other_max_ratio": y}) for y in (0.40, 0.50, 0.60, 0.70)] + [
        count_row("ML off (geometry only)", tracker=ML_OFF)
    ]
    tables = {"return_angle": pd.DataFrame(return_rows), "lock_grace": pd.DataFrame(policy_rows), "ml_ratio": pd.DataFrame(ml_rows)}
    for name, table in tables.items():
        table.to_csv(OUT_DIR / f"variants_{name}.csv", index=False, encoding="utf-8-sig")
    return tables


def synthetic_continuous_set(tops: list[float], *, down=0.9, up=0.9, pause=0.0, bottom=70.0, hip_drop=0.55):
    """쉬지 않고 이어지는 반복: i번째 반복이 끝날 때 무릎이 tops[i]도까지만 올라온다(마지막은 충분히 선다)."""
    leg_length, base_hip = 160.0, 150.0
    points = [(0.0, 175.0), (1.5, 175.0)]
    t = 1.5
    for top in tops:
        points += [(t + down, bottom), (t + down + 0.3, bottom), (t + down + 0.3 + up, top)]
        t += down + 0.3 + up
        if pause > 0:
            points.append((t + pause, top))
            t += pause
    points += [(t + 0.6, 175.0), (t + 2.1, 175.0)]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    frames = []
    for index in range(int(xs[-1] * 30) + 1):
        s = index / 30.0
        knee = float(np.interp(s, xs, ys))
        hip_y = base_hip + hip_drop * leg_length * (175.0 - knee) / 105.0
        frames.append((RepFrame(s, True, knee, True, "left", "right", 45.0, 28.0, RepMeasures(hip_y, 318.0, leg_length, 3.0)),
                       "stand" if knee >= 160 else "squat"))
    return frames


def stage_synthetic() -> pd.DataFrame:
    """가설 1을 합성 시퀀스로 확인: 세트 중간 반복이 160도까지 못 올라오면 현재 규칙은 몇 회로 세는가, 대응안은 어떤가."""
    scenarios = {
        "all 7 reps return to 175": [175] * 7,
        "reps 4-5 return only to 158": [175, 175, 175, 158, 158, 175, 175],
        "reps 4-5 return only to 150": [175, 175, 175, 150, 150, 175, 175],
        "reps 4-5 return only to 140": [175, 175, 175, 140, 140, 175, 175],
        "reps 3-6 return only to 155 (fatigue)": [175, 175, 155, 155, 155, 155, 175],
    }
    variants = {"current 160/150": (160, 150), "return 155/150": (155, 150), "return 150/140": (150, 140), "return 145/135": (145, 135)}
    rows = []
    for name, tops in scenarios.items():
        row = {"scenario": name, "actual": len(tops)}
        for vname, (a, d) in variants.items():
            tracker = RepTracker(standing_angle=a, descent_angle=d)
            results = [r for frame, label in synthetic_continuous_set(tops) if (r := tracker.update(frame, label)) is not None]
            row[vname] = len(counted(results))
        merge_events = []
        tracker = RepTracker()
        for frame, label in synthetic_continuous_set(tops):
            tracker.update(frame, label)
            merge_events.extend(e for e in tracker.pop_events() if e["kind"] == "rep_merge_suspect")
        row["merge_suspect_events (current rule)"] = len(merge_events)
        rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "synthetic_return_angle.csv", index=False, encoding="utf-8-sig")
    return table


def stage_valley_boundaries() -> pd.DataFrame:
    """'상승 후 일정 각도 회복 + 각속도 부호 전환' 방식의 오프라인 근사: 평활 무릎각의 골짜기를 prominence로 센다.
    걷기·이동 굴곡이 새로 잡히는지(확정 조건을 적용하기 전의 후보 수)를 본다."""
    rows = []
    for session in ALL_SESSIONS:
        payload = load(session)
        t = np.array([f["t"] for f in payload["frames"]])
        knee = np.array([np.nan if f["knee_smoothed"] is None else f["knee_smoothed"] for f in payload["frames"]])
        grid = np.arange(t[0], t[-1], 1 / 30)
        valid = ~np.isnan(knee)
        interp = np.interp(grid, t[valid], knee[valid])
        row = {"session": session}
        for prominence in (20, 30, 40, 60):
            valleys, _ = find_peaks(-interp, prominence=prominence)
            row[f"valleys_prom{prominence}_below150"] = int(np.sum(interp[valleys] < 150.0))
        _, results, _, _, _ = simulate(session)
        row["current_rule_counted"] = len(counted(results))
        rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "valley_boundary_candidates.csv", index=False, encoding="utf-8-sig")
    return table


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    peaks = stage_peaks()
    print("== 반복 사이 최대 무릎각 (반복 순서별)\n" + peaks.round(2).to_string(index=False))
    print("== 요약\n" + peaks_summary(peaks).round(3).to_string(index=False))
    plot_peaks(peaks)
    print("== 세트 중간 잠금 해제\n" + stage_lock_gaps().round(2).to_string(index=False))
    ml = stage_ml_ratio()
    print("== 정상 반복 ML 비율(세션별)\n" + ml.groupby("session").ratio.agg(["count", "min", "median", "max"]).round(3).to_string())
    print(f"전체 최대 {ml.ratio.max():.3f} (여유 {0.40 - ml.ratio.max():.3f}); 비율 > 0.30인 반복 {int((ml.ratio > 0.30).sum())}개 / {len(ml)}개")
    print("== 반복 순서별 ML 비율 평균\n" + ml.groupby("rep_order").ratio.agg(["count", "mean", "max"]).round(3).to_string())
    for name, table in stage_variants().items():
        print(f"== 대응안 시뮬레이션: {name}\n" + table.to_string(index=False))
    print("== 합성 연속 세트(가설 1)\n" + stage_synthetic().to_string(index=False))
    print("== 골짜기(prominence) 기반 경계 후보 수\n" + stage_valley_boundaries().to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
