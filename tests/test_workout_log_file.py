"""로컬 운동 기록 파일(workout_<시작시각>.json): 저장 내용, 쓰기 실패 시 동작, 경로 선택(개발/패키징), 서버 업로드 형식 불변."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import src.main as main_module
import src.paths as paths
from src.exercise_counter import SQUAT_MODE, ExerciseCounter
from src.rep_tracker import RepTracker
from src.workout_session import LOCAL_RECORD_SCHEMA_VERSION, WorkoutSession
from test_rep_tracker import rep_curve

KST = timezone(timedelta(hours=9))
STARTED = datetime(2026, 10, 19, 20, 1, 11, tzinfo=KST)
UPLOAD_KEYS = {"workout_date", "started_at", "ended_at", "workout_seconds", "squat_count", "stretch_seconds"}


def run_session(log_dir, *, curves=({}, {"hip_drop": 0.05}, {"bottom": 92.0}), started=STARTED, **session_options):
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    session = WorkoutSession(log_dir=log_dir, **session_options)
    assert session.start(counter, 0.0, started)
    clock = 0.0
    for curve in curves:
        for frame, label in rep_curve(start=clock, **curve):
            counter.update(label, frame.timestamp, frame)
        clock += 6.0
    summary = session.end(counter, clock, started + timedelta(seconds=clock))
    return session, counter, summary


# ---------------------------------------------------------------- 저장 내용


def test_a_finished_session_writes_one_json_named_after_its_start_time(tmp_path) -> None:
    session, _, summary = run_session(tmp_path)
    expected = tmp_path / "workout_20261019_200111.json"
    assert session.last_record_path == expected and expected.is_file() and session.last_save_error is None
    assert sorted(p.name for p in tmp_path.iterdir()) == ["workout_20261019_200111.json"]  # 임시 파일이 남지 않는다


def test_the_file_has_the_schema_version_the_summary_fields_and_the_per_rep_results(tmp_path) -> None:
    session, _, summary = run_session(tmp_path)
    record = json.loads(session.last_record_path.read_text(encoding="utf-8"))
    assert record["schema_version"] == LOCAL_RECORD_SCHEMA_VERSION == 1
    assert {key: record[key] for key in UPLOAD_KEYS} == summary  # 서버로 업로드하는 summary와 같은 필드·값
    first, rejected, third = record["reps"]
    assert [r["counted"] for r in record["reps"]] == [True, False, True] and [r["rep_number"] for r in record["reps"]] == [1, None, 2]
    assert first["posture"]["item_status"] == {"depth": "normal", "torso_shin": "normal"} and first["posture"]["worst_item"] is None
    assert first["posture"]["total_score"] == pytest.approx(100.0)
    assert rejected["reasons"] == ["shallow_hip_drop"] and rejected["posture"] is None
    assert third["posture"]["worst_item"] == "depth" and third["posture"]["item_status"]["depth"] == "caution"
    assert set(third["posture"]) >= {"total_score", "worst_item", "item_status", "item_scores", "measures", "capped"}


def test_the_decision_settings_are_recorded_so_the_scores_can_be_read_later(tmp_path) -> None:
    session, _, _ = run_session(tmp_path)
    recorded = json.loads(session.last_record_path.read_text(encoding="utf-8"))["settings"]
    assert recorded["POSTURE_DEPTH_NORMAL_MAX"] == 80.0 and recorded["POSTURE_DEPTH_ZERO_AT"] == 120.0 and recorded["REP_MIN_HIP_DROP"] == 0.20


def test_no_landmarks_or_face_data_or_nan_are_written(tmp_path) -> None:
    session, _, _ = run_session(tmp_path)
    text = session.last_record_path.read_text(encoding="utf-8")
    for forbidden in ("landmark", "world", "nose", "face", "NaN", "Infinity", "crop_bbox"):
        assert forbidden not in text
    json.loads(text)  # 표준 JSON(allow_nan=False로 썼다)


def test_a_session_without_reps_still_writes_a_record_with_an_empty_rep_list(tmp_path) -> None:
    session, _, _ = run_session(tmp_path, curves=())
    record = json.loads(session.last_record_path.read_text(encoding="utf-8"))
    assert record["reps"] == [] and record["squat_count"] == 0


def test_two_sessions_ending_in_the_same_second_do_not_overwrite_each_other(tmp_path) -> None:
    first, _, _ = run_session(tmp_path)
    second, _, _ = run_session(tmp_path)
    assert first.last_record_path != second.last_record_path
    assert sorted(p.name for p in tmp_path.iterdir()) == ["workout_20261019_200111.json", "workout_20261019_200111_2.json"]


def test_nothing_is_written_when_there_is_no_active_session_or_saving_is_off(tmp_path) -> None:
    idle = WorkoutSession(log_dir=tmp_path)
    assert idle.end(ExerciseCounter(), 1.0) is None and list(tmp_path.iterdir()) == []
    session, _, summary = run_session(tmp_path / "off", save_local_record=False)
    assert summary is not None and session.last_record_path is None and not (tmp_path / "off").exists()


# ---------------------------------------------------------------- 쓰기 실패


class FakeUploader:
    def __init__(self):
        self.submitted = []

    def submit(self, summary):
        self.submitted.append(summary)
        return True


def blocked_directory(tmp_path):
    """폴더를 만들 수 없는 경로(같은 이름의 파일이 이미 있다)."""
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    return blocker / "workout_logs"


def test_a_write_failure_does_not_stop_the_session_from_ending_and_is_logged(tmp_path, caplog, capsys) -> None:
    with caplog.at_level("WARNING"):
        session, _, summary = run_session(blocked_directory(tmp_path))
    assert summary is not None and set(summary) == UPLOAD_KEYS  # 세션은 정상 종료되고 summary가 나온다
    assert session.is_active is False and session.last_summary == summary
    assert session.last_record_path is None and session.last_save_error is not None
    assert "Could not save the local workout record" in caplog.text  # 로그에 남는다
    assert "[Local] Could not save" in capsys.readouterr().out  # 사용자에게도 한 줄 알린다
    assert session.last_local_record is not None  # 메모리의 기록은 그대로 있다


def test_a_write_failure_does_not_block_the_server_upload(tmp_path) -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    session = WorkoutSession(log_dir=blocked_directory(tmp_path))
    session.start(counter, 0.0, STARTED)
    uploader = FakeUploader()
    summary = main_module.complete_session(counter, session, uploader, 5.0)
    assert uploader.submitted == [summary] and set(summary) == UPLOAD_KEYS


def test_an_os_replace_failure_leaves_no_partial_file_and_does_not_raise(tmp_path, monkeypatch) -> None:
    def broken_replace(source, destination):
        raise PermissionError("locked by another process")

    monkeypatch.setattr("src.workout_session.os.replace", broken_replace)
    session, _, summary = run_session(tmp_path)
    assert summary is not None and session.last_save_error is not None
    assert not list(tmp_path.glob("workout_*.json"))  # 완성된 파일은 만들어지지 않는다


# ---------------------------------------------------------------- 서버 업로드 형식 불변


def test_the_upload_summary_has_exactly_the_original_keys_and_none_of_the_local_fields(tmp_path) -> None:
    session, _, summary = run_session(tmp_path)
    assert set(summary) == UPLOAD_KEYS == set(session.last_summary)
    text = json.dumps(summary)
    for local_only in ("schema_version", "reps", "posture", "settings", "worst_item"):
        assert local_only not in text


def test_complete_session_uploads_the_same_summary_that_the_file_contains(tmp_path) -> None:
    counter = ExerciseCounter(rep_tracker=RepTracker())
    counter.set_mode(SQUAT_MODE, 0.0)
    session = WorkoutSession(log_dir=tmp_path)
    session.start(counter, 0.0, STARTED)
    uploader = FakeUploader()
    summary = main_module.complete_session(counter, session, uploader, 5.0)
    record = json.loads(session.last_record_path.read_text(encoding="utf-8"))
    assert uploader.submitted == [summary] and {key: record[key] for key in UPLOAD_KEYS} == summary


# ---------------------------------------------------------------- 경로 선택(개발/패키징)


def test_the_development_path_is_data_workout_logs_in_the_repository(monkeypatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.get_workout_log_dir() == Path(paths.__file__).resolve().parents[1] / "data" / "workout_logs"


def test_the_packaged_path_is_under_the_per_user_local_app_data(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert paths.get_workout_log_dir() == tmp_path / "FitRoute" / "workout_logs"


def test_the_packaged_path_falls_back_to_the_home_directory_without_local_app_data(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert paths.get_workout_log_dir() == Path.home() / "AppData" / "Local" / "FitRoute" / "workout_logs"


def test_the_packaged_path_is_not_the_install_folder(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Program Files" / "FitRoute" / "FitRouteAIClient.exe"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert paths.get_app_root() not in paths.get_workout_log_dir().parents  # 설치 폴더 아래가 아니다


def test_the_default_save_goes_to_the_configured_directory_and_creates_it(monkeypatch, tmp_path) -> None:
    target = tmp_path / "nested" / "workout_logs"
    monkeypatch.setattr("src.workout_session.get_workout_log_dir", lambda: target)
    session, _, _ = run_session(None)
    assert session.last_record_path.parent == target and target.is_dir()
