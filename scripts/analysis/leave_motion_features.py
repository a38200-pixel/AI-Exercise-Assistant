"""ML 조건을 뺐을 때 확정되는 반복 후보마다 "자리를 뜨는 동작"과 실제 스쿼트를 가를 특징을 계산해 비교한다. 카메라를 쓰지 않는다.

입력은 원본 로그(jsonl) 여러 개. 후보 = ML 조건 제거(other_max_ratio=2.0)로 재생했을 때 확정되는 반복.
특징(반복 구간 t_start~t_end의 프레임 기준):
  non_side   : landmark가 있는 프레임 중 측면 판정(view.is_side)이 아닌 비율
  yaw_range  : view.hip_yaw_deg 최대-최소 (도)
  hipx_shift : 실제 RepTracker의 hip_shift_norm = 잠근 다리 엉덩이 x(프레임 픽셀)의 최대-최소 / 반복 중 L 중앙값 (이 도구가 따로 계산하지 않는다)
  invalid    : landmark가 있는 프레임 중 전신 무효(full_body.valid=False) 비율
  missing    : RepTracker가 계산한 사람/자세 없음 비율(pose_missing_ratio)
  bbox_h     : YOLO bbox 높이 / 프레임 높이의 최대
  L_growth   : 구간 안 L(다리 길이) 최대 / 서 있을 때 L (사람이 카메라에 다가가면 커진다)
  hip_drop, seconds: 현재 확정 조건의 값
실행(저장소 루트에서): python -m scripts.analysis.leave_motion_features --log data/landmark_sequences/session_*.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ml_condition_replay as ml  # noqa: E402
import replay_flags as rf  # noqa: E402

FEATURES = ("non_side", "yaw_range", "hipx_shift", "invalid", "missing", "bbox_h", "L_growth", "hip_drop", "seconds")


def load_raw(path: Path):
    return [r for r in (json.loads(line) for line in path.open("r", encoding="utf-8") if line.strip()) if r.get("type") == "frame"]


def candidate_features(path: Path):
    payload = rf.load_log(path)
    result = ml.run(payload, ml.REMOVED)
    now = rf.replay(payload, rf.PRESETS["off"])  # 새 기본 설정(지금 확정되는가)
    frames = load_raw(path)
    rows = []
    previous_end = -1e9
    for r in result.results:
        if not r.counted:
            previous_end = max(previous_end, r.t_end)
            continue
        window = [f for f in frames if r.t_start <= f["t"] <= r.t_end]
        present = [f for f in window if f.get("person") and f.get("landmarks") is not None and f.get("geometry") is not None]
        base = [p for p in payload["frames"] if max(r.t_start - 1.0, previous_end) <= p["t"] <= r.t_start and p["present"] and p["leg_length"]]
        base_l = statistics.median(p["leg_length"] for p in base) if base else float("nan")
        yaw = [f["view"]["hip_yaw_deg"] for f in present if f.get("view") and f["view"].get("hip_yaw_deg") is not None]
        window_l = [p["leg_length"] for p in payload["frames"] if r.t_start <= p["t"] <= r.t_end and p["present"] and p["leg_length"]]
        height = [(f["yolo_bbox"][3] - f["yolo_bbox"][1]) / f["frame_size"][1] for f in window if f.get("yolo_bbox") and f.get("person")]
        n = max(1, len(present))
        rows.append({
            "log": path.stem[8:], "t": r.t_start,
            "non_side": sum(1 for f in present if not (f.get("view") or {}).get("is_side")) / n,
            "yaw_range": (max(yaw) - min(yaw)) if yaw else float("nan"),
            "hipx_shift": r.hip_shift_norm,  # 실제 RepTracker 값(반복 중 L 중앙값으로 정규화). 이전에는 이 도구가 따로 계산해 서 있을 때 L로 나눴다
            "invalid": sum(1 for f in present if not (f.get("full_body") or {}).get("valid")) / n,
            "missing": r.pose_missing_ratio, "bbox_h": max(height) if height else float("nan"),
            "L_growth": max(window_l) / base_l if window_l and base_l == base_l else float("nan"),
            "hip_drop": r.hip_drop_norm, "seconds": r.total_seconds,
            "counted_now": any(abs(x.t_start - r.t_start) < 0.3 and x.counted for x in now.results),
        })
        previous_end = r.t_end
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="+", type=Path, required=True)
    parser.add_argument("--nonsquat", nargs="*", default=["nonsquat_lunge", "nonsquat_chair", "nonsquat_walk"],
                        help="이 note가 들어간 로그는 실제 스쿼트가 아니다(비교 대상에서 따로 표시)")
    parser.add_argument("--artifact", nargs="*", default=[], help="'로그이름:시작초' 형태로 지정한 후보는 세트 후 동작으로 따로 표시")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    artifacts = {(a.split(":")[0], round(float(a.split(":")[1]), 1)) for a in args.artifact}
    all_rows = []
    for path in args.log:
        first = json.loads(path.open("r", encoding="utf-8").readline())
        note = (first.get("metadata") or {}).get("note") or ""
        if "oblique" in path.name or "front" in path.name:
            continue
        for row in candidate_features(path):
            row["note"] = note
            row["kind"] = "세트후" if (row["log"], round(row["t"], 1)) in artifacts else ("비스쿼트" if any(n in note for n in args.nonsquat) else "스쿼트")
            all_rows.append(row)
    print("| 로그 | 시작초 | 구분 | 지금 확정 | " + " | ".join(FEATURES) + " |")
    print("|---|---|---|---|" + "---|" * len(FEATURES))
    for row in all_rows:
        print(f"| {row['log']} | {row['t']:.1f} | {row['kind']} | {'O' if row['counted_now'] else 'X'} | " + " | ".join(f"{row[k]:.2f}" for k in FEATURES) + " |")
    print("\n## 분포")
    print("| 특징 | 스쿼트 min / 중앙값 / 최대 | 비스쿼트 후보 | 세트 후 동작 후보 |")
    print("|---|---|---|---|")
    groups = {kind: [r for r in all_rows if r["kind"] == kind] for kind in ("스쿼트", "비스쿼트", "세트후")}
    for k in FEATURES:
        v = sorted(r[k] for r in groups["스쿼트"] if r[k] == r[k])
        cells = []
        for kind in ("비스쿼트", "세트후"):
            w = [r[k] for r in groups[kind] if r[k] == r[k]]
            cells.append(", ".join(f"{x:.2f}" for x in sorted(w)) or "-")
        print(f"| {k} | {v[0]:.2f} / {statistics.median(v):.2f} / {v[-1]:.2f} | {cells[0]} | {cells[1]} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
