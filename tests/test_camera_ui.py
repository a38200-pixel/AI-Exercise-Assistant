"""Webcam 실행 없이 Camera UI의 pose filtering과 landmark rendering을 검증한다."""

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from src.main import (
    ALLOWED_DISPLAY_POSES,
    BODY_CONNECTIONS,
    BODY_LANDMARK_INDICES,
    draw_body_pose,
    update_display_pose,
)


def test_only_squat_workout_labels_are_exposed() -> None:
    pose, confidence = update_display_pose("stand", 0.91)
    assert pose == "STAND"
    assert confidence == 0.91

    for blocked_pose in ("run", "sit", "walk", "jump", "bendover", "lying"):
        pose, confidence = update_display_pose(blocked_pose, 0.99, pose, confidence)
        assert pose == "STAND"
        assert confidence == 0.91

    assert ALLOWED_DISPLAY_POSES == {"stand", "squat", "stretch"}


def test_body_renderer_excludes_face_and_connects_body_landmarks() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    landmarks = [
        SimpleNamespace(x=index / 40, y=index / 40, z=0.0, visibility=1.0)
        for index in range(33)
    ]

    with patch("src.main.cv2.circle") as circle, patch("src.main.cv2.line") as line:
        draw_body_pose(frame, landmarks, (0, 0, 100, 100))

    rendered_points = {call.args[1] for call in circle.call_args_list}
    expected_body_points = {(int(index * 2.5), int(index * 2.5)) for index in BODY_LANDMARK_INDICES}
    face_points = {(int(index * 2.5), int(index * 2.5)) for index in range(11)}

    assert rendered_points == expected_body_points
    assert rendered_points.isdisjoint(face_points)
    assert line.call_count == len(BODY_CONNECTIONS)


def test_incomplete_landmarks_are_not_rendered() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    landmarks = [SimpleNamespace(x=0.5, y=0.5) for _ in range(32)]

    with patch("src.main.cv2.circle") as circle, patch("src.main.cv2.line") as line:
        draw_body_pose(frame, landmarks, (0, 0, 100, 100))

    circle.assert_not_called()
    line.assert_not_called()
