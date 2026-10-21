"""테스트가 저장소의 data/workout_logs/에 운동 기록 파일을 만들지 않도록, 기본 저장 경로를 테스트별 임시 폴더로 돌린다."""

import pytest


@pytest.fixture(autouse=True)
def isolated_workout_log_dir(tmp_path_factory, monkeypatch):
    import src.workout_session as workout_session

    monkeypatch.setattr(workout_session, "get_workout_log_dir", lambda: tmp_path_factory.mktemp("workout_logs"))
