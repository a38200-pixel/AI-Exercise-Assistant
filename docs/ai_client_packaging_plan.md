# FitRoute AI Client Packaging Plan

## 범위와 현재 상태

이 문서는 개발 PC의 `vision_ai` Conda 환경과 Repository source에 의존하는 Python AI Client를 향후 독립적인 Windows `FitRouteAIClient.exe`로 패키징하기 위한 1단계 조사 결과다.

1단계에서 완료한 것은 runtime dependency 조사, 절대경로/CWD 의존성 조사, frozen-aware model path 정리와 테스트다. 1단계에서는 새 Conda 환경, `FitRouteAIClient.spec`, PyInstaller AI Client build, ONNX fallback, installer와 Release를 만들지 않았다. 현재 2단계 환경 결과는 이 문서 아래의 별도 절에 기록한다.

현재 성공한 개발 환경 E2E는 다음과 같다.

```text
Vercel Web
  → fitroute://start?exercise=squat
  → FitRouteLauncher.exe
  → Desktop Supabase Auth
  → vision_ai Python + src/main.py
  → Camera Workout
  → Render API
  → Supabase
  → Web Dashboard
```

목표 구조는 다음과 같다.

```text
FitRouteLauncher.exe
  → FitRouteAIClient.exe
  → exe 옆 models/와 _internal/ runtime 사용
```

## 현재 AI runtime 구조와 import graph

`src/main.py`가 실행 시 사용하는 코드 경로는 다음과 같다.

```text
src/main.py
├─ cv2, numpy
├─ config.settings → src.paths
├─ src.camera → cv2
├─ src.person_detector → ultralytics.YOLO (동적 import)
│  └─ TensorRT engine → ultralytics.nn.backends.tensorrt
│     ├─ tensorrt (동적 import)
│     ├─ torch CUDA tensors
│     └─ numpy buffers
├─ src.pose_estimator → cv2, numpy, mediapipe (동적 import)
├─ src.pose_classifier → numpy, xgboost.XGBClassifier (동적 import)
├─ src.prediction_smoother
├─ src.exercise_counter
├─ src.workout_session
└─ src.api_client → httpx
```

Python 표준 라이브러리는 `argparse`, `datetime`, `functools`, `json`, `os`, `pathlib`, `sys`, `time`, `typing`을 직접 사용한다. `subprocess`와 Desktop Supabase Auth는 Launcher 책임이며 AI Client runtime graph에는 없다.

## Dependency 분류

| 분류 | Package/모듈 | 판단 근거 |
|---|---|---|
| A: 직접 필수 | `numpy` | frame, landmark feature, TensorRT binding buffer |
| A: 직접 필수 | `opencv-contrib-python`의 `cv2` | Camera, MSMF capture, 색상 변환, HUD/GUI |
| A: 직접 필수 | `ultralytics` | `YOLO(engine, task="detect")`와 inference orchestration |
| A: 직접 필수 | `torch`, `torchvision` | Ultralytics runtime 및 TensorRT CUDA input/output tensor |
| A: 직접 필수 | `tensorrt` | serialized `.engine` deserialize 및 execution context |
| A: 직접 필수 | `mediapipe` | PoseLandmarker Tasks API |
| A: 직접 필수 | `xgboost` | 기존 `XGBClassifier` model load와 `predict_proba` |
| A: 직접 필수 | `httpx` | 완료된 Workout Session의 Render API upload |
| A: 보수적 유지 | `scikit-learn` | 현재 코드가 XGBoost sklearn wrapper인 `XGBClassifier`를 사용하므로 첫 독립 build에서는 현행 동작 보존 |
| A: transitive | `scipy`, `Pillow`, `PyYAML`, `requests`, `psutil`, `polars`, `nvidia-ml-py`, `ultralytics-thop` | Ultralytics/XGBoost declared runtime dependency |
| A: transitive | `absl-py`, `flatbuffers`, `sounddevice`, `certifi` | MediaPipe declared runtime dependency |
| B: build-only | `PyInstaller` | onedir Analysis/EXE/COLLECT 생성에만 사용 |
| B: test-only | `pytest` | unit test runner; 최종 runtime에서 제외 |
| B: export-only | `onnx`, `onnxruntime`, export toolchain | 현재 TensorRT engine 실행에는 사용하지 않으며 ONNX fallback도 이번 범위 밖 |
| B/C: 현재 runtime 미사용 | `pandas` | Repository AI runtime에서 import하지 않음; XGBoost optional extra |
| C: 불필요 | `pygame` | AI Client source import 없음 |
| C: 불필요 | `supabase` | Desktop Auth는 Launcher 책임이며 AI Client는 access token만 환경변수로 받음 |
| C: 불필요 | `PyQt5`, `PyQt6` | OpenCV window와 tkinter Launcher를 사용하며 Qt UI를 사용하지 않음 |

`opencv-python`, `opencv-python-headless`는 현재 환경에 설치되어 있지 않다. 실제 `cv2` provider는 `opencv-contrib-python`이다. 다음 환경에서도 OpenCV distribution을 여러 개 동시에 설치하지 않고 Camera/MediaPipe에 필요한 contrib build 하나를 우선 검증한다.

## 현재 설치 버전 스냅샷

조사일: 2026-09-14, `vision_ai` environment.

| Component | Version |
|---|---:|
| Python | 3.12.12 |
| PyTorch | 2.11.0+cu128 |
| TorchVision | 0.26.0+cu128 |
| PyTorch CUDA runtime | 12.8 |
| cuDNN reported by PyTorch | 9.19.0 (`91900`) |
| Ultralytics | 8.4.70 |
| OpenCV distribution | opencv-contrib-python 5.0.0.93 |
| NumPy | 2.4.4 |
| SciPy | 1.17.1 |
| MediaPipe | 0.10.35 |
| XGBoost | 3.4.1 |
| scikit-learn | 1.9.1 |
| pandas | 3.0.2 (현재 runtime source 미사용) |
| TensorRT / cu13 bindings / cu13 libs | 11.0.0.114 |
| HTTPX | 0.28.1 |
| Pillow | 12.2.0 |
| PyYAML | 6.0.3 |
| Requests | 2.32.5 |
| psutil | 7.2.2 |
| polars | 1.40.1 |
| nvidia-ml-py | 13.610.43 |
| ultralytics-thop | 2.0.19 |
| absl-py | 2.4.0 |
| flatbuffers | 25.12.19 |
| sounddevice | 0.5.6 |
| PyInstaller (build-only) | 6.22.3 |
| ONNX Runtime distribution | 설치되지 않음 |

`pip freeze` 전체를 새 requirements로 복사하지 않는다. 위 표는 현재 성공 환경의 비교 기준이며 다음 단계에서 최소 build environment를 실제 import/inference 테스트하며 줄인다.

## Model resources와 runtime path

| Resource | Repository path / 개발 runtime path | 크기 | Frozen runtime path |
|---|---|---:|---|
| YOLO TensorRT | `models/detector/yolo26n.engine` | 7,731,821 bytes / 7.3736 MiB | `<exe-dir>/models/detector/yolo26n.engine` |
| MediaPipe Task | `models/pose/pose_landmarker_full.task` | 9,398,198 bytes / 8.9628 MiB | `<exe-dir>/models/pose/pose_landmarker_full.task` |
| XGBoost model | `models/classifier/model_weights.xgb` | 3,378,634 bytes / 3.2221 MiB | `<exe-dir>/models/classifier/model_weights.xgb` |
| Class labels | `models/classifier/classes.json` | 110 bytes / 0.0001 MiB | `<exe-dir>/models/classifier/classes.json` |

`models/detector/yolo26n.pt`도 개발 Repository에 존재하지만 현재 우선 runtime resource는 `.engine`이다. `.pt` fallback을 최종 package에 포함할지는 용량과 TensorRT 실패 정책을 확정한 후 결정한다. 이번 단계에서는 fallback 동작이나 모델을 변경하지 않았다.

### 공통 root 전략

`src.paths.get_app_root()`의 규칙은 다음과 같다.

- 개발 실행: `src/paths.py`의 부모 구조로 Repository root 반환
- frozen 실행: `Path(sys.executable).resolve().parent` 반환
- model path: 항상 `<app-root>/models/...`

이 방식은 PyInstaller 6의 bundle 내부 `__file__` 위치와 무관하게 설치 폴더의 exe 옆 `models/`를 선택한다. 목표 onedir 구조는 다음과 같다.

```text
dist/FitRouteAIClient/
├─ FitRouteAIClient.exe
├─ _internal/
└─ models/
   ├─ detector/yolo26n.engine
   ├─ pose/pose_landmarker_full.task
   └─ classifier/
      ├─ model_weights.xgb
      └─ classes.json
```

PyInstaller 6의 기본 onedir `contents_directory="_internal"`은 data도 `_internal` 아래에 둘 수 있으므로, 다음 build에서는 models를 Analysis data로 무작정 넣지 않는다. 먼저 Python/native runtime을 onedir로 만들고 build staging 단계에서 검증된 models tree를 exe 옆으로 복사하는 방식을 우선한다.

## 절대경로와 실행 위치 조사

AI Client runtime인 `src/`와 `config/`에는 사용자명, `anaconda3`, `vision_ai`, `Documents\GitHub`를 hardcoding한 경로가 없다.

- 기존 `config/settings.py`의 `Path(__file__).resolve().parents[1]`은 개발 실행에는 맞지만 frozen `_internal` 배치에서는 잘못된 model root가 될 수 있어 공통 helper로 교체했다.
- `src/main.py`의 direct-script용 `sys.path` 보정은 `__file__` 기반이며 CWD에 의존하지 않는다. `python src/main.py` 호환을 위해 유지했다.
- `src/`와 `config/`에는 `Path.cwd()`, `os.getcwd()`, `os.chdir()` 호출이 없다.
- `scripts/export_yolo26n_tensorrt.py`의 `Path.cwd()`는 사용자에게 받은 상대 output 경로를 해석하는 개발/export 전용 동작이며 packaged runtime에 포함하지 않는다.
- `desktop_launcher/config.json`의 Python/Project 절대경로는 현재 개발 Launcher의 의도된 의존성이다. 최종 Launcher가 `FitRouteAIClient.exe`를 직접 호출하도록 바꾸는 것은 다음 패키징 단계 이후 작업이다.
- 문서와 테스트의 예시 경로는 runtime dependency가 아니다.

## Native dependency 조사

| Package | 확인한 native 구성 | 다음 build 주의사항 |
|---|---|---|
| NumPy | 다수의 `.pyd` 및 bundled runtime | PyInstaller NumPy hook 결과와 DLL 검색 경로 확인 |
| OpenCV | `cv2/cv2.pyd` 약 107.7 MiB, `opencv_videoio_ffmpeg500_64.dll` 약 29.4 MiB | `cv2` binary/data 수집, HighGUI와 videoio backend smoke test 필요 |
| PyTorch | `torch_python.dll`, `torch_cpu.dll`, `torch_cuda.dll`과 CUDA/cuDNN DLL 다수 | `collect_dynamic_libs("torch")`의 용량이 매우 크므로 실제 TensorRT inference 최소 집합을 분석 |
| TorchVision | 11개 native file, 약 22.29 MiB | Ultralytics import 및 ops hidden import 확인 |
| TensorRT | Python `.pyd`, `nvinfer_11.dll`, `nvinfer_plugin_11.dll`, `nvonnxparser_11.dll`; 설치 libs 전체 약 2,222.32 MiB | builder resource DLL 전체를 runtime에 복사하지 말고 deserialize/inference 최소 집합 검증 |
| MediaPipe | `mediapipe/tasks/c/libmediapipe.dll` 약 27.4 MiB | `importlib.resources.files("mediapipe.tasks.c")`로 찾으므로 package-relative 위치 보존 |
| XGBoost | `xgboost/lib/xgboost.dll` 약 54.3 MiB, `VCOMP140.DLL` 의존 | package-relative `xgboost/lib`와 MSVC/OpenMP runtime 수집 확인 |
| SciPy | 109개 native file, 약 33.01 MiB | XGBoost/Ultralytics가 실제 사용하는 범위를 Analysis로 확인 |
| scikit-learn | 71개 native file, 약 10.44 MiB | 첫 build에서는 XGBClassifier 호환을 위해 유지 후 제거 가능성 검증 |
| Pillow | 8개 native file, 약 12.76 MiB | Ultralytics image utility import에 따른 plugin/data 확인 |
| psutil | native `.pyd` 1개 | Ultralytics system utility 경로 |
| MSVC runtime | System32의 `vcruntime140.dll`, `vcruntime140_1.dll`, `msvcp140.dll` 14.51.36247.0 | 지원 OS에 VC++ Redistributable prerequisite를 명시하거나 PyInstaller 수집 결과 검증 |

## TensorRT와 CUDA 패키징 리스크

`PersonDetector`는 `.engine`이 있으면 이를 우선 선택하고 `ultralytics.YOLO(str(path), task="detect")`에 전달한다. Ultralytics 8.4.70의 TensorRT backend는 다음을 수행한다.

1. `tensorrt`를 동적 import한다.
2. Ultralytics가 engine 앞에 저장한 JSON metadata 길이와 metadata를 읽는다.
3. 나머지 payload를 `trt.Runtime.deserialize_cuda_engine()`으로 역직렬화한다.
4. input/output buffer를 NumPy로 만들고 `torch.from_numpy(...).to(cuda)`로 GPU에 할당한다.

현재 engine은 metadata를 제외한 payload로 TensorRT 11.0.0.114에서 역직렬화에 성공했다. Metadata는 Ultralytics 8.4.70, batch 1, static 640×640, FP16, end-to-end model을 기록한다. TensorRT `hardware_compatibility_level`은 `NONE`이므로 다른 GPU architecture에 대한 호환을 가정하면 안 된다.

현재 GPU/CUDA 관계:

- GPU: NVIDIA GeForce RTX 3080, compute capability 8.6, VRAM 10 GiB
- NVIDIA driver: 595.95; driver가 보고하는 CUDA capability: 13.2
- 설치된 CUDA Toolkit/nvcc: 13.2.51
- PyTorch wheel runtime: CUDA 12.8
- TensorRT wheel: cu13, TensorRT 11.0.0.114

NVIDIA driver는 외부 prerequisite로 남겨야 한다. PyTorch wheel과 TensorRT wheel이 각 runtime DLL을 제공할 수 있으므로 CUDA Toolkit 전체를 installer에 넣는 것은 우선 요구사항이 아니다. 다만 Toolkit이 없는 clean VM에서 engine deserialize와 한 frame inference를 검증하기 전에는 독립 실행을 확정할 수 없다. TensorRT engine은 TensorRT serialization version, OS, GPU architecture와 plugin에 민감하므로 같은 RTX 3080에서 먼저 검증하고 지원 GPU 범위를 별도로 정해야 한다.

## MediaPipe 패키징 리스크

MediaPipe 0.10.35 Tasks API는 `ctypes`와 `importlib.resources`를 사용해 `mediapipe/tasks/c/libmediapipe.dll`을 package-relative path에서 로드한다. 외부 `pose_landmarker_full.task`만 복사해서는 충분하지 않다.

다음 spec 단계에서 확인할 항목:

- `collect_dynamic_libs("mediapipe")` 또는 명시적 `libmediapipe.dll` 수집
- DLL을 `mediapipe/tasks/c/` 상대 위치에 보존
- `mediapipe.tasks.python`, `core`, `vision`, `pose_landmarker`의 동적 import
- 필요한 package data를 `collect_data_files("mediapipe")` 결과에서 선별
- external task model을 exe 옆 `models/pose/`에서 정상 open하는지 확인

## XGBoost 패키징 리스크

`PoseClassifier`는 `XGBClassifier()`를 만든 뒤 `load_model(str(XGBOOST_MODEL_PATH))`을 호출하고 `predict_proba()`를 사용한다. XGBoost 3.4.1은 package 내부 `xgboost/lib/xgboost.dll`을 ctypes로 로드하며 이 DLL은 Windows의 `VCOMP140.DLL`에 의존한다.

다음 spec 단계에서는 `collect_dynamic_libs("xgboost")` 또는 package-relative explicit binary 수집과 VC++/OpenMP runtime을 확인한다. 현재 `.xgb` 파일은 XGBoost가 UBJSON으로 추정해 읽는 경고가 있지만 정상 로드된다. 이번 단계에서는 모델 format을 변환하지 않았다.

## OpenCV와 Camera 패키징 리스크

현재 Camera는 Windows에서 먼저 `cv2.VideoCapture(index, cv2.CAP_MSMF)`를 시도하고 실패하면 backend를 지정하지 않은 `cv2.VideoCapture(index)`로 fallback한다. `CAP_DSHOW`는 사용하지 않는다.

현재 `cv2.pyd`는 Windows Media Foundation의 `MFPlat.dll`, `MF.dll`, `MFReadWrite.dll`과 Direct3D 관련 system DLL에 의존한다. 따라서 Windows N/KN edition에서는 Media Feature Pack이 추가 prerequisite가 될 수 있다. `opencv-python-headless`는 HighGUI의 `imshow`, `waitKey`, `destroyAllWindows`와 Camera UI 요구사항을 만족하지 않으므로 사용하지 않는다.

다음 build에서는 Webcam을 자동 실행하지 않는 import smoke test 후, 사용자가 승인한 별도 단계에서 Camera open/read, MSMF fallback, OpenCV window 표시를 검증한다.

## API/Auth와 CLI 호환성

AI Client의 보안 경계는 변경하지 않았다.

- `FITROUTE_ACCESS_TOKEN`: Launcher가 child process environment로만 전달하고 `src/api_client.py`가 읽는다.
- `FITROUTE_API_BASE_URL`: 같은 child environment에서 읽으며 없으면 개발 기본값 `http://127.0.0.1:8000`을 사용한다.
- Password와 refresh token: AI Client가 받거나 저장하지 않는다.
- Supabase Desktop Auth와 Credential Manager: Launcher 책임이다.

다음 개발 CLI는 그대로 유지한다.

```powershell
python src/main.py --exercise squat
python src/main.py --exercise squat --auto-start-session
```

## PyInstaller onedir 선택 이유

AI runtime에는 수백 MiB 이상의 Torch/CUDA/TensorRT/OpenCV native binary와 외부 model이 있다. `--onefile`은 매 실행마다 임시 디렉터리로 대용량 압축 해제하고 DLL 탐색과 보안 제품 검사 비용을 증가시킨다. 첫 독립 AI Client는 다음 이유로 `--onedir`를 선택한다.

- DLL과 package-relative resource 위치를 직접 검사하기 쉽다.
- 누락 binary를 단계적으로 진단할 수 있다.
- 실행 시 압축 해제 지연이 없다.
- 모델을 exe 옆 `models/`로 독립 배치할 수 있다.
- installer가 전체 폴더를 설치하도록 구성하기 쉽다.

## 다음 build environment 후보

첫 후보는 현재 성공 환경과 ABI를 맞춘 Python 3.12 전용 `fitroute_build` Conda environment다. 아래 목록은 초안이며 이번 단계에서 환경을 생성하거나 설치하지 않았다.

Runtime 직접 후보:

```text
python=3.12
numpy==2.4.4
opencv-contrib-python==5.0.0.93
ultralytics==8.4.70
torch==2.11.0+cu128
torchvision==0.26.0+cu128
tensorrt==11.0.0.114
mediapipe==0.10.35
xgboost==3.4.1
scikit-learn==1.9.1
httpx==0.28.1
```

Build/test 후보:

```text
pyinstaller==6.22.3
pytest
```

Ultralytics와 MediaPipe의 declared dependencies가 서로 다른 OpenCV distribution을 설치하려 할 수 있으므로, 새 환경에서는 `cv2` provider가 `opencv-contrib-python` 하나인지 확인한다. PyTorch CUDA wheel은 공식 CUDA 12.8 index를 사용해야 할 수 있다. transitive package는 resolver 결과를 기록하되 `vision_ai`의 전체 freeze를 복사하지 않는다.

## 다음 FitRouteAIClient.spec 개요

아직 spec은 만들지 않았다. 다음 단계의 예상 구성은 다음과 같다.

1. Entry: `src/main.py`
2. Mode: `onedir`, 초기 진단 build는 `console=True`
3. Contents directory: `_internal`
4. `pathex`: Repository root
5. Hidden imports: Ultralytics TensorRT backend, `tensorrt`, 필요한 MediaPipe Tasks 하위 모듈
6. Binaries: Torch/CUDA runtime, TensorRT inference 최소 DLL, `libmediapipe.dll`, `xgboost.dll`, OpenCV/FFmpeg native binary
7. Data: 필요한 package data만 선별; models는 build 후 exe 옆 `models/`로 staging
8. Excludes: test/dev/export/UI package는 Analysis 결과와 import smoke test 후 확정
9. Runtime hook: 필요할 경우 `_internal` native DLL directory만 `os.add_dll_directory()`로 등록
10. Validation: import → model existence → TensorRT deserialize → MediaPipe create → XGBoost load/predict → Webcam 없는 CLI smoke 순서

## 이번 단계 테스트

추가한 `tests/test_paths.py`는 다음을 검증한다.

- 개발 실행의 Repository root 계산
- mocked frozen 실행의 `sys.executable.parent` 계산
- 네 개 model resource의 frozen path
- 개발 Repository의 실제 model file 존재와 config path 일치

전체 관련 테스트는 Webcam을 열지 않고 실행한다.

## 다음 단계 명령 초안

다음 승인 단계에서만 실행한다.

```powershell
conda create -n fitroute_build python=3.12 -y
conda activate fitroute_build

# 실제 설치는 PyTorch CUDA 12.8 공식 wheel source와 OpenCV provider 충돌을
# 먼저 확정한 뒤, 위 후보 버전을 사용한다.
python -m pip install pyinstaller==6.22.3 pytest

# 이후에만 FitRouteAIClient.spec 작성 및 onedir build
python -m PyInstaller FitRouteAIClient.spec --noconfirm --clean
```

이 명령은 1단계에서는 실행하지 않았다. 실제 2단계 성공 명령은 다음 절에 기록한다.

## 2단계: clean build environment 검증 결과

검증일: 2026-09-14. 기존 `vision_ai`는 조회와 기존 path test 실행에만 사용했고 package 설치, 제거, upgrade 또는 downgrade를 하지 않았다.

### 환경 생성과 설치 결과

- 환경: `fitroute_build`
- Python: 3.12.12
- 실행 파일: `C:\Users\AISW_203_113\anaconda3\envs\fitroute_build\python.exe`
- `conda run -n fitroute_build where.exe python`의 첫 결과도 위 실행 파일이었다.
- Torch 2.11.0+cu128과 TorchVision 0.26.0+cu128은 PyTorch 공식 CUDA 12.8 wheel index에서 설치했다.
- TensorRT metapackage가 실제로 `tensorrt_cu13`, `tensorrt_cu13_bindings`, `tensorrt_cu13_libs` 11.0.0.114를 설치하는 것을 확인했다.
- PyInstaller 6.22.3과 `pyinstaller-hooks-contrib` 2026.7을 설치했지만 spec 작성이나 build는 실행하지 않았다.

Repository의 dependency 파일은 역할을 분리한다.

- `packaging/ai_client/requirements-runtime.txt`: 사람이 관리하는 핵심 top-level runtime 버전
- `packaging/ai_client/requirements-build.txt`: PyInstaller build 도구
- `packaging/ai_client/requirements-lock.txt`: 검증 환경에서 해석된 전체 snapshot. Conda bootstrap의 `pip`, `setuptools`, `wheel`은 제외했다.

### 핵심 버전 비교

| Package | vision_ai | fitroute_build | 결과 |
|---|---:|---:|---|
| Python | 3.12.12 | 3.12.12 | 일치 |
| NumPy | 2.4.4 | 2.4.4 | 일치 |
| PyTorch | 2.11.0+cu128 | 2.11.0+cu128 | 일치 |
| TorchVision | 0.26.0+cu128 | 0.26.0+cu128 | 일치 |
| Ultralytics | 8.4.70 | 8.4.70 | 일치 |
| OpenCV distribution | opencv-contrib-python 5.0.0.93 | opencv-contrib-python 5.0.0.93 | 일치 |
| MediaPipe | 0.10.35 | 0.10.35 | 일치 |
| XGBoost | 3.4.1 | 3.4.1 | 일치 |
| scikit-learn | 1.9.1 | 1.9.1 | 일치 |
| HTTPX | 0.28.1 | 0.28.1 | 일치 |
| TensorRT | 11.0.0.114 | 11.0.0.114 | 일치 |
| TensorRT cu13 packages | 11.0.0.114 | 11.0.0.114 | 일치 |
| PyInstaller | 6.22.3 | 6.22.3 | 일치 |

### CUDA, import와 model smoke 결과

- `torch.cuda.is_available()`: `True`
- PyTorch CUDA runtime: 12.8
- GPU: NVIDIA GeForce RTX 3080
- 개별 import: `cv2`, `numpy`, `torch`, `torchvision`, `ultralytics`, `mediapipe`, `xgboost`, `sklearn`, `httpx`, `tensorrt` 모두 성공
- TensorRT import/version: 11.0.0.114
- OpenCV: module 5.0.0, `CAP_MSMF == 1400`, `cv2.imshow` callable, provider는 `opencv-contrib-python` 하나
- CLI: `python src/main.py --help` 성공. Camera는 열리지 않았다.
- Resource: engine 7,731,821 bytes, task 9,398,198 bytes, XGBoost model 3,378,634 bytes, classes 110 bytes 모두 Repository root에서 발견
- XGBoost: model load 성공, 132 features 확인. 기존 확장자 경고에 따라 UBJSON으로 추정했지만 오류는 없었다.
- Class order: `squat`, `run`, `sit`, `stretch`, `walk`, `jump`, `bendover`, `stand`, `lying`
- MediaPipe: Tasks API import, `PoseLandmarkerOptions`, 외부 task asset을 사용한 PoseLandmarker 생성과 close 성공. Image/Camera inference는 하지 않았다.
- Ultralytics: `YOLO` import와 TensorRT engine path 선택 성공. GPU/TensorRT context 생성을 피하려고 YOLO 객체 생성과 inference는 하지 않았다.
- 기존 path test: 4 passed

### Known Packaging Metadata Exception: OpenCV

현재 두 핵심 package의 declared requirement는 동시에 단일 OpenCV provider를 표현할 수 없다.

- MediaPipe 0.10.35: `opencv-contrib-python` 요구
- Ultralytics 8.4.70: `opencv-python>=4.6.0` 요구

두 wheel은 같은 `cv2` namespace와 native files를 설치하므로 clean build environment에는 `opencv-contrib-python`만 설치하고 Ultralytics를 `--no-deps`로 설치했다. 실제 imports, HighGUI와 MSMF 검증은 성공했지만 distribution metadata상 `opencv-contrib-python`은 `opencv-python`을 대신 만족시키지 않는다. 따라서 `python -m pip check`는 다음 한 건으로 종료 코드 1을 반환한다.

```text
ultralytics 8.4.70 requires opencv-python, which is not installed.
```

기존 `vision_ai`도 Ultralytics에 대해 같은 경고가 있으며, 그 외 오래된 개발 package의 OpenCV 요구 불일치도 존재한다. 새 환경에 두 OpenCV wheel을 동시에 설치하거나 package metadata를 위조하지 않았다.

FitRoute build validation은 다음 중 하나만 유효한 상태로 판정한다.

1. `pip check`가 종료 코드 0으로 성공한다.
2. 위 문구와 정확히 같은 오류 한 줄만 존재하고, `opencv-contrib-python==5.0.0.93`만 설치되어 있으며 OpenCV GUI/MSMF smoke가 성공한다.

허용 문구가 달라지거나 다른 dependency conflict가 한 줄이라도 추가되면 실패한다. contrib wheel이 없거나 `opencv-python`, `opencv-python-headless`, `opencv-contrib-python-headless` 중 하나가 함께 설치되어도 실패한다.

### Build environment validator

`packaging/ai_client/validate_build_env.py`가 위 정책을 실행 가능한 validation rule로 고정한다. 이 스크립트는 현재 Python environment, OpenCV distribution 집합과 버전, GUI/MSMF, CUDA, TensorRT, MediaPipe Tasks, XGBoost, Ultralytics, HTTPX import를 검사하고 `pip check` 원문을 제한적으로 판정한다. Webcam, 모델 inference와 GPU benchmark는 실행하지 않는다.

`fitroute_build`에서의 실제 결과:

```text
Python environment: fitroute_build
OpenCV distribution: opencv-contrib-python 5.0.0.93
Duplicate OpenCV wheels: NO
OpenCV GUI: OK
MSMF: OK
CUDA: OK (12.8)
TensorRT: OK (11.0.0.114)
MediaPipe: OK (0.10.35)
XGBoost: OK (3.4.1)
Ultralytics: OK (8.4.70)
HTTPX: OK (0.28.1)
Known metadata exception: ALLOWED
Allowed metadata exceptions: 1
Unexpected dependency conflicts: 0
BUILD ENVIRONMENT VALID
```

Validator 종료 코드는 0이었다. 정책 단위 테스트 5개와 기존 path test 4개도 통과했으므로 2단계 build environment 준비를 완료하고 3단계 spec 작성이 가능한 상태로 판정한다.

### 불필요 package 유입 검사

`PyQt5`, `PyQt6`, `pygame`, `IPython`, `jupyter`, `black`, `pytest`는 새 환경에 없다. `matplotlib`은 MediaPipe 0.10.35가 직접 선언한 runtime dependency라 resolver가 설치했다. `cv2`의 distribution mapping은 `opencv-contrib-python` 하나다.

### 실제 성공한 환경 재생성 명령

현재 셸에는 `PIP_NO_INDEX=1`이 설정될 수 있으므로 설치 시 명시적으로 해제한다. 아래는 이번 단계에서 성공한 순서다. 긴 첫 설치 명령은 OpenCV namespace 충돌을 막기 위해 Ultralytics를 제외한다.

```powershell
conda create -n fitroute_build python=3.12.12 pip -y
conda activate fitroute_build
$env:PIP_NO_INDEX = "0"

python -m pip install --extra-index-url https://download.pytorch.org/whl/cu128 `
  numpy==2.4.4 torch==2.11.0+cu128 torchvision==0.26.0+cu128 `
  tensorrt==11.0.0.114 opencv-contrib-python==5.0.0.93 `
  mediapipe==0.10.35 xgboost==3.4.1 scikit-learn==1.9.1 `
  httpx==0.28.1 pillow==12.2.0 pyyaml==6.0.3 requests==2.32.5 `
  scipy==1.17.1 psutil==7.2.2 polars==1.40.1 `
  nvidia-ml-py==13.610.43 ultralytics-thop==2.0.19 `
  pyinstaller==6.22.3

python -m pip install --no-deps ultralytics==8.4.70
```

Snapshot 기반 clean 재현 후보는 다음과 같다. 이는 이번 단계에서 별도 두 번째 환경으로 재실행하지 않았으며, `--no-deps`를 빼면 pip가 `opencv-python`을 추가할 수 있다.

```powershell
python -m pip install --no-deps `
  --extra-index-url https://download.pytorch.org/whl/cu128 `
  -r packaging/ai_client/requirements-lock.txt
```

### 다음 spec 단계 입력 정보

Hidden import 후보:

- `ultralytics.nn.backends.tensorrt`, `tensorrt`
- `mediapipe.tasks.python`, `mediapipe.tasks.python.core`, `mediapipe.tasks.python.vision`, `mediapipe.tasks.python.vision.pose_landmarker`
- 동적 분석 결과에 따라 `torch`, `torchvision` 하위 backend와 XGBoost sklearn wrapper

Binary/data 후보:

- TensorRT inference DLL과 Python bindings. builder resource DLL은 자동 전체 수집하지 않는다.
- Torch CUDA/cuDNN runtime과 TorchVision native binaries
- `mediapipe/tasks/c/libmediapipe.dll` 및 필요한 package-relative data
- `xgboost/lib/xgboost.dll`, MSVC/OpenMP runtime
- `cv2.pyd`, `opencv_videoio_ffmpeg500_64.dll`, 필요한 OpenCV data
- exe 옆 외부 `models/` 네 resource

OpenCV metadata 차이는 validator로 관리되는 알려진 예외이며 실제 runtime blocker로 취급하지 않는다. 남은 핵심 위험은 clean VM의 NVIDIA driver 및 Toolkit 없는 CUDA/TensorRT 검증, TensorRT engine GPU 호환성, PyInstaller native DLL 최소 집합 선별이다. 이번 단계에서는 spec, EXE, dist, model copy, Launcher, Registry, deploy와 Release를 변경하지 않았다.

## 3단계: PyInstaller onedir 첫 독립 빌드

검증일: 2026-09-14. `fitroute_build`의 Python 3.12.12와 PyInstaller 6.22.3만 사용했다. Launcher, protocol, installer, deploy, Registry와 `vision_ai`는 변경하지 않았다.

### Spec과 build entry

- Spec: `packaging/ai_client/FitRouteAIClient.spec`
- Entry: `src/main.py`
- Mode: onedir, `console=True`, `_internal`, UPX 비활성화
- Build wrapper: `packaging/ai_client/build_ai_client.ps1`
- Wrapper는 활성 환경 이름이 `fitroute_build`인지 확인하고 `validate_build_env.py`를 먼저 실행한다. Ultralytics 분석이 선택 package를 설치하지 못하도록 `YOLO_AUTOINSTALL=false`도 설정한다.

반복 build 명령:

```powershell
conda activate fitroute_build
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/ai_client/build_ai_client.ps1
```

Wrapper 내부 PyInstaller 명령:

```powershell
python -m PyInstaller --noconfirm --clean packaging/ai_client/FitRouteAIClient.spec
```

### Spec 수집 정책

명시적 datas:

- `models/detector/yolo26n.engine` → `models/detector`
- `models/pose/pose_landmarker_full.task` → `models/pose`
- `models/classifier/model_weights.xgb` → `models/classifier`
- `models/classifier/classes.json` → `models/classifier`
- MediaPipe non-binary package data
- XGBoost `VERSION`, `py.typed`
- Ultralytics, MediaPipe, XGBoost, HTTPX distribution metadata

PyInstaller 6은 Analysis datas를 `_internal`에 놓으므로 spec의 COLLECT 이후 검증된 model tree만 EXE 옆 `models/`로 이동한다. Python/native runtime은 `_internal`에 유지한다.

명시적 hidden imports:

- MediaPipe Tasks/Core/Vision/PoseLandmarker 계층
- `tensorrt`, `tensorrt_bindings`, `tensorrt_libs`
- `ultralytics.nn.backends.tensorrt`
- `xgboost`, `xgboost.sklearn`
- `certifi`

Native 처리:

- OpenCV, Torch/TorchVision, scikit-learn은 PyInstaller/contrib 공식 hook을 사용한다.
- MediaPipe `libmediapipe.dll`은 `collect_dynamic_libs("mediapipe")`로 package-relative 위치를 보존한다.
- XGBoost `xgboost.dll`은 `collect_dynamic_libs("xgboost")`로 `xgboost/lib`에 둔다.
- TensorRT contrib hook이 wheel의 `tensorrt_libs`를 수집한다. 첫 안정성 build에서는 builder resource DLL도 유지한다.
- Binary analysis가 개발 PC의 `C:\TensorRT-11.0.0.114\bin`에서 추가로 찾은 최상위 DLL 3개는 wheel-owned DLL과 중복이다. 최상위 복사본을 임시 제외하고 제한된 PATH에서 frozen 진단이 통과한 뒤, spec에서 이 3개만 필터링했다.
- CUDA Toolkit 전체나 Launcher DLL 목록은 수동으로 복사하지 않았다. Torch hook이 wheel 내부 CUDA/cuDNN runtime을 수집했다.
- Matplotlib는 MediaPipe dependency이므로 유지하되 backend는 GUI toolkit이 필요 없는 `Agg`로 고정했다.

Excludes는 `PyQt5`, `PyQt6`, `pygame`, `IPython`, `jupyter`, `black`, `pytest`, `tkinter`, `_tkinter`다. Tkinter는 AI Client runtime graph에 없고 Desktop Login은 Launcher 책임이다.

### 첫 build 문제와 수정

첫 build 자체는 성공했지만 frozen diagnostic에서 XGBoost가 `_internal/xgboost/VERSION`을 찾지 못했다. `collect_data_files("xgboost")` 결과 중 non-binary data를 추가해 `VERSION`과 `py.typed`을 포함한 뒤 model load가 성공했다.

첫 분석 과정에서는 optional tracker import가 `lap` AutoInstall을 실행했다. `lap`은 `fitroute_build`에서 제거했고 build wrapper에 `YOLO_AUTOINSTALL=false`를 넣었다. 이후 clean build에서 다시 설치되지 않았으며 dist에도 포함되지 않았다.

### 최종 산출물

```text
dist/FitRouteAIClient/
├─ FitRouteAIClient.exe
├─ _internal/
└─ models/
   ├─ detector/yolo26n.engine
   ├─ pose/pose_landmarker_full.task
   └─ classifier/
      ├─ model_weights.xgb
      └─ classes.json
```

- EXE: 50,751,244 bytes / 48.40 MiB
- dist: 7,295,590,444 bytes / 6,957.62 MiB / 6.79 GiB
- 파일 수: 3,664
- 네 model resource 모두 EXE 옆에 존재하고 `_internal/models`는 없다.

크기가 큰 주된 이유는 Torch/CUDA/cuDNN과 TensorRT builder resource다. 첫 독립 실행 안정성 검증을 우선했으므로 이번 단계에서는 더 줄이지 않는다.

### Frozen runtime diagnostic

`src/main.py`에 `--diagnose-runtime`을 추가했다. Camera, inference와 network 요청 없이 frozen status, app root, 네 model, OpenCV GUI/MSMF, CUDA/GPU, TensorRT, MediaPipe Tasks, Ultralytics, HTTPX 및 XGBoost 실제 model load를 검사한다. Access Token이나 credential은 출력하지 않는다.

최종 EXE는 개발 Conda/TensorRT 경로를 제외한 Windows system PATH만 둔 상태에서도 다음을 통과했다.

```text
FitRouteAIClient.exe --help                  exit 0
FitRouteAIClient.exe --diagnose-runtime      exit 0
Frozen: YES
CUDA: OK (12.8, NVIDIA GeForce RTX 3080)
TensorRT: OK (11.0.0.114)
MediaPipe: OK (0.10.35)
OpenCV: OK (5.0.0, GUI=True, MSMF=True)
XGBoost: OK (9 classes, 132 features)
RUNTIME DIAGNOSTIC PASS
```

XGBoost의 기존 `.xgb` 확장자를 UBJSON으로 추정하는 warning과 sandbox 임시 폴더의 Matplotlib font cache 쓰기 warning은 비치명적이며 진단 결과에는 영향을 주지 않았다.

### Warning과 native dependency 분석

`build/FitRouteAIClient/warn-FitRouteAIClient.txt`는 885줄이다. TensorRT, MediaPipe, XGBoost, OpenCV, HTTPX, certifi 등 직접 필요한 module 자체의 missing warning은 없다. 주요 warning은 Torch의 선택 기능인 Triton/TensorBoard, export용 ONNX, XGBoost optional pandas/CuPy, HTTP 압축 extras, Ultralytics tracker용 `lap` 등이다. 현재 AI detector/upload 경로에는 필요하지 않고 frozen 진단도 통과했으므로 추가하지 않았다.

PE import table을 EXE, `cv2.pyd`, `libmediapipe.dll`, `xgboost.dll`, TensorRT binding, `torch_cuda.dll`에 대해 검사했다. Bundle 전체와 Windows System32를 기준으로 누락된 direct dependency는 0개다. 포함 확인:

- `cv2.pyd`, `opencv_videoio_ffmpeg500_64.dll`
- `mediapipe/tasks/c/libmediapipe.dll`
- `xgboost/lib/xgboost.dll`, `VCOMP140.DLL`
- Torch/CUDA/cuDNN DLL
- `tensorrt_bindings` pyd와 wheel-owned `tensorrt_libs` DLL
- `python3.dll`, `python312.dll`

PyQt5, PyQt6, pygame, IPython, Jupyter, black, pytest와 lap은 dist에 없다.

### 독립성과 다음 검증

Spec과 build script는 Repository 상대 위치와 PyInstaller가 제공하는 `SPECPATH`, `DISTPATH`를 사용하며 사용자명, Conda 환경 절대경로를 runtime config로 저장하지 않는다. Analysis TOC와 debug metadata에는 build source 절대경로가 기록될 수 있지만 실행 시 참조하는 경로는 아니다. 제한된 PATH frozen diagnostic 성공으로 Python/Conda 및 외부 TensorRT 설치 경로가 startup/import dependency가 아님을 확인했다.

## 4단계: 실제 Camera 수동 검증

사용자가 `dist\FitRouteAIClient\FitRouteAIClient.exe --exercise squat`을 직접 두 차례 실행했다. 두 실행 모두 Camera, YOLO26n TensorRT, MediaPipe, XGBoost, Exercise Logic, HUD와 실제 Squat session이 정상 동작했다.

| 실행 | Processed Frames | End-to-End FPS | Inference FPS |
|---|---:|---:|---:|
| 1차 | 1,765 | 16.88 | 20.28 |
| 2차 | 691 | 15.87 | 21.04 |

Launcher 없이 직접 실행한 2차 테스트의 `Save failed`는 `FITROUTE_ACCESS_TOKEN`이 없는 예상 결과였다. Camera pipeline 실패가 아니며, 5단계에서 Desktop Auth가 만든 token을 child environment로 전달해 해결하도록 했다.

## 5단계: Launcher와 Frozen AI Client 연동

검증일: 2026-09-14. Launcher runtime에서 `python_executable`, `project_root`, `entry_script`를 제거하고 `ai_client_executable` 하나로 교체했다. 상대 경로는 frozen Launcher의 `sys.executable` 부모를 기준으로 해석한다.

```text
fitroute://start?exercise=squat
  -> FitRouteLauncher.exe
  -> Desktop Supabase Auth / Credential Manager
  -> child environment: FITROUTE_ACCESS_TOKEN, FITROUTE_API_BASE_URL
  -> FitRouteAIClient.exe --exercise squat --auto-start-session
```

개발 build의 config는 `desktop_launcher/dist`에서 `..\..\dist\FitRouteAIClient\FitRouteAIClient.exe`를 참조한다. 최종 설치 구조의 기본 예시는 `ai_client\FitRouteAIClient.exe`다. EXE가 없으면 Python이나 source로 fallback하지 않는다. `shell=False`, protocol/command/exercise whitelist, named mutex, Desktop Auth, refresh token Credential Manager 저장과 child-only access token 전달은 유지했다.

Launcher onefile 재빌드 결과는 63,476,752 bytes다. noconsole build에서 stdout/stderr가 없는 경우를 위한 최소 null stream을 추가해 `argparse --help`가 숨겨진 예외 창을 남기지 않게 했다. `--help`와 `--dry-run`은 exit 0이고 각 실행 후 잔류 Launcher process는 0개였으며, config의 상대 EXE 존재 검사도 성공했다. Frozen AI Client의 Camera 없는 `--diagnose-runtime`도 다시 PASS했다. Launcher/Auth/auto-start/path/runtime diagnostic 관련 테스트 39개와 전체 root suite 85개가 통과했다. 자동 검증에서는 Webcam, 실제 Supabase Login, Registry 수정과 network POST를 실행하지 않았다.

다음 수동 E2E는 `start "" "fitroute://start?exercise=squat"`로 수행한다. Desktop Auth 복원 또는 Login, Frozen Client 실행, Camera/inference 후 `E`, Render의 `POST /api/workouts` 201과 Web Dashboard 반영을 사용자가 확인해야 한다. 성공 후 다음 단계는 Inno Setup에 Launcher와 전체 `ai_client/` onedir bundle을 함께 넣는 작업이다.
