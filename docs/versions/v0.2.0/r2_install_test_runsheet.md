# R2 업로드본 설치 테스트 진행표 (0.2.0)

R2에 올라간 설치 파일(Prepare 결과물)은 앞서 설치판 확인에 쓴 사전 빌드본과 **해시가 다르다.** 그래서 업로드본으로 한 번 더 확인한다. 웹사이트의 다운로드 링크는 아직 **0.1.1**을 가리키므로(Promote 전) 공개 URL에서 직접 받는다. 카메라는 사람이 직접 켠다. 안 맞아도 코드·설정을 고치지 않고 그대로 기록한다.

> **별도 Windows PC가 있으면 그 PC에서 하는 것이 더 낫다.** 이 PC는 개발 환경(Python, 이전 설치, 로컬 기록, 로그인 정보)이 남아 있어 "처음 설치한 사용자" 상황을 재현하지 못한다. 별도 PC에서는 1절(제거)을 건너뛰고 2절부터 하면 되고, 이 PC에서는 확인되지 않는 항목(최초 실행 첫 세션 저장 실패 가능성: README Known Issues)도 확인된다.

기준값(`releases/windows/v0.2.0.json`):

| 항목 | 값 |
|---|---|
| 파일 | `FitRoute-AI-Client-Setup-0.2.0.exe` |
| 크기 | 2,379,765,928바이트 |
| SHA-256 | `5D243B3BF6B07CAF49309CCB7E19606FE450FF9B160AED97E314130F59904EA9` |
| 공개 URL | `https://pub-08036d191fd84004a7a3d27bf8521aaf.r2.dev/releases/v0.2.0/FitRoute-AI-Client-Setup-0.2.0.exe` |

(사전 빌드본은 2,379,730,431바이트, `4B5A4C46…A174`. 두 파일의 AI 번들은 검증기 기준으로 같다: 3,653개 파일, 5,204,054,133바이트, exe SHA-256 `7E3C9D33…FB9CE`.)

## 1. 설치된 0.2.0 제거 (이 PC에서만)
- [ ] 실행 중인 FitRoute 영상 창·런처를 닫는다.
- [ ] Windows 설정 > 앱 > 설치된 앱 > FitRoute AI Client > 제거.
- [ ] 제거 확인:
  ```powershell
  Test-Path "$env:LOCALAPPDATA\Programs\FitRoute AI Client"   # 폴더가 남아 있으면 내용을 기록
  Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}_is1' -ErrorAction SilentlyContinue
  ```
- 로컬 운동 기록(`%LOCALAPPDATA%\FitRoute\workout_logs\`)은 제거해도 남는다. 지우지 않는다.

## 2. 공개 URL에서 직접 내려받기와 해시 확인
```powershell
$url  = 'https://pub-08036d191fd84004a7a3d27bf8521aaf.r2.dev/releases/v0.2.0/FitRoute-AI-Client-Setup-0.2.0.exe'
$out  = "$env:USERPROFILE\Downloads\FitRoute-AI-Client-Setup-0.2.0.exe"
curl.exe -L --fail -o $out $url
(Get-Item $out).Length                      # 2379765928 이어야 한다
$h = (Get-FileHash $out -Algorithm SHA256).Hash
$h
$h -eq '5D243B3BF6B07CAF49309CCB7E19606FE450FF9B160AED97E314130F59904EA9'   # True 이어야 한다
```
- [ ] 크기 일치, 해시 `True`. **다르면 설치하지 말고 값과 출력을 기록한다.**
- [ ] (선택) 저장소의 `releases/windows/v0.2.0.json`의 `sha256`과도 같은지 눈으로 확인.

## 3. 설치
- [ ] 받은 파일을 실행한다. 서명이 없는 설치 파일(`signed: false`)이라 Windows SmartScreen 경고가 뜰 수 있다. 뜨면 "추가 정보 > 실행"으로 진행하고 경고가 떴다고 기록한다.
- [ ] 기본 경로(`%LOCALAPPDATA%\Programs\FitRoute AI Client`)로 끝까지 설치. 오류 문구가 있으면 그대로 기록.
- [ ] 버전 표시 0.2.0:
  ```powershell
  Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}_is1' | Select-Object DisplayName,DisplayVersion
  (Get-ChildItem "$env:LOCALAPPDATA\Programs\FitRoute AI Client\ai_client" -Recurse -File | Measure-Object).Count   # 3653
  & "$env:LOCALAPPDATA\Programs\FitRoute AI Client\ai_client\FitRouteAIClient.exe" --diagnose-runtime   # PASS
  ```

## 4. 런처로 실행, 측면 스쿼트, 기록 확인
- [ ] `fitroute://start?exercise=squat`(웹의 "운동 시작" 버튼 또는 Win+R)로 런처 실행. 로그인이 풀려 있으면 다시 로그인.
- [ ] **영상 창에서 `S`, `R`, `0`/`1`/`2` 키를 누르지 않는다.** 측면으로 서서 스쿼트 5회 → `E` 또는 `Q`로 종료.
- [ ] 화면 횟수 5, 점수 줄·범위 안내·구도 안내가 한글로 나온다.
- [ ] 로컬 기록 생성:
  ```powershell
  Get-ChildItem "$env:LOCALAPPDATA\FitRoute\workout_logs" | Sort-Object LastWriteTime -Descending | Select-Object -First 2 Name,Length,LastWriteTime
  ```
- [ ] 서버 업로드: `install_check_runsheet.md` 4절의 Supabase 조회로 새 `workout_sessions` 행(`squat_count` 5)과 `daily_workout_summary` 증가를 확인한다. 이번에는 테스트 행을 삭제하지 않아도 된다(일별 요약 수동 되돌림 위험이 있어 앞서 지우지 않았다. 지울지는 사용자가 정한다).

## 5. 기록표
날짜 ______ / PC: □ 이 PC □ 별도 PC / 받은 파일 크기 ______ / 해시 일치 □

| 항목 | 결과 | 메모 |
|---|---|---|
| 2 크기·해시 일치 | □ | |
| 3 설치 완료(SmartScreen 경고 여부) | □ | |
| 3 DisplayVersion 0.2.0, 파일 3,653개, 진단 PASS | □ | |
| 4 런처 실행·로그인 | □ | |
| 4 스쿼트 5회 카운트·점수·안내·한글 | □ | |
| 4 로컬 기록 생성 | □ | |
| 4 서버 행 생성(squat_count 5) | □ | |
| (별도 PC) 최초 실행 첫 세션 저장 | □ | |

문제가 생기면 남길 정보는 `install_check_runsheet.md` 5절과 같다(`launcher.log`, 콘솔 `[Cloud]` 줄, 로컬 기록, 진단 출력).
