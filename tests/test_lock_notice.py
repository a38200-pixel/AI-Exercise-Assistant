"""BodyLock 안내 문구, BodyLockPolicy, USE_REP_TRACKER 스위치, 엉덩이 하강 임계값, 안내 화면 표시."""

import ast
import builtins
import json
from pathlib import Path

import numpy as np
import pytest

import config.settings as settings
import src.main as main_module
from src.exercise_counter import SQUAT_MODE, STRETCH_MODE, ExerciseCounter
from src.geometry_tracker import BodyLockPolicy
from src.geometry_tracker import GeometryTracker
from src.main import NOTICE_TEXT, compose_workout_ui, create_exercise_counter, run_geometry
from src.rep_tracker import (
    NOTICE_FULL_BODY_INVALID,
    NOTICE_NOT_SIDE,
    REASON_SHALLOW_HIP_DROP,
    RepFrame,
    RepTracker,
)
from src.sequence_logger import SequenceLogger, session_metadata, settings_snapshot
from test_rep_tracker import FPS, counted, rep_curve, run, simulate
from test_sequence_logger import make_person

DELAY = settings.LOCK_GUIDANCE_DELAY_SECONDS


# ---------------------------------------------------------------- 안내 사유와 시점 (RepTracker.notice)


def unlocked_frame(t, *, side_now=False, body_valid=True, present=True):
    if not present:
        return RepFrame.missing(t)
    return RepFrame(t, True, 175.0, False, None, None, None, None, None, side_now, body_valid)


def feed(tracker, start, seconds, **kwargs):
    for index in range(int(seconds * FPS) + 1):
        tracker.update(unlocked_frame(start + index / FPS, **kwargs), "stand")


def test_the_default_delay_is_two_seconds() -> None:
    assert settings.LOCK_GUIDANCE_DELAY_SECONDS == 2.0


def test_no_notice_until_the_lock_has_been_missing_for_the_delay() -> None:
    tracker = RepTracker()
    feed(tracker, 0.0, DELAY - 0.1, side_now=False)
    assert tracker.notice is None  # 아직 지연 시간 전
    feed(tracker, DELAY - 0.1 + 1 / FPS, 0.3, side_now=False)
    assert tracker.notice == NOTICE_NOT_SIDE


def test_a_user_who_is_not_facing_sideways_gets_the_not_side_notice() -> None:
    tracker = RepTracker()
    feed(tracker, 0.0, 3.0, side_now=False, body_valid=True)
    assert tracker.notice == NOTICE_NOT_SIDE


def test_an_invalid_full_body_gets_the_full_body_notice_even_if_the_view_is_not_side() -> None:
    tracker = RepTracker()
    feed(tracker, 0.0, 3.0, side_now=False, body_valid=False)
    assert tracker.notice == NOTICE_FULL_BODY_INVALID  # 전신이 안 보이면 시점 판정을 믿을 수 없으므로 이 사유가 먼저다


def test_the_most_common_recent_reason_wins() -> None:
    tracker = RepTracker()
    feed(tracker, 0.0, 1.0, side_now=False, body_valid=False)  # 처음 1초는 발이 안 보임
    feed(tracker, 1.0 + 1 / FPS, 3.0, side_now=False, body_valid=True)  # 그 뒤 3초는 정면
    assert tracker.notice == NOTICE_NOT_SIDE  # 최근 2초는 모두 정면


def test_a_side_user_who_is_simply_waiting_for_the_lock_gets_no_notice() -> None:
    tracker = RepTracker()
    feed(tracker, 0.0, 5.0, side_now=True, body_valid=True)  # 측면이고 전신이 보이는데 아직 잠기지 않음
    assert tracker.notice is None


def test_the_notice_is_cleared_as_soon_as_the_lock_is_held_and_restarts_after_it_is_lost() -> None:
    tracker = RepTracker()
    feed(tracker, 0.0, 3.0, side_now=False)
    assert tracker.notice == NOTICE_NOT_SIDE

    tracker.update(RepFrame(3.1, True, 175.0, True, "left", "right", 0.0, 0.0, None, True, True), "stand")
    assert tracker.notice is None  # 잠기자마자 지운다

    feed(tracker, 3.2, 1.5, side_now=False)  # 잠금을 잃었다. 지연 시간을 처음부터 센다.
    assert tracker.notice is None
    feed(tracker, 4.8, 1.0, side_now=False)
    assert tracker.notice == NOTICE_NOT_SIDE


def test_an_empty_scene_gives_no_notice_and_leaving_for_a_while_restarts_the_count() -> None:
    tracker = RepTracker()
    for index in range(int(10 * FPS)):
        tracker.update(unlocked_frame(index / FPS, present=False), None)
    assert tracker.notice is None  # 사람이 없으면 안내할 사유가 없다

    tracker = RepTracker()
    feed(tracker, 0.0, 1.5, side_now=False)
    for index in range(int(3 * FPS)):  # 3초 동안 자리를 떠남
        tracker.update(unlocked_frame(1.6 + index / FPS, present=False), None)
    feed(tracker, 4.7, 1.5, side_now=False)  # 돌아와서 1.5초
    assert tracker.notice is None  # 떠나기 전 1.5초와 합쳐 3초가 아니라 처음부터 센다


def test_the_delay_can_be_configured_and_reset_clears_the_notice() -> None:
    tracker = RepTracker(notice_delay_seconds=0.5)
    feed(tracker, 0.0, 0.8, side_now=False)
    assert tracker.notice == NOTICE_NOT_SIDE
    tracker.reset()
    assert tracker.notice is None


def test_status_shows_the_notice_only_in_squat_mode() -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    for index in range(int(3 * FPS)):
        frame = unlocked_frame(index / FPS, side_now=False)
        counter.update("stand", frame.timestamp, frame)
    assert counter.get_status(3.0)["rep_notice"] == NOTICE_NOT_SIDE

    counter.set_mode(STRETCH_MODE, 3.0)  # 모드를 바꾸면 RepTracker도 초기화된다
    assert counter.get_status(3.0)["rep_notice"] is None
    assert ExerciseCounter().get_status(0.0)["rep_notice"] is None  # RepTracker 없이는 안내 없음


# ---------------------------------------------------------------- 실측 fixture: 정면·사선은 문구, 측면은 잠금 후 문구 없음


@pytest.mark.parametrize("session", ["7", "6"], ids=["front", "oblique"])
def test_front_and_oblique_sessions_show_the_notice_and_never_count(session) -> None:
    payload, results, timeline, events = simulate(session)
    assert payload["actual_squats"] == 5
    assert counted(results) == []  # 측면 전용: 5회를 해도 세지 않는다

    exercise = [(locked, notice) for t, locked, notice in timeline if 22.0 <= t <= 40.0]  # 두 세션 모두 반복 구간
    assert exercise and all(not locked and notice == NOTICE_NOT_SIDE for locked, notice in exercise)

    first_present = next(row[0] for row in payload["rows"] if row[1])
    first_notice = next(t for t, locked, notice in timeline if notice)
    assert first_notice - first_present >= DELAY - 0.1  # 지연 시간 전에는 나오지 않는다
    if session == "7":
        assert not any(decision == "acquire" for _, decision in events)  # 정면은 한 번도 잠기지 않는다


@pytest.mark.parametrize("session", ["1", "2", "3", "4", "5"])
def test_side_sessions_lose_the_notice_once_the_lock_is_held(session) -> None:
    _, _, timeline, events = simulate(session)
    first_lock = next(t for t, locked, notice in timeline if locked)
    assert any(notice for t, locked, notice in timeline if t < first_lock)  # 자리 잡는 동안에는 안내가 떴다
    assert all(notice is None for t, locked, notice in timeline if locked)  # 잠겨 있는 동안은 항상 없다
    first_release = next((t for t, decision in events if decision != "acquire"), float("inf"))
    held = [(t, notice) for t, locked, notice in timeline if first_lock <= t < first_release]
    assert held and all(notice is None for _, notice in held)


# ---------------------------------------------------------------- BodyLockPolicy (신호만 받는다)


def policy_steps(policy, start, seconds, **kwargs):
    decisions = []
    for index in range(int(seconds * FPS) + 1):
        decisions.append(policy.step(start + index / FPS, **kwargs))
    return decisions


def test_policy_acquires_only_after_half_a_second_of_side_standing() -> None:
    policy = BodyLockPolicy()
    assert "acquire" not in policy_steps(policy, 0.0, 0.45, standing=True, side_now=True, lockable=True)
    assert policy.locked is False
    assert policy.step(0.5, standing=True, side_now=True, lockable=True) == "acquire"
    assert policy.locked is True


@pytest.mark.parametrize(
    "signals",
    [
        {"standing": False, "side_now": True, "lockable": True},  # 서 있지 않음
        {"standing": True, "side_now": False, "lockable": True},  # 측면 아님
        {"standing": True, "side_now": True, "lockable": False},  # 전신 무효 또는 facing 불명
    ],
    ids=["not-standing", "not-side", "not-lockable"],
)
def test_policy_never_acquires_unless_every_condition_holds(signals) -> None:
    policy = BodyLockPolicy()
    assert "acquire" not in policy_steps(policy, 0.0, 3.0, **signals)
    assert policy.locked is False


def test_policy_refreshes_while_standing_on_side_frames_and_ignores_the_rep() -> None:
    policy = BodyLockPolicy()
    policy_steps(policy, 0.0, 0.6, standing=True, side_now=True, lockable=True)
    assert policy.step(1.0, standing=True, side_now=True, lockable=True) == "refresh"
    assert policy.step(1.1, standing=True, side_now=False, lockable=True) is None  # 비측면 프레임은 갱신하지 않는다
    assert policy.step(1.2, standing=False, side_now=False, lockable=True) is None  # 반복 중
    for index in range(60):  # 반복 중에는 비측면이 아무리 길어도 풀지 않는다
        assert policy.step(1.3 + index / FPS, standing=False, side_now=False, lockable=True) is None
    assert policy.locked is True


def test_policy_releases_after_the_non_side_run_while_standing() -> None:
    policy = BodyLockPolicy()
    policy_steps(policy, 0.0, 0.6, standing=True, side_now=True, lockable=True)
    assert policy.step(1.0, standing=True, side_now=False, lockable=True) is None
    assert policy.step(1.3, standing=True, side_now=False, lockable=True) is None
    assert policy.step(1.45, standing=True, side_now=False, lockable=True) == "release_view"
    assert policy.locked is False


def test_policy_releases_when_the_person_is_missing_for_long_enough_and_missing_breaks_continuity() -> None:
    policy = BodyLockPolicy()
    policy_steps(policy, 0.0, 0.6, standing=True, side_now=True, lockable=True)
    assert policy.missing(1.0) is None
    assert policy.missing(2.9) is None
    assert policy.missing(3.1) == "release_missing"
    assert policy.locked is False

    policy = BodyLockPolicy()
    policy.step(0.0, standing=True, side_now=True, lockable=True)
    policy.step(0.3, standing=True, side_now=True, lockable=True)
    policy.missing(0.4)  # 연속성이 끊긴다
    assert policy.step(0.55, standing=True, side_now=True, lockable=True) is None  # 0.0부터가 아니라 새로 센다
    assert policy.step(1.05, standing=True, side_now=True, lockable=True) == "acquire"


# ---------------------------------------------------------------- 엉덩이 하강 임계값 0.20


def test_the_hip_drop_threshold_is_point_two() -> None:
    assert settings.REP_MIN_HIP_DROP == pytest.approx(0.20)


def test_a_rep_shallower_than_the_half_squats_of_the_field_test_is_still_counted() -> None:
    # 현장 실측에서 가장 얕은 정상 반복의 엉덩이 하강은 0.33(무릎 약 100도). 0.22면 그보다 훨씬 얕은 반복이다.
    results = run(RepTracker(), rep_curve(bottom=125.0, hip_drop=0.22))
    assert len(results) == 1 and results[0].counted
    assert results[0].hip_drop_norm == pytest.approx(0.22, abs=0.03)


def test_a_rep_with_barely_any_hip_drop_is_still_rejected() -> None:
    results = run(RepTracker(), rep_curve(bottom=125.0, hip_drop=0.15))
    assert results[0].reasons == (REASON_SHALLOW_HIP_DROP,)


# ---------------------------------------------------------------- USE_REP_TRACKER 스위치


def test_the_rep_tracker_is_on_by_default() -> None:
    # 실행 중 값이 아니라 settings.py에 적힌 기본값을 본다(스위치를 바꿔 돌리는 테스트 실행에서도 의미가 같다).
    tree = ast.parse(Path(settings.__file__).read_text(encoding="utf-8"))
    values = [
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "USE_REP_TRACKER" for t in node.targets)
    ]
    assert values == [True]


def test_the_switch_chooses_between_the_rep_tracker_and_the_v01x_label_counter(monkeypatch) -> None:
    monkeypatch.setattr(settings, "USE_REP_TRACKER", True)
    assert create_exercise_counter().uses_rep_tracker is True

    monkeypatch.setattr(settings, "USE_REP_TRACKER", False)
    assert create_exercise_counter().uses_rep_tracker is False


def test_with_the_switch_off_squats_are_counted_by_labels_like_v01x(monkeypatch) -> None:
    monkeypatch.setattr(settings, "USE_REP_TRACKER", False)
    counter = create_exercise_counter()
    counter.set_mode(SQUAT_MODE, 0.0)
    for label in ("stand", "squat", "stand"):
        counter.update(label, 1.0)  # rep_frame 없이 라벨만: v0.1.x 방식
    assert counter.squat_count == 1
    status = counter.get_status(1.0)
    assert status["state"] == "WAITING_SQUAT" and status["rep_guidance"] is None and status["rep_notice"] is None


def test_with_the_switch_on_labels_alone_do_not_count(monkeypatch) -> None:
    monkeypatch.setattr(settings, "USE_REP_TRACKER", True)
    counter = create_exercise_counter()
    counter.set_mode(SQUAT_MODE, 0.0)
    for label in ("stand", "squat", "stand"):
        counter.update(label, 1.0)
    assert counter.squat_count == 0


def test_the_switch_and_the_rep_constants_are_in_the_logging_snapshot_and_header(tmp_path) -> None:
    snapshot = settings_snapshot()
    expected = {
        "USE_REP_TRACKER": settings.USE_REP_TRACKER, "LOCK_GUIDANCE_DELAY_SECONDS": 2.0, "REP_MIN_HIP_DROP": 0.20,
        "REP_MIN_SECONDS": 1.0, "REP_MAX_ANKLE_GAP": 0.25, "REP_OTHER_EXERCISE_MAX_RATIO": 0.40,
        "BODY_LOCK_ACQUIRE_SIDE_SECONDS": 0.5, "BODY_LOCK_RELEASE_NONSIDE_SECONDS": 0.4,
    }
    for name, value in expected.items():
        assert snapshot[name] == value

    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
    path = logger.start()
    logger.close()
    header = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert header["settings"]["USE_REP_TRACKER"] is settings.USE_REP_TRACKER  # 실행 중 스위치 값이 헤더에 남는다
    assert header["settings"]["REP_MIN_HIP_DROP"] == pytest.approx(0.20)


# ---------------------------------------------------------------- 안내 화면 표시


def hud(notice):
    frame = np.full((480, 640, 3), 90, dtype=np.uint8)
    status = {"mode": "squat", "squat_count": 3}
    session = {"status": "ACTIVE", "elapsed_seconds": 65}
    return compose_workout_ui(frame, status, session, "READY", "STAND", 0.9, True, notice)


def changed_region(a, b):
    rows, cols = np.where(np.any(a != b, axis=2))
    return rows.min(), rows.max(), cols.min(), cols.max()


@pytest.mark.parametrize("notice", [NOTICE_NOT_SIDE, NOTICE_FULL_BODY_INVALID])
def test_the_notice_is_drawn_only_in_a_band_at_the_bottom_of_the_video(notice) -> None:
    plain, noticed = hud(None), hud(notice)
    top, bottom, left, right = changed_region(plain, noticed)
    header_height = 64
    assert top >= header_height + 480 - 70 and bottom <= header_height + 480  # 영상 아래쪽 띠 안
    assert left >= 12 and right <= 640 - 12  # 오른쪽 패널·카운트는 건드리지 않는다


def test_an_unknown_notice_code_draws_nothing() -> None:
    assert np.array_equal(hud(None), hud("unknown"))


def test_without_a_korean_font_the_notice_falls_back_to_english(monkeypatch) -> None:
    korean = hud(NOTICE_NOT_SIDE)
    monkeypatch.setattr(main_module, "_korean_font", lambda *args, **kwargs: None)
    english = hud(NOTICE_NOT_SIDE)
    assert not np.array_equal(english, hud(None))  # 폰트가 없어도 안내는 나온다
    assert not np.array_equal(english, korean)  # 한글 렌더링과는 다른 그림(영어 문구)
    assert NOTICE_TEXT[NOTICE_NOT_SIDE] == ("카메라 쪽으로 옆모습이 보이게 서주세요", "TURN SIDEWAYS TO THE CAMERA")
    assert NOTICE_TEXT[NOTICE_FULL_BODY_INVALID] == ("발끝까지 화면에 들어오게 서주세요", "STAND SO YOUR FEET ARE IN VIEW")


# ---------------------------------------------------------------- 기하 분석을 돌릴지(run_geometry)와 스위치


def squat_counter(use_rep_tracker, mode=SQUAT_MODE):
    counter = ExerciseCounter(rep_tracker=RepTracker() if use_rep_tracker else None)
    counter.set_mode(mode, 0.0)
    return counter


def geometry_call(counter, tracker, *, recording=False, was_active=False, timestamp=0.0):
    return run_geometry(counter, tracker, make_person(), (640, 480), timestamp, recording=recording, was_active=was_active)


def test_geometry_runs_in_squat_mode_when_the_rep_tracker_is_used() -> None:
    active, geometry, rep_frame = geometry_call(squat_counter(True), GeometryTracker())
    assert active is True and geometry is not None and rep_frame.present


def test_geometry_does_not_run_in_other_modes_or_when_the_switch_is_off() -> None:
    for counter in (squat_counter(True, STRETCH_MODE), squat_counter(False)):
        active, geometry, rep_frame = geometry_call(counter, GeometryTracker())
        assert (active, geometry, rep_frame) == (False, None, None)  # v0.1.x와 같이 기하 분석 비용이 없다


def test_logging_alone_keeps_the_geometry_running_even_with_the_switch_off() -> None:
    active, geometry, _ = geometry_call(squat_counter(False), GeometryTracker(), recording=True)
    assert active is True and geometry is not None  # 로그에는 계속 잠금·각도를 남긴다


def test_stale_lock_is_dropped_when_the_geometry_turns_back_on() -> None:
    counter, tracker = squat_counter(True), GeometryTracker()
    geometry_call(counter, tracker, timestamp=0.0)
    _, geometry, _ = geometry_call(counter, tracker, was_active=True, timestamp=0.6)
    assert geometry[1].locked is True  # 0.5초 측면 서 있음으로 잠김

    counter.set_mode(STRETCH_MODE, 1.0)
    assert geometry_call(counter, tracker, was_active=True, timestamp=1.1)[0] is False
    counter.set_mode(SQUAT_MODE, 2.0)
    _, geometry, _ = geometry_call(counter, tracker, was_active=False, timestamp=2.0)  # 다시 켜짐: reset
    assert geometry[1].locked is False  # 오래된 잠금이 남지 않고 0.5초를 처음부터 센다


def test_the_whole_per_frame_path_counts_a_rep_with_the_switch_on_and_not_off() -> None:
    # main의 프레임 처리 순서(run_geometry → ExerciseCounter.update)를 두 설정에서 같은 입력으로 돌린다.
    for use_rep_tracker in (True, False):
        counter, tracker, was_active = squat_counter(use_rep_tracker), GeometryTracker(), False
        for index in range(int(6 * FPS)):
            t = index / FPS
            second = t % 6.0
            label = "stand" if second < 1.5 or second > 4.5 else "squat"
            was_active, _, rep_frame = run_geometry(
                counter, tracker, make_person(), (640, 480), t, recording=False, was_active=was_active
            )
            counter.update(label, t, rep_frame)
        # 같은 자세 사진을 계속 넣었으므로 무릎각은 그대로 180도다: RepTracker는 반복을 못 보고, v0.1.x는 라벨로 센다.
        assert counter.squat_count == (0 if use_rep_tracker else 1)


# ---------------------------------------------------------------- 렌더링 캐시와 Pillow·폰트 대체


@pytest.fixture
def fresh_font_caches():
    """폰트·안내 레이어 캐시를 비워 시작하고, 테스트가 만든 상태가 다른 테스트로 새지 않게 끝에서도 비운다."""
    main_module._korean_font.cache_clear()
    main_module._notice_text_layer.cache_clear()
    yield
    main_module._korean_font.cache_clear()
    main_module._notice_text_layer.cache_clear()


def test_the_notice_text_is_drawn_once_and_only_composited_on_the_next_frames(fresh_font_caches) -> None:
    for _ in range(5):
        hud(NOTICE_NOT_SIDE)
    info = main_module._notice_text_layer.cache_info()
    assert info.misses == 1 and info.hits == 4  # 문구는 한 번만 그리고 나머지 프레임은 합성만 한다
    hud(NOTICE_FULL_BODY_INVALID)  # 문구가 바뀌면 그때 다시 그린다
    assert main_module._notice_text_layer.cache_info().misses == 2
    hud(NOTICE_NOT_SIDE)
    assert main_module._notice_text_layer.cache_info().misses == 2  # 이미 그려 둔 문구는 다시 그리지 않는다


def test_nothing_is_rendered_while_there_is_no_notice(fresh_font_caches) -> None:
    hud(None)
    info = main_module._notice_text_layer.cache_info()
    assert info.hits == 0 and info.misses == 0


def test_the_cached_layer_gives_the_same_picture_as_drawing_the_text_every_frame(fresh_font_caches) -> None:
    from scripts.analysis.notice_render_benchmark import legacy_draw_notice_band

    frame = np.random.default_rng(1).integers(30, 220, size=(480, 640, 3), dtype=np.uint8)
    status = {"mode": "squat", "squat_count": 3}
    session = {"status": "ACTIVE", "elapsed_seconds": 65}
    cached = compose_workout_ui(frame, status, session, "READY", "STAND", 0.9, True, NOTICE_NOT_SIDE)
    current_band = main_module._draw_notice_band
    main_module._draw_notice_band = legacy_draw_notice_band
    try:
        legacy = compose_workout_ui(frame, status, session, "READY", "STAND", 0.9, True, NOTICE_NOT_SIDE)
    finally:
        main_module._draw_notice_band = current_band
    assert np.abs(cached.astype(int) - legacy.astype(int)).max() <= 1  # 반올림 차이뿐이다


def test_the_cached_layer_does_not_keep_the_video_of_the_frame_that_created_it(fresh_font_caches) -> None:
    dark = np.full((480, 640, 3), 20, dtype=np.uint8)
    bright = np.full((480, 640, 3), 230, dtype=np.uint8)
    status = {"mode": "squat", "squat_count": 0}
    session = {"status": "ACTIVE", "elapsed_seconds": 0}
    first = compose_workout_ui(dark, status, session, "READY", "STAND", 0.9, True, NOTICE_NOT_SIDE)
    second = compose_workout_ui(bright, status, session, "READY", "STAND", 0.9, True, NOTICE_NOT_SIDE)
    band = (slice(64 + 480 - 54, 64 + 480 - 10), slice(12, 628))
    assert second[band].mean() > first[band].mean() + 20  # 영상 밝기가 그대로 반영된다(첫 프레임이 굳어 있지 않다)


def test_without_pillow_the_notice_falls_back_to_english_and_the_app_keeps_running(monkeypatch, fresh_font_caches) -> None:
    real_import = builtins.__import__

    def import_without_pillow(name, *args, **kwargs):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("No module named 'PIL' (simulated)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_pillow)
    assert main_module._korean_font() is None
    english = hud(NOTICE_NOT_SIDE)
    monkeypatch.undo()
    assert not np.array_equal(english, hud(None))  # 안내는 영어로 나온다
    assert main_module._notice_text_layer(NOTICE_NOT_SIDE, 616, 44, None) is None  # 폰트가 없으면 레이어는 만들지 않는다


def test_a_missing_font_file_falls_back_to_english(monkeypatch, fresh_font_caches) -> None:
    monkeypatch.setattr(main_module, "_KOREAN_FONT_CANDIDATES", ("C:/no/such/font.ttf", "/no/such/font.ttc"))
    main_module._korean_font.cache_clear()
    assert main_module._korean_font() is None
    english = hud(NOTICE_FULL_BODY_INVALID)
    assert not np.array_equal(english, hud(None))
    assert main_module._notice_text_layer(NOTICE_FULL_BODY_INVALID, 616, 44, None) is None


def test_the_font_is_looked_up_once_even_when_it_is_missing(monkeypatch, fresh_font_caches) -> None:
    calls = []

    def fake_truetype(path, size):
        calls.append(path)
        raise OSError("missing")

    monkeypatch.setattr("PIL.ImageFont.truetype", fake_truetype)
    for _ in range(3):
        assert main_module._korean_font() is None
    assert len(calls) == len(main_module._KOREAN_FONT_CANDIDATES)  # 매 프레임 파일 시스템을 뒤지지 않는다
