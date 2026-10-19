"""원본 로그의 landmark로 기하 추적(GeometryTracker)과 RepTracker를 처음부터 다시 돌려, 수정 전·후 동작을 비교한다. 카메라를 쓰지 않는다.

fixture 재생(replay_flags)은 로그에 기록된 잠금 시점의 값을 쓰지만, 이 스크립트는 landmark에서 기하·잠금·평활을 다시 계산하므로
잠금 다리 선택과 갱신 규칙의 변경을 검증할 수 있다. 얼굴 landmark(저장되지 않음)는 판정에 쓰지 않으므로 0으로 채운다.

수정 전 동작은 GeometryTracker(leg_switch_margin=0, other_leg_refresh=False)와 RepTracker(standing_max_gap_seconds=0)로 재현한다.

실행(저장소 루트에서): python -m scripts.analysis.geometry_replay --log data/landmark_sequences/session_*.jsonl [--window 17.5 22.7]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.geometry_tracker import GeometryTracker  # noqa: E402
from src.rep_tracker import STATE_WAITING_LOCK, RepTracker, track_primary_person  # noqa: E402

OLD = {"tracker": {"leg_switch_margin": 0.0, "other_leg_refresh": False}, "rep": {"standing_max_gap_seconds": 0.0}}
NEW = {"tracker": {}, "rep": {}}


def landmark_rows(rows: list[list[float | None]]) -> list[tuple[float, float, float, float]]:
    return [tuple(0.0 if v is None else v for v in row[:3]) + (1.0 if row[3] is None else row[3],) for row in rows]


def read_frames(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    frames, footer = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["type"] == "frame":
            frames.append(record)
        elif record["type"] == "footer":
            footer = record
    return frames, footer


def replay(frames: list[dict[str, Any]], config: dict[str, dict], window: tuple[float, float] | None = None) -> dict[str, Any]:
    tracker = GeometryTracker(**config["tracker"])
    rep_tracker = RepTracker(**config["rep"])
    counted, rejected, leg_changes, waiting_in_window, invalid_frames = [], 0, 0, 0.0, 0
    previous_t = None
    previous_leg = None
    for frame in frames:
        t = frame["t"]
        person = None
        if frame.get("person") and frame.get("landmarks") is not None:
            person = {
                "bbox": frame["yolo_bbox"],
                "padded_bbox": frame["crop_bbox"],
                "landmarks": landmark_rows(frame["landmarks"]),
                "world_landmarks": None,
            }
        tracked, lock, rep_frame = track_primary_person(tracker, person, tuple(frame["frame_size"]), t)
        if lock.locked and lock.leg is not None:
            if previous_leg is not None and lock.leg != previous_leg:
                leg_changes += 1
            previous_leg = lock.leg
        elif not lock.locked:
            previous_leg = None
        result = rep_tracker.update(rep_frame, (frame.get("labels") or {}).get("stable"))
        if result is not None:
            if result.counted:
                counted.append((round(result.t_start, 2), round(result.t_end, 2)))
            else:
                rejected += 1
        dt = 0.0 if previous_t is None else t - previous_t
        previous_t = t
        if window and window[0] <= t < window[1] and rep_tracker.state == STATE_WAITING_LOCK and frame.get("person"):
            waiting_in_window += dt
        if tracked is not None and not tracked.geometry.full_body.valid and tracked.geometry_now.full_body.valid:
            invalid_frames += 1  # 잠근(또는 선택된) 다리는 무효인데 이 프레임의 다른 다리는 유효한 프레임
    return {
        "counted": counted,
        "rejected": rejected,
        "leg_changes": leg_changes,
        "waiting_in_window": waiting_in_window,
        "locked_leg_invalid_frames": invalid_frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="+", type=Path, required=True)
    parser.add_argument("--window", nargs=2, type=float, help="WAITING_LOCK 시간을 따로 잴 구간(초)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    window = tuple(args.window) if args.window else None
    print("| 로그 | 실제 | 센 횟수 전→후 | 잠금 다리 바뀜 전→후 | 잠근 다리 무효·다른 다리 유효 프레임 전→후 | 구간 WAITING_LOCK(초) 전→후 | 탈락 후보 전→후 |")
    print("|---|---|---|---|---|---|---|")
    for path in args.log:
        frames, footer = read_frames(path)
        old, new = replay(frames, OLD, window), replay(frames, NEW, window)
        actual = "-" if footer is None else footer.get("actual_reps")
        print(
            f"| {path.stem[8:]} | {actual} | {len(old['counted'])}→{len(new['counted'])} | {old['leg_changes']}→{new['leg_changes']} "
            f"| {old['locked_leg_invalid_frames']}→{new['locked_leg_invalid_frames']} | {old['waiting_in_window']:.1f}→{new['waiting_in_window']:.1f} "
            f"| {old['rejected']}→{new['rejected']} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
