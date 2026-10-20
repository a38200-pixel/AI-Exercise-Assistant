"""랜드마크 공백(YOLO가 사람을 찾았는데 PoseLandmarker가 landmark를 못 돌려준 프레임, 또는 사람 자체를 놓친 프레임)이 어디에 몰리는지 분석한다.

입력: 원본 로그(--log). 분석만 하며 제품 코드는 바꾸지 않는다. 카메라를 쓰지 않는다.
공백의 종류: yolo_miss = person False(YOLO가 사람을 못 찾음), pose_miss = person True인데 landmarks 없음(MediaPipe가 crop에서 포즈를 못 찾음).
자세(서 있음/하강/최저점 부근/상승)와 무릎각 구간은 공백 프레임에는 무릎각이 없으므로 앞뒤 유효 프레임의 무릎각을 보간해 정한다.

실행(저장소 루트에서): python -m scripts.analysis.landmark_gap_analysis --log data/landmark_sequences/session_*.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.analysis import replay_flags as rf  # noqa: E402

SLOPE_WINDOW = 0.25  # 초: 이 앞뒤 무릎각 차이로 방향을 정한다
SLOPE_DEG_PER_S = 30.0
PHASES = ("서 있음", "하강", "최저점 부근", "상승")
KNEE_BANDS = (("≥160", 160.0, 400.0), ("100~160", 100.0, 160.0), ("<100", -1.0, 100.0))


def load(path: Path) -> list[dict[str, Any]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["type"] == "frame":
            out.append(record)
    return out


def set_span(path: Path) -> tuple[float, float] | None:
    """확정된 반복의 첫 시작~마지막 끝(세트). 반복이 없으면 None."""
    result = rf.replay(rf.load_log(path))
    spans = [(r.t_start, r.t_end) for r in result.results if r.counted]
    return (spans[0][0], spans[-1][1]) if spans else None


def annotate(frames: list[dict[str, Any]]) -> None:
    """프레임마다 gap(None/'yolo_miss'/'pose_miss'), 보간 무릎각, 자세, bbox 특징을 붙인다."""
    t = np.array([f["t"] for f in frames])
    valid = np.array([f.get("landmarks") is not None and f.get("geometry") is not None for f in frames])
    knee_raw = np.array([f["geometry"]["knee"] if v and f["geometry"].get("knee") is not None else np.nan for f, v in zip(frames, valid)])
    ok = ~np.isnan(knee_raw)
    knee = np.interp(t, t[ok], knee_raw[ok]) if ok.sum() > 1 else np.full_like(t, np.nan)
    before = np.interp(t - SLOPE_WINDOW, t[ok], knee_raw[ok])
    after = np.interp(t + SLOPE_WINDOW, t[ok], knee_raw[ok])
    slope = (after - before) / (2 * SLOPE_WINDOW)
    for i, f in enumerate(frames):
        f["_gap"] = None if f.get("landmarks") is not None else ("pose_miss" if f.get("person") else "yolo_miss")
        f["_knee"] = float(knee[i])
        if slope[i] < -SLOPE_DEG_PER_S:
            f["_phase"] = "하강"
        elif slope[i] > SLOPE_DEG_PER_S:
            f["_phase"] = "상승"
        else:
            f["_phase"] = "서 있음" if knee[i] >= 160 else "최저점 부근"
        bbox = f.get("yolo_bbox")
        f["_bbox"] = None
        if f.get("person") and bbox:
            width, height = f["frame_size"]
            x1, y1, x2, y2 = bbox
            edge = min(x1, y1, width - x2, height - y2)
            f["_bbox"] = {"h": (y2 - y1) / height, "ar": (y2 - y1) / max(1, x2 - x1), "edge": edge, "touch": edge <= 2}
    previous = None
    for f in frames:
        b = f["_bbox"]
        if b is not None and previous is not None and f["t"] - previous[0] <= 0.2:
            b["dh"] = abs(b["h"] - previous[1]["h"]) / max(previous[1]["h"], 1e-6)
        if b is not None:
            previous = (f["t"], b)


def runs(frames: list[dict[str, Any]]) -> list[tuple[float, float, int]]:
    """랜드마크가 연속으로 없는 구간 (시작 시각, 길이 초, 프레임 수)."""
    out, start, count, last = [], None, 0, None
    dts = np.diff([f["t"] for f in frames])
    dt = float(np.median(dts[dts > 0])) if len(dts) else 0.06
    for f in frames:
        if f["_gap"]:
            if start is None:
                start, count = f["t"], 0
            count += 1
            last = f["t"]
        elif start is not None:
            out.append((start, last - start + dt, count))
            start = None
    if start is not None:
        out.append((start, last - start + dt, count))
    return out


def rate_table(rows: list[tuple[str, int, int]], title: str) -> str:
    lines = [f"| {title} | 프레임 수 | pose_miss(YOLO는 찾음) 비율 |", "|---|---|---|"]
    for name, bad, total in rows:
        lines.append(f"| {name} | {total} | {bad / total * 100:.1f}% ({bad}) |" if total else f"| {name} | 0 | - |")
    return "\n".join(lines)


def count(frames: list[dict[str, Any]], predicate) -> tuple[int, int]:
    selected = [f for f in frames if predicate(f)]
    return sum(1 for f in selected if f["_gap"]), len(selected)


def pct(values: list[float], q: float) -> float:
    return float(np.percentile(values, q)) if values else float("nan")


def report_tables(label: str, frames: list[dict[str, Any]]) -> None:
    yolo = [f for f in frames if f.get("person")]
    boxed = [f for f in yolo if f["_bbox"]]
    changed = [f for f in boxed if "dh" in f["_bbox"]]
    print(f"\n## pose_miss가 몰리는 곳 ({label}, YOLO가 사람을 찾은 프레임 {len(yolo)}개 기준)")
    print(rate_table([(p, *count(yolo, lambda f, p=p: f["_phase"] == p)) for p in PHASES], "자세(보간 무릎각 기울기)"))
    print()
    print(rate_table([(n, *count(yolo, lambda f, lo=lo, hi=hi: lo <= f["_knee"] < hi)) for n, lo, hi in KNEE_BANDS], "보간 무릎각 구간"))
    print()
    edge_bins = (("경계 접촉(≤2px)", -1, 2), ("경계 3~20px", 2, 20), ("경계 20px 초과", 20, 10**6))
    print(rate_table([(n, *count(boxed, lambda f, lo=lo, hi=hi: lo < f["_bbox"]["edge"] <= hi)) for n, lo, hi in edge_bins], "bbox와 프레임 경계 거리"))
    print()
    height_bins = (("0.6 미만", 0.0, 0.6), ("0.6~0.8", 0.6, 0.8), ("0.8~0.95", 0.8, 0.95), ("0.95 이상", 0.95, 2.0))
    print(rate_table([(n, *count(boxed, lambda f, lo=lo, hi=hi: lo <= f["_bbox"]["h"] < hi)) for n, lo, hi in height_bins], "bbox 높이(프레임 높이 대비)"))
    print()
    change_bins = (("<2%", 0.0, 0.02), ("2~5%", 0.02, 0.05), ("5~10%", 0.05, 0.10), ("≥10%", 0.10, 9.0))
    print(rate_table([(n, *count(changed, lambda f, lo=lo, hi=hi: lo <= f["_bbox"]["dh"] < hi)) for n, lo, hi in change_bins], "직전 프레임 대비 bbox 높이 변화"))
    print()
    ratio_bins = (("<2.0", 0.0, 2.0), ("2.0~3.0", 2.0, 3.0), ("3.0~4.0", 3.0, 4.0), ("≥4.0", 4.0, 99.0))
    print(rate_table([(n, *count(boxed, lambda f, lo=lo, hi=hi: lo <= f["_bbox"]["ar"] < hi)) for n, lo, hi in ratio_bins], "bbox 종횡비(h/w)"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="+", type=Path, required=True)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("## 로그별 요약")
    print("| 로그 | 프레임 | 공백 전체 | yolo_miss | pose_miss | 세트 안 공백률(프레임) | 세트 밖 공백률(프레임) |")
    print("|---|---|---|---|---|---|---|")
    pooled: list[dict[str, Any]] = []
    all_runs: dict[str, list[float]] = {"세트 안": [], "세트 밖": []}
    follow = [0, 0]
    for path in args.log:
        frames = load(path)
        annotate(frames)
        span = set_span(path)
        for f in frames:
            f["_in_set"] = span is not None and span[0] <= f["t"] <= span[1]
        gap = sum(1 for f in frames if f["_gap"])
        inside = [f for f in frames if f["_in_set"]]
        outside = [f for f in frames if not f["_in_set"]]
        rate = lambda xs: f"{sum(1 for f in xs if f['_gap']) / len(xs) * 100:.1f}% ({len(xs)})" if xs else "-"
        print(
            f"| {path.stem[8:]} | {len(frames)} | {gap / len(frames) * 100:.1f}% | {sum(1 for f in frames if f['_gap'] == 'yolo_miss')} "
            f"| {sum(1 for f in frames if f['_gap'] == 'pose_miss')} | {rate(inside)} | {rate(outside)} |"
        )
        pooled.extend(frames)
        for a, b in zip(frames[:-1], frames[1:]):
            if a["_gap"] == "pose_miss" and b.get("person"):
                follow[1] += 1
                follow[0] += bool(b["_gap"])
        for start, length, _ in runs(frames):
            all_runs["세트 안" if span is not None and span[0] <= start <= span[1] else "세트 밖"].append(length)

    in_set = [f for f in pooled if f["_in_set"]]
    print(f"\n전체 프레임 {len(pooled)}개 (세트 안 {len(in_set)}개, 세트 밖 {len(pooled) - len(in_set)}개).")
    report_tables("세트 안", in_set)
    report_tables("전체", pooled)
    print(f"\n직전 프레임이 pose_miss이고 이번에도 YOLO가 사람을 찾았을 때 다시 pose_miss일 비율: {follow[0] / max(1, follow[1]) * 100:.1f}% ({follow[1]}개 중)")

    print("\n## 공백 길이 분포(연속으로 landmark가 없는 구간)")
    print("| 구분 | 구간 수 | 중앙값 | p90 | p99 | 최대 | >0.3초 | >0.5초 | >1.0초 | >1.5초 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name, lengths in all_runs.items():
        if lengths:
            print(
                f"| {name} | {len(lengths)} | {pct(lengths, 50):.2f}s | {pct(lengths, 90):.2f}s | {pct(lengths, 99):.2f}s | {max(lengths):.2f}s "
                f"| {sum(v > 0.3 for v in lengths)} | {sum(v > 0.5 for v in lengths)} | {sum(v > 1.0 for v in lengths)} | {sum(v > 1.5 for v in lengths)} |"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
