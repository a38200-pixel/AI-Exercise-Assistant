"""Project paths and the small set of runtime inference settings."""

from src.paths import get_app_root, get_model_path


PROJECT_ROOT = get_app_root()

MODEL_DIR = get_model_path()
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

# Prediction smoothing: 일반 자세는 3프레임, 짧은 jump는 2프레임 확인한다.
DEFAULT_STABLE_FRAMES = 3
POSE_STABLE_FRAMES = {
    "jump": 2,
}
MISSING_POSE_TOLERANCE_FRAMES = 3
SHOW_SMOOTHING_DEBUG = True
