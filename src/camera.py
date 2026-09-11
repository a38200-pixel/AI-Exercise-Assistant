"""Small OpenCV webcam wrapper with a Windows MSMF fallback."""

import cv2

from config.settings import CAMERA_INDEX


class Camera:
    def __init__(self, index: int = CAMERA_INDEX) -> None:
        self.index = index
        self.capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        if self.capture is not None and self.capture.isOpened():
            return

        capture = cv2.VideoCapture(self.index, cv2.CAP_MSMF)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(self.index)

        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open camera index {self.index}.")

        self.capture = capture

    def read(self):
        if self.capture is None or not self.capture.isOpened():
            raise RuntimeError("Camera is not open. Call open() first.")

        ok, frame = self.capture.read()
        if not ok or frame is None:
            raise RuntimeError("Could not read a frame from the camera.")
        return frame

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

