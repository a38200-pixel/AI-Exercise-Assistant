"""구도 안내(A안): YOLO bbox만으로 판단하는 조건별 표시, 지속 시간 미만 미표시, 반복 중 미표시, 다른 안내와의 우선순위, 로그 기록."""

import numpy as np
import pytest

import config.settings as settings
from src.exercise_counter import SQUAT_MODE, STRETCH_MODE, ExerciseCounter
from src.framing_guide import NOTICE_MOVE_BACK, NOTICE_MOVE_CENTER, FramingGuide, classify_framing
from src.geometry_tracker import GeometryTracker
from src.main import NOTICE_TEXT, compose_workout_ui, pick_notice, update_framing, with_framing
from src.rep_tracker import NOTICE_NOT_SIDE, RepTracker
from src.sequence_logger import SequenceLogger, SequenceRecorder, session_metadata
from test_pose_geometry import FRAME
from test_sequence_logger import make_person, read_records, smoothing_state

SIZE = (640, 480)
OK_BOX = (250, 60, 390, 420)  # 위 60px, 아래 60px 여유, 좌우 여유 큼: 문제 없음
TOUCHING = (250, 60, 390, 479)  # 발이 아래 경계에 닿음
LEFT = (0, 60, 140, 420)  # 왼쪽 경계에 닿음
DELAY = settings.FRAMING_NOTICE_DELAY_SECONDS


def feed(guide, bbox, start, seconds, step=0.06, in_rep=False):
    """bbox를 start부터 seconds초 동안 넣고 마지막 결과와 처음 안내가 보인 시각을 돌려준다."""
    shown_at, last = None, None
    for i in range(int(round(seconds / step)) + 1):
        t = start + i * step
        last = guide.update(bbox, SIZE, t, in_rep=in_rep)
        if last and shown_at is None:
            shown_at = t
    return last, shown_at


# ---------------------------------------------------------------- 조건별 분류


@pytest.mark.parametrize(
    ("bbox", "expected"),
    [
        (OK_BOX, None),
        (TOUCHING, NOTICE_MOVE_BACK),
        ((250, 40, 390, 480), NOTICE_MOVE_BACK),
        ((250, 50, 390, 462), NOTICE_MOVE_BACK),  # 발 아래 여유 18px: 프레임 높이의 4%(19.2px) 이하
        ((250, 50, 390, 450), None),  # 여유 30px: 괜찮다
        ((0, 60, 140, 420), NOTICE_MOVE_CENTER),  # 왼쪽 경계
        ((500, 60, 640, 420), NOTICE_MOVE_CENTER),  # 오른쪽 경계
        ((1, 60, 140, 420), NOTICE_MOVE_CENTER),  # 허용 오차 2px 이내
        ((3, 60, 140, 420), None),
        ((250, 0, 390, 420), None),  # 위(머리) 경계 접촉만으로는 조건이 아니다
        ((250, 0, 390, 300), None),
        ((0, 60, 140, 479), NOTICE_MOVE_BACK),  # 아래와 왼쪽이 함께면 뒤로 물러서기가 먼저
    ],
)
def test_the_bbox_conditions(bbox, expected) -> None:
    assert classify_framing(bbox, SIZE) == expected


def test_the_height_ratio_alone_triggers_move_back_even_with_room_below() -> None:
    needed = settings.FRAMING_MAX_HEIGHT_RATIO * 480  # 456px
    tall = (250, 0, 390, int(needed))  # 높이 456px = 95%, 아래 여유 24px(4% = 19.2px 초과)
    assert 480 - tall[3] > settings.FRAMING_FEET_MARGIN_RATIO * 480
    assert classify_framing(tall, SIZE) == NOTICE_MOVE_BACK
    assert classify_framing((250, 0, 390, int(needed) - 4), SIZE) is None  # 높이 94.2%, 여유 28px


def test_the_conditions_scale_with_the_frame_size() -> None:
    assert classify_framing((500, 100, 700, 700), (1280, 720)) == NOTICE_MOVE_BACK  # 아래 여유 20px(720의 2.8%)
    assert classify_framing((500, 100, 700, 650), (1280, 720)) is None  # 여유 70px


# ---------------------------------------------------------------- 지속 시간


def test_nothing_is_shown_before_the_condition_has_lasted_the_delay() -> None:
    last, shown_at = feed(FramingGuide(), TOUCHING, 0.0, DELAY - 0.2)
    assert last is None and shown_at is None


def test_the_notice_appears_once_the_delay_has_passed_and_stays() -> None:
    last, shown_at = feed(FramingGuide(), TOUCHING, 0.0, DELAY + 1.0)
    assert last == NOTICE_MOVE_BACK and DELAY <= shown_at <= DELAY + 0.1


def test_each_condition_shows_its_own_text_after_the_delay() -> None:
    assert feed(FramingGuide(), TOUCHING, 0.0, DELAY + 0.5)[0] == NOTICE_MOVE_BACK
    assert feed(FramingGuide(), LEFT, 0.0, DELAY + 0.5)[0] == NOTICE_MOVE_CENTER
    assert feed(FramingGuide(), (250, 0, 390, 480), 0.0, DELAY + 0.5)[0] == NOTICE_MOVE_BACK
    assert feed(FramingGuide(), OK_BOX, 0.0, DELAY + 0.5)[0] is None


def test_a_flicker_shorter_than_the_clear_time_does_not_restart_the_timer() -> None:
    guide = FramingGuide()
    feed(guide, TOUCHING, 0.0, 1.0)
    guide.update(OK_BOX, SIZE, 1.06)  # 잠깐 경계에서 벗어남(0.06초)
    last, _ = feed(guide, TOUCHING, 1.12, 0.5)
    assert last == NOTICE_MOVE_BACK  # 처음 시작부터 센 시간이 이어진다(1.6초 > 1.5초)


def test_the_notice_clears_after_the_condition_is_gone_for_the_clear_time_and_needs_the_delay_again() -> None:
    guide = FramingGuide()
    feed(guide, TOUCHING, 0.0, DELAY + 0.5)
    last, _ = feed(guide, OK_BOX, 3.0, settings.FRAMING_NOTICE_CLEAR_SECONDS + 0.2)
    assert last is None
    again, shown_at = feed(guide, TOUCHING, 4.0, DELAY + 0.5)
    assert again == NOTICE_MOVE_BACK and shown_at - 4.0 >= DELAY - 0.01  # 다시 처음부터 지속 시간을 센다


def test_switching_between_the_two_problems_keeps_the_timer() -> None:
    guide = FramingGuide()
    feed(guide, LEFT, 0.0, 1.0)
    last, _ = feed(guide, TOUCHING, 1.06, 0.6)
    assert last == NOTICE_MOVE_BACK


def test_missing_person_frames_do_not_reset_the_state_until_the_absent_limit() -> None:
    guide = FramingGuide()
    feed(guide, TOUCHING, 0.0, 1.0)
    for i in range(10):
        assert guide.update(None, SIZE, 1.06 + i * 0.1) is None  # 사람 없음 1초: 상태는 유지, 안내는 없다
    last, _ = feed(guide, TOUCHING, 2.2, 0.3)
    assert last == NOTICE_MOVE_BACK  # 이어서 센 시간이 지속 시간을 넘었다
    reset = FramingGuide()
    feed(reset, TOUCHING, 0.0, 1.0)
    for i in range(int((settings.FRAMING_ABSENT_RESET_SECONDS + 1.0) / 0.1)):
        reset.update(None, SIZE, 1.06 + i * 0.1)
    assert feed(reset, TOUCHING, 4.5, 0.3)[0] is None  # 오래 사라졌다 돌아오면 처음부터


# ---------------------------------------------------------------- 반복 중 미표시


def test_nothing_is_shown_during_a_rep_and_the_notice_returns_after_it_if_the_problem_continues() -> None:
    guide = FramingGuide()
    feed(guide, TOUCHING, 0.0, DELAY + 0.5)
    last, _ = feed(guide, TOUCHING, 3.0, 2.0, in_rep=True)
    assert last is None  # 반복 중에는 보이지 않는다
    after, _ = feed(guide, TOUCHING, 5.1, 0.2, in_rep=False)
    assert after == NOTICE_MOVE_BACK  # 반복이 끝났는데 조건이 계속되면 다시 보인다


def test_the_pipeline_helper_suppresses_the_notice_in_rep_and_outside_squat_mode_or_without_a_rep_tracker() -> None:
    def counter(mode, with_tracker=True):
        c = ExerciseCounter(rep_tracker=RepTracker() if with_tracker else None)
        c.set_mode(mode, 0.0)
        return c

    person = {"bbox": TOUCHING}

    def run(c, guidance, seconds=DELAY + 0.5):
        guide, status, shown = FramingGuide(), {"rep_guidance": guidance}, None
        for i in range(int(seconds / 0.06)):
            shown = update_framing(guide, c, status, person, SIZE, i * 0.06)
        return shown

    assert run(counter(SQUAT_MODE), "ready") == NOTICE_MOVE_BACK
    assert run(counter(SQUAT_MODE), "in_rep") is None
    assert run(counter(STRETCH_MODE), "ready") is None
    assert run(counter(SQUAT_MODE, with_tracker=False), None) is None  # USE_REP_TRACKER=False(v0.1.x)에서는 새 안내가 없다
    assert update_framing(FramingGuide(), counter(SQUAT_MODE), {"rep_guidance": "ready"}, None, SIZE, 0.0) is None  # 사람 없음


# ---------------------------------------------------------------- 우선순위와 화면


def test_the_framing_notice_has_priority_over_the_lock_notices() -> None:
    assert pick_notice(NOTICE_MOVE_BACK, NOTICE_NOT_SIDE) == NOTICE_MOVE_BACK
    assert pick_notice(NOTICE_MOVE_CENTER, "full_body_invalid") == NOTICE_MOVE_CENTER
    assert pick_notice(None, NOTICE_NOT_SIDE) == NOTICE_NOT_SIDE
    assert pick_notice(None, None) is None


def test_the_notice_texts_are_the_agreed_ones() -> None:
    assert NOTICE_TEXT[NOTICE_MOVE_BACK][0] == "뒤로 물러서 주세요"
    assert NOTICE_TEXT[NOTICE_MOVE_CENTER][0] == "화면 가운데로 이동해 주세요"
    assert NOTICE_TEXT[NOTICE_MOVE_BACK][1] and NOTICE_TEXT[NOTICE_MOVE_CENTER][1]  # 한글 폰트가 없을 때의 영어 문구


@pytest.mark.parametrize("code", [NOTICE_MOVE_BACK, NOTICE_MOVE_CENTER])
def test_the_framing_notice_is_drawn_in_the_band_at_the_bottom_of_the_video(code) -> None:
    frame = np.full((480, 640, 3), 90, dtype=np.uint8)
    status, session = {"mode": "squat", "squat_count": 3}, {"status": "ACTIVE", "elapsed_seconds": 65}
    plain = compose_workout_ui(frame, status, session, "READY", "STAND", 0.9, True, None, None)
    noticed = compose_workout_ui(frame, status, session, "READY", "STAND", 0.9, True, code, None)
    rows, cols = np.where(np.any(plain != noticed, axis=2))
    assert rows.min() >= 64 + 480 - 70 and rows.max() <= 64 + 480 and cols.min() >= 12 and cols.max() <= 640 - 12


def test_the_settings_are_the_values_from_the_gap_analysis() -> None:
    assert settings.FRAMING_FEET_MARGIN_RATIO == 0.04 and settings.FRAMING_MAX_HEIGHT_RATIO == 0.95
    assert settings.FRAMING_EDGE_TOUCH_PX == 2 and settings.FRAMING_NOTICE_DELAY_SECONDS == 1.5


# ---------------------------------------------------------------- 로그


def test_the_frame_log_records_the_framing_notice_in_the_rep_diagnostics(tmp_path) -> None:
    logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05, clock=lambda: 100.0)
    path = logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker())
    diagnostics = with_framing({"state": "STANDING", "notice": None, "events": []}, NOTICE_MOVE_BACK)
    recorder.record(
        frame_size=FRAME, primary_person=make_person(), smoothing_state=smoothing_state(), display_pose="STAND",
        display_confidence=0.9, capture_time=100.1, logic_time=100.1, rep=diagnostics,
    )
    recorder.close()
    frame = [r for r in read_records(path) if r["type"] == "frame"][0]
    assert frame["rep"] == {"state": "STANDING", "notice": None, "framing": NOTICE_MOVE_BACK}
    assert with_framing(None, NOTICE_MOVE_BACK) is None
