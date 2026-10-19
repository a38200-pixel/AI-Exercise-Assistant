"""구도 안내(FramingGuide)를 원본 로그에 재생해, 안내가 켜졌을 구간과 실제 랜드마크 공백 구간의 겹침을 센다. 카메라를 쓰지 않는다.

로그의 YOLO bbox(yolo_bbox)와 프레임 크기만 쓴다. 반복 중(IN_REP) 여부는 RepTracker 재생 결과의 반복 후보 구간(시작~끝)으로 정한다.
공백(gap) = 사람(YOLO)은 있는데 landmark가 없는 프레임(pose_miss). 세트 = 확정된 반복의 첫 시작~마지막 끝.

실행(저장소 루트에서): python -m scripts.analysis.framing_replay --log data/landmark_sequences/session_*.jsonl [--delays 1.0 1.5 2.0] [--list]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.analysis import landmark_gap_analysis as gaps  # noqa: E402
from scripts.analysis import replay_flags as rf  # noqa: E402
from src.framing_guide import FramingGuide, classify_framing  # noqa: E402


def candidate_spans(path: Path) -> list[tuple[float, float]]:
    result = rf.replay(rf.load_log(path), rf.PRESETS["off"])
    return [(r.t_start, r.t_end) for r in result.results]


def run(frames: list[dict[str, Any]], spans: list[tuple[float, float]], delay: float) -> list[dict[str, Any]]:
    guide = FramingGuide(delay_seconds=delay)
    out = []
    for f in frames:
        in_rep = any(s <= f["t"] <= e for s, e in spans)
        bbox = f.get("yolo_bbox") if f.get("person") else None
        shown = guide.update(bbox, tuple(f["frame_size"]), f["t"], in_rep=in_rep)
        out.append({"t": f["t"], "shown": shown, "raw": classify_framing(bbox, tuple(f["frame_size"])) if bbox else None, "in_rep": in_rep})
    return out


def intervals(states: list[dict[str, Any]]) -> list[tuple[float, float, str]]:
    result, start, kind, last = [], None, None, None
    for state in states:
        if state["shown"] and start is None:
            start, kind = state["t"], state["shown"]
        if state["shown"]:
            last = state["t"]
        elif start is not None:
            result.append((start, last, kind))
            start = None
    if start is not None:
        result.append((start, last, kind))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="+", type=Path, required=True)
    parser.add_argument("--delays", nargs="+", type=float, default=[1.0, 1.5, 2.0])
    parser.add_argument("--list", action="store_true", help="세트 안에서 안내가 켜진 구간을 나열")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logs = []
    for path in args.log:
        frames = gaps.load(path)
        gaps.annotate(frames)
        logs.append((path, frames, gaps.set_span(path), candidate_spans(path)))

    print(f"| 지속 시간 | 안내 켜진 구간 수(로그 {len(logs)}개) | 켜진 프레임 중 공백(pose_miss) 비율 | 공백 프레임 중 안내가 켜져 있던 비율 | 세트 안 켜진 프레임 / 세트 안 프레임 | 세트 안 켜진 구간 수 |")
    print("|---|---|---|---|---|---|")
    detail: dict[float, list[str]] = {}
    for delay in args.delays:
        shown_total = shown_gap = gap_total = gap_shown = in_set_shown = in_set_total = count = in_set_intervals = 0
        lines = []
        for path, frames, span, spans in logs:
            states = run(frames, spans, delay)
            ivs = intervals(states)
            count += len(ivs)
            for f, s in zip(frames, states):
                in_set = span is not None and span[0] <= f["t"] <= span[1]
                gap = f["_gap"] == "pose_miss"
                if gap:
                    gap_total += 1
                    gap_shown += bool(s["shown"])
                if s["shown"]:
                    shown_total += 1
                    shown_gap += gap
                if in_set:
                    in_set_total += 1
                    in_set_shown += bool(s["shown"])
            for start, end, kind in ivs:
                if span is not None and span[0] <= start <= span[1]:
                    in_set_intervals += 1
                    window = [f for f in frames if start <= f["t"] <= end]
                    margins = [f["frame_size"][1] - f["yolo_bbox"][3] for f in window if f.get("yolo_bbox")]
                    lines.append(
                        f"{path.stem[8:]} {start:.1f}~{end:.1f}s {kind}: 구간 안 공백 프레임 {sum(f['_gap'] == 'pose_miss' for f in window)}/{len(window)}, "
                        f"bbox 아래 여유 최소 {min(margins) if margins else '-'}px"
                    )
        detail[delay] = lines
        print(
            f"| {delay:g}초 | {count} | {shown_gap / max(1, shown_total) * 100:.1f}% ({shown_gap}/{shown_total}) "
            f"| {gap_shown / max(1, gap_total) * 100:.1f}% ({gap_shown}/{gap_total}) | {in_set_shown}/{in_set_total} | {in_set_intervals} |"
        )
    if args.list:
        for delay, lines in detail.items():
            print(f"\n세트 안에서 켜진 구간(지속 {delay:g}초):")
            for line in lines or ["(없음)"]:
                print("- " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
