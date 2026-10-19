"""대응안 플래그 조합을 로그·fixture에 재생해 반복 수를 비교한다. 카메라를 쓰지 않는다. 제품 코드의 기본값은 바꾸지 않는다.

입력(둘 중 하나):
- 기본: tests/fixtures/rep_sessions/session_*.json (field_test_1에서 뽑은 판정용 값. 평활 전 무릎각 knee_raw 포함)
- --log <session_*.jsonl>...: 로깅(--log-sequence)으로 저장한 원본 로그. 재현 로그를 받으면 이쪽으로 바로 재생한다.

재생은 fixture/로그의 프레임별 신호(평활 무릎각, 원본 무릎각, 측면 판정, 전신 유효, 판정용 좌표, stable 라벨)를 새
BodyLockPolicy와 RepTracker에 넣는 방식이다(tests/test_rep_tracker.py의 simulate와 같다). 잠금은 로그에 기록된 값이
아니라 정책이 다시 정한다. 반복 경계용 light 신호는 원본 무릎각을 별도 One Euro로 다시 평활해 만든다.

사용 예(저장소 루트에서):
    python -m scripts.analysis.replay_flags --matrix                 # 프리셋 x 세션 표(기본: fixture 세션 1~5, 7, 8a~8c)
    python -m scripts.analysis.replay_flags --matrix --markdown
    python -m scripts.analysis.replay_flags --set-baseline --return-angle 155 --lock-grace 0.6 --boundary light
    python -m scripts.analysis.replay_flags --log data/landmark_sequences/session_X.jsonl --matrix
    python -m scripts.analysis.replay_flags --list-presets
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
from src.geometry_tracker import BOUNDARY_SIGNALS, BodyLockPolicy  # noqa: E402
from src.pose_geometry import OneEuroFilter  # noqa: E402
from src.rep_tracker import RepFrame, RepMeasures, RepTracker  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "rep_sessions"
DEFAULT_SESSIONS = ("1", "2", "3", "4", "5", "7", "8a", "8b", "8c")
START_TOLERANCE_SECONDS = 0.5  # 경계 신호를 바꾸면 반복 시작 시각이 프레임 몇 개만큼 달라질 수 있다


@dataclass(frozen=True)
class Flags:
    """대응안 플래그. 기본값은 모두 꺼짐(제품 기본 설정과 같다)."""

    set_baseline: bool = False
    return_angle: float | None = None
    boundary: str = "smoothed"
    lock_grace: float = 0.0

    def label(self) -> str:
        parts = []
        if self.set_baseline:
            parts.append("기준높이")
        if self.return_angle is not None:
            parts.append(f"복귀{self.return_angle:g}")
        if self.boundary != "smoothed":
            parts.append(f"경계={self.boundary}")
        if self.lock_grace:
            parts.append(f"유예{self.lock_grace:g}s")
        return "+".join(parts) or "꺼짐(기본)"


PRESETS: dict[str, Flags] = {
    "off": Flags(),
    "baseline": Flags(set_baseline=True),
    "return155": Flags(return_angle=155.0),
    "light": Flags(boundary="light"),
    "raw": Flags(boundary="raw"),
    "grace0.6": Flags(lock_grace=0.6),
    "all": Flags(set_baseline=True, return_angle=155.0, boundary="light", lock_grace=0.6),
}


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


def replay(payload: dict[str, Any], flags: Flags) -> Replay:
    policy = BodyLockPolicy(release_grace_seconds=flags.lock_grace)
    tracker = RepTracker(return_angle=flags.return_angle, set_baseline=flags.set_baseline)
    light = OneEuroFilter(
        min_cutoff=settings.REP_BOUNDARY_LIGHT_MIN_CUTOFF, beta=settings.ONE_EURO_BETA, d_cutoff=settings.ONE_EURO_D_CUTOFF
    )
    results, merge_suspects, releases = [], 0, 0
    leg = facing = None
    for v in payload["frames"]:
        t = v["t"]
        if not v["present"]:
            if policy.missing(t) == "release_missing":
                releases += 1
            if policy.missing_long_enough(t):
                light.reset()
            result = tracker.update(RepFrame.missing(t), v["label"])
        else:
            knee = v["knee_smoothed"]
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
            boundary = knee
            raw = v.get("knee_raw")
            # 전신 무효 프레임(knee가 None)은 평활도 갱신하지 않는다(GeometryTracker와 같다).
            if knee is not None and raw is not None:
                if flags.boundary == "raw":
                    boundary = raw
                elif flags.boundary == "light":
                    boundary = light(raw, t)
            measures = RepMeasures(v["hip_y"], v["heel_y"], v["leg_length"], v["ankle_gap"]) if v["hip_y"] is not None else None
            frame = RepFrame(
                t, True, knee, policy.locked, leg, facing, v["torso_signed"], v["shin_signed"], measures,
                side_now=bool(v["side_now"]), body_valid=bool(v["valid"]), knee_boundary=boundary,
            )
            result = tracker.update(frame, v["label"])
        if result is not None:
            results.append(result)
        merge_suspects += sum(1 for e in tracker.pop_events() if e["kind"] == "rep_merge_suspect")
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
        frames=len(payload["frames"]),
    )


# ---------------------------------------------------------------- 출력


def cell(r: Replay, baseline: Replay | None) -> str:
    actual = "?" if r.actual is None else str(r.actual)
    text = f"{r.counted}/{actual}"
    if baseline is not None and not same_reps(r.counted_starts, baseline.counted_starts):
        text += " Δ"  # 꺼짐(기본)과 센 반복이 다르다
    return text


def same_reps(a: list[float], b: list[float], tolerance: float = START_TOLERANCE_SECONDS) -> bool:
    """센 반복이 같은가: 개수가 같고 시작 시각이 프레임 한두 개(tolerance) 안에서 맞는다."""
    return len(a) == len(b) and all(abs(x - y) <= tolerance for x, y in zip(a, b))


def render(rows: list[list[str]], head: list[str], markdown: bool) -> str:
    if markdown:
        lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
        return "\n".join(lines)
    widths = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
    return "\n".join("  ".join(str(x).ljust(w) for x, w in zip(r, widths)) for r in [head, *rows])


def matrix(payloads: list[dict[str, Any]], presets: dict[str, Flags], markdown: bool) -> str:
    results = {name: [replay(p, flags) for p in payloads] for name, flags in presets.items()}
    base = results.get("off") or next(iter(results.values()))
    head = ["세션(노트)"] + list(presets)
    rows = []
    for i, p in enumerate(payloads):
        note = f"{p['session']}" + (f"({p['note']})" if p.get("note") else "")
        rows.append([note] + [cell(results[name][i], base[i] if name != "off" else None) for name in presets])
    out = [f"센 횟수/실제 횟수. Δ = 꺼짐(기본)과 센 반복이 다름(개수 또는 시작 시각 {START_TOLERANCE_SECONDS}초 초과 차이).", render(rows, head, markdown), ""]
    extra_head = ["프리셋", "탈락 사유 합계(세션 전체)", "잠금 해제 합계", "합쳐짐 의심 합계"]
    extra = []
    for name in presets:
        reasons: dict[str, int] = {}
        for r in results[name]:
            for k, n in r.rejected.items():
                reasons[k] = reasons.get(k, 0) + n
        extra.append(
            [
                name,
                ", ".join(f"{k}={n}" for k, n in sorted(reasons.items())) or "-",
                str(sum(r.lock_releases for r in results[name])),
                str(sum(r.merge_suspects for r in results[name])),
            ]
        )
    out.append(render(extra, extra_head, markdown))
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="+", type=Path, help="원본 로그(jsonl). 없으면 fixture를 쓴다")
    parser.add_argument("--sessions", nargs="+", help="fixture 세션 id(기본: 1 2 3 4 5 7 8a 8b 8c)")
    parser.add_argument("--matrix", action="store_true", help="프리셋 x 세션 표")
    parser.add_argument("--presets", nargs="+", choices=list(PRESETS), help="--matrix에 쓸 프리셋(기본: 전부)")
    parser.add_argument("--list-presets", action="store_true")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--set-baseline", action="store_true", help="세트 단위 서 있는 기준 높이")
    parser.add_argument("--return-angle", type=float, help="STANDING 복귀 무릎각(150 초과 160 이하)")
    parser.add_argument("--boundary", choices=BOUNDARY_SIGNALS, default="smoothed", help="반복 경계 신호")
    parser.add_argument("--lock-grace", type=float, default=0.0, help="잠금 해제 유예(초)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.list_presets:
        for name, flags in PRESETS.items():
            print(f"{name:10s} {flags.label()}")
        return 0
    payloads = [load_log(p) for p in args.log] if args.log else [load_fixture(s) for s in (args.sessions or DEFAULT_SESSIONS)]
    if args.matrix:
        presets = {n: PRESETS[n] for n in (args.presets or PRESETS)}
        print(matrix(payloads, presets, args.markdown))
        return 0
    flags = Flags(args.set_baseline, args.return_angle, args.boundary, args.lock_grace)
    print(f"플래그: {flags.label()}")
    head = ["세션", "센/실제", "탈락 사유", "잠금 해제", "합쳐짐 의심"]
    rows = []
    for p in payloads:
        r = replay(p, flags)
        reasons = ", ".join(f"{k}={n}" for k, n in sorted(r.rejected.items())) or "-"
        rows.append([r.session, cell(r, None), reasons, str(r.lock_releases), str(r.merge_suspects)])
    print(render(rows, head, args.markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
