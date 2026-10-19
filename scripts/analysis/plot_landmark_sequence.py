"""Landmark 시퀀스 세션 로그를 읽어 무릎각 시계열, 부호 있는 몸통·정강이각, 전신 유효 구간,
라벨 분포를 그린다. 아직 RepTracker가 없으므로 반복 구간은 무릎각 그래프에서 눈으로 확인한다.

실행 예:
    python scripts/analysis/plot_landmark_sequence.py --session data/landmark_sequences/session_....jsonl

출력(--out-dir, 기본은 세션 파일 옆 plots/): <세션 이름>_timeline.png, <세션 이름>_labels.png
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


LABEL_COLORS = {
    "stand": "#2a9d8f",
    "squat": "#e76f51",
    "stretch": "#8ab17d",
    "sit": "#f4a261",
    "bendover": "#b5838d",
    "walk": "#457b9d",
    "run": "#1d3557",
    "jump": "#6d597a",
    "lying": "#8d99ae",
    None: "#cccccc",
}


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--session", type=Path, required=True, help="data/landmark_sequences/의 세션 JSONL 파일")
    parser.add_argument("--out-dir", type=Path, default=None, help="그래프 저장 위치 (기본: 세션 파일 옆 plots/)")
    parser.add_argument(
        "--max-gap",
        type=float,
        default=0.5,
        help="이 초 이상 벌어진 프레임 사이는 선을 잇지 않고 라벨 시간에도 넣지 않습니다.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------- 읽기


SUPPORTED_FORMAT_VERSIONS = (1, 2)  # 1: RepTracker 진단 이전 로그, 2: rep 상태와 event 줄이 있는 로그
REP_STATE_COLORS = {"WAITING_LOCK": "#bbbbbb", "STANDING": "#2a9d8f", "IN_REP": "#e9a23b"}


def load_events(path: Path) -> list[dict[str, Any]]:
    """v2 로그의 event 줄(rep_end, rep_merge_suspect, lock). v1 로그에는 없으므로 빈 목록이다."""
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") == "event":
                events.append(record)
    return events


def load_session(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None, int]:
    """(헤더, 프레임 목록, 끝 줄 또는 None, 읽을 수 없어 건너뛴 줄 수). 비정상 종료로 잘린 마지막 줄을 견딘다."""
    header: dict[str, Any] | None = None
    frames: list[dict[str, Any]] = []
    end: dict[str, Any] | None = None
    skipped = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            kind = record.get("type")
            if kind == "session":
                header = record
            elif kind == "frame":
                frames.append(record)
            elif kind == "end":
                end = record
    if header is None:
        raise ValueError(f"No session header found in {path}")
    version = header.get("format_version", 1)
    if version not in SUPPORTED_FORMAT_VERSIONS:
        raise ValueError(f"Unsupported format_version {version} in {path} (supported: {SUPPORTED_FORMAT_VERSIONS})")
    return header, frames, end, skipped


def _value(record: dict[str, Any] | None, key: str) -> float:
    if record is None or record.get(key) is None:
        return np.nan
    return float(record[key])


def build_series(header: dict[str, Any], frames: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    """프레임 목록을 시간축 배열로 바꾼다. 값이 없는 프레임은 NaN."""
    names = header["landmark_names"]
    index = {name: position for position, name in enumerate(names)}

    def frame_y(frame: dict[str, Any], landmark: str) -> float:
        """crop 정규화 y를 프레임 픽셀 y로 바꾼다(crop이 프레임마다 달라지므로 필수)."""
        geometry, rows, crop = frame.get("geometry"), frame.get("landmarks"), frame.get("crop_bbox")
        if geometry is None or rows is None or crop is None:
            return np.nan
        y = rows[index[f"{geometry['leg']}_{landmark}"]][1]
        return np.nan if y is None else crop[1] + y * (crop[3] - crop[1])

    series: dict[str, list] = defaultdict(list)
    for frame in frames:
        geometry = frame.get("geometry")
        full_body = frame.get("full_body")
        view = frame.get("view")
        labels = frame.get("labels") or {}
        series["t"].append(frame["t"])
        series["person"].append(bool(frame.get("person")))
        series["knee"].append(_value(geometry, "knee"))
        series["knee_smoothed"].append(_value(geometry, "knee_smoothed"))
        series["torso"].append(_value(geometry, "torso"))
        series["shin"].append(_value(geometry, "shin"))
        series["torso_signed"].append(_value(geometry, "torso_signed"))
        series["shin_signed"].append(_value(geometry, "shin_signed"))
        series["valid"].append(bool(full_body and full_body["valid"]))
        series["locked"].append(bool((frame.get("lock") or {}).get("locked")))
        series["heel_y"].append(frame_y(frame, "heel"))
        series["toe_y"].append(frame_y(frame, "foot_index"))
        series["hip_y"].append(frame_y(frame, "hip"))
        series["knee_y"].append(frame_y(frame, "knee"))
        series["shoulder_ratio"].append(_value(view, "shoulder_ratio"))
        series["nose_visibility"].append(_value(view, "nose_visibility"))
        series["hip_yaw_deg"].append(_value(view, "hip_yaw_deg"))
        series["rep_state"].append((frame.get("rep") or {}).get("state"))  # v1 로그에는 없다
        series["stable"].append(labels.get("stable"))
        series["raw"].append(labels.get("raw"))
        series["display"].append(labels.get("display"))
    result: dict[str, np.ndarray] = {}
    for key, values in series.items():
        result[key] = np.asarray(values, dtype=object if key in ("stable", "raw", "display", "rep_state") else float)
    for key in ("person", "valid", "locked"):
        result[key] = result[key].astype(bool)
    return result


def frame_durations(t: np.ndarray, max_gap: float) -> np.ndarray:
    """각 프레임이 차지하는 시간(다음 프레임까지, 초). max_gap보다 긴 공백은 0으로 본다."""
    if len(t) == 0:
        return np.zeros(0)
    durations = np.append(np.diff(t), 0.0)
    durations[durations > max_gap] = 0.0
    return durations


def label_seconds(labels: np.ndarray, durations: np.ndarray, mask: np.ndarray | None = None) -> dict[Any, float]:
    totals: dict[Any, float] = defaultdict(float)
    for position, label in enumerate(labels):
        if mask is None or mask[position]:
            totals[label] += float(durations[position])
    return dict(totals)


def summarize(header: dict[str, Any], series: dict[str, np.ndarray], end: dict[str, Any] | None, skipped: int, max_gap: float) -> str:
    t = series["t"]
    durations = frame_durations(t, max_gap)
    total = float(durations.sum())
    lines = [
        f"session started : {header['started_at']}",
        f"metadata        : {header['metadata']}",
        f"frames          : {len(t)}" + (f" (offered {end['frames_offered']}, dropped {end['frames_dropped']})" if end else " (no end line: the session did not close normally)"),
    ]
    if skipped:
        lines.append(f"skipped lines   : {skipped} (unreadable, probably cut off)")
    if len(t) > 1 and t[-1] > t[0]:
        lines.append(f"duration / FPS  : {t[-1] - t[0]:.1f} s, {(len(t) - 1) / (t[-1] - t[0]):.1f} frames/s")
    if total > 0:
        for name, mask in (("person detected", series["person"]), ("full body valid", series["valid"]), ("body locked", series["locked"])):
            lines.append(f"{name:<16}: {durations[mask].sum() / total * 100:.1f}% of time")
        seconds = label_seconds(series["stable"], durations)
        shares = ", ".join(f"{label}: {value:.1f}s" for label, value in sorted(seconds.items(), key=lambda item: -item[1]))
        lines.append(f"stable labels   : {shares}")
    return "\n".join(lines)


# ---------------------------------------------------------------- 그리기


def _shade(axis, t: np.ndarray, mask: np.ndarray, color: str, alpha: float) -> None:
    """mask가 True인 연속 구간을 칠한다."""
    start = None
    for position in range(len(t)):
        if mask[position] and start is None:
            start = position
        if start is not None and not mask[position]:
            axis.axvspan(t[start], t[position], color=color, alpha=alpha, linewidth=0)
            start = None
    if start is not None:
        axis.axvspan(t[start], t[-1], color=color, alpha=alpha, linewidth=0)


def _broken(t: np.ndarray, values: np.ndarray, max_gap: float) -> tuple[np.ndarray, np.ndarray]:
    """공백이 긴 곳에서 선이 끊기도록 NaN을 끼워 넣는다."""
    if len(t) < 2:
        return t, values
    gaps = np.where(np.diff(t) > max_gap)[0]
    return np.insert(t, gaps + 1, np.nan), np.insert(values, gaps + 1, np.nan)


def format_events(events: list[dict[str, Any]]) -> list[str]:
    """event 줄을 시간 순으로 한 줄씩 읽기 쉽게 바꾼다(그래프 없이 터미널에서 원인을 볼 수 있게)."""

    def number(value: Any, digits: int = 2) -> str:
        return "-" if value is None else f"{value:.{digits}f}"

    lines = []
    for event in sorted(events, key=lambda e: e["t"]):
        kind, t = event.get("kind"), event["t"]
        if kind == "rep_end":
            verdict = "COUNTED" if event["counted"] else "REJECTED(" + ",".join(event["reasons"]) + ")"
            limits = event.get("limits", {})
            lines.append(
                f"  [{t:7.2f}s] rep_end   {verdict:<34} {number(event['t_start'])}-{number(event['t_end'])}s "
                f"len {number(event['total_seconds'])} (>= {limits.get('min_seconds', '-')}) "
                f"hip {number(event['hip_drop_norm'])} (>= {limits.get('min_hip_drop', '-')}) "
                f"gap {number(event['ankle_gap_norm'])} (<= {limits.get('max_ankle_gap', '-')}) "
                f"ml {number(event['other_exercise_ratio'])} (<= {limits.get('other_max_ratio', '-')}) "
                f"min_knee {number(event['min_knee'], 0)} merge_suspects {event.get('merge_suspects', 0)}"
                + (" TIMEOUT" if event.get("timeout") else "")
            )
        elif kind == "rep_merge_suspect":
            lines.append(
                f"  [{t:7.2f}s] MERGE?    rose to {number(event['peak_knee'], 1)} deg (needed {event['standing_angle']:g}, short by "
                f"{number(event['peak_shortfall'], 1)}) from {number(event['min_knee'], 1)} deg, then went down again"
            )
        elif kind == "lock":
            detail = event.get("detail") or {}
            text = ", ".join(f"{k}={v}" for k, v in detail.items())
            lines.append(f"  [{t:7.2f}s] lock      {event['event']}" + (f" ({text})" if text else ""))
    return lines


def _lock_release_spans(events: list[dict[str, Any]], end_time: float) -> list[tuple[float, float, str]]:
    """lock event에서 해제부터 다시 잠길 때까지(또는 끝까지)의 구간 [(시작, 끝, 사유 문구)]."""
    spans: list[tuple[float, float, str]] = []
    open_since: tuple[float, str] | None = None
    for event in sorted((e for e in events if e.get("kind") == "lock"), key=lambda e: e["t"]):
        if event["event"] in ("released_view", "released_missing"):
            detail = event.get("detail") or {}
            open_since = (event["t"], f"{detail.get('reason', event['event'])} {detail.get('seconds', 0):.1f}s")
        elif event["event"] == "acquired" and open_since is not None:
            spans.append((open_since[0], event["t"], open_since[1]))
            open_since = None
    if open_since is not None:
        spans.append((open_since[0], end_time, open_since[1]))
    return spans


def _annotate_rep_events(axis, events: list[dict[str, Any]], end_time: float) -> None:
    """무릎각 그래프 위에 반복 후보(확정=초록, 탈락=빨강+사유), 합쳐짐 의심 지점, 잠금 해제 구간을 그린다."""
    for event in events:
        if event.get("kind") == "rep_end":
            counted = event["counted"]
            axis.axvspan(event["t_start"], event["t_end"], color="#2a9d8f" if counted else "#d62828", alpha=0.16, linewidth=0)
            if not counted:
                axis.text((event["t_start"] + event["t_end"]) / 2, 183, ",".join(event["reasons"]), rotation=90,
                          ha="center", va="top", fontsize=6.5, color="#9d0208")
        elif event.get("kind") == "rep_merge_suspect":
            axis.axvline(event["t"], color="#7b2cbf", linestyle="--", linewidth=1)
            axis.plot([event["t_peak"]], [event["peak_knee"]], marker="v", color="#7b2cbf", markersize=7, zorder=5)
            axis.text(event["t_peak"], min(event["peak_knee"] + 6, 186), f"peak {event['peak_knee']:.0f}", fontsize=7,
                      color="#7b2cbf", ha="center")
    for start, stop, reason in _lock_release_spans(events, end_time):
        axis.axvspan(start, stop, ymin=0.0, ymax=0.08, color="#f77f00", alpha=0.85, linewidth=0)
        axis.text((start + stop) / 2, 46, reason, fontsize=7, color="#9a4a00", ha="center")


def plot_timeline(
    header: dict[str, Any],
    series: dict[str, np.ndarray],
    out_path: Path,
    max_gap: float,
    events: list[dict[str, Any]] | None = None,
) -> None:
    t = series["t"]
    settings = header.get("settings", {})
    fig, axes = plt.subplots(
        6, 1, figsize=(15, 15), sharex=True, gridspec_kw={"height_ratios": [3, 0.8, 2.2, 2, 1.6, 2]}
    )
    knee_axis, rep_axis, lean_axis, foot_axis, label_axis, view_axis = axes

    for axis in axes:
        _shade(axis, t, ~series["valid"] & series["person"], "#d62828", 0.10)
        _shade(axis, t, ~series["person"], "#999999", 0.12)
        axis.grid(alpha=0.25)

    knee_axis.plot(*_broken(t, series["knee"], max_gap), color="#999999", linewidth=0.8, label="knee angle (raw)")
    knee_axis.plot(*_broken(t, series["knee_smoothed"], max_gap), color="#1d4e89", linewidth=1.6, label="knee angle (One Euro, valid frames)")
    if "STANDING_KNEE_ANGLE" in settings:
        knee_axis.axhline(settings["STANDING_KNEE_ANGLE"], color="#2a9d8f", linestyle="--", linewidth=1, label=f"STANDING {settings['STANDING_KNEE_ANGLE']:.0f}")
    knee_axis.set_ylabel("knee angle (deg)")
    knee_axis.set_ylim(0, 190)
    # 잠금 구간을 아래쪽 띠로 표시한다.
    lock_band = np.where(series["locked"], 4.0, np.nan)
    knee_axis.plot(*_broken(t, lock_band, max_gap), color="#2a9d8f", linewidth=5, solid_capstyle="butt", label="BodyLock locked")
    if events:
        _annotate_rep_events(knee_axis, events, float(t[-1]))
    knee_axis.legend(loc="lower right", ncol=2, fontsize=8)
    # RepTracker 상태 띠(v2). 오렌지 = 반복 중, 청록 = 잠긴 채 서 있음, 회색 = 잠금 대기.
    if any(state is not None for state in series["rep_state"]):
        for state, color in REP_STATE_COLORS.items():
            mask = series["rep_state"] == state
            rep_axis.scatter(t[mask], np.zeros(mask.sum()), marker="s", s=22, color=color, linewidths=0, label=state)
        rep_axis.legend(loc="upper right", ncol=3, fontsize=7)
    else:
        rep_axis.text(0.5, 0.5, "no RepTracker data (format_version 1 log)", transform=rep_axis.transAxes, ha="center", va="center", fontsize=8, color="#777777")
    rep_axis.set_yticks([0], ["RepTracker"], fontsize=8)
    rep_axis.set_ylim(-1, 1)
    title = f"{header['metadata'].get('intended_posture')} / {header['metadata'].get('camera_view')}  ({header['started_at']})"
    knee_axis.set_title(title + "   [red = person but full body invalid, gray = no person]", fontsize=10)

    lean_axis.axhline(0, color="black", linewidth=0.6)
    lean_axis.plot(*_broken(t, series["torso_signed"], max_gap), color="#e76f51", linewidth=1.4, label="torso lean (signed, forward = +)")
    lean_axis.plot(*_broken(t, series["shin_signed"], max_gap), color="#264653", linewidth=1.4, label="shin lean (signed, knee ahead = +)")
    lean_axis.plot(*_broken(t, series["torso"], max_gap), color="#e76f51", linewidth=0.7, linestyle=":", label="torso (unsigned)")
    lean_axis.plot(*_broken(t, series["shin"], max_gap), color="#264653", linewidth=0.7, linestyle=":", label="shin (unsigned)")
    lean_axis.set_ylabel("angle from vertical (deg)")
    lean_axis.legend(loc="upper right", ncol=2, fontsize=8)

    foot_axis.plot(*_broken(t, series["heel_y"], max_gap), color="#6a4c93", linewidth=1.2, label="heel y (frame px)")
    foot_axis.plot(*_broken(t, series["toe_y"], max_gap), color="#1982c4", linewidth=1.2, label="foot_index y (frame px)")
    foot_axis.invert_yaxis()  # 위로 올라가면 그래프에서도 위로
    foot_axis.set_ylabel("y in frame (px, up = higher)")
    foot_axis.legend(loc="upper right", ncol=2, fontsize=8)

    rows = (("stable", 2, "stable (before display filter)"), ("raw", 1, "raw per frame"), ("display", 0, "display"))
    for key, level, _ in rows:
        for label in sorted({value for value in series[key] if value is not None}, key=str):
            color = LABEL_COLORS.get(str(label).lower(), "#888888")
            mask = series[key] == label
            label_axis.scatter(t[mask], np.full(mask.sum(), level), marker="s", s=14, color=color, linewidths=0)
    label_axis.set_yticks([level for _, level, _ in rows], [name for _, _, name in rows], fontsize=8)
    label_axis.set_ylim(-0.7, 2.7)
    handles = [plt.Line2D([], [], marker="s", linestyle="", color=color, label=str(label)) for label, color in LABEL_COLORS.items() if label is not None]
    label_axis.legend(handles=handles, loc="upper right", ncol=9, fontsize=7)

    view_axis.plot(*_broken(t, series["shoulder_ratio"], max_gap), color="#e07a5f", linewidth=1.0, label="(a) shoulder ratio")
    view_axis.plot(*_broken(t, series["nose_visibility"], max_gap), color="#3d405b", linewidth=1.0, label="(c) nose visibility")
    if "SIDE_VIEW_MAX_SHOULDER_RATIO" in settings:
        view_axis.axhline(settings["SIDE_VIEW_MAX_SHOULDER_RATIO"], color="#e07a5f", linestyle="--", linewidth=0.8)
    view_axis.set_ylim(0, 1.6)
    view_axis.set_ylabel("ratio / visibility")
    yaw_axis = view_axis.twinx()
    yaw_axis.plot(*_broken(t, series["hip_yaw_deg"], max_gap), color="#81b29a", linewidth=1.0, label="(b) hip yaw (0 = front/back, 90 = side)")
    yaw_axis.set_ylim(0, 95)
    yaw_axis.set_ylabel("hip yaw (deg)")
    handles_a, names_a = view_axis.get_legend_handles_labels()
    handles_b, names_b = yaw_axis.get_legend_handles_labels()
    view_axis.legend(handles_a + handles_b, names_a + names_b, loc="upper right", ncol=3, fontsize=8)
    view_axis.set_xlabel("time since logging start (s)")

    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_label_distribution(series: dict[str, np.ndarray], out_path: Path, max_gap: float) -> None:
    durations = frame_durations(series["t"], max_gap)
    groups = (
        ("all time", None),
        ("full body valid", series["valid"]),
        ("knee < 150 (smoothed, valid)", np.nan_to_num(series["knee_smoothed"], nan=999.0) < 150.0),
    )
    fig, axes = plt.subplots(1, len(groups), figsize=(16, 4.5), sharex=False)
    for axis, (title, mask) in zip(axes, groups):
        seconds = label_seconds(series["stable"], durations, mask)
        items = sorted(seconds.items(), key=lambda item: -item[1])
        names = [str(label) for label, _ in items]
        values = [value for _, value in items]
        colors = [LABEL_COLORS.get(str(label).lower(), "#888888") for label, _ in items]
        axis.barh(names[::-1], values[::-1], color=colors[::-1])
        axis.set_title(f"stable label time — {title}", fontsize=10)
        axis.set_xlabel("seconds")
        axis.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    session_path: Path = arguments.session
    if not session_path.is_file():
        sys.exit(f"ERROR: session file not found: {session_path}")

    header, frames, end, skipped = load_session(session_path)
    if not frames:
        sys.exit("ERROR: the session has no frames.")
    series = build_series(header, frames)
    events = load_events(session_path)
    print(summarize(header, series, end, skipped, arguments.max_gap))
    if events:
        kinds = {kind: sum(1 for e in events if e.get("kind") == kind) for kind in sorted({e.get("kind") for e in events})}
        print(f"events          : {kinds}")
        for line in format_events(events):
            print(line)

    out_dir = arguments.out_dir if arguments.out_dir is not None else session_path.parent / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    timeline_path = out_dir / f"{session_path.stem}_timeline.png"
    labels_path = out_dir / f"{session_path.stem}_labels.png"
    plot_timeline(header, series, timeline_path, arguments.max_gap, events)
    plot_label_distribution(series, labels_path, arguments.max_gap)
    print(f"saved: {timeline_path}\nsaved: {labels_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
