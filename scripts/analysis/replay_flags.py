"""로그·fixture의 신호를 기본 설정의 BodyLockPolicy와 RepTracker에 다시 넣어 반복 수를 재생한다. 카메라를 쓰지 않는다. 제품 코드는 바꾸지 않는다.

(모듈 이름은 이전의 "대응안 플래그 재생 도구"에서 왔다. 기본 꺼짐 플래그 4개는 2026-10-20에 제거되어 지금은 기본 설정 재생과 저FPS 재생만 한다.
이름을 바꾸지 않은 것은 이 모듈을 쓰는 스크립트·테스트·문서가 많기 때문이다.)

입력(둘 중 하나):
- 기본: tests/fixtures/rep_sessions/session_*.json (field_test_1에서 뽑은 판정용 값. 평활 전 무릎각 knee_raw 포함)
- --log <session_*.jsonl>...: 로깅(--log-sequence)으로 저장한 원본 로그.

재생은 fixture/로그의 프레임별 신호(평활 무릎각, 원본 무릎각, 측면 판정, 전신 유효, 판정용 좌표, stable 라벨)를 새
BodyLockPolicy와 RepTracker에 넣는 방식이다(tests/test_rep_tracker.py의 simulate와 같다). 잠금은 로그에 기록된 값이
아니라 정책이 다시 정한다. 이 접착 코드가 실제 파이프라인과 같은 판정을 내는지는 replay_fidelity_check.py와
tests/test_replay_matches_real_pipeline.py가 확인한다.

사용 예(저장소 루트에서):
    python -m scripts.analysis.replay_flags                          # fixture 세션 표(기본: 1~5, 7, 8a~8c)
    python -m scripts.analysis.replay_flags --markdown
    python -m scripts.analysis.replay_flags --log data/landmark_sequences/session_X.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings  # noqa: E402
from src.geometry_tracker import BodyLockPolicy  # noqa: E402
from src.pose_geometry import OneEuroFilter  # noqa: E402
from src.rep_tracker import RepFrame, RepMeasures, RepTracker  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "rep_sessions"
DEFAULT_SESSIONS = ("1", "2", "3", "4", "5", "7", "8a", "8b", "8c")


@dataclass
class Replay:
    session: str
    actual: int | None
    counted: int
    rejected: dict[str, int]
    counted_starts: list[float]
    lock_releases: int  # 세트 중간 포함, 잠금이 풀린 횟수
    merge_suspects: int
    frames: int
    results: list = None  # 반복마다의 RepResult(확정·탈락 모두)
    events: list = None  # RepTracker 진단 이벤트(rep_end, rep_merge_suspect)
    states: list = None  # 프레임마다 (시각, 업데이트 직후 RepTracker 상태). 구도 안내처럼 실시간 반복 상태가 필요한 재생에 쓴다


# ---------------------------------------------------------------- 입력


def load_fixture(session: str) -> dict[str, Any]:
    payload = json.loads((FIXTURES / f"session_{session}.json").read_text(encoding="utf-8"))
    payload["frames"] = [dict(zip(payload["columns"], row)) for row in payload["rows"]]
    return payload


def load_log(path: Path) -> dict[str, Any]:
    """원본 로그(jsonl)를 fixture와 같은 형태로 바꾼다. 실제 횟수는 footer(있다면)에서 읽는다."""
    from extract_rep_fixtures import COLUMNS, extract

    rows = extract(path)
    actual = None
    note = None
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("type") == "footer":
                actual = record.get("actual_reps")
                note = record.get("note")
    return {
        "session": path.stem,
        "source": path.name,
        "note": note,
        "actual_squats": actual,
        "columns": COLUMNS,
        "frames": [dict(zip(COLUMNS, row)) for row in rows],
    }


# ---------------------------------------------------------------- 재생


def decimate(frames: list[dict[str, Any]], fps: float) -> list[dict[str, Any]]:
    """프레임 솎아내기: 시각 격자(시작 + k/fps)마다 그 시각 이후 첫 프레임만 남긴다. 타임스탬프는 원본 그대로다."""
    if not frames:
        return []
    step = 1.0 / fps
    kept, next_time = [], frames[0]["t"]
    for frame in frames:
        if frame["t"] >= next_time - 1e-9:
            kept.append(frame)
            while next_time <= frame["t"] + 1e-9:
                next_time += step
    return kept


def replay(payload: dict[str, Any], *, fps: float | None = None) -> Replay:
    """fps를 주면 프레임을 그 속도로 솎아낸 뒤 **솎아낸 프레임만으로 무릎각을 다시 평활**하고(원본 무릎각 + 새 One Euro) 재생한다.
    솎아낸 프레임의 판정용 값(측면 판정, 좌표, 라벨)은 원본 그대로다. MediaPipe 추적 품질 저하는 재현하지 못한다."""
    frames = payload["frames"] if fps is None else decimate(payload["frames"], fps)
    smoother = OneEuroFilter() if fps is not None else None
    policy = BodyLockPolicy()
    tracker = RepTracker()
    results, merge_suspects, releases, events, states = [], 0, 0, [], []
    leg = facing = None
    for v in frames:
        t = v["t"]
        if not v["present"]:
            if policy.missing(t) == "release_missing":
                releases += 1
            if policy.missing_long_enough(t) and smoother is not None:
                smoother.reset()
            result = tracker.update(RepFrame.missing(t, locked=policy.locked), v["label"])
            states.append((t, tracker.state))
        else:
            knee = v["knee_smoothed"]
            if smoother is not None and knee is not None and v.get("knee_raw") is not None:
                knee = smoother(v["knee_raw"], t)  # 솎아낸 프레임만 보는 평활
            decision = policy.step(
                t,
                standing=knee is not None and knee >= settings.STANDING_KNEE_ANGLE,
                side_now=bool(v["side_now"]),
                lockable=bool(v["valid"]) and v["facing_now"] is not None,
            )
            if decision in ("acquire", "refresh"):
                leg, facing = v["leg_now"], v["facing_now"]
            if decision in ("release_view", "release_missing"):
                releases += 1
            hip_x = v.get("hip_x")  # 옛 fixture에는 없다(엉덩이 이동 조건은 NaN이면 건너뛴다)
            measures = (
                RepMeasures(v["hip_y"], v["heel_y"], v["leg_length"], v["ankle_gap"], float("nan") if hip_x is None else hip_x)
                if v["hip_y"] is not None
                else None
            )
            frame = RepFrame(
                t, True, knee, policy.locked, leg, facing, v["torso_signed"], v["shin_signed"], measures,
                side_now=bool(v["side_now"]), body_valid=bool(v["valid"]),
            )
            result = tracker.update(frame, v["label"])
            states.append((t, tracker.state))
        if result is not None:
            results.append(result)
        popped = tracker.pop_events()
        events.extend(popped)
        merge_suspects += sum(1 for e in popped if e["kind"] == "rep_merge_suspect")
    rejected: dict[str, int] = {}
    for r in results:
        if not r.counted:
            for reason in r.reasons:
                rejected[reason] = rejected.get(reason, 0) + 1
    return Replay(
        session=str(payload["session"]),
        actual=payload.get("actual_squats"),
        counted=sum(1 for r in results if r.counted),
        rejected=rejected,
        counted_starts=[round(r.t_start, 3) for r in results if r.counted],
        lock_releases=releases,
        merge_suspects=merge_suspects,
        frames=len(frames),
        results=results,
        events=events,
        states=states,
    )


# ---------------------------------------------------------------- 출력


def render(rows: list[list[str]], head: list[str], markdown: bool) -> str:
    if markdown:
        lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
        return "\n".join(lines)
    widths = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
    return "\n".join("  ".join(str(x).ljust(w) for x, w in zip(r, widths)) for r in [head, *rows])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="+", type=Path, help="원본 로그(jsonl). 없으면 fixture를 쓴다")
    parser.add_argument("--sessions", nargs="+", help="fixture 세션 id(기본: 1 2 3 4 5 7 8a 8b 8c)")
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    payloads = [load_log(p) for p in args.log] if args.log else [load_fixture(s) for s in (args.sessions or DEFAULT_SESSIONS)]
    head = ["세션", "센/실제", "탈락 사유", "잠금 해제", "합쳐짐 의심"]
    rows = []
    for p in payloads:
        r = replay(p)
        reasons = ", ".join(f"{k}={n}" for k, n in sorted(r.rejected.items())) or "-"
        actual = "?" if r.actual is None else str(r.actual)
        rows.append([r.session, f"{r.counted}/{actual}", reasons, str(r.lock_releases), str(r.merge_suspects)])
    print(render(rows, head, args.markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
