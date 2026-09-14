# FitRoute Desktop Launcher

개발 PC의 기존 Python AI Client를 `fitroute://start?exercise=squat`에서 실행하는 소형 Windows Launcher입니다.

Desktop은 Supabase에 별도로 로그인하고 refresh token만 Windows Credential Manager에 저장합니다. Access token은 command line이나 config에 저장하지 않고 AI child process environment에만 전달합니다. Camera가 준비되면 Workout Session이 자동으로 시작됩니다.

```powershell
python -m pytest tests/test_desktop_auth.py -q -p no:cacheprovider
python -m pytest tests/test_desktop_launcher.py tests/test_auto_start_session.py -q -p no:cacheprovider
```

PyInstaller build는 `build_launcher.ps1`을 사용합니다. 이 스크립트는 범용 Conda 환경의 PyQt5/PyQt6와 사용하지 않는 matplotlib을 제외하고, `_ctypes`, `pyexpat`, tkinter가 필요로 하는 확인된 Conda `Library\bin` DLL을 onefile bundle에 포함합니다.

빌드 명령, protocol 등록/제거, 인증 흐름, installer, 실패 원인과 해결 기록 및 E2E 절차는 [프로젝트 README](../README.md#web--windows-desktop-launcher)와 [상세 개발 문서](../docs/desktop_client_launcher.md)를 참고하세요.

이 폴더의 스크립트는 자동으로 Registry를 변경하지 않습니다. 등록 또는 installer 실행은 사용자가 직접 수행해야 합니다.
