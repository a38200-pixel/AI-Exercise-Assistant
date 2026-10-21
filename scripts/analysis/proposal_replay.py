"""P01 2차 로그 뒤 제안된 변경의 조합을 전체 로그에 재생해 현재와 비교한다. 카메라를 쓰지 않는다. 제품 코드는 바꾸지 않는다.

--counts: 확정 조건 조합 재생
    이전 기본   : ML 상한 0.40, 새 조건 없음(변경 전 기본 설정)
    ML제거      : other_exercise 비율 조건 제거(비율은 기록만)
    +발간격     : + 최저점 발 간격/L <= --ankle-bottom (기존 서 있을 때 <= 0.25는 유지)
    조합(새 기본): + 반복 중 엉덩이 x 이동/(반복 중 L 중앙값) <= --hip-shift
  각 변형을 실제 RepTracker의 설정(other_max_ratio, max_ankle_gap_bottom, max_hip_shift)으로 재생한다. 이 도구는 판정을 따로 계산하지 않는다.
--signed: torso_shin을 |몸통각-정강이각| 대신 max(몸통각-정강이각, 0)으로 바꾼 점수 재생(기준 25/35는 그대로).
    posture_score.torso_shin_difference를 메모리에서만 바꿔 같은 score_posture를 다시 부른다.

실행(저장소 루트에서): python -m scripts.analysis.proposal_replay --counts --signed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ml_condition_replay as ml  # noqa: E402
import replay_flags as rf  # noqa: E402
from src import posture_score as ps  # noqa: E402

DATA = ROOT / "data" / "landmark_sequences"


def short(path: Path) -> str:
    return path.stem[len("session_"):]


def label(payload, path: Path) -> str:
    note = payload.get("note") or ""
    return short(path) + (f" ({note})" if note else "")


def counts(paths, ankle_bottom, hip_shift):
    """각 변형을 **실제 RepTracker의 설정**으로 재생한다(조건을 이 도구가 따로 계산하지 않는다)."""
    print()
    print(f"## 확정 조건 조합 재생 (최저점 발 간격/L <= {ankle_bottom:g}, 엉덩이 x 이동/반복 중 L 중앙값 <= {hip_shift:g})")
    variants = (
        ("이전 기본", dict(other_max=0.40)),
        ("ML제거", dict(other_max=None)),
        ("+발간격", dict(other_max=None, max_ankle_gap_bottom=ankle_bottom)),
        ("조합(새 기본)", dict(other_max=None, max_ankle_gap_bottom=ankle_bottom, max_hip_shift=hip_shift)),
    )
    print("| 로그 | 실제 | " + " | ".join(name for name, _ in variants) + " | 새 기본에서 걸러진 후보 |")
    print("|---|---|" + "---|" * (len(variants) + 1))
    for path in paths:
        payload = rf.load_log(path)
        runs = [ml.run(payload, **options) for _, options in variants]
        removed = [
            f"{r.t_start:.1f}초 {'/'.join(r.reasons)}"
            for r, before in zip(runs[-1].results, runs[1].results)
            if before.counted and not r.counted
        ]
        actual = "?" if payload.get("actual_squats") is None else payload["actual_squats"]
        print(f"| {label(payload, path)} | {actual} | " + " | ".join(str(r.counted) for r in runs) + f" | {'; '.join(removed) or '-'} |")


def signed_difference(torso, shin):
    if torso is None or shin is None or torso != torso or shin != shin:
        return None
    return max(float(torso) - float(shin), 0.0)


def signed(paths):
    print("\n## torso_shin 부호 있는 차이 재생 (현재 설정으로 확정된 반복, 기준 25/35 그대로)")
    original = ps.torso_shin_difference
    print("| 로그 | 반복 | 판정 변화 반복 | 점수 변화 반복 | 측정값 중앙값: \\|차이\\| → 부호 있는 값 |")
    print("|---|---|---|---|---|")
    details = []
    for path in paths:
        payload = rf.load_log(path)
        res = rf.replay(payload)
        reps = [r for r in res.results if r.counted]
        if not reps:
            continue
        changed_status = changed_score = 0
        old_m, new_m = [], []
        for r in reps:
            old = ps.score_posture(r.min_knee_angle, r.torso_signed_at_bottom, r.shin_signed_at_bottom)
            ps.torso_shin_difference = signed_difference
            try:
                new = ps.score_posture(r.min_knee_angle, r.torso_signed_at_bottom, r.shin_signed_at_bottom)
            finally:
                ps.torso_shin_difference = original
            if old.measures[ps.ITEM_TORSO_SHIN] is not None:
                old_m.append(old.measures[ps.ITEM_TORSO_SHIN])
                new_m.append(new.measures[ps.ITEM_TORSO_SHIN])
            status_changed = old.item_status != new.item_status
            score_changed = (old.total_score is None) != (new.total_score is None) or (
                old.total_score is not None and abs(old.total_score - new.total_score) > 0.05
            )
            changed_status += status_changed
            changed_score += score_changed
            if status_changed or score_changed:
                details.append((short(path), r.t_start, old, new, r))
        med = lambda v: sorted(v)[len(v) // 2] if v else float("nan")  # noqa: E731
        print(f"| {label(payload, path)} | {len(reps)} | {changed_status} | {changed_score} | {med(old_m):.1f} → {med(new_m):.1f} |")
    print("\n### 판정 또는 점수가 바뀐 반복")
    if not details:
        print("(없음)")
        return
    print("| 로그 | 시작초 | 최저 무릎각 | 몸통-정강이(부호) | \\|차이\\| → 새 값 | 판정(전 → 후) | 총점(전 → 후) |")
    print("|---|---|---|---|---|---|---|")
    for name, t, old, new, r in details:
        diff = r.torso_signed_at_bottom - r.shin_signed_at_bottom
        print(
            f"| {name} | {t:.1f} | {r.min_knee_angle:.0f}° | {diff:+.1f} | {old.measures[ps.ITEM_TORSO_SHIN]:.1f} → {new.measures[ps.ITEM_TORSO_SHIN]:.1f} "
            f"| {old.item_status[ps.ITEM_TORSO_SHIN]} → {new.item_status[ps.ITEM_TORSO_SHIN]} | {old.total_score:.0f} → {new.total_score:.0f} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--counts", action="store_true")
    parser.add_argument("--signed", action="store_true")
    parser.add_argument("--ankle-bottom", type=float, default=0.40)
    parser.add_argument("--hip-shift", type=float, default=0.70)
    parser.add_argument("--log", nargs="*", type=Path, help="기본: data/landmark_sequences/session_*.jsonl 전부")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    paths = args.log or sorted(DATA.glob("session_*.jsonl"))
    if args.counts:
        counts(paths, args.ankle_bottom, args.hip_shift)
    if args.signed:
        signed(paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
