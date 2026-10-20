"""분석 도구가 자체 구현한 각도·다리 선택 수식이 실제 src 코드와 같은 값을 내는지 확인한다.

polar_squat_angle_analysis.compute_angles는 POLAR 학습 데이터(DataFrame)에서 무릎각과 가까운 쪽 다리를 따로 구현한다(arccos 방식).
이 값으로 Phase 0의 임계값 근거(서 있음 160°, 내려감 150° 등)를 봤으므로, src.pose_geometry의 knee_angle(atan2 방식)·select_near_leg와
같은 값을 내야 그 근거가 실제 앱의 값에 그대로 적용된다.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for extra in (PROJECT_ROOT / "scripts" / "analysis",):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import polar_squat_angle_analysis as polar  # noqa: E402
from src.pose_geometry import LANDMARK_INDEX, LANDMARK_NAMES, knee_angle, landmarks_to_array, select_near_leg, to_pixel_points  # noqa: E402

NAMES = ("left_hip", "left_knee", "left_ankle", "right_hip", "right_knee", "right_ankle", "left_shoulder", "right_shoulder")


def random_rows(count, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(count):
        row = {"crop_w": float(rng.integers(200, 500)), "crop_h": float(rng.integers(300, 700))}
        for name in NAMES:
            row[f"{name}_x"], row[f"{name}_y"] = rng.uniform(0.1, 0.9, 2)
            row[f"{name}_visibility"] = float(rng.uniform(0.3, 1.0))
        rows.append(row)
    return rows


def real_landmarks(row):
    landmarks = [SimpleNamespace(x=0.5, y=0.5, z=0.0, visibility=1.0) for _ in LANDMARK_NAMES]
    for name in NAMES:
        landmarks[LANDMARK_INDEX[name]] = SimpleNamespace(x=row[f"{name}_x"], y=row[f"{name}_y"], z=0.0, visibility=row[f"{name}_visibility"])
    return landmarks


def test_the_polar_analysis_knee_angle_and_near_leg_match_the_real_geometry_code() -> None:
    rows = random_rows(300)
    result = polar.compute_angles(pd.DataFrame(rows))
    for row, near_leg, analysis_angle in zip(rows, result["near_leg"], result["knee_angle"]):
        array = landmarks_to_array(real_landmarks(row))
        assert select_near_leg(array) == near_leg
        points = to_pixel_points(array, row["crop_w"], row["crop_h"])
        assert knee_angle(points, near_leg) == pytest.approx(float(analysis_angle), abs=1e-6)


def test_the_two_formulas_agree_on_the_standing_and_descent_thresholds() -> None:
    # 서 있음 160°·내려감 150° 근처의 값에서도 같은 쪽에 떨어진다(경계 판정이 도구와 앱에서 달라지지 않는다).
    rng = np.random.default_rng(3)
    for degrees in (150.0, 160.0, 175.0, 90.0):
        radians = np.radians(degrees)
        vertex, first = np.array([100.0, 200.0]), np.array([100.0, 100.0])
        second = vertex + 100.0 * np.array([np.sin(radians), np.cos(radians) * -1.0])
        row = {"crop_w": 400.0, "crop_h": 600.0}
        for name in NAMES:
            row[f"{name}_x"], row[f"{name}_y"], row[f"{name}_visibility"] = rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8), 0.9
        for prefix in ("left", "right"):
            for joint, point in (("hip", first), ("knee", vertex), ("ankle", second)):
                row[f"{prefix}_{joint}_x"], row[f"{prefix}_{joint}_y"] = point[0] / 400.0, point[1] / 600.0
        analysis = polar.compute_angles(pd.DataFrame([row]))["knee_angle"].iloc[0]
        array = landmarks_to_array(real_landmarks(row))
        real = knee_angle(to_pixel_points(array, 400.0, 600.0), "left")
        assert real == pytest.approx(float(analysis), abs=1e-6)
        assert (real >= 160.0) == (analysis >= 160.0) and (real < 150.0) == (analysis < 150.0)
