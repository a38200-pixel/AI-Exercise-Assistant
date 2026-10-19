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

# Pose geometry (v0.2.0): 아래 값은 모두 임시 초기값이며 Phase 4 실측 후 확정한다.
# 전신 가시성 검사: 사용하는 다리 관절의 visibility 하한과 bbox-프레임 경계 허용 오차.
MIN_LANDMARK_VISIBILITY = 0.5
FRAME_BORDER_TOLERANCE_PX = 1

# 측면 판별 (a)+(c): 어깨 간격/몸통 길이 비율 상한, 코 visibility 하한(뒷모습 배제).
SIDE_VIEW_MAX_SHOULDER_RATIO = 0.35
SIDE_VIEW_MIN_NOSE_VISIBILITY = 0.5

# One Euro filter(연속 각도 신호 평활화). 단위: min_cutoff/d_cutoff는 Hz, beta는 초/도.
ONE_EURO_MIN_CUTOFF = 1.0
ONE_EURO_BETA = 0.02
ONE_EURO_D_CUTOFF = 1.0

# 서 있는 상태로 보는 무릎각 하한. POLAR 측면+전신유효 stand의 p25(163.4도)를 근거로 한 초기값.
STANDING_KNEE_ANGLE = 160.0
# BodyLock 정책(field_test_1 실측 기반 초기값, 2차 실측 전까지 확정 아님).
# 획득: STANDING이고 측면 판정이 이 시간 연속 유지될 때만 잠근다(측면이 아니면 잠그지 않는다).
BODY_LOCK_ACQUIRE_SIDE_SECONDS = 0.5
# 해제: 잠긴 채 STANDING일 때 비측면 판정이 이 시간 연속되면 푼다. 반복 중에는 시점이 바뀌어도 고정한다.
BODY_LOCK_RELEASE_NONSIDE_SECONDS = 0.4
# Pose를 이 시간 넘게 놓치면 다리/방향 잠금을 푼다.
BODY_LOCK_MISSING_RELEASE_SECONDS = 2.0
