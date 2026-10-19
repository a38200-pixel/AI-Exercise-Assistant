# Phase 5(릴리스) 체크리스트

릴리스 전에 확인할 것을 모은 목록이다. DEVLOG에 흩어져 있던 항목을 모았고, 완료하면 체크한다. (이 문서는 2026-10-19에 만들었다. 이전에는 별도 체크리스트가 없었다.)

## 설치판(패키징 빌드) 확인
- [ ] **설치판에서 운동 기록이 `%LOCALAPPDATA%\FitRoute\workout_logs\`에 저장되는지 확인**: 세션을 시작·종료한 뒤 `workout_<시작시각>.json`이 생기고(`schema_version` 1, 반복별 결과), 설치 폴더에는 아무것도 안 생기는지, 폴더가 읽기 전용일 때(또는 일부러 막았을 때) 세션 종료와 서버 업로드가 정상이고 콘솔·로그에 저장 실패 한 줄이 남는지 본다. 개발 실행은 `data/workout_logs/`.
- [ ] 실제 PyInstaller 빌드를 만들어 `--diagnose-runtime`로 확인(지금까지는 spec·런처의 정적 확인만 했다).
- [ ] 빌드한 앱에서 안내·점수 문구가 한글로 나오는지(맑은 고딕 폰트 탐색, 없으면 영어 대체), `PIL.*` hiddenimports가 spec에 반영됐는지(기준 spec만 수정함, `optimized*.spec` 3개는 손대지 않음).
- [ ] 패키징 빌드에서 `--log-sequence`의 실제 횟수 입력(footer)이 묻지 않는지(frozen은 묻지 않음).

## 문서·버전
- [ ] Installer 기본값 3곳(`installer/FitRouteAIClient.iss`, `installer/build_installer.ps1`, `installer/validate_installer_inputs.py`)을 0.2.0으로.
- [ ] README의 테스트 수 갱신(`tests/`와 `backend/tests`를 구분해 재측정).
- [ ] CHANGELOG의 0.1.0/0.1.1 항목은 README Version History 표 기준 요약안을 제안.
- [ ] RELEASE.md 6절 "검증 방법"에 측정한 값만 기재(2차 실측 뒤).
- [ ] 2차 실측(`field_test_2_protocol.md`)으로 임계값 검증: 자세 점수 깊이 0점 지점(`POSTURE_DEPTH_ZERO_AT` 임시 120°), 구도 안내 기준값, 엉덩이 하강 0.20.

## 백업·저장소
- [ ] 로그 원본(`data/landmark_sequences/`)은 별도 백업(`D:\FitRoute_backup\`)에 있는지, 저장소에는 올라가지 않았는지.
- [ ] 큰 추적 파일(pptx 26MB 등)은 Git LFS·릴리스 첨부 후보로 별도 검토.
