"""발 간격 조건(ankle_gap / leg_length <= REP_MAX_ANKLE_GAP)의 입력값을 후보마다 풀어서 본다. 카메라를 쓰지 않는다. 제품 코드는 바꾸지 않는다.

기준값은 RepTracker와 같은 방식으로 다시 구한다: 내려가기 직전 REP_BASELINE_SECONDS(1초) 안에서 서 있던(무릎각 STANDING 이상) 프레임의
|왼쪽 발목 x - 오른쪽 발목 x|(프레임 픽셀) 중앙값 = 발 간격, |엉덩이-무릎| + |무릎-발목|(잠근 다리, 프레임 픽셀) 중앙값 = L.
재구성한 비율이 RepTracker가 기록한 ankle_gap_norm과 얼마나 다른지도 함께 출력한다(검증). 최저점 비율은 실제 RepTracker의 ankle_gap_bottom_norm을 옆에 함께 보인다
(판정에 쓰이는 값은 항상 RepTracker의 값이고, 이 도구의 재구성은 픽셀 값을 보여 주기 위한 설명용이다).

실행(저장소 루트에서):
    python -m scripts.analysis.ankle_gap_analysis --fixtures --log data/landmark_sequences/session_X.jsonl [--trace 9 16]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import replay_flags as rf  # noqa: E402
from config import settings  # noqa: E402


def median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else float("nan")


def candidates(payload):
    result = rf.replay(payload, rf.PRESETS["off"])
    frames = payload["frames"]
    rows = []
    previous_end = -1e9
    for r in result.results:
        window = [
            f for f in frames
            if max(r.t_start - settings.REP_BASELINE_SECONDS, previous_end) <= f["t"] <= r.t_start  # 이전 반복이 끝난 뒤의 서 있는 프레임만
            and f["present"] and f["hip_y"] is not None and (f["knee_smoothed"] or 0.0) >= settings.STANDING_KNEE_ANGLE
        ]
        bottom = [f for f in frames if abs(f["t"] - r.t_bottom) <= 0.25 and f["present"] and f["leg_length"] is not None] if r.t_bottom == r.t_bottom else []
        previous_end = r.t_end
        gap, length = median([f["ankle_gap"] for f in window]), median([f["leg_length"] for f in window])
        inside = [f for f in frames if r.t_start <= f["t"] <= r.t_end and f["present"] and f["ankle_gap"] is not None]
        gap_bottom = median([f["ankle_gap"] for f in bottom])
        rows.append({
            "t": r.t_start, "counted": r.counted, "reasons": ",".join(r.reasons) or "-", "gap_px": gap, "L_px": length,
            "ratio": gap / length if length == length and length else float("nan"), "recorded": r.ankle_gap_norm,
            "L_bottom": median([f["leg_length"] for f in bottom]), "n": len(window), "hip_drop": r.hip_drop_norm,
            "bottom_recorded": r.ankle_gap_bottom_norm, "gap_bottom_px": gap_bottom, "gap_max_px": max((f["ankle_gap"] for f in inside), default=float("nan")),
        })
    return rows


def print_table(name, rows):
    print(f"\n### {name}")
    print("| 시작초 | 확정 | 사유 | 발 간격 px | L px | 비율(재구성) | 비율(기록) | 최저점 L px | 최저점 L / 서 있을 때 L | 기준 프레임 | 최저점 발 간격 px (비율=L 대비) | 반복 중 최대 발 간격 px (비율) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        shrink = r["L_bottom"] / r["L_px"] if r["L_px"] == r["L_px"] and r["L_px"] else float("nan")
        print(f"| {r['t']:.1f} | {'O' if r['counted'] else 'X'} | {r['reasons']} | {r['gap_px']:.0f} | {r['L_px']:.0f} | {r['ratio']:.3f} | {r['recorded']:.3f} | {r['L_bottom']:.0f} | {shrink:.2f} | {r['n']} | {r['gap_bottom_px']:.0f} ({r['gap_bottom_px'] / r['L_px']:.2f}; 실제 RepTracker {r['bottom_recorded']:.2f}) | {r['gap_max_px']:.0f} ({r['gap_max_px'] / r['L_px']:.2f}) |")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fixtures", action="store_true", help="1차 fixture(1~5, 8a, 8c, c10, c10_fast) 포함")
    parser.add_argument("--log", nargs="*", type=Path, default=[])
    parser.add_argument("--trace", nargs=2, type=float, help="마지막 --log 의 구간(초) 시간 경과를 0.25초 간격으로 출력")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    payloads = [rf.load_fixture(s) for s in ("1", "2", "3", "4", "5", "8a", "8c", "c10", "c10_fast")] if args.fixtures else []
    payloads += [rf.load_log(p) for p in args.log]
    for payload in payloads:
        print_table(f"{payload['session']} {payload.get('note') or ''}", candidates(payload))
    if args.trace and payloads:
        t0, t1 = args.trace
        print(f"\n### 시간 경과 {t0:g}~{t1:g}초 ({payloads[-1]['session']})")
        print("| t | 무릎각 | 발 간격 px | L px | 잠금 |")
        print("|---|---|---|---|---|")
        last = -9.0
        for f in payloads[-1]["frames"]:
            if t0 <= f["t"] <= t1 and f["t"] - last >= 0.25:
                last = f["t"]
                knee = "-" if f["knee_smoothed"] is None else f"{f['knee_smoothed']:.0f}"
                gap = "-" if f["ankle_gap"] is None else f"{f['ankle_gap']:.0f}"
                length = "-" if f["leg_length"] is None else f"{f['leg_length']:.0f}"
                print(f"| {f['t']:.2f} | {knee} | {gap} | {length} | {f['locked']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
