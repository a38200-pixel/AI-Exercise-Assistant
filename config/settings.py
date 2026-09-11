"""Project paths and the small set of runtime inference settings."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_DIR = PROJECT_ROOT / "models"
DETECTOR_MODEL_DIR = MODEL_DIR / "detector"
POSE_MODEL_DIR = MODEL_DIR / "pose"
CLASSIFIER_MODEL_DIR = MODEL_DIR / "classifier"

YOLO_PT_PATH = DETECTOR_MODEL_DIR / "yolo26n.pt"
YOLO_ENGINE_PATH = DETECTOR_MODEL_DIR / "yolo26n.engine"
POSE_MODEL_PATH = POSE_MODEL_DIR / "pose_landmarker_full.task"
XGBOOST_MODEL_PATH = CLASSIFIER_MODEL_DIR / "model_weights.xgb"
CLASSES_PATH = CLASSIFIER_MODEL_DIR / "classes.json"

CAMERA_INDEX = 0

YOLO_IMAGE_SIZE = 640
YOLO_CONFIDENCE = 0.30
YOLO_PERSON_CLASS_ID = 0
YOLO_DEVICE = 0
YOLO_MAX_DET = 5

BBOX_PADDING = 0.30

MIN_POSE_DETECTION_CONFIDENCE = 0.20
MIN_POSE_PRESENCE_CONFIDENCE = 0.20

