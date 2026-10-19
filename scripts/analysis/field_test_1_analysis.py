"""field_test_1 (2026-10-18 실측) 분석. data/landmark_sequences/의 로그 원본은 읽기만 한다. 카메라는 쓰지 않는다.

실행(저장소 루트에서):
    python scripts/analysis/field_test_1_analysis.py

출력: docs/versions/v0.2.0/analysis/field_test_1/ (CSV, 그래프). 보고서(report.md)는 이 결과를 보고 쓴다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from field_test_1_lib import (  # noqa: E402
    LABELS, NON_SQUAT_IDS, SIDE_SQUAT_IDS, extract_reps, load_session, match_sessions, rep_metrics,
)
from src.exercise_counter import ExerciseCounter  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "landmark_sequences"
OUT_DIR = ROOT / "docs" / "versions" / "v0.2.0" / "analysis" / "field_test_1"
SHORT_REP_S = 1.0  # 이보다 짧은 후보는 반복이 아니라 이동·걷기 같은 짧은 굴곡으로 본다(transit 판정에만 사용)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 200)


def load_all():
    infos = match_sessions(DATA_DIR)
    return infos, {info.plan_id: load_session(info) for info in infos}


# ---------------------------------------------------------------- 0. 매칭표 + 2. 데이터 품질


def stage_match_and_quality(infos, sessions) -> dict:
    rows = []
    for info in infos:
        s = sessions[info.plan_id]
        rows.append(
            {
                "session": info.plan_id, "file": info.path.name, "started_at": info.started_at.isoformat(timespec="seconds"),
                "delta_vs_plan_s": info.delta_s, "metadata_note": info.metadata.get("note"),
                "posture": info.metadata.get("intended_posture"), "view": info.metadata.get("camera_view"),
                "used_for_analysis": info.use, "frames": s.n,
            }
        )
    match = pd.DataFrame(rows)
    match.to_csv(OUT_DIR / "session_match.csv", index=False, encoding="utf-8-sig")

    quality = []
    for info in infos:
        s = sessions[info.plan_id]
        dt = np.diff(s.t)
        fps = 1.0 / dt[dt > 0]
        person = s.person
        quality.append(
            {
                "session": info.plan_id, "frames": s.n, "duration_s": s.t[-1] - s.t[0],
                "fps_mean": (s.n - 1) / (s.t[-1] - s.t[0]), "fps_median": float(np.median(fps)),
                "fps_p5": float(np.percentile(fps, 5)), "max_frame_gap_s": float(dt.max()),
                "dropped": (s.end or {}).get("frames_dropped"),
                "person_ratio": float(person.mean()),
                "full_body_valid_ratio_all": float(s.valid.mean()),
                "full_body_valid_ratio_person": float(s.valid[person].mean()) if person.any() else float("nan"),
                "body_lock_ratio_all": float(s.locked.mean()),
                "body_lock_ratio_person": float(s.locked[person].mean()) if person.any() else float("nan"),
            }
        )
    q = pd.DataFrame(quality)
    q.to_csv(OUT_DIR / "data_quality.csv", index=False, encoding="utf-8-sig")
    return {"match": match, "quality": q}


# ---------------------------------------------------------------- 1. v0.1.x 기준선 복원


def replay_counter(s) -> tuple[int, list[float]]:
    """로그의 stable 라벨(표시 필터 전, 카운터가 실제로 받던 값)을 ExerciseCounter에 그대로 넣는다."""
    counter = ExerciseCounter()
    counter.set_mode("squat", float(s.t[0]))
    events: list[float] = []
    previous = 0
    for t, label in zip(s.t, s.stable):
        counter.update(label, float(t))
        if counter.squat_count != previous:
            events.append(float(t))
            previous = counter.squat_count
    return counter.squat_count, events


def stage_baseline(infos, sessions) -> pd.DataFrame:
    rows = []
    for info in infos:
        s = sessions[info.plan_id]
        count, events = replay_counter(s)
        rows.append(
            {
                "session": info.plan_id, "what": info.what, "actual": info.actual if info.actual is not None else "",
                "motions": info.motions if info.motions is not None else "",
                "screen_count": "" if info.screen is None else info.screen, "replay_v01x": count,
                "match_screen": "" if info.screen is None else (count == info.screen),
                "count_event_times_s": " ".join(f"{e:.1f}" for e in events),
            }
        )
    base = pd.DataFrame(rows)
    base.to_csv(OUT_DIR / "baseline_v01x.csv", index=False, encoding="utf-8-sig")
    return base


# ---------------------------------------------------------------- 3. 반복 구간 추출


def stage_reps(infos, sessions) -> pd.DataFrame:
    all_rows = []
    for info in infos:
        s = sessions[info.plan_id]
        spans, k = extract_reps(s.t, s.knee_s)
        rows = [rep_metrics(s, span, k, n + 1) for n, span in enumerate(spans)]
        # transit: (짧거나 중단된) 후보가, 짧지도 중단되지도 않은 후보들이 이루는 구간(core) 밖에 있을 때
        solid = [n for n, r in enumerate(rows) if not r["aborted"] and r["t_total"] >= SHORT_REP_S]
        core = (rows[solid[0]]["t_start"], rows[solid[-1]]["t_end"]) if solid else None
        for r in rows:
            weak = r["aborted"] or r["t_total"] < SHORT_REP_S
            r["transit"] = bool(weak and core is not None and (r["t_end"] < core[0] or r["t_start"] > core[1]))
            r["short"] = r["t_total"] < SHORT_REP_S
        all_rows.extend(rows)
    reps = pd.DataFrame(all_rows)
    reps["session_posture"] = reps["session"].map({i.plan_id: i.metadata.get("intended_posture") for i in infos})
    reps["view"] = reps["session"].map({i.plan_id: i.metadata.get("camera_view") for i in infos})
    reps.to_csv(OUT_DIR / "reps_all_candidates.csv", index=False, encoding="utf-8-sig")
    return reps


def rep_count_table(infos, reps) -> pd.DataFrame:
    rows = []
    for info in infos:
        r = reps[reps.session == info.plan_id]
        rows.append(
            {
                "session": info.plan_id, "actual": "" if info.actual is None else info.actual,
                "candidates_raw_rule": len(r), "transit_excluded": int(r.transit.sum()),
                "detected_after_transit": int((~r.transit).sum()),
                "of_which_short_lt_1s": int(((~r.transit) & r.short).sum()),
                "of_which_aborted": int(((~r.transit) & r.aborted).sum()),
            }
        )
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "rep_counts.csv", index=False, encoding="utf-8-sig")
    return table


def label_share(df: pd.DataFrame, labels, prefix: str = "label_all_") -> pd.Series:
    total = sum(df[f"{prefix}{label}"] for label in LABELS)
    return sum(df[f"{prefix}{label}"] for label in labels) / total


def auc(worse: np.ndarray, better: np.ndarray) -> float:
    """worse 값이 better 값보다 클 확률(동률은 0.5). 1.0 = 완전 분리(worse가 항상 큼), 0.5 = 분리 안 됨."""
    worse, better = np.asarray(worse, float), np.asarray(better, float)
    worse, better = worse[~np.isnan(worse)], better[~np.isnan(better)]
    greater = (worse[:, None] > better[None, :]).sum() + 0.5 * (worse[:, None] == better[None, :]).sum()
    return float(greater / (len(worse) * len(better)))


def best_cut(worse: np.ndarray, better: np.ndarray) -> dict:
    """worse >= cut이면 '나쁨'으로 판정할 때 균형 정확도(TPR과 TNR의 평균)가 최대인 cut."""
    worse, better = np.asarray(worse, float), np.asarray(better, float)
    worse, better = worse[~np.isnan(worse)], better[~np.isnan(better)]
    values = np.unique(np.concatenate([worse, better]))
    mids = (values[:-1] + values[1:]) / 2
    best = None
    for cut in mids:
        tpr, tnr = float((worse >= cut).mean()), float((better < cut).mean())
        score = (tpr + tnr) / 2
        if best is None or score > best["balanced_accuracy"] + 1e-12:
            best = {"cut": float(cut), "tpr": tpr, "tnr": tnr, "balanced_accuracy": score}
    return best


# ---------------------------------------------------------------- 4. 판정 경계값

# 항목, 지표, 나쁜 방향(+1 = 값이 클수록 나쁨), 표적 세션, 깨끗한 음성 세션(그 항목의 오류를 의도하지 않은 세션)
ITEM_SPECS = [
    ("depth", "min_knee_smoothed", +1, ["3"], ["1", "2", "5", "9"]),
    ("depth", "hip_below_knee_norm", -1, ["3"], ["1", "2", "5", "9"]),
    ("torso_shin", "abs_torso_minus_shin_signed_deg", +1, ["4"], ["1", "2", "3", "5", "9"]),
    ("torso_shin", "abs_torso_minus_shin_unsigned_deg", +1, ["4"], ["1", "2", "3", "5", "9"]),
    ("heel", "heel_rise_px", +1, ["5"], ["1", "2", "3", "4", "9"]),
    ("heel", "heel_rise_bottom_px", +1, ["5"], ["1", "2", "3", "4", "9"]),
    ("heel", "heel_rise_p10_px", +1, ["5"], ["1", "2", "3", "4", "9"]),
    ("heel", "heel_rise_norm", +1, ["5"], ["1", "2", "3", "4", "9"]),
    ("heel", "foot_pitch_delta_deg", +1, ["5"], ["1", "2", "3", "4", "9"]),
]


def stage_thresholds(reps: pd.DataFrame) -> dict:
    use = reps[(~reps.transit) & reps.session.isin(SIDE_SQUAT_IDS)].copy()
    stat_rows, sep_rows = [], []
    for item, metric, sign, target, negatives in ITEM_SPECS:
        for session, g in use.groupby("session"):
            x = g[metric].to_numpy(float)
            stat_rows.append(
                {"item": item, "metric": metric, "session": session, "n": int(np.isfinite(x).sum()), "min": np.nanmin(x),
                 "p25": np.nanpercentile(x, 25), "median": np.nanmedian(x), "p75": np.nanpercentile(x, 75), "max": np.nanmax(x)}
            )
        value = lambda ids: sign * use[use.session.isin(ids)][metric].to_numpy(float)  # noqa: E731
        ref = ["1", "2"]
        row = {"item": item, "metric": metric, "bad_direction": "high" if sign > 0 else "low", "target_sessions": "+".join(target),
               "n_target": len(value(target)), "n_normal_ref_s1_s2": len(value(ref)), "n_clean_negatives": len(value(negatives)),
               "auc_target_vs_s1s2": auc(value(target), value(ref)), "auc_target_vs_clean": auc(value(target), value(negatives))}
        cut_ref, cut_clean = best_cut(value(target), value(ref)), best_cut(value(target), value(negatives))
        for tag, cut in (("s1s2", cut_ref), ("clean", cut_clean)):
            row.update({f"best_cut_{tag}": sign * cut["cut"], f"tpr_{tag}": cut["tpr"], f"tnr_{tag}": cut["tnr"]})
        row.update({"normal_ref_worst": sign * np.nanmax(value(ref)), "target_best": sign * np.nanmin(value(target)),
                    "target_median": sign * np.nanmedian(value(target))})
        sep_rows.append(row)
    stats, sep = pd.DataFrame(stat_rows), pd.DataFrame(sep_rows)
    stats.to_csv(OUT_DIR / "thresholds_distribution.csv", index=False, encoding="utf-8-sig")
    sep.to_csv(OUT_DIR / "thresholds_separation.csv", index=False, encoding="utf-8-sig")
    return {"stats": stats, "sep": sep}


def status_counts(reps: pd.DataFrame, proposals: dict) -> pd.DataFrame:
    """제안한 정상/주의/교정 경계를 반복에 적용해 세션별 개수를 센다. proposals: metric -> (ok_max, bad_min, sign)."""
    use = reps[(~reps.transit) & reps.session.isin(SIDE_SQUAT_IDS)]
    rows = []
    for metric, (ok_max, bad_min, sign) in proposals.items():
        for session, g in use.groupby("session"):
            x = sign * g[metric].to_numpy(float)
            rows.append(
                {"metric": metric, "session": session, "n": len(x), "정상": int((x <= sign * ok_max if sign > 0 else x <= -ok_max).sum()),
                 "교정": int((x >= sign * bad_min if sign > 0 else x >= -bad_min).sum())}
            )
    table = pd.DataFrame(rows)
    table["주의"] = table["n"] - table["정상"] - table["교정"]
    return table[["metric", "session", "n", "정상", "주의", "교정"]]


def stage_reversed_check(reps: pd.DataFrame) -> pd.DataFrame:
    """세션 9(반대 방향)가 세션 1·2와 같은 분포인지: 중앙값, 범위, 세션 1·2의 합집합 범위 안에 든 비율, 순위합 검정."""
    from scipy.stats import mannwhitneyu

    use = reps[~reps.transit]
    metrics = ["min_knee_smoothed", "hip_below_knee_norm", "torso_signed_deg", "shin_signed_deg", "torso_minus_shin_signed_deg",
               "abs_torso_minus_shin_unsigned_deg", "heel_rise_bottom_px", "hip_drop_norm"]
    rows = []
    s1, s2, s9 = (use[use.session == k] for k in ("1", "2", "9"))
    for metric in metrics:
        a, b, c = s1[metric].to_numpy(float), s2[metric].to_numpy(float), s9[metric].to_numpy(float)
        ref = np.concatenate([a, b])
        inside = float(((c >= np.nanmin(ref)) & (c <= np.nanmax(ref))).mean())
        rows.append(
            {"metric": metric, "s1_median": np.nanmedian(a), "s1_range": f"{np.nanmin(a):.2f}..{np.nanmax(a):.2f}",
             "s2_median": np.nanmedian(b), "s2_range": f"{np.nanmin(b):.2f}..{np.nanmax(b):.2f}",
             "s9_median": np.nanmedian(c), "s9_range": f"{np.nanmin(c):.2f}..{np.nanmax(c):.2f}",
             "s9_inside_s1s2_range": inside, "mannwhitney_p_s9_vs_s1": float(mannwhitneyu(c, a).pvalue),
             "mannwhitney_p_s9_vs_s2": float(mannwhitneyu(c, b).pvalue)}
        )
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "reversed_check_s9_vs_s1s2.csv", index=False, encoding="utf-8-sig")
    return table


# ---------------------------------------------------------------- 5. 스쿼트가 아닌 동작


def stage_nonsquat(reps: pd.DataFrame) -> dict:
    df = reps.copy()
    df["sit_share"] = label_share(df, ["sit"])
    df["walk_share"] = label_share(df, ["walk"])
    df["stretch_share"] = label_share(df, ["stretch"])
    df["ml_excl_share"] = label_share(df, ["walk", "run", "jump", "lying"])
    normal = df[(~df.transit) & df.session.isin(SIDE_SQUAT_IDS)]
    other = df[(~df.transit) & df.session.isin(NON_SQUAT_IDS)]
    features = ["t_total", "hip_drop_norm", "min_knee_smoothed", "other_knee_min", "knee_lr_diff_at_bottom", "ankle_gap_start_norm",
                "ankle_gap_bottom_norm", "torso_signed_deg", "t_bottom_dwell", "sit_share", "walk_share", "stretch_share", "ml_excl_share"]
    summary = pd.concat(
        [
            normal.groupby("session")[features].agg(["min", "median", "max"]).round(3),
            other.groupby("session")[features].agg(["min", "median", "max"]).round(3),
        ]
    )
    summary.to_csv(OUT_DIR / "nonsquat_feature_summary.csv", encoding="utf-8-sig")

    conditions = {
        "duration >= 1.0 s": lambda d: d.t_total >= 1.0,
        "hip_drop_norm >= 0.25": lambda d: d.hip_drop_norm >= 0.25,
        "other knee also flexed (other_knee_min <= 130)": lambda d: d.other_knee_min <= 130,
        "knee L/R diff at bottom <= 8 deg": lambda d: d.knee_lr_diff_at_bottom <= 8,
        "ankle gap at standing <= 0.25 L (feet together)": lambda d: d.ankle_gap_start_norm <= 0.25,
        "torso_signed at bottom >= 30 deg (not upright/back)": lambda d: d.torso_signed_deg >= 30,
        "bottom dwell <= 2.2 s": lambda d: d.t_bottom_dwell <= 2.2,
        "sit label share <= 0.25": lambda d: d.sit_share <= 0.25,
        "walk label share <= 0.35": lambda d: d.walk_share <= 0.35,
        "ML exclusion share (walk+run+jump+lying) <= 0.45": lambda d: d.ml_excl_share <= 0.45,
    }
    rows = []
    for name, fn in conditions.items():
        keep_normal, keep_other = fn(normal), fn(other)
        row = {"condition (rep is squat-like if True)": name, "normal_reps_total": len(normal), "normal_reps_rejected": int((~keep_normal).sum())}
        for sid in NON_SQUAT_IDS:
            sel = other.session == sid
            row[f"{sid}_candidates"] = int(sel.sum())
            row[f"{sid}_still_kept"] = int(keep_other[sel].sum())
        rows.append(row)
    all_rule = lambda d: np.logical_and.reduce([fn(d) for name, fn in conditions.items() if name.startswith(("duration", "hip_drop", "ankle", "torso_signed", "sit"))])  # noqa: E731
    row = {"condition (rep is squat-like if True)": "COMBINED: duration + hip_drop + ankle gap + torso + sit", "normal_reps_total": len(normal),
           "normal_reps_rejected": int((~all_rule(normal)).sum())}
    for sid in NON_SQUAT_IDS:
        sel = other.session == sid
        row[f"{sid}_candidates"] = int(sel.sum())
        row[f"{sid}_still_kept"] = int(all_rule(other)[sel].sum())
    rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "nonsquat_conditions.csv", index=False, encoding="utf-8-sig")
    return {"summary": summary, "conditions": table, "df": df}


# 제안했던 5개 조건: (이름, 지표, 방향(+1: 지표 >= 기준이면 스쿼트 같음, -1: <= 기준), 기준값)
ABLATION_CONDITIONS = [
    ("duration >= 1.0 s", "t_total", +1, 1.0),
    ("hip_drop_norm >= 0.25", "hip_drop_norm", +1, 0.25),
    ("ankle_gap_start_norm <= 0.25 (side only)", "ankle_gap_start_norm", -1, 0.25),
    ("torso_signed >= 30 deg", "torso_signed_deg", +1, 30.0),
    ("sit_share <= 0.25", "sit_share", -1, 0.25),
]
FINAL_CONDITIONS = ("duration >= 1.0 s", "hip_drop_norm >= 0.25", "ankle_gap_start_norm <= 0.25 (side only)")


def stage_ablation(ns: dict) -> dict:
    """조건 하나만 뺐을 때(leave-one-out) 정상 탈락 수와 비스쿼트 잔존 수, 그리고 조건별 여유(margin)."""
    df = ns["df"]
    df = df[~df.transit]
    normal = df[df.session.isin(SIDE_SQUAT_IDS)]
    others = {sid: df[df.session == sid] for sid in NON_SQUAT_IDS}

    def passes(d, names):
        ok = np.ones(len(d), bool)
        for name, metric, sign, cut in ABLATION_CONDITIONS:
            if name in names:
                ok &= (d[metric] >= cut) if sign > 0 else (d[metric] <= cut)
        return ok

    all_names = [c[0] for c in ABLATION_CONDITIONS]
    rows = []

    def add(label, names):
        row = {"rule": label, "normal_total": len(normal), "normal_rejected": int((~passes(normal, names)).sum())}
        for sid, d in others.items():
            row[f"{sid}_candidates"] = len(d)
            row[f"{sid}_remaining"] = int(passes(d, names).sum())
        rows.append(row)

    add("all 5 conditions", all_names)
    for name in all_names:
        add(f"without [{name}]", [n for n in all_names if n != name])
    add("FINAL 3 (duration + hip_drop + ankle gap)", list(FINAL_CONDITIONS))
    for name in FINAL_CONDITIONS:
        add(f"FINAL 3 without [{name}]", [n for n in FINAL_CONDITIONS if n != name])
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "ablation_leave_one_out.csv", index=False, encoding="utf-8-sig")

    margins = []
    for name, metric, sign, cut in ABLATION_CONDITIONS:
        n_vals = normal[metric].to_numpy(float)
        normal_worst = np.nanmin(n_vals) if sign > 0 else np.nanmax(n_vals)  # 기준에 가장 가까운 정상 값
        row = {"condition": name, "threshold": cut, "normal_worst": normal_worst, "normal_margin_to_threshold": sign * (normal_worst - cut)}
        for sid, d in others.items():
            v = d[metric].to_numpy(float)
            best = np.nanmax(v) if sign > 0 else np.nanmin(v)  # 기준을 통과하는 쪽에 가장 가까운 비스쿼트 값
            row[f"{sid}_nearest_to_pass"] = best
            row[f"{sid}_margin_to_threshold"] = sign * (cut - best)  # >0이면 이 세션의 모든 후보가 기준 밖(배제됨)
            row[f"{sid}_gap_normal_vs_nonsquat"] = sign * (normal_worst - best)
        margins.append(row)
    margin_table = pd.DataFrame(margins)
    margin_table.to_csv(OUT_DIR / "ablation_margins.csv", index=False, encoding="utf-8-sig")
    return {"loo": table, "margins": margin_table}


# ---------------------------------------------------------------- 6. ML 배제 조건


def stage_ml(reps: pd.DataFrame, infos, sessions) -> dict:
    df = reps[~reps.transit].copy()
    groups = {"side_squat_1-5,9": SIDE_SQUAT_IDS, "oblique_6": ("6",), "front_7": ("7",), "walk_8a": ("8a",), "chair_8b": ("8b",), "lunge_8c": ("8c",)}
    rows = []
    for gname, ids in groups.items():
        g = df[df.session.isin(ids)]
        for phase in ("descent", "bottom", "ascent", "all"):
            total = sum(g[f"label_{phase}_{label}"] for label in LABELS)
            for label in LABELS:
                share = g[f"label_{phase}_{label}"].sum() / total.sum() if total.sum() else float("nan")
                rows.append({"group": gname, "phase": phase, "label": label, "share_of_time": share})
    phase_table = pd.DataFrame(rows)
    phase_table.to_csv(OUT_DIR / "ml_label_share_by_phase.csv", index=False, encoding="utf-8-sig")

    variants = {
        "walk+run+jump+lying (current list)": ["walk", "run", "jump", "lying"],
        "walk+run+lying (jump removed)": ["walk", "run", "lying"],
        "walk+run+jump+lying+stretch": ["walk", "run", "jump", "lying", "stretch"],
        "walk only": ["walk"],
        "jump only": ["jump"],
        "stretch only": ["stretch"],
    }
    per_rep = []
    for vname, labs in variants.items():
        share = label_share(df, labs)
        for session, g in share.groupby(df.session):
            per_rep.append({"variant": vname, "session": session, "n": len(g), "min": g.min(), "median": g.median(), "p95": g.quantile(0.95), "max": g.max()})
    variant_table = pd.DataFrame(per_rep)
    variant_table.to_csv(OUT_DIR / "ml_exclusion_variants.csv", index=False, encoding="utf-8-sig")

    # 무릎각 < 150 구간의 stable 라벨 비율(전신 유효 프레임, 시간 가중). 세션 0의 약 20% jump 관찰을 재확인한다.
    knee_rows = []
    for info in infos:
        s = sessions[info.plan_id]
        dt = np.append(np.diff(s.t), 0.0)
        dt[dt > 0.5] = 0.0
        mask = np.nan_to_num(s.knee_s, nan=999.0) < 150.0
        total = dt[mask].sum()
        shares = {label: float(dt[mask & (np.array([str(x) for x in s.stable]) == label)].sum() / total) if total else float("nan") for label in LABELS}
        knee_rows.append({"session": info.plan_id, "seconds_below_150": total, **{f"share_{k}": v for k, v in shares.items()}})
    knee_table = pd.DataFrame(knee_rows)
    knee_table.to_csv(OUT_DIR / "ml_labels_when_knee_below_150.csv", index=False, encoding="utf-8-sig")
    return {"phase": phase_table, "variants": variant_table, "knee": knee_table}


# ---------------------------------------------------------------- 7. 시점 판별


def active_window(reps_session: pd.DataFrame) -> tuple[float, float]:
    """운동 구간: 첫 반복 시작 1초 전 ~ 마지막 반복 끝 1초 후. 세션 앞의 자리 잡기와 끝의 돌아섬은 뺀다."""
    return float(reps_session.t_start.min() - 1.0), float(reps_session.t_end.max() + 1.0)


def stage_view(infos, sessions, reps: pd.DataFrame) -> dict:
    roles = {**{k: "side" for k in SIDE_SQUAT_IDS}, "6": "oblique", "7": "front"}
    frame_rows = []
    for sid, role in roles.items():
        s = sessions[sid]
        r = reps[(reps.session == sid) & (~reps.transit)]
        t0, t1 = active_window(r)
        m = s.standing_flag & s.person & (s.t >= t0) & (s.t <= t1)
        frame_rows.append(pd.DataFrame({"session": sid, "role": role, "t": s.t[m], "a": s.sig_a[m], "b": s.sig_b[m], "c": s.sig_c[m],
                                        "side_ac": s.view_side_now[m], "locked": s.locked[m], "lock_side": s.lock_view_side[m]}))
    frames = pd.concat(frame_rows, ignore_index=True)
    dist = frames.groupby(["role", "session"]).agg(
        n=("a", "size"), a_p5=("a", lambda x: x.quantile(0.05)), a_median=("a", "median"), a_p95=("a", lambda x: x.quantile(0.95)),
        b_p5=("b", lambda x: x.quantile(0.05)), b_median=("b", "median"), b_p95=("b", lambda x: x.quantile(0.95)),
        c_p5=("c", lambda x: x.quantile(0.05)), c_median=("c", "median"),
        side_ac_ratio=("side_ac", "mean"), locked_ratio=("locked", "mean"), lock_side_ratio=("lock_side", "mean"),
    ).reset_index()
    dist.to_csv(OUT_DIR / "view_signal_distribution.csv", index=False, encoding="utf-8-sig")

    side, non_side = frames[frames.role == "side"], frames[frames.role != "side"]
    sep_rows = []
    for name, col, side_is_low in (("(a) shoulder_ratio", "a", True), ("(b) hip_yaw_deg", "b", False), ("(c) nose_visibility", "c", False)):
        s_vals, n_vals = side[col].to_numpy(float), non_side[col].to_numpy(float)
        # AUC: 측면 프레임이 비측면 프레임보다 '측면다운' 방향으로 클 확률
        a_val = auc(-s_vals, -n_vals) if side_is_low else auc(s_vals, n_vals)
        sweep = []
        for cut in np.unique(np.round(np.quantile(np.concatenate([s_vals, n_vals])[~np.isnan(np.concatenate([s_vals, n_vals]))], np.linspace(0.01, 0.99, 197)), 3)):
            tpr = float((s_vals <= cut).mean()) if side_is_low else float((s_vals >= cut).mean())
            tnr_all = float((n_vals > cut).mean()) if side_is_low else float((n_vals < cut).mean())
            sweep.append((cut, tpr, tnr_all))
        best = max(sweep, key=lambda x: (x[1] + x[2]) / 2)
        sep_rows.append({"signal": name, "auc_side_vs_nonside": a_val, "best_cut": best[0], "side_tpr_at_best": best[1], "nonside_tnr_at_best": best[2]})
    for label, col in (("(a)+(c) current: a<=0.35 & c>=0.5", "side_ac"),):
        side_pass, non_pass = side[col].to_numpy(bool), non_side[col].to_numpy(bool)
        sep_rows.append({"signal": label, "auc_side_vs_nonside": float("nan"), "best_cut": float("nan"), "side_tpr_at_best": float(side_pass.mean()),
                         "nonside_tnr_at_best": float((~non_pass).mean())})
    for cut in (30, 40, 50, 60):
        side_pass, non_pass = (side.b >= cut).to_numpy(), (non_side.b >= cut).to_numpy()
        sep_rows.append({"signal": f"(b) yaw >= {cut}", "auc_side_vs_nonside": float("nan"), "best_cut": cut, "side_tpr_at_best": float(side_pass.mean()),
                         "nonside_tnr_at_best": float((~non_pass).mean())})
    for role in ("oblique", "front"):
        sub = frames[frames.role == role]
        sep_rows.append({"signal": f"[{role}] (a)+(c) judged non-side", "auc_side_vs_nonside": float("nan"), "best_cut": float("nan"),
                         "side_tpr_at_best": float("nan"), "nonside_tnr_at_best": float((~sub.side_ac).mean())})
        sep_rows.append({"signal": f"[{role}] (b>=50) judged non-side", "auc_side_vs_nonside": float("nan"), "best_cut": 50,
                         "side_tpr_at_best": float("nan"), "nonside_tnr_at_best": float((sub.b < 50).mean())})
    sep = pd.DataFrame(sep_rows)
    sep.to_csv(OUT_DIR / "view_separation.csv", index=False, encoding="utf-8-sig")

    # 반복 시작(STANDING에서 잠긴 값) 시점의 판정
    start_rows = []
    for sid, role in roles.items():
        r = reps[(reps.session == sid) & (~reps.transit)]
        for _, row in r.iterrows():
            start_rows.append({"session": sid, "role": role, "rep": row.rep, "lock_view_side_at_start": bool(row.lock_view_side_at_start),
                               "a": row.sig_a_start, "b": row.sig_b_start, "c": row.sig_c_start})
    starts = pd.DataFrame(start_rows)
    starts.to_csv(OUT_DIR / "view_at_rep_start.csv", index=False, encoding="utf-8-sig")
    return {"frames": frames, "dist": dist, "sep": sep, "starts": starts}


# ---------------------------------------------------------------- 8. 세션 0: 정면으로 돌아섰을 때 BodyLock


def nonside_runs(s, mask: np.ndarray, min_len: int = 1):
    """mask가 True(서 있는 상태에서 측면 아님)인 연속 구간: (시작 시각, 끝 시각, 프레임 수)."""
    runs, start = [], None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            if i - start >= min_len:
                runs.append((float(s.t[start]), float(s.t[i - 1]), i - start))
            start = None
    if start is not None:
        runs.append((float(s.t[start]), float(s.t[-1]), len(mask) - start))
    return runs


def stage_session0(infos, sessions, reps: pd.DataFrame) -> dict:
    s = sessions["0"]
    standing_nonside = s.standing_flag & ~s.view_side_now & s.person
    runs0 = nonside_runs(s, standing_nonside, min_len=3)
    rows = []
    for t0, t1, n in runs0:
        m = (s.t >= t0) & (s.t <= t1)
        events = [(round(float(s.t[i]), 2), s.lock_event[i]) for i in np.where(m)[0] if s.lock_event[i]]
        rows.append({"start_s": t0, "end_s": t1, "duration_s": t1 - t0, "frames": n, "locked_frames": int(s.locked[m].sum()),
                     "released_events": sum(1 for _, e in events if e == "released_missing"),
                     "lock_changed_events": sum(1 for _, e in events if e == "changed"),
                     "a_max": float(np.nanmax(s.sig_a[m])), "b_min": float(np.nanmin(s.sig_b[m]))})
    episodes = pd.DataFrame(rows)
    episodes.to_csv(OUT_DIR / "session0_nonside_standing_episodes.csv", index=False, encoding="utf-8-sig")

    # 측면 세션의 활동 구간에서, 서 있는 상태의 '측면 아님' 연속 구간 최대 길이(해제 지연 후보를 정하는 근거)
    calib_rows = []
    for sid in SIDE_SQUAT_IDS:
        sx = sessions[sid]
        r = reps[(reps.session == sid) & (~reps.transit)]
        t0, t1 = active_window(r)
        window = (sx.t >= t0) & (sx.t <= t1)
        mask = sx.standing_flag & ~sx.view_side_now & sx.person & window
        runs = nonside_runs(sx, mask)
        durations = [b - a for a, b, _ in runs]
        frames = [n for _, _, n in runs]
        calib_rows.append({"session": sid, "runs": len(runs), "longest_run_s": max(durations) if durations else 0.0,
                           "longest_run_frames": max(frames) if frames else 0, "nonside_frames_in_window": int(mask.sum()),
                           "standing_frames_in_window": int((sx.standing_flag & sx.person & window).sum())})
    calib = pd.DataFrame(calib_rows)
    calib.to_csv(OUT_DIR / "side_sessions_nonside_run_lengths.csv", index=False, encoding="utf-8-sig")
    return {"episodes": episodes, "calib": calib}


def stage_baseline_causes(infos, sessions, reps: pd.DataFrame, base: pd.DataFrame) -> dict:
    """v0.1.x 카운터가 놓친 반복의 원인: 반복마다 squat 라벨이 있었는가, 반복이 끝난 뒤 stand 라벨이 나왔는가, 카운트가 올랐는가."""
    rows = []
    for info in infos:
        sid = info.plan_id
        s = sessions[sid]
        _, events = replay_counter(s)
        r = reps[(reps.session == sid) & (~reps.transit)].reset_index(drop=True)
        for n, row in r.iterrows():
            nxt = float(r.t_start[n + 1]) if n + 1 < len(r) else float(s.t[-1])
            after = (s.t >= row.t_end) & (s.t < nxt)
            after_labels = pd.Series([str(x) for x in s.stable[after]]).value_counts()
            top = after_labels.index[0] if len(after_labels) else ""
            rows.append(
                {"session": sid, "rep_no": n + 1, "t_start": row.t_start, "t_end": row.t_end,
                 "squat_label_s": row.label_all_squat, "got_squat_label": row.label_all_squat >= 0.3,
                 "stand_label_after_s": float((np.append(np.diff(s.t), 0.0)[after & (np.array([str(x) for x in s.stable]) == "stand")]).sum()),
                 "top_label_after_rep": top, "top_label_after_share": float(after_labels.iloc[0] / after_labels.sum()) if len(after_labels) else float("nan"),
                 "counter_incremented_before_next_rep": any(row.t_start <= e < nxt for e in events)}
            )
    causes = pd.DataFrame(rows)
    causes["got_stand_after"] = causes.stand_label_after_s > 0
    causes.to_csv(OUT_DIR / "baseline_rep_causes.csv", index=False, encoding="utf-8-sig")
    summary = causes.groupby("session").agg(
        reps=("rep_no", "size"), got_squat_label=("got_squat_label", "sum"), got_stand_after=("got_stand_after", "sum"),
        counter_incremented=("counter_incremented_before_next_rep", "sum"),
        top_label_after_rep=("top_label_after_rep", lambda x: x.value_counts().index[0]),
    ).reset_index()
    summary.to_csv(OUT_DIR / "baseline_cause_summary.csv", index=False, encoding="utf-8-sig")
    return {"causes": causes, "summary": summary}


def stage_release_table(infos, base: pd.DataFrame, counts: pd.DataFrame) -> pd.DataFrame:
    """RELEASE.md 비교용: 세션별 실제 횟수 vs v0.1.x 카운트(재계산) vs 기하 반복 추출(임시 규칙) 검출 수."""
    rows = []
    for info in infos:
        b = base[base.session == info.plan_id].iloc[0]
        c = counts[counts.session == info.plan_id].iloc[0]
        rows.append(
            {"session": info.plan_id, "what": info.what, "actual_squats": "" if info.actual is None else info.actual,
             "nonsquat_motions": b.motions, "screen_count_v01x": b.screen_count, "replay_v01x": b.replay_v01x,
             "replay_matches_screen": b.match_screen, "geometry_candidates": c.candidates_raw_rule,
             "geometry_after_transit": c.detected_after_transit}
        )
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "release_comparison.csv", index=False, encoding="utf-8-sig")
    return table


def signal_runs(s, mask: np.ndarray):
    """mask(True)가 이어지는 구간: (시작 시각, 끝 시각, 프레임 수)."""
    runs, start = [], None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            runs.append((float(s.t[start]), float(s.t[i - 1]), i - start))
            start = None
    if start is not None:
        runs.append((float(s.t[start]), float(s.t[-1]), len(mask) - start))
    return runs


def stage_release_design(infos, sessions, reps: pd.DataFrame) -> dict:
    """STANDING 중 비측면이 되면 잠금을 해제하는 설계의 근거.

    - 해제: 측면 세션의 운동 구간(첫 반복 시작 1초 전 ~ 마지막 반복 끝 1초 후)에서 '측면 아님' 판정이 이어진 최대 길이 vs
      세션 0에서 실제로 돌아선 구간의 길이. 시점 신호가 있는 프레임 기준이고 전신 유효 여부는 보지 않는다.
    - 획득: 측면 판정이 0.5초 연속 유지된 첫 시각 vs 첫 반복 시작 시각.
    """
    rows = []
    for sid in SIDE_SQUAT_IDS:
        s = sessions[sid]
        r = reps[(reps.session == sid) & (~reps.transit)]
        t0, t1 = float(r.t_start.min() - 1.0), float(r.t_end.max() + 1.0)
        has = ~np.isnan(s.sig_a)
        window = (s.t >= t0) & (s.t <= t1)
        runs = signal_runs(s, has & ~s.view_side_now & window)
        side = s.view_side_now & s.person
        first = float("nan")
        for i in range(s.n):
            j = int(np.searchsorted(s.t, s.t[i] - 0.5))
            if s.t[i] - s.t[j] >= 0.45 and side[j : i + 1].all():
                first = float(s.t[i])
                break
        rows.append({"session": sid, "exercise_window_s": f"{t0:.1f}-{t1:.1f}", "nonside_runs_in_window": len(runs),
                     "longest_nonside_run_frames": max([n for *_, n in runs], default=0),
                     "longest_nonside_run_s": max([b - a for a, b, _ in runs], default=0.0),
                     "first_0.5s_continuous_side_at_s": first, "first_rep_start_s": float(r.t_start.min())})
    side_table = pd.DataFrame(rows)
    side_table.to_csv(OUT_DIR / "lock_release_evidence_side_sessions.csv", index=False, encoding="utf-8-sig")

    s0 = sessions["0"]
    has = ~np.isnan(s0.sig_a)
    runs0 = [(a, b, n) for a, b, n in signal_runs(s0, has & ~s0.view_side_now) if n >= 3]
    rows0 = []
    for a, b, n in runs0:
        m = (s0.t >= a) & (s0.t <= b)
        rows0.append({"start_s": a, "end_s": b, "frames": n, "duration_s": b - a, "locked_ratio": float(s0.locked[m].mean()),
                      "lock_view_side_ratio": float(s0.lock_view_side[m].mean()),
                      "lock_events": " ".join(str(e) for e in s0.lock_event[m] if e),
                      "stable_labels": " ".join(f"{k}:{v}" for k, v in pd.Series([str(x) for x in s0.stable[m]]).value_counts().items())})
    s0_table = pd.DataFrame(rows0)
    s0_table.to_csv(OUT_DIR / "lock_release_evidence_session0.csv", index=False, encoding="utf-8-sig")
    return {"side": side_table, "session0": s0_table}


def stage_view_extremes(view: dict) -> pd.DataFrame:
    frames = view["frames"]
    rows = []
    for role, g in frames.groupby("role"):
        rows.append({"role": role, "n": len(g), **{f"{c}_{q}": float(getattr(g[c], q)()) for c in ("a", "b") for q in ("min", "max")}})
    table = pd.DataFrame(rows)
    table.to_csv(OUT_DIR / "view_signal_extremes.csv", index=False, encoding="utf-8-sig")
    return table


# ---------------------------------------------------------------- 그래프

# 제안 경계(report.md의 표와 같은 값). (정상 상한, 교정 하한)
PROPOSAL = {"depth_knee_deg": (80.0, 95.0), "torso_shin_deg": (25.0, 35.0), "heel_bottom_norm": (0.10, 0.20)}
VIEW_CUT = {"a_current": 0.35, "a_proposed": 0.30, "b_proposed": 55.0}
# Okabe-Ito: 색각 이상에서도 구분되는 범주 색. 세션 의미(의도한 자세)마다 고정.
COLORS = {"normal": "#0072B2", "shallow": "#E69F00", "torso_lean": "#D55E00", "heel_lift": "#009E73", "reversed": "#CC79A7",
          "oblique": "#56B4E9", "front": "#999999", "walk": "#333333", "chair": "#F0E442", "lunge": "#882255"}
SESSION_COLOR = {"1": COLORS["normal"], "2": COLORS["normal"], "3": COLORS["shallow"], "4": COLORS["torso_lean"],
                 "5": COLORS["heel_lift"], "9": COLORS["reversed"], "6": COLORS["oblique"], "7": COLORS["front"],
                 "8a": COLORS["walk"], "8b": COLORS["chair"], "8c": COLORS["lunge"]}


def _strip(ax, groups: list[tuple[str, np.ndarray, str]], hlines=(), ylabel="", title=""):
    for x, (label, values, color) in enumerate(groups):
        values = np.asarray(values, float)
        jitter = (np.random.default_rng(x).random(len(values)) - 0.5) * 0.3
        ax.scatter(np.full(len(values), x) + jitter, values, s=22, color=color, edgecolor="white", linewidth=0.6, zorder=3)
        ax.hlines(np.nanmedian(values), x - 0.3, x + 0.3, color="black", linewidth=1.2, zorder=4)
    for value, text, style in hlines:
        ax.axhline(value, color="#555555", linestyle=style, linewidth=1)
        ax.text(len(groups) - 0.5, value, f" {text}", va="bottom", ha="right", fontsize=7, color="#333333")
    ax.set_xticks(range(len(groups)), [g[0] for g in groups], fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_title(title, fontsize=9, loc="left")
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)


def stage_plots(infos, sessions, reps, ns, ml, view) -> None:
    import matplotlib.pyplot as plt

    plot_dir = OUT_DIR / "plots"
    plot_dir.mkdir(exist_ok=True)
    use = reps[(~reps.transit)]

    # A. 반복 추출 개요: 세션별 평활 무릎각과 검출 구간
    fig, axes = plt.subplots(5, 3, figsize=(17, 14))
    for ax, info in zip(axes.ravel(), infos):
        s = sessions[info.plan_id]
        spans, k = extract_reps(s.t, s.knee_s)
        ax.plot(s.t, k, color="#1d4e89", linewidth=1)
        for _, row in reps[reps.session == info.plan_id].iterrows():
            color = "#999999" if row.transit else ("#D55E00" if row.short else "#009E73")
            ax.axvspan(row.t_start, row.t_end, color=color, alpha=0.25, linewidth=0)
        ax.axhline(160, color="#555555", linestyle=":", linewidth=0.8)
        ax.axhline(150, color="#555555", linestyle=":", linewidth=0.8)
        r = reps[reps.session == info.plan_id]
        ax.set_title(f"{info.plan_id} {info.what} | actual {'-' if info.actual is None else info.actual}, "
                     f"candidates {len(r)}, after transit {int((~r.transit).sum())}", fontsize=8, loc="left")
        ax.set_ylim(0, 190)
        ax.tick_params(labelsize=7)
    for ax in axes.ravel()[len(infos):]:
        ax.axis("off")
    fig.suptitle("Offline rep extraction (smoothed knee angle, 160/150 hysteresis). green = rep, orange = short (<1 s), gray = transit (excluded)", fontsize=10)
    fig.tight_layout()
    fig.savefig(plot_dir / "rep_extraction_overview.png", dpi=110)
    plt.close(fig)

    # B. 판정 지표 분포
    order = ["1", "2", "9", "3", "4", "5"]
    names = {"1": "1 parallel", "2": "2 deep", "9": "9 reversed", "3": "3 shallow", "4": "4 torso", "5": "5 heel"}
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5))
    specs = [
        ("min_knee_smoothed", "depth: lowest knee angle (deg, higher = shallower)", [(PROPOSAL["depth_knee_deg"][0], "normal <= 80", "--"), (PROPOSAL["depth_knee_deg"][1], "correct >= 95", ":")]),
        ("hip_below_knee_norm", "depth (aux): hip y - knee y, / leg length (>0 = hip below knee)", []),
        ("abs_torso_minus_shin_signed_deg", "torso_shin: |torso - shin| at bottom (deg)", [(PROPOSAL["torso_shin_deg"][0], "normal <= 25", "--"), (PROPOSAL["torso_shin_deg"][1], "correct >= 35", ":")]),
        ("heel_rise_px", "heel: rise vs standing, min over rep (px) [spec definition]", []),
        ("heel_rise_bottom_norm", "heel: rise at bottom, median / leg length [robust]", [(PROPOSAL["heel_bottom_norm"][0], "placeholder 0.10", "--"), (PROPOSAL["heel_bottom_norm"][1], "placeholder 0.20", ":")]),
        ("foot_pitch_delta_deg", "heel (alt): foot pitch change heel->toe (deg)", []),
    ]
    for ax, (metric, title, lines) in zip(axes.ravel(), specs):
        groups = [(names[sid], use[use.session == sid][metric].to_numpy(float), SESSION_COLOR[sid]) for sid in order]
        _strip(ax, groups, hlines=lines, title=title)
    fig.suptitle("Per-rep metrics by session (dots = reps, bar = median). Sessions 1,2 = normal reference; 3/4/5 = intended fault; 9 = reversed facing", fontsize=10)
    fig.tight_layout()
    fig.savefig(plot_dir / "threshold_metric_distributions.png", dpi=110)
    plt.close(fig)

    # C. 비스쿼트 배제 지표
    df = ns["df"]
    df = df[~df.transit]
    normal = df[df.session.isin(SIDE_SQUAT_IDS)]
    groups_def = [("squat 1-5,9", normal, COLORS["normal"]), ("walk 8a", df[df.session == "8a"], COLORS["walk"]),
                  ("chair 8b", df[df.session == "8b"], COLORS["chair"]), ("lunge 8c", df[df.session == "8c"], COLORS["lunge"])]
    fig, axes = plt.subplots(2, 4, figsize=(18, 8.5))
    specs = [("t_total", "rep duration (s)", [(1.0, ">= 1.0", "--")]), ("hip_drop_norm", "hip drop / leg length", [(0.25, ">= 0.25", "--")]),
             ("ankle_gap_start_norm", "ankle gap at standing / leg length (side view)", [(0.25, "<= 0.25", "--")]),
             ("torso_signed_deg", "torso lean at bottom (deg, forward +)", [(30, ">= 30", "--")]),
             ("t_bottom_dwell", "bottom dwell (s)", [(2.2, "<= 2.2 (no margin)", ":")]),
             ("knee_lr_diff_at_bottom", "|left - right knee| at bottom (deg)", [(8, "<= 8 (rejects s9)", ":")]),
             ("sit_share", "'sit' label share of rep", [(0.25, "<= 0.25", "--")]),
             ("ml_excl_share", "walk+run+jump+lying share of rep", [(0.45, "<= 0.45", "--")])]
    for ax, (metric, title, lines) in zip(axes.ravel(), specs):
        _strip(ax, [(lab, d[metric].to_numpy(float), c) for lab, d, c in groups_def], hlines=lines, title=title)
    fig.suptitle("Non-squat vs squat candidates (rep-level). Squat group = sessions 1-5 and 9 after transit exclusion", fontsize=10)
    fig.tight_layout()
    fig.savefig(plot_dir / "nonsquat_features.png", dpi=110)
    plt.close(fig)

    # D. ML 라벨 구간별 비율
    phase = ml["phase"]
    label_colors = {"squat": "#0072B2", "stand": "#009E73", "bendover": "#E69F00", "jump": "#D55E00", "walk": "#333333", "run": "#882255",
                    "sit": "#F0E442", "lying": "#CC79A7", "stretch": "#56B4E9", "None": "#CCCCCC"}
    groups = list(phase.group.unique())
    fig, axes = plt.subplots(1, len(groups), figsize=(18, 4.5), sharey=True)
    for ax, group in zip(axes, groups):
        bottom = np.zeros(3)
        for label in LABELS:
            values = np.array([phase[(phase.group == group) & (phase.phase == ph) & (phase.label == label)].share_of_time.iloc[0] for ph in ("descent", "bottom", "ascent")])
            ax.bar(["descent", "bottom", "ascent"], values, bottom=bottom, color=label_colors[label], label=label, edgecolor="white", linewidth=0.8)
            bottom += np.nan_to_num(values)
        ax.set_title(group, fontsize=9, loc="left")
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("share of time (stable label)")
    axes[-1].legend(fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.tight_layout()
    fig.savefig(plot_dir / "ml_label_share_by_phase.png", dpi=110)
    plt.close(fig)

    # E. 시점 신호 분포 (서 있는 프레임, 운동 구간)
    frames = view["frames"]
    role_color = {"side": COLORS["normal"], "oblique": COLORS["oblique"], "front": COLORS["front"]}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for ax, (col, title, lines) in zip(axes, [("a", "(a) shoulder ratio", [(VIEW_CUT["a_current"], "current 0.35", "--"), (VIEW_CUT["a_proposed"], "proposed 0.30", ":")]),
                                              ("b", "(b) hip yaw (deg; 90 = side)", [(VIEW_CUT["b_proposed"], "proposed 55", "--")]),
                                              ("c", "(c) nose visibility", [(0.5, "0.5", "--")])]):
        _strip(ax, [(role, frames[frames.role == role][col].to_numpy(float)[::3], role_color[role]) for role in ("side", "oblique", "front")], hlines=lines, title=title)
    fig.suptitle("View signals on standing frames inside the exercise window (every 3rd frame shown)", fontsize=10)
    fig.tight_layout()
    fig.savefig(plot_dir / "view_signals.png", dpi=110)
    plt.close(fig)

    # F. 세션 0: 정면으로 돌아선 구간의 BodyLock
    s = sessions["0"]
    fig, axes = plt.subplots(3, 2, figsize=(15, 8.5), sharex="col")
    for col, (t0, t1) in enumerate(((25.0, 36.0), (70.0, 80.0))):
        m = (s.t >= t0) & (s.t <= t1)
        t = s.t[m]
        axes[0, col].plot(t, s.knee_s[m], color="#1d4e89", linewidth=1.2)
        axes[0, col].axhline(160, color="#555555", linestyle=":", linewidth=0.8)
        axes[0, col].set_ylabel("knee_smoothed (deg)", fontsize=8)
        axes[1, col].plot(t, s.sig_a[m], color="#D55E00", linewidth=1.2, label="(a) shoulder ratio")
        axes[1, col].axhline(0.35, color="#D55E00", linestyle="--", linewidth=0.8)
        ax2 = axes[1, col].twinx()
        ax2.plot(t, s.sig_b[m], color="#009E73", linewidth=1.2, label="(b) hip yaw")
        ax2.set_ylim(0, 95)
        axes[1, col].set_ylim(0, 1.0)
        axes[1, col].set_ylabel("(a)", fontsize=8)
        ax2.set_ylabel("(b) deg", fontsize=8)
        locked = np.where(s.locked[m], 1.0, np.nan)
        lock_side = np.where(s.lock_view_side[m] & s.locked[m], 0.5, np.nan)
        axes[2, col].plot(t, locked, color="#333333", linewidth=6, solid_capstyle="butt", label="BodyLock locked")
        axes[2, col].plot(t, lock_side, color="#0072B2", linewidth=6, solid_capstyle="butt", label="locked view = side")
        events = [(s.t[i], str(s.lock_event[i])) for i in np.where(m)[0] if s.lock_event[i]]
        for te, ev in events:
            axes[2, col].axvline(te, color="#D55E00", linewidth=0.8, alpha=0.7)
        axes[2, col].set_ylim(0, 1.5)
        axes[2, col].set_yticks([])
        axes[2, col].set_xlabel("time (s)", fontsize=8)
        if col == 0:
            axes[2, col].legend(fontsize=7, loc="upper left", ncol=2)
        axes[0, col].set_title(f"session 0, {t0:.0f}-{t1:.0f} s (orange vertical lines = lock 'changed' events)", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(plot_dir / "session0_turn_lock.png", dpi=110)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    infos, sessions = load_all()

    mq = stage_match_and_quality(infos, sessions)
    print("== 세션 매칭\n" + mq["match"].to_string(index=False))
    print("== 데이터 품질\n" + mq["quality"].round(3).to_string(index=False))
    base = stage_baseline(infos, sessions)
    print("== v0.1.x 기준선\n" + base.to_string(index=False))
    reps = stage_reps(infos, sessions)
    counts = rep_count_table(infos, reps)
    print("== 반복 수\n" + counts.to_string(index=False))
    causes = stage_baseline_causes(infos, sessions, reps, base)
    print("== v0.1.x 불일치 원인(반복 단위 요약)\n" + causes["summary"].to_string(index=False))
    print("== RELEASE 비교표\n" + stage_release_table(infos, base, counts).to_string(index=False))

    th = stage_thresholds(reps)
    print("== 경계값 분리도\n" + th["sep"].round(3).to_string(index=False))
    print("== 세션별 분포\n" + th["stats"].round(2).to_string(index=False))
    print("== 세션 9 vs 1·2\n" + stage_reversed_check(reps).round(3).to_string(index=False))
    ns = stage_nonsquat(reps)
    print("== 비스쿼트 지표\n" + ns["summary"].to_string())
    print("== 비스쿼트 조건\n" + ns["conditions"].to_string(index=False))
    ab = stage_ablation(ns)
    print("== ablation (leave-one-out)\n" + ab["loo"].to_string(index=False))
    print("== ablation margins\n" + ab["margins"].round(3).T.to_string())
    ml = stage_ml(reps, infos, sessions)
    print("== ML 구간별\n" + ml["phase"][ml["phase"].phase != "all"].pivot_table(index=["group", "label"], columns="phase", values="share_of_time").round(3).to_string())
    print("== ML 변형\n" + ml["variants"].round(3).to_string(index=False))
    print("== 무릎각<150 라벨\n" + ml["knee"].round(3).to_string(index=False))
    view = stage_view(infos, sessions, reps)
    print("== 시점 분포\n" + view["dist"].round(3).to_string(index=False))
    print("== 시점 분리\n" + view["sep"].round(3).to_string(index=False))
    print("== 반복 시작 시점 판정\n" + view["starts"].groupby(["role", "session"]).lock_view_side_at_start.agg(["sum", "count"]).to_string())
    print("== 시점 신호 극값(활동 구간, 서 있는 프레임)\n" + stage_view_extremes(view).round(3).to_string(index=False))
    s0 = stage_session0(infos, sessions, reps)
    design = stage_release_design(infos, sessions, reps)
    print("== 해제·획득 설계 근거: 측면 세션\n" + design["side"].round(2).to_string(index=False))
    print("== 해제 설계 근거: 세션 0의 비측면 구간\n" + design["session0"].round(2).to_string(index=False))
    stage_plots(infos, sessions, reps, ns, ml, view)
    print(f"plots saved to {OUT_DIR / 'plots'}")
    print("== 세션0 서있는 비측면 구간\n" + s0["episodes"].round(2).to_string(index=False))
    print("== 측면 세션 비측면 연속 구간\n" + s0["calib"].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
