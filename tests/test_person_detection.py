"""Manual webcam benchmark for YOLO26n person detection."""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2

from src.camera import Camera
from src.person_detector import PersonDetector


WARMUP_FRAMES = 30
WINDOW_NAME = "YOLO26n Person Detection Test"


def main() -> None:
    camera = Camera()
    detector = PersonDetector()
    frame_count = 0
    measured_fps: list[float] = []
    measurement_started: float | None = None

    try:
        camera.open()
        while True:
            frame_started = time.perf_counter()
            frame = camera.read()
            detections = detector.detect(frame)
            frame_elapsed = time.perf_counter() - frame_started
            frame_count += 1

            if frame_count > WARMUP_FRAMES:
                if measurement_started is None:
                    measurement_started = frame_started
                measured_fps.append(1.0 / frame_elapsed if frame_elapsed > 0 else 0.0)

            for detection in detections:
                x1, y1, x2, y2 = detection["bbox"]
                confidence = detection["confidence"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (40, 220, 40), 2)
                cv2.putText(
                    frame,
                    f"Person {confidence:.2f}",
                    (x1, max(24, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (40, 220, 40),
                    2,
                    cv2.LINE_AA,
                )

            current_fps = 1.0 / frame_elapsed if frame_elapsed > 0 else 0.0
            cv2.putText(
                frame,
                f"FPS {current_fps:.1f}",
                (16, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF in (27, ord("q"), ord("Q")):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

    elapsed = (
        time.perf_counter() - measurement_started
        if measurement_started is not None
        else 0.0
    )
    print("\n========================================")
    print("Detection Benchmark")
    print("========================================")
    print(f"Frames:      {len(measured_fps)}")
    print(f"Elapsed:     {elapsed:.2f} s")
    if measured_fps:
        print(f"Average FPS: {len(measured_fps) / elapsed:.2f}" if elapsed else "Average FPS: 0.00")
        print(f"Min FPS:     {min(measured_fps):.2f}")
        print(f"Max FPS:     {max(measured_fps):.2f}")
    else:
        print("Average FPS: N/A (warmup was not completed)")
        print("Min FPS:     N/A")
        print("Max FPS:     N/A")


if __name__ == "__main__":
    main()

