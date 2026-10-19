"""Real-time YOLO -> MediaPipe -> XGBoost pose classification pipeline."""

import argparse
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np

from config.settings import (
    BBOX_PADDING,
    LANDMARK_SEQUENCE_DIR,
    SEQUENCE_LOG_FACE_LANDMARKS,
    SEQUENCE_LOGGING_ENABLED,
)
from src.api_client import WorkoutUploader, create_api_client_from_environment
from src.camera import Camera
from src.exercise_counter import (
    IDLE_MODE,
    SQUAT_MODE,
    STRETCH_MODE,
    ExerciseCounter,
)
from src.geometry_tracker import GeometryTracker
from src.person_detector import PersonDetector
from src.pose_classifier import PoseClassifier
from src.pose_estimator import PoseEstimator
from src.prediction_smoother import PredictionSmoother
from src.rep_tracker import NOTICE_FULL_BODY_INVALID, NOTICE_NOT_SIDE, RepTracker, track_primary_person
from src.runtime_diagnostic import run_runtime_diagnostic
from src.sequence_logger import (
    CAMERA_VIEWS,
    INTENDED_POSTURES,
    SequenceLogger,
    SequenceRecorder,
    collect_session_footer,
    session_metadata,
)
from src.workout_session import WorkoutSession


WINDOW_NAME = "AI Exercise Assistant"
WARMUP_FRAMES = 30
YOLO_ONLY_BASELINE_FPS = 29.44
PREVIOUS_END_TO_END_FPS = 15.89

# 33개 landmark는 분류 입력에 그대로 사용하고, 화면에는 얼굴(0~10)을 제외한
# 몸 관절만 표시한다.
BODY_LANDMARK_INDICES = tuple(range(11, 33))
BODY_CONNECTIONS = (
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (15, 17), (17, 19), (19, 15), (15, 21),
    (16, 18), (18, 20), (20, 16), (16, 22),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
)
ALLOWED_DISPLAY_POSES = frozenset({"stand", "squat", "stretch"})

INK = (14, 17, 11)
SURFACE = (21, 26, 17)
ELEVATED = (28, 35, 24)
LIME = (99, 255, 183)
MUTED_LIME = (86, 181, 126)
WHITE = (245, 247, 246)
MUTED_TEXT = (145, 154, 148)


def add_bbox_padding(
    bbox: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """사람 bbox의 각 방향에 30% 여백을 더하고 이미지 범위로 제한한다."""
    x1, y1, x2, y2 = bbox
    bbox_width = max(0, x2 - x1)
    bbox_height = max(0, y2 - y1)
    padding_x = bbox_width * BBOX_PADDING
    padding_y = bbox_height * BBOX_PADDING

    padded_x1 = max(0, int(x1 - padding_x))
    padded_y1 = max(0, int(y1 - padding_y))
    padded_x2 = min(image_width, int(x2 + padding_x))
    padded_y2 = min(image_height, int(y2 + padding_y))
    return padded_x1, padded_y1, padded_x2, padded_y2


def classify_detected_people(
    frame: np.ndarray,
    detections: list[dict[str, Any]],
    pose_estimator: PoseEstimator,
    pose_classifier: PoseClassifier,
) -> tuple[list[dict[str, Any]], float, float]:
    """각 YOLO bbox를 crop하고 MediaPipe와 XGBoost를 순서대로 실행한다."""
    image_height, image_width = frame.shape[:2]
    person_results: list[dict[str, Any]] = []
    mediapipe_seconds = 0.0
    xgboost_seconds = 0.0

    for detection in detections:
        original_bbox = detection["bbox"]

        # 원래 YOLO bbox와 MediaPipe 입력용 padded bbox를 별도로 유지한다.
        padded_bbox = add_bbox_padding(original_bbox, image_width, image_height)
        padded_x1, padded_y1, padded_x2, padded_y2 = padded_bbox
        person_crop = frame[padded_y1:padded_y2, padded_x1:padded_x2]

        mediapipe_started = time.perf_counter()
        extraction = pose_estimator.extract(person_crop)
        mediapipe_seconds += time.perf_counter() - mediapipe_started

        # 분류기에는 이전과 같은 정규화 landmark만 넘긴다. world landmarks는 진단 로그 전용이다.
        landmarks = extraction.landmarks if extraction is not None else None
        world_landmarks = extraction.world_landmarks if extraction is not None else None

        prediction = None
        if landmarks is not None:
            xgboost_started = time.perf_counter()
            prediction = pose_classifier.classify(landmarks)
            xgboost_seconds += time.perf_counter() - xgboost_started

        person_results.append(
            {
                "bbox": original_bbox,
                "padded_bbox": padded_bbox,
                "person_confidence": detection["confidence"],
                "landmarks": landmarks,
                "world_landmarks": world_landmarks,
                "prediction": prediction,
            }
        )

    return person_results, mediapipe_seconds, xgboost_seconds


def _landmark_frame_points(
    frame: np.ndarray,
    landmarks: list[Any],
    padded_bbox: tuple[int, int, int, int],
) -> dict[int, tuple[int, int]]:
    """Body landmark만 crop 좌표에서 원본 frame 좌표로 변환한다."""
    padded_x1, padded_y1, padded_x2, padded_y2 = padded_bbox
    crop_width = padded_x2 - padded_x1
    crop_height = padded_y2 - padded_y1
    image_height, image_width = frame.shape[:2]

    points: dict[int, tuple[int, int]] = {}
    for index in BODY_LANDMARK_INDICES:
        landmark = landmarks[index]
        frame_x = padded_x1 + int(landmark.x * crop_width)
        frame_y = padded_y1 + int(landmark.y * crop_height)
        frame_x = min(max(frame_x, 0), image_width - 1)
        frame_y = min(max(frame_y, 0), image_height - 1)
        points[index] = (frame_x, frame_y)
    return points


def draw_body_pose(
    frame: np.ndarray,
    landmarks: list[Any],
    padded_bbox: tuple[int, int, int, int],
) -> None:
    """얼굴을 제외한 MediaPipe body skeleton을 FitRoute 색상으로 표시한다."""
    if len(landmarks) < 33:
        return
    points = _landmark_frame_points(frame, landmarks, padded_bbox)

    # 선을 먼저 그리고 관절점을 위에 올려 관절 구조가 또렷하게 보이게 한다.
    for start_index, end_index in BODY_CONNECTIONS:
        cv2.line(
            frame,
            points[start_index],
            points[end_index],
            MUTED_LIME,
            2,
            cv2.LINE_AA,
        )
    for index in BODY_LANDMARK_INDICES:
        cv2.circle(frame, points[index], 4, INK, -1, cv2.LINE_AA)
        cv2.circle(frame, points[index], 2, LIME, -1, cv2.LINE_AA)


def draw_person_results(
    frame: np.ndarray,
    primary_person: dict[str, Any] | None,
) -> None:
    """사용자-facing 화면에는 주 사용자의 body skeleton만 표시한다."""
    if primary_person is None or primary_person["landmarks"] is None:
        return
    draw_body_pose(
        frame,
        primary_person["landmarks"],
        primary_person["padded_bbox"],
    )


def find_primary_person_index(person_results: list[dict[str, Any]]) -> int | None:
    """Tracking 없이 화면에서 가장 큰 사람을 주 사용자로 선택한다."""
    if not person_results:
        return None

    largest_area = -1
    primary_index = 0
    for index, person_result in enumerate(person_results):
        x1, y1, x2, y2 = person_result["bbox"]
        bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
        if bbox_area > largest_area:
            largest_area = bbox_area
            primary_index = index

    return primary_index


def update_primary_person_smoothing(
    person_results: list[dict[str, Any]],
    prediction_smoother: PredictionSmoother,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """가장 큰 bbox 한 명의 Raw prediction만 stable prediction으로 변환한다."""
    primary_index = find_primary_person_index(person_results)
    if primary_index is None:
        smoothing_state = prediction_smoother.update_missing()
        return None, smoothing_state

    primary_person = person_results[primary_index]
    raw_prediction = primary_person["prediction"]

    if raw_prediction is None:
        smoothing_state = prediction_smoother.update_missing()
    else:
        smoothing_state = prediction_smoother.update(
            raw_prediction["label"],
            raw_prediction["confidence"],
        )

    primary_person["smoothing_state"] = smoothing_state
    return primary_person, smoothing_state


def update_display_pose(
    stable_pose: str | None,
    stable_confidence: float,
    previous_pose: str = "ANALYZING",
    previous_confidence: float = 0.0,
) -> tuple[str, float]:
    """Squat UI에는 허용된 pose만 전달하고 나머지는 마지막 정상값을 유지한다."""
    if stable_pose in ALLOWED_DISPLAY_POSES:
        return stable_pose.upper(), float(stable_confidence)
    return previous_pose, previous_confidence


def format_session_duration(duration_seconds: float) -> str:
    """세션 시간을 MM:SS 또는 한 시간 이상이면 HH:MM:SS로 표시한다."""
    total_seconds = int(max(0.0, duration_seconds))
    hours, remaining_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remaining_seconds, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _put_ui_text(
    image: np.ndarray,
    text: str,
    origin: tuple[int, int],
    scale: float,
    color: tuple[int, int, int] = WHITE,
    thickness: int = 1,
) -> None:
    cv2.putText(
        image,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


# 안내 사유 → (한글 문구, 한글 폰트를 쓸 수 없을 때의 영어 문구)
NOTICE_TEXT = {
    NOTICE_NOT_SIDE: ("카메라 쪽으로 옆모습이 보이게 서주세요", "TURN SIDEWAYS TO THE CAMERA"),
    NOTICE_FULL_BODY_INVALID: ("발끝까지 화면에 들어오게 서주세요", "STAND SO YOUR FEET ARE IN VIEW"),
}
NOTICE_COLOR = (94, 190, 255)
_KOREAN_FONT_CANDIDATES = (
    "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
)


@lru_cache(maxsize=1)
def _korean_font(size: int = 22):
    """한글을 그릴 수 있는 폰트. Pillow나 폰트 파일이 없으면 None(그러면 영어 문구로 대체한다)."""
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    for path in _KOREAN_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return None


@lru_cache(maxsize=8)
def _notice_text_layer(notice: str, width: int, band_height: int, font: Any) -> tuple[np.ndarray, np.ndarray] | None:
    """안내 문구를 한 번만 그려 둔 합성용 레이어. 문구(notice)·띠 크기·폰트가 바뀔 때만 다시 그린다.

    반환: (255 - 알파, 문구색 x 알파)를 uint16 배열로 둔 쌍. 프레임마다 영상 위에 `(영상 x (255-알파) + 문구색 x 알파) // 255`로
    합성만 하면 된다(PIL 변환·폰트 렌더링 없음). 폰트가 없으면 None(영어 문구로 대체).
    """
    if font is None:
        return None
    from PIL import Image, ImageDraw

    mask_image = Image.new("L", (width, band_height), 0)
    draw = ImageDraw.Draw(mask_image)
    text_width = draw.textlength(NOTICE_TEXT[notice][0], font=font)
    draw.text(((width - text_width) / 2, 9), NOTICE_TEXT[notice][0], font=font, fill=255)
    alpha = np.asarray(mask_image, dtype=np.uint16)[:, :, None]
    color = np.array(NOTICE_COLOR, dtype=np.uint16)  # BGR
    return 255 - alpha, color * alpha


def _draw_notice_band(canvas: np.ndarray, notice: str, left: int, right: int, bottom: int) -> None:
    """영상 영역 아래쪽에 반투명 띠를 깔고 안내 한 줄을 그린다. 안내가 있을 때만 호출한다."""
    _, english = NOTICE_TEXT[notice]
    band_height = 44
    top = bottom - band_height - 10
    region = canvas[top:top + band_height, left:right]
    region[:] = cv2.addWeighted(region, 0.25, np.full_like(region, INK), 0.75, 0)
    layer = _notice_text_layer(notice, region.shape[1], band_height, _korean_font())
    if layer is not None:
        inverse_alpha, foreground = layer
        region[:] = (region.astype(np.uint16) * inverse_alpha + foreground) // 255
        return
    scale = 0.62
    text_width = cv2.getTextSize(english, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)[0][0]
    _put_ui_text(canvas, english, (left + (right - left - text_width) // 2, top + 30), scale, NOTICE_COLOR, 2)


def _workout_ui_status(session_status: str, cloud_status: str) -> tuple[str, tuple[int, int, int]]:
    if session_status == "ACTIVE":
        return "ACTIVE", LIME
    if cloud_status == "SAVED":
        return "SAVED", LIME
    if cloud_status == "FAILED":
        return "RETRY AVAILABLE", (94, 190, 255)
    return "READY", MUTED_TEXT


@lru_cache(maxsize=4)
def _workout_ui_template(
    frame_height: int,
    frame_width: int,
    panel_width: int,
    header_height: int,
    footer_height: int,
) -> np.ndarray:
    """해상도별 고정 HUD를 한 번만 그려 매 frame의 폰트 렌더링을 줄인다."""
    canvas = np.full(
        (frame_height + header_height + footer_height, frame_width + panel_width, 3),
        INK,
        dtype=np.uint8,
    )
    panel_x = frame_width
    cv2.rectangle(
        canvas,
        (panel_x, header_height),
        (frame_width + panel_width - 1, header_height + frame_height),
        SURFACE,
        -1,
    )
    cv2.line(canvas, (panel_x, header_height), (panel_x, header_height + frame_height), ELEVATED, 1)
    cv2.line(canvas, (0, header_height - 1), (canvas.shape[1], header_height - 1), ELEVATED, 1)
    cv2.line(canvas, (0, header_height + frame_height), (canvas.shape[1], header_height + frame_height), ELEVATED, 1)

    _put_ui_text(canvas, "FitRoute", (24, 42), 0.83, WHITE, 2)
    _put_ui_text(canvas, ".", (135, 42), 0.83, LIME, 3)

    left = panel_x + 26
    right = frame_width + panel_width - 26
    _put_ui_text(canvas, "SESSION", (left, header_height + 42), 0.42, MUTED_TEXT, 1)
    cv2.line(canvas, (left, header_height + 88), (right, header_height + 88), ELEVATED, 1)

    metric_y = header_height + 126
    metric_gap = max(76, min(112, max(280, frame_height - 150) // 4))
    for label in ("SESSION TIME", "SQUAT COUNT", "CURRENT POSE", "CONFIDENCE"):
        _put_ui_text(canvas, label, (left, metric_y), 0.39, MUTED_TEXT, 1)
        metric_y += metric_gap

    footer_y = header_height + frame_height + 34
    _put_ui_text(canvas, "S  START", (24, footer_y), 0.45, WHITE, 1)
    _put_ui_text(canvas, "E  END WORKOUT", (132, footer_y), 0.45, WHITE, 1)
    _put_ui_text(canvas, "R  RESET", (300, footer_y), 0.45, WHITE, 1)
    _put_ui_text(canvas, "P  RETRY SAVE", (412, footer_y), 0.45, MUTED_TEXT, 1)
    _put_ui_text(canvas, "Q / ESC  QUIT", (canvas.shape[1] - 145, footer_y), 0.42, MUTED_TEXT, 1)
    return canvas


def compose_workout_ui(
    frame: np.ndarray,
    exercise_status: dict[str, Any],
    session_status: dict[str, Any],
    cloud_status: str,
    display_pose: str,
    display_confidence: float,
    tracking_active: bool,
    notice: str | None = None,
) -> np.ndarray:
    """추론 frame을 유지하면서 고정 크기 FitRoute HUD를 바깥에 구성한다. notice가 있으면 영상 아래쪽에 안내 한 줄을 보인다."""
    frame_height, frame_width = frame.shape[:2]
    header_height = 64
    footer_height = 54
    panel_width = max(270, min(350, int(frame_width * 0.32)))
    canvas = _workout_ui_template(
        frame_height,
        frame_width,
        panel_width,
        header_height,
        footer_height,
    ).copy()
    canvas[header_height:header_height + frame_height, :frame_width] = frame
    if notice in NOTICE_TEXT:
        _draw_notice_band(canvas, notice, 12, frame_width - 12, header_height + frame_height)

    panel_x = frame_width

    # Header
    mode_text = exercise_status["mode"].upper()
    mode_width = cv2.getTextSize(mode_text, cv2.FONT_HERSHEY_SIMPLEX, 0.66, 2)[0][0]
    _put_ui_text(canvas, mode_text, ((canvas.shape[1] - mode_width) // 2, 41), 0.66, WHITE, 2)
    ai_text = "AI ACTIVE" if tracking_active else "SEARCHING"
    ai_color = LIME if tracking_active else MUTED_TEXT
    ai_width = cv2.getTextSize(ai_text, cv2.FONT_HERSHEY_SIMPLEX, 0.54, 1)[0][0]
    ai_x = canvas.shape[1] - ai_width - 25
    cv2.circle(canvas, (ai_x - 12, 34), 4, ai_color, -1, cv2.LINE_AA)
    _put_ui_text(canvas, ai_text, (ai_x, 39), 0.54, ai_color, 1)

    # Right session panel
    left = panel_x + 26
    status_text, status_color = _workout_ui_status(session_status["status"], cloud_status)
    _put_ui_text(canvas, status_text, (left, header_height + 68), 0.60, status_color, 2)

    metric_y = header_height + 126
    metrics = (
        (format_session_duration(session_status["elapsed_seconds"]), 0.93),
        (str(exercise_status["squat_count"]), 1.18),
        (display_pose, 0.78),
        (f"{display_confidence * 100:.1f}%" if display_confidence > 0 else "--", 0.78),
    )
    available_height = max(280, frame_height - 150)
    metric_gap = max(76, min(112, available_height // len(metrics)))
    for value, value_scale in metrics:
        _put_ui_text(canvas, value, (left, metric_y + 33), value_scale, WHITE, 2)
        metric_y += metric_gap

    save_label = {
        "READY": "SAVE READY",
        "SAVING": "SAVING...",
        "SAVED": "WORKOUT SAVED",
        "FAILED": "SAVE FAILED - PRESS P",
        "DISABLED": "LOCAL ONLY",
    }.get(cloud_status, "SAVE READY")
    save_color = (105, 105, 235) if cloud_status == "FAILED" else (LIME if cloud_status == "SAVED" else MUTED_TEXT)
    _put_ui_text(canvas, save_label, (left, header_height + frame_height - 27), 0.40, save_color, 1)

    return canvas


def print_workout_summary(summary: dict[str, Any]) -> None:
    """숫자형 summary는 유지하고 terminal 표시만 읽기 쉽게 변환한다."""
    print("\n========================================")
    print("Workout Session Summary")
    print("========================================")
    print(f"Date:          {summary['workout_date']}")
    print(f"Started:       {summary['started_at']}")
    print(f"Ended:         {summary['ended_at']}")
    print(f"Workout Time:  {format_session_duration(summary['workout_seconds'])}")
    print(f"Squat Count:   {summary['squat_count']}")
    print(f"Stretch Time:  {format_session_duration(summary['stretch_seconds'])}")


def complete_session(
    exercise_counter: ExerciseCounter,
    workout_session: WorkoutSession,
    workout_uploader: WorkoutUploader,
    current_time: float,
) -> dict[str, Any] | None:
    """Finalize, print, and upload a session through the shared safe path."""
    summary = workout_session.end(exercise_counter, current_time)
    if summary is None:
        return None
    print_workout_summary(summary)
    workout_uploader.submit(summary)
    return summary


def handle_keyboard_input(
    pressed_key: int,
    exercise_counter: ExerciseCounter,
    workout_session: WorkoutSession,
    workout_uploader: WorkoutUploader,
    current_time: float,
) -> bool:
    """Session, 운동 모드, reset 키를 처리하고 종료 여부를 반환한다."""
    if pressed_key in (27, ord("q"), ord("Q")):
        if workout_session.is_active:
            complete_session(
                exercise_counter,
                workout_session,
                workout_uploader,
                current_time,
            )
        return True

    if pressed_key in (ord("p"), ord("P")):
        workout_uploader.retry()
        return False

    if pressed_key in (ord("s"), ord("S")):
        if workout_uploader.pending_summary is not None:
            print("[Cloud] Retry the pending workout with P before starting a new session.")
            return False
        workout_session.start(exercise_counter, current_time)
        return False

    if pressed_key in (ord("e"), ord("E")):
        complete_session(
            exercise_counter,
            workout_session,
            workout_uploader,
            current_time,
        )
        return False

    mode_by_key = {
        ord("0"): IDLE_MODE,
        ord("1"): SQUAT_MODE,
        ord("2"): STRETCH_MODE,
    }
    if pressed_key in mode_by_key:
        exercise_counter.set_mode(mode_by_key[pressed_key], current_time)
    elif pressed_key in (ord("r"), ord("R")):
        exercise_counter.reset_current_exercise(current_time)

    return False


def auto_start_session_when_ready(
    enabled: bool,
    already_started: bool,
    exercise_counter: ExerciseCounter,
    workout_session: WorkoutSession,
    current_time: float,
) -> bool:
    """첫 inference frame이 정상 완료된 뒤 Launcher 요청 세션을 한 번만 시작한다."""
    if not enabled or already_started:
        return already_started
    started = workout_session.start(exercise_counter, current_time)
    if started:
        print("Workout session auto-started.")
    return started


def print_startup_information(
    detector: PersonDetector,
    pose_classifier: PoseClassifier,
) -> None:
    print("========================================")
    print("AI Exercise Assistant")
    print("========================================")
    print(f"Detector:     YOLO26n {detector.backend}")
    print("Pose:         MediaPipe PoseLandmarker")
    print("Classifier:   XGBoost")
    print(f"Pose Classes: {len(pose_classifier.classes)}")
    print(f"Features:     {pose_classifier.FEATURE_COUNT}")


def print_benchmark(benchmark: dict[str, Any]) -> None:
    processed_frames = len(benchmark["total"])
    elapsed = benchmark["elapsed"]

    print("\n========================================")
    print("Full Pipeline Benchmark")
    print("========================================")
    print(f"Processed Frames: {processed_frames}")
    print(f"Elapsed:          {elapsed:.2f} s")

    if not processed_frames or elapsed <= 0:
        print("End-to-End FPS:          N/A (warmup was not completed)")
        print("Inference FPS:           N/A")
        print("Min Inference FPS:       N/A")
        print("Max Inference FPS:       N/A")
        print("Average YOLO:     N/A")
        print("Average MediaPipe:N/A")
        print("Average XGBoost:  N/A")
        print("Average Smoothing:N/A")
        print("Average Exercise Logic:N/A")
        print("Average Draw:     N/A")
        print("Average Inference Time:N/A")
        print(f"\nYOLO26n TensorRT only: {YOLO_ONLY_BASELINE_FPS:.2f} FPS")
        print(f"Previous End-to-End:   {PREVIOUS_END_TO_END_FPS:.2f} FPS")
        print("Full pipeline:         N/A")
        return

    frame_rates = [1.0 / duration for duration in benchmark["total"] if duration > 0]
    average_inference_seconds = float(np.mean(benchmark["total"]))
    end_to_end_fps = processed_frames / elapsed
    inference_fps = 1.0 / average_inference_seconds
    print(f"End-to-End FPS:          {end_to_end_fps:.2f}")
    print(f"Inference FPS:           {inference_fps:.2f}")
    print(f"Min Inference FPS:       {min(frame_rates):.2f}")
    print(f"Max Inference FPS:       {max(frame_rates):.2f}")
    print(f"Average YOLO:     {np.mean(benchmark['yolo']) * 1000:.2f} ms")
    print(f"Average MediaPipe:{np.mean(benchmark['mediapipe']) * 1000:9.2f} ms")
    print(f"Average XGBoost:  {np.mean(benchmark['xgboost']) * 1000:.2f} ms")
    print(f"Average Smoothing:{np.mean(benchmark['smoothing']) * 1000:9.2f} ms")
    print(f"Average Exercise Logic:{np.mean(benchmark['exercise']) * 1000:7.2f} ms")
    print(f"Average Draw:     {np.mean(benchmark['draw']) * 1000:.2f} ms")
    if any(benchmark.get("sequence", ())):
        print(f"Average Sequence Log: {np.mean(benchmark['sequence']) * 1000:.3f} ms")
    print(f"Average Inference Time:{average_inference_seconds * 1000:8.2f} ms")
    print(f"\nYOLO26n TensorRT only: {YOLO_ONLY_BASELINE_FPS:.2f} FPS")
    print(f"Previous End-to-End:   {PREVIOUS_END_TO_END_FPS:.2f} FPS")
    print(f"Full pipeline:         {end_to_end_fps:.2f} FPS")


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exercise",
        choices=(SQUAT_MODE, STRETCH_MODE, IDLE_MODE),
        default=SQUAT_MODE,
        help="시작할 운동 모드입니다. Web Exercise Home의 Squat 선택은 squat을 전달합니다.",
    )
    parser.add_argument(
        "--benchmark-seconds",
        type=float,
        default=None,
        help="30-frame warmup 후 지정한 초 동안 측정하고 자동 종료합니다.",
    )
    parser.add_argument(
        "--auto-start-session",
        action="store_true",
        help="첫 inference frame 준비 후 Workout Session을 자동 시작합니다.",
    )
    parser.add_argument(
        "--diagnose-runtime",
        action="store_true",
        help="Camera와 network 없이 frozen runtime과 모델 파일을 검증합니다.",
    )
    parser.add_argument(
        "--log-sequence",
        action="store_true",
        default=SEQUENCE_LOGGING_ENABLED,
        help="(진단용) landmark 시퀀스를 data/landmark_sequences/에 JSONL로 기록합니다. 영상은 저장하지 않으며 기본은 꺼져 있습니다.",
    )
    parser.add_argument(
        "--session-posture",
        choices=INTENDED_POSTURES,
        default=None,
        help="--log-sequence 세션의 의도한 자세: normal(정상), shallow(얕음), torso_lean(상체 숙임), heel_lift(뒤꿈치 들림).",
    )
    parser.add_argument(
        "--session-view",
        choices=CAMERA_VIEWS,
        default=None,
        help="--log-sequence 세션의 카메라 시점: side(측면), oblique(사선), front(정면).",
    )
    parser.add_argument(
        "--session-note",
        default=None,
        help="--log-sequence 세션에 남길 자유 메모.",
    )
    parser.add_argument(
        "--log-face-landmarks",
        action="store_true",
        default=SEQUENCE_LOG_FACE_LANDMARKS,
        help="--log-sequence에서 얼굴 landmark(0~10번)의 좌표까지 저장합니다. 기본은 저장하지 않으며(코의 visibility만 남김) 꺼져 있습니다.",
    )
    arguments = parser.parse_args(argv)
    if arguments.benchmark_seconds is not None and arguments.benchmark_seconds <= 0:
        parser.error("--benchmark-seconds must be greater than 0")
    session_options = (arguments.session_posture, arguments.session_view, arguments.session_note)
    if not arguments.log_sequence and (
        any(option is not None for option in session_options) or arguments.log_face_landmarks
    ):
        parser.error(
            "--session-posture, --session-view, --session-note and --log-face-landmarks "
            "require --log-sequence"
        )
    return arguments


def start_sequence_recording(
    arguments: argparse.Namespace,
    detector: PersonDetector,
    pose_classifier: PoseClassifier,
    geometry_tracker: GeometryTracker | None = None,
) -> SequenceRecorder:
    """--log-sequence가 켜졌을 때만 호출한다. 기록 파일을 만들고 헤더(메타데이터, 임계값)를 남긴다.

    geometry_tracker는 RepTracker와 공유하는 추적기다. 없으면 기록기가 자기 것을 만든다.
    """
    logger = SequenceLogger(
        LANDMARK_SEQUENCE_DIR,
        metadata=session_metadata(
            arguments.session_posture,
            arguments.session_view,
            arguments.session_note,
        ),
        runtime={
            "detector_backend": detector.backend,
            "pose_classes": list(pose_classifier.classes),
            "exercise_mode": arguments.exercise,
        },
        options={"face_landmarks": arguments.log_face_landmarks},
    )
    path = logger.start()
    face_note = "face landmark coordinates INCLUDED" if arguments.log_face_landmarks else "face landmark coordinates not stored"
    print(f"[Sequence] Recording landmark sequence (no video, {face_note}): {path}")
    return SequenceRecorder(
        logger,
        geometry_tracker if geometry_tracker is not None else GeometryTracker(),
        include_face_landmarks=arguments.log_face_landmarks,
    )


def finish_sequence_log(
    sequence_recorder: SequenceRecorder | None,
    exercise_counter: ExerciseCounter,
    *,
    ask_actual_reps: bool,
    input_fn=input,
    interactive: bool | None = None,
) -> None:
    """로깅을 끝낸다. 대화형으로 Q/ESC 종료한 --log-sequence 실행이면 먼저 실제 반복 횟수를 묻고 footer로 남긴다.

    로깅을 켜지 않았으면(recorder가 None) 아무것도 묻지 않는다. 패키징 빌드·비대화형 입력에서는 묻지 않는다(미입력으로 기록).
    """
    if sequence_recorder is None:
        return
    try:
        if ask_actual_reps:
            footer = collect_session_footer(
                exercise_counter.squat_count, mode=exercise_counter.exercise_mode, input_fn=input_fn, interactive=interactive
            )
            if footer["prompt"] != "unavailable" or not getattr(sys, "frozen", False):
                sequence_recorder.logger.log_footer(footer)
    finally:
        sequence_recorder.close()
        print(
            f"[Sequence] Saved: {sequence_recorder.logger.path} "
            f"(dropped frames: {sequence_recorder.logger.frames_dropped})"
        )


def create_exercise_counter() -> ExerciseCounter:
    """settings.USE_REP_TRACKER가 True면 RepTracker로 스쿼트를 세고, False면 v0.1.x(stable 라벨 전이)로 센다."""
    import config.settings as settings

    return ExerciseCounter(rep_tracker=RepTracker() if settings.USE_REP_TRACKER else None)


def run_geometry(
    exercise_counter: ExerciseCounter,
    geometry_tracker: GeometryTracker,
    primary_person: dict[str, Any] | None,
    frame_size: tuple[int, int],
    timestamp: float,
    *,
    recording: bool,
    was_active: bool,
):
    """한 프레임의 기하 분석(무릎각·BodyLock)을 필요할 때만 한다. 반환: (이번에 켜져 있었나, (TrackedFrame|None, LockState)|None, RepFrame|None).

    RepTracker로 스쿼트를 세는 중(settings.USE_REP_TRACKER가 True이고 squat 모드)이거나 로깅 중일 때만 돌린다.
    꺼져 있다 켜질 때는 오래된 잠금과 평활화를 버린다(reset). USE_REP_TRACKER가 False면 로깅이 아닐 때 분석하지 않는다(v0.1.x와 같음).
    """
    active = (
        exercise_counter.uses_rep_tracker and exercise_counter.exercise_mode == SQUAT_MODE
    ) or recording
    if active and not was_active:
        geometry_tracker.reset()
    if not active:
        return False, None, None
    tracked, lock_state, rep_frame = track_primary_person(geometry_tracker, primary_person, frame_size, timestamp)
    return True, (tracked, lock_state), rep_frame


def main() -> int:
    arguments = parse_arguments()
    if arguments.diagnose_runtime:
        return run_runtime_diagnostic()

    camera = Camera()
    detector = PersonDetector()
    pose_classifier = PoseClassifier()
    pose_estimator = PoseEstimator()
    prediction_smoother = PredictionSmoother()
    geometry_tracker = GeometryTracker()
    exercise_counter = create_exercise_counter()
    exercise_counter.set_mode(arguments.exercise, time.perf_counter())
    workout_session = WorkoutSession()
    workout_uploader = WorkoutUploader(create_api_client_from_environment())
    print_startup_information(detector, pose_classifier)
    if workout_uploader.api_client is None:
        print("[Cloud] FitRoute API token not configured.")
        print("[Cloud] Workout sessions will not be uploaded.")
    else:
        print("[Cloud] Workout upload is ready.")

    sequence_recorder = (
        start_sequence_recording(arguments, detector, pose_classifier, geometry_tracker)
        if arguments.log_sequence
        else None
    )

    frame_count = 0
    quit_requested = False  # Q/ESC로 직접 종료했는가(벤치마크 시간 종료·예외 종료와 구분)
    measurement_started: float | None = None
    display_pose = "ANALYZING"
    display_confidence = 0.0
    auto_start_completed = False
    geometry_was_active = False
    benchmark: dict[str, Any] = {
        "yolo": [],
        "mediapipe": [],
        "xgboost": [],
        "smoothing": [],
        "exercise": [],
        "draw": [],
        "sequence": [],
        "total": [],
        "elapsed": 0.0,
    }

    try:
        camera.open()
        while True:
            frame = camera.read()
            pipeline_started = time.perf_counter()

            yolo_started = time.perf_counter()
            detections = detector.detect(frame)
            yolo_seconds = time.perf_counter() - yolo_started

            person_results, mediapipe_seconds, xgboost_seconds = classify_detected_people(
                frame,
                detections,
                pose_estimator,
                pose_classifier,
            )

            smoothing_started = time.perf_counter()
            primary_person, smoothing_state = update_primary_person_smoothing(
                person_results,
                prediction_smoother,
            )
            smoothing_seconds = time.perf_counter() - smoothing_started

            # 운동 판단에는 Raw prediction이 아닌 stable pose만 전달한다.
            exercise_started = time.perf_counter()
            current_time = time.perf_counter()
            stable_pose = smoothing_state["stable_label"]
            geometry_was_active, geometry, rep_frame = run_geometry(
                exercise_counter,
                geometry_tracker,
                primary_person,
                (frame.shape[1], frame.shape[0]),
                pipeline_started,
                recording=sequence_recorder is not None,
                was_active=geometry_was_active,
            )
            exercise_counter.update(stable_pose, current_time, rep_frame)
            display_pose, display_confidence = update_display_pose(
                stable_pose,
                smoothing_state["stable_confidence"],
                display_pose,
                display_confidence,
            )
            auto_start_completed = auto_start_session_when_ready(
                arguments.auto_start_session,
                auto_start_completed,
                exercise_counter,
                workout_session,
                current_time,
            )
            exercise_status = exercise_counter.get_status(current_time)
            workout_session.update(current_time)
            session_status = workout_session.get_status(current_time)
            exercise_seconds = time.perf_counter() - exercise_started

            draw_started = time.perf_counter()
            draw_person_results(frame, primary_person)
            display_frame = compose_workout_ui(
                frame,
                exercise_status,
                session_status,
                workout_uploader.cloud_status,
                display_pose,
                display_confidence,
                primary_person is not None and primary_person["landmarks"] is not None,
                exercise_status["rep_notice"],
            )
            draw_seconds = time.perf_counter() - draw_started

            # 진단 로깅(기본 꺼짐). 원래 stable 라벨(표시 필터 전)과 표시 라벨을 함께 남긴다.
            sequence_started = time.perf_counter()
            if sequence_recorder is not None:
                sequence_recorder.record(
                    frame_size=(frame.shape[1], frame.shape[0]),
                    primary_person=primary_person,
                    smoothing_state=smoothing_state,
                    display_pose=display_pose,
                    display_confidence=display_confidence,
                    capture_time=pipeline_started,
                    logic_time=current_time,
                    geometry=geometry,
                    rep=exercise_counter.rep_diagnostics(),
                )
            sequence_seconds = time.perf_counter() - sequence_started
            total_seconds = time.perf_counter() - pipeline_started

            frame_count += 1
            if frame_count > WARMUP_FRAMES:
                if measurement_started is None:
                    measurement_started = pipeline_started
                benchmark["yolo"].append(yolo_seconds)
                benchmark["mediapipe"].append(mediapipe_seconds)
                benchmark["xgboost"].append(xgboost_seconds)
                benchmark["smoothing"].append(smoothing_seconds)
                benchmark["exercise"].append(exercise_seconds)
                benchmark["draw"].append(draw_seconds)
                benchmark["sequence"].append(sequence_seconds)
                benchmark["total"].append(total_seconds)

            cv2.imshow(WINDOW_NAME, display_frame)
            pressed_key = cv2.waitKey(1) & 0xFF
            should_quit = handle_keyboard_input(
                pressed_key,
                exercise_counter,
                workout_session,
                workout_uploader,
                time.perf_counter(),
            )
            if should_quit:
                quit_requested = True
                break

            if (
                arguments.benchmark_seconds is not None
                and measurement_started is not None
                and time.perf_counter() - measurement_started >= arguments.benchmark_seconds
            ):
                break
    finally:
        if measurement_started is not None:
            benchmark["elapsed"] = time.perf_counter() - measurement_started
        if workout_session.is_active:
            complete_session(
                exercise_counter,
                workout_session,
                workout_uploader,
                time.perf_counter(),
            )
        if sequence_recorder is not None and quit_requested:
            camera.release()
            cv2.destroyAllWindows()  # 터미널 입력을 받는 동안 멈춘 영상 창이 남지 않게 한다
        finish_sequence_log(
            sequence_recorder,
            exercise_counter,
            ask_actual_reps=quit_requested,
        )
        pose_estimator.close()
        camera.release()
        cv2.destroyAllWindows()

    print_benchmark(benchmark)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
