"""other_exercise(ML 라벨 비율) 확정 조건을 빼면 센 횟수가 어떻게 바뀌는지 재생해 비교한다. 카메라를 쓰지 않는다. 제품 코드는 바꾸지 않는다.

현재(기본 other_max_ratio=0.40)와 조건 제거(상한 2.0 = 비율이 항상 통과)를 같은 입력에 재생한다.
입력: tests/fixtures/rep_sessions/session_*.json 전부 + --log 로 준 원본 로그.

실행(저장소 루트에서):
    python -m scripts.analysis.ml_condition_replay --log data/landmark_sequences/session_20261019_*.jsonl
"""

from __future__ import annotations

import argparse
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import replay_flags as rf  # noqa: E402
from src.rep_tracker import RepTracker  # noqa: E402

REMOVED = 2.0  # 비율은 0~1이라 2.0이면 조건이 절대 걸리지 않는다


def run(payload, other_max, **tracker_options):
    """실제 RepTracker에 설정만 바꿔 재생한다. 새 조건(최저점 발 간격, 엉덩이 이동)은 따로 주지 않으면 **꺼진** 상태다.

    이 도구가 처음 만들어질 때의 비교(ML 조건 0.40 대 제거, 새 조건 없음)를 그대로 재현하려는 것이다. 새 기본 동작과 비교하려면
    run(payload, None, max_ankle_gap_bottom=0.40, max_hip_shift=0.70) 또는 replay_flags.replay를 그대로 쓴다."""
    tracker_options = {"max_ankle_gap_bottom": None, "max_hip_shift": None, **tracker_options}
    original = rf.RepTracker
    rf.RepTracker = partial(RepTracker, other_max_ratio=other_max, **tracker_options)
    try:
        return rf.replay(payload, rf.PRESETS["off"])
    finally:
        rf.RepTracker = original


def label_of(payload) -> str:
    session = str(payload["session"])
    short = session[len("session_"):] if session.startswith("session_") else session
    note = payload.get("note") or ""
    return short + (f" ({note})" if note else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="*", type=Path, default=[])
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    payloads = [rf.load_fixture(p.stem[len("session_"):]) for p in sorted(rf.FIXTURES.glob("session_*.json"))]
    payloads += [rf.load_log(p) for p in args.log]
    print("| 세션 | 실제 | 현재 | ML 조건 제거 | 변화 | 새로 확정된 후보(시작초: 비율) | 제거 후에도 탈락한 사유 |")
    print("|---|---|---|---|---|---|---|")
    for payload in payloads:
        now, off = run(payload, 0.40), run(payload, REMOVED)
        gained = [r for r in off.results if r.counted and not any(abs(r.t_start - n.t_start) < 0.3 and n.counted for n in now.results)]
        lost = [n for n in now.results if n.counted and not any(abs(r.t_start - n.t_start) < 0.3 and r.counted for r in off.results)]
        actual = "?" if payload.get("actual_squats") is None else payload["actual_squats"]
        newly = ", ".join(f"{r.t_start:.1f}s: {r.other_exercise_ratio:.2f}" for r in gained) or "-"
        rest = ", ".join(f"{k}={v}" for k, v in sorted(off.rejected.items())) or "-"
        change = f"+{off.counted - now.counted}" if off.counted != now.counted else "0"
        if lost:
            change += f" (사라진 확정 {len(lost)})"
        print(f"| {label_of(payload)} | {actual} | {now.counted} | {off.counted} | {change} | {newly} | {rest} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
