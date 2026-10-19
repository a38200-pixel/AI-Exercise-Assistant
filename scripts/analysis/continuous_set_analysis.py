"""연속 세트 재현 로그 분석(FPS, 반복 사이 봉우리, 이벤트, 잠금 다리)과 저FPS 재생. 카메라를 쓰지 않는다.

입력: --log <session_*.jsonl>... (원본 로그) 와 field_test_1 fixture(세션 1~5). 제품 코드는 바꾸지 않는다.

실행(저장소 루트에서):
    python -m scripts.analysis.continuous_set_analysis --log data/landmark_sequences/session_20261019_171322_normal_side.jsonl ...
        [--fps 17 12 10 8 6 5] [--fixtures 1 2 3 4 5]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.analysis import replay_flags as rf  # noqa: E402

FPS_LIST = (12, 10, 8, 6, 5)
PRESET_NAMES = ("off", "light", "return155", "all")


# ---------------------------------------------------------------- 원본 로그 읽기


def read_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fps_stats(frames: list[dict[str, Any]]) -> tuple[float, float]:
    """(중앙값 FPS, 하위 5% FPS = 프레임 간격 상위 5% 지점의 역수)."""
    dt = np.diff([f["t"] for f in frames])
    dt = dt[dt > 0]
    return float(1.0 / np.median(dt)), float(1.0 / np.percentile(dt, 95))


def between_rep_peaks(frames: list[dict[str, Any]], rep_ends: list[dict[str, Any]]) -> list[dict[str, float]]:
    """연속한 두 반복의 최저점 시각 사이에서 원본(knee)·평활(knee_smoothed) 무릎각의 최댓값(반복 사이 봉우리)."""
    bottoms = [e["t_bottom"] for e in rep_ends if e.get("t_bottom") is not None]
    rows = []
    for a, b in zip(bottoms, bottoms[1:]):
        raw, smooth = [], []
        for f in frames:
            if a <= f["t"] <= b and f.get("geometry"):
                g = f["geometry"]
                if g.get("knee_smoothed") is not None:  # 전신이 유효한 프레임만(평활과 같은 조건)
                    raw.append(g["knee"])
                    smooth.append(g["knee_smoothed"])
        rows.append({"gap": b - a, "raw": max(raw) if raw else float("nan"), "smooth": max(smooth) if smooth else float("nan")})
    return rows


def lock_leg_report(frames: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    """잠근 다리가 바뀐 횟수와, 잠근 다리의 전신 무효가 이어져 WAITING_LOCK에 갇힌(서 있는데 반복 추적이 시작되지 않은) 구간."""
    lock_events = [e for e in events if e.get("kind") == "lock"]
    changes = [e for e in lock_events if e.get("event") == "changed"]
    stuck, start, end, reasons = [], None, None, {}
    for f in frames:
        g, fb, rep = f.get("geometry"), f.get("full_body"), f.get("rep")
        lock = f.get("lock") or {}
        bad = bool(
            f.get("person") and g and fb and not fb["valid"] and lock.get("locked")
            and rep and rep["state"] == "WAITING_LOCK" and g.get("leg_now") not in (None, lock.get("leg"))
        )
        if bad:
            start = f["t"] if start is None else start
            end = f["t"]
            for r in fb["reasons"]:
                reasons[r] = reasons.get(r, 0) + 1
        elif start is not None:
            if end - start >= 1.0:
                stuck.append((start, end))
            start = None
    if start is not None and end - start >= 1.0:
        stuck.append((start, end))
    return {"lock_events": len(lock_events), "leg_changes": len(changes), "stuck": stuck, "reasons": reasons}


# ---------------------------------------------------------------- 저FPS 재생


def baseline_reps(payload: dict[str, Any]) -> list[tuple[float, float]]:
    base = rf.replay(payload, rf.PRESETS["off"])
    return [(r.t_start, r.t_end) for r in base.results if r.counted]


def explain_missing(base: list[tuple[float, float]], result: rf.Replay) -> list[str]:
    """원래(최대 FPS) 확정 반복마다 솎아낸 재생에서 어떻게 됐는지: 'ok' 또는 누락 사유."""
    rep_ends = [e for e in result.events if e["kind"] == "rep_end"]
    out = []
    for s, e in base:
        overlapping = [r for r in rep_ends if r["t_start"] < e and r["t_end"] > s]
        counted = [r for r in overlapping if r["counted"]]
        if counted:
            span = [i for i, (bs, be) in enumerate(base, start=1) if counted[0]["t_start"] < be and counted[0]["t_end"] > bs]
            out.append("ok" if len(span) == 1 else f"합쳐짐({','.join(map(str, span))}번이 1회로)")
        elif overlapping:
            out.append("탈락:" + "+".join(overlapping[0]["reasons"]))
        else:
            out.append("후보 없음(반복이 시작되지 않음)")
    return out


def peak_between(payload_frames: list[dict[str, Any]], fps: float, base: list[tuple[float, float]]) -> float:
    """솎아내고 다시 평활한 무릎각의 반복 사이 최소 봉우리(원래 반복 사이 구간, 160° 도달 여부 판단용)."""
    from src.pose_geometry import OneEuroFilter

    kept = rf.decimate(payload_frames, fps)
    smoother, series = OneEuroFilter(), []
    for f in kept:
        if f["present"] and f["knee_smoothed"] is not None and f.get("knee_raw") is not None:
            series.append((f["t"], smoother(f["knee_raw"], f["t"])))
    peaks = []
    for (_, e1), (s2, _) in zip(base, base[1:]):
        window = [v for t, v in series if e1 - 0.5 <= t <= s2 + 0.5]
        if window:
            peaks.append(max(window))
    return min(peaks) if peaks else float("nan")


def low_fps_table(sources: list[tuple[str, dict[str, Any]]], fps_values: list[float]) -> str:
    lines = [
        "| 입력 | FPS | 센 횟수/기준 | 누락 위치와 사유(꺼짐) | 반복 사이 최소 봉우리(재평활) | light | 복귀155 | 모두 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, payload in sources:
        base = baseline_reps(payload)
        for fps in fps_values:
            results = {p: rf.replay(payload, rf.PRESETS[p], fps=fps) for p in PRESET_NAMES}
            off = results["off"]
            explanation = explain_missing(base, off)
            missing = [f"{i}번 {why}" for i, why in enumerate(explanation, start=1) if why != "ok"]
            peak = peak_between(payload["frames"], fps, base)
            lines.append(
                f"| {name} | {fps:g} | {off.counted}/{len(base)} | {'; '.join(missing) or '없음'} | {peak:.1f}° "
                f"| {results['light'].counted} | {results['return155'].counted} | {results['all'].counted} |"
            )
    return "\n".join(lines)


ABSENT = {"present": 0, "knee_smoothed": None, "knee_raw": None, "hip_y": None, "heel_y": None, "leg_length": None,
          "ankle_gap": None, "torso_signed": None, "shin_signed": None, "side_now": None, "valid": None,
          "facing_now": None, "leg_now": None}


def inject_dropout(payload: dict[str, Any], base: list[tuple[float, float]], length: float, offset: float = 0.05) -> dict[str, Any]:
    """반복마다 서 있다가 내려가기 시작한 직후 `length`초 동안 사람 없음(YOLO/Pose 놓침) 프레임을 끼워 넣는다(첫 반복 제외).
    field_test_1 세션 1에서 실제로 이 위치(내려가기 시작 직후)에 사람 없음 프레임이 몰려 있었다."""
    frames = []
    for f in payload["frames"]:
        hit = any(s + offset <= f["t"] < s + offset + length for s, _ in base[1:])
        frames.append({**f, **ABSENT, "label": None} if hit else f)
    return {**payload, "frames": frames}


def dropout_table(sources: list[tuple[str, dict[str, Any]]], lengths: list[float], offsets: list[float]) -> str:
    """반복의 '내려가기 시작' 시각(마지막 서 있는 프레임)을 기준으로 offset초부터 length초 동안 사람 없음을 끼웠을 때, 첫 반복을 뺀
    나머지 반복 중 몇 개가 세어지는지. 열은 offset(초, 음수 = 내려가기 시작 전)이다."""
    head = "| 입력 | 사람 없음 길이 | " + " | ".join(f"{o:+g}초" for o in offsets) + " |"
    lines = [head, "|---|---|" + "---|" * len(offsets)]
    for name, payload in sources:
        base = baseline_reps(payload)
        for length in lengths:
            cells = []
            for offset in offsets:
                result = rf.replay(inject_dropout(payload, base, length, offset), rf.PRESETS["off"])
                kept = sum(1 for r in result.results if r.counted and any(r.t_start < e and r.t_end > s for s, e in base[1:]))
                cells.append(f"{min(kept, len(base) - 1)}/{len(base) - 1}")
            lines.append(f"| {name} | {length:g}초 | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", nargs="*", type=Path, default=[])
    parser.add_argument("--fixtures", nargs="*", default=["1", "2", "3", "4", "5"])
    parser.add_argument("--fps", nargs="*", type=float, default=[17.0, *FPS_LIST])
    parser.add_argument("--dropout", nargs="*", type=float, default=[0.12, 0.3, 0.6])
    parser.add_argument("--offsets", nargs="*", type=float, default=[-0.9, -0.6, -0.3, 0.0, 0.1, 0.2, 0.3])
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    sources: list[tuple[str, dict[str, Any]]] = []
    for path in args.log:
        records = read_records(path)
        frames = [r for r in records if r["type"] == "frame"]
        events = [r for r in records if r["type"] == "event"]
        rep_ends = [e for e in events if e["kind"] == "rep_end"]
        footer = next((r for r in records if r["type"] == "footer"), None)
        median_fps, low_fps = fps_stats(frames)
        note = records[0]["metadata"].get("note")
        print(f"## {path.name} (note={note})")
        print(f"- FPS 중앙값 {median_fps:.1f}, 하위 5% {low_fps:.1f}; 프레임 {len(frames)}개, 버림 {records[-1].get('frames_dropped')}")
        if footer:
            print(f"- 실제 {footer['actual_reps']} / 화면 {footer['app_reps']} / 검출(rep_end 확정) {sum(1 for e in rep_ends if e['counted'])}")
        kinds: dict[str, int] = {}
        for e in events:
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        print(f"- 이벤트: {kinds}; 합쳐짐 의심 {sum(e['merge_suspects'] for e in rep_ends)}건")
        peaks = between_rep_peaks(frames, rep_ends)
        if peaks:
            raw = [p["raw"] for p in peaks]
            smooth = [p["smooth"] for p in peaks]
            print(
                f"- 반복 사이 봉우리({len(peaks)}곳): 원본 최소 {min(raw):.1f}° / 중앙값 {statistics.median(raw):.1f}° / 최대 {max(raw):.1f}°, "
                f"평활 최소 {min(smooth):.1f}° / 중앙값 {statistics.median(smooth):.1f}° / 최대 {max(smooth):.1f}° (복귀 기준 160°)"
            )
            print(f"- 반복 사이 간격(최저점~최저점): {min(p['gap'] for p in peaks):.2f}~{max(p['gap'] for p in peaks):.2f}초")
            ordered = sorted(rep_ends, key=lambda e: e["t_start"])
            dwell = [b["t_start"] - a["t_end"] for a, b in zip(ordered, ordered[1:])]
            print(f"- 서 있는 시간(반복 끝~다음 반복 시작): {min(dwell):.2f}~{max(dwell):.2f}초, 중앙값 {statistics.median(dwell):.2f}초 (field_test_1의 휴지는 0.9~2.5초)")
        lock = lock_leg_report(frames, events)
        print(f"- 잠금 이벤트 {lock['lock_events']}건, 그중 다리가 바뀐 `changed` {lock['leg_changes']}건")
        for s, e in lock["stuck"]:
            print(f"- 잠근 다리는 전신 무효인데 반대 다리는 보이는 채 WAITING_LOCK에 갇힌 구간: {s:.1f}~{e:.1f}초 ({e - s:.1f}초), 사유 {lock['reasons']}")
        print()
        sources.append((note or path.stem, rf.load_log(path)))
    for session in args.fixtures:
        sources.append((f"fixture {session}", rf.load_fixture(session)))
    print("## 저FPS 재생(솎아내기 + 솎아낸 프레임만으로 재평활)")
    print(low_fps_table(sources, args.fps))
    print()
    print("## 사람 없음 프레임 끼워 넣기(원래 FPS, 내려가기 시작 직후)")
    print(dropout_table(sources, args.dropout, args.offsets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
