# Windows AI Client Runtime Module Trace

최종 최적화 후보인 `dist_candidate_protoc/FitRouteAIClient`를 실제 카메라·TensorRT 추론 흐름으로 실행해 100ms 간격으로 native module을 관찰한 결과다. 이 문서에는 재현에 필요한 요약만 유지하며, 개인 PC 절대경로가 포함되는 전체 JSON/Markdown 출력은 Git에서 제외된 `artifacts/runtime-traces/`에 생성한다.

## Trace 결과

| 항목 | 결과 |
|---|---:|
| 실행 시간 | 75.609초 |
| 프로세스 종료 코드 | 0 |
| 관찰한 고유 모듈 | 361개 |
| Bundle native inventory | 331개 |
| 실제 로드된 bundle native | 218개 |
| 관찰되지 않은 bundle native | 113개 |

모듈 origin은 Bundle 219개, Windows 134개, NVIDIA Driver 5개, External 3개였다.

## 핵심 런타임 그룹

| 그룹 | Bundle 파일 | 실제 로드 | 크기 |
|---|---:|---:|---:|
| CUDA | 25 | **25** | 2,986.367 MiB |
| Torch native | 12 | **12** | 1,049.196 MiB |
| TensorRT | 4 | **4** | 408.249 MiB |
| MediaPipe | 1 | **1** | 27.405 MiB |
| XGBoost | 1 | **1** | 54.279 MiB |
| OpenCV | 2 | 1 | - |
| TorchVision | 10 | 7 | - |

CUDA, Torch native, TensorRT 핵심 파일은 모두 실제 추론 과정에서 로드됐다. 따라서 이 그룹을 관찰 결과만으로 더 제거하면 실행 안정성을 해칠 가능성이 높다. `torch.testing` 역시 PyTorch 2.11의 최상위 초기화 과정에서 직접 import되므로 유지한다.

관찰되지 않은 파일 중 가장 큰 항목은 OpenCV FFmpeg DLL 약 29.446 MiB였고, 그다음은 PIL AVIF 약 7.527 MiB, TorchVision의 `python312.dll` 약 7.066 MiB였다. 50~100 MiB 이상인 미관찰 native 후보는 없었다. TensorRT builder resource, Polars, `protoc.exe`는 최종 후보에서 모두 0개로 확인됐다.

## 결론

실측 결과로 제거 안전성을 입증할 만한 대형 native dependency가 더 남아 있지 않아 6-B 최적화를 종료했다. 최종 baseline은 원본 6.794548 GiB에서 4.846573 GiB로 줄었으며, 전체 절감량은 약 1.948 GiB(28.67%)다.

## 재현

```powershell
python packaging\ai_client\trace_loaded_modules.py
```

기본 출력 위치:

```text
artifacts/runtime-traces/runtime_module_trace.json
artifacts/runtime-traces/runtime_module_trace.md
```

`artifacts/`는 로컬 분석 산출물 전용이며 Git에 포함하지 않는다.
