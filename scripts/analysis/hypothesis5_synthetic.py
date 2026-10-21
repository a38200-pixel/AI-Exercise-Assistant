"""가설 5(평활이 연속 반복의 봉우리를 160° 아래로 깎는다) 합성 검증.

휴지 없는 연속 스쿼트의 무릎각을 코사인 파형으로 만들고(봉우리 PEAK, 바닥 BOTTOM), 현재 One Euro 파라미터로 평활한 뒤
봉우리 최대값이 얼마나 깎이는지와 STANDING 복귀 기준(160°)에 닿는지 표로 보고한다. 카메라·로그를 쓰지 않는다.

실행: python -m scripts.analysis.hypothesis5_synthetic [--markdown]
"""

from __future__ import annotations

import argparse
import math
import sys

from config import settings
from src.pose_geometry import OneEuroFilter

FPS_VALUES = (8, 15, 30)
PEAK_VALUES = (162.0, 165.0, 170.0)
PERIOD_VALUES = (2.5, 2.0, 1.5)  # 반복 1회 주기(초): 느린 연속 / 보통 연속 / 빠르게
BOTTOM = 85.0
REPS = 10


def knee_wave(
    peak: float, bottom: float, period: float, fps: int, reps: int, phase_samples: float = 0.0
) -> list[tuple[float, float]]:
    """(t, 무릎각). phase_samples=0이면 샘플이 봉우리 정점에 정확히 떨어지고, 0.5면 정점이 두 샘플 사이(최악 위상)다."""
    n = int(round(period * reps * fps)) + 1
    mid = (peak + bottom) / 2.0
    amp = (peak - bottom) / 2.0
    return [(i / fps, mid + amp * math.cos(2.0 * math.pi * (i + phase_samples) / fps / period)) for i in range(n)]


def smoothed_tops(series, smoother) -> tuple[list[float], list[float]]:
    """봉우리마다(처음·끝 제외) 원본과 평활값의 최대."""
    raw_tops, smooth_tops = [], []
    values = [(t, v, smoother(v, t)) for t, v in series]
    # 봉우리 구간: 원본이 중간값보다 큰 연속 구간
    mid = (max(v for _, v, _ in values) + min(v for _, v, _ in values)) / 2.0
    run: list[tuple[float, float, float]] = []
    for item in values + [(0.0, mid - 1, 0.0)]:
        if item[1] > mid:
            run.append(item)
        elif run:
            raw_tops.append(max(v for _, v, _ in run))
            smooth_tops.append(max(s for _, _, s in run))
            run = []
    return raw_tops[1:-1], smooth_tops[1:-1]  # 처음과 끝 봉우리는 잘려 있으므로 제외


def count_reps(series, smoother, standing: float, descent: float) -> int:
    """무릎각만으로 한 히스테리시스 반복 수(RepTracker의 길이·엉덩이 조건은 제외한 순수 각도 경계)."""
    state, count = "wait", 0
    for t, v in series:
        s = smoother(v, t)
        if state == "wait" and s >= standing:
            state = "stand"
        elif state == "stand" and s < descent:
            state = "rep"
        elif state == "rep" and s >= standing:
            state, count = "stand", count + 1
    return count


def run() -> list[dict]:
    rows = []
    for period in PERIOD_VALUES:
        for fps in FPS_VALUES:
            for peak in PEAK_VALUES:
                tops_all: list[float] = []
                counted = []
                for phase in (0.0, 0.5):  # 샘플 위상: 정점 위 / 정점 사이(최악)
                    series = knee_wave(peak, BOTTOM, period, fps, REPS, phase)
                    _, tops = smoothed_tops(series, OneEuroFilter())
                    tops_all.extend(tops)
                    counted.append(
                        count_reps(series, OneEuroFilter(), settings.STANDING_KNEE_ANGLE, settings.REP_DESCENT_KNEE_ANGLE)
                    )
                rows.append(
                    {
                        "period": period,
                        "fps": fps,
                        "peak": peak,
                        "top_min": min(tops_all),
                        "cut": peak - min(tops_all),
                        "below_160": sum(1 for v in tops_all if v < settings.STANDING_KNEE_ANGLE),
                        "tops": len(tops_all),
                        "counted": min(counted),
                    }
                )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", action="store_true", help="마크다운 표로 출력")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = run()
    head = ("주기(s)", "FPS", "봉우리(°)", "평활 봉우리 최소(°)", "최대 깎임(°)", "160° 미달 봉우리", "각도만으로 센 반복(최소)")
    print(
        f"One Euro min_cutoff={settings.ONE_EURO_MIN_CUTOFF} beta={settings.ONE_EURO_BETA} "
        f"d_cutoff={settings.ONE_EURO_D_CUTOFF}, 바닥 {BOTTOM:.0f}°, 연속 {REPS}회, "
        f"기준 {settings.STANDING_KNEE_ANGLE:.0f}°/{settings.REP_DESCENT_KNEE_ANGLE:.0f}°, "
        "샘플 위상 2종(정점 위/정점 사이) 합산"
    )
    if args.markdown:
        print("| " + " | ".join(head) + " |")
        print("|" + "---|" * len(head))
    for r in rows:
        cells = (
            f"{r['period']:.1f}", str(r["fps"]), f"{r['peak']:.0f}", f"{r['top_min']:.1f}",
            f"{r['cut']:.1f}", f"{r['below_160']}/{r['tops']}", f"{r['counted']}/{REPS}",
        )
        print(("| " + " | ".join(cells) + " |") if args.markdown else "  ".join(f"{c:>10}" for c in cells))


if __name__ == "__main__":
    main()
