"""재생 도구가 실제 코드와 같은 판정을 내는지 로그마다 비교한다. 카메라를 쓰지 않는다. 제품 코드는 바꾸지 않는다.

같은 로그를 세 방법으로 본다(모두 같은 RepTracker 설정으로, 기본은 로그를 만들 때의 설정: ML 상한 0.40, 새 조건 꺼짐):
  live   로그의 rep_end 이벤트: 로그를 만들 때 **실제 앱 코드**가 내린 판정(이벤트가 있는 로그만. 코드가 그 뒤 바뀌었으면 달라질 수 있다)
  G      geometry_replay.replay: 원본 landmark에서 GeometryTracker + RepTracker를 처음부터 다시 돌림(실제 코드 전체)
  R      replay_flags.replay: 로그에 기록된 신호(평활 무릎각, 측면 판정, leg_now 등)를 BodyLockPolicy + RepTracker에 넣음(분석 도구의 자체 접착 코드)
비교 단위는 반복 후보: 시작 시각(0.15초 이내), 확정 여부, 탈락 사유, 측정값(엉덩이 하강, 서 있을 때 양발 간격, ML 비율).
R이 G와 다르면 replay_flags의 접착 코드(잠금 다리 선택, 평활 등)가 실제 파이프라인과 다르게 계산하는 것이다.

실행(저장소 루트에서): python -m scripts.analysis.replay_fidelity_check --log data/landmark_sequences/session_*.jsonl [--current]
  --current: 새 기본 설정(ML 조건 없음, 새 조건 켜짐)으로 비교한다(live 열은 건너뜀)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import geometry_replay as gr  # noqa: E402
import replay_flags as rf  # noqa: E402
from src.rep_tracker import RepTracker  # noqa: E402

OLD_SETTINGS = {"other_max_ratio": 0.40, "max_ankle_gap_bottom": None, "max_hip_shift": None}
START_TOLERANCE = 0.15
VALUE_TOLERANCE = 0.02


def live_events(path: Path):
    events = []
    for line in path.open("r", encoding="utf-8"):
        record = json.loads(line)
        if record.get("type") == "event" and record.get("kind") == "rep_end":
            events.append(record)
    return events


def as_rows_from_result(results):
    return [
        {"t": r.t_start, "counted": r.counted, "reasons": tuple(sorted(r.reasons)), "hip": r.hip_drop_norm, "gap": r.ankle_gap_norm, "ml": r.other_exercise_ratio}
        for r in results
    ]


def as_rows_from_events(events):
    nan = float("nan")
    return [
        {
            "t": e["t_start"], "counted": e["counted"], "reasons": tuple(sorted(e["reasons"])),
            "hip": nan if e.get("hip_drop_norm") is None else e["hip_drop_norm"],
            "gap": nan if e.get("ankle_gap_norm") is None else e["ankle_gap_norm"],
            "ml": nan if e.get("other_exercise_ratio") is None else e["other_exercise_ratio"],
        }
        for e in events
    ]


def close(a, b):
    return (math.isnan(a) and math.isnan(b)) or abs(a - b) <= VALUE_TOLERANCE


def compare(left, right):
    """두 반복 목록을 순서대로 맞춰 본다. 반환: (같은 반복 수, 다른 점 목록)."""
    problems = []
    if len(left) != len(right):
        problems.append(f"후보 수 {len(left)} 대 {len(right)}")
    same = 0
    for a, b in zip(left, right):
        if abs(a["t"] - b["t"]) > START_TOLERANCE:
            problems.append(f"시작 {a['t']:.2f}s 대 {b['t']:.2f}s")
            continue
        diffs = []
        if a["counted"] != b["counted"] or a["reasons"] != b["reasons"]:
            diffs.append(f"판정 {a['counted']}{list(a['reasons'])} 대 {b['counted']}{list(b['reasons'])}")
        for key in ("hip", "gap", "ml"):
            if not close(a[key], b[key]):
                diffs.append(f"{key} {a[key]:.2f} 대 {b[key]:.2f}")
        if diffs:
            problems.append(f"{a['t']:.1f}s: " + "; ".join(diffs))
        else:
            same += 1
    return same, problems


def run_G(path: Path, rep_options):
    frames, _ = gr.read_frames(path)
    return as_rows_from_result(gr.replay(frames, {"tracker": {}, "rep": rep_options})["results"])


def run_R(path: Path, rep_options):
    original = rf.RepTracker
    rf.RepTracker = partial(RepTracker, **rep_options)
    try:
        return as_rows_from_result(rf.replay(rf.load_log(path), rf.PRESETS["off"]).results)
    finally:
        rf.RepTracker = original


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="+", type=Path, required=True)
    parser.add_argument("--current", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    options = {} if args.current else OLD_SETTINGS
    print(f"설정: {'새 기본(ML 조건 없음, 새 조건 켜짐)' if args.current else '로그 생성 당시(ML 상한 0.40, 새 조건 꺼짐)'}")
    print("| 로그 | 후보 | R 대 G | live 대 G | live 대 R | 다른 점(처음 3개) |")
    print("|---|---|---|---|---|---|")
    bad = 0
    for path in args.log:
        g, r = run_G(path, options), run_R(path, options)
        live = as_rows_from_events(live_events(path)) if not args.current else []
        rg_same, rg_problems = compare(r, g)
        cells = [f"{rg_same}/{len(g)}" if not rg_problems else f"{rg_same}/{len(g)} 다름"]
        problems = list(rg_problems)
        for name, left, right in (("live 대 G", live, g), ("live 대 R", live, r)):
            if not live:
                cells.append("-")
                continue
            same, probs = compare(left, right)
            cells.append(f"{same}/{len(live)}" if not probs else f"{same}/{len(live)} 다름")
            problems += [f"[{name}] {p}" for p in probs]
        bad += bool(rg_problems)
        print(f"| {path.stem[8:]} | {len(g)} | {cells[0]} | {cells[1]} | {cells[2]} | {'; '.join(problems[:3]) or '-'} |")
    print(f"\nR 대 G가 다른 로그: {bad}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
