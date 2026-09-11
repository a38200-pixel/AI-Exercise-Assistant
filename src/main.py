"""Initial webcam + person detection integration test."""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2

from src.camera import Camera
from src.person_detector import PersonDetector


WINDOW_NAME = "AI Exercise Assistant"


def main() -> None:
    camera = Camera()
    detector = PersonDetector()

    try:
        camera.open()
        while True:
            frame = camera.read()
            for detection in detector.detect(frame):
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
            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF in (27, ord("q"), ord("Q")):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

