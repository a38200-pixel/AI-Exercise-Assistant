"""Real-time YOLO -> MediaPipe -> XGBoost pose classification pipeline."""

import argparse
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np

from config.settings import BBOX_PADDING, SHOW_SMOOTHING_DEBUG
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


WINDOW_NAME = "AI Exercise Assistant"
WARMUP_FRAMES = 30
YOLO_ONLY_BASELINE_FPS = 29.44
PREVIOUS_END_TO_END_FPS = 15.89


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


def draw_landmark_points(
    frame: np.ndarray,
    landmarks: list[Any],
    padded_bbox: tuple[int, int, int, int],
) -> None:
    """Crop 정규화 좌표를 원본 frame 좌표로 변환해 점으로 표시한다."""
    padded_x1, padded_y1, padded_x2, padded_y2 = padded_bbox
    crop_width = padded_x2 - padded_x1
    crop_height = padded_y2 - padded_y1
    image_height, image_width = frame.shape[:2]

    for landmark in landmarks:
        frame_x = padded_x1 + int(landmark.x * crop_width)
        frame_y = padded_y1 + int(landmark.y * crop_height)
        frame_x = min(max(frame_x, 0), image_width - 1)
        frame_y = min(max(frame_y, 0), image_height - 1)
        cv2.circle(frame, (frame_x, frame_y), 3, (0, 215, 255), -1)


def draw_person_results(frame: np.ndarray, person_results: list[dict[str, Any]]) -> None:
    for person_result in person_results:
        x1, y1, x2, y2 = person_result["bbox"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (40, 220, 40), 2)

        landmarks = person_result["landmarks"]
        prediction = person_result["prediction"]
        smoothing_state = person_result.get("smoothing_state")

        # 주 사용자는 debug 표시 여부와 관계없이 stable 결과를 bbox에 표시한다.
        if smoothing_state is not None and smoothing_state["stable_label"] is not None:
            label_text = (
                f"Stable {smoothing_state['stable_label']} "
                f"{smoothing_state['stable_confidence'] * 100:.1f}%"
            )
            label_color = (40, 220, 40)
        elif landmarks is None or prediction is None:
            label_text = "Pose not detected"
            label_color = (0, 165, 255)
        else:
            label_text = f"{prediction['label']} {prediction['confidence'] * 100:.1f}%"
            label_color = (40, 220, 40)

        if landmarks is not None:
            draw_landmark_points(frame, landmarks, person_result["padded_bbox"])

        cv2.putText(
            frame,
            label_text,
            (x1, max(24, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            label_color,
            2,
            cv2.LINE_AA,
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


def draw_smoothing_status(
    frame: np.ndarray,
    primary_person: dict[str, Any] | None,
    smoothing_state: dict[str, Any],
) -> None:
    """Raw, Stable, Candidate를 구분해 화면 왼쪽 위에 표시한다."""
    raw_prediction = primary_person["prediction"] if primary_person is not None else None
    if raw_prediction is None:
        raw_text = "Raw    : Pose not detected"
    else:
        raw_text = (
            f"Raw    : {raw_prediction['label']} "
            f"{raw_prediction['confidence'] * 100:.1f}%"
        )


def format_duration(duration_seconds: float) -> str:
    """누적 초를 화면용 MM:SS.s 문자열로 변환한다."""
    minutes = int(duration_seconds // 60)
    remaining_seconds = duration_seconds - minutes * 60
    return f"{minutes:02d}:{remaining_seconds:04.1f}"


def draw_exercise_status(frame: np.ndarray, exercise_status: dict[str, Any]) -> None:
    """현재 운동 모드, stable pose, 기록과 state를 화면에 표시한다."""
    exercise_mode = exercise_status["mode"]
    stable_pose = exercise_status["stable_pose"] or "-"

    if exercise_mode == SQUAT_MODE:
        record_text = f"Count  : {exercise_status['squat_count']}"
    elif exercise_mode == STRETCH_MODE:
        duration_text = format_duration(exercise_status["stretch_seconds"])
        record_text = f"Time   : {duration_text}"
    else:
        record_text = "Record : -"

    exercise_lines = (
        f"Mode   : {exercise_mode.upper()}",
        f"Pose   : {stable_pose}",
        record_text,
        f"Step   : {exercise_status['state']}",
    )
    for line_index, status_text in enumerate(exercise_lines):
        cv2.putText(
            frame,
            status_text,
            (16, 158 + line_index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 230, 120),
            2,
            cv2.LINE_AA,
        )

    image_height = frame.shape[0]
    cv2.putText(
        frame,
        "[1] Squat  [2] Stretch  [0] Idle",
        (16, max(28, image_height - 42)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "[R] Reset current exercise  [Q/ESC] Quit",
        (16, max(52, image_height - 16)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )


def handle_keyboard_input(
    pressed_key: int,
    exercise_counter: ExerciseCounter,
    current_time: float,
) -> bool:
    """운동 모드와 reset 키를 처리하고 종료 여부를 반환한다."""
    if pressed_key in (27, ord("q"), ord("Q")):
        return True

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

    stable_label = smoothing_state["stable_label"]
    if stable_label is None:
        stable_text = "Stable : -"
    else:
        stable_text = (
            f"Stable : {stable_label} "
            f"{smoothing_state['stable_confidence'] * 100:.1f}%"
        )

    candidate_label = smoothing_state["candidate_label"]
    if candidate_label is None:
        candidate_text = "Next   : -"
    else:
        candidate_text = (
            f"Next   : {candidate_label} "
            f"{smoothing_state['candidate_count']}/{smoothing_state['required_count']}"
        )

    status_lines = (raw_text, stable_text, candidate_text)
    for line_index, status_text in enumerate(status_lines):
        cv2.putText(
            frame,
            status_text,
            (16, 62 + line_index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


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
    print_startup_information(detector, pose_classifier)

    frame_count = 0
    measurement_started: float | None = None
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
            exercise_status = exercise_counter.get_status(current_time)
            exercise_seconds = time.perf_counter() - exercise_started

            draw_started = time.perf_counter()
            draw_person_results(frame, person_results)
            if SHOW_SMOOTHING_DEBUG:
                draw_smoothing_status(frame, primary_person, smoothing_state)
            draw_exercise_status(frame, exercise_status)

            cv2.putText(
                frame,
                f"YOLO26n {detector.backend}",
                (16, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
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

            cv2.imshow(WINDOW_NAME, frame)
            pressed_key = cv2.waitKey(1) & 0xFF
            should_quit = handle_keyboard_input(
                pressed_key,
                exercise_counter,
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
        pose_estimator.close()
        camera.release()
        cv2.destroyAllWindows()

    print_benchmark(benchmark)


if __name__ == "__main__":
    main()
