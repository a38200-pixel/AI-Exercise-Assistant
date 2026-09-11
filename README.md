# AI Exercise Assistant

#초기 yolo detection FPS29.44

## Overview

실시간 카메라 영상에서 사람을 검출하고 자세를 분류하기 위한 AI 운동 보조 시스템의 초기 실행 구조입니다. 이 단계는 기존 학습 모델을 재학습하지 않으며, 사람 검출과 이후 자세 분류 파이프라인의 기반만 제공합니다.

## Current AI Pipeline

```text
Camera
  -> YOLO26n TensorRT / PyTorch (Person Detection)
  -> Person BBox
  -> MediaPipe Pose (33 Landmarks)
  -> 132 Features (x, y, z, visibility)
  -> XGBoost (9-Class Pose Classification)
  -> [Planned] Exercise State Machine
  -> [Planned] Squat / Stretch / Burpee
```

TensorRT 엔진이 있으면 우선 사용하고, 없으면 PyTorch 모델로 fallback합니다.

## Supported Pose Classes

|  ID | Class    |
| --: | -------- |
|   0 | squat    |
|   1 | run      |
|   2 | sit      |
|   3 | stretch  |
|   4 | walk     |
|   5 | jump     |
|   6 | bendover |
|   7 | stand    |
|   8 | lying    |

## Exercise Rules (Planned)

- Squat: `stand -> squat -> stand` 완료 시 1회
- Stretch: `stretch` 자세 유지 시간 측정
- Burpee: `stand -> bendover -> lying -> bendover -> jump -> stand` 완료 시 1회

운동 카운터, 타이머, 상태 머신과 로그 기능은 아직 구현되지 않았습니다.

## Setup

기존 Conda 환경을 활성화한 뒤 필요한 최소 패키지를 설치합니다. 버전은 현재 환경과 기존 모델의 호환성을 유지하도록 의도적으로 고정하지 않았습니다.

```bash
pip install -r requirements.txt
```

TensorRT export는 NVIDIA GPU, CUDA, TensorRT 및 현재 Ultralytics 버전과 호환되는 환경이 필요하며, export 과정에서 추가 패키지 설치가 요구될 수 있습니다.

## Models

다음 기존 파일은 사용자가 직접 복사해야 합니다. 애플리케이션은 이 파일들을 임의로 생성하거나 다운로드하지 않습니다.

```text
models/pose/pose_landmarker_full.task
models/classifier/model_weights.xgb
models/classifier/classes.json
```

`classes.json`은 학습 당시의 클래스 순서를 그대로 유지해야 합니다.

YOLO 파일 위치는 다음과 같습니다.

```text
models/detector/yolo26n.pt
models/detector/yolo26n.engine
```

`yolo26n.pt`가 없어도 export script가 Ultralytics의 공식 로딩 방식으로 준비합니다. `.engine` 파일은 생성 GPU/TensorRT 환경에 종속적이므로 Git에서 제외됩니다.

## Environment Check

```bash
python scripts/check_environment.py
```

Python과 주요 패키지 버전, CUDA/GPU 상태 및 모든 모델 파일의 존재 여부를 출력합니다.

## TensorRT Export

```bash
python scripts/export_yolo26n_tensorrt.py
```

정적 batch 1, image size 640, FP16 설정으로 export하며 최종 결과를 다음 위치에 둡니다.

```text
models/detector/yolo26n.engine
```

## Person Detection Test

```bash
python tests/test_person_detection.py
```

웹캠 화면에 사람 bounding box, confidence, FPS를 표시합니다. 처음 30프레임은 평균 benchmark에서 제외합니다. `Esc` 또는 `Q`로 종료합니다.

## Main

```bash
python src/main.py
```

현재 main은 Camera와 YOLO 사람 검출을 연결하고 사용 중인 TensorRT/PyTorch backend를 표시하는 integration test입니다. `Esc` 또는 `Q`로 종료합니다.

## Next Steps

1. Prediction smoothing
2. Squat counter
3. Stretch timer
4. Burpee state machine
5. Workout session timer
6. CSV workout log
