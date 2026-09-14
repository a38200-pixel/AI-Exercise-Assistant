# FitRoute AI Client Bundle Size Analysis

분석일: 2026-09-14  
대상: `dist/FitRouteAIClient/` 기준 onedir reference build  
원칙: 이 문서는 6-A 읽기 전용 분석 결과다. Bundle, spec, runtime code, package와 build environment는 변경하지 않았다.

## 결론

정확한 전체 크기는 **7,295,590,444 bytes / 6,957.617 MiB / 6.794548 GiB**다. 파일 3,664개, root를 제외한 디렉터리 572개다. 기존 6.79 GiB/3,664 files 보고와 일치한다.

용량의 핵심은 Python source나 모델이 아니라 native runtime이다. `.dll` 125개가 6,759,375,392 bytes로 전체의 92.65%다. `_internal/torch` 4,078.972 MiB(58.63%)와 `_internal/tensorrt_libs` 2,222.316 MiB(31.94%)만 합쳐도 전체의 90.57%다.

## A. Top-level size

| 항목 | Bytes | MiB | 전체 대비 | Files |
|---|---:|---:|---:|---:|
| `_internal/` | 7,224,330,437 | 6,889.658 | 99.02% | 3,659 |
| `FitRouteAIClient.exe` | 50,751,244 | 48.400 | 0.70% | 1 |
| `models/` | 20,508,763 | 19.559 | 0.28% | 4 |
| **합계** | **7,295,590,444** | **6,957.617** | **100%** | **3,664** |

Models는 `pose_landmarker_full.task` 8.963 MiB, `yolo26n.engine` 7.374 MiB, XGBoost model 3.222 MiB와 110-byte classes JSON이다. 모두 현재 runtime 입력이므로 KEEP이다.

## B. `_internal` Top 30 directories

| # | Directory | Bytes | MiB | Bundle % | Files |
|---:|---|---:|---:|---:|---:|
| 1 | `torch` | 4,277,112,178 | 4,078.972 | 58.6260% | 2,201 |
| 2 | `tensorrt_libs` | 2,330,267,344 | 2,222.316 | 31.9408% | 11 |
| 3 | `_polars_runtime_32` | 182,326,272 | 173.880 | 2.4991% | 1 |
| 4 | `cv2` | 143,789,497 | 137.128 | 1.9709% | 13 |
| 5 | `xgboost` | 56,915,463 | 54.279 | 0.7801% | 3 |
| 6 | `scipy` | 55,520,256 | 52.948 | 0.7610% | 98 |
| 7 | `mediapipe` | 28,770,040 | 27.437 | 0.3943% | 6 |
| 8 | `torchvision` | 25,418,473 | 24.241 | 0.3484% | 187 |
| 9 | `numpy.libs` | 20,990,544 | 20.018 | 0.2877% | 2 |
| 10 | `scipy.libs` | 20,260,864 | 19.322 | 0.2777% | 1 |
| 11 | `matplotlib` | 14,387,698 | 13.721 | 0.1972% | 211 |
| 12 | `PIL` | 13,368,320 | 12.749 | 0.1832% | 7 |
| 13 | `sklearn` | 12,401,042 | 11.827 | 0.1700% | 391 |
| 14 | `numpy` | 6,092,288 | 5.810 | 0.0835% | 13 |
| 15 | `ultralytics` | 3,743,676 | 3.570 | 0.0513% | 341 |
| 16 | `tensorrt_bindings` | 2,996,224 | 2.857 | 0.0411% | 1 |
| 17 | `_sounddevice_data` | 2,039,278 | 1.945 | 0.0280% | 8 |
| 18 | `contourpy` | 487,936 | 0.465 | 0.0067% | 1 |
| 19 | `charset_normalizer` | 310,784 | 0.296 | 0.0043% | 2 |
| 20 | `yaml` | 253,952 | 0.242 | 0.0035% | 1 |
| 21 | `certifi` | 240,216 | 0.229 | 0.0033% | 2 |
| 22 | `numpy-2.4.4.dist-info` | 212,007 | 0.202 | 0.0029% | 24 |
| 23 | `dateutil` | 156,400 | 0.149 | 0.0021% | 1 |
| 24 | `kiwisolver` | 151,552 | 0.145 | 0.0021% | 1 |
| 25 | `ultralytics-8.4.70.dist-info` | 124,901 | 0.119 | 0.0017% | 8 |
| 26 | `psutil` | 70,656 | 0.067 | 0.0010% | 1 |
| 27 | `mediapipe-0.10.35.dist-info` | 49,212 | 0.047 | 0.0007% | 7 |
| 28 | `torchvision-0.26.0+cu128.dist-info` | 45,117 | 0.043 | 0.0006% | 7 |
| 29 | `xgboost-3.4.1.dist-info` | 21,494 | 0.020 | 0.0003% | 6 |
| 30 | `setuptools` | 18,263 | 0.017 | 0.0003% | 8 |

## C. Largest files Top 50

| # | Relative path | MiB | Ext | Owner |
|---:|---|---:|---|---|
| 1 | `_internal/torch/lib/torch_cuda.dll` | 773.960 | dll | PyTorch |
| 2 | `_internal/torch/lib/cublasLt64_12.dll` | 643.413 | dll | PyTorch/CUDA |
| 3 | `_internal/torch/lib/cudnn_engines_precompiled64_9.dll` | 458.732 | dll | cuDNN |
| 4 | `_internal/tensorrt_libs/nvinfer_builder_resource_sm90_11.dll` | 432.987 | dll | TensorRT builder |
| 5 | `_internal/torch/lib/cusparse64_12.dll` | 361.954 | dll | CUDA |
| 6 | `_internal/tensorrt_libs/nvinfer_11.dll` | 358.353 | dll | TensorRT runtime |
| 7 | `_internal/tensorrt_libs/nvinfer_builder_resource_sm100_11.dll` | 270.099 | dll | TensorRT builder |
| 8 | `_internal/torch/lib/cufft64_11.dll` | 263.330 | dll | CUDA |
| 9 | `_internal/torch/lib/cudnn_adv64_9.dll` | 256.554 | dll | cuDNN |
| 10 | `_internal/torch/lib/torch_cpu.dll` | 253.645 | dll | PyTorch |
| 11 | `_internal/tensorrt_libs/nvinfer_builder_resource_sm120_11.dll` | 250.372 | dll | TensorRT builder |
| 12 | `_internal/tensorrt_libs/nvinfer_builder_resource_ptx_11.dll` | 230.090 | dll | TensorRT builder |
| 13 | `_internal/torch/lib/cusolver64_11.dll` | 215.229 | dll | CUDA |
| 14 | `_internal/tensorrt_libs/nvinfer_builder_resource_sm80_11.dll` | 178.134 | dll | TensorRT builder |
| 15 | `_internal/tensorrt_libs/nvinfer_builder_resource_sm89_11.dll` | 176.588 | dll | TensorRT builder |
| 16 | `_internal/_polars_runtime_32/_polars_runtime.pyd` | 173.880 | pyd | Polars |
| 17 | `_internal/tensorrt_libs/nvinfer_builder_resource_sm86_11.dll` | 167.951 | dll | TensorRT builder |
| 18 | `_internal/torch/lib/cusolverMg64_11.dll` | 149.795 | dll | CUDA |
| 19 | `_internal/tensorrt_libs/nvinfer_builder_resource_sm75_11.dll` | 110.703 | dll | TensorRT builder |
| 20 | `_internal/torch/lib/cublas64_12.dll` | 108.448 | dll | CUDA |
| 21 | `_internal/cv2/cv2.pyd` | 107.668 | pyd | OpenCV |
| 22 | `_internal/torch/lib/cudnn_ops64_9.dll` | 100.712 | dll | cuDNN |
| 23 | `_internal/torch/lib/nvrtc64_120_0.alt.dll` | 82.773 | dll | CUDA JIT |
| 24 | `_internal/torch/lib/nvrtc64_120_0.dll` | 82.710 | dll | CUDA JIT |
| 25 | `_internal/torch/lib/nvJitLink_120_0.dll` | 74.253 | dll | CUDA JIT |
| 26 | `_internal/torch/lib/curand64_10.dll` | 68.623 | dll | CUDA |
| 27 | `_internal/torch/lib/cudnn_heuristic64_9.dll` | 56.148 | dll | cuDNN |
| 28 | `_internal/xgboost/lib/xgboost.dll` | 54.279 | dll | XGBoost |
| 29 | `FitRouteAIClient.exe` | 48.400 | exe | Python/PyInstaller |
| 30 | `_internal/tensorrt_libs/nvinfer_plugin_11.dll` | 44.894 | dll | TensorRT plugin |
| 31 | `_internal/cv2/opencv_videoio_ffmpeg500_64.dll` | 29.446 | dll | OpenCV FFmpeg |
| 32 | `_internal/mediapipe/tasks/c/libmediapipe.dll` | 27.405 | dll | MediaPipe |
| 33 | `_internal/torch/lib/cudnn_engines_runtime_compiled64_9.dll` | 26.473 | dll | cuDNN |
| 34 | `_internal/torch/lib/nvperf_host.dll` | 20.639 | dll | CUDA profiling |
| 35 | `_internal/numpy.libs/libscipy_openblas64_-63c857e738469261263c764a36be9436.dll` | 19.470 | dll | NumPy BLAS |
| 36 | `_internal/scipy.libs/libscipy_openblas-64eda39e79589aedb16f58e5547eb599.dll` | 19.322 | dll | SciPy BLAS |
| 37 | `_internal/torch/lib/torch_python.dll` | 18.277 | dll | PyTorch |
| 38 | `models/pose/pose_landmarker_full.task` | 8.963 | task | Model |
| 39 | `_internal/PIL/_avif.cp312-win_amd64.pyd` | 7.527 | pyd | Pillow |
| 40 | `models/detector/yolo26n.engine` | 7.374 | engine | Model |
| 41 | `_internal/python312.dll` | 7.125 | dll | Python runtime |
| 42 | `_internal/torchvision/python312.dll` | 7.066 | dll | TorchVision-associated |
| 43 | `_internal/libcrypto-3-x64.dll` | 7.009 | dll | OpenSSL |
| 44 | `_internal/torchvision/_C.pyd` | 7.000 | pyd | TorchVision ops |
| 45 | `_internal/scipy/optimize/_highspy/_core.cp312-win_amd64.pyd` | 6.145 | pyd | SciPy |
| 46 | `_internal/torch/lib/nvrtc-builtins64_128.dll` | 6.062 | dll | CUDA JIT |
| 47 | `_internal/torchvision/nvjpeg64_12.dll` | 5.886 | dll | TorchVision/NVIDIA |
| 48 | `_internal/torch/lib/cupti64_2025.1.1.dll` | 4.276 | dll | CUDA profiler |
| 49 | `_internal/scipy/sparse/_sparsetools.cp312-win_amd64.pyd` | 3.924 | pyd | SciPy |
| 50 | `_internal/numpy/_core/_multiarray_umath.cp312-win_amd64.pyd` | 3.542 | pyd | NumPy |

50 MiB 이상은 위 표 1~28번의 28개다. 48.400 MiB인 EXE는 50 MiB 미만이다.

## Package detail

| Component | Bytes | MiB | Files | 판단 |
|---|---:|---:|---:|---|
| PyTorch | 4,277,112,178 | 4,078.972 | 2,201 | Core KEEP / 일부 세부 항목 조사 |
| `torch/lib` | 4,231,593,696 | 4,035.562 | 37 | DO_NOT_TOUCH_YET |
| Torch CUDA-name DLL | 3,916,844,928 | 3,735.394 | 23 | DO_NOT_TOUCH_YET |
| TorchVision | 25,463,590 | 24.284 | 194 | Core ops KEEP, data 후보 조사 |
| TensorRT | 2,333,273,210 | 2,225.183 | 15 | Runtime KEEP, builder 후보 |
| MediaPipe | 28,819,252 | 27.484 | 13 | KEEP |
| OpenCV | 143,789,497 | 137.128 | 13 | KEEP, FFmpeg 별도 시험 후보 |
| XGBoost | 56,936,957 | 54.299 | 9 | KEEP |
| scikit-learn | 12,401,042 | 11.827 | 391 | wrapper core KEEP, broad subpackages 후보 |
| SciPy incl. `scipy.libs` | 75,781,120 | 72.271 | 99 | NEEDS_RUNTIME_TEST |
| NumPy incl. `numpy.libs` | 27,294,839 | 26.030 | 39 | KEEP |
| Matplotlib | 14,387,698 | 13.721 | 211 | NEEDS_RUNTIME_TEST |
| Ultralytics | 3,868,577 | 3.689 | 349 | inference core KEEP, feature data 후보 |

### PyTorch and TorchVision

`torch/lib`가 Torch 크기의 98.94%다. Python/source 쪽 큰 항목은 `_inductor` 8.190 MiB, `testing` 4.876 MiB, `distributed` 4.790 MiB, `_dynamo` 3.952 MiB, `bin` 2.671 MiB, `ao` 1.866 MiB, `utils` 1.843 MiB, `nn` 1.735 MiB, `fx` 1.734 MiB, `_functorch` 1.270 MiB, `onnx` 1.130 MiB다.

Torch는 TensorRT engine을 사용해도 제거할 수 없다. 실제 Ultralytics TensorRT backend는 다음에 Torch를 사용한다.

- `torch.device("cuda:0")`로 device 선택
- `torch.from_numpy(...).to(device)`로 TensorRT I/O binding용 CUDA tensor 할당
- input/output pointer를 Torch tensor에서 취득
- frame preprocessing과 dtype/FP16 변환
- postprocessing, class filtering, NMS와 결과 tensor
- FitRoute에서 `boxes.xyxy/conf.detach().cpu()` 결과 변환

TorchVision은 `_C.pyd` 7.000 MiB, 별도 `python312.dll` 7.066 MiB, `nvjpeg` 5.886 MiB가 대부분이다. Ultralytics predictor가 TorchVision을 import하고 NMS가 `torchvision.ops.nms` 경로를 가질 수 있다. `models` 0.978 MiB, `datasets` 0.381 MiB, 일부 transforms는 현재 TensorRT detection에는 불필요해 보이지만 ops/native와 분리해 시험해야 한다.

### TensorRT

| 분류 | 내용 | MiB | 판정 |
|---|---|---:|---|
| A | `nvinfer_11.dll` inference runtime | 358.353 | KEEP / High risk |
| A | `nvinfer_plugin_11.dll` plugin runtime | 44.894 | KEEP; engine plugin 사용 여부가 직렬화 내용에 의존 |
| A | Python bindings | 2.857 | KEEP |
| B | builder resources 8개 | 1,816.925 | LIKELY_REMOVABLE / Medium risk |
| B | `nvonnxparser_11.dll` | 2.145 | 논리상 미사용이나 binding의 direct import라 단순 삭제 금지 |
| C | Python/package resource | 0.009 | 영향 미미 |

현재 runtime은 기존 `.engine` 역직렬화/inference만 수행하며 builder와 ONNX parse/export를 호출하지 않는다. 그러나 `tensorrt_libs/__init__.py`는 폴더의 모든 DLL을 `ctypes.CDLL()`로 시도하고, Python binding은 `nvinfer`, plugin, `nvonnxparser`를 direct import한다. 따라서 builder resource는 가장 유력한 6-B 필터 후보지만 실제 삭제는 새 build에서 diagnostic, Camera/inference와 E2E로 검증해야 한다. Parser DLL은 current binding 구조상 파일만 빼면 import가 깨질 가능성이 높다.

TensorRT headers, source, samples와 docs는 final bundle에서 확인되지 않았다. Lean/dispatch runtime DLL도 없다. 현재 2,225.183 MiB는 runtime/plugin/binding/parser와 builder resource로 설명된다.

### MediaPipe, OpenCV and XGBoost

- MediaPipe 27.484 MiB 중 `libmediapipe.dll`이 27.405 MiB다. 나머지는 Tasks metadata schema 약 0.032 MiB와 매우 작은 label files다. tests/examples는 없다. PoseLandmarker Tasks API가 사용하므로 실질적 절감 후보가 아니다.
- OpenCV 137.128 MiB는 `cv2.pyd` 107.668 MiB와 FFmpeg DLL 29.446 MiB다. Windows bundle에 Qt 파일은 없고 MSMF/HighGUI는 `cv2.pyd`에 들어 있다. `cv2.pyd`는 KEEP, FFmpeg는 Webcam-only 기능 기준 NEEDS_RUNTIME_TEST다.
- XGBoost 54.299 MiB는 사실상 `xgboost.dll` 54.279 MiB다. 현재 `XGBClassifier.load_model/predict`에 필요하다. `VERSION`, `py.typed`, metadata는 매우 작다.
- scikit-learn은 XGBoost `compat.py`와 `XGBClassifier` base/tag/check paths에서 실제 import된다. 전체 11.827 MiB에는 metrics 1.673, utils 1.586, loss 1.323, cluster 1.316, neighbors 1.001, tree 0.894, SVM 0.772, datasets 0.699 MiB 등이 포함된다. 전체 삭제가 아니라 필요한 base/wrapper 경계를 먼저 찾아야 한다.

### SciPy, NumPy, Matplotlib and Ultralytics

- SciPy 72.271 MiB에는 별도 OpenBLAS 19.322 MiB와 optimize 9.928, special 9.811, linalg 7.230, sparse 7.069 MiB 등이 포함된다. sklearn broad graph와 Ultralytics validator/tracker/plot paths가 끌어온다.
- NumPy 26.030 MiB에는 NumPy OpenBLAS 19.470 MiB가 포함된다. FitRoute feature, MediaPipe/XGBoost, Ultralytics preprocessing에 직접 필요하므로 KEEP이다. SciPy와 NumPy OpenBLAS는 파일명이 다르고 hash가 다른 별도 binary라 exact duplicate로 계산하지 않았다.
- Matplotlib 13.721 MiB 중 `mpl-data`가 9.202 MiB(204 files)이며 font가 대부분이다. Spec의 hook config는 `Agg`다. 실제 plot은 사용하지 않지만 현재 import graph에서 Ultralytics utils/checks, XGBoost plotting과 sklearn optional path가 Matplotlib을 참조한다.
- Ultralytics 자체는 3.689 MiB로 전체 영향이 작다. models 0.906, utils 0.761, nn 0.379, cfg 0.333, data 0.333, engine 0.305, assets 0.179, trackers 0.166, solutions 0.157 MiB다. training/export/tracking/data 기능이 graph에 있지만 이 package data만 줄이는 효과는 제한적이다.
- `_polars_runtime_32/_polars_runtime.pyd` 하나가 173.880 MiB다. Xref상 Ultralytics trainer/utils/benchmark/callback/plotting과 XGBoost optional compat가 유입점이며 현재 inference에는 필요할 가능성이 낮다.

## D. CUDA/NVIDIA DLL summary

아래 표는 요청된 CUDA/NVIDIA 이름 패턴에 맞는 DLL 전부다. 같은 이름은 `cudart64_12.dll` 하나만 두 위치에 있다.

| File | MiB | Relative path | Duplicate |
|---|---:|---|---|
| `cublasLt64_12.dll` | 643.413 | `_internal/torch/lib/` | No |
| `cudnn_engines_precompiled64_9.dll` | 458.732 | `_internal/torch/lib/` | No |
| `cusparse64_12.dll` | 361.954 | `_internal/torch/lib/` | No |
| `cufft64_11.dll` | 263.330 | `_internal/torch/lib/` | No |
| `cudnn_adv64_9.dll` | 256.554 | `_internal/torch/lib/` | No |
| `cusolver64_11.dll` | 215.229 | `_internal/torch/lib/` | No |
| `cusolverMg64_11.dll` | 149.795 | `_internal/torch/lib/` | No |
| `cublas64_12.dll` | 108.448 | `_internal/torch/lib/` | No |
| `cudnn_ops64_9.dll` | 100.712 | `_internal/torch/lib/` | No |
| `nvrtc64_120_0.alt.dll` | 82.773 | `_internal/torch/lib/` | No; different filename |
| `nvrtc64_120_0.dll` | 82.710 | `_internal/torch/lib/` | No |
| `nvJitLink_120_0.dll` | 74.253 | `_internal/torch/lib/` | No |
| `curand64_10.dll` | 68.623 | `_internal/torch/lib/` | No |
| `cudnn_heuristic64_9.dll` | 56.148 | `_internal/torch/lib/` | No |
| `cudnn_engines_runtime_compiled64_9.dll` | 26.473 | `_internal/torch/lib/` | No |
| `nvrtc-builtins64_128.dll` | 6.062 | `_internal/torch/lib/` | No |
| `cudnn_cnn64_9.dll` | 2.846 | `_internal/torch/lib/` | No |
| `cudnn_graph64_9.dll` | 2.378 | `_internal/torch/lib/` | No |
| `cudart64_12.dll` | 0.547 | `_internal/torch/lib/` | exact duplicate |
| `cudart64_12.dll` | 0.547 | `_internal/torchvision/` | exact duplicate |
| `cudnn64_9.dll` | 0.252 | `_internal/torch/lib/` | No |
| `cufftw64_11.dll` | 0.156 | `_internal/torch/lib/` | No |
| `nvToolsExt64_1.dll` | 0.046 | `_internal/torch/lib/` | No |

`torch_cuda.dll`의 direct imports에는 bundle의 `cublas`, `cublasLt`, `cudnn`, `cufft`, `cusolver`, `cusparse`, `torch_cpu`, `c10` 계열이 확인된다. NVRTC/JIT/profiler/secondary libraries는 direct import가 아니어도 PyTorch가 기능별로 동적 로드할 수 있으므로 파일명만 보고 제거할 수 없다.

## E. Duplicate DLL summary

동일 filename group은 5개다. 그중 exact duplicate group 2개, 같은 이름이지만 다른 binary인 group 3개다. SHA-256 기준 이론적 exact duplicate 낭비는 **786,872 bytes / 0.750 MiB**뿐이다.

| Name | Paths | SHA-256 / 판정 | Waste MiB |
|---|---|---|---:|
| `cudart64_12.dll` | `torch/lib`, `torchvision` | `c2c9a9c22a9bcba90e261825968836787b331038047a26770cffb7a583c28344`, exact | 0.547 |
| `VCOMP140.DLL` | `_internal`, `sklearn/.libs` | `95d4ce4a6802d1e18b5e0e1722cc30ea72ca7e033f83828f05c0b7b993fe7cbf`, exact | 0.203 |
| `python312.dll` | `_internal` | `3436d46bb65a87ba3d215df065f010d9fdab18c994caa275b546b8877b5205b2` | 0 |
| `python312.dll` | `torchvision` | `72c1bea78e0c49f746889a3af8c4973e044e50e319c1c976dd98059a403404da`, different binary | 0 |
| `msvcp140.dll` | `_internal` | `8f141b4454fa78db34bc1f28c571b4da0e00cd2c43f7ad0e282f313036826aae` | 0 |
| `msvcp140.dll` | `sklearn/.libs` | `7c26614e1d733892c2deac7e245ce115504b1d80592dd0a01b08e3e5a55f89ca`, different binary | 0 |
| `zlib.dll` | `torchvision` | `bb5e7e442c70bdfa2d3c45c9620835ecc5e98191bde2bc226b4d799a09ad30b3` | 0 |
| `zlib.dll` | `_internal` | `a2e123cc624634d08200b4e5ee6a2828d2df88fd9573b5b5fdd9da336f5738a6`, different binary | 0 |

가장 큰 same-name group은 두 `python312.dll`의 총 14.191 MiB지만 hash가 달라 중복 낭비로 계산하지 않는다. 가장 큰 exact group은 `cudart64_12.dll` 총 1.095 MiB다. DLL loader의 package-relative 탐색이 있으므로 exact hash라도 바로 제거하지 않는다.

Python resource 측면에서 큰 물리적 복제는 확인되지 않았다. Dist-info 전체는 약 0.48 MiB다. 다만 Torch와 TorchVision hook의 `module_collection_mode='pyz+py'` 때문에 source `.py`를 외부에 유지하면서 PYZ에도 bytecode가 들어간다. 전체 외부 `.py`는 45.697 MiB이고 Torch가 대부분이다. JIT/TorchScript 호환을 위한 hook 정책이므로 source copy 제거는 runtime test 대상이다. 명시적인 test/example 후보는 Torch testing 4.876 MiB가 가장 크고 나머지는 0.3 MiB 미만이다.

## F. Spec and PyInstaller hook impact

현재 spec은 `collect_all`과 `collect_submodules`를 직접 호출하지 않는다.

- Spec `collect_dynamic_libs("mediapipe")`: 27.405 MiB `libmediapipe.dll`; 필요한 native runtime이다.
- Spec `collect_data_files("mediapipe")`: DLL/PYD를 제외한 schema/label data 약 0.032 MiB; 영향이 작다.
- Spec `collect_dynamic_libs("xgboost")`: 54.279 MiB `xgboost.dll`; 필요하다.
- Spec `collect_data_files("xgboost")`: `VERSION`, `py.typed`; 영향이 사실상 없다.
- Spec `copy_metadata`: 네 distribution metadata 전체가 0.25 MiB보다 작다.
- Hidden import `ultralytics.nn.backends.tensorrt`: TensorRT backend가 `torch`, TensorRT binding/runtime graph를 연결한다.
- Hidden import `tensorrt_libs`: contrib `hook-tensorrt_libs.py`가 `collect_dynamic_libs("tensorrt_libs")`로 DLL 11개 전체, 특히 builder resources 1,816.925 MiB를 수집한다. 가장 큰 조정 후보다.
- `hook-torch.py`: `collect_submodules("torch")`, `collect_data_files("torch")`, `collect_dynamic_libs("torch")`, `pyz+py`를 적용한다. 4,078.972 MiB와 2,201 files의 직접 원인이다.
- `hook-torchvision.py`: `_C` hidden import와 `pyz+py`를 적용한다.
- `hook-cv2.py`: cv2 submodules와 dynamic libs를 수집하며 FFmpeg를 포함한다. Windows bundle에는 Qt가 없다.
- `hook-matplotlib.py`: `mpl-data` 전체 9.202 MiB를 수집한다. Spec은 backend를 Agg로 제한했지만 data/fonts 수집은 남는다.
- `hook-sklearn.py`와 sub-hooks: package data와 native extensions를 수집하고, XGBoost sklearn wrapper가 진입점이다.
- SciPy/NumPy hooks: respective delvewheel OpenBLAS DLL을 각각 보존한다.

Analysis TOC에는 외부 `C:\TensorRT-11.0.0.114\bin`에서 발견된 DLL 3개 기록이 있지만 spec filter 이후 final COLLECT와 dist의 `_internal` root에는 해당 복사본이 0개다. 최종 runtime은 wheel-owned `_internal/tensorrt_libs`를 사용한다.

## G. Optimization candidate summary

아래 절감량은 서로 겹치지 않도록 큰 항목을 분리한 이론값이다. 실제 삭제 승인이 아니다.

| Candidate | Class | Risk | Theoretical saving | 근거/필수 검증 |
|---|---|---|---:|---|
| TensorRT builder resources 8개 | LIKELY_REMOVABLE | Medium | 1,816.925 MiB | engine build 미사용; diagnostic + Camera + E2E 필수 |
| Polars native runtime | LIKELY_REMOVABLE | Low/Medium | 173.880 MiB | training/plot/optional compat graph; XGBoost predict 확인 |
| Torch `testing`/examples | LIKELY_REMOVABLE | Low | 약 4.95 MiB | inference import 회귀 확인 |
| Ultralytics cfg/assets/tracker/solutions 등 data | LIKELY_REMOVABLE | Low | 약 1.0~2.0 MiB | package resource lookup 확인 |
| TorchVision models/datasets data | LIKELY_REMOVABLE | Low/Medium | 약 1.36 MiB | ops/NMS는 유지 |
| Exact duplicate DLL | NEEDS_RUNTIME_TEST | Medium | 0.750 MiB | package-relative loader 때문에 hash만으로 삭제 금지 |
| Matplotlib + mpl-data | NEEDS_RUNTIME_TEST | Medium | 13.721 MiB, deps 포함 약 14.3 MiB | startup import가 존재; Agg inference 회귀 확인 |
| SciPy broad submodules/libs | NEEDS_RUNTIME_TEST | Medium | 최대 50~72.271 MiB | sklearn/Ultralytics 실제 사용 경계 필요 |
| scikit-learn broad submodules | NEEDS_RUNTIME_TEST | Medium/High | 최대 약 8~11.827 MiB | XGBClassifier base/tag path 유지 |
| OpenCV FFmpeg | NEEDS_RUNTIME_TEST | Medium | 29.446 MiB | MSMF Camera/HighGUI만 대상으로 재검증 |
| Torch compiler/distributed/ONNX Python trees | NEEDS_RUNTIME_TEST | Medium | 약 20~30 MiB | `collect_submodules` filter + import test |
| Torch/TorchVision external source copy | NEEDS_RUNTIME_TEST | High | 최대 약 45 MiB | JIT/TorchScript 및 runtime source lookup 확인 |
| TensorRT ONNX parser | DO_NOT_TOUCH_YET | High | 2.145 MiB | current Python binding direct import |
| Torch optional CUDA JIT/profiler/secondary DLL | DO_NOT_TOUCH_YET | High | 대략 0.4~0.6 GiB 후보 | dynamic loads; GPU/Camera 장시간 시험 필요 |
| Torch CUDA/cuDNN/cuBLAS/core | DO_NOT_TOUCH_YET | High | 매우 큼 | 실제 tensor allocation/pre/postprocess에서 필요 |
| TensorRT runtime/plugin/binding | KEEP | High | 0 | serialized engine inference 핵심 |
| MediaPipe/OpenCV core/XGBoost/NumPy/models | KEEP | High | 0 | 현재 기능의 직접 dependency |

### 현실적 범위

- **보수적 1차**: builder resources + Polars + 명백한 tests/data를 검증 후 제외하면 약 **1.90~1.96 GiB 절감**, 최종 **4.84~4.90 GiB**가 현실적이다.
- **중간**: 보수적 항목에 Matplotlib, FFmpeg, SciPy/sklearn broad graph, Torch Python optional tree 일부를 더하면 총 **2.10~2.35 GiB 절감**, 최종 **4.44~4.69 GiB** 범위다.
- **공격적**: CUDA JIT/profiler/secondary DLL과 Torch source/import graph를 반복적으로 분리하면 총 **2.7~3.2 GiB 절감**, 최종 **3.59~4.09 GiB** 가능성이 있다. 이는 높은 회귀 위험을 감수한 상한 추정이다.
- Torch를 완전히 없애 3 GiB보다 훨씬 작게 만드는 것은 현재 Ultralytics API와 TensorRT backend를 유지한 spec 최적화가 아니라 preprocessing, CUDA buffer, NMS와 result pipeline을 재작성하는 별도 아키텍처 작업이다.

6.79 GiB의 주된 원인 Top 5를 겹치지 않게 나누면 Torch/lib 4,035.562 MiB, TensorRT builder 1,816.925 MiB, TensorRT inference/plugin/binding/parser 약 408.249 MiB, Polars 173.880 MiB, OpenCV 137.128 MiB다.

## H. CUDA Toolkit and NVIDIA Driver boundary

Final COLLECT/dist에는 시스템 CUDA Toolkit 경로나 `C:\Program Files\NVIDIA GPU Computing Toolkit` 파일이 없다. 주요 `torch_cuda.dll`의 direct CUDA imports는 모두 `_internal/torch/lib`에 존재한다. TensorRT runtime/plugin/binding도 wheel-owned DLL을 사용한다. 이전 제한 PATH frozen diagnostic 성공 결과와 일치하므로 시스템 CUDA Toolkit 설치는 현재 bundle의 startup/inference runtime requirement로 보이지 않는다.

반면 **호환 NVIDIA GPU와 NVIDIA Driver는 계속 필요하다**. Driver가 제공하는 `nvcuda.dll`/kernel interface는 CUDA runtime이 동적으로 사용하며 installer에 포함하는 redistributable bundle 항목이 아니다. Bundle은 CUDA/TensorRT user-mode runtime을 포함하지만 GPU driver를 대체하지 않는다.

## 6-B 우선순위

1. TensorRT builder resource 8개만 명시적으로 필터링한 별도 candidate build
2. Polars graph 제외
3. Torch testing/examples와 명백한 non-runtime source/data filter
4. Matplotlib/Agg 및 SciPy broad graph를 각각 독립 실험
5. OpenCV FFmpeg와 TorchVision non-ops data를 별도 실험

각 candidate는 reference bundle을 보존하고 새 dist name으로 빌드한 뒤 `--diagnose-runtime`, 실제 Camera, TensorRT inference, MediaPipe/XGBoost, session save와 Launcher E2E를 순서대로 통과해야 한다. 이 분석만으로 어떤 파일도 직접 삭제하면 안 된다.

## Reproduction

분석 스크립트:

```powershell
python packaging/ai_client/analyze_bundle_size.py dist/FitRouteAIClient
```

스크립트는 recursive size, top directories/files, extension/package 분류, CUDA/TensorRT inventory와 same-name DLL SHA-256만 stdout JSON으로 출력한다. Bundle에는 쓰지 않는다.

## 6-B-1 TensorRT Builder Candidate

6-A reference를 덮어쓰지 않고 `FitRouteAIClient.optimized.spec`으로 별도 onedir candidate를 만들었다. 실험 변수는 TensorRT 11 wheel의 builder resource 8개뿐이다. Candidate spec은 아래 정확한 basename을 Analysis TOC에서 찾고, 집합과 개수가 일치하지 않으면 빌드를 중단한 뒤 일치할 때만 제외한다.

| Builder resource | Bytes | MiB |
|---|---:|---:|
| `nvinfer_builder_resource_ptx_11.dll` | 241,266,800 | 230.090 |
| `nvinfer_builder_resource_sm75_11.dll` | 116,080,752 | 110.703 |
| `nvinfer_builder_resource_sm80_11.dll` | 186,787,440 | 178.134 |
| `nvinfer_builder_resource_sm86_11.dll` | 176,109,168 | 167.951 |
| `nvinfer_builder_resource_sm89_11.dll` | 185,166,448 | 176.588 |
| `nvinfer_builder_resource_sm90_11.dll` | 454,019,696 | 432.987 |
| `nvinfer_builder_resource_sm100_11.dll` | 283,219,056 | 270.099 |
| `nvinfer_builder_resource_sm120_11.dll` | 262,534,256 | 250.372 |
| **합계** | **1,905,183,616** | **1,816.925** |

원본은 `fitroute_build/Lib/site-packages/tensorrt_libs/`, reference dist에서는 `_internal/tensorrt_libs/`에 있었다. PE import 검사 결과 builder resource는 TensorRT Python binding, `nvinfer_11.dll`, `nvinfer_plugin_11.dll`, `nvonnxparser_11.dll`의 direct dependency가 아니다. Binding은 parser/plugin/runtime을 직접 import하므로 이 세 DLL과 binding은 유지했다. TensorRT 내부 `LoadLibrary` 방식의 동적 사용 가능성은 정적 검사와 diagnostic만으로 배제할 수 없다.

| 항목 | Reference | Candidate | 차이 |
|---|---:|---:|---:|
| 전체 bytes | 7,295,590,444 | 5,390,406,828 | -1,905,183,616 |
| 전체 MiB | 6,957.617229 | 5,140.692547 | -1,816.924683 |
| 전체 GiB | 6.794548 | 5.020208 | -1.774341 |
| 파일 수 | 3,664 | 3,656 | -8 |
| TensorRT bytes | 2,333,273,210 | 428,089,594 | -1,905,183,616 |
| TensorRT builder bytes | 1,905,183,616 | 0 | -1,905,183,616 |
| Torch bytes | 4,277,112,178 | 4,277,112,178 | 0 |
| Models bytes | 20,508,763 | 20,508,763 | 0 |

절감률은 reference 대비 **26.114180%**다. Candidate 위치는 `dist_candidate/FitRouteAIClient/`, PyInstaller work 위치는 `build_candidate/FitRouteAIClient.optimized/`이다. 두 경로는 `.gitignore`에 포함했다.

검증 결과:

- `--help`: exit code 0, Camera 미실행
- 제한 PATH `--diagnose-runtime`: `RUNTIME DIAGNOSTIC PASS`
- Frozen CUDA: 12.8 / NVIDIA GeForce RTX 3080
- Frozen TensorRT: 11.0.0.114
- OpenCV: 5.0.0, GUI/MSMF OK
- MediaPipe: 0.10.35
- XGBoost: 9 classes / 132 features, model load OK
- Ultralytics 8.4.70, HTTPX 0.28.1
- 핵심 TensorRT binding/runtime/plugin/parser missing direct PE dependency: 0
- Candidate builder resource 검색 결과: 0개
- 모델 4개 존재 및 reference와 SHA-256 동일
- Reference EXE와 모델 4개 SHA-256은 build 전후 동일
- Reference와 candidate PyInstaller warning 파일은 SHA-256까지 동일하며 TensorRT 관련 warning은 둘 다 0개

`--diagnose-runtime`은 engine deserialize/inference를 수행하지 않으므로 최초 결과는 사용자 Camera inference 시험 준비 상태였다. 이후 사용자가 candidate Camera benchmark를 완료했다.

- Processed frames: 561
- Elapsed: 35.41 s
- End-to-end: 15.84 FPS (기존 15.89 FPS)
- Inference: 21.20 FPS
- 평균 YOLO / MediaPipe / XGBoost: 15.64 / 28.99 / 1.18 ms
- 평균 inference time: 47.18 ms

Camera, TensorRT engine inference와 전체 pose pipeline은 **PASS**이며 기존 대비 유의미한 성능 저하는 확인되지 않았다. 6-B-1.5에서는 production 기본값이나 Registry를 변경하지 않고, 로컬 Launcher dist의 ignored config만 `dist_candidate/FitRouteAIClient/FitRouteAIClient.exe`로 전환했다. Reference용 `config.reference.json`과 candidate용 `config.candidate.json`을 함께 보관하며 현재 active `config.json`은 candidate와 동일하다. Launcher/Protocol/Auth/Auto Start/Render/Supabase/Dashboard 실제 E2E는 사용자 확인 전까지 **PENDING**이다.
