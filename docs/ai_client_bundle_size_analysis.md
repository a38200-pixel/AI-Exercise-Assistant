# FitRoute AI Client Bundle Size Analysis

분석/검증: 2026-09-14~15
상태: **6-B 최적화 완료 — `dist_candidate_protoc/FitRouteAIClient`을 최종 Installer baseline으로 채택**

## Final result

| Stage | Files | Bytes | GiB | Original 대비 |
|---|---:|---:|---:|---:|
| Original | 3,664 | 7,295,590,444 | 6.794548 | - |
| TensorRT builder 제거 | 3,656 | 5,390,406,828 | 5.020208 | -26.11% |
| Polars 제거 | 3,654 | 5,206,768,754 | 4.849181 | -28.63% |
| `torch/bin/protoc.exe` 제거 | 3,653 | 5,203,968,114 | **4.846573** | **-28.67%** |

총 절감량은 **2,091,622,330 bytes / 1.947975 GiB**, 감소율은 **28.669679%**다.

최적화는 reference를 보존하고 항목 하나만 제외한 별도 candidate를 만든 뒤 Camera/AI/Launcher/Cloud E2E를 통과한 경우에만 다음 baseline으로 승격하는 방식으로 진행했다.

## Original bottleneck

Original 6.794548 GiB bundle의 92.65%는 DLL이었다. 가장 큰 영역은 다음과 같다.

| Group | Size | Original 비율 | 판단 |
|---|---:|---:|---|
| Torch | 4,078.972 MiB | 58.63% | 현재 Ultralytics/PyTorch 구조의 핵심 runtime |
| TensorRT libs | 2,222.316 MiB | 31.94% | inference 외 builder resource 분리 가능 |
| Polars runtime | 173.880 MiB | 2.50% | FitRoute runtime에서 미사용 |
| OpenCV | 137.128 MiB | 1.97% | Camera/GUI/inference에 필요 |
| XGBoost | 54.279 MiB | 0.78% | 자세 분류에 필요 |
| SciPy | 52.948 MiB | 0.76% | dependency graph에서 보수적으로 유지 |
| MediaPipe | 27.437 MiB | 0.39% | pose 추정에 필요 |

모델 4개는 약 19.559 MiB로 전체 용량의 핵심 원인이 아니며 모두 runtime 입력이므로 유지했다.

## Accepted optimizations

### TensorRT builder resources

현재 Client는 기존 `.engine` 역직렬화와 inference만 수행하고 engine build/export를 수행하지 않는다. TensorRT builder 전용 resource 8개를 정확한 basename/count 조건으로 제외해 약 1.774 GiB를 절감했다.

유지 항목:

- TensorRT Python bindings
- `nvinfer`, plugin과 parser runtime
- YOLO engine deserialize/inference 경로

Camera benchmark와 Web → Launcher → Auth → AI → Render/Supabase/Dashboard E2E를 통과했다.

### Polars runtime

FitRoute source와 실제 Ultralytics inference path에서 사용하지 않는 Polars package를 제외했다. 약 0.171 GiB를 추가 절감했으며 함께 제거된 `_zoneinfo.pyd`는 Polars가 유일하게 가져오던 orphan dependency였다.

### `torch/bin/protoc.exe`

런타임에서 `.proto` code generation이나 compiler subprocess 호출이 없어 `protoc.exe` 한 파일만 제외했다. 절감량은 2,800,640 bytes이며 나머지 공통 파일, Torch DLL과 모델 hash는 baseline과 같았다.

## Rejected optimization

`torch.testing` 제거 candidate는 size/build/`--help`까지 통과했지만 `--diagnose-runtime`에서 실패했다. PyTorch 2.11의 최상위 `torch/__init__.py`가 `torch.testing`을 직접 import하므로 test-only 파일로 볼 수 없다.

- Candidate size: 5,197,262,619 bytes / 4.840328 GiB
- Result: `ModuleNotFoundError: No module named 'torch.testing'`
- Decision: **FAIL / 최종 baseline에 미반영**

실패 candidate는 Camera, Launcher, Installer 또는 Production config에 연결하지 않았다.

## Runtime trace evidence

최종 baseline을 실제 Camera/TensorRT 흐름으로 75.609초 추적했다.

| Group | Bundle | Loaded |
|---|---:|---:|
| CUDA | 25 | 25 |
| Torch native | 12 | 12 |
| TensorRT | 4 | 4 |
| MediaPipe | 1 | 1 |
| XGBoost | 1 | 1 |

Bundle native 331개 중 218개가 실제 로드됐다. 미관찰 파일 중 가장 큰 항목은 OpenCV FFmpeg 약 29.446 MiB였으며, 50~100 MiB 이상의 명확한 추가 제거 후보가 없었다. 세부 내용은 [Runtime Module Trace](runtime_module_trace.md)에 있다.

## Final decision

현재 Ultralytics + Torch 구조에서 native CUDA/Torch DLL을 더 삭제하는 것은 절감 효과보다 회귀 위험이 크다. 따라서 6-B 최적화를 종료하고 4.846573 GiB bundle을 v0.1.1 Installer 입력으로 고정했다.

GiB 단위 추가 절감이 필요하면 파일 삭제가 아니라 Ultralytics/PyTorch를 통과하지 않는 Direct TensorRT 전처리·후처리 구조를 별도 프로젝트로 검증해야 한다.

## Reproduction tools

```powershell
python packaging\ai_client\analyze_bundle_size.py
python packaging\ai_client\analyze_torch_bundle.py
python packaging\ai_client\trace_loaded_modules.py
```

기계별 절대경로를 포함하는 JSON/Markdown 원본은 Git에서 제외된 `artifacts/`에 생성한다.
