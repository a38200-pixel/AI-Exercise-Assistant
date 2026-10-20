"""재생 도구(replay_flags, geometry_replay)가 실제 앱 경로와 같은 반복 판정을 내는지 합성 스쿼트로 비교한다.

실제 앱 경로 = GeometryTracker + track_primary_person + ExerciseCounter(RepTracker) + SequenceRecorder가 쓴 로그의 rep_end 이벤트.
replay_flags는 그 로그에서 뽑은 신호(평활 무릎각, 측면 판정, leg_now 등)를 BodyLockPolicy + RepTracker에 다시 넣는 자체 접착 코드를 쓰므로,
이 접착 코드가 실제 경로와 다르게 계산하면 여기서 드러난다. geometry_replay는 landmark에서 실제 코드 전체를 다시 돌린다.
(원본 로그는 저장소에 없다. 실제 로그 26개에서의 같은 비교는 scripts/analysis/replay_fidelity_check.py로 한다.)
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for extra in (PROJECT_ROOT / "scripts" / "analysis",):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import geometry_replay  # noqa: E402
import replay_flags  # noqa: E402
from src.exercise_counter import SQUAT_MODE, ExerciseCounter  # noqa: E402
from src.geometry_tracker import GeometryTracker  # noqa: E402
from src.rep_tracker import RepTracker, track_primary_person  # noqa: E402
from src.sequence_logger import SequenceLogger, SequenceRecorder, session_metadata  # noqa: E402
from test_pose_geometry import FRAME, build_world  # noqa: E402
from test_sequence_logger import STANDING_POSE, make_person, read_records, smoothing_state  # noqa: E402

FPS = 20
BASE = 1000.0  # 가짜 시계
# 최저점에서 각 landmark가 서 있는 자세에서 옮겨 가는 양(프레임 픽셀). 엉덩이는 뒤로·아래로, 무릎은 앞으로, 상체는 숙인다.
BOTTOM_SHIFT = {
    "nose": (-40, 55), "left_shoulder": (-40, 50), "right_shoulder": (-40, 50),
    "left_hip": (-55, 65), "right_hip": (-55, 65), "left_knee": (30, 5), "right_knee": (30, 5),
}


def pose_at(depth):
    return {
        name: (x + BOTTOM_SHIFT.get(name, (0, 0))[0] * depth, y + BOTTOM_SHIFT.get(name, (0, 0))[1] * depth)
        for name, (x, y) in STANDING_POSE.items()
    }


def depth_curve(seconds, hold=0.4, down=1.0, up=1.0, rest_after=1.2, rest_before=1.0):
    """서 있음 → 내려감 → 최저점 유지 → 올라옴 → 서 있음. (시각, 깊이 0~1) 목록."""
    total = rest_before + down + hold + up + rest_after
    points = []
    for index in range(int(total * FPS)):
        s = index / FPS
        if s < rest_before:
            d = 0.0
        elif s < rest_before + down:
            d = (s - rest_before) / down
        elif s < rest_before + down + hold:
            d = 1.0
        elif s < rest_before + down + hold + up:
            d = 1.0 - (s - rest_before - down - hold) / up
        else:
            d = 0.0
        points.append((seconds + s, d))
    return points


def record_session(tmp_path, curve, *, rep_options=None, label="squat"):
    """합성 시퀀스를 실제 앱 경로로 돌려 로그를 쓰고 그 경로를 돌려준다."""
    logger = SequenceLogger(tmp_path, metadata=session_metadata("normal", "side"), flush_interval=0.05, clock=lambda: BASE)
    path = logger.start()
    geometry_tracker = GeometryTracker()
    counter = ExerciseCounter(rep_tracker=RepTracker(**(rep_options or {})))
    counter.set_mode(SQUAT_MODE, 0.0)
    recorder = SequenceRecorder(logger, geometry_tracker)
    world = build_world((0.0, 0.0, -0.1), (0.0, 0.0, 0.1))
    for t, depth in curve:
        person = make_person(pose_at(depth), world=world, prediction={"label": label, "confidence": 0.9})
        tracked, lock, rep_frame = track_primary_person(geometry_tracker, person, FRAME, BASE + t)
        stable = "stand" if depth < 0.15 else label
        counter.update(stable, BASE + t, rep_frame)
        recorder.record(
            frame_size=FRAME, primary_person=person, smoothing_state=smoothing_state(stable), display_pose=stable.upper(),
            display_confidence=0.9, capture_time=BASE + t, logic_time=BASE + t, geometry=(tracked, lock),
            rep=counter.rep_diagnostics(),
        )
    recorder.close()
    return path


def two_squats():
    first = depth_curve(0.0, rest_after=0.0)
    return first + depth_curve(first[-1][0] + 1 / FPS, rest_before=0.3)


def key(row):
    return (round(row["t"], 1), row["counted"], tuple(sorted(row["reasons"])))


def rows_from_events(path):
    return [
        {"t": e["t_start"], "counted": e["counted"], "reasons": e["reasons"], "hip": e["hip_drop_norm"], "gap": e["ankle_gap_norm"],
         "bottom": e.get("ankle_gap_bottom_norm"), "shift": e.get("hip_shift_norm")}
        for e in read_records(path) if e["type"] == "event" and e.get("kind") == "rep_end"
    ]


def rows_from_results(results):
    def number(value):
        return None if value != value else round(float(value), 4)

    return [
        {"t": r.t_start, "counted": r.counted, "reasons": list(r.reasons), "hip": number(r.hip_drop_norm), "gap": number(r.ankle_gap_norm),
         "bottom": number(r.ankle_gap_bottom_norm), "shift": number(r.hip_shift_norm)}
        for r in results
    ]


def assert_same_reps(left, right):
    assert [key(r) for r in left] == [key(r) for r in right]
    for a, b in zip(left, right):
        for name in ("hip", "gap", "bottom", "shift"):
            assert a[name] == pytest.approx(b[name], abs=0.02), name


def test_the_synthetic_session_is_a_real_squat_that_the_app_path_counts(tmp_path) -> None:
    events = rows_from_events(record_session(tmp_path, two_squats()))
    assert [e["counted"] for e in events] == [True, True], events  # 합성 입력이 실제 경로에서 정상 반복 두 번으로 센다


def test_replay_flags_makes_the_same_rep_decisions_as_the_app_path(tmp_path) -> None:
    path = record_session(tmp_path, two_squats())
    live = rows_from_events(path)
    replayed = rows_from_results(replay_flags.replay(replay_flags.load_log(path), replay_flags.PRESETS["off"]).results)
    assert_same_reps(live, replayed)


def test_geometry_replay_makes_the_same_rep_decisions_as_the_app_path(tmp_path) -> None:
    path = record_session(tmp_path, two_squats())
    live = rows_from_events(path)
    frames, _ = geometry_replay.read_frames(path)
    replayed = rows_from_results(geometry_replay.replay(frames, {"tracker": {}, "rep": {}})["results"])
    assert_same_reps(live, replayed)


def test_the_rejection_reasons_also_match_when_the_session_has_a_rejected_rep(tmp_path) -> None:
    # 엉덩이가 가로로 크게 이동하는(자리를 뜨는) 동작을 흉내 내려고 상한을 낮춘다: 실제 경로에서 hip_shift로 탈락하고 재생도 같은 사유를 낸다.
    path = record_session(tmp_path, depth_curve(0.0), rep_options={"max_hip_shift": 0.05})
    live = rows_from_events(path)
    assert live and live[0]["reasons"] == ["hip_shift"]
    original = replay_flags.RepTracker
    replay_flags.RepTracker = lambda **kwargs: RepTracker(max_hip_shift=0.05, **kwargs)
    try:
        replayed = rows_from_results(replay_flags.replay(replay_flags.load_log(path), replay_flags.PRESETS["off"]).results)
    finally:
        replay_flags.RepTracker = original
    assert_same_reps(live, replayed)


def test_the_fixture_extraction_keeps_the_hip_x_the_hip_shift_condition_needs(tmp_path) -> None:
    payload = replay_flags.load_log(record_session(tmp_path, depth_curve(0.0)))
    assert payload["columns"][-1] == "hip_x"
    moved = [f["hip_x"] for f in payload["frames"] if f["hip_x"] is not None]
    assert max(moved) - min(moved) > 40  # 최저점에서 엉덩이가 55 px 뒤로 간다
