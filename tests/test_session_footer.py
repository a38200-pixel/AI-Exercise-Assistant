"""종료 시 실제 반복 횟수 입력(footer): 입력값 기록, 미입력 처리, 로깅이 꺼졌거나 패키징 빌드·비대화형일 때 묻지 않음, 읽는 쪽 호환."""

import ast
import json
import sys
from pathlib import Path

import pytest

import src.main as main_module
from src.exercise_counter import SQUAT_MODE, ExerciseCounter
from src.geometry_tracker import GeometryTracker
from src.main import finish_sequence_log
from src.sequence_logger import (
    FOOTER_ENTERED,
    FOOTER_MAX_REPS,
    FOOTER_NOT_ENTERED,
    FOOTER_NOTE_MAX_CHARS,
    FORMAT_VERSION,
    SUPPORTED_FORMAT_VERSIONS,
    SequenceLogger,
    SequenceRecorder,
    collect_session_footer,
    session_metadata,
)
from test_sequence_logger import read_records

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for extra in (PROJECT_ROOT / "scripts" / "analysis",):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))


def scripted(*answers):
    """차례로 답을 돌려주는 input 대용. 예외 인스턴스가 있으면 그 입력에서 던진다."""
    queue = list(answers)
    prompts: list[str] = []

    def fake_input(prompt=""):
        prompts.append(prompt)
        answer = queue.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    fake_input.prompts = prompts
    return fake_input


def never_asked(prompt=""):
    raise AssertionError(f"nothing should be asked here: {prompt}")


# ---------------------------------------------------------------- 입력 받기


def test_an_entered_count_and_note_are_recorded_with_the_screen_count() -> None:
    footer = collect_session_footer(5, mode="squat", input_fn=scripted("7", "마지막 두 번은 빠르게"), output_fn=lambda *_: None, interactive=True)
    assert footer["actual_reps"] == 7 and footer["actual_status"] == FOOTER_ENTERED
    assert footer["app_reps"] == 5 and footer["mode"] == "squat"
    assert footer["note"] == "마지막 두 번은 빠르게" and footer["prompt"] == "answered"


def test_zero_is_a_valid_actual_count() -> None:
    footer = collect_session_footer(0, input_fn=scripted("0", ""), output_fn=lambda *_: None, interactive=True)
    assert footer["actual_reps"] == 0 and footer["actual_status"] == FOOTER_ENTERED


def test_skipping_the_count_records_not_entered_but_keeps_the_note() -> None:
    footer = collect_session_footer(5, input_fn=scripted("", "카운트 모르겠음"), output_fn=lambda *_: None, interactive=True)
    assert footer["actual_reps"] is None and footer["actual_status"] == FOOTER_NOT_ENTERED
    assert footer["note"] == "카운트 모르겠음" and footer["prompt"] == "skipped"
    assert footer["app_reps"] == 5  # 화면 카운트는 항상 남는다


def test_a_blank_note_is_stored_as_none() -> None:
    footer = collect_session_footer(5, input_fn=scripted("5", "   "), output_fn=lambda *_: None, interactive=True)
    assert footer["note"] is None


def test_a_mistyped_count_is_asked_again_and_three_bad_answers_mean_not_entered() -> None:
    retried = collect_session_footer(5, input_fn=scripted("칠", "-3", "7", ""), output_fn=lambda *_: None, interactive=True)
    assert retried["actual_reps"] == 7
    gave_up = collect_session_footer(5, input_fn=scripted("a", "b", str(FOOTER_MAX_REPS + 1), ""), output_fn=lambda *_: None, interactive=True)
    assert gave_up["actual_reps"] is None and gave_up["actual_status"] == FOOTER_NOT_ENTERED


def test_a_note_is_cut_to_the_maximum_length() -> None:
    footer = collect_session_footer(5, input_fn=scripted("5", "가" * 900), output_fn=lambda *_: None, interactive=True)
    assert len(footer["note"]) == FOOTER_NOTE_MAX_CHARS


@pytest.mark.parametrize("interrupt", [EOFError(), KeyboardInterrupt()])
def test_a_closed_input_or_ctrl_c_leaves_not_entered_without_failing(interrupt) -> None:
    footer = collect_session_footer(5, input_fn=scripted(interrupt), output_fn=lambda *_: None, interactive=True)
    assert footer["actual_reps"] is None and footer["actual_status"] == FOOTER_NOT_ENTERED
    kept = collect_session_footer(5, input_fn=scripted("6", interrupt), output_fn=lambda *_: None, interactive=True)
    assert kept["actual_reps"] == 6  # 횟수를 받은 뒤 끊기면 받은 것은 남는다


def test_without_a_terminal_nothing_is_asked_and_the_count_is_not_entered() -> None:
    footer = collect_session_footer(5, input_fn=never_asked, output_fn=lambda *_: None, interactive=False)
    assert footer["actual_status"] == FOOTER_NOT_ENTERED and footer["prompt"] == "unavailable"


def test_a_packaged_build_is_never_interactive(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    footer = collect_session_footer(5, input_fn=never_asked, output_fn=lambda *_: None)
    assert footer["prompt"] == "unavailable"


# ---------------------------------------------------------------- 로그 파일


def new_recorder(tmp_path):
    logger = SequenceLogger(tmp_path, metadata=session_metadata("normal", "side"), flush_interval=0.05)
    logger.start()
    return SequenceRecorder(logger, GeometryTracker())


def squat_counter(count):
    counter = ExerciseCounter()
    counter.set_mode(SQUAT_MODE, 0.0)
    counter.squat_count = count
    return counter


def test_the_footer_is_written_just_before_the_end_line_and_is_not_a_frame(tmp_path) -> None:
    recorder = new_recorder(tmp_path)
    assert recorder.logger.log_footer({"app_reps": 5, "actual_reps": 7, "actual_status": FOOTER_ENTERED, "note": None})
    recorder.close()
    records = read_records(recorder.logger.path)
    assert [r["type"] for r in records] == ["session", "footer", "end"]
    assert records[1]["actual_reps"] == 7 and records[1]["app_reps"] == 5
    assert records[2]["frames_written"] == 0 and records[2]["events_written"] == 0  # footer는 프레임·이벤트 집계에 들어가지 않는다


def test_the_format_version_stays_at_2_because_the_footer_is_an_optional_trailing_line(tmp_path) -> None:
    recorder = new_recorder(tmp_path)
    recorder.logger.log_footer({"app_reps": 0, "actual_reps": None, "actual_status": FOOTER_NOT_ENTERED, "note": None})
    recorder.close()
    header = read_records(recorder.logger.path)[0]
    assert header["format_version"] == FORMAT_VERSION == 2 and 2 in SUPPORTED_FORMAT_VERSIONS


def test_a_footer_after_close_is_refused(tmp_path) -> None:
    recorder = new_recorder(tmp_path)
    recorder.close()
    assert recorder.logger.log_footer({"app_reps": 1}) is False
    assert [r["type"] for r in read_records(recorder.logger.path)] == ["session", "end"]


# ---------------------------------------------------------------- finish_sequence_log (main이 종료 때 부르는 함수)


def test_finishing_asks_and_records_the_entered_count_and_the_screen_count(tmp_path) -> None:
    recorder = new_recorder(tmp_path)
    finish_sequence_log(recorder, squat_counter(5), ask_actual_reps=True, input_fn=scripted("7", "정상 7회"), interactive=True)
    footer = [r for r in read_records(recorder.logger.path) if r["type"] == "footer"][0]
    assert footer["actual_reps"] == 7 and footer["app_reps"] == 5 and footer["mode"] == "squat" and footer["note"] == "정상 7회"
    assert read_records(recorder.logger.path)[-1]["type"] == "end"


def test_finishing_with_a_skipped_answer_records_not_entered(tmp_path) -> None:
    recorder = new_recorder(tmp_path)
    finish_sequence_log(recorder, squat_counter(5), ask_actual_reps=True, input_fn=scripted("", ""), interactive=True)
    footer = [r for r in read_records(recorder.logger.path) if r["type"] == "footer"][0]
    assert footer["actual_reps"] is None and footer["actual_status"] == FOOTER_NOT_ENTERED and footer["app_reps"] == 5


def test_nothing_is_asked_when_logging_is_off() -> None:
    finish_sequence_log(None, squat_counter(5), ask_actual_reps=True, input_fn=never_asked, interactive=True)


def test_nothing_is_asked_and_no_footer_is_written_when_the_run_was_not_ended_with_q_or_esc(tmp_path) -> None:
    recorder = new_recorder(tmp_path)
    finish_sequence_log(recorder, squat_counter(5), ask_actual_reps=False, input_fn=never_asked, interactive=True)
    assert [r["type"] for r in read_records(recorder.logger.path)] == ["session", "end"]


def test_a_packaged_build_asks_nothing_and_writes_no_footer(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    recorder = new_recorder(tmp_path)
    finish_sequence_log(recorder, squat_counter(5), ask_actual_reps=True, input_fn=never_asked)
    assert [r["type"] for r in read_records(recorder.logger.path)] == ["session", "end"]


def test_without_a_terminal_the_footer_still_keeps_the_screen_count(tmp_path) -> None:
    recorder = new_recorder(tmp_path)
    finish_sequence_log(recorder, squat_counter(4), ask_actual_reps=True, input_fn=never_asked, interactive=False)
    footer = [r for r in read_records(recorder.logger.path) if r["type"] == "footer"][0]
    assert footer["app_reps"] == 4 and footer["actual_status"] == FOOTER_NOT_ENTERED and footer["prompt"] == "unavailable"


def test_the_recorder_is_closed_even_if_the_question_fails(tmp_path) -> None:
    recorder = new_recorder(tmp_path)

    def broken_input(prompt=""):
        raise RuntimeError("terminal exploded")

    with pytest.raises(RuntimeError):
        finish_sequence_log(recorder, squat_counter(5), ask_actual_reps=True, input_fn=broken_input, interactive=True)
    assert read_records(recorder.logger.path)[-1]["type"] == "end"  # 로그는 정상적으로 닫힌다


def test_main_asks_only_through_finish_sequence_log_and_only_after_q_or_esc() -> None:
    """main()에는 input() 호출이 없고, 종료 때만 finish_sequence_log를 quit_requested로 부른다(로깅을 안 켜면 recorder가 None이라 묻지 않는다)."""
    tree = ast.parse(Path(main_module.__file__).read_text(encoding="utf-8"))
    input_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "input"]
    assert input_calls == []
    main_function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    finish_calls = [
        n for n in ast.walk(main_function) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "finish_sequence_log"
    ]
    assert len(finish_calls) == 1
    keywords = {k.arg: k.value for k in finish_calls[0].keywords}
    assert isinstance(keywords["ask_actual_reps"], ast.Name) and keywords["ask_actual_reps"].id == "quit_requested"


# ---------------------------------------------------------------- 읽는 쪽: 실제 횟수와 검출 횟수를 나란히


def test_the_plot_reader_finds_the_footer_and_the_session_still_loads(tmp_path) -> None:
    plot = pytest.importorskip("plot_landmark_sequence")
    recorder = new_recorder(tmp_path)
    finish_sequence_log(recorder, squat_counter(5), ask_actual_reps=True, input_fn=scripted("7", ""), interactive=True)
    header, frames, end, skipped = plot.load_session(recorder.logger.path)
    assert header["format_version"] == 2 and end is not None and skipped == 0
    footer = plot.load_footer(recorder.logger.path)
    assert footer["actual_reps"] == 7 and footer["app_reps"] == 5


def test_a_log_without_a_footer_reads_as_none(tmp_path) -> None:
    plot = pytest.importorskip("plot_landmark_sequence")
    recorder = new_recorder(tmp_path)
    recorder.close()
    assert plot.load_footer(recorder.logger.path) is None


REP_ENDS = [{"kind": "rep_end", "counted": True}] * 5 + [{"kind": "rep_end", "counted": False}] * 2


def test_actual_screen_and_detected_counts_are_shown_side_by_side() -> None:
    plot = pytest.importorskip("plot_landmark_sequence")
    entered = {"actual_reps": 7, "actual_status": FOOTER_ENTERED, "app_reps": 5, "note": "연속 세트"}
    line = plot.format_counts(entered, REP_ENDS)
    assert line.startswith("actual 7 | screen 5 | detected 5") and "(differs by -2)" in line and "연속 세트" in line
    assert "연속 세트" not in plot.format_counts(entered, REP_ENDS, include_note=False)
    assert plot.count_summary(entered, REP_ENDS) == {"actual": 7, "status": "entered", "screen": 5, "detected": 5, "note": "연속 세트"}


def test_not_entered_and_missing_footer_are_labelled_differently() -> None:
    plot = pytest.importorskip("plot_landmark_sequence")
    skipped = {"actual_reps": None, "actual_status": FOOTER_NOT_ENTERED, "app_reps": 5, "note": None}
    assert plot.format_counts(skipped, REP_ENDS).startswith("actual 미입력 | screen 5 | detected 5")
    assert "no footer" in plot.format_counts(None, REP_ENDS)
    assert plot.format_counts(None, []).endswith("screen - | detected -")  # RepTracker를 안 쓴 로그는 검출 횟수가 없다
    matching = {"actual_reps": 5, "actual_status": FOOTER_ENTERED, "app_reps": 5, "note": None}
    assert "differs" not in plot.format_counts(matching, REP_ENDS)


def test_the_replay_script_reads_the_actual_count_from_the_footer(tmp_path) -> None:
    from scripts.analysis import replay_flags

    recorder = new_recorder(tmp_path)
    finish_sequence_log(recorder, squat_counter(5), ask_actual_reps=True, input_fn=scripted("7", "연속"), interactive=True)
    records = [json.loads(line) for line in recorder.logger.path.read_text(encoding="utf-8").splitlines()]
    assert records[-2]["type"] == "footer" and records[-2]["actual_reps"] == 7
    loaded = replay_flags.load_log(recorder.logger.path)  # 프레임이 없는 로그라도 footer에서 실제 횟수와 메모를 읽는다
    assert loaded["actual_squats"] == 7 and loaded["note"] == "연속"
