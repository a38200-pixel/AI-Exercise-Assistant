# FitRoute Desktop Launcher

`fitroute://start?exercise=squat`을 검증하고 Desktop Supabase 인증 후 독립형 `FitRouteAIClient.exe`를 실행하는 Windows Launcher입니다.

Desktop은 refresh token만 Windows Credential Manager에 저장합니다. Access token은 protocol URL, config, command line과 log에 저장하지 않고 AI Client child process environment의 `FITROUTE_ACCESS_TOKEN`으로만 전달합니다. API 주소도 `FITROUTE_API_BASE_URL` child environment로 전달합니다.

Launcher의 실제 argv는 다음 형태이며 `shell=False`를 유지합니다.

```text
FitRouteAIClient.exe --exercise squat --auto-start-session
```

설치 기본 구조는 다음과 같습니다.

```text
%LOCALAPPDATA%\FitRoute\
├─ FitRouteLauncher.exe
├─ config.json
└─ ai_client\
   ├─ FitRouteAIClient.exe
   ├─ _internal\
   └─ models\
```

상대 AI Client 경로는 Launcher EXE 위치를 기준으로 해석합니다. EXE가 없으면 Python/Conda/source fallback 없이 실패합니다.

```powershell
python -m pytest tests/test_desktop_auth.py -q -p no:cacheprovider
python -m pytest tests/test_desktop_launcher.py tests/test_auto_start_session.py -q -p no:cacheprovider
```

PyInstaller build는 `build_launcher.ps1`을 사용합니다. 이 스크립트는 build에 선택한 Conda Python의 runtime DLL을 포함하고 PyQt5, PyQt6와 matplotlib을 제외하지만, 해당 환경의 package를 제거하지 않습니다. Build용 Python 경로는 runtime config에 저장되지 않습니다.

Build 명령, protocol 등록/제거, 인증 흐름, 실패 해결 기록과 사용자 E2E 절차는 [프로젝트 README](../README.md#web--windows-desktop-launcher)와 [Desktop Launcher 문서](../docs/desktop_client_launcher.md)를 참고하세요. 이 폴더의 스크립트는 자동으로 Registry나 Webcam을 변경·실행하지 않습니다.
