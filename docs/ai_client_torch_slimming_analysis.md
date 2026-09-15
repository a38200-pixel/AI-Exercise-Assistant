# FitRoute AI Client Torch Slimming Analysis

분석/검증: 2026-09-14~15
상태: **분석 완료 — `protoc.exe`만 제거하고 `torch.testing` 및 native Torch/CUDA runtime은 유지**

## Conclusion

Polars 제거 후 baseline 4.849181 GiB 중 Torch는 4,078.972 MiB로 약 82.1%를 차지했다. 그러나 대부분은 Python test code가 아니라 CUDA/cuDNN을 포함한 native runtime이다.

- `torch/bin/protoc.exe`: 제거 성공, 최종 baseline 반영
- `torch.testing`: 제거 시 `import torch` 실패, 유지
- CUDA/Torch native DLL: 실제 inference trace에서 핵심 그룹 전부 로드, 유지
- Direct TensorRT: GiB 단위 절감 가능성이 있지만 별도 아키텍처 작업으로 분리

## Baseline

| Item | Value |
|---|---:|
| Bundle | `dist_candidate_polars/FitRouteAIClient/` |
| Total | 5,206,768,754 bytes / 4.849181 GiB |
| Torch total | 4,277,112,178 bytes / 4,078.972 MiB |
| `torch/lib` | 4,035.562 MiB |
| Torch Python/subtree remainder | 약 43.410 MiB |

Torch Python code만 줄여 얻을 수 있는 최대치는 수십 MiB다. GiB 단위 절감에는 native CUDA 구조 변경이나 Torch dependency 제거가 필요하다.

## Native dependency findings

FitRoute source는 TensorRT engine 실행을 위해 Ultralytics `YOLO` API를 사용한다. 이 backend가 PyTorch tensor, CUDA device, preprocessing/postprocessing과 NMS 관련 기능을 사용하므로 `import torch`만 성공한다고 inference runtime이 보장되지는 않는다.

PE dependency와 runtime trace에서 확인한 핵심 항목:

- `torch_cuda.dll`, `torch_cpu.dll`, `torch_python.dll`
- cuBLAS, cuDNN, cuSPARSE, cuSOLVER, cuFFT 등 CUDA runtime
- TorchVision native extension
- TensorRT runtime/plugin/parser

최종 Camera trace에서 CUDA 25/25, Torch native 12/12와 TensorRT 4/4가 모두 로드됐다. 따라서 개별 native DLL을 정적 파일명만 보고 제거하지 않았다.

## Accepted candidate: `torch/bin/protoc.exe`

`protoc.exe`는 Protocol Buffers schema compiler이며 FitRoute runtime에는 `.proto` code generation이나 compiler subprocess 경로가 없다.

| Item | Baseline | Candidate | Difference |
|---|---:|---:|---:|
| Bytes | 5,206,768,754 | 5,203,968,114 | -2,800,640 |
| Files | 3,654 | 3,653 | -1 |
| GiB | 4.849181 | 4.846573 | -0.002608 |

Spec은 destination이 정확히 `torch/bin/protoc.exe`인 항목 하나만 제외하고 개수가 다르면 build를 중단한다. 공통 파일, `torch/lib` 37개 DLL과 모델 hash가 baseline과 일치함을 확인했다.

검증 결과:

- PyInstaller build PASS
- `--help`, 제한 PATH `--diagnose-runtime` PASS
- MediaPipe/XGBoost model load PASS
- 실제 Camera/TensorRT/Pose/Squat count PASS
- Launcher/Protocol/Auth/Auto Start PASS
- Render/Supabase/Dashboard E2E PASS

따라서 `dist_candidate_protoc/FitRouteAIClient`을 최종 baseline으로 채택했다.

## Rejected candidate: `torch.testing`

`torch.testing` 6,705,495 bytes를 제외한 candidate는 build와 `--help`에는 성공했지만 runtime diagnostic에서 즉시 실패했다.

```text
ModuleNotFoundError: No module named 'torch.testing'
```

PyTorch 2.11의 최상위 `torch/__init__.py`가 `torch.testing`을 직접 import하기 때문이다.

| Item | Baseline | Candidate | Difference |
|---|---:|---:|---:|
| Bytes | 5,203,968,114 | 5,197,262,619 | -6,705,495 |
| GiB | 4.846573 | 4.840328 | -0.006245 |
| Runtime | PASS | FAIL | `import torch` 회귀 |

이 candidate는 Camera/E2E 대상이 아니며 성공 baseline, Launcher와 Installer에 합치지 않았다.

## Direct TensorRT option

Torch 약 4GB를 근본적으로 제거하려면 Ultralytics/PyTorch backend 대신 TensorRT Python/C++ API를 직접 사용하는 구조가 필요하다.

필수 검증 범위:

- image resize/letterbox/normalize parity
- TensorRT input/output binding과 CUDA memory 관리
- YOLO postprocessing/NMS parity
- 기존 bbox/confidence 결과 비교
- Camera FPS와 GPU memory
- `.pt` fallback 상실에 대한 운영 정책

이는 파일 제거 최적화가 아니라 inference architecture 변경이므로 v0.1.1 범위에는 포함하지 않았다.

## Decision rule

최적화 후보는 하나씩 별도 build하고 `startup → diagnostic → model load → Camera inference → Launcher/Auth → cloud save` 순서로 검증한다. Build size가 줄어도 첫 필수 runtime 단계가 실패하면 즉시 폐기한다.

전체 크기 변화는 [Bundle Size Analysis](ai_client_bundle_size_analysis.md), 실제 DLL 로딩은 [Runtime Module Trace](runtime_module_trace.md)를 참고한다.
