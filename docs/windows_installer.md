# FitRoute Windows Installer

최종 갱신: 2026-09-15
현재 Production Installer는 검증된 Launcher와 Frozen AI Client를 하나의 Inno Setup offline installer로 배포한다.

## Current release

| Item | Value |
|---|---|
| Version | `0.1.1` |
| Filename | `FitRoute-AI-Client-Setup-0.1.1.exe` |
| Size | 2,379,641,099 bytes / 2.216213 GiB |
| SHA-256 | `748E721160116539DA8ABADCA329C43BFAAE8A52E06AFB3FEB458554D6E2D0DD` |
| Scope | Per-user, no administrator privilege |
| Signing | Unsigned |

Installer binary는 Git이 아니라 Cloudflare R2의 versioned object로 관리한다. 공개 URL과 현재 상태는 `releases/windows/v0.1.1.json`, `releases/windows/production.json`에 기록되어 있다.

## Input baseline

- AI Client: `dist_candidate_protoc/FitRouteAIClient/`
- AI bundle: 3,653 files / 5,203,968,114 bytes / 4.846573 GiB
- Launcher: `desktop_launcher/dist/FitRouteLauncher.exe`
- Production config: `installer/config.production.json`
- AppId: `{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}`

최종 baseline에서는 TensorRT builder resource, Polars runtime과 `torch/bin/protoc.exe`를 제외했다. `torch.testing` 제거 candidate는 `import torch` 회귀로 실패했으므로 최종 bundle에는 유지한다.

## Installed layout

```text
%LOCALAPPDATA%\Programs\FitRoute AI Client\
├─ FitRouteLauncher.exe
├─ config.json
└─ ai_client\
   ├─ FitRouteAIClient.exe
   ├─ _internal\
   └─ models\
      ├─ detector\yolo26n.engine
      ├─ pose\pose_landmarker_full.task
      └─ classifier\
         ├─ model_weights.xgb
         └─ classes.json
```

`PrivilegesRequired=lowest`인 per-user 설치이며 Desktop shortcut이나 설치 직후 자동 Camera 실행을 만들지 않는다. 실행 중인 AI Client는 `Local\FitRouteAIClientCamera` mutex로 설치/업데이트와 충돌하지 않게 한다.

## Runtime and security boundary

Installer는 Python runtime, Torch/CUDA user-mode runtime, TensorRT, OpenCV, MediaPipe, XGBoost와 모델을 포함한다. 사용자 PC에는 Python, Conda, pip 또는 CUDA Toolkit을 별도로 설치하지 않는다. 호환 NVIDIA GPU와 Driver는 외부 요구사항이다.

Production config에는 다음 공개 설정만 포함한다.

- AI Client 상대경로 `ai_client\FitRouteAIClient.exe`
- Render API `https://fitroute-api.onrender.com`
- Supabase project URL과 publishable client key

Service-role key, 사용자 password/token/session, localhost와 개발 PC 절대경로는 포함하지 않는다. Refresh token은 설치 파일이 아니라 로그인 후 Windows Credential Manager에 저장된다.

## Protocol and uninstall

Installer는 현재 사용자 Registry의 `HKCU\Software\Classes\fitroute`에 protocol handler를 등록한다.

```text
"{app}\FitRouteLauncher.exe" "%1"
```

Uninstall 시 Launcher `--logout`으로 Desktop refresh credential을 제거한 후 설치 tree와 protocol key를 정리한다. Supabase의 cloud 운동 기록은 삭제하지 않는다.

## Validation and build

입력 검증은 Camera, Registry와 network를 실행하지 않는다.

```powershell
python installer\validate_installer_inputs.py --version 0.1.1 --write-manifest
```

검사 범위:

- AI bundle path, file count와 전체 bytes
- Launcher, AI EXE와 모델 SHA-256
- 제거 대상 TensorRT builder/Polars/protoc 0개
- production HTTPS endpoint와 상대 실행 경로
- secret, localhost와 개발 절대경로 차단
- Inno Setup protocol quoting, mutex, stale bundle과 uninstall 설정

Installer build:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File installer\build_installer.ps1 `
  -Version 0.1.1 `
  -PythonExecutable "C:\path\to\python.exe"
```

Build script는 validator 실행, `ISCC.exe` 탐색, compile, 산출물 확인, size/compression ratio/SHA-256 출력과 보호 대상 hash 불변 검사를 수행한다. PyInstaller rebuild나 package 설치는 수행하지 않는다.

```text
installer_output/FitRoute-AI-Client-Setup-0.1.1.exe
```

## Completed E2E validation

개발 PC와 Python/Conda/Repository가 없는 별도 Windows PC에서 다음 흐름을 완료했다.

```text
Web download → Installer → fitroute:// → Launcher → Desktop Auth
→ Frozen AI Client → Camera/TensorRT/MediaPipe/XGBoost
→ Workout 종료 → Render/Supabase 저장 → Dashboard 조회 → Uninstall
```

확인 결과:

- 설치와 per-user protocol 등록 정상
- Desktop 로그인/token 복원과 AI Client 실행 정상
- Camera 및 실시간 inference 정상
- 운동 결과 cloud 저장과 Dashboard 조회 정상
- 제거 후 설치 tree, Registry protocol과 Desktop credential 정리
- Supabase 운동 기록 유지

v0.1.1에서 최초 실행의 첫 운동 저장이 실패할 가능성이 한 차례 관찰되었으며 원인은 확정되지 않았다. 후속 분석 항목은 [루트 README Known Issue](../README.md#16-known-issue)에 기록한다.

## Known limitations

- Code-signing certificate가 없어 SmartScreen 경고가 나타날 수 있다.
- `yolo26n.engine`은 생성 GPU/TensorRT 환경에 따른 portability 제한이 있다.
- ONNX 파일은 Repository에 fallback 후보로 보존하지만 현재 Installer runtime에는 포함하지 않는다.
