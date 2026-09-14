# FitRoute Desktop Launcher (개발용)

## 목적과 구조

현재 버전은 Web의 Squat 선택을 기존 Windows/Python AI Client 실행으로 연결하는 개발 PC용 진입점이다.

```text
React /exercise
  -> fitroute://start?exercise=squat
  -> HKCU custom protocol
  -> FitRouteLauncher.exe
  -> config.json의 기존 vision_ai Python + 프로젝트
  -> src/main.py --exercise squat
```

Launcher는 AI 모델이나 Python runtime을 포함하지 않는다. 기존 Conda 환경, 모델 파일, 프로젝트 source가 설치된 현재 개발 PC를 대상으로 한다.

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

## Launcher 구성

설치 폴더의 `config.json`은 다음 구조다.

```json
{
  "python_executable": "C:\\path\\to\\vision_ai\\python.exe",
  "project_root": "C:\\path\\to\\AI-Exercise-Assistant",
  "entry_script": "src/main.py"
}
```

`entry_script`는 반드시 `project_root` 내부의 상대 경로여야 한다. 개발용 예시는 `desktop_launcher/config.example.json`에 있다.

## 테스트와 dry-run

Camera를 실행하지 않고 parsing과 최종 argument list를 확인할 수 있다.

```powershell
Copy-Item desktop_launcher/config.example.json desktop_launcher/config.json
# config.json의 두 경로를 현재 PC에 맞게 수정
python desktop_launcher/launcher.py --config desktop_launcher/config.json --dry-run "fitroute://start?exercise=squat"
python -m pytest tests/test_desktop_launcher.py -q -p no:cacheprovider
```

## Launcher EXE 빌드

현재 PC 검사 결과 PyInstaller는 설치되어 있지 않다. Codex는 이를 자동 설치하지 않았다. 사용자가 선택한 환경에 PyInstaller를 설치한 후 실행한다.

```powershell
C:\Users\AISW_203_113\anaconda3\envs\vision_ai\python.exe -m pip install pyinstaller
powershell -ExecutionPolicy Bypass -File .\desktop_launcher\build_launcher.ps1 `
  -PythonExecutable "C:\Users\AISW_203_113\anaconda3\envs\vision_ai\python.exe" `
  -ProjectRoot "C:\Users\AISW_203_113\Documents\GitHub\AI-Exercise-Assistant"
```

생성물:

```text
desktop_launcher/dist/FitRouteLauncher.exe
desktop_launcher/dist/config.json
```

`config.json`에는 개발 PC의 절대 경로가 들어가므로 Git에 포함하지 않는다.

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

## Installer 생성

`desktop_launcher/installer/FitRouteAIClient.iss`는 Inno Setup source다. 현재 PC 검사 결과 Inno Setup compiler(`ISCC.exe`)는 설치되어 있지 않으며 Codex는 외부 프로그램을 설치하지 않았다.

1. 먼저 Launcher EXE와 `config.json`을 빌드한다.
2. 사용자가 Inno Setup을 설치한다.
3. 다음 source를 Inno Setup Compiler에서 빌드한다.

```text
desktop_launcher/installer/FitRouteAIClient.iss
```

예상 installer artifact:

```text
desktop_launcher/dist/installer/FitRoute-AI-Client-Setup.exe
```

Installer는 `%LOCALAPPDATA%\FitRoute`에 Launcher와 config만 설치하고 `fitroute://`를 HKCU에 등록한다. Uninstall은 해당 protocol과 설치 폴더만 제거하며 Conda 환경, 모델, 프로젝트 source는 건드리지 않는다.

## Web fallback과 다운로드 URL

웹은 protocol 실행 후 약 1.8초 동안 blur/hidden 신호가 없으면 설치 안내 Modal을 표시한다. 브라우저는 handler 설치 여부를 정확히 제공하지 않으므로 이는 확정 탐지가 아니다. Chrome/Edge의 외부 앱 실행 확인창은 정상이며 우회하지 않는다.

Installer 공개 주소는 한 곳에서 관리한다.

```dotenv
VITE_DESKTOP_CLIENT_DOWNLOAD_URL=<공개한-installer-asset-URL>
```

현재 실제 public installer URL은 없으므로 가짜 값을 넣지 않았다. 값이 비어 있으면 Web 설치 버튼은 `다운로드 준비 중`으로 비활성화되며 CLI fallback을 보여준다. 이후 GitHub Release 같은 versioned asset에 사용자가 직접 업로드한 뒤 URL을 설정하고 Frontend를 다시 빌드한다.

## 현재 개발용 제약

- 현재 PC의 `vision_ai` Python, 프로젝트 source, 모델과 호환 GPU/TensorRT가 필요하다.
- Launcher installer는 완전한 일반 사용자용 AI Client installer가 아니다.
- Web 인증 token은 Desktop으로 전달하지 않는다. 기존 `FITROUTE_ACCESS_TOKEN` 환경설정 방식을 유지한다.

## 일반 사용자 배포 전 남은 작업

- Python runtime과 AI dependencies 패키징 전략
- 모델 파일 배포 및 라이선스 검토
- CUDA/TensorRT/GPU 호환성 검사와 CPU fallback 정책
- code signing 및 installer 서명
- 자동 업데이트와 버전 호환 정책
- Web-to-Desktop 인증 handoff 설계
- 공식 Release asset 배포와 checksum 제공
