"""카메라 없이 로깅 파이프라인(임시 잠금 정책, JSONL 기록, CLI, 기본 꺼짐)을 검증한다.

합성 자세 생성 함수는 test_pose_geometry.py의 것을 재사용한다(tests 폴더는 패키지가 아니므로
pytest가 폴더를 sys.path에 넣어 주는 방식에 기댄다).
"""

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config.settings as settings
from desktop_launcher.launcher import LauncherConfig, LauncherError, build_ai_command, parse_launch_url
from src.geometry_tracker import GeometryTracker
import src.main as main_module
from src.main import parse_arguments, start_sequence_recording
from src.sequence_logger import (
    FACE_LANDMARK_COUNT,
    SequenceLogger,
    SequenceRecorder,
    build_frame_record,
    build_labels,
    session_metadata,
    settings_snapshot,
)
from test_pose_geometry import (
    FRAME,
    LEFT_LEG_HIDDEN,
    PERSON,
    RIGHT_LEG_HIDDEN,
    SIDE_POSE,
    CROP_A,
    build_landmarks,
    build_world,
)


# 서 있는 자세(무릎 180도, 오른쪽을 봄)와 그 crop/bbox. 머리 위쪽 여유를 두어 전신이 프레임 안에 있다.
STANDING_POSE = {
    "nose": (210, 45),
    "left_shoulder": (200, 70),
    "right_shoulder": (203, 71),
    "left_hip": (200, 150),
    "right_hip": (203, 151),
    "left_knee": (200, 230),
    "right_knee": (203, 231),
    "left_ankle": (200, 310),
    "right_ankle": (203, 311),
    "left_heel": (190, 318),
    "right_heel": (193, 319),
    "left_foot_index": (260, 318),
    "right_foot_index": (263, 319),
}
CROP_S = (40, 20, 360, 400)
PERSON_S = (90, 30, 310, 330)
# 오른쪽 다리가 더 잘 보이지만 왼쪽 다리도 전신 유효 기준(0.5)은 넘는다.
RIGHT_LEG_VISIBLE = {
    **{f"right_{j}": 1.0 for j in ("hip", "knee", "ankle")},
    **{f"left_{j}": 0.6 for j in ("hip", "knee", "ankle")},
}


def frame_arguments(pose, crop, person, visibility=None, world=None):
    visibility = {"nose": 0.99, **RIGHT_LEG_HIDDEN, **(visibility or {})}
    return {
        "landmarks": build_landmarks(pose, crop, visibility),
        "crop_bbox": crop,
        "person_bbox": person,
        "frame_size": FRAME,
        "world_landmarks": world,
    }


def standing(tracker, timestamp, **kwargs):
    return tracker.update(timestamp=timestamp, **frame_arguments(STANDING_POSE, CROP_S, PERSON_S, **kwargs))


def squatting(tracker, timestamp, **kwargs):
    return tracker.update(timestamp=timestamp, **frame_arguments(SIDE_POSE, CROP_A, PERSON, **kwargs))


def smoothing_state(stable="stand"):
    return {
        "stable_label": stable,
        "stable_confidence": 0.93,
        "candidate_label": None,
        "candidate_count": 0,
        "required_count": 0,
        "missing_count": 0,
    }


def read_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def wait_until(condition, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return condition()


# ---------------------------------------------------------------- BodyLock 정책 (GeometryTracker)

# 정면을 향해 서 있는 자세: 어깨 간격이 몸통 길이와 같아 측면으로 판정되지 않는다(무릎·발 위치는 STANDING_POSE와 같다).
FRONT_STANDING_POSE = {**STANDING_POSE, "left_shoulder": (160, 70), "right_shoulder": (240, 71)}


def front_standing(tracker, timestamp, **kwargs):
    return tracker.update(timestamp=timestamp, **frame_arguments(FRONT_STANDING_POSE, CROP_S, PERSON_S, **kwargs))


def locked_tracker(**kwargs) -> GeometryTracker:
    """측면으로 서서 잠금이 걸린 추적기(잠금은 0.5초 연속 측면 판정 뒤에 걸린다)."""
    tracker = GeometryTracker(**kwargs)
    standing(tracker, 0.0)
    assert standing(tracker, 0.5).lock.event == "acquired"
    return tracker


def test_lock_is_acquired_only_after_the_side_view_holds() -> None:
    tracker = GeometryTracker()
    first = standing(tracker, 0.0)

    assert first.standing is True
    assert first.knee_angle_smoothed == pytest.approx(180.0, abs=1e-6)
    assert first.lock.locked is False  # 측면 판정이 아직 0.5초 이어지지 않았다
    assert standing(tracker, 0.45).lock.locked is False

    tracked = standing(tracker, 0.5)
    assert tracked.lock.locked is True
    assert (tracked.lock.leg, tracked.lock.facing) == ("left", "right")
    assert tracked.lock.event == "acquired"
    assert tracked.lock.view.is_side

    assert standing(tracker, 0.5 + 1 / 30).lock.event is None  # 같은 값으로 갱신되면 이벤트 없음


def test_a_front_view_is_never_locked() -> None:
    tracker = GeometryTracker()
    for step in range(60):  # 2초 동안 정면으로 서 있다
        tracked = front_standing(tracker, step / 30)
        assert tracked.geometry_now.view.is_side is False
        assert tracked.standing is True
        assert tracked.lock.locked is False


def test_a_side_view_that_flickers_does_not_accumulate_toward_the_lock() -> None:
    tracker = GeometryTracker()
    standing(tracker, 0.0)
    standing(tracker, 0.3)
    front_standing(tracker, 0.4)  # 측면 판정이 끊기면 연속 시간을 처음부터 센다
    assert standing(tracker, 0.55).lock.locked is False  # 0.0부터가 아니라 0.55에서 새로 시작
    assert standing(tracker, 1.05).lock.locked is True


def test_lock_is_released_when_a_standing_user_turns_away_long_enough() -> None:
    tracker = locked_tracker()
    assert front_standing(tracker, 1.0).lock.locked is True  # 비측면이 막 시작됨
    assert front_standing(tracker, 1.3).lock.locked is True  # 0.3초: 아직 유지
    released = front_standing(tracker, 1.45)  # 0.4초 이상 연속(1.4는 부동소수점 때문에 0.3999…초)
    assert released.lock.locked is False
    assert released.lock.event == "released_view"


def test_a_short_turn_does_not_release_the_lock() -> None:
    tracker = locked_tracker()
    front_standing(tracker, 1.0)
    front_standing(tracker, 1.3)
    tracked = standing(tracker, 1.35)  # 0.4초가 되기 전에 다시 측면
    assert tracked.lock.locked is True
    assert front_standing(tracker, 1.5).lock.locked is True  # 비측면 연속 시간은 다시 시작


def test_lock_leg_and_facing_are_not_updated_by_non_side_frames() -> None:
    tracker = locked_tracker()
    # 정면 프레임에서 오른쪽 다리가 더 잘 보여도(전신 유효) 잠근 다리·방향은 그대로다.
    tracked = front_standing(tracker, 1.0, visibility=RIGHT_LEG_VISIBLE)
    assert tracked.geometry_now.leg == "right"
    assert (tracked.lock.leg, tracked.lock.facing) == ("left", "right")
    assert tracked.lock.event is None


def test_lock_is_frozen_once_the_user_starts_descending() -> None:
    tracker = locked_tracker()

    # 내려가는 동안 오른쪽 다리가 더 잘 보이게 되어도 잠근 다리와 방향을 유지한다.
    tracked = squatting(tracker, 0.55, visibility=RIGHT_LEG_VISIBLE)
    assert tracked.knee_angle_smoothed < 160.0
    assert tracked.standing is False
    assert tracked.lock.event is None
    assert (tracked.lock.leg, tracked.lock.facing) == ("left", "right")
    assert tracked.geometry.leg == "left"  # 잠근 다리 기준
    assert tracked.geometry_now.leg == "right"  # 이 프레임만 보면 오른쪽 (정책 검증용으로 함께 남김)


def test_a_view_change_during_the_rep_does_not_release_the_lock() -> None:
    tracker = locked_tracker()
    squatting(tracker, 0.55)
    # 반복 중(STANDING이 아닐 때)에는 측면이 아닌 프레임이 길게 이어져도 풀지 않는다.
    for step in range(1, 40):
        tracked = tracker.update(
            timestamp=0.55 + step / 30,
            **frame_arguments({**SIDE_POSE, "left_shoulder": (160, 70), "right_shoulder": (240, 71)}, CROP_A, PERSON),
        )
        assert tracked.standing is False
        assert tracked.lock.locked is True


def test_lock_is_refreshed_on_the_next_side_standing_frame() -> None:
    tracker = locked_tracker()
    squatting(tracker, 0.55)

    # 다시 서면 그 프레임의 다리로 갱신한다(다음 반복의 시작).
    tracked = standing(tracker, 3.0, visibility=RIGHT_LEG_VISIBLE)
    assert tracked.standing is True
    assert tracked.lock.event == "changed"
    assert tracked.lock.leg == "right"


def test_smoothing_follows_timestamps_not_frame_count() -> None:
    fast, slow = GeometryTracker(), GeometryTracker()
    standing(fast, 0.0)
    standing(slow, 0.0)
    after_fast = squatting(fast, 0.033).knee_angle_smoothed  # 한 프레임(약 30fps) 뒤
    after_slow = squatting(slow, 1.0).knee_angle_smoothed  # 1초 뒤에는 원래 값(약 106.7도) 근처까지 따라온다
    assert after_slow < after_fast < 180.0
    assert after_fast - after_slow > 15.0  # 같은 입력이라도 경과 시간이 길수록 더 많이 따라온다
    assert after_slow == pytest.approx(106.7, abs=8.0)


def test_invalid_body_does_not_lock_or_smooth() -> None:
    tracker = GeometryTracker()
    tracked = None
    for step in range(30):
        tracked = tracker.update(
            timestamp=step / 30,
            **frame_arguments(STANDING_POSE, CROP_S, (90, 30, 310, 480)),  # bbox 하단이 프레임에 닿음
        )
    assert tracked.geometry.full_body.valid is False
    assert tracked.knee_angle_smoothed is None
    assert tracked.standing is False
    assert tracked.lock.locked is False


def test_lock_is_released_after_the_pose_is_missing_for_long_enough() -> None:
    tracker = locked_tracker(missing_release_seconds=2.0)

    assert tracker.update_missing(1.0).locked is True  # 1초: 아직 유지
    assert tracker.update_missing(2.5).locked is True  # 첫 놓침 후 1.5초
    released = tracker.update_missing(3.1)  # 첫 놓침(1.0) 후 2.1초
    assert released.locked is False
    assert released.event == "released_missing"

    # 평활화 상태도 초기화되어 다음 프레임은 그 값 그대로 시작한다.
    assert squatting(tracker, 4.0).knee_angle_smoothed == pytest.approx(
        squatting(GeometryTracker(), 0.0).knee_angle_smoothed, abs=1e-6
    )


def test_seeing_the_person_again_resets_the_missing_timer() -> None:
    tracker = locked_tracker(missing_release_seconds=2.0)
    tracker.update_missing(1.0)
    standing(tracker, 1.5)  # 다시 보임
    assert tracker.update_missing(3.0).locked is True  # 새로 시작한 놓침이라 1.5초 뒤까지 유지


def test_missing_frames_break_the_side_continuity_needed_for_the_lock() -> None:
    tracker = GeometryTracker()
    standing(tracker, 0.0)
    standing(tracker, 0.3)
    tracker.update_missing(0.4)
    assert standing(tracker, 0.55).lock.locked is False  # 끊겼으므로 0.55에서 새로 시작
    assert standing(tracker, 1.05).lock.locked is True


def test_reset_drops_the_lock_and_the_smoothing_state() -> None:
    tracker = locked_tracker()
    tracker.reset()
    tracked = standing(tracker, 2.0)
    assert tracked.lock.locked is False  # 측면 연속 시간도 처음부터
    assert tracked.knee_angle_smoothed == pytest.approx(180.0, abs=1e-6)


# ---------------------------------------------------------------- 기록 내용


def make_person(pose=STANDING_POSE, crop=CROP_S, person=PERSON_S, world=None, prediction=None):
    return {
        "bbox": person,
        "padded_bbox": crop,
        "person_confidence": 0.91234567,
        "landmarks": build_landmarks(pose, crop, {"nose": 0.99, **RIGHT_LEG_HIDDEN}),
        "world_landmarks": world,
        "prediction": prediction,
    }


def test_settings_snapshot_is_json_serializable_and_excludes_paths() -> None:
    snapshot = settings_snapshot()
    json.dumps(snapshot)
    for name in ("STANDING_KNEE_ANGLE", "MIN_LANDMARK_VISIBILITY", "SIDE_VIEW_MAX_SHOULDER_RATIO", "ONE_EURO_BETA"):
        assert snapshot[name] == getattr(settings, name)
    assert "LANDMARK_SEQUENCE_DIR" not in snapshot
    assert "MODEL_DIR" not in snapshot
    assert "POSE_STABLE_FRAMES" in snapshot  # dict 값은 포함


def test_session_metadata_validates_choices() -> None:
    assert session_metadata("shallow", "side", "메모") == {
        "intended_posture": "shallow",
        "camera_view": "side",
        "note": "메모",
    }
    assert session_metadata() == {"intended_posture": None, "camera_view": None, "note": None}
    with pytest.raises(ValueError):
        session_metadata(intended_posture="deep")
    with pytest.raises(ValueError):
        session_metadata(camera_view="back")


def test_frame_record_contains_everything_the_analysis_needs() -> None:
    world = build_world((0.0, 0.0, -0.1), (0.0, 0.0, 0.1))
    tracker = GeometryTracker()
    standing(tracker, 0.0, world=world)
    tracked = standing(tracker, 0.5, world=world)  # 측면 판정이 0.5초 이어져 잠금이 걸린 프레임
    labels = build_labels({"label": "stand", "confidence": 0.8765432}, smoothing_state("stand"), "STAND", 0.93)

    record = build_frame_record(
        t=1.23456789,
        t_logic=1.3,
        frame_size=FRAME,
        person_confidence=0.91234567,
        yolo_bbox=PERSON_S,
        crop_bbox=CROP_S,
        landmarks=build_landmarks(STANDING_POSE, CROP_S, {"nose": 0.99}),
        world_landmarks=world,
        tracked=tracked,
        lock=tracked.lock,
        labels=labels,
    )
    json.dumps(record, allow_nan=False)

    assert record["t"] == 1.23457 and record["t_logic"] == 1.3
    assert record["frame_size"] == [640, 480]
    assert record["yolo_bbox"] == list(PERSON_S) and record["crop_bbox"] == list(CROP_S)
    assert len(record["landmarks"]) == 33 and all(len(row) == 4 for row in record["landmarks"])
    assert len(record["world_landmarks"]) == 33
    assert record["geometry"]["knee"] == pytest.approx(180.0, abs=1e-4)
    assert set(record["geometry"]) >= {
        "leg", "facing", "knee", "torso", "shin", "torso_signed", "shin_signed", "knee_smoothed", "standing",
        "leg_now", "facing_now",
    }
    assert record["full_body"] == {"valid": True, "reasons": [], "notes": []}
    assert set(record["view"]) == {"shoulder_ratio", "hip_yaw_deg", "nose_visibility", "is_side", "reasons"}
    assert record["view"]["hip_yaw_deg"] == pytest.approx(90.0)
    assert record["lock"]["locked"] is True and record["lock"]["leg"] == "left" and record["lock"]["facing"] == "right"
    assert record["labels"]["raw"] == "stand" and record["labels"]["stable"] == "stand"
    assert record["labels"]["display"] == "STAND"


def test_frame_record_keeps_the_timeline_when_nobody_is_detected() -> None:
    tracker = GeometryTracker()
    labels = build_labels(None, {**smoothing_state(None), "missing_count": 4}, "ANALYZING", 0.0)
    record = build_frame_record(
        t=2.0, t_logic=2.0, frame_size=FRAME, person_confidence=None, yolo_bbox=None, crop_bbox=None,
        landmarks=None, world_landmarks=None, tracked=None, lock=tracker.update_missing(2.0), labels=labels,
    )
    json.dumps(record, allow_nan=False)
    assert record["person"] is False
    assert record["landmarks"] is None and record["geometry"] is None
    assert record["lock"]["locked"] is False
    assert record["labels"]["missing_count"] == 4


# ---------------------------------------------------------------- 파일 기록


def test_logger_writes_header_frames_and_end_in_one_file(tmp_path) -> None:
    logger = SequenceLogger(
        tmp_path,
        metadata=session_metadata("shallow", "side", "첫 세션"),
        runtime={"detector_backend": "PyTorch"},
        flush_interval=0.05,
    )
    path = logger.start()
    for index in range(5):
        logger.log_frame({"t": index / 30})
    logger.close()

    assert path.parent == tmp_path and path.name.startswith("session_") and path.name.endswith("_shallow_side.jsonl")
    records = read_records(path)
    header, frames, end = records[0], records[1:-1], records[-1]

    assert header["type"] == "session" and header["format_version"] == 2  # v2: rep 상태와 event 줄이 생겼다
    assert header["metadata"] == {"intended_posture": "shallow", "camera_view": "side", "note": "첫 세션"}
    assert header["settings"]["STANDING_KNEE_ANGLE"] == settings.STANDING_KNEE_ANGLE
    assert header["runtime"]["detector_backend"] == "PyTorch"
    assert header["started_at"]  # 기록 시작 시각(tz 포함 ISO)
    assert len(header["landmark_names"]) == 33 and header["landmark_names"][29] == "left_heel"

    assert [frame["i"] for frame in frames] == [1, 2, 3, 4, 5]
    assert all(frame["type"] == "frame" for frame in frames)
    assert end["type"] == "end" and end["frames_offered"] == 5 and end["frames_written"] == 5
    assert end["frames_dropped"] == 0 and end["write_error"] is None


def test_each_session_gets_its_own_file(tmp_path) -> None:
    paths = []
    for _ in range(3):
        logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
        paths.append(logger.start())
        logger.close()
    assert len(set(paths)) == 3
    assert len(list(tmp_path.glob("*.jsonl"))) == 3


def test_flushed_lines_survive_when_the_process_never_closes_the_logger(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    path = logger.start()
    for index in range(4):
        logger.log_frame({"t": index / 30})

    # close()를 호출하지 않은 채(비정상 종료와 같은 상황) 파일을 읽는다.
    assert wait_until(lambda: len(path.read_text(encoding="utf-8").splitlines()) >= 5)
    records = read_records(path)
    assert records[0]["type"] == "session"
    assert [record["i"] for record in records[1:]] == [1, 2, 3, 4]
    assert all(record["type"] != "end" for record in records)
    logger.close()


def test_logging_never_blocks_the_pipeline_and_accounts_for_every_frame(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), queue_size=1, flush_interval=0.05)
    path = logger.start()
    payload = {"t": 0.0, "landmarks": [[0.5, 0.5, 0.0, 1.0]] * 33}

    real_put = logger._queue.put
    blocking_calls = []

    def watched_put(item, block=True, timeout=None):
        if block:
            blocking_calls.append(item)  # 기다릴 수 있는 put
        return real_put(item, block, timeout)

    logger._queue.put = watched_put  # 실제 시간을 재는 대신, 기다릴 수 있는 호출을 쓰지 않는지로 확인한다
    for _ in range(2000):
        logger.log_frame(payload)  # 큐가 가득 차도 호출 쪽은 기다리지 않는다
    del logger._queue.put
    assert blocking_calls == []
    logger.close()

    end = read_records(path)[-1]
    assert end["frames_offered"] == 2000
    assert end["frames_written"] + end["frames_dropped"] + end["frames_invalid"] == 2000
    assert end["frames_dropped"] > 0  # 큐 크기 1이면 일부는 버려진다
    frames = read_records(path)[1:-1]
    assert len(frames) == end["frames_written"]
    indices = [frame["i"] for frame in frames]
    assert indices == sorted(indices)  # 버려진 프레임은 번호의 공백으로 드러난다


def test_an_unserializable_frame_is_skipped_without_stopping_the_log(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    path = logger.start()
    logger.log_frame({"t": float("nan")})  # JSON으로 쓸 수 없는 값
    logger.log_frame({"t": 1.0})
    logger.close()

    records = read_records(path)
    assert [record["i"] for record in records[1:-1]] == [2]
    assert records[-1]["frames_invalid"] == 1 and records[-1]["frames_written"] == 1


def test_a_write_failure_stops_logging_without_raising(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    logger.start()
    logger._file.close()  # 디스크 오류와 같은 상황

    logger.log_frame({"t": 0.0})
    assert wait_until(lambda: logger.write_error is not None)
    assert logger.log_frame({"t": 1.0}) is False  # 이후 프레임은 조용히 버려진다
    started = time.perf_counter()
    logger.close()  # 예외 없이, 오래 기다리지 않고 끝난다
    assert time.perf_counter() - started < 3.0
    assert logger.frames_dropped >= 1


def test_close_is_safe_to_call_twice_or_before_start(tmp_path) -> None:
    SequenceLogger(tmp_path, metadata=session_metadata()).close()
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    logger.start()
    logger.close()
    logger.close()
    assert logger.log_frame({"t": 0.0}) is False


# ---------------------------------------------------------------- 파이프라인 연결 (SequenceRecorder)


def test_recorder_logs_labels_lock_and_geometry_per_frame(tmp_path) -> None:
    base = 1000.0  # 가짜 시계
    logger = SequenceLogger(tmp_path, metadata=session_metadata("normal", "side"), flush_interval=0.05, clock=lambda: base)
    path = logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker())
    world = build_world((0.0, 0.0, -0.1), (0.0, 0.0, 0.1))

    # 사람이 0.5초 동안 서 있어서(라벨 stand) 잠금이 걸리고, 그 뒤 사람이 사라진다.
    for offset in (0.10, 0.35, 0.60):
        recorder.record(
            frame_size=FRAME,
            primary_person=make_person(world=world, prediction={"label": "stand", "confidence": 0.9}),
            smoothing_state=smoothing_state("stand"),
            display_pose="STAND",
            display_confidence=0.93,
            capture_time=base + offset,
            logic_time=base + offset + 0.02,
        )
    recorder.record(
        frame_size=FRAME,
        primary_person=None,
        smoothing_state={**smoothing_state(None), "missing_count": 1},
        display_pose="STAND",
        display_confidence=0.93,
        capture_time=base + 0.70,
        logic_time=base + 0.71,
    )
    recorder.close()

    records = read_records(path)[1:-1]
    first, _, locked, missing = [r for r in records if r["type"] == "frame"]  # 잠금 이벤트 줄(event)은 따로 본다
    assert [(r["kind"], r["event"]) for r in records if r["type"] == "event"] == [("lock", "acquired")]
    assert first["person"] is True and first["lock"]["locked"] is False  # 측면 판정이 0.5초 이어지기 전
    assert locked["lock"]["locked"] is True and locked["lock"]["event"] == "acquired"
    assert locked["lock"]["leg"] == "left" and locked["lock"]["facing"] == "right"
    assert first["geometry"]["knee"] == pytest.approx(180.0, abs=1e-4)
    assert first["labels"]["raw"] == "stand" and first["labels"]["stable"] == "stand"
    assert first["labels"]["display"] == "STAND"
    assert first["view"]["hip_yaw_deg"] == pytest.approx(90.0)
    assert 0 < first["t"] < first["t_logic"] < locked["t"]  # 같은 시간 기준(세션 시작 후 초)

    assert missing["person"] is False and missing["landmarks"] is None
    assert missing["labels"]["stable"] is None and missing["labels"]["missing_count"] == 1
    assert missing["lock"]["locked"] is True  # 2초 미만이라 잠금은 유지


def test_recorder_uses_the_geometry_it_is_given_instead_of_updating_the_tracker_again(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    path = logger.start()
    tracker = GeometryTracker()
    recorder = SequenceRecorder(logger, tracker)
    tracked = standing(tracker, 0.0)  # 호출하는 쪽이 이미 이 프레임을 계산했다

    recorder.record(
        frame_size=FRAME,
        primary_person=make_person(),
        smoothing_state=smoothing_state("stand"),
        display_pose="STAND",
        display_confidence=0.9,
        capture_time=time.perf_counter(),
        logic_time=time.perf_counter(),
        geometry=(tracked, tracked.lock),
    )
    recorder.close()

    # 주어진 값이 그대로 기록되었는지 본다(같은 프레임을 추적기에 다시 넣지 않는다).
    frame = read_records(path)[1]
    assert frame["geometry"]["knee_smoothed"] == pytest.approx(tracked.knee_angle_smoothed, abs=1e-4)
    assert frame["lock"]["locked"] is tracked.lock.locked


def test_recorder_keeps_the_original_stable_label_even_when_the_display_filters_it(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    path = logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker())

    recorder.record(
        frame_size=FRAME,
        primary_person=make_person(prediction={"label": "walk", "confidence": 0.7}),
        smoothing_state=smoothing_state("walk"),
        display_pose="STAND",  # 표시 필터는 walk를 직전 표시값(STAND)으로 대체한다
        display_confidence=0.91,
        capture_time=time.perf_counter(),
        logic_time=time.perf_counter(),
    )
    recorder.close()

    labels = read_records(path)[1]["labels"]
    assert labels["raw"] == "walk" and labels["stable"] == "walk" and labels["display"] == "STAND"


def test_recorder_swallows_errors_so_the_workout_continues(tmp_path, capsys) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker())
    broken_person = {**make_person(), "landmarks": ["not", "landmarks"]}

    for _ in range(3):
        recorder.record(
            frame_size=FRAME,
            primary_person=broken_person,
            smoothing_state=smoothing_state(),
            display_pose="STAND",
            display_confidence=0.9,
            capture_time=time.perf_counter(),
            logic_time=time.perf_counter(),
        )
    recorder.close()

    assert capsys.readouterr().out.count("Logging error ignored") == 1  # 한 번만 알린다


# ---------------------------------------------------------------- 기본 꺼짐과 CLI


def test_logging_is_off_by_default() -> None:
    assert settings.SEQUENCE_LOGGING_ENABLED is False
    arguments = parse_arguments([])
    assert arguments.log_sequence is False
    assert (arguments.session_posture, arguments.session_view, arguments.session_note) == (None, None, None)


def test_session_options_are_parsed_when_logging_is_enabled() -> None:
    arguments = parse_arguments(
        ["--log-sequence", "--session-posture", "heel_lift", "--session-view", "oblique", "--session-note", "2세트"]
    )
    assert arguments.log_sequence is True
    assert (arguments.session_posture, arguments.session_view, arguments.session_note) == (
        "heel_lift",
        "oblique",
        "2세트",
    )


@pytest.mark.parametrize(
    "argv",
    (
        ["--session-posture", "normal"],  # --log-sequence 없이
        ["--session-view", "side"],
        ["--log-sequence", "--session-posture", "deep"],  # 허용되지 않는 값
        ["--log-sequence", "--session-view", "back"],
    ),
)
def test_invalid_session_options_are_rejected(argv) -> None:
    with pytest.raises(SystemExit):
        parse_arguments(argv)


def test_launcher_cannot_turn_logging_on() -> None:
    config = LauncherConfig(
        ai_client_executable=Path("C:/FitRoute/ai_client/FitRouteAIClient.exe"),
        api_base_url="https://fitroute-api.onrender.com",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="publishable-key",
    )
    command = build_ai_command(config, parse_launch_url("fitroute://start?exercise=squat"), auto_start_session=True)
    assert not any(argument.startswith(("--log-sequence", "--session-")) for argument in command)
    with pytest.raises(LauncherError):
        parse_launch_url("fitroute://start?exercise=squat&log_sequence=1")  # URL로 옵션을 넘길 수 없다


def test_packaging_does_not_bundle_the_sequence_directory() -> None:
    packaged_files = [
        *PROJECT_ROOT.glob("packaging/**/*.spec"),
        *PROJECT_ROOT.glob("installer/*.iss"),
        *PROJECT_ROOT.glob("installer/*.json"),
    ]
    assert packaged_files  # 검사 대상이 실제로 있어야 의미가 있다
    for path in packaged_files:
        assert "landmark_sequences" not in path.read_text(encoding="utf-8", errors="ignore"), path


# ---------------------------------------------------------------- 얼굴 landmark (0~10번)

# 로그 어디에도 나타나면 안 되는 서로 구별되는 값(정규화·world 각각)
FACE_NORMALIZED = (0.31415, 0.27182, -0.1618)
FACE_WORLD = (0.07771, -0.08882, 0.09993)
FACE_ONLY_NOSE_VISIBILITY = 0.77


def landmarks_with_face_values():
    """얼굴 11개 landmark에 식별 가능한 좌표를 넣은 정규화 landmark 33개."""
    landmarks = build_landmarks(STANDING_POSE, CROP_S, {"nose": FACE_ONLY_NOSE_VISIBILITY})
    for index in range(FACE_LANDMARK_COUNT):
        x, y, z = FACE_NORMALIZED
        landmarks[index] = SimpleNamespace(x=x, y=y, z=z, visibility=FACE_ONLY_NOSE_VISIBILITY)
    return landmarks


def world_with_face_values():
    world = build_world((0.0, 0.0, -0.1), (0.0, 0.0, 0.1))
    for index in range(FACE_LANDMARK_COUNT):
        x, y, z = FACE_WORLD
        world[index] = SimpleNamespace(x=x, y=y, z=z, visibility=0.9)
    return world


def face_record(include_face_landmarks=None):
    landmarks = landmarks_with_face_values()
    world = world_with_face_values()
    tracked = GeometryTracker().update(
        landmarks,
        crop_bbox=CROP_S,
        person_bbox=PERSON_S,
        frame_size=FRAME,
        world_landmarks=world,
        timestamp=0.0,
    )
    extra = {} if include_face_landmarks is None else {"include_face_landmarks": include_face_landmarks}
    return build_frame_record(
        t=0.0, t_logic=0.0, frame_size=FRAME, person_confidence=0.9, yolo_bbox=PERSON_S, crop_bbox=CROP_S,
        landmarks=landmarks, world_landmarks=world, tracked=tracked, lock=tracked.lock,
        labels=build_labels(None, smoothing_state(), "STAND", 0.9), **extra,
    )


def test_face_landmark_count_is_the_first_eleven_points() -> None:
    from src.pose_classifier import LANDMARK_NAMES

    assert FACE_LANDMARK_COUNT == 11
    assert LANDMARK_NAMES[0] == "nose" and LANDMARK_NAMES[10] == "mouth_right"
    assert LANDMARK_NAMES[11] == "left_shoulder"  # 11번부터는 몸


def test_face_landmark_coordinates_are_not_in_the_record_by_default() -> None:
    record = face_record()

    assert len(record["landmarks"]) == 33 and len(record["world_landmarks"]) == 33  # 인덱스 정렬 유지
    for index in range(FACE_LANDMARK_COUNT):
        assert record["landmarks"][index][:3] == [None, None, None]
        assert record["world_landmarks"][index] == [None, None, None, None]
    # 코(0번)의 visibility만 정규화 landmark 행에 남는다. 다른 얼굴 점의 visibility는 남기지 않는다.
    assert record["landmarks"][0][3] == FACE_ONLY_NOSE_VISIBILITY
    for index in range(1, FACE_LANDMARK_COUNT):
        assert record["landmarks"][index] == [None, None, None, None]
    # 시점 신호 (c)용 코 visibility는 view에도 있다.
    assert record["view"]["nose_visibility"] == FACE_ONLY_NOSE_VISIBILITY


def test_body_landmarks_are_unchanged_when_the_face_is_removed() -> None:
    default, with_face = face_record(), face_record(include_face_landmarks=True)

    assert default["landmarks"][FACE_LANDMARK_COUNT:] == with_face["landmarks"][FACE_LANDMARK_COUNT:]
    assert default["world_landmarks"][FACE_LANDMARK_COUNT:] == with_face["world_landmarks"][FACE_LANDMARK_COUNT:]
    for index in range(FACE_LANDMARK_COUNT, 33):
        assert all(value is not None for value in default["landmarks"][index])  # 몸은 값이 있다
    # 분석에 쓰는 값(각도, 전신 유효, 시점 신호)도 얼굴 저장 여부와 무관하다.
    for key in ("geometry", "full_body", "view", "lock", "labels"):
        assert default[key] == with_face[key]


def test_face_landmark_coordinates_can_be_included_when_requested() -> None:
    record = face_record(include_face_landmarks=True)

    for index in range(FACE_LANDMARK_COUNT):
        assert record["landmarks"][index][:3] == [0.31415, 0.27182, -0.1618]
        assert record["world_landmarks"][index][:3] == [0.07771, -0.08882, 0.09993]


def test_face_values_never_reach_the_file_by_default(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    path = logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker())  # 기본 설정
    person = {
        "bbox": PERSON_S,
        "padded_bbox": CROP_S,
        "person_confidence": 0.9,
        "landmarks": landmarks_with_face_values(),
        "world_landmarks": world_with_face_values(),
        "prediction": {"label": "stand", "confidence": 0.9},
    }
    for index in range(3):
        recorder.record(
            frame_size=FRAME, primary_person=person, smoothing_state=smoothing_state(),
            display_pose="STAND", display_confidence=0.9, capture_time=time.perf_counter(), logic_time=time.perf_counter(),
        )
    recorder.close()

    text = path.read_text(encoding="utf-8")
    for value in (*FACE_NORMALIZED, *FACE_WORLD):
        assert f"{value}" not in text  # 파일 전체에서 얼굴 좌표 문자열이 없다
    frames = read_records(path)[1:-1]
    assert len(frames) == 3 and frames[0]["view"]["nose_visibility"] == FACE_ONLY_NOSE_VISIBILITY

    # 같은 입력을 옵션을 켜고 기록하면 파일에 나타난다(위 검사가 의미 있는지 확인).
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), options={"face_landmarks": True}, flush_interval=0.05)
    path_with_face = logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker(), include_face_landmarks=True)
    recorder.record(
        frame_size=FRAME, primary_person=person, smoothing_state=smoothing_state(),
        display_pose="STAND", display_confidence=0.9, capture_time=time.perf_counter(), logic_time=time.perf_counter(),
    )
    recorder.close()
    text_with_face = path_with_face.read_text(encoding="utf-8")
    assert "0.31415" in text_with_face and "0.07771" in text_with_face


def test_face_landmark_logging_is_off_by_default_in_settings_and_cli() -> None:
    assert settings.SEQUENCE_LOG_FACE_LANDMARKS is False
    assert settings_snapshot()["SEQUENCE_LOG_FACE_LANDMARKS"] is False
    assert parse_arguments([]).log_face_landmarks is False
    assert parse_arguments(["--log-sequence"]).log_face_landmarks is False
    assert parse_arguments(["--log-sequence", "--log-face-landmarks"]).log_face_landmarks is True


def test_face_landmark_option_requires_sequence_logging() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["--log-face-landmarks"])


@pytest.mark.parametrize("face_option", ([], ["--log-face-landmarks"]))
def test_main_wiring_passes_the_face_option_to_the_log(tmp_path, monkeypatch, face_option) -> None:
    """카메라 없이 main의 연결 함수만 실행해 옵션이 기록기와 헤더에 전달되는지 확인한다."""
    monkeypatch.setattr(main_module, "LANDMARK_SEQUENCE_DIR", tmp_path)
    arguments = parse_arguments(["--log-sequence", "--session-posture", "normal", "--session-view", "side", *face_option])
    detector = SimpleNamespace(backend="PyTorch")
    classifier = SimpleNamespace(classes=["squat", "stand"])

    recorder = start_sequence_recording(arguments, detector, classifier)
    recorder.close()

    expected = bool(face_option)
    assert recorder.include_face_landmarks is expected
    header = read_records(next(tmp_path.glob("*.jsonl")))[0]
    assert header["options"] == {"face_landmarks": expected}
    assert header["metadata"]["intended_posture"] == "normal" and header["metadata"]["camera_view"] == "side"
