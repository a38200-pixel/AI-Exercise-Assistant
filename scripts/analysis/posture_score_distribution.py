"""field_test_1의 확정된 반복에 자세 점수(src/posture_score.py)를 적용해 세션별 점수 분포와 worst_item을 낸다. 카메라·화면 연결 없음.

실행(저장소 루트에서): python -m scripts.analysis.posture_score_distribution [--per-rep]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.analysis import replay_flags  # noqa: E402
from src.posture_score import ITEM_DEPTH, ITEM_TORSO_SHIN, score_posture  # noqa: E402

SESSIONS = ("1", "2", "3", "4", "5", "9")


def scored_reps(session: str) -> list[dict]:
    result = replay_flags.replay(replay_flags.load_fixture(session), replay_flags.PRESETS["off"])
    rows = []
    for r in result.results:
        if not r.counted:
            continue
        s = score_posture(r.min_knee_angle, r.torso_signed_at_bottom, r.shin_signed_at_bottom)
        rows.append({"session": session, "min_knee": r.min_knee_angle, "ts": s.measures[ITEM_TORSO_SHIN], "score": s})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-rep", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("| 세션 | 반복 | 최저 무릎각 중앙값(범위) | torso_shin 중앙값(범위) | depth 상태 | torso_shin 상태 | 총점 중앙값 (최소~최대) | worst_item |")
    print("|---|---|---|---|---|---|---|---|")
    for session in SESSIONS:
        reps = scored_reps(session)
        if not reps:
            continue
        knees = [r["min_knee"] for r in reps]
        ts = [r["ts"] for r in reps if r["ts"] is not None]
        totals = [r["score"].total_score for r in reps]
        st_d = Counter(r["score"].item_status[ITEM_DEPTH] for r in reps)
        st_t = Counter(r["score"].item_status[ITEM_TORSO_SHIN] for r in reps)
        worst = Counter(r["score"].worst_item or "-" for r in reps)
        fmt = lambda c: ", ".join(f"{k} {v}" for k, v in sorted(c.items()))
        print(
            f"| {session} | {len(reps)} | {statistics.median(knees):.0f}° ({min(knees):.0f}~{max(knees):.0f}) "
            f"| {statistics.median(ts):.0f}° ({min(ts):.0f}~{max(ts):.0f}) | {fmt(st_d)} | {fmt(st_t)} "
            f"| {statistics.median(totals):.0f} ({min(totals):.0f}~{max(totals):.0f}) | {fmt(worst)} |"
        )
        if args.per_rep:
            for r in reps:
                print(f"    rep knee {r['min_knee']:.1f} ts {r['ts']:.1f} -> {r['score'].total_score:.1f} {r['score'].worst_item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
