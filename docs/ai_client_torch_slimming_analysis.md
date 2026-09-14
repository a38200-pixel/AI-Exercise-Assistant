# FitRoute Windows AI Client — Torch 4GB 정밀 분석 (6-B-3A)

## 1. 결론

현재 검증 완료 baseline은 `dist_candidate_polars/FitRouteAIClient/`이며, 이 디렉터리는 이번 단계에서 수정하지 않았다. 전체 4.849181 GiB 중 Torch가 4,078.972 MiB(약 82.1%)이고, 그중 `torch/lib`가 4,035.562 MiB다. 즉 Torch Python 코드만 줄여 얻을 수 있는 최대치는 수십 MiB이고, GiB 단위 감축에는 native CUDA runtime 구조 변경 또는 Torch를 쓰지 않는 직접 TensorRT 경로가 필요하다.

정적 PE 분석만으로 제거 가능한 대형 DLL은 확정할 수 없다. 특히 `torch_cuda.dll`은 cuBLAS, cuDNN, cuFFT, cuSOLVER, cuSPARSE를 직접 import하며, `torch_cpu.dll`도 cudart, CUPTI, OpenMP, libuv를 직접 import한다. native DLL 제거 전에는 실제 카메라 추론 과정의 loaded-module trace가 필수다.

이번 단계에서는 분석 스크립트와 보고서/JSON inventory만 추가했다. spec, baseline bundle, Launcher, AI Client 실행 코드는 변경하지 않았고 PyInstaller rebuild, Webcam, 네트워크 요청도 수행하지 않았다.

## 2. Current baseline

| 항목 | Bytes | MiB | GiB | 파일 수 |
|---|---:|---:|---:|---:|
| 전체 6-B-2 baseline | 5,206,768,754 | 4,965.561632 | 4.849181 | 3,654 |
| `_internal/torch` | 4,277,112,178 | 4,078.972033 | 3.983371 | 2,201 |
| `_internal/torch/lib` | 4,231,593,696 | 4,035.562225 | 3.941018 | 37 |
| Torch Python/data (`lib` 제외) | 45,518,482 | 43.409807 | 0.042392 | 2,164 |
| `_internal/torchvision` | 25,418,473 | 24.240945 | 0.023673 | 187 |
| TorchVision root `cudart64_12.dll` | 573,952 | 0.547363 | 0.000535 | 1 |

`torch/lib` 37개 파일은 모두 AMD64 PE DLL이다. 전체 파일별 SHA256, architecture, direct imports의 기계 판독 가능한 원본은 `docs/ai_client_torch_bundle_inventory.json`에 있다.

## 3. Table A — Torch Top 50 files

| # | 상대 경로 (`_internal/torch/`) | Bytes | MiB |
|---:|---|---:|---:|
| 1 | `lib/torch_cuda.dll` | 811,555,840 | 773.959961 |
| 2 | `lib/cublasLt64_12.dll` | 674,667,520 | 643.413086 |
| 3 | `lib/cudnn_engines_precompiled64_9.dll` | 481,015,408 | 458.732040 |
| 4 | `lib/cusparse64_12.dll` | 379,535,872 | 361.953613 |
| 5 | `lib/cufft64_11.dll` | 276,121,600 | 263.330078 |
| 6 | `lib/cudnn_adv64_9.dll` | 269,016,688 | 256.554306 |
| 7 | `lib/torch_cpu.dll` | 265,966,080 | 253.645020 |
| 8 | `lib/cusolver64_11.dll` | 225,683,456 | 215.228516 |
| 9 | `lib/cusolverMg64_11.dll` | 157,071,360 | 149.794922 |
| 10 | `lib/cublas64_12.dll` | 113,716,224 | 108.448242 |
| 11 | `lib/cudnn_ops64_9.dll` | 105,604,208 | 100.712021 |
| 12 | `lib/nvrtc64_120_0.alt.dll` | 86,794,240 | 82.773438 |
| 13 | `lib/nvrtc64_120_0.dll` | 86,728,192 | 82.710449 |
| 14 | `lib/nvJitLink_120_0.dll` | 77,860,352 | 74.253418 |
| 15 | `lib/curand64_10.dll` | 71,955,968 | 68.622559 |
| 16 | `lib/cudnn_heuristic64_9.dll` | 58,874,992 | 56.147568 |
| 17 | `lib/cudnn_engines_runtime_compiled64_9.dll` | 27,759,216 | 26.473251 |
| 18 | `lib/nvperf_host.dll` | 21,641,792 | 20.639221 |
| 19 | `lib/torch_python.dll` | 19,164,672 | 18.276855 |
| 20 | `lib/nvrtc-builtins64_128.dll` | 6,356,480 | 6.062012 |
| 21 | `lib/cupti64_2025.1.1.dll` | 4,483,664 | 4.275955 |
| 22 | `lib/cudnn_cnn64_9.dll` | 2,984,560 | 2.846298 |
| 23 | `bin/protoc.exe` | 2,800,640 | 2.670898 |
| 24 | `lib/cudnn_graph64_9.dll` | 2,493,040 | 2.377548 |
| 25 | `lib/libiomp5md.dll` | 1,614,184 | 1.539406 |
| 26 | `testing/_internal/common_methods_invocations.py` | 1,382,286 | 1.318251 |
| 27 | `lib/c10.dll` | 1,088,000 | 1.037598 |
| 28 | `lib/cudart64_12.dll` | 573,952 | 0.547363 |
| 29 | `testing/_internal/generated/annotated_fn_args.py` | 561,383 | 0.535377 |
| 30 | `sparse/_triton_ops_meta.py` | 509,227 | 0.485637 |
| 31 | `testing/_internal/distributed/distributed_test.py` | 452,469 | 0.431508 |
| 32 | `_torch_docs.py` | 450,031 | 0.429183 |
| 33 | `lib/c10_cuda.dll` | 409,600 | 0.390625 |
| 34 | `_inductor/ir.py` | 369,816 | 0.352684 |
| 35 | `fx/experimental/symbolic_shapes.py` | 357,172 | 0.340626 |
| 36 | `_meta_registrations.py` | 292,666 | 0.279108 |
| 37 | `_inductor/scheduler.py` | 288,100 | 0.274754 |
| 38 | `_inductor/lowering.py` | 268,808 | 0.256355 |
| 39 | `nn/functional.py` | 268,135 | 0.255713 |
| 40 | `_inductor/codegen/triton.py` | 267,405 | 0.255017 |
| 41 | `lib/cudnn64_9.dll` | 264,304 | 0.252060 |
| 42 | `_dynamo/symbolic_convert.py` | 260,376 | 0.248314 |
| 43 | `testing/_internal/common_utils.py` | 256,887 | 0.244987 |
| 44 | `distributed/distributed_c10d.py` | 256,735 | 0.244842 |
| 45 | `_inductor/codegen/cpp.py` | 241,098 | 0.229929 |
| 46 | `_refs/__init__.py` | 235,579 | 0.224666 |
| 47 | `onnx/_internal/torchscript_exporter/symbolic_opset9.py` | 232,707 | 0.221927 |
| 48 | `testing/_internal/distributed/rpc/rpc_test.py` | 231,980 | 0.221233 |
| 49 | `_dynamo/variables/higher_order_ops.py` | 224,021 | 0.213643 |
| 50 | `testing/_internal/common_modules.py` | 221,598 | 0.211332 |

## 4. Table B — CUDA/native DLL group size

그룹은 중복 없이 합산했다.

| 그룹 | Bytes | MiB | 파일 수 | 정적 판단 |
|---|---:|---:|---:|---|
| A. Torch CPU core | 286,238,208 | 272.978027 | 5 | KEEP |
| B. Torch CUDA core | 811,965,440 | 774.350586 | 2 | KEEP |
| C. cuBLAS | 788,383,744 | 751.861328 | 2 | DO_NOT_TOUCH_YET |
| D. cuDNN | 948,012,416 | 904.095093 | 8 | DO_NOT_TOUCH_YET |
| E. cuFFT | 276,284,928 | 263.485840 | 2 | DO_NOT_TOUCH_YET |
| F. cuRAND | 71,955,968 | 68.622559 | 1 | NEEDS_DYNAMIC_TRACE |
| G. cuSOLVER | 382,754,816 | 365.023438 | 2 | DO_NOT_TOUCH_YET |
| H. cuSPARSE | 379,535,872 | 361.953613 | 1 | DO_NOT_TOUCH_YET |
| I. CUDA runtime / cudart | 573,952 | 0.547363 | 1 | KEEP |
| J. NVRTC | 179,896,832 | 171.562988 | 4 | NEEDS_DYNAMIC_TRACE |
| K. NVJitLink | 77,860,352 | 74.253418 | 1 | DO_NOT_TOUCH_YET (`cusparse` 직접 의존) |
| L. NCCL/distributed support | 210,432 | 0.200684 | 2 | KEEP (core 직접 의존); NCCL DLL 없음 |
| M. profiler/NVTX | 26,173,584 | 24.961075 | 3 | 혼합: CUPTI KEEP, 나머지 trace |
| N. OpenMP/runtime | 1,658,064 | 1.581253 | 2 | KEEP (`torch_cpu` 직접 의존) |
| O. Other | 89,088 | 0.084961 | 1 | NEEDS_DYNAMIC_TRACE |

Windows bundle에는 NCCL DLL이 없고 `uv.dll`(0.186035 MiB)과 `shm.dll`(0.014648 MiB)만 있다. `uv.dll`은 `torch_cpu.dll`, `shm.dll`은 `torch_python.dll`의 직접 의존성이므로 Python distributed 기능을 쓰지 않더라도 현재 wheel 구조에서는 단순 삭제할 수 없다.

## 5. Table C — Torch Python subtree size

| 서브트리 | Bytes | MiB | 파일 수 | FitRoute 직접 사용 | 판단 |
|---|---:|---:|---:|---|---|
| `torch._dynamo` | 4,144,448 | 3.952454 | 111 | 없음 | MEDIUM, import graph 검증 필요 |
| `torch._inductor` | 8,587,584 | 8.189758 | 335 | 없음 | MEDIUM, import graph 검증 필요 |
| `torch.compiler` | 50,133 | 0.047811 | 3 | 없음 | MEDIUM |
| `torch.fx` | 1,818,411 | 1.734172 | 102 | 없음 | MEDIUM; Torch 내부 사용 범위가 넓음 |
| `torch.export` | 569,431 | 0.543052 | 27 | 없음 | LOW 후보 |
| `torch.onnx` | 1,184,839 | 1.129951 | 92 | 없음 | LOW 후보 |
| `torch.jit` | 405,846 | 0.387045 | 29 | 없음 | DO_NOT_TOUCH_YET; Torch import/serialization 영향 가능 |
| `torch.distributed` | 5,022,619 | 4.789943 | 356 | 없음 | LOW/MEDIUM |
| `torch.testing` | 5,113,291 | 4.876414 | 106 | 없음 | LOW 후보 |
| `torch.profiler` | 154,036 | 0.146900 | 7 | 없음 | LOW 후보(Python만) |

경로명에 `test/tests/testing/example/examples/benchmark/benchmarks`가 포함된 파일을 합치면 5,406,600 bytes, 5.156136 MiB, 172개다. 이 값은 `torch.testing`과 중복되므로 다른 절감량에 더하지 않는다. `torch/include`, `torch/share`, `torch/cmake`는 모두 존재하지 않아 절감 가능량은 0이다. `torch/bin/protoc.exe`는 2.670898 MiB이며 runtime에서 protobuf compiler를 호출하지 않는다면 별도 LOW 후보가 된다.

## 6. Table D — PE dependency summary

아래는 크기/위험도가 큰 파일의 핵심 direct imports다. Windows system DLL은 간략화했다. 전체 37개 DLL의 full SHA256 및 모든 direct imports는 JSON inventory에 기록했다.

| 파일 | MiB | SHA256 | 주요 direct imports | 역할/판단 |
|---|---:|---|---|---|
| `torch_cuda.dll` | 773.959961 | `d5ca93bdf3e246af9c962ec92554e5576dec03b665f9cbf1c664e653f76ddb50` | `c10`, `c10_cuda`, `torch_cpu`, cuBLAS/Lt, `cudnn64_9`, cuFFT, cuSOLVER, cuSPARSE | Torch CUDA dispatcher/kernel; KEEP |
| `torch_cpu.dll` | 253.645020 | `8cdc985486ac95635517786642c8761d3ab5b5372655ec7b4eaaa4c2f98a2212` | `c10`, `cudart64_12`, CUPTI, OpenMP, `uv` | Tensor core/CPU dispatcher; KEEP |
| `torch_python.dll` | 18.276855 | `d8bb1840848cf43554334cd98ed06e4917e3044fb1b5745deec1fa842cdd5a55` | `python312`, `shm`, `torch_cpu`, `torch_cuda` | Python binding; KEEP |
| `cublas64_12.dll` | 108.448242 | `9513540e4ec4c51ee9e7304138c2cc255c29a8c181f9e80c38efa25738becd99` | `cublasLt64_12` | BLAS front-end; direct chain |
| `cublasLt64_12.dll` | 643.413086 | `b199d1ff892a81b7fd3d57ba1781549609b41500b36008fef326038393ad46c7` | system only | BLAS kernels |
| `cudnn_engines_precompiled64_9.dll` | 458.732040 | `3a97df241beb2b75eb5d6152996a9a90d2155c2d4da1aeac5bd66850ed2446c1` | `cudnn_graph64_9` | cuDNN precompiled engines; trace 필요 |
| `cudnn_adv64_9.dll` | 256.554306 | `a8aed3390144ea20d96c0d618462a12cbc7897620380e60438489329b9722531` | `cudnn_graph`, `cudnn_ops` | cuDNN advanced ops; trace 필요 |
| `cudnn_ops64_9.dll` | 100.712021 | `922897bd15a66acecde7c026ecc835b0fc5662c9ae08c120fd89f0f73affa7da` | `cudnn_graph` | cuDNN ops; trace 필요 |
| `cufft64_11.dll` | 263.330078 | `f4fea9227b14843894ad5436725f9638b172171142c95291fc6ae7a493248221` | system only | FFT; `torch_cuda` 직접 의존 |
| `cusolver64_11.dll` | 215.228516 | `3d4f7a66b5f352db56d4bb5962bb453a42d5feb2d831779f4a0bebc9971c36fb` | cuBLAS/Lt, cuSPARSE | solver; `torch_cuda` 직접 의존 |
| `cusolverMg64_11.dll` | 149.794922 | `c3377f10606ff0606be2f08401d54aff6c37f137b78d6b6e21be356a5b4d6cc2` | cuBLAS | multi-GPU solver; trace 필요하나 그룹 부분 제거 위험 |
| `cusparse64_12.dll` | 361.953613 | `f4688daa6163c47a0b5293926ec7ae367de6b4af54ea201638b308831b322a0e` | `nvJitLink_120_0` | sparse; `torch_cuda` 직접 의존 |
| `curand64_10.dll` | 68.622559 | `3465fd1b46e551339b8f44c455756a0f2cba8bd846562eb659040d48edb7aaac` | system only | random ops; dynamic trace 후보 |
| `nvrtc64_120_0.dll` | 82.710449 | `02d2d7ef4690bf1a55dda1d3ac94c86ce8d16920071c87bcd3e70e94ef346e93` | system only | runtime CUDA compilation; trace 후보 |
| `nvrtc64_120_0.alt.dll` | 82.773438 | `5464ea01b079d78042374dc7819684910c8e9d5c63000e2d2d5aa02298ecf2ae` | system only | alternate NVRTC; trace 후보 |
| `nvJitLink_120_0.dll` | 74.253418 | `959d3cb44527ec884db8dc20772520b584dbe7d622d11b0530e6326417078b3e` | system only | JIT linker; cuSPARSE가 직접 참조 |
| `nvperf_host.dll` | 20.639221 | `473b14252a2927607090cba4f12f06436842310245e8e9f5747548813eaff215` | system/VC runtime | profiler; trace 후보 |
| `cupti64_2025.1.1.dll` | 4.275955 | `d026870a2c503d1b6e38a793170823ceca83d776f9b887f63fb0bb5c93d5c525` | system/VC runtime | `torch_cpu` 직접 의존; KEEP |
| `cudart64_12.dll` | 0.547363 | `c2c9a9c22a9bcba90e261825968836787b331038047a26770cffb7a583c28344` | Windows API set | CUDA runtime; `torch_cpu`, `c10_cuda` 직접 의존 |

Direct PE import는 Windows loader가 모듈 로드 시 해결해야 하는 의존성이다. 반면 cuDNN component, NVRTC 등의 내부 `LoadLibrary` 사용 여부는 import table만으로 완전히 알 수 없다. 따라서 “direct import에 없음”은 “삭제 가능”을 의미하지 않는다.

`torch_cuda.dll`에는 cudart의 직접 import가 없지만 `c10_cuda.dll -> cudart64_12.dll` 및 `torch_cpu.dll -> cudart64_12.dll` 체인이 있다. NVRTC는 `torch_cuda.dll`의 direct import는 아니지만 `caffe2_nvrtc.dll -> nvrtc64_120_0.dll` 체인과 runtime lazy-load 가능성이 있다. MKL DLL은 수집되지 않았고 현재 Torch hook 로그도 이 wheel이 MKL에 의존하지 않는 것으로 판정했다.

## 7. Table E — FitRoute/Ultralytics Torch API usage

| 위치/단계 | 확인된 API/동작 | 실행 분류 |
|---|---|---|
| `src/runtime_diagnostic.py` | `import torch`, `torch.cuda.is_available()`, `torch.cuda.get_device_name(0)`, `torch.version.cuda` | 실제 진단 경로 |
| `src/person_detector.py` | 직접 `torch` import 없음; Ultralytics 결과 tensor에 `.detach().cpu().tolist()`, `.item()` | 실제 inference 결과 처리 |
| Ultralytics TensorRT backend | `torch.device`, `torch.from_numpy(np.empty(...)).to(device)`, tensor `.data_ptr()`, `.resize_()` | 실제 engine binding/output |
| Ultralytics predictor preprocess | `torch.from_numpy`, `.to(device)`, `.half()`/`.float()`, `/= 255` | 실제 프레임 전처리 |
| Ultralytics detection postprocess | `non_max_suppression`, boolean/index tensor ops, 클래스 필터용 `torch.tensor(..., device=...)` | 실제 후처리 |
| 모델 metadata | `end2end=true`, `nms=false`, batch 1, image 640, FP16, dynamic false | engine에서 NMS 포함된 출력 |
| NMS 구현 | `end2end` 또는 마지막 차원 6이면 일반 `torchvision.ops.nms` 경로를 조기 우회 | 현재 engine 경로 |
| PyTorch YOLO layers | Conv/BatchNorm/C2f 등 model definition은 import될 수 있으나 `.engine` 추론에서 실행되지 않음 | import-only |
| compiler/training | `torch.compile`, Triton, Inductor, custom CUDA compilation, training, engine build 사용 없음 | 미사용 |

현재 engine은 end-to-end 결과를 내므로 일반 NMS kernel은 우회하지만, confidence/class filtering과 좌표/결과 처리는 여전히 Torch tensor 연산이다. FitRoute가 `classes=[0]`을 전달하므로 Ultralytics NMS 함수 안에서 `torch.tensor(classes, device=prediction.device)`도 실행될 수 있다.

TorchVision은 stream/screenshot/video source 설정과 일반 NMS 경로에서 참조된다. FitRoute는 매 호출마다 OpenCV ndarray 한 장을 전달하고 engine이 end-to-end이므로 핵심 추론 경로에서는 `torchvision.ops.nms` 실행 가능성이 낮다. 다만 hook이 `torchvision._C`를 hidden import하고 Ultralytics의 넓은 import graph가 있으므로 정적 분석만으로 전체 제거를 확정하지 않고 `NEEDS_DYNAMIC_TRACE`로 둔다.

## 8. PyInstaller hook 및 import graph

사용 버전은 PyInstaller 6.22.3, hooks-contrib 2026.7이다. 실제 `hook-torch.py`는 다음을 수행한다.

- `collect_submodules("torch")`: Torch 서브모듈 전체를 hidden import로 수집한다.
- `collect_dynamic_libs("torch")`: wheel의 native DLL 전체를 binaries로 수집한다.
- `collect_data_files("torch", ...)`: header, `.lib`, C++/CUDA source, `.pyi`, `.cmake`를 제외한 data를 수집한다.
- `module_collection_mode = "pyz+py"`: PYZ뿐 아니라 원본 Python 파일도 함께 둔다.
- Windows에서 MKL dependency를 검사하나 이번 build에는 MKL을 추가하지 않았다.

따라서 runtime이 compiler/distributed/testing을 직접 쓰지 않아도 hook 자체가 전체 서브모듈과 전체 dynamic library를 강제로 넣는 것이 4GB 수집의 주원인이다. Analysis TOC에는 `_inductor`, `_dynamo`, `distributed`, `testing` 등이 대량 포함되어 있다. TorchVision hook 역시 `torchvision._C`를 hidden import하고 `pyz+py` 모드를 사용한다. Ultralytics hook은 패키지 data 전체를 수집하고 `pyz+py` 모드를 사용한다.

후속 custom hook/spec에서 가능한 제어 지점은 hidden-import filtering, explicit excludes, datas filtering, binaries TOC filtering, module collection mode 축소다. 하지만 Torch 최상위 import의 side effect 및 Ultralytics lazy import를 고려해 항목별 candidate build와 전체 E2E 회귀 검증이 필요하다.

현재 Analysis TOC에서 `C:\Program Files\NVIDIA GPU Computing Toolkit\...` 문자열은 0건이다. 제한 PATH에서 통과한 기존 진단과 함께 볼 때 시스템 CUDA Toolkit은 runtime 요구사항이 아니며, NVIDIA Driver는 설치 대상 PC에 별도로 있어야 한다. 구분은 다음과 같다.

- NVIDIA Driver: 설치 대상 시스템 제공, bundle에 포함하지 않음.
- CUDA/PyTorch CUDA DLL: 현재 `_internal/torch/lib`에 포함.
- TensorRT runtime: bundle에 별도 포함.
- CUDA Toolkit/compiler: build-time 도구이며 현재 runtime TOC 출처가 아님.

## 9. Table F — Optimization candidate matrix

| 후보 | 크기(MiB) | 분류 | 위험 | 근거/필수 검증 |
|---|---:|---|---|---|
| Torch CPU/CUDA core, c10, torch_python | 1,047.329 | KEEP | HIGH | Torch tensor/binding과 Python API 핵심 |
| cudart | 0.547 | KEEP | HIGH | `torch_cpu`, `c10_cuda` 직접 import |
| cuBLAS | 751.861 | DO_NOT_TOUCH_YET | HIGH | `torch_cuda` 직접 import |
| cuDNN 전체 | 904.095 | DO_NOT_TOUCH_YET | HIGH | loader를 `torch_cuda`가 직접 import; component lazy-load 가능 |
| cuFFT | 263.486 | DO_NOT_TOUCH_YET | HIGH | `torch_cuda` 직접 import |
| cuSOLVER | 365.023 | DO_NOT_TOUCH_YET | HIGH | `torch_cuda` 직접 import; 내부 cuBLAS/cuSPARSE 연쇄 |
| cuSPARSE | 361.954 | DO_NOT_TOUCH_YET | HIGH | `torch_cuda` 직접 import; NVJitLink 연쇄 |
| NVJitLink | 74.253 | DO_NOT_TOUCH_YET | HIGH | cuSPARSE가 직접 import |
| cuRAND | 68.623 | NEEDS_DYNAMIC_TRACE | MEDIUM/HIGH | FitRoute random op 없음; native lazy-load 확인 필요 |
| NVRTC group | 171.563 | NEEDS_DYNAMIC_TRACE | MEDIUM/HIGH | compile/Inductor 미사용이나 `caffe2_nvrtc` 및 lazy-load 확인 필요 |
| `nvperf_host` + NVTX (CUPTI 제외) | 20.685 | NEEDS_DYNAMIC_TRACE | MEDIUM | profiler 미사용; CUPTI는 core 직접 의존이라 제외 불가 |
| TorchVision | 24.241 | NEEDS_DYNAMIC_TRACE | MEDIUM | 현재 end-to-end NMS에는 불필요해 보이나 import/startup 추적 필요 |
| `torch.testing` | 4.876 | LIKELY_REMOVABLE | LOW | runtime 기능이 아닌 테스트 지원 |
| `torch/bin/protoc.exe` | 2.671 | LIKELY_REMOVABLE | LOW | runtime code generation 없음 |
| `torch.onnx` | 1.130 | LIKELY_REMOVABLE | LOW | ONNX export 미사용 |
| `torch.export` | 0.543 | LIKELY_REMOVABLE | LOW | export 미사용 |
| `torch.profiler` Python | 0.147 | LIKELY_REMOVABLE | LOW | profiler 미사용; native CUPTI와 구분 |
| `torch.distributed` Python | 4.790 | LIKELY_REMOVABLE | LOW/MEDIUM | single process/GPU지만 Torch 내부 import 확인 필요 |
| `_dynamo` + `_inductor` + `compiler` | 12.190 | LIKELY_REMOVABLE | MEDIUM | compile 미사용; import-time coupling 검증 필요 |
| `torch.fx` | 1.734 | DO_NOT_TOUCH_YET | MEDIUM | Torch/Ultralytics model import에서 참조될 가능성 큼 |
| `torch.jit` | 0.387 | DO_NOT_TOUCH_YET | MEDIUM | Torch initialization/serialization 영향 가능 |
| include/share/cmake | 0 | 해당 없음 | LOW | 이미 미수집 |

## 10. Table G — Expected savings

중복 없는 합계만 표시한다. 이는 파일을 삭제하라는 결정이 아니라 후속 candidate experiment의 상한치다.

| 경로 | 포함 항목 | 예상 절감 | 예상 bundle 크기 | 신뢰도 |
|---|---|---:|---:|---|
| Low-risk 1차 | testing, protoc, onnx, export, profiler Python | 9.367 MiB | 약 4.840 GiB | 높음(여전히 rebuild/E2E 필요) |
| Python-only 확대 | 위 + distributed, dynamo, inductor, compiler | 26.347 MiB | 약 4.823 GiB | 중간 |
| Python-only 이론 최대 | Torch Python/data 전체 | 43.410 MiB | 약 4.807 GiB | 낮음; 실제 제거 불가 모듈 포함 |
| Native trace 후보 | NVRTC + cuRAND + nvperf/NVTX | 최대 약 260.871 MiB | Python 확대와 함께 약 4.569 GiB | 낮음; loaded-module trace 전 제거 금지 |
| 직접 TensorRT 구조 | Torch/TorchVision/Ultralytics 의존 최소화 | 대략 3.8~4.0 GiB | 약 0.8~1.0 GiB | 아키텍처 변경 필요 |

Python-only 현실적 감축은 4GB 문제의 약 0.6%에 불과하다. native 후보는 절감 폭이 크지만 wheel의 정적/동적 연결 관계 때문에 실패 비용도 크다. 현재 구조를 유지한 채 안전하게 시도할 다음 target은 약 4.82~4.84 GiB다.

## 11. Dynamic DLL tracing plan

다음 단계에서는 baseline과 candidate를 같은 방식으로 추적한다. 외부 도구 설치 없이 별도 Python monitor에서 Windows PSAPI(`EnumProcessModulesEx`, `GetModuleFileNameExW`) 또는 `psutil.Process(pid).memory_maps()`를 사용해 대상 PID의 module path를 100ms 이하 주기로 polling할 수 있다. 짧게 load 후 unload되는 모듈을 놓치지 않으려면 한 번의 snapshot보다 누적 집합을 저장한다.

권장 시퀀스:

1. baseline 프로세스 시작 직후 import/startup 모듈 집합을 기록한다.
2. 카메라 준비 후 첫 프레임 전 집합을 기록한다.
3. 실제 TensorRT 추론을 여러 프레임 수행하며 누적 모듈을 기록한다.
4. 종료 전 집합과 단계별 delta를 JSON/CSV로 저장한다.
5. 동일 하드웨어·환경에서 candidate를 반복하고 기능/성능/E2E 결과와 비교한다.

우선 추적할 파일은 cuDNN 8개 component, cuBLAS 2개, cuFFT 2개, cuSOLVER 2개, cuSPARSE, cuRAND, NVRTC 4개, NVJitLink, `nvperf_host`, NVTX, CUPTI, TorchVision `_C.pyd` 및 Torch core DLL이다. Process Explorer/Process Monitor는 수동 교차검증용으로 사용할 수 있지만 자동화 결과는 PSAPI 기반 누적 trace가 재현성이 더 좋다.

## 12. cuDNN/cuBLAS/기타 native 판단

- cuDNN: TensorRT는 자체 runtime/plugin으로 engine을 실행하고 PyTorch Conv layer는 실행하지 않지만, `torch_cuda.dll`이 cuDNN loader를 직접 참조하고 cuDNN 9 component는 lazy-load될 수 있다. 전체 및 component 모두 아직 제거 금지다.
- cuBLAS: FitRoute 코드가 행렬곱을 직접 호출하지 않아도 `torch_cuda.dll`의 직접 의존이다. 제거 금지다.
- cuFFT: FFT 사용은 없지만 `torch_cuda.dll` 직접 의존이라 제거 금지다.
- cuSOLVER: solver 사용은 없지만 `torch_cuda.dll` 직접 의존이며 cuBLAS/cuSPARSE 연쇄가 있어 제거 금지다.
- cuSPARSE: sparse op 사용은 없지만 `torch_cuda.dll` 직접 의존이고 NVJitLink를 직접 참조한다. 제거 금지다.
- cuRAND: random CUDA op는 확인되지 않았고 direct import chain에도 나타나지 않아 trace 후보지만 정적 정보만으로 제거하지 않는다.
- NVRTC: `torch.compile`, Triton, Inductor, custom CUDA compile, TensorRT engine build는 실행하지 않는다. 다만 Torch native lazy load와 `caffe2_nvrtc`를 확인해야 하므로 trace 후보다.

## 13. Alternative direct-TensorRT strategy

현재 7.37 MiB YOLO26n engine은 metadata상 정적 batch 1, 640 입력, FP16, end-to-end 출력이다. Ultralytics/Torch 대신 TensorRT Python API를 직접 쓰는 구조는 기술적으로 가능하다.

필요 작업은 engine metadata 파싱, TensorRT 11 named-tensor binding, CUDA device buffer/stream 및 H2D/D2H copy, OpenCV/NumPy letterbox·BGR→RGB·BCHW·FP16 normalization, `[1, 300, 6]` end-to-end 결과의 confidence/class filter와 좌표 scaling, 기존 detection result interface 호환이다.

장점은 Torch native 약 4GB와 TorchVision/Ultralytics import 상당 부분을 없앨 가능성이 있고 startup 및 dependency 통제가 쉬워지는 것이다. 위험은 전처리/후처리 parity, CUDA context/memory 수명, TensorRT/GPU/driver ABI 호환, engine metadata 변화, 결과 인터페이스 회귀, PT fallback 상실, 별도의 성능·정확도 검증 비용이다. 이는 파일 제거 실험이 아니라 별도 아키텍처 프로젝트로 다뤄야 하며 이번 단계에서는 구현하지 않았다.

## 14. 6-B-3B 권장 순서

가장 낮은 위험의 개별 후보 5개는 다음 순서다.

1. `torch/bin/protoc.exe` (2.670898 MiB)
2. `torch.testing` (4.876414 MiB)
3. `torch.profiler` Python tree (0.146900 MiB)
4. `torch.onnx` (1.129951 MiB)
5. `torch.export` (0.543052 MiB)

각 후보는 한 번에 하나씩 custom hook/TOC filtering candidate로 만들고 `--help`, `--diagnose-runtime`, import/startup, Camera/TensorRT inference, pose/classification/count, Launcher/protocol/auth, Render/Supabase/dashboard, A/B 성능까지 모두 통과한 뒤에만 다음 후보와 합친다. native CUDA DLL 실험은 이 다섯 항목보다 먼저 하지 않는다.

## 15. 재현 방법과 작업 보호

분석 스크립트:

```powershell
C:\Users\AISW_203_113\anaconda3\envs\fitroute_build\python.exe packaging\ai_client\analyze_torch_bundle.py --output docs\ai_client_torch_bundle_inventory.json
```

스크립트는 baseline을 읽어 크기, SHA256, PE import, 그룹, Top 50, Python subtree를 계산한다. 결과 문서는 다음과 같다.

- `packaging/ai_client/analyze_torch_bundle.py`
- `docs/ai_client_torch_bundle_inventory.json`
- `docs/ai_client_torch_slimming_analysis.md`

6-B-3A에서는 baseline 수정 없음, spec 수정 없음, rebuild 없음, Webcam 실행 없음, network 실행 없음, commit/push 없음이다. 따라서 6-B-3B의 Python-only 1차 후보 실험으로 진행할 수 있지만, 실제 변경 전 현재 baseline을 rollback 기준으로 계속 보존해야 한다.

## 16. 6-B-3B-1 — protoc.exe candidate

### 범위와 출처

성공 baseline `dist_candidate_polars/FitRouteAIClient/`은 그대로 보존하고, 별도 candidate에서 다음 파일 하나만 제외했다.

| 항목 | 값 |
|---|---|
| Source package | PyTorch `2.11.0+cu128` |
| Source | `fitroute_build/Lib/site-packages/torch/bin/protoc.exe` |
| Baseline path | `_internal/torch/bin/protoc.exe` |
| PyInstaller TOC 종류 | `BINARY` |
| 크기 | 2,800,640 bytes / 2.670898 MiB |
| SHA256 | `56F90682F1B878CBBCE76B7A8738DBAF20495938D4A809416EA0938D3E55245E` |

이 실행 파일은 PyTorch wheel이 제공하는 Protocol Buffers schema compiler다. Python object serialization이나 MediaPipe Tasks runtime에 필요한 일반 runtime DLL이 아니다. 저장소와 FitRoute runtime import 경로에서 `.proto`→Python code generation 또는 `protoc.exe` subprocess 호출은 발견되지 않았다. `fitroute_build`에는 `google.protobuf` 패키지도 없으며 현재 MediaPipe 0.10.35 Tasks 경로는 FlatBuffers runtime으로 정상 import된다.

### Candidate 구현

- Spec: `packaging/ai_client/FitRouteAIClient.optimized_protoc.spec`
- Build script: `packaging/ai_client/build_ai_client_candidate_protoc.ps1`
- Workpath: `build_candidate_protoc/`
- Distpath: `dist_candidate_protoc/`
- 기존 TensorRT builder 8개 fail-closed filter 유지
- 기존 Polars exclusion/guard 유지
- binaries/datas에서 destination이 정확히 `torch/bin/protoc.exe`인 항목만 조회
- 예상 개수 1, collection `binaries`, typecode `BINARY`, source parent `torch/bin`을 모두 확인한 뒤 제외
- 조건이 다르면 build를 중단하고, COLLECT 후에도 `protoc.exe`가 발견되면 중단

실행한 build 명령의 핵심은 다음과 같다.

```powershell
python -m PyInstaller `
  --noconfirm `
  --clean `
  --workpath build_candidate_protoc `
  --distpath dist_candidate_protoc `
  packaging/ai_client/FitRouteAIClient.optimized_protoc.spec
```

실제 build는 `fitroute_build` 환경, PyInstaller 6.22.3, hooks-contrib 2026.7에서 성공했다. `vision_ai` 패키지는 변경하지 않았고 어떤 패키지도 install/uninstall/upgrade/downgrade하지 않았다.

### 정적 비교 결과

| 항목 | Baseline | protoc candidate | 결과 |
|---|---:|---:|---|
| 파일 수 | 3,654 | 3,653 | -1 |
| Bytes | 5,206,768,754 | 5,203,968,114 | -2,800,640 |
| MiB | 4,965.561632 | 4,962.890734 | -2.670898 |
| GiB | 4.849181 | 4.846573 | -0.002608 |
| 절감률 | - | 0.053788% | baseline 대비 |
| `protoc.exe` | 1 | 0 | PASS |
| TensorRT builder resource | 0 | 0 | PASS |
| Polars runtime/module | 0 | 0 | PASS |
| `torch/lib` | 37 files / 4,231,593,696 bytes | 동일 | PASS |

상대 경로 집합의 유일한 차이는 `_internal/torch/bin/protoc.exe`다. 나머지 모든 공통 파일의 크기는 동일하다. `torch/lib` 37개 DLL 전체 SHA256가 일치하며 `torch_cuda.dll`, `torch_cpu.dll`도 각각 baseline과 동일하다. 다음 모델 4개의 SHA256도 모두 일치한다.

| 모델 | SHA256 |
|---|---|
| `yolo26n.engine` | `BBA6FE01B7114764E4C6625D49E06EBABBCFD15FABFF41E5CBC77BD7F60DAE11` |
| `pose_landmarker_full.task` | `5134A3AAD27A58B93DA0088D431F366DA362B44E3CCFBE3462B3827A839011B1` |
| `model_weights.xgb` | `93571ABF066A2EF50840C88B83B40571D1BCBE93878347613AA9138E07F0A99D` |
| `classes.json` | `A5D6627B3862AAC345A3F40EDE1774C3231F924ACE79B48FCD9A66F907091D87` |

### 카메라 없는 검증

| 검증 | 결과 |
|---|---|
| PowerShell build script syntax | PASS |
| Spec Python syntax | PASS |
| Build environment validation | PASS |
| `FitRouteAIClient.exe --help` | PASS, exit 0 |
| `FitRouteAIClient.exe --diagnose-runtime` | `RUNTIME DIAGNOSTIC PASS`, exit 0 |
| Models | 4개 모두 OK |
| OpenCV | 5.0.0, GUI/MSMF OK |
| CUDA | 12.8, RTX 3080 OK |
| TensorRT | 11.0.0.114 OK |
| MediaPipe | 0.10.35 import/Tasks API OK |
| Ultralytics | 8.4.70 OK |
| HTTPX | 0.28.1 OK |
| XGBoost | 9 classes / 132 features OK |
| MediaPipe PoseLandmarker asset 생성/종료 smoke | PASS |
| FlatBuffers + MediaPipe Tasks import | PASS |
| PyInstaller missing-library warning | 0 |

Baseline/candidate warn 파일은 각각 843줄이며 의미상 새 warning은 없다. 유일한 textual 차이는 같은 Windows optional `posix` warning의 importer 순서뿐이다. 기존 matplotlib font cache permission warning과 XGBoost 구형 `.xgb` format warning은 candidate 신규 회귀가 아니다.

MediaPipe model-load smoke는 Webcam 없이 성공했지만 MediaPipe 내부 Clearcut telemetry가 외부 연결을 자동으로 한 차례 시도했고 `Status_ConnectFailed: 12029`로 실패했다. FitRoute API, Render POST, Supabase 변경은 실행하지 않았으며 성공한 외부 전송은 확인되지 않았다. 후속 자동 smoke에서는 해당 telemetry 가능성을 고려해야 한다.

### 다음 검증

Codex는 Webcam, `--exercise squat`, `fitroute://`, Launcher 설정 변경 또는 workout POST를 실행하지 않았다. 사용자가 직접 실행할 Camera 검증 명령은 다음과 같다.

```cmd
dist_candidate_protoc\FitRouteAIClient\FitRouteAIClient.exe --exercise squat
```

Camera에서 TensorRT detection, MediaPipe pose, XGBoost classification, Squat count와 FPS가 정상인지 확인한다. 이 검증이 통과한 뒤에만 Launcher active config를 candidate EXE로 임시 변경하고 `fitroute://start?exercise=squat`, Desktop Auth, auto session, workout 종료, Render 201, Supabase 저장, Dashboard 증가를 확인한다. E2E 성공 전에는 Launcher가 현재 성공 baseline을 계속 가리키도록 유지한다.

현재 상태는 **CANDIDATE READY FOR USER CAMERA TEST**다. Camera와 Launcher E2E까지 성공하면 다음 candidate는 `torch.testing` 하나만 제외하는 실험이며 여러 Torch subtree를 동시에 제외하지 않는다.
