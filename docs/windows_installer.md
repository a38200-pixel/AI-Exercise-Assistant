# FitRoute Windows Installer

## 상태와 목적

7-A는 검증 완료된 Windows Launcher와 Frozen AI Client를 관리자 권한 없이 설치할 수 있는 Inno Setup offline installer로 묶는 단계다. Installer는 AI Client나 Launcher를 다시 빌드하지 않으며 Python, Conda, pip, CUDA Toolkit 또는 인터넷 다운로드를 요구하지 않는다.

현재 Installer는 개발/release candidate이며 code signing되지 않는다. 실제 설치·실행·제거 검증은 7-B, clean PC 검증은 7-C에서 수행한다.

현재 개발 PC에서는 Installer 입력 검증과 Launcher/Auth 테스트가 통과했지만 Inno Setup compiler(`ISCC.exe`)가 발견되지 않아 Setup compile은 아직 수행되지 않았다. Build wrapper는 이 경우 자동 다운로드나 설치 없이 `INSTALLER SCRIPT READY / INNO SETUP COMPILER NOT FOUND`로 종료한다. Inno Setup 6 설치 후 아래 build 명령을 다시 실행해야 7-B용 Setup EXE가 생성된다.

## Source baseline

- AI Client: `dist_candidate_protoc/FitRouteAIClient/`
- AI baseline: 3,653 files, 5,203,968,114 bytes, 4,962.890734 MiB, 4.846573 GiB
- Launcher: `desktop_launcher/dist/FitRouteLauncher.exe`
- Production config: `installer/config.production.json`
- Installer version: `0.1.0`
- 고정 AppId: `{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}`

최종 baseline에는 TensorRT builder resource, Polars runtime과 `torch/bin/protoc.exe`가 없다. 실패한 `torch.testing` 제거 candidate는 사용하지 않으며 정상 baseline에는 `torch.testing`을 유지한다.

## Installer architecture

```text
FitRoute-AI-Client-Setup-0.1.0.exe
  ├─ FitRouteLauncher.exe
  ├─ config.json
  └─ ai_client/
      ├─ FitRouteAIClient.exe
      ├─ _internal/
      └─ models/
          ├─ detector/yolo26n.engine
          ├─ pose/pose_landmarker_full.task
          └─ classifier/
              ├─ model_weights.xgb
              └─ classes.json
```

기본 설치 위치는 `%LOCALAPPDATA%\Programs\FitRoute AI Client`다. `PrivilegesRequired=lowest`인 per-user 설치이므로 관리자 권한을 요구하지 않는다. Desktop shortcut과 설치 후 프로그램 실행 항목은 만들지 않는다.

## Production config와 보안

설치 시 `config.production.json`을 `{app}\config.json`으로 배치한다. AI Client 경로는 `ai_client\FitRouteAIClient.exe`, API는 `https://fitroute-api.onrender.com`이다. Supabase Desktop Auth에는 공개 가능한 project URL과 `sb_publishable_` client key만 포함한다.

다음 값은 포함하지 않는다.

- Supabase service-role/secret key
- 사용자 password
- access token 또는 refresh token
- 사용자 login session과 계정 데이터
- Repository, Conda 또는 개발 PC 절대경로
- localhost API 주소

Launcher의 기존 보안 경계는 유지된다. Protocol은 `start` command와 `squat` exercise whitelist를 통과해야 하며, access token은 AI child environment에만 전달된다. Refresh token은 Windows Generic Credential Manager의 `FitRoute AI Client/supabase_refresh_token` target에 저장되고 평문 파일이나 Registry에는 저장되지 않는다.

## URL protocol

Installer는 현재 사용자 Registry에 다음 key를 등록한다.

```text
HKCU\Software\Classes\fitroute
```

Open command는 다음 설치 파일을 인용부호로 감싸 protocol URL 하나만 전달한다.

```text
"{app}\FitRouteLauncher.exe" "%1"
```

Uninstall 시 Inno Setup의 `uninsdeletekey`로 해당 protocol tree를 제거한다. 기존 개발용 HKCU 등록이 있으면 설치 시 동일 key가 설치 경로로 업데이트된다. Registry는 Setup을 사용자가 실행할 때만 변경된다.

## Upgrade와 실행 중 프로그램

PyInstaller onedir의 stale DLL이 남지 않도록 설치 전에 `{app}\ai_client`만 `filesandordirs` 방식으로 제거한 뒤 새 tree를 설치한다. 사용자 cloud 기록이나 Credential Manager를 이 정리 대상으로 삼지 않는다.

Launcher가 AI process 종료까지 유지하는 `Local\FitRouteAIClientCamera` mutex를 Installer의 `AppMutex`로 사용한다. 실행 중이면 설치/업데이트를 시작하지 않으며 custom process kill은 사용하지 않는다. `CloseApplications=no`로 강제 종료도 하지 않는다.

Uninstall 시 지원되는 `FitRouteLauncher.exe --logout`을 먼저 실행하여 현재 사용자의 저장된 Desktop refresh credential을 삭제한다. 이후 설치 파일, AI tree, Launcher, config와 protocol Registry key가 제거된다. Supabase의 운동 기록은 삭제하지 않는다.

## System requirements

- Windows 10/11 x64
- 호환 NVIDIA GPU
- 호환 NVIDIA Driver

Python, Conda, pip, PyTorch 별도 설치, TensorRT 별도 설치와 CUDA Toolkit은 요구하지 않는다. 필요한 user-mode runtime과 확인된 MSVC runtime DLL은 Frozen bundle에 포함되어 있다. Installer는 dependency를 인터넷에서 다운로드하지 않는다.

현재 `yolo26n.engine`은 검증 환경에서 생성된 TensorRT engine이다. TensorRT engine은 GPU architecture와 runtime 환경에 따른 portability 제한이 있을 수 있으므로 모든 NVIDIA GPU에서 동작한다고 보장하지 않는다. ONNX fallback은 이번 Installer에 포함하지 않는다.

## Input validation

다음 명령은 Setup, Camera, Registry 또는 network를 실행하지 않고 입력을 검사하고 secret 없는 manifest를 갱신한다.

```powershell
python installer\validate_installer_inputs.py --write-manifest
```

검사 항목은 다음과 같다.

- 최종 baseline 경로, 전체 byte와 file count
- Launcher, AI EXE와 모델 4개 SHA-256
- 모델 4개 존재 여부
- TensorRT builder, Polars와 `protoc.exe` 0개
- production 상대 경로와 HTTPS endpoint
- publishable client key 형식 및 service-role 차단
- 개발 절대경로, localhost, token/credential 값 차단
- 실패한 testing candidate와 다른 candidate 미사용
- MSVC runtime 포함 여부
- Inno Setup protocol quoting, uninstall cleanup, mutex와 stale bundle 설정

검증 결과는 `installer/installer_manifest.json`에 기록되지만 publishable key 값 자체는 manifest에 쓰지 않는다.

## Build procedure

Inno Setup 6을 개발 PC에 별도로 설치한 후 Repository root에서 실행한다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File installer\build_installer.ps1 `
  -PythonExecutable "C:\path\to\python.exe"
```

필요하면 compiler를 명시할 수 있다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File installer\build_installer.ps1 `
  -PythonExecutable "C:\path\to\python.exe" `
  -IsccExecutable "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

Build script는 입력 검증, ISCC 탐색, compile, output 확인, byte/MiB/GiB, compression ratio와 SHA-256 출력을 수행한다. Compile 전후 Launcher, AI EXE와 모델 hash 및 AI tree count/bytes가 같은지도 확인한다. PyInstaller build나 package 설치는 수행하지 않는다.

출력 목표:

```text
installer_output/FitRoute-AI-Client-Setup-0.1.0.exe
```

`lzma2/normal`, solid compression과 disk spanning 비활성화를 사용해 single Setup EXE를 우선한다. 현재 환경에 ISCC가 없거나 Inno Setup 단일 파일 크기 제한을 넘으면 임의로 disk spanning으로 바꾸지 않고 정확한 오류를 보고한다.

## 7-B manual installation checklist

1. 실행 중인 FitRoute Launcher와 AI Client가 없는지 확인한다.
2. `installer_output/FitRoute-AI-Client-Setup-0.1.0.exe`를 사용자가 직접 실행한다.
3. `%LOCALAPPDATA%\Programs\FitRoute AI Client`와 위 installed tree를 확인한다.
4. `HKCU\Software\Classes\fitroute`의 command가 설치된 Launcher를 가리키는지 확인한다.
5. `start "" "fitroute://start?exercise=squat"`을 실행한다.
6. Desktop Auth 로그인 또는 Credential Manager refresh를 확인한다.
7. Camera, TensorRT, MediaPipe, XGBoost와 Squat count를 확인한다.
8. `E`로 session을 종료하고 Render 201, Supabase 저장과 Dashboard 증가를 확인한다.
9. Windows 설정에서 FitRoute AI Client를 제거한다.
10. 설치 tree와 `HKCU\Software\Classes\fitroute`가 제거됐는지 확인한다.
11. Supabase 운동 기록은 유지되고 Desktop refresh credential은 삭제됐는지 확인한다.

## 7-C clean-PC checklist

7-B 성공 후 Python, Conda, Repository와 CUDA Toolkit이 없는 clean Windows 10/11 x64 PC에서 검증한다. 호환 NVIDIA GPU와 Driver만 준비한다. 설치부터 protocol/Auth/Camera/inference/cloud save/uninstall까지 반복하고 시스템 Python, 개발 환경, 외부 TensorRT/CUDA Toolkit 경로를 참조하지 않는지 확인한다.

## Signing and release

현재 code-signing certificate가 없으므로 output은 unsigned candidate다. Windows SmartScreen 경고가 나타날 수 있다. 공개 Release 전에는 code signing, Setup SHA-256 게시, clean-PC 결과와 TensorRT 지원 범위를 별도로 확정한다.
