# AI Client Pipeline

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

모델의 class 결과 자체를 운동 횟수로 사용하지 않고, **stable pose의 상태 전이**를 기준으로 반복 동작을 기록합니다.

---

## 구성 요소별 역할

| Type | Details |
| --- | --- |
| **Deep Learning / Vision** | YOLO26n 기반 Person Detection, MediaPipe PoseLandmarker 기반 Pose 추정 |
| **Inference Acceleration** | TensorRT FP16 기반 YOLO26n 추론 가속 |
| **Machine Learning** | 132차원 landmark feature를 입력으로 사용하는 XGBoost 9-class classifier |
| **Rule-based Logic** | stable pose 상태 전이를 이용한 Squat count / Stretch duration 계산 |
