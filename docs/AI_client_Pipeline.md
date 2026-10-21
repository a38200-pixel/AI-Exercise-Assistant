# AI Client Pipeline

> **v0.2.0 안내**: 아래 "Pipeline" 도식은 사람 검출부터 자세 분류(화면 표시용)까지의 흐름입니다. v0.2.0부터 스쿼트 횟수는 이 도식의 XGBoost 라벨이 아니라 무릎각 기반 반복 추적으로 셉니다. 바뀐 부분은 [v0.2.0에서 바뀐 점](#v020에서-바뀐-점)에 정리했습니다.

## Pipeline

```text
Webcam
  ↓
YOLO26n
(Person Detection)
  ↓
TensorRT FP16 Inference
  ↓
Person ROI (+30% padding)
  ↓
MediaPipe PoseLandmarker
(33 landmarks)
  ↓
132 Features
  ↓
XGBoost Classifier
  ↓
Temporal Smoothing
  ↓
Squat / Stretch Logic
  ↓
Workout Summary
```

---

## 설계 포인트

### YOLO26n

사람 영역을 먼저 탐지해 Pose 분석 영역을 제한하는 **Person Detection 모델**로 사용했습니다.

### TensorRT

YOLO26n 추론을 Windows NVIDIA 환경에서 가속하기 위해 **FP16 TensorRT engine**을 사용했습니다.

### MediaPipe PoseLandmarker

33개 landmark의 좌표 정보를 추출해 자세 분류의 입력 feature로 사용했습니다.

### XGBoost

landmark 기반 feature를 입력받아 **9개 자세 class**를 분류합니다.  
Frame 단위 예측의 흔들림을 줄이기 위해 **Temporal Smoothing**을 적용한 뒤 실제 운동 로직과 연결했습니다.

### Rule-based Exercise Logic

모델의 class 결과 자체를 운동 횟수로 사용하지 않고, **stable pose의 상태 전이**를 기준으로 반복 동작을 기록합니다. (v0.1.x 기준입니다. v0.2.0의 스쿼트 카운트는 [v0.2.0에서 바뀐 점](#v020에서-바뀐-점)을 참고하세요. 스트레칭 시간은 v0.2.0에서도 stable pose로 계산합니다.)

---

## 구성 요소별 역할

| Type | Details |
| --- | --- |
| **Deep Learning / Vision** | YOLO26n 기반 Person Detection, MediaPipe PoseLandmarker 기반 Pose 추정 |
| **Inference Acceleration** | TensorRT FP16 기반 YOLO26n 추론 가속 |
| **Machine Learning** | 132차원 landmark feature를 입력으로 사용하는 XGBoost 9-class classifier |
| **Rule-based Logic** | stable pose 상태 전이를 이용한 Squat count / Stretch duration 계산 (v0.1.x 기준, v0.2.0의 Squat count는 아래 절 참고) |

---

## v0.2.0에서 바뀐 점

v0.1.x의 설명은 위에 그대로 두고, v0.2.0에서 달라진 부분만 정리합니다. 모든 기준값은 `config/settings.py`의 값이며 [README 5절](../README.md)과 같습니다.

### 두 갈래 경로

```text
MediaPipe 33 landmarks
  ├─ (분류 경로) 132 features → XGBoost → Temporal Smoothing → stable pose
  │     → 화면의 현재 자세 표시, 스트레칭 시간, 기록용 라벨 비율
  └─ (반복 추적 경로) 기하 계산 → 전신 가시성·측면 판별 → BodyLock
        → RepTracker → 확정 조건 → 카운트 + 자세 점수 → 화면 한 줄

YOLO bbox ─ 구도 안내(FramingGuide): "뒤로 물러서 주세요" / "화면 가운데로 이동해 주세요"
```

- **스쿼트 횟수는 반복 추적 경로만 셉니다.** 분류 경로의 라벨(stable pose)은 현재 자세 표시와 기록용이고, 스트레칭 시간 계산에는 계속 쓰입니다.
- 반복 추적은 `ExerciseCounter`가 `RepTracker`의 확정 반복만 세는 방식입니다(`src/exercise_counter.py`). `USE_REP_TRACKER`를 False로 하면 v0.1.x의 라벨 상태 전이 방식으로 돌아갑니다.

### 기하 계산과 반복 분할

| 단계 | 내용 | 값 | 출처 |
| --- | --- | --- | --- |
| 기하 계산 | 종횡비 보정 후 엉덩이-무릎-발목 무릎각, 몸통각, 정강이각. 타임스탬프 기반 One Euro 평활 | `ONE_EURO_MIN_CUTOFF` 1.0, `ONE_EURO_BETA` 0.02 | `src/pose_geometry.py`, `src/geometry_tracker.py` |
| 반복 분할 | 서 있음 → 하강 → 복귀 상태 머신(히스테리시스) | 서 있음 160° 이상, 하강 150° 미만 (`STANDING_KNEE_ANGLE`, `REP_DESCENT_KNEE_ANGLE`) | `src/rep_tracker.py` |
| 측면 전용 판정 | 서 있는 동안 측면이 이어지면 가까운 다리·방향을 잠그고 반복 중에는 고정, 서 있을 때 비측면이 이어지면 해제 | 획득 0.5초, 해제 0.4초, 놓침 해제 2.0초 | `src/geometry_tracker.py` |
| 전신 가시성 | 사용하는 다리의 엉덩이·무릎·발목·뒤꿈치·발끝과 같은 쪽 어깨의 visibility가 충분하고 bbox가 하단·좌·우 경계에 닿지 않을 때만 각도를 유효로 처리 | `MIN_LANDMARK_VISIBILITY` | `src/pose_geometry.py` |
| 짧은 놓침 허용 | 서 있는 동안·반복 중 사람 검출이 짧게 끊겨도 상태를 유지 | 1.5초 이하 (`REP_STANDING_MAX_GAP_SECONDS`, `REP_MAX_GAP_SECONDS`) | `src/rep_tracker.py` |

### 반복 확정 조건 (기하 조건만 사용)

| 조건 | 기준 | 설정 이름 |
| --- | --- | --- |
| 반복 길이 | 1.0초 이상 | `REP_MIN_SECONDS` |
| 엉덩이 하강 | 다리 길이(L)의 0.20 이상 | `REP_MIN_HIP_DROP` |
| 서 있을 때 발 간격 | 0.25 L 이하 | `REP_MAX_ANKLE_GAP` |
| 최저점 발 간격 | 0.40 L 이하 (최저점 ±0.25초 중앙값) | `REP_MAX_ANKLE_GAP_BOTTOM`, `REP_BOTTOM_WINDOW_SECONDS` |
| 반복 중 엉덩이 수평 이동 | 0.70 L 이하 (반복 중 L의 중앙값으로 정규화) | `REP_MAX_HIP_SHIFT` |

XGBoost 라벨(walk/run/lying) 비율은 확정 조건에서 제외하고 기록만 합니다(`REP_OTHER_EXERCISE_MAX_RATIO = None`). 사람마다 분류기 라벨이 달라 정상 반복이 탈락한 실측 결과 때문입니다(README 9-7).

### 자세 점수와 화면 문구

| 항목 | 정상 | 교정 | 점수 |
| --- | --- | --- | --- |
| 깊이(최저 무릎각) | 80° 이하 | 95° 이상 | 80° 100점 · 95° 50점 · 120° 0점(임시값) |
| 상체 정렬(최저점 몸통각 − 정강이각) | 25° 이하 | 35° 이상 | 25° 100점 → 35° 0점(선형), 깊이가 교정이면 판정하지 않고 기록만 |

- 두 항목을 같은 가중치(0.5/0.5)로 평균하고, 교정 항목이 하나라도 있으면 총점은 50점을 넘지 못합니다. 출처: `src/posture_score.py`, `config/settings.py`(`POSTURE_*`).
- 반복이 확정되면 `78점 · 더 깊게 앉아보세요` 형식의 한 줄을 화면에 보여줍니다(`src/rep_feedback.py`).
- 구도 안내(`src/framing_guide.py`)는 YOLO bbox만 사용하므로 랜드마크가 없어도 동작합니다: 발 아래 여유가 프레임 높이의 4% 이하이거나 몸 높이가 95% 이상이면 "뒤로 물러서 주세요", 판정용 crop이 좌우로 크게 잘리면(0.5 이상) "화면 가운데로 이동해 주세요". 1.5초 이상 이어질 때만 표시합니다.

### 측면 전용, 로컬 기록

- **측면 전용**: 카메라에 옆모습이 보일 때만 반복 추적이 시작되고, 정면·사선에서는 카운트하지 않고 옆모습 안내만 표시합니다.
- **로컬 기록**: 세션이 끝나면 반복별 판정(항목 status, 점수, 탈락 사유)을 `%LOCALAPPDATA%\FitRoute\workout_logs\workout_<시작시각>.json`에 저장합니다(개발 실행은 `data/workout_logs/`). 서버로 보내는 요약의 형식은 바뀌지 않았습니다. 출처: `src/workout_session.py`, `src/paths.py`, [workout_record_format.md](versions/v0.2.0/workout_record_format.md).
- 처리 속도 수치(15.84 FPS 등)는 v0.1.1 패키징 클라이언트 기준이며 [Runtime_Performance.md](Runtime_Performance.md)에 측정 시점이 적혀 있습니다.

자세한 근거와 한계는 [v0.2.0 RELEASE](versions/v0.2.0/RELEASE.md)에 있습니다.
