# AI Exercise Assistant

#초기 yolo detection FPS29.44

## Overview

실시간 카메라 영상에서 사람을 검출하고 자세를 분류하는 AI 운동 보조 시스템입니다. 기존 학습 모델을 재학습하지 않고 YOLO26n, MediaPipe Tasks와 XGBoost를 연결합니다.

## Current AI Pipeline

```text
Camera
  -> YOLO26n TensorRT / PyTorch (Person Detection)
  -> Person BBox
  -> MediaPipe Pose (33 Landmarks)
  -> 132 Features (x, y, z, visibility)
  -> XGBoost (9-Class Pose Classification)
  -> Raw pose prediction
  -> Consecutive-frame prediction smoothing
  -> Stable pose + confidence 표시
  -> Exercise State Machine
  -> Squat / Stretch
  -> Workout Session Timer
  -> Session Summary (Python dict)
  -> FastAPI POST /api/workouts (session end only)
  -> Supabase workout_sessions + daily_workout_summary
  -> React Dashboard / History / Statistics
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

## Exercise Rules

- Squat: `stand -> squat -> stand` 완료 시 1회
- Stretch: `stretch` 자세 유지 시간 측정

운동 카운터와 타이머는 stable pose 기반 상태 머신으로 구현되어 있습니다. Workout Session은 전체 경과시간과 세션 내 Squat 횟수 및 Stretch 시간을 관리합니다. 세션 종료 시 선택적으로 FastAPI를 통해 Supabase에 저장합니다.

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

현재 main은 각 YOLO 사람 bbox에 30% padding을 적용한 crop에서 33개 landmark를 추출하고, 132개 feature로 XGBoost 자세 분류를 수행합니다. 원본 bbox, landmark point, 자세 label과 confidence를 화면에 표시하며 `Esc` 또는 `Q`로 종료합니다.

Prediction smoothing은 일반 자세를 3프레임, 짧은 `jump`를 2프레임 연속 확인한 뒤 stable 자세로 확정합니다. 일시적인 pose 미검출은 3프레임까지 기존 stable 자세를 유지합니다. Tracking은 아직 사용하지 않으므로 화면에서 가장 큰 사람을 주 사용자로 선택합니다.

운동 판단에는 raw prediction이 아닌 stable pose만 사용합니다.

- `1`: Squat — `stand -> squat -> stand` 완료 시 1회
- `2`: Stretch — `stretch` 자세의 실제 경과 시간 누적
- `0`: Idle
- `R`: 현재 선택된 운동 기록만 초기화
- `S`: 새 Workout Session 시작 및 운동 기록 전체 초기화
- `E`: 진행 중인 Session 종료 및 terminal summary 출력
- `P`: 직전 저장 실패 Session의 API 업로드 재시도
- `Q` 또는 `Esc`: 종료

세션 시간은 운동 모드와 독립적이므로 Idle과 휴식 시간도 포함합니다. 세션이 진행 중일 때 `Q` 또는 `Esc`로 종료하면 현재 시각까지 자동으로 마감합니다. Summary는 향후 API 전송을 위해 다음 필드를 유지합니다.

```text
workout_date, started_at, ended_at, workout_seconds,
squat_count, stretch_seconds
```

## AI Client → FastAPI 자동 저장

AI 프로그램은 `FITROUTE_ACCESS_TOKEN`이 설정된 경우 `E`, `Q`, `Esc`로 세션을 종료하는 순간 summary를 `POST /api/workouts`에 한 번 전송합니다. 토큰과 비밀번호는 파일에 저장하지 않습니다.

8000 포트를 `vmnat`가 사용 중인 현재 개발 환경에서는 Backend를 8001로 실행합니다.

```cmd
uvicorn backend.app.main:app --reload --port 8001
```

새 터미널에서 로그인 토큰을 발급합니다.

```cmd
python backend/scripts/get_test_token.py
```

CMD:

```cmd
set FITROUTE_ACCESS_TOKEN=eyJ...
set FITROUTE_API_BASE_URL=http://127.0.0.1:8001
python src/main.py
```

PowerShell:

```powershell
$env:FITROUTE_ACCESS_TOKEN="eyJ..."
$env:FITROUTE_API_BASE_URL="http://127.0.0.1:8001"
python src/main.py
```

토큰이 없으면 `Cloud: DISABLED`로 표시되며 로컬 운동 인식은 그대로 동작합니다. 저장 성공 시 `Cloud: SAVED`와 Session ID를 표시합니다. 401, validation 오류, 서버 오류, timeout 또는 연결 실패 시 프로그램은 종료되지 않고 `Cloud: FAILED`와 함께 summary를 메모리에 유지합니다. Backend를 복구하거나 토큰을 갱신한 뒤 `P`를 누르면 같은 pending summary만 재시도합니다. 성공한 summary는 pending에서 제거되므로 `P`로 중복 저장되지 않습니다.

API Client 단위 테스트:

```cmd
pytest tests/test_api_client.py -v
```

Smoothing 로직만 검증하려면 다음 명령을 사용합니다.

```bash
python tests/test_prediction_smoothing.py
```

운동 상태 머신만 검증하려면 다음 명령을 사용합니다.

```bash
python tests/test_exercise_counter.py
```

Workout Session을 검증하려면 다음 명령을 사용합니다.

```bash
python tests/test_workout_session.py
```

30-frame warmup 후 30초 동안 전체 파이프라인의 단계별 성능을 측정하려면 다음 명령을 사용합니다.

```bash
python src/main.py --benchmark-seconds 30
```

## Next Steps

1. 실제 웹캠 Session 종료 → Supabase 저장 → React 재조회 검증
2. Frontend/FastAPI production 배포 준비
3. Production 환경변수와 CORS 분리

## Backend

Supabase PostgreSQL schema, RLS, Supabase Auth Bearer token dependency와 FastAPI API scaffold는 [backend/README.md](backend/README.md)를 참고하세요. 실제 Cloud 연결 전에도 schema와 service unit test를 실행할 수 있습니다.

## Frontend

React + Vite 기반 FitRoute 웹 대시보드는 [frontend/README.md](frontend/README.md)를 참고하세요.

```powershell
# Terminal 1 (8000 포트 충돌 시 8001 사용)
uvicorn backend.app.main:app --reload --port 8001

# Terminal 2
cd frontend
npm install
npm run dev
```

`frontend/.env`의 `VITE_API_BASE_URL` 포트는 실제 Backend 포트와 같아야 합니다.

Production 배포 준비와 실제 배포 순서는 [Production Deployment Checklist](docs/production_deployment_checklist.md)를 참고하세요.
