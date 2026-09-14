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

from config.settings import BBOX_PADDING
from src.api_client import WorkoutUploader, create_api_client_from_environment
from src.camera import Camera
from src.exercise_counter import (
    IDLE_MODE,
    SQUAT_MODE,
    STRETCH_MODE,
    ExerciseCounter,
)
from src.person_detector import PersonDetector
from src.pose_classifier import PoseClassifier
from src.pose_estimator import PoseEstimator
from src.prediction_smoother import PredictionSmoother
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
        landmarks = pose_estimator.extract(person_crop)
        mediapipe_seconds += time.perf_counter() - mediapipe_started

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
) -> np.ndarray:
    """추론 frame을 유지하면서 고정 크기 FitRoute HUD를 바깥에 구성한다."""
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
    print(f"Average Inference Time:{average_inference_seconds * 1000:8.2f} ms")
    print(f"\nYOLO26n TensorRT only: {YOLO_ONLY_BASELINE_FPS:.2f} FPS")
    print(f"Previous End-to-End:   {PREVIOUS_END_TO_END_FPS:.2f} FPS")
    print(f"Full pipeline:         {end_to_end_fps:.2f} FPS")


def parse_arguments() -> argparse.Namespace:
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
    arguments = parser.parse_args()
    if arguments.benchmark_seconds is not None and arguments.benchmark_seconds <= 0:
        parser.error("--benchmark-seconds must be greater than 0")
    return arguments


def main() -> None:
    arguments = parse_arguments()
    camera = Camera()
    detector = PersonDetector()
    pose_classifier = PoseClassifier()
    pose_estimator = PoseEstimator()
    prediction_smoother = PredictionSmoother()
    exercise_counter = ExerciseCounter()
    exercise_counter.set_mode(arguments.exercise, time.perf_counter())
    workout_session = WorkoutSession()
    workout_uploader = WorkoutUploader(create_api_client_from_environment())
    print_startup_information(detector, pose_classifier)
    if workout_uploader.api_client is None:
        print("[Cloud] FitRoute API token not configured.")
        print("[Cloud] Workout sessions will not be uploaded.")
    else:
        print("[Cloud] Workout upload is ready.")

    frame_count = 0
    measurement_started: float | None = None
    display_pose = "ANALYZING"
    display_confidence = 0.0
    benchmark: dict[str, Any] = {
        "yolo": [],
        "mediapipe": [],
        "xgboost": [],
        "smoothing": [],
        "exercise": [],
        "draw": [],
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
            exercise_counter.update(stable_pose, current_time)
            display_pose, display_confidence = update_display_pose(
                stable_pose,
                smoothing_state["stable_confidence"],
                display_pose,
                display_confidence,
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
            )
            draw_seconds = time.perf_counter() - draw_started
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
        pose_estimator.close()
        camera.release()
        cv2.destroyAllWindows()

    print_benchmark(benchmark)


if __name__ == "__main__":
    main()
