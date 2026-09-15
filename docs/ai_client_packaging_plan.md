# FitRoute AI Client Packaging and Validation

최종 갱신: 2026-09-15
상태: **Windows 독립형 AI Client onedir 패키징, Launcher/Installer 통합 및 타 PC E2E 완료**

## Goal and result

개발 PC의 Repository, Python, Conda와 CUDA Toolkit에 의존하지 않고 실행할 수 있도록 AI Client를 PyInstaller `onedir` bundle로 구성했다. 최종 baseline은 다음과 같다.

| Item | Result |
|---|---|
| Bundle | `dist_candidate_protoc/FitRouteAIClient/` |
| Files | 3,653 |
| Size | 5,203,968,114 bytes / 4.846573 GiB |
| Entry | `FitRouteAIClient.exe` |
| Packaging | PyInstaller 6.22.3 onedir |
| Installer | Inno Setup v0.1.1 |

`onedir`은 수 GB의 Torch/CUDA/TensorRT native runtime을 매 실행마다 임시 해제하지 않고, DLL과 model path를 명시적으로 검증하기 위해 선택했다.

## Runtime stack

| Dependency | Validated version |
|---|---|
| Python | 3.12.12 |
| NumPy | 2.4.4 |
| PyTorch / TorchVision | 2.11.0+cu128 / 0.26.0+cu128 |
| CUDA runtime / cuDNN | 12.8 / 9.19 |
| TensorRT | 11.0.0.114 |
| OpenCV provider | opencv-contrib-python 5.0.0.93 |
| MediaPipe | 0.10.35 |
| XGBoost / scikit-learn | 3.4.1 / 1.9.1 |
| Ultralytics | 8.4.70 |
| HTTPX | 0.28.1 |

Build 전용 dependency는 `requirements-build.txt`, runtime 직접/간접 dependency는 `requirements-runtime.txt`, 검증 환경 snapshot은 `requirements-lock.txt`에 분리했다. `opencv-python`과 `opencv-contrib-python`을 동시에 설치하지 않으며 현재 `cv2` provider는 contrib package 하나다.

## Runtime resources

```text
FitRouteAIClient/
├─ FitRouteAIClient.exe
├─ _internal/                 # Python/native runtime
└─ models/
   ├─ detector/yolo26n.engine
   ├─ pose/pose_landmarker_full.task
   └─ classifier/
      ├─ model_weights.xgb
      └─ classes.json
```

Frozen 실행은 `src/paths.py`를 통해 EXE 위치 기준 resource root를 사용한다. 개발 PC username, Conda environment와 Repository 절대경로는 runtime에 저장하지 않는다.

`.engine`을 우선 사용하고 개발 source 실행에서는 `.pt` fallback을 지원한다. ONNX/FP16 ONNX는 Repository에 향후 fallback 후보로 보존하지만 현재 Installer runtime에는 포함하지 않는다.

## Build environment

검증된 별도 Conda environment 이름은 `fitroute_build`다. Build wrapper는 environment를 확인하고 dependency validator를 먼저 실행하며 Ultralytics auto-install을 비활성화한다.

```powershell
powershell -ExecutionPolicy Bypass -File packaging\ai_client\build_ai_client_candidate_protoc.ps1 `
  -PythonExecutable "C:\path\to\fitroute_build\python.exe"
```

기본 재현과 새 baseline 작성에는 `build_ai_client.ps1` 및 `FitRouteAIClient.spec`을 사용하고, 최종 최적화 재현에는 `FitRouteAIClient.optimized_protoc.spec`을 사용한다. Build/output 디렉터리는 Git에 포함하지 않는다.

## PyInstaller collection policy

- OpenCV, Torch/TorchVision과 scikit-learn은 PyInstaller/contrib hook 사용
- MediaPipe `libmediapipe.dll`과 package data의 상대 위치 유지
- XGBoost `xgboost.dll`과 metadata 유지
- TensorRT inference binding/plugin/parser와 Torch CUDA/cuDNN runtime 유지
- Model tree는 COLLECT 후 EXE 옆 `models/`로 배치
- Launcher와 AI Client를 서로 다른 executable/bundle로 유지

AI Client는 Supabase 인증 UI나 Credential Manager를 포함하지 않는다. Launcher가 access token과 API URL을 child environment로 전달하며 AI Client는 완료된 workout summary만 Render API로 전송한다.

## Optimization history

| Baseline | Size | Result |
|---|---:|---|
| Original | 6.794548 GiB | 기능 기준 reference |
| TensorRT builder resource 제거 | 5.020208 GiB | Camera/AI/Launcher E2E PASS |
| Polars runtime 제거 | 4.849181 GiB | Camera/AI/Launcher E2E PASS |
| `torch/bin/protoc.exe` 제거 | **4.846573 GiB** | 최종 baseline, E2E PASS |
| `torch.testing` 제거 | 4.840328 GiB | `import torch` 실패, 폐기 |

Original 대비 2,091,622,330 bytes / 1.947975 GiB, 28.669679%를 절감했다. 성공 candidate만 다음 baseline으로 승격하고 실패 candidate는 Launcher/Installer에 연결하지 않았다.

세부 근거는 [Bundle Size Analysis](ai_client_bundle_size_analysis.md), [Torch Slimming Analysis](ai_client_torch_slimming_analysis.md), [Runtime Module Trace](runtime_module_trace.md)에 정리되어 있다.

## Validation sequence

1. Build environment와 OpenCV provider 검사
2. `--help` startup smoke
3. 제한 PATH의 `--diagnose-runtime`
4. 모델 존재, TensorRT deserialize, MediaPipe create, XGBoost load/predict
5. 실제 Camera frame과 YOLO TensorRT inference
6. Pose/classification/smoothing/Squat count
7. Web → protocol → Launcher → Auth → Frozen Client
8. Render `POST /api/workouts` → Supabase → Dashboard
9. Inno Setup install/uninstall과 별도 Windows PC E2E

최종 candidate는 위 흐름을 통과했다. 자동 smoke에서는 사용자 credential, Registry와 Webcam을 임의로 실행하지 않는다.

## Native runtime findings

- 실제 75.609초 Camera/TensorRT trace에서 Python module 361개 관찰
- Bundle native 331개 중 218개 로드
- CUDA 25/25, Torch native 12/12, TensorRT 4/4 로드
- MediaPipe 1/1, XGBoost 1/1 로드
- 50~100 MiB 이상의 안전한 추가 제거 후보 없음

현재 Ultralytics + Torch 구조에서 추가 native DLL 삭제는 절감 효과보다 회귀 위험이 크다. Torch 약 4GB를 근본적으로 줄이려면 Ultralytics/PyTorch를 통과하지 않는 Direct TensorRT 전처리·후처리 구조가 필요하며 이는 별도 아키텍처 작업이다.

## Known limitations

- TensorRT engine은 GPU architecture, driver와 runtime 호환성에 민감하다.
- NVIDIA Driver는 Installer 외부 prerequisite다.
- XGBoost의 기존 `.xgb` 파일은 UBJSON 추정 경고와 함께 정상 로드된다.
- MediaPipe가 설치 metadata상 matplotlib을 요구하지만 Launcher bundle에서는 사용하지 않아 제외하며, AI Client bundle 정책은 별도로 유지한다.
