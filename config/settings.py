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

# 스쿼트 카운트 방식 스위치. True(기본)면 RepTracker(무릎각 반복 구간, 측면 전용), False면 v0.1.x(stable 라벨 stand → squat → stand).
USE_REP_TRACKER = True
# squat 모드에서 BodyLock이 이 시간(초) 넘게 잡히지 않으면 사유별 한 줄 안내를 화면에 보인다. 잠금이 잡히면 지운다.
LOCK_GUIDANCE_DELAY_SECONDS = 2.0

# RepTracker(v0.2.0 Phase 2). 모두 field_test_1(한 사람, 하루, 세션당 5~10회)로 정한 초기값이다.
# 반복: 평활 무릎각이 STANDING_KNEE_ANGLE 이상이던 뒤 REP_DESCENT_KNEE_ANGLE 미만으로 내려갔다가 다시 STANDING_KNEE_ANGLE 이상.
REP_DESCENT_KNEE_ANGLE = 150.0
# 반복 중 전신 무효 등으로 평활 무릎각이 이 시간보다 오래 비면 그 반복을 버린다.
REP_MAX_GAP_SECONDS = 1.5
# 반복 확정 조건(기하): 반복 길이 하한, 엉덩이 하강량 하한(서 있을 때 대비, 다리 길이 비), 서 있을 때 양발 간격 상한(다리 길이 비, 측면 전용).
# 엉덩이 하강 하한 0.20: 정상 반복 최소 0.331(세션 3, 무릎 약 100°)과 걷기 최대 0.085의 중앙(0.208)에 가깝게 잡았다.
# 이전 0.25는 정상 쪽 여유가 0.09뿐이라 하프보다 얕은 반복이 "얕음" 판정 없이 아예 안 세어질 위험이 있었다. 쿼터 스쿼트 데이터는 없다.
REP_MIN_SECONDS = 1.0
REP_MIN_HIP_DROP = 0.20
REP_MAX_ANKLE_GAP = 0.25
# 반복 확정 조건(ML, 2차): 반복 구간의 stable 라벨 시간 중 이 라벨들의 비율이 상한 이하일 때만 확정한다. jump·sit·bendover·stretch는 넣지 않는다.
REP_OTHER_EXERCISE_LABELS = ("walk", "run", "lying")
REP_OTHER_EXERCISE_MAX_RATIO = 0.40
# 서 있을 때 기준값(엉덩이·뒤꿈치 y, 다리 길이, 양발 간격)을 내려가기 직전 이 시간의 중앙값으로 정한다.
REP_BASELINE_SECONDS = 1.0
# 최저점 체류: 평활 무릎각이 (최저 + 이 값) 이하인 시간(진단용 원자료, 판정에 쓰지 않음).
REP_BOTTOM_PLATEAU_DEGREES = 10.0
# 반복 합쳐짐 의심(진단 전용, 카운트에 영향 없음): 반복 중 무릎각이 직전 최저점보다 REP_MERGE_RISE_DEGREES 이상 올라온 뒤
# 최고점보다 REP_MERGE_DROP_DEGREES 이상 다시 내려가면(STANDING 복귀 각도에 닿지 못한 채) 이벤트로 남긴다.
REP_MERGE_RISE_DEGREES = 20.0
REP_MERGE_DROP_DEGREES = 10.0

# 대응안 후보(세트 중간 누락 진단용, v0.2.0): 모두 기본은 꺼짐이며 기본 동작은 바뀌지 않는다. 2차 실측 로그로 효과를 확인한 뒤 켤지 정한다.
# 세트 단위 서 있는 기준 높이(가설 4): 켜면 서 있을 때 기준값(엉덩이·뒤꿈치 y, 다리 길이, 양발 간격)을 내려가기 직전 1초(REP_BASELINE_SECONDS)가
# 아니라, 잠금이 유지되는 동안(세트) 최근 REP_SET_BASELINE_WINDOW_SECONDS 안에서 무릎각이 STANDING_KNEE_ANGLE 이상이던 프레임의 중앙값으로
# 정한다(엉덩이 y는 중앙값 대신 높은 쪽 REP_SET_BASELINE_HIP_PERCENTILE 분위수: 세트 중에는 완전히 선 프레임이 적어 중앙값이 낮아지기 쉽다).
# 휴지 없는 연속 세트에서는 직전 1초에 완전히 선 프레임이 거의 없어 기준 높이가 낮아지고 엉덩이 하강량이 작게 나온다.
# 해당 프레임이 REP_SET_BASELINE_MIN_SAMPLES보다 적으면 기존 방식(직전 1초)으로 되돌아간다.
REP_SET_BASELINE_ENABLED = False
REP_SET_BASELINE_WINDOW_SECONDS = 30.0
REP_SET_BASELINE_MIN_SAMPLES = 5
REP_SET_BASELINE_HIP_PERCENTILE = 25.0
# 복귀 각도 조정: 반복이 끝나는 '서 있음으로 복귀' 기준 무릎각. None이면 STANDING_KNEE_ANGLE과 같다(꺼짐).
# REP_DESCENT_KNEE_ANGLE < 값 <= STANDING_KNEE_ANGLE이어야 한다. 낮추면 기준 높이가 더 낮은 프레임에서 끝나므로 세트 단위 기준 높이가 자동으로 함께 켜진다.
REP_RETURN_KNEE_ANGLE = None
# 반복 경계(내려감·복귀) 판정에 쓰는 무릎각 신호(가설 5). "smoothed"(기본): STANDING 판정과 같은 One Euro 평활값,
# "light": 별도 가벼운 평활(min_cutoff만 REP_BOUNDARY_LIGHT_MIN_CUTOFF로 올림), "raw": 평활 없는 원본값. 잠금 정책의 STANDING 판정과 최저점 계산은 평활값을 그대로 쓴다.
REP_BOUNDARY_SIGNAL = "smoothed"
REP_BOUNDARY_LIGHT_MIN_CUTOFF = 4.0
# 잠금 해제 유예(가설 2): 해제 기준(BODY_LOCK_RELEASE_NONSIDE_SECONDS)에 이 시간(초)을 더해 일시적인 비측면 판정으로 세트 중간에 잠금이 풀리는 것을 늦춘다. 0이면 꺼짐.
BODY_LOCK_RELEASE_GRACE_SECONDS = 0.0

# Landmark 시퀀스 로깅(진단용): 기본은 꺼져 있고 CLI --log-sequence로만 켠다. 영상은 저장하지 않는다.
SEQUENCE_LOGGING_ENABLED = False
# 얼굴 landmark(0~10번)의 좌표는 기본으로 저장하지 않는다. 코(0번)의 visibility만 시점 신호용으로 남긴다.
SEQUENCE_LOG_FACE_LANDMARKS = False
LANDMARK_SEQUENCE_DIR = PROJECT_ROOT / "data" / "landmark_sequences"
SEQUENCE_LOG_FLUSH_INTERVAL_SECONDS = 1.0
SEQUENCE_LOG_QUEUE_SIZE = 4096
