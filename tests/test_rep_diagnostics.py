"""RepTracker 진단 로깅(format_version 2): 이벤트 내용, 합쳐짐 의심, 잠금 해제 상세, 로그 왕복, v1 로그 호환."""

import json
import time

import numpy as np
import pytest

from src.exercise_counter import SQUAT_MODE, ExerciseCounter
from src.geometry_tracker import GeometryTracker
from src.rep_tracker import RepFrame, RepMeasures, RepTracker, track_primary_person
from src.sequence_logger import (
    EVENT_TIME_KEYS,
    FORMAT_VERSION,
    SUPPORTED_FORMAT_VERSIONS,
    SequenceLogger,
    SequenceRecorder,
    session_metadata,
)
from test_plot_landmark_sequence import FPS as PLOT_FPS
from test_plot_landmark_sequence import blend, knee_weight, plot
from test_pose_geometry import FRAME, RIGHT_LEG_HIDDEN, build_landmarks
from test_rep_tracker import BASE_HIP_Y, FPS, LEG_LENGTH, counted, rep_curve, simulate
from test_sequence_logger import (
    CROP_S,
    PERSON_S,
    front_standing,
    locked_tracker,
    read_records,
    smoothing_state,
    standing,
)


def events_of(tracker, frames):
    """frames를 넣으며 쌓인 진단 이벤트를 모두 모은다."""
    events = []
    for frame, label in frames:
        tracker.update(frame, label)
        events.extend(tracker.pop_events())
    return events


def keypoint_curve(points, start=0.0):
    """(상대 시각, 무릎각) 점들을 선형으로 이어 30fps 프레임으로 만든다. 엉덩이 높이는 rep_curve와 같은 관계(바닥 70도에서 0.55)."""
    frames = []
    end = points[-1][0]
    for index in range(int(end * FPS) + 1):
        s = index / FPS
        knee = float(np.interp(s, [p[0] for p in points], [p[1] for p in points]))
        hip_y = BASE_HIP_Y + 0.55 * LEG_LENGTH * (175.0 - knee) / 105.0
        frame = RepFrame(
            start + s, True, knee, True, "left", "right", 45.0, 28.0,
            RepMeasures(hip_y=hip_y, heel_y=318.0, leg_length=LEG_LENGTH, ankle_gap=3.0),
        )
        frames.append((frame, "stand" if knee >= 160 else "squat"))
    return frames


# ---------------------------------------------------------------- rep_end 이벤트


def test_a_confirmed_rep_leaves_one_json_safe_event_with_its_measurements_and_limits() -> None:
    tracker = RepTracker()
    events = events_of(tracker, rep_curve())
    assert [e["kind"] for e in events] == ["rep_end"]
    event = events[0]
    json.dumps(event, allow_nan=False)  # NaN이 남아 있으면 로거가 그 줄을 버린다
    assert event["counted"] is True and event["reasons"] == [] and event["timeout"] is False
    assert event["total_seconds"] == pytest.approx(event["t_end"] - event["t_start"], abs=1e-3)
    assert event["min_knee"] == pytest.approx(70.0, abs=0.5) and event["hip_drop_norm"] == pytest.approx(0.55, abs=0.03)
    assert event["ankle_gap_norm"] == pytest.approx(0.02, abs=0.005) and event["other_exercise_ratio"] == 0.0
    assert event["limits"] == {
        "min_seconds": 1.0, "min_hip_drop": 0.20, "max_ankle_gap": 0.25, "other_max_ratio": 0.40, "standing_angle": 160.0,
    }
    assert tracker.pop_events() == []  # 가져가면 비워진다


def test_a_rejected_rep_records_the_failed_conditions_with_their_values() -> None:
    event = events_of(RepTracker(), rep_curve(hip_drop=0.10, label="walk"))[0]
    assert event["counted"] is False and set(event["reasons"]) == {"shallow_hip_drop", "other_exercise"}
    assert event["hip_drop_norm"] == pytest.approx(0.10, abs=0.03)  # 기준(0.20) 미달
    assert event["other_exercise_ratio"] > event["limits"]["other_max_ratio"]  # 기준(0.40) 초과
    assert event["total_seconds"] >= event["limits"]["min_seconds"]  # 이 조건은 통과했다는 것도 보인다


def test_a_rep_aborted_by_a_gap_is_flagged_as_a_timeout_and_stays_json_safe() -> None:
    event = events_of(RepTracker(), rep_curve(hold=2.5, blank=(2.8, 2.0)))[0]
    assert event["reasons"] == ["tracking_lost"] and event["timeout"] is True and event["counted"] is False
    assert event["hip_drop_norm"] is None  # 값을 알 수 없는 항목은 NaN이 아니라 None
    json.dumps(event, allow_nan=False)


def test_every_candidate_of_the_field_sessions_has_a_matching_event() -> None:
    for session, actual in (("1", 10), ("3", 8)):
        events = []
        _, results, _, _ = simulate(session, events_out=events)
        ends = [e for e in events if e["kind"] == "rep_end"]
        assert len(ends) == len(results)
        assert sum(e["counted"] for e in ends) == len(counted(results)) == actual


# ---------------------------------------------------------------- 합쳐짐 의심


def test_rising_part_way_and_going_down_again_is_flagged_with_the_peak_that_was_reached() -> None:
    # 70도까지 내려갔다가 135도까지만 올라오고(복귀 각도 160도에 25도 모자람) 다시 90도로 내려간 뒤 일어선다.
    frames = keypoint_curve([(0, 175), (1.5, 175), (2.7, 70), (3.2, 70), (4.2, 135), (4.8, 90), (5.0, 90), (6.2, 175), (7.7, 175)])
    events = events_of(RepTracker(), frames)
    suspects = [e for e in events if e["kind"] == "rep_merge_suspect"]
    assert len(suspects) == 1
    suspect = suspects[0]
    assert suspect["peak_knee"] == pytest.approx(135.0, abs=2.0)  # 올라온 최대 무릎각
    assert suspect["min_knee"] == pytest.approx(70.0, abs=1.0) and suspect["peak_shortfall"] == pytest.approx(25.0, abs=2.0)
    assert suspect["t_min"] < suspect["t_peak"] < suspect["t"] and suspect["rep_t_start"] < suspect["t_min"]
    json.dumps(suspect, allow_nan=False)

    ends = [e for e in events if e["kind"] == "rep_end"]
    assert len(ends) == 1 and ends[0]["merge_suspects"] == 1  # 한 반복으로 끝났고, 의심 횟수가 남는다


def test_clean_reps_and_small_bottom_jitter_are_not_flagged() -> None:
    assert [e["kind"] for e in events_of(RepTracker(), rep_curve())] == ["rep_end"]

    jitter = []
    for frame, label in rep_curve(hold=1.5):
        knee = frame.knee_smoothed + (3.0 * np.sin(frame.timestamp * 9.0) if frame.knee_smoothed < 100 else 0.0)
        jitter.append((RepFrame(frame.timestamp, True, knee, True, "left", "right", 45.0, 28.0, frame.measures), label))
    assert [e["kind"] for e in events_of(RepTracker(), jitter)] == ["rep_end"]  # ±3도 흔들림은 의심이 아니다


def test_a_rise_smaller_than_the_threshold_is_not_flagged() -> None:
    frames = keypoint_curve([(0, 175), (1.5, 175), (2.7, 70), (3.2, 70), (3.7, 85), (4.2, 70), (5.4, 175), (6.9, 175)])
    assert [e["kind"] for e in events_of(RepTracker(), frames)] == ["rep_end"]  # 15도 오르내림 < 20도


def test_session_1_to_5_reps_are_never_flagged_as_merged() -> None:
    for session in ("1", "2", "3", "4", "5"):
        events = []
        simulate(session, events_out=events)
        assert [e for e in events if e["kind"] == "rep_merge_suspect"] == [], session


# ---------------------------------------------------------------- 잠금 해제·재잠금 상세


def test_the_first_lock_has_no_detail_and_a_release_records_why_and_for_how_long() -> None:
    tracker = GeometryTracker()
    standing(tracker, 0.0)
    assert standing(tracker, 0.5).lock.detail is None  # 첫 획득: 해제 이력이 없다

    front_standing(tracker, 1.0)
    front_standing(tracker, 1.3)
    released = front_standing(tracker, 1.45)
    assert released.lock.event == "released_view"
    assert released.lock.detail["reason"] == "non_side" and released.lock.detail["seconds"] == pytest.approx(0.45, abs=0.01)


def test_reacquiring_after_a_release_records_the_unlocked_time_and_the_previous_reason() -> None:
    tracker = locked_tracker()
    for t in (1.0, 1.3, 1.45):
        front_standing(tracker, t)  # 1.45초에 해제
    acquired_at, tracked = None, None
    for step in range(20):
        now = 2.0 + step * 0.05
        tracked = standing(tracker, now)
        if tracked.lock.event == "acquired":
            acquired_at = now
            break
    assert acquired_at is not None
    assert tracked.lock.detail["previous_release_reason"] == "non_side"
    assert tracked.lock.detail["unlocked_seconds"] == pytest.approx(acquired_at - 1.45, abs=0.01)


def test_a_release_by_a_missing_person_records_that_reason() -> None:
    tracker = locked_tracker(missing_release_seconds=2.0)
    tracker.update_missing(1.0)
    released = tracker.update_missing(3.1)
    assert released.event == "released_missing"
    assert released.detail == {"reason": "person_missing", "seconds": pytest.approx(2.1, abs=0.01)}


# ---------------------------------------------------------------- ExerciseCounter.rep_diagnostics


def test_rep_diagnostics_reports_state_notice_and_drains_the_events() -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    assert counter.rep_diagnostics() is None  # squat 모드가 아니다
    counter.set_mode(SQUAT_MODE, 0.0)
    for frame, label in rep_curve():
        counter.update(label, frame.timestamp, frame)
    diagnostics = counter.rep_diagnostics()
    assert diagnostics["state"] == "STANDING" and diagnostics["notice"] is None
    assert [e["kind"] for e in diagnostics["events"]] == ["rep_end"]
    assert counter.rep_diagnostics()["events"] == []  # 한 번 가져가면 비워진다
    assert ExerciseCounter().rep_diagnostics() is None  # RepTracker가 없으면 진단도 없다


# ---------------------------------------------------------------- 로그 왕복(v2)과 v1 호환


def record_rep_session(directory, seconds=5.0):
    """로깅 중 main과 같은 순서(기하 분석 → ExerciseCounter → 기록)로 반복 한 번(1~3초)을 기록한다."""
    base = 1000.0  # 가짜 시계: 부하와 상관없이 세션 시간이 프레임 시각과 정확히 같다
    logger = SequenceLogger(directory, metadata=session_metadata("normal", "side"), flush_interval=0.05, clock=lambda: base)
    path = logger.start()
    tracker = GeometryTracker()
    recorder = SequenceRecorder(logger, tracker)
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    for index in range(int(seconds * PLOT_FPS)):
        second = index / PLOT_FPS
        weight = knee_weight(second)
        person = {
            "bbox": PERSON_S, "padded_bbox": CROP_S, "person_confidence": 0.9,
            "landmarks": build_landmarks(blend(weight), CROP_S, {"nose": 0.99, **RIGHT_LEG_HIDDEN}),
            "world_landmarks": None, "prediction": None,
        }
        label = "squat" if weight > 0.5 else "stand"
        tracked, lock_state, rep_frame = track_primary_person(tracker, person, FRAME, base + second)
        counter.update(label, base + second, rep_frame)
        recorder.record(
            frame_size=FRAME, primary_person=person, smoothing_state=smoothing_state(label), display_pose=label.upper(),
            display_confidence=0.9, capture_time=base + second, logic_time=base + second + 0.002,
            geometry=(tracked, lock_state), rep=counter.rep_diagnostics(),
        )
    recorder.close()
    return path


def test_the_logger_writes_format_version_two_and_the_reader_accepts_one_and_two() -> None:
    assert FORMAT_VERSION == 2 and SUPPORTED_FORMAT_VERSIONS == (1, 2)
    assert plot.SUPPORTED_FORMAT_VERSIONS == (1, 2)


def test_a_recorded_session_contains_the_rep_state_and_every_event_kind_it_produced(tmp_path) -> None:
    path = record_rep_session(tmp_path)
    records = read_records(path)
    frames = [r for r in records if r["type"] == "frame"]
    events = [r for r in records if r["type"] == "event"]

    assert records[0]["format_version"] == 2
    states = [f["rep"]["state"] for f in frames]
    assert states[0] == "WAITING_LOCK" and "STANDING" in states and "IN_REP" in states  # 상태가 프레임마다 남는다
    assert all(f["rep"]["notice"] in (None, "not_side", "full_body_invalid") for f in frames)

    lock_events = [e for e in events if e["kind"] == "lock"]
    assert [e["event"] for e in lock_events] == ["acquired"] and lock_events[0]["detail"] is None
    ends = [e for e in events if e["kind"] == "rep_end"]
    assert len(ends) == 1 and isinstance(ends[0]["counted"], bool) and ends[0]["hip_drop_norm"] is not None
    # 시각은 세션 시작 기준 초로 바뀌어 프레임의 t와 같은 축에 놓인다.
    last_t = frames[-1]["t"]
    assert 0.0 <= ends[0]["t_start"] < ends[0]["t_bottom"] < ends[0]["t_end"] <= last_t
    assert all(ev["i"] >= 1 for ev in events)  # 어느 프레임에서 일어났는지
    assert records[-1]["type"] == "end" and records[-1]["events_written"] == len(events) and records[-1]["events_dropped"] == 0
    assert {"t", "t_start", "t_end"} <= set(EVENT_TIME_KEYS)


def test_frames_without_rep_diagnostics_stay_valid_and_have_no_rep_field_value(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    path = logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker())
    person = {
        "bbox": PERSON_S, "padded_bbox": CROP_S, "person_confidence": 0.9,
        "landmarks": build_landmarks(blend(0.0), CROP_S, {"nose": 0.99, **RIGHT_LEG_HIDDEN}),
        "world_landmarks": None, "prediction": None,
    }
    recorder.record(
        frame_size=FRAME, primary_person=person, smoothing_state=smoothing_state(), display_pose="STAND",
        display_confidence=0.9, capture_time=time.perf_counter(), logic_time=time.perf_counter(),
    )
    recorder.close()
    assert read_records(path)[1]["rep"] is None


def make_v1_copy(source, destination):
    """v2 로그에서 v2에서 생긴 것(rep, lock.detail, event 줄, end의 events_*)을 빼고 format_version을 1로 되돌린 로그."""
    lines = []
    for line in source.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["type"] == "event":
            continue
        if record["type"] == "session":
            record["format_version"] = 1
        if record["type"] == "frame":
            record.pop("rep", None)
            record["lock"].pop("detail", None)
        if record["type"] == "end":
            record.pop("events_written", None)
            record.pop("events_dropped", None)
        lines.append(json.dumps(record, separators=(",", ":")))
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_a_format_version_one_log_is_still_read_and_plotted(tmp_path, capsys) -> None:
    v2 = record_rep_session(tmp_path)
    v1 = tmp_path / "session_v1.jsonl"
    make_v1_copy(v2, v1)

    header, frames, end, skipped = plot.load_session(v1)
    assert header["format_version"] == 1 and skipped == 0 and end is not None and len(frames) == int(5.0 * PLOT_FPS)
    assert plot.load_events(v1) == []
    series = plot.build_series(header, frames)
    assert all(state is None for state in series["rep_state"])  # v1에는 RepTracker 상태가 없다
    assert np.nanmin(series["knee"]) == pytest.approx(106.7, abs=0.2)  # 기존 원자료는 그대로 복원된다

    out_dir = tmp_path / "plots_v1"
    assert plot.main(["--session", str(v1), "--out-dir", str(out_dir)]) == 0
    assert "events          :" not in capsys.readouterr().out
    assert (out_dir / "session_v1_timeline.png").stat().st_size > 10_000


def test_a_format_version_two_log_is_read_with_its_events_and_plotted(tmp_path, capsys) -> None:
    v2 = record_rep_session(tmp_path)
    header, frames, _, _ = plot.load_session(v2)
    events = plot.load_events(v2)
    assert header["format_version"] == 2 and {e["kind"] for e in events} >= {"lock", "rep_end"}
    series = plot.build_series(header, frames)
    assert {"WAITING_LOCK", "STANDING", "IN_REP"} <= set(series["rep_state"])

    out_dir = tmp_path / "plots_v2"
    assert plot.main(["--session", str(v2), "--out-dir", str(out_dir)]) == 0
    output = capsys.readouterr().out
    assert "events          : {" in output
    assert "lock      acquired" in output and "rep_end" in output and "hip " in output and "(>= 0.2)" in output  # 측정값과 기준값이 같이 나온다
    assert (out_dir / f"{v2.stem}_timeline.png").stat().st_size > 10_000


def test_format_events_prints_every_kind_with_the_values_that_explain_it() -> None:
    lines = plot.format_events(
        [
            {"kind": "lock", "event": "released_view", "t": 9.0, "detail": {"reason": "non_side", "seconds": 0.5}},
            {"kind": "rep_merge_suspect", "t": 5.0, "peak_knee": 150.0, "peak_shortfall": 10.0, "min_knee": 70.0, "standing_angle": 160.0},
            {"kind": "rep_end", "t": 4.0, "counted": False, "reasons": ["other_exercise"], "timeout": False, "t_start": 1.0, "t_end": 4.0,
             "total_seconds": 3.0, "hip_drop_norm": 0.5, "ankle_gap_norm": 0.0, "other_exercise_ratio": 0.45, "min_knee": 70.0,
             "merge_suspects": 0, "limits": {"min_seconds": 1.0, "min_hip_drop": 0.2, "max_ankle_gap": 0.25, "other_max_ratio": 0.4}},
        ]
    )
    assert [line.split("]")[1].split()[0] for line in lines] == ["rep_end", "MERGE?", "lock"]  # 시간 순서
    assert "REJECTED(other_exercise)" in lines[0] and "ml 0.45 (<= 0.4)" in lines[0]
    assert "rose to 150.0" in lines[1] and "short by 10.0" in lines[1]
    assert "released_view (reason=non_side, seconds=0.5)" in lines[2]


def test_an_unknown_format_version_is_rejected_instead_of_misread(tmp_path) -> None:
    v2 = record_rep_session(tmp_path)
    future = tmp_path / "future.jsonl"
    text = v2.read_text(encoding="utf-8").replace('"format_version":2', '"format_version":3', 1)
    future.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="format_version"):
        plot.load_session(future)


def test_lock_release_spans_are_paired_with_the_next_acquire_and_keep_the_reason() -> None:
    events = [
        {"kind": "lock", "event": "acquired", "t": 1.0, "detail": None},
        {"kind": "lock", "event": "released_view", "t": 10.0, "detail": {"reason": "non_side", "seconds": 0.5}},
        {"kind": "lock", "event": "acquired", "t": 11.2, "detail": {"unlocked_seconds": 1.2, "previous_release_reason": "non_side"}},
        {"kind": "lock", "event": "released_missing", "t": 20.0, "detail": {"reason": "person_missing", "seconds": 2.1}},
    ]
    spans = plot._lock_release_spans(events, end_time=30.0)
    assert spans == [(10.0, 11.2, "non_side 0.5s"), (20.0, 30.0, "person_missing 2.1s")]  # 마지막은 끝까지 열려 있다
