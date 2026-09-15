# FitRoute Desktop Launcher

최종 갱신: 2026-09-15
상태: **독립형 Launcher/AI Client 연동, Installer 배포 및 별도 Windows PC E2E 검증 완료**

## 목적과 구조

현재 버전은 Web의 Squat 선택을 독립형 Windows AI Client 실행으로 연결한다.

```text
React /exercise
  -> fitroute://start?exercise=squat
  -> HKCU custom protocol
  -> FitRouteLauncher.exe
  -> Windows Credential Manager refresh 또는 Desktop Login
  -> access token은 child environment로만 전달
  -> FitRouteAIClient.exe --exercise squat --auto-start-session
  -> Render POST /api/workouts
```

Launcher 자체에는 AI 모델을 넣지 않는다. 별도 `FitRouteAIClient` onedir bundle이 Python runtime, native dependency와 모델을 포함하며 Launcher는 해당 EXE만 직접 실행한다.

## URL과 보안 경계

지원 URL은 다음 하나뿐이다.

```text
fitroute://start?exercise=squat
```

- command whitelist: `start`
- exercise whitelist: `squat`
- 추가 query, path, fragment와 다른 protocol은 거부한다.
- URL 값을 shell 문자열, 파일 경로 또는 Python code로 사용하지 않는다.
- `subprocess.Popen([...], shell=False)`의 고정 argument list만 사용한다.
- access token, refresh token, password는 URL이나 Launcher command line으로 전달하지 않는다.
- `sb_secret_` 또는 legacy JWT의 `service_role` key는 Desktop config에서 거부한다.

## Launcher 구성

설치 폴더의 `config.json`은 다음 구조다.

```json
{
  "ai_client_executable": "ai_client\\FitRouteAIClient.exe",
  "api_base_url": "https://fitroute-api.onrender.com",
  "supabase_url": "https://YOUR_PROJECT.supabase.co",
  "supabase_anon_key": "YOUR_PUBLISHABLE_KEY"
}
```

상대 `ai_client_executable`은 frozen 실행 시 `Path(sys.executable).resolve().parent`, source 실행 시 `launcher.py`의 디렉터리를 기준으로 해석한다. 설치 기본값은 `ai_client\FitRouteAIClient.exe`다. Repository에서 개발 검증할 때만 `desktop_launcher\dist` 기준의 `..\..\dist\FitRouteAIClient\FitRouteAIClient.exe` 또는 명시적인 EXE 경로를 사용할 수 있다. EXE가 없으면 Python fallback 없이 `FitRoute AI Client executable was not found.`로 실패한다.

## 테스트와 dry-run

Camera를 실행하지 않고 parsing과 최종 argument list를 확인할 수 있다.

```powershell
Copy-Item desktop_launcher/config.example.json desktop_launcher/config.json
# config.json의 AI Client 경로와 Supabase publishable 설정 확인
python desktop_launcher/launcher.py --config desktop_launcher/config.json --dry-run "fitroute://start?exercise=squat"
python -m pytest tests/test_desktop_auth.py -q -p no:cacheprovider
python -m pytest tests/test_desktop_launcher.py tests/test_auto_start_session.py -q -p no:cacheprovider
```

## Launcher EXE 빌드

현재 `vision_ai` 환경에서 PyInstaller onefile 빌드와 startup/import smoke test를 완료했다. 새 환경에서는 Launcher 의존성과 PyInstaller를 명시적으로 설치한 후 빌드한다.

```powershell
<python-executable> -m pip install -r desktop_launcher\requirements.txt
<python-executable> -m pip install pyinstaller
powershell -ExecutionPolicy Bypass -File .\desktop_launcher\build_launcher.ps1 `
  -PythonExecutable "<python-executable>" `
  -ApiBaseUrl "https://fitroute-api.onrender.com" `
  -SupabaseUrl "https://YOUR_PROJECT.supabase.co" `
  -SupabaseAnonKey "YOUR_PUBLISHABLE_KEY"
```

생성물:

```text
desktop_launcher/dist/FitRouteLauncher.exe
desktop_launcher/dist/config.json
```

기본 개발 build의 `config.json`은 `..\..\dist\FitRouteAIClient\FitRouteAIClient.exe` 상대 경로를 기록한다. `-AiClientExecutable`로 별도 개발 EXE 경로를 명시할 수도 있다. `-PythonExecutable`은 Launcher build 도구 선택에만 쓰이고 runtime config에는 저장되지 않는다.

`build_launcher.ps1`은 `-PythonExecutable`의 부모를 Conda 환경 root로 계산한다. 범용 AI 환경에 함께 설치된 PyQt5/PyQt6와 Launcher가 사용하지 않는 matplotlib은 제외하며, Supabase Auth hidden import와 tkinter는 유지한다. `_ctypes`, `pyexpat`, tkinter 등 Conda extension이 직접 요구하는 `Library\bin` DLL은 실제 존재하는 파일만 onefile bundle에 추가한다.

현재 빌드 및 문제 해결 기록은 [프로젝트 README의 Launcher 섹션](../README.md#8-windows-desktop-연동)을 참고한다. DLL 누락 여부는 파일명 추측이 아니라 `.pyd`의 PE dependency, PyInstaller TOC와 onefile archive 목록으로 확인한다.

## Protocol 등록과 제거

등록 스크립트는 실행만으로 자동 호출되지 않는다. 사용자가 명시적으로 실행해야 HKCU가 변경된다.

```powershell
python desktop_launcher/register_protocol.py --launcher desktop_launcher/dist/FitRouteLauncher.exe
```

등록 위치:

```text
HKEY_CURRENT_USER\Software\Classes\fitroute
  URL Protocol
  DefaultIcon
  shell\open\command
```

관리자 권한 없이 Current User에만 등록된다. 수동 등록을 제거하려면 다음을 실행한다.

```powershell
python desktop_launcher/unregister_protocol.py
```

이 스크립트는 `fitroute://` registry key만 제거하며 프로젝트나 Conda 환경은 삭제하지 않는다.

## 중복 Camera 방지

Launcher는 `Local\FitRouteAIClientCamera` Windows named mutex를 획득하고 AI process가 끝날 때까지 유지한다. 이미 mutex가 존재하면 두 번째 Camera process를 만들지 않고 종료한다.

## Desktop 인증

Desktop은 Web token을 전달받지 않고 같은 Supabase Project에 별도로 로그인한다. 현재 설치된 `supabase==2.31.0`의 `sign_in_with_password()`와 `refresh_session()`을 사용한다.

최초 실행 흐름:

1. Credential Manager에 refresh token이 없으면 tkinter Login Dialog를 표시한다.
2. 사용자는 Web에서 사용 중인 동일한 계정의 email/password를 입력한다.
3. password는 로그인 요청에만 사용하고 저장하지 않는다.
4. access token은 현재 Launcher memory에만 유지한다.
5. refresh token과 계정 email은 Windows Generic Credential `FitRoute AI Client/supabase_refresh_token`에 저장한다.

이후 실행 흐름:

1. Credential Manager에서 refresh token을 읽는다.
2. Supabase session을 refresh해 최신 access token을 얻는다.
3. token rotation이 있으면 새 refresh token으로 Credential Manager를 갱신한다.
4. refresh가 거부되면 기존 credential을 제거하고 Login Dialog를 한 번 표시한다.

Credential Manager 접근 또는 저장이 실패해도 config, `.env`, Registry에 token을 평문 저장하지 않는다. 로그인에 성공했다면 이번 Camera 실행에서만 access token을 사용하고 다음 실행에는 다시 로그인한다.

Desktop 인증정보만 제거하려면 설치된 Launcher에서 다음을 실행한다.

```powershell
& "$env:LOCALAPPDATA\Programs\FitRoute AI Client\FitRouteLauncher.exe" --logout
```

source 개발 모드에서는 다음 명령을 사용할 수 있다.

```powershell
python desktop_launcher/launcher.py --logout
```

## Child process와 Session 자동 시작

Launcher는 갱신된 access token을 command line이나 protocol URL에 넣지 않는다. `os.environ.copy()`로 만든 child 전용 environment에만 다음 값을 추가한다.

```text
FITROUTE_ACCESS_TOKEN=<현재 access token>
FITROUTE_API_BASE_URL=<config의 Render URL>
```

실행 argument list에는 민감정보 없이 다음만 포함된다.

```text
FitRouteAIClient.exe --exercise squat --auto-start-session
```

`subprocess.Popen`은 argument list와 `shell=False`를 사용하고 작업 디렉터리는 AI Client EXE의 부모다. Access Token은 argv, protocol URL, config와 log에 들어가지 않는다. Launcher 옆 `launcher.log`에는 시작, protocol 검증, auth 성공, EXE 해석/존재 여부, token/API URL 존재 여부, auto-start 여부, child PID와 exit code만 기록한다.

AI Client는 모델 초기화, Camera open과 첫 inference frame 처리가 성공한 뒤 `WorkoutSession.start()`를 호출한다. 따라서 모델 로딩 시간은 운동 시간에 포함되지 않으며 초기화가 실패하면 빈 Session도 생성되지 않는다. 기존 `python src/main.py --exercise squat` 명령은 계속 manual `S` 시작 방식이다.

## Installer 생성

현재 Installer source와 검증·빌드 도구는 루트 `installer/`에 통합되어 있다.

1. 검증된 Launcher EXE와 최종 Frozen AI Client baseline을 준비한다.
2. Installer 입력 검증을 실행한다.
3. Inno Setup Compiler로 다음 source를 빌드한다.

```text
installer/FitRouteAIClient.iss
```

예상 installer artifact:

```text
installer_output/FitRoute-AI-Client-Setup-0.1.1.exe
```

현재 Installer는 Launcher, production config, 전체 onedir AI Client와 모델을 포함한다. 개발 PC와 Python/Conda/Repository가 없는 별도 Windows PC에서 install/protocol/Auth/Camera/cloud save/uninstall 흐름을 검증했다. Code signing은 아직 적용하지 않았다. 상세 절차는 [Windows Installer](windows_installer.md)를 참고한다.

## Web fallback과 다운로드 URL

웹은 protocol 실행 후 약 1.8초 동안 blur/hidden 신호가 없으면 설치 안내 Modal을 표시한다. 브라우저는 handler 설치 여부를 정확히 제공하지 않으므로 이는 확정 탐지가 아니다. Chrome/Edge의 외부 앱 실행 확인창은 정상이며 우회하지 않는다.

Installer 공개 주소는 한 곳에서 관리한다.

```dotenv
VITE_DESKTOP_CLIENT_DOWNLOAD_URL=<공개한-installer-asset-URL>
```

Production Frontend에는 Cloudflare R2의 versioned Installer URL을 설정한다. 값이 비어 있으면 Web은 URL을 임의로 만들지 않고 `다운로드 준비 중` 상태를 표시한다.

## 현재 배포 제약

- Python, Conda와 repository source는 runtime에 필요하지 않다.
- Launcher와 최종 4.846573 GiB AI Client bundle은 Inno Setup Installer로 패키징했다.
- 호환 NVIDIA GPU/driver와 현재 TensorRT engine이 필요하다.
- Web 인증 token은 Desktop으로 전달하지 않는다. Web과 Desktop에서 같은 계정으로 각각 로그인해야 한다.
- 기존 CMD의 `FITROUTE_ACCESS_TOKEN` 환경설정 방식은 manual/debug fallback으로 계속 사용할 수 있다.

## 실제 E2E 확인

1. Web과 Desktop Login Dialog에서 동일한 FitRoute 계정을 사용한다.
2. `/exercise`에서 Squat을 선택하고 운동 시작을 누른다.
3. 브라우저의 FitRoute 외부 앱 열기를 허용한다.
4. 최초 한 번 Desktop Login을 완료한다.
5. Camera HUD가 즉시 `ACTIVE`, `00:00`, Squat Count `0`으로 시작하는지 확인한다.
6. `stand -> squat -> stand` 후 Count가 1 증가하는지 확인한다.
7. `E`를 눌러 종료한다.
8. Render log의 `POST /api/workouts` 응답이 201인지 확인한다.
9. Web Dashboard/History를 새로고침하고 실행 전 실제 값 대비 증가량을 확인한다.

테스트 자동화에서는 Registry, Webcam, 실제 Supabase login 또는 실제 DB write를 수행하지 않는다.

## 현재 제한사항과 후속 과제

- Code signing 및 Installer 서명
- TensorRT engine의 GPU/driver 호환 범위 확대와 CPU/ONNX fallback 정책
- 자동 업데이트와 client/backend version compatibility 정책
- v0.1.1 최초 실행의 첫 운동 저장 실패 가능성 재현 및 분석
