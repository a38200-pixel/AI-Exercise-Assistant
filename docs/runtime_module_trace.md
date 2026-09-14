# FitRoute runtime module trace

## Execution

- Executable: `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\FitRouteAIClient.exe`
- Arguments: `--exercise squat`
- PID: 19920
- Started: 2026-09-14T11:44:47.763081+00:00
- Elapsed: 75.609 seconds
- Poll interval: 100 ms
- Exit code: 0

## Summary

- Unique modules observed: 361
- Bundle native inventory: 331
- Loaded bundle native: 218
- Static-required native files: 11
- Not observed bundle native: 113
- `NOT_OBSERVED` means review only; it does not mean removable.

## Baseline validation

- TensorRT builder resources: 0
- Polars runtime paths: 0
- `torch/bin/protoc.exe`: 0

## Loaded module origins

- BUNDLE: 219
- WINDOWS: 134
- NVIDIA_DRIVER: 5
- EXTERNAL: 3

## Group summary

| Group | Files | MiB | Loaded | Static required | Not observed | Unknown |
|---|---:|---:|---:|---:|---:|---:|
| CUDA | 25 | 2986.367 | 25 | 6 | 0 | 0 |
| MediaPipe | 1 | 27.405 | 1 | 0 | 0 | 0 |
| OpenCV | 2 | 137.114 | 1 | 0 | 1 | 0 |
| Other | 276 | 151.092 | 167 | 2 | 109 | 0 |
| TensorRT | 4 | 408.249 | 4 | 0 | 0 | 0 |
| Torch | 12 | 1049.196 | 12 | 3 | 0 | 0 |
| TorchVision | 10 | 22.021 | 7 | 0 | 3 | 0 |
| XGBoost | 1 | 54.279 | 1 | 0 | 0 | 0 |

## Top 20 NOT_OBSERVED bundle native files

| File | MiB | Group | Direct dependency | Status |
|---|---:|---|---|---|
| `_internal/cv2/opencv_videoio_ffmpeg500_64.dll` | 29.446 | OpenCV / OpenCV native | No known direct requirement | NOT_OBSERVED |
| `_internal/PIL/_avif.cp312-win_amd64.pyd` | 7.527 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/torchvision/python312.dll` | 7.066 | TorchVision / TorchVision native | No known direct requirement | NOT_OBSERVED |
| `_internal/scipy/io/_fast_matrix_market/_fmm_core.cp312-win_amd64.pyd` | 2.714 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/sqlite3.dll` | 1.599 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/sklearn/_loss/_loss.cp312-win_amd64.pyd` | 1.264 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/scipy/signal/_max_len_seq_inner.cp312-win_amd64.pyd` | 0.960 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/matplotlib/_qhull.cp312-win_amd64.pyd` | 0.589 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/torchvision/cudart64_12.dll` | 0.547 | TorchVision / TorchVision native | No known direct requirement | NOT_OBSERVED |
| `_internal/matplotlib/backends/_backend_agg.cp312-win_amd64.pyd` | 0.467 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/contourpy/_contourpy.cp312-win_amd64.pyd` | 0.465 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/PIL/_webp.cp312-win_amd64.pyd` | 0.391 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/sklearn/neighbors/_ball_tree.cp312-win_amd64.pyd` | 0.352 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/sklearn/neighbors/_kd_tree.cp312-win_amd64.pyd` | 0.352 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/_sounddevice_data/portaudio-binaries/libportaudio64bit-asio.dll` | 0.327 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/matplotlib/_tri.cp312-win_amd64.pyd` | 0.317 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/sklearn/linear_model/_cd_fast.cp312-win_amd64.pyd` | 0.306 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/_sounddevice_data/portaudio-binaries/libportaudioarm64-asio.dll` | 0.302 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/_sounddevice_data/portaudio-binaries/libportaudioarm64.dll` | 0.280 | Other / Other native | No known direct requirement | NOT_OBSERVED |
| `_internal/_sounddevice_data/portaudio-binaries/libportaudio32bit-asio.dll` | 0.268 | Other / Other native | No known direct requirement | NOT_OBSERVED |

## STATIC_REQUIRED

These files remain required by the recorded PE dependency graph. A loaded file can be both `LOADED` and `static_required=true`.

| File | MiB | Group | Status |
|---|---:|---|---|
| `_internal/torch/lib/cublasLt64_12.dll` | 643.413 | CUDA / cuBLASLt | LOADED + STATIC_REQUIRED |
| `_internal/torch/lib/cusparse64_12.dll` | 361.954 | CUDA / cuSPARSE | LOADED + STATIC_REQUIRED |
| `_internal/torch/lib/cufft64_11.dll` | 263.330 | CUDA / cuFFT | LOADED + STATIC_REQUIRED |
| `_internal/torch/lib/torch_cpu.dll` | 253.645 | Torch / Torch core | LOADED + STATIC_REQUIRED |
| `_internal/torch/lib/cusolver64_11.dll` | 215.229 | CUDA / cuSOLVER | LOADED + STATIC_REQUIRED |
| `_internal/torch/lib/cublas64_12.dll` | 108.448 | CUDA / cuBLAS | LOADED + STATIC_REQUIRED |
| `_internal/torch/lib/c10.dll` | 1.038 | Torch / Torch core | LOADED + STATIC_REQUIRED |
| `_internal/sklearn/.libs/msvcp140.dll` | 0.614 | Other / Other native | LOADED + STATIC_REQUIRED |
| `_internal/msvcp140.dll` | 0.532 | Other / Other native | LOADED + STATIC_REQUIRED |
| `_internal/torch/lib/c10_cuda.dll` | 0.391 | Torch / Torch core | LOADED + STATIC_REQUIRED |
| `_internal/torch/lib/cudnn64_9.dll` | 0.252 | CUDA / cuDNN | LOADED + STATIC_REQUIRED |

## Loaded modules by origin

| First seen (s) | Module | Origin | Full path |
|---:|---|---|---|
| 0.125 | `ADVAPI32.dll` | WINDOWS | `C:\Windows\System32\ADVAPI32.dll` |
| 0.125 | `bcrypt.dll` | WINDOWS | `C:\Windows\SYSTEM32\bcrypt.dll` |
| 0.125 | `bcryptprimitives.dll` | WINDOWS | `C:\Windows\System32\bcryptprimitives.dll` |
| 0.125 | `FitRouteAIClient.exe` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\FitRouteAIClient.exe` |
| 0.125 | `GDI32.dll` | WINDOWS | `C:\Windows\System32\GDI32.dll` |
| 0.125 | `gdi32full.dll` | WINDOWS | `C:\Windows\System32\gdi32full.dll` |
| 0.125 | `IMM32.DLL` | WINDOWS | `C:\Windows\System32\IMM32.DLL` |
| 0.125 | `KERNEL32.DLL` | WINDOWS | `C:\Windows\System32\KERNEL32.DLL` |
| 0.125 | `KERNELBASE.dll` | WINDOWS | `C:\Windows\System32\KERNELBASE.dll` |
| 0.125 | `msvcp_win.dll` | WINDOWS | `C:\Windows\System32\msvcp_win.dll` |
| 0.125 | `msvcrt.dll` | WINDOWS | `C:\Windows\System32\msvcrt.dll` |
| 0.125 | `ntdll.dll` | WINDOWS | `C:\Windows\SYSTEM32\ntdll.dll` |
| 0.125 | `python312.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\python312.dll` |
| 0.125 | `RPCRT4.dll` | WINDOWS | `C:\Windows\System32\RPCRT4.dll` |
| 0.125 | `sechost.dll` | WINDOWS | `C:\Windows\System32\sechost.dll` |
| 0.125 | `ucrtbase.dll` | WINDOWS | `C:\Windows\System32\ucrtbase.dll` |
| 0.125 | `ucrtbase.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\ucrtbase.dll` |
| 0.125 | `USER32.dll` | WINDOWS | `C:\Windows\System32\USER32.dll` |
| 0.125 | `VCRUNTIME140.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\VCRUNTIME140.dll` |
| 0.125 | `VERSION.dll` | WINDOWS | `C:\Windows\SYSTEM32\VERSION.dll` |
| 0.125 | `win32u.dll` | WINDOWS | `C:\Windows\System32\win32u.dll` |
| 0.125 | `WS2_32.dll` | WINDOWS | `C:\Windows\System32\WS2_32.dll` |
| 0.125 | `zlib.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\zlib.dll` |
| 0.234 | `_bz2.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_bz2.pyd` |
| 0.234 | `_ctypes.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_ctypes.pyd` |
| 0.234 | `_lzma.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_lzma.pyd` |
| 0.234 | `combase.dll` | WINDOWS | `C:\Windows\System32\combase.dll` |
| 0.234 | `ffi.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\ffi.dll` |
| 0.234 | `LIBBZ2.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\LIBBZ2.dll` |
| 0.234 | `liblzma.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\liblzma.dll` |
| 0.234 | `ole32.dll` | WINDOWS | `C:\Windows\System32\ole32.dll` |
| 0.234 | `OLEAUT32.dll` | WINDOWS | `C:\Windows\System32\OLEAUT32.dll` |
| 0.234 | `python3.DLL` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\python3.DLL` |
| 0.344 | `_socket.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_socket.pyd` |
| 0.344 | `IPHLPAPI.DLL` | WINDOWS | `C:\Windows\SYSTEM32\IPHLPAPI.DLL` |
| 0.344 | `select.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\select.pyd` |
| 0.469 | `_queue.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_queue.pyd` |
| 0.469 | `_wmi.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_wmi.pyd` |
| 0.469 | `PROPSYS.dll` | WINDOWS | `C:\Windows\SYSTEM32\PROPSYS.dll` |
| 0.578 | `_hashlib.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_hashlib.pyd` |
| 0.578 | `_ssl.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_ssl.pyd` |
| 0.578 | `CRYPT32.dll` | WINDOWS | `C:\Windows\System32\CRYPT32.dll` |
| 0.578 | `ISModule_x64.dll` | EXTERNAL | `C:\Program Files (x86)\ESTsoft\RansomShield\ISModule_x64.dll` |
| 0.578 | `kernel.appcore.dll` | WINDOWS | `C:\Windows\SYSTEM32\kernel.appcore.dll` |
| 0.578 | `libcrypto-3-x64.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\libcrypto-3-x64.dll` |
| 0.578 | `libssl-3-x64.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\libssl-3-x64.dll` |
| 0.578 | `NETAPI32.dll` | WINDOWS | `C:\Windows\SYSTEM32\NETAPI32.dll` |
| 0.578 | `NETUTILS.DLL` | WINDOWS | `C:\Windows\SYSTEM32\NETUTILS.DLL` |
| 0.578 | `PSAPI.DLL` | WINDOWS | `C:\Windows\System32\PSAPI.DLL` |
| 0.578 | `SHELL32.dll` | WINDOWS | `C:\Windows\System32\SHELL32.dll` |
| 0.578 | `SHLWAPI.dll` | WINDOWS | `C:\Windows\System32\SHLWAPI.dll` |
| 0.578 | `uxtheme.dll` | WINDOWS | `C:\Windows\system32\uxtheme.dll` |
| 0.687 | `cscapi.dll` | WINDOWS | `C:\Windows\SYSTEM32\cscapi.dll` |
| 0.687 | `wkscli.dll` | WINDOWS | `C:\Windows\SYSTEM32\wkscli.dll` |
| 1.406 | `amsi.dll` | WINDOWS | `C:\Windows\SYSTEM32\amsi.dll` |
| 1.406 | `clbcatq.dll` | WINDOWS | `C:\Windows\System32\clbcatq.dll` |
| 1.406 | `fastprox.dll` | WINDOWS | `C:\Windows\system32\wbem\fastprox.dll` |
| 1.406 | `MpOav.dll` | EXTERNAL | `C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.3-0\MpOav.dll` |
| 1.406 | `profapi.dll` | WINDOWS | `C:\Windows\SYSTEM32\profapi.dll` |
| 1.406 | `USERENV.dll` | WINDOWS | `C:\Windows\SYSTEM32\USERENV.dll` |
| 1.406 | `wbemcomn.dll` | WINDOWS | `C:\Windows\SYSTEM32\wbemcomn.dll` |
| 1.406 | `wbemprox.dll` | WINDOWS | `C:\Windows\system32\wbem\wbemprox.dll` |
| 1.406 | `wbemsvc.dll` | WINDOWS | `C:\Windows\system32\wbem\wbemsvc.dll` |
| 1.609 | `_multiarray_umath.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\_core\_multiarray_umath.cp312-win_amd64.pyd` |
| 1.609 | `_umath_linalg.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\linalg\_umath_linalg.cp312-win_amd64.pyd` |
| 1.609 | `libscipy_openblas64_-63c857e738469261263c764a36be9436.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy.libs\libscipy_openblas64_-63c857e738469261263c764a36be9436.dll` |
| 1.609 | `msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy.libs\msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll` |
| 1.609 | `VCRUNTIME140_1.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\VCRUNTIME140_1.dll` |
| 1.719 | `cfgmgr32.dll` | WINDOWS | `C:\Windows\SYSTEM32\cfgmgr32.dll` |
| 1.719 | `COMCTL32.dll` | WINDOWS | `C:\Windows\WinSxS\amd64_microsoft.windows.common-controls_6595b64144ccf1df_6.0.26100.9278_none_3e0d1ba8e3303201\COMCTL32.dll` |
| 1.719 | `COMDLG32.dll` | WINDOWS | `C:\Windows\System32\COMDLG32.dll` |
| 1.719 | `cv2.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\cv2\cv2.pyd` |
| 1.719 | `d3d11.dll` | WINDOWS | `C:\Windows\SYSTEM32\d3d11.dll` |
| 1.719 | `dxgi.dll` | WINDOWS | `C:\Windows\SYSTEM32\dxgi.dll` |
| 1.719 | `MF.dll` | WINDOWS | `C:\Windows\SYSTEM32\MF.dll` |
| 1.719 | `MFCORE.DLL` | WINDOWS | `C:\Windows\SYSTEM32\MFCORE.DLL` |
| 1.719 | `MFPlat.DLL` | WINDOWS | `C:\Windows\SYSTEM32\MFPlat.DLL` |
| 1.719 | `MFReadWrite.dll` | WINDOWS | `C:\Windows\SYSTEM32\MFReadWrite.dll` |
| 1.719 | `powrprof.dll` | WINDOWS | `C:\Windows\SYSTEM32\powrprof.dll` |
| 1.719 | `RTWorkQ.DLL` | WINDOWS | `C:\Windows\SYSTEM32\RTWorkQ.DLL` |
| 1.719 | `shcore.dll` | WINDOWS | `C:\Windows\System32\shcore.dll` |
| 1.719 | `UMPDC.dll` | WINDOWS | `C:\Windows\SYSTEM32\UMPDC.dll` |
| 1.719 | `unicodedata.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\unicodedata.pyd` |
| 1.719 | `WSOCK32.dll` | WINDOWS | `C:\Windows\SYSTEM32\WSOCK32.dll` |
| 1.812 | `c10.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\c10.dll` |
| 1.812 | `c10_cuda.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\c10_cuda.dll` |
| 1.812 | `caffe2_nvrtc.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\caffe2_nvrtc.dll` |
| 1.812 | `CRYPTBASE.DLL` | WINDOWS | `C:\Windows\SYSTEM32\CRYPTBASE.DLL` |
| 1.812 | `cublas64_12.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cublas64_12.dll` |
| 1.812 | `cublasLt64_12.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cublasLt64_12.dll` |
| 1.812 | `cudart64_12.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudart64_12.dll` |
| 1.812 | `dbghelp.dll` | WINDOWS | `C:\Windows\SYSTEM32\dbghelp.dll` |
| 1.812 | `msvcp140.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\msvcp140.dll` |
| 1.812 | `nvrtc64_120_0.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\nvrtc64_120_0.dll` |
| 1.922 | `cudnn64_9.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudnn64_9.dll` |
| 1.922 | `cudnn_adv64_9.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudnn_adv64_9.dll` |
| 1.922 | `cudnn_cnn64_9.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudnn_cnn64_9.dll` |
| 1.922 | `cudnn_engines_precompiled64_9.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudnn_engines_precompiled64_9.dll` |
| 1.922 | `cudnn_engines_runtime_compiled64_9.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudnn_engines_runtime_compiled64_9.dll` |
| 1.922 | `cudnn_graph64_9.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudnn_graph64_9.dll` |
| 1.922 | `cudnn_heuristic64_9.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudnn_heuristic64_9.dll` |
| 1.922 | `cudnn_ops64_9.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cudnn_ops64_9.dll` |
| 1.922 | `cufft64_11.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cufft64_11.dll` |
| 1.922 | `cufftw64_11.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cufftw64_11.dll` |
| 1.922 | `cupti64_2025.1.1.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cupti64_2025.1.1.dll` |
| 1.922 | `curand64_10.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\curand64_10.dll` |
| 1.922 | `cusolver64_11.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cusolver64_11.dll` |
| 1.922 | `cusparse64_12.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cusparse64_12.dll` |
| 1.922 | `nvcuda.dll` | NVIDIA_DRIVER | `C:\Windows\SYSTEM32\nvcuda.dll` |
| 1.922 | `nvJitLink_120_0.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\nvJitLink_120_0.dll` |
| 2.047 | `cusolverMg64_11.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\cusolverMg64_11.dll` |
| 2.047 | `dxcore.dll` | WINDOWS | `C:\Windows\SYSTEM32\dxcore.dll` |
| 2.047 | `imagehlp.dll` | WINDOWS | `C:\Windows\System32\imagehlp.dll` |
| 2.047 | `libiomp5md.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\libiomp5md.dll` |
| 2.047 | `libiompstubs5md.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\libiompstubs5md.dll` |
| 2.047 | `MSASN1.dll` | WINDOWS | `C:\Windows\SYSTEM32\MSASN1.dll` |
| 2.047 | `nvperf_host.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\nvperf_host.dll` |
| 2.047 | `nvrtc-builtins64_128.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\nvrtc-builtins64_128.dll` |
| 2.047 | `nvrtc64_120_0.alt.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\nvrtc64_120_0.alt.dll` |
| 2.047 | `nvToolsExt64_1.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\nvToolsExt64_1.dll` |
| 2.047 | `SETUPAPI.dll` | WINDOWS | `C:\Windows\System32\SETUPAPI.dll` |
| 2.047 | `shm.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\shm.dll` |
| 2.047 | `torch_cpu.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\torch_cpu.dll` |
| 2.047 | `torch_cuda.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\torch_cuda.dll` |
| 2.047 | `uv.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\uv.dll` |
| 2.047 | `windows.storage.dll` | WINDOWS | `C:\Windows\system32\windows.storage.dll` |
| 2.047 | `WINTRUST.dll` | WINDOWS | `C:\Windows\System32\WINTRUST.dll` |
| 2.359 | `torch.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\torch.dll` |
| 2.469 | `_C.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\_C.cp312-win_amd64.pyd` |
| 2.469 | `torch_global_deps.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\torch_global_deps.dll` |
| 2.469 | `torch_python.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\torch_python.dll` |
| 2.469 | `zlibwapi.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torch\lib\zlibwapi.dll` |
| 2.562 | `_asyncio.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_asyncio.pyd` |
| 2.562 | `_overlapped.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_overlapped.pyd` |
| 2.562 | `mswsock.dll` | WINDOWS | `C:\Windows\system32\mswsock.dll` |
| 2.781 | `_uuid.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_uuid.pyd` |
| 2.890 | `_multiprocessing.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_multiprocessing.pyd` |
| 4.234 | `_imaging.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\PIL\_imaging.cp312-win_amd64.pyd` |
| 4.234 | `_yaml.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\yaml\_yaml.cp312-win_amd64.pyd` |
| 4.234 | `DNSAPI.dll` | WINDOWS | `C:\Windows\SYSTEM32\DNSAPI.dll` |
| 4.234 | `DSPARSE.dll` | WINDOWS | `C:\Windows\SYSTEM32\DSPARSE.dll` |
| 4.234 | `fwpuclnt.dll` | WINDOWS | `C:\Windows\System32\fwpuclnt.dll` |
| 4.234 | `NSI.dll` | WINDOWS | `C:\Windows\System32\NSI.dll` |
| 4.234 | `rasadhlp.dll` | WINDOWS | `C:\Windows\System32\rasadhlp.dll` |
| 4.344 | `_c_internal_utils.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\matplotlib\_c_internal_utils.cp312-win_amd64.pyd` |
| 4.344 | `_decimal.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_decimal.pyd` |
| 4.344 | `_imagingft.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\PIL\_imagingft.cp312-win_amd64.pyd` |
| 4.344 | `libfribidi-0.DLL` | EXTERNAL | `C:\msys64\mingw64\bin\libfribidi-0.DLL` |
| 4.453 | `_path.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\matplotlib\_path.cp312-win_amd64.pyd` |
| 4.562 | `_cext.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\kiwisolver\_cext.cp312-win_amd64.pyd` |
| 4.562 | `_image.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\matplotlib\_image.cp312-win_amd64.pyd` |
| 4.562 | `ft2font.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\matplotlib\ft2font.cp312-win_amd64.pyd` |
| 4.562 | `libexpat.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\libexpat.dll` |
| 4.562 | `pyexpat.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\pyexpat.pyd` |
| 5.703 | `_C.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torchvision\_C.pyd` |
| 5.922 | `image.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torchvision\image.pyd` |
| 5.922 | `jpeg8.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torchvision\jpeg8.dll` |
| 5.922 | `libpng16.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torchvision\libpng16.dll` |
| 5.922 | `libsharpyuv.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torchvision\libsharpyuv.dll` |
| 5.922 | `libwebp.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torchvision\libwebp.dll` |
| 5.922 | `nvjpeg64_12.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\torchvision\nvjpeg64_12.dll` |
| 6.031 | `_elementtree.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_elementtree.pyd` |
| 6.656 | `_bounded_integers.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\_bounded_integers.cp312-win_amd64.pyd` |
| 6.656 | `_pocketfft_umath.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\fft\_pocketfft_umath.cp312-win_amd64.pyd` |
| 6.765 | `_common.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\_common.cp312-win_amd64.pyd` |
| 6.765 | `_generator.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\_generator.cp312-win_amd64.pyd` |
| 6.765 | `_mt19937.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\_mt19937.cp312-win_amd64.pyd` |
| 6.765 | `_pcg64.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\_pcg64.cp312-win_amd64.pyd` |
| 6.765 | `_philox.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\_philox.cp312-win_amd64.pyd` |
| 6.765 | `_sfc64.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\_sfc64.cp312-win_amd64.pyd` |
| 6.765 | `bit_generator.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\bit_generator.cp312-win_amd64.pyd` |
| 6.765 | `mtrand.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\numpy\random\mtrand.cp312-win_amd64.pyd` |
| 7.922 | `_ccallback_c.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\_lib\_ccallback_c.cp312-win_amd64.pyd` |
| 7.922 | `_cyutility.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\_cyutility.cp312-win_amd64.pyd` |
| 8.031 | `_csparsetools.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\_csparsetools.cp312-win_amd64.pyd` |
| 8.031 | `_sparsetools.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\_sparsetools.cp312-win_amd64.pyd` |
| 8.031 | `cd.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\charset_normalizer\cd.cp312-win_amd64.pyd` |
| 8.031 | `md.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\charset_normalizer\md.cp312-win_amd64.pyd` |
| 8.140 | `_check_build.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\__check_build\_check_build.cp312-win_amd64.pyd` |
| 8.140 | `_psutil_windows.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\psutil\_psutil_windows.pyd` |
| 8.140 | `msvcp140.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\.libs\msvcp140.dll` |
| 8.140 | `pdh.dll` | WINDOWS | `C:\Windows\SYSTEM32\pdh.dll` |
| 8.140 | `SspiCli.dll` | WINDOWS | `C:\Windows\SYSTEM32\SspiCli.dll` |
| 8.140 | `vcomp140.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\.libs\vcomp140.dll` |
| 8.140 | `wtsapi32.dll` | WINDOWS | `C:\Windows\SYSTEM32\wtsapi32.dll` |
| 8.250 | `_comb.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\special\_comb.cp312-win_amd64.pyd` |
| 8.250 | `_ellip_harm_2.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\special\_ellip_harm_2.cp312-win_amd64.pyd` |
| 8.250 | `_gufuncs.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\special\_gufuncs.cp312-win_amd64.pyd` |
| 8.250 | `_specfun.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\special\_specfun.cp312-win_amd64.pyd` |
| 8.250 | `_special_ufuncs.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\special\_special_ufuncs.cp312-win_amd64.pyd` |
| 8.250 | `_ufuncs.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\special\_ufuncs.cp312-win_amd64.pyd` |
| 8.250 | `_ufuncs_cxx.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\special\_ufuncs_cxx.cp312-win_amd64.pyd` |
| 8.250 | `libscipy_openblas-64eda39e79589aedb16f58e5547eb599.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy.libs\libscipy_openblas-64eda39e79589aedb16f58e5547eb599.dll` |
| 8.359 | `_batched_linalg.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_batched_linalg.cp312-win_amd64.pyd` |
| 8.359 | `_cythonized_array_utils.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_cythonized_array_utils.cp312-win_amd64.pyd` |
| 8.359 | `_decomp_lu_cython.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_decomp_lu_cython.cp312-win_amd64.pyd` |
| 8.359 | `_decomp_update.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_decomp_update.cp312-win_amd64.pyd` |
| 8.359 | `_fblas.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_fblas.cp312-win_amd64.pyd` |
| 8.359 | `_flapack.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_flapack.cp312-win_amd64.pyd` |
| 8.359 | `_linalg_pythran.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_linalg_pythran.cp312-win_amd64.pyd` |
| 8.359 | `_matfuncs_expm.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_matfuncs_expm.cp312-win_amd64.pyd` |
| 8.359 | `_matfuncs_schur_sqrtm.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_matfuncs_schur_sqrtm.cp312-win_amd64.pyd` |
| 8.359 | `_solve_toeplitz.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_solve_toeplitz.cp312-win_amd64.pyd` |
| 8.359 | `cython_blas.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\cython_blas.cp312-win_amd64.pyd` |
| 8.359 | `cython_lapack.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\cython_lapack.cp312-win_amd64.pyd` |
| 8.469 | `_arpacklib.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\linalg\_eigen\arpack\_arpacklib.cp312-win_amd64.pyd` |
| 8.469 | `_ckdtree.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\spatial\_ckdtree.cp312-win_amd64.pyd` |
| 8.469 | `_distance_pybind.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\spatial\_distance_pybind.cp312-win_amd64.pyd` |
| 8.469 | `_distance_wrap.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\spatial\_distance_wrap.cp312-win_amd64.pyd` |
| 8.469 | `_hausdorff.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\spatial\_hausdorff.cp312-win_amd64.pyd` |
| 8.469 | `_propack.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\linalg\_propack.cp312-win_amd64.pyd` |
| 8.469 | `_qhull.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\spatial\_qhull.cp312-win_amd64.pyd` |
| 8.469 | `_rotation_cy.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\spatial\transform\_rotation_cy.cp312-win_amd64.pyd` |
| 8.469 | `_superlu.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\linalg\_dsolve\_superlu.cp312-win_amd64.pyd` |
| 8.469 | `_voronoi.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\spatial\_voronoi.cp312-win_amd64.pyd` |
| 8.469 | `messagestream.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\_lib\messagestream.cp312-win_amd64.pyd` |
| 8.578 | `_core.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_highspy\_core.cp312-win_amd64.pyd` |
| 8.578 | `_decomp_interpolative.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\linalg\_decomp_interpolative.cp312-win_amd64.pyd` |
| 8.578 | `_group_columns.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_group_columns.cp312-win_amd64.pyd` |
| 8.578 | `_highs_options.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_highspy\_highs_options.cp312-win_amd64.pyd` |
| 8.578 | `_lbfgsb.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_lbfgsb.cp312-win_amd64.pyd` |
| 8.578 | `_minpack.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_minpack.cp312-win_amd64.pyd` |
| 8.578 | `_moduleTNC.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_moduleTNC.cp312-win_amd64.pyd` |
| 8.578 | `_rigid_transform_cy.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\spatial\transform\_rigid_transform_cy.cp312-win_amd64.pyd` |
| 8.578 | `_slsqplib.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_slsqplib.cp312-win_amd64.pyd` |
| 8.578 | `_trlib.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_trlib\_trlib.cp312-win_amd64.pyd` |
| 8.578 | `_uarray.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\_lib\_uarray\_uarray.cp312-win_amd64.pyd` |
| 8.578 | `_zeros.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_zeros.cp312-win_amd64.pyd` |
| 8.578 | `givens_elimination.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_lsq\givens_elimination.cp312-win_amd64.pyd` |
| 8.687 | `_bglu_dense.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_bglu_dense.cp312-win_amd64.pyd` |
| 8.687 | `_dfitpack.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\interpolate\_dfitpack.cp312-win_amd64.pyd` |
| 8.687 | `_dierckx.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\interpolate\_dierckx.cp312-win_amd64.pyd` |
| 8.687 | `_direct.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_direct.cp312-win_amd64.pyd` |
| 8.687 | `_dop.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\integrate\_dop.cp312-win_amd64.pyd` |
| 8.687 | `_fitpack.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\interpolate\_fitpack.cp312-win_amd64.pyd` |
| 8.687 | `_lsap.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_lsap.cp312-win_amd64.pyd` |
| 8.687 | `_odepack.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\integrate\_odepack.cp312-win_amd64.pyd` |
| 8.687 | `_pava_pybind.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\optimize\_pava_pybind.cp312-win_amd64.pyd` |
| 8.687 | `_quadpack.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\integrate\_quadpack.cp312-win_amd64.pyd` |
| 8.687 | `_vode.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\integrate\_vode.cp312-win_amd64.pyd` |
| 8.687 | `pypocketfft.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\fft\_pocketfft\pypocketfft.cp312-win_amd64.pyd` |
| 8.812 | `_interpnd.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\interpolate\_interpnd.cp312-win_amd64.pyd` |
| 8.812 | `_ppoly.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\interpolate\_ppoly.cp312-win_amd64.pyd` |
| 8.812 | `_rbfinterp_pythran.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\interpolate\_rbfinterp_pythran.cp312-win_amd64.pyd` |
| 8.812 | `_rgi_cython.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\interpolate\_rgi_cython.cp312-win_amd64.pyd` |
| 8.812 | `_stats.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_stats.cp312-win_amd64.pyd` |
| 8.812 | `cython_special.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\special\cython_special.cp312-win_amd64.pyd` |
| 8.922 | `_biasedurn.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_biasedurn.cp312-win_amd64.pyd` |
| 8.922 | `_stats_pythran.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_stats_pythran.cp312-win_amd64.pyd` |
| 8.922 | `levyst.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_levy_stable\levyst.cp312-win_amd64.pyd` |
| 9.031 | `_ansari_swilk_statistics.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_ansari_swilk_statistics.cp312-win_amd64.pyd` |
| 9.140 | `_flow.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\csgraph\_flow.cp312-win_amd64.pyd` |
| 9.140 | `_matching.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\csgraph\_matching.cp312-win_amd64.pyd` |
| 9.140 | `_min_spanning_tree.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\csgraph\_min_spanning_tree.cp312-win_amd64.pyd` |
| 9.140 | `_nd_image.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\ndimage\_nd_image.cp312-win_amd64.pyd` |
| 9.140 | `_ni_label.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\ndimage\_ni_label.cp312-win_amd64.pyd` |
| 9.140 | `_qmc_cy.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_qmc_cy.cp312-win_amd64.pyd` |
| 9.140 | `_qmvnt_cy.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_qmvnt_cy.cp312-win_amd64.pyd` |
| 9.140 | `_rank_filter_1d.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\ndimage\_rank_filter_1d.cp312-win_amd64.pyd` |
| 9.140 | `_reordering.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\csgraph\_reordering.cp312-win_amd64.pyd` |
| 9.140 | `_shortest_path.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\csgraph\_shortest_path.cp312-win_amd64.pyd` |
| 9.140 | `_sobol.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_sobol.cp312-win_amd64.pyd` |
| 9.140 | `_tools.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\csgraph\_tools.cp312-win_amd64.pyd` |
| 9.140 | `_traversal.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\sparse\csgraph\_traversal.cp312-win_amd64.pyd` |
| 9.140 | `rcont.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\scipy\stats\_rcont\rcont.cp312-win_amd64.pyd` |
| 9.250 | `_argkmin.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_pairwise_distances_reduction\_argkmin.cp312-win_amd64.pyd` |
| 9.250 | `_base.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_pairwise_distances_reduction\_base.cp312-win_amd64.pyd` |
| 9.250 | `_cython_blas.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\_cython_blas.cp312-win_amd64.pyd` |
| 9.250 | `_cyutility.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\_cyutility.cp312-win_amd64.pyd` |
| 9.250 | `_datasets_pair.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_pairwise_distances_reduction\_datasets_pair.cp312-win_amd64.pyd` |
| 9.250 | `_dist_metrics.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_dist_metrics.cp312-win_amd64.pyd` |
| 9.250 | `_expected_mutual_info_fast.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\cluster\_expected_mutual_info_fast.cp312-win_amd64.pyd` |
| 9.250 | `_heap.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\_heap.cp312-win_amd64.pyd` |
| 9.250 | `_isfinite.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\_isfinite.cp312-win_amd64.pyd` |
| 9.250 | `_middle_term_computer.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_pairwise_distances_reduction\_middle_term_computer.cp312-win_amd64.pyd` |
| 9.250 | `_openmp_helpers.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\_openmp_helpers.cp312-win_amd64.pyd` |
| 9.250 | `_sorting.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\_sorting.cp312-win_amd64.pyd` |
| 9.250 | `murmurhash.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\murmurhash.cp312-win_amd64.pyd` |
| 9.250 | `sparsefuncs_fast.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\sparsefuncs_fast.cp312-win_amd64.pyd` |
| 9.375 | `_argkmin_classmode.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_pairwise_distances_reduction\_argkmin_classmode.cp312-win_amd64.pyd` |
| 9.375 | `_pairwise_fast.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_pairwise_fast.cp312-win_amd64.pyd` |
| 9.375 | `_radius_neighbors.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_pairwise_distances_reduction\_radius_neighbors.cp312-win_amd64.pyd` |
| 9.375 | `_radius_neighbors_classmode.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\metrics\_pairwise_distances_reduction\_radius_neighbors_classmode.cp312-win_amd64.pyd` |
| 9.375 | `_vector_sentinel.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\_vector_sentinel.cp312-win_amd64.pyd` |
| 9.500 | `_csr_polynomial_expansion.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\preprocessing\_csr_polynomial_expansion.cp312-win_amd64.pyd` |
| 9.500 | `_random.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\utils\_random.cp312-win_amd64.pyd` |
| 9.500 | `_target_encoder_fast.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\sklearn\preprocessing\_target_encoder_fast.cp312-win_amd64.pyd` |
| 9.500 | `xgboost.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\xgboost\lib\xgboost.dll` |
| 9.609 | `cryptnet.dll` | WINDOWS | `C:\Windows\SYSTEM32\cryptnet.dll` |
| 9.609 | `devobj.dll` | WINDOWS | `C:\Windows\SYSTEM32\devobj.dll` |
| 9.609 | `drvstore.dll` | WINDOWS | `C:\Windows\SYSTEM32\drvstore.dll` |
| 9.609 | `nvapi64.dll` | NVIDIA_DRIVER | `C:\Windows\SYSTEM32\nvapi64.dll` |
| 9.609 | `nvcuda64.dll` | WINDOWS | `C:\Windows\system32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\nvcuda64.dll` |
| 9.609 | `nvcudart_hybrid64.dll` | WINDOWS | `C:\Windows\System32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\nvcudart_hybrid64.dll` |
| 9.609 | `nvdxgdmal64.dll` | WINDOWS | `C:\Windows\System32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\nvdxgdmal64.dll` |
| 9.609 | `wldp.dll` | WINDOWS | `C:\Windows\SYSTEM32\wldp.dll` |
| 9.719 | `_cffi_backend.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_cffi_backend.cp312-win_amd64.pyd` |
| 9.719 | `AVRT.dll` | WINDOWS | `C:\Windows\SYSTEM32\AVRT.dll` |
| 9.719 | `libportaudio64bit.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\_sounddevice_data\portaudio-binaries\libportaudio64bit.dll` |
| 9.719 | `MMDevAPI.DLL` | WINDOWS | `C:\Windows\SYSTEM32\MMDevAPI.DLL` |
| 9.719 | `wdmaud.drv` | WINDOWS | `C:\Windows\SYSTEM32\wdmaud.drv` |
| 9.719 | `wdmaud2.drv` | WINDOWS | `C:\Windows\SYSTEM32\wdmaud2.drv` |
| 9.719 | `WINMM.dll` | WINDOWS | `C:\Windows\SYSTEM32\WINMM.dll` |
| 9.719 | `winmmbase.dll` | WINDOWS | `C:\Windows\SYSTEM32\winmmbase.dll` |
| 9.828 | `AUDIOSES.DLL` | WINDOWS | `C:\Windows\SYSTEM32\AUDIOSES.DLL` |
| 9.828 | `dsound.dll` | WINDOWS | `C:\Windows\SYSTEM32\dsound.dll` |
| 9.828 | `ksuser.dll` | WINDOWS | `C:\Windows\SYSTEM32\ksuser.dll` |
| 9.828 | `midimap.dll` | WINDOWS | `C:\Windows\SYSTEM32\midimap.dll` |
| 9.828 | `MSACM32.dll` | WINDOWS | `C:\Windows\SYSTEM32\MSACM32.dll` |
| 9.828 | `msacm32.drv` | WINDOWS | `C:\Windows\SYSTEM32\msacm32.drv` |
| 9.828 | `msdmo.dll` | WINDOWS | `C:\Windows\SYSTEM32\msdmo.dll` |
| 9.828 | `ResampleDmo.DLL` | WINDOWS | `C:\Windows\SYSTEM32\ResampleDmo.DLL` |
| 9.828 | `resourcepolicyclient.dll` | WINDOWS | `C:\Windows\SYSTEM32\resourcepolicyclient.dll` |
| 9.937 | `iertutil.dll` | WINDOWS | `C:\Windows\SYSTEM32\iertutil.dll` |
| 9.937 | `libmediapipe.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\mediapipe\tasks\c\libmediapipe.dll` |
| 9.937 | `ondemandconnroutehelper.dll` | WINDOWS | `C:\Windows\SYSTEM32\ondemandconnroutehelper.dll` |
| 9.937 | `srvcli.dll` | WINDOWS | `C:\Windows\SYSTEM32\srvcli.dll` |
| 9.937 | `WINHTTP.dll` | WINDOWS | `C:\Windows\SYSTEM32\WINHTTP.dll` |
| 9.937 | `WININET.dll` | WINDOWS | `C:\Windows\SYSTEM32\WININET.dll` |
| 9.937 | `WINNSI.DLL` | WINDOWS | `C:\Windows\SYSTEM32\WINNSI.DLL` |
| 10.140 | `CRYPTSP.dll` | WINDOWS | `C:\Windows\System32\CRYPTSP.dll` |
| 10.140 | `directxdatabasehelper.dll` | WINDOWS | `C:\Windows\SYSTEM32\directxdatabasehelper.dll` |
| 10.140 | `nvgpucomp64.dll` | NVIDIA_DRIVER | `C:\Windows\System32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\nvgpucomp64.dll` |
| 10.140 | `nvldumdx.dll` | NVIDIA_DRIVER | `C:\Windows\System32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\nvldumdx.dll` |
| 10.140 | `rsaenh.dll` | WINDOWS | `C:\Windows\system32\rsaenh.dll` |
| 10.250 | `NvMemMapStoragex.dll` | WINDOWS | `C:\Windows\System32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\NvMemMapStoragex.dll` |
| 10.250 | `nvwgf2umx.dll` | NVIDIA_DRIVER | `C:\Windows\System32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\nvwgf2umx.dll` |
| 10.359 | `FrameServerClient.dll` | WINDOWS | `C:\Windows\System32\FrameServerClient.dll` |
| 10.359 | `MFSENSORGROUP.dll` | WINDOWS | `C:\Windows\System32\MFSENSORGROUP.dll` |
| 10.359 | `nvppex.dll` | WINDOWS | `C:\Windows\System32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\nvppex.dll` |
| 10.359 | `policymanager.dll` | WINDOWS | `C:\Windows\SYSTEM32\policymanager.dll` |
| 10.484 | `AppXDeploymentClient.dll` | WINDOWS | `C:\Windows\System32\AppXDeploymentClient.dll` |
| 10.484 | `CompPkgSup.DLL` | WINDOWS | `C:\Windows\SYSTEM32\CompPkgSup.DLL` |
| 10.484 | `Windows.ApplicationModel.dll` | WINDOWS | `C:\Windows\System32\Windows.ApplicationModel.dll` |
| 10.484 | `Windows.Media.dll` | WINDOWS | `C:\Windows\System32\Windows.Media.dll` |
| 10.484 | `Windows.Media.MediaControl.dll` | WINDOWS | `C:\Windows\System32\Windows.Media.MediaControl.dll` |
| 10.484 | `windows.staterepositoryclient.dll` | WINDOWS | `C:\Windows\SYSTEM32\windows.staterepositoryclient.dll` |
| 10.484 | `windows.staterepositorycore.dll` | WINDOWS | `C:\Windows\SYSTEM32\windows.staterepositorycore.dll` |
| 10.484 | `Windows.StateRepositoryPS.dll` | WINDOWS | `C:\Windows\System32\Windows.StateRepositoryPS.dll` |
| 10.484 | `wintypes.dll` | WINDOWS | `C:\Windows\SYSTEM32\wintypes.dll` |
| 10.578 | `nvDecMFTMjpegx.dll` | WINDOWS | `C:\Windows\System32\DriverStore\FileRepository\nvhdc.inf_amd64_b1ac92a5da30b00b\nvDecMFTMjpegx.dll` |
| 10.687 | `mfmjpegdec.dll` | WINDOWS | `C:\Windows\System32\mfmjpegdec.dll` |
| 11.453 | `msvproc.dll` | WINDOWS | `C:\Windows\System32\msvproc.dll` |
| 11.984 | `nvinfer_11.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\tensorrt_libs\nvinfer_11.dll` |
| 12.109 | `nvinfer_plugin_11.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\tensorrt_libs\nvinfer_plugin_11.dll` |
| 12.109 | `nvonnxparser_11.dll` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\tensorrt_libs\nvonnxparser_11.dll` |
| 12.109 | `tensorrt.cp312-win_amd64.pyd` | BUNDLE | `C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant\dist_candidate_protoc\FitRouteAIClient\_internal\tensorrt_bindings\tensorrt.cp312-win_amd64.pyd` |
| 12.640 | `CoreMessaging.dll` | WINDOWS | `C:\Windows\SYSTEM32\CoreMessaging.dll` |
| 12.640 | `CoreUIComponents.dll` | WINDOWS | `C:\Windows\SYSTEM32\CoreUIComponents.dll` |
| 12.640 | `GLU32.dll` | WINDOWS | `C:\Windows\SYSTEM32\GLU32.dll` |
| 12.640 | `IMGSF50Filter_x64.dll` | WINDOWS | `C:\Windows\system32\IMGSF50Filter_x64.dll` |
| 12.640 | `MSCTF.dll` | WINDOWS | `C:\Windows\System32\MSCTF.dll` |
| 12.640 | `Opengl32.dll` | WINDOWS | `C:\Windows\SYSTEM32\Opengl32.dll` |
| 12.640 | `textinputframework.dll` | WINDOWS | `C:\Windows\SYSTEM32\textinputframework.dll` |
| 69.937 | `DPAPI.DLL` | WINDOWS | `C:\Windows\System32\DPAPI.DLL` |
| 69.937 | `urlmon.dll` | WINDOWS | `C:\Windows\SYSTEM32\urlmon.dll` |
| 70.047 | `ncrypt.dll` | WINDOWS | `C:\Windows\SYSTEM32\ncrypt.dll` |
| 70.047 | `ncryptsslp.dll` | WINDOWS | `C:\Windows\system32\ncryptsslp.dll` |
| 70.047 | `NTASN1.dll` | WINDOWS | `C:\Windows\SYSTEM32\NTASN1.dll` |
| 70.047 | `schannel.DLL` | WINDOWS | `C:\Windows\system32\schannel.DLL` |
| 71.234 | `icu.dll` | WINDOWS | `C:\Windows\system32\icu.dll` |

## Interpretation

- LOADED: observed at least once during this run.
- STATIC_REQUIRED: not observed, but a direct PE dependency of `torch_cuda.dll`; do not remove.
- NOT_OBSERVED: not observed and not statically required by the imported Torch inventory; review only.
- UNKNOWN/EXTERNAL paths must be investigated before any packaging change.
- No file was removed or modified by this trace.
