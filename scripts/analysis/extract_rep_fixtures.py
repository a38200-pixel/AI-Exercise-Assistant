"""실측 로그에서 RepTracker 회귀 테스트용 최소 시퀀스를 뽑아 tests/fixtures/rep_sessions/에 저장한다.

로그 원본(data/landmark_sequences/)은 저장소에 넣지 않는다. fixture에는 RepTracker가 쓰는 값만 남긴다:
프레임 시각, 평활 무릎각, 잠금 상태(다리·방향), 부호 있는 몸통·정강이각, stable 라벨, 판정용 좌표(엉덩이·뒤꿈치 y,
다리 길이, 양발 간격). **얼굴 landmark와 전체 landmark는 저장하지 않는다.**

실행(저장소 루트에서):
    python scripts/analysis/extract_rep_fixtures.py

로그의 잠금 상태는 로깅 당시의 임시 정책(서 있는 첫 프레임부터 잠금)으로 만들어진 값이다. 그래서 이 fixture는
RepTracker의 상태기계와 확정 조건을 검증하는 데 쓰고, 새 BodyLock 정책(측면 0.5초 연속)은 합성 테스트로 검증한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from field_test_1_lib import match_sessions  # noqa: E402
from src.rep_tracker import measure_frame  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "landmark_sequences"
OUT_DIR = ROOT / "tests" / "fixtures" / "rep_sessions"

# 실제 횟수(사용자 기록). 세션 9는 사용자가 횟수를 확신하지 못해 횟수 검증에서 제외한다(actual=None).
# 8b(의자)·8c(런지)·8a(걷기)는 스쿼트가 아니다(8b는 알려진 한계로 센다).
# 6(사선)·7(정면)은 실제 5회씩이지만 측면이 아니라 새 정책에서는 잠금이 걸리지 않아 세지 않는다(안내 문구 테스트용).
SESSIONS = {"1": 10, "2": 8, "3": 8, "4": 8, "5": 8, "6": 5, "7": 5, "8a": 0, "8b": None, "8c": 0, "9": None}
# side_now/valid/facing_now/leg_now: 새 BodyLock 정책(BodyLockPolicy)을 로그의 신호로 다시 재생하기 위한 값.
# lock_*는 로깅 당시의 옛 임시 정책이 남긴 값이라 참고용이다.
COLUMNS = [
    "t", "present", "knee_smoothed", "locked", "lock_leg", "lock_facing", "torso_signed", "shin_signed",
    "label", "hip_y", "heel_y", "leg_length", "ankle_gap", "side_now", "valid", "facing_now", "leg_now",
]


def _round(value, digits=4):
    return None if value is None else round(float(value), digits)


def _landmark_tuples(rows):
    """로그의 landmark 행을 (x, y, z, visibility)로 바꾼다. 얼굴 행(저장 안 됨)은 0으로 채운다(판정에 쓰지 않는다)."""
    return [tuple(0.0 if v is None else v for v in row[:3]) + (1.0 if row[3] is None else row[3],) for row in rows]


def extract(path: Path) -> list[list]:
    rows: list[list] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("type") != "frame":
                continue
            geometry, lock, labels = record.get("geometry"), record.get("lock") or {}, record.get("labels") or {}
            if not record.get("person") or record.get("landmarks") is None or geometry is None:
                rows.append(
                    [_round(record["t"]), 0, None, 0, None, None, None, None, labels.get("stable"), None, None, None, None,
                     None, None, None, None]
                )
                continue
            measures = measure_frame(_landmark_tuples(record["landmarks"]), record["crop_bbox"], geometry["leg"])
            rows.append(
                [
                    _round(record["t"]), 1, _round(geometry["knee_smoothed"]), int(bool(lock.get("locked"))),
                    lock.get("leg"), lock.get("facing"), _round(geometry["torso_signed"]), _round(geometry["shin_signed"]),
                    labels.get("stable"), _round(measures.hip_y, 2), _round(measures.heel_y, 2),
                    _round(measures.leg_length, 2), _round(measures.ankle_gap, 2),
                    int(bool((record.get("view") or {}).get("is_side"))), int(bool((record.get("full_body") or {}).get("valid"))),
                    geometry.get("facing_now"), geometry.get("leg_now"),
                ]
            )
    return rows


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for info in match_sessions(DATA_DIR):
        if info.plan_id not in SESSIONS:
            continue
        rows = extract(info.path)
        payload = {
            "session": info.plan_id,
            "source": info.path.name,
            "note": info.metadata.get("note"),
            "actual_squats": SESSIONS[info.plan_id],
            "columns": COLUMNS,
            "rows": rows,
        }
        out = OUT_DIR / f"session_{info.plan_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{out.name}: {len(rows)} frames, {out.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
