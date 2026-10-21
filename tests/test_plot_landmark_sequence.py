"""시퀀스 분석 스크립트가 로거가 만든 로그를 읽고 Phase 3에 필요한 원자료를 복원하는지 검증한다."""

import sys
import time
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("matplotlib")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for extra in (PROJECT_ROOT, PROJECT_ROOT / "scripts" / "analysis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import plot_landmark_sequence as plot
from src.geometry_tracker import GeometryTracker
from src.sequence_logger import SequenceLogger, SequenceRecorder, session_metadata
from test_pose_geometry import FRAME, RIGHT_LEG_HIDDEN, SIDE_POSE, build_landmarks
from test_sequence_logger import CROP_S, PERSON_S, STANDING_POSE, smoothing_state


FPS = 30.0


def blend(weight: float) -> dict[str, tuple[float, float]]:
    """서 있는 자세(0)와 쪼그린 자세(1) 사이를 좌표 보간한 자세."""
    return {
        name: (
            STANDING_POSE[name][0] * (1 - weight) + SIDE_POSE[name][0] * weight,
            STANDING_POSE[name][1] * (1 - weight) + SIDE_POSE[name][1] * weight,
        )
        for name in STANDING_POSE
    }


def knee_weight(second: float) -> float:
    """1~2초에 내려가고 2~3초에 올라오는 반복 한 번(앞뒤 1초는 서 있음)."""
    return float(np.clip(1 - abs(second - 2.0), 0.0, 1.0))


def record_session(directory: Path, seconds: float = 4.0) -> Path:
    base = 1000.0
    logger = SequenceLogger(directory, metadata=session_metadata("normal", "side"), flush_interval=0.05, clock=lambda: base)
    path = logger.start()
    recorder = SequenceRecorder(logger, GeometryTracker())
    for index in range(int(seconds * FPS)):
        second = index / FPS
        weight = knee_weight(second)
        person = {
            "bbox": PERSON_S,
            "padded_bbox": CROP_S,
            "person_confidence": 0.9,
            "landmarks": build_landmarks(blend(weight), CROP_S, {"nose": 0.99, **RIGHT_LEG_HIDDEN}),
            "world_landmarks": None,
            "prediction": {"label": "squat" if weight > 0.5 else "stand", "confidence": 0.9},
        }
        recorder.record(
            frame_size=FRAME,
            primary_person=person,
            smoothing_state=smoothing_state("squat" if weight > 0.5 else "stand"),
            display_pose="SQUAT" if weight > 0.5 else "STAND",
            display_confidence=0.9,
            capture_time=base + second,
            logic_time=base + second + 0.002,
        )
    recorder.close()
    return path


def test_load_session_tolerates_a_cut_off_last_line(tmp_path) -> None:
    path = record_session(tmp_path, seconds=1.0)
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"type":"frame","i":9999,"t":1.')  # 비정상 종료로 잘린 줄

    header, frames, end, skipped = plot.load_session(path)
    assert header["metadata"]["intended_posture"] == "normal"
    assert len(frames) == int(1.0 * FPS)
    assert end is not None and skipped == 1


def test_series_recovers_what_the_tempo_and_heel_analysis_needs(tmp_path) -> None:
    path = record_session(tmp_path)
    header, frames, _, _ = plot.load_session(path)
    series = plot.build_series(header, frames)

    # 타임스탬프: 실제 프레임 간격(1/30초)이 그대로 남아 하강/상승/체류 시간을 계산할 수 있다.
    assert np.allclose(np.diff(series["t"]), 1 / FPS, atol=2e-5)

    # 무릎각: 서 있을 때 180도, 가장 깊을 때 쪼그린 자세의 각도(약 106.7도)
    assert np.nanmax(series["knee"]) == pytest.approx(180.0, abs=1e-3)
    assert np.nanmin(series["knee"]) == pytest.approx(106.7, abs=0.2)
    bottom_time = series["t"][int(np.nanargmin(series["knee"]))]
    assert bottom_time == pytest.approx(2.0, abs=0.05)  # 최저점 시각

    # heel/foot_index y는 crop 정규화 값이 아니라 프레임 픽셀로 복원된다(crop이 프레임마다 달라져도 비교 가능).
    assert series["heel_y"][0] == pytest.approx(STANDING_POSE["left_heel"][1], abs=0.01)
    assert series["toe_y"][0] == pytest.approx(STANDING_POSE["left_foot_index"][1], abs=0.01)
    bottom = int(np.nanargmin(series["knee"]))
    assert series["heel_y"][bottom] == pytest.approx(SIDE_POSE["left_heel"][1], abs=0.01)

    # 부호 있는 각도와 무부호 각도가 둘 다 있다.
    assert not np.isnan(series["torso_signed"]).any() and not np.isnan(series["torso"]).any()
    assert series["valid"].all()
    # 잠금은 측면 판정이 0.5초 이어진 뒤에 걸리고(처음 0.5초는 잠금 없음), 반복 중에도 유지된다.
    assert not series["locked"][0] and series["locked"][int(0.6 * FPS):].all()


def test_crop_changes_do_not_leak_into_the_heel_position(tmp_path) -> None:
    """같은 자세를 서로 다른 crop으로 기록해도 복원한 프레임 y가 같아야 한다."""
    heel_y = []
    for crop in (CROP_S, (30, 10, 400, 420)):
        logger = SequenceLogger(tmp_path, metadata=session_metadata(), flush_interval=0.05)
        path = logger.start()
        recorder = SequenceRecorder(logger, GeometryTracker())
        person = {
            "bbox": PERSON_S,
            "padded_bbox": crop,
            "person_confidence": 0.9,
            "landmarks": build_landmarks(STANDING_POSE, crop, {"nose": 0.99, **RIGHT_LEG_HIDDEN}),
            "world_landmarks": None,
            "prediction": None,
        }
        recorder.record(
            frame_size=FRAME, primary_person=person, smoothing_state=smoothing_state(),
            display_pose="STAND", display_confidence=0.9, capture_time=time.perf_counter(), logic_time=time.perf_counter(),
        )
        recorder.close()
        header, frames, _, _ = plot.load_session(path)
        heel_y.append(plot.build_series(header, frames)["heel_y"][0])
    assert heel_y[0] == pytest.approx(heel_y[1], abs=0.01)


def test_summary_and_plots_are_produced(tmp_path, capsys) -> None:
    path = record_session(tmp_path)
    out_dir = tmp_path / "plots"

    assert plot.main(["--session", str(path), "--out-dir", str(out_dir)]) == 0

    output = capsys.readouterr().out
    assert "frames          : 120" in output and "dropped 0" in output
    assert "full body valid : 100.0% of time" in output
    assert "stand:" in output and "squat:" in output
    timeline, labels = out_dir / f"{path.stem}_timeline.png", out_dir / f"{path.stem}_labels.png"
    assert timeline.stat().st_size > 10_000 and labels.stat().st_size > 5_000


def test_missing_session_file_is_reported(tmp_path) -> None:
    with pytest.raises(SystemExit):
        plot.main(["--session", str(tmp_path / "missing.jsonl")])
