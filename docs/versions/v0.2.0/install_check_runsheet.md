# 설치판(0.2.0) 직접 확인 진행표

설치 파일을 만든 뒤 **사용자가 직접** 확인할 항목이다(카메라·로그인·서버가 필요해 자동화하지 않았다). 설치 파일은 `FitRoute-AI-Client-Setup-0.2.0.exe`이며 경로·해시는 DEVLOG의 D단계 기록에 있다. **서버(Supabase) 접근과 삭제는 사용자가 한다.** 안 맞아도 코드·설정을 고치지 않고 그대로 기록한다.

소요 약 30~40분. 순서대로 1 → 5.

## 1. 0.1.1 위에 0.2.0 설치 (업그레이드)

0.1.1이 설치된 PC에서 한다(같은 AppId라 같은 폴더에 덮어 설치된다). 설치 폴더는 `%LOCALAPPDATA%\Programs\FitRoute AI Client\`.

1. **먼저 실행 중인 FitRoute 영상 창·런처를 모두 닫는다**(카메라 뮤텍스 `Local\FitRouteAIClientCamera`가 잡혀 있으면 설치가 막힌다).
2. 설치 전 상태 기록(PowerShell):
   ```powershell
   $d = "$env:LOCALAPPDATA\Programs\FitRoute AI Client"
   Get-ChildItem $d | Select-Object Name,Length,LastWriteTime
   (Get-ChildItem $d\ai_client -Recurse -File | Measure-Object).Count
   ```
   파일 수(0.1.1)와 `FitRouteLauncher.exe` 수정 시각을 적어 둔다.
3. `FitRoute-AI-Client-Setup-0.2.0.exe` 실행 → 끝까지 설치. 오류 창이 뜨면 문구를 그대로 적는다.
4. 확인 항목:
   - [ ] **버전 표시**: Windows 설정 > 앱 > 설치된 앱의 "FitRoute AI Client" 버전이 **0.2.0**. (0.1.1 항목이 따로 남아 있지 않고 하나만 있어야 한다.) 확인 명령:
     ```powershell
     Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}_is1' | Select-Object DisplayName,DisplayVersion,InstallLocation
     ```
   - [ ] **`fitroute://` 실행**: 실행창(Win+R) 또는 브라우저 주소창에 `fitroute://start?exercise=squat` → 런처가 뜬다(웹의 "운동 시작" 버튼에서 열어도 된다).
   - [ ] **옛 파일 잔재 없음**: 설치 후 같은 명령(2번)을 다시 실행. `ai_client` 폴더는 설치 때 먼저 지운 뒤 새로 복사하므로 파일 수가 **3,653개**(0.2.0 번들)여야 하고, `ai_client` 밖의 낯선 파일(0.1.1에만 있던 것)이 없어야 한다. 폴더에 `FitRouteLauncher.exe`, `config.json`, `ai_client\`, (실행 후) `launcher.log`만 있으면 정상.
   - [ ] `config.json`의 API 주소: `Get-Content "$env:LOCALAPPDATA\Programs\FitRoute AI Client\config.json"` → `https://fitroute-api.onrender.com` (로컬 주소가 아니어야 한다).
   - [ ] `& "$d\ai_client\FitRouteAIClient.exe" --diagnose-runtime` 이 **PASS**(이 PC에서 빌드 폴더로는 PASS 확인함).

## 2. 설치판 스모크 (카메라 사용)

**런처에서 시작한다**(`python -m src.main` 직접 실행이 아니다 — 그것은 토큰이 없어 업로드되지 않는다). 런처가 AI Client를 `--exercise squat --auto-start-session`으로 띄워 세션이 자동으로 열린다.

- **영상 창에서 `S`, `R`, `0`/`1`/`2` 키를 누르지 않는다.** 종료는 `E`(세션 종료) 또는 `Q`/`ESC`.
- 4절 서버 확인과 한 번에 하려면 아래를 **로그인된 상태에서 한 번만** 한다(4-1 사전 기록을 먼저).

확인 항목(측면으로 서서 정위치):
- [ ] 앱 시작, 영상 창이 뜬다.
- [ ] **측면 스쿼트 5~10회가 세어진다**(실제 횟수와 화면 횟수를 적는다).
- [ ] 반복마다 **"N점 · …" 점수 줄**이 나온다.
- [ ] 첫 점수 때 **범위 안내 한 번**: "자세 점수는 깊이와 상체 정렬만 봅니다"(세션당 1회).
- [ ] **구도 안내**가 나온다(일부러 발끝이 화면 아래에 걸리게 하거나 멀리 서서 확인. "뒤로 물러서 주세요" 등).
- [ ] **한글이 깨지지 않는다**(네모 □ 또는 `?`로 나오면 폰트 문제 — 화면을 캡처해 둔다). 맑은 고딕(`C:\Windows\Fonts\malgun.ttf`)이 없으면 영어 문구로 나오는 것이 정상 대체다.
- [ ] 종료 후 영상 창이 닫히고 콘솔 창에 오류 줄이 없다.

## 3. 로컬 운동 기록 위치

- 위치: `%LOCALAPPDATA%\FitRoute\workout_logs\` (설치 폴더가 **아니다**)
  ```powershell
  Get-ChildItem "$env:LOCALAPPDATA\FitRoute\workout_logs" | Sort-Object LastWriteTime -Descending | Select-Object -First 3 Name,Length,LastWriteTime
  ```
- [ ] 2절 세션을 끝낸 뒤 `workout_<시작시각>.json`이 새로 생긴다.
- [ ] 내용: `Get-Content <그 파일> | ConvertFrom-Json | Select-Object schema_version` → `1`, 반복별 결과가 들어 있다(횟수가 2절 화면과 맞는지).
- [ ] 설치 폴더(`ai_client` 아래 `data\` 등)에는 기록이 **생기지 않는다**.
- [ ] (선택) 저장 실패 시 동작: 위 폴더를 읽기 전용으로 만들거나 같은 이름 파일을 잠근 채 세션을 종료해 본다. 세션 종료와 서버 업로드는 정상이고 콘솔·로그에 저장 실패 한 줄만 남아야 한다. 확인 뒤 되돌린다.
- 영상 로그(`--log-sequence`)는 설치판에서 쓰는 기능이 아니다. 기록하지 않는다.

## 4. 서버 업로드 확인 (Supabase)

9월 15일 이후 실제 업로드 경로가 한 번도 실행되지 않았다. **README Known Issues**: 설치 후 **최초 실행의 첫 세션 저장이 실패할 수 있다**(원인 미확정, 재시도하면 정상). 첫 시도에 행이 없으면 **한 번 더 시도**하고 두 시도 모두 기록한다.

### 4-1. 사전 기록 (세션 전)
Supabase SQL Editor에서 오늘 날짜·본인 계정의 현재 값을 먼저 적는다(`<USER_ID>`는 본인 `auth.users.id`).
```sql
-- 본인 user_id 찾기(이메일은 본인 것으로 바꾼다)
select id, email from auth.users where email = '<본인 이메일>';

-- 세션 전: 세션 행 수와 오늘 일일 요약
select count(*) as sessions_before from public.workout_sessions where user_id = '<USER_ID>';
select * from public.daily_workout_summary
 where user_id = '<USER_ID>' and workout_date = current_date;
```
**일일 요약 행이 없었는지, 있었다면 값(squat_count, stretch_seconds, workout_seconds, session_count)을 적어 둔다.** (RPC가 값을 더하는 방식이라 복구에 필요하다.) 서버 날짜 기준(UTC/KST)이 달라 `workout_date`가 오늘과 어긋나면 어제·내일 날짜도 같이 조회한다.

### 4-2. 세션
1. 런처로 로그인(웹 로그인 → 런처). 로그인 안 된 상태면 업로드되지 않는다.
2. 런처로 스쿼트 시작 → **짧은 세션 1회**(스쿼트 3~5회, 1분 이내) → `E` 또는 `Q`로 종료. 콘솔 창의 `[Cloud]` 줄을 그대로 기록한다.
3. Render 서버가 잠들어 있으면 첫 응답이 수십 초 걸릴 수 있다. 종료 후 약 1분 기다린 뒤 조회한다.

### 4-3. 세션 후 조회
```sql
-- 방금 세션 행(가장 최근 5개)
select id, user_id, workout_date, started_at, ended_at, workout_seconds,
       squat_count, stretch_seconds, created_at
  from public.workout_sessions
 where user_id = '<USER_ID>'
 order by created_at desc
 limit 5;

-- 일일 요약
select user_id, workout_date, squat_count, stretch_seconds, workout_seconds,
       session_count, created_at, updated_at
  from public.daily_workout_summary
 where user_id = '<USER_ID>'
 order by workout_date desc
 limit 3;
```
- [ ] `workout_sessions`에 새 행: `squat_count`가 화면·로컬 기록 횟수와 같고 `workout_seconds`가 실제 시간과 비슷하다.
- [ ] `daily_workout_summary`의 값이 사전 기록 값 **+ 이번 세션 값**, `session_count`가 +1.
- [ ] 로컬 기록 json(3절)의 횟수와 서버 `squat_count`가 같다.

실패하면 구분해서 적는다: ① 콘솔에 `[Cloud]` 토큰 없음/인증 실패 → 런처 로그인·토큰 전달 문제, ② 요청은 나갔으나 연결/시간 초과 → Render cold start나 네트워크, ③ 서버가 4xx/5xx 응답 → 서버·DB. (런처 로그는 5절.)

### 4-4. 테스트 행 정리 (사용자가 실행, 확인 뒤에만)
**먼저 4-3의 `id`가 방금 만든 테스트 행이 맞는지 눈으로 확인한 뒤** 실행한다. 일일 요약은 RPC가 값을 더한 것이고 세션 행을 지워도 자동으로 빠지지 않으므로 **수동으로 되돌려야 한다.**
```sql
-- (A) 테스트 세션 행 삭제 — <SESSION_ID>는 4-3에서 확인한 값
delete from public.workout_sessions where id = '<SESSION_ID>';

-- (B-1) 사전에 오늘 요약 행이 "없었던" 경우: 행 삭제
delete from public.daily_workout_summary
 where user_id = '<USER_ID>' and workout_date = '<테스트 날짜>';

-- (B-2) 사전에 행이 "있었던" 경우: 사전 기록 값으로 되돌림
update public.daily_workout_summary
   set squat_count = <사전 squat_count>,
       stretch_seconds = <사전 stretch_seconds>,
       workout_seconds = <사전 workout_seconds>,
       session_count = <사전 session_count>
 where user_id = '<USER_ID>' and workout_date = '<테스트 날짜>';
```
삭제 뒤 4-1의 조회를 다시 실행해 사전 값과 같은지 확인한다. (첫 시도 실패 뒤 재시도로 행이 둘 생겼다면 두 세션을 모두 정리한다.)

## 5. 문제가 생기면 남길 정보

| 무엇 | 어디 |
|---|---|
| 런처 로그 | `%LOCALAPPDATA%\Programs\FitRoute AI Client\launcher.log` (런처 옆) |
| AI Client 콘솔 출력 | AI Client는 콘솔 창으로 뜬다. `[Cloud]` 줄 포함해 창 내용을 복사(종료 직전 캡처) |
| 로컬 운동 기록 | `%LOCALAPPDATA%\FitRoute\workout_logs\workout_*.json` |
| 설치 로그 | 설치 파일을 `FitRoute-AI-Client-Setup-0.2.0.exe /LOG="%TEMP%\fitroute_setup.log"`로 실행하면 남는다 |
| 런타임 진단 | `& "$env:LOCALAPPDATA\Programs\FitRoute AI Client\ai_client\FitRouteAIClient.exe" --diagnose-runtime` 출력 전체 |
| 설치 상태 | 1절 2번 명령 출력, 레지스트리 `DisplayVersion` |
| 서버 쪽 | 4-1·4-3 조회 결과, 웹 대시보드 화면 |
| 인증 | Windows 자격 증명 관리자의 `FitRoute AI Client/supabase_refresh_token` 항목 유무. 로그인 꼬임이 의심되면 `FitRouteLauncher.exe --logout` 후 다시 로그인 |

함께 적을 것: 몇 시에, 어느 단계(1~4)에서, 화면에 뜬 문구 그대로, 첫 실행/재시도 여부.

## 6. 기록표

날짜 ______ / 설치 전 버전 ______ / 설치 후 DisplayVersion ______ / 파일 수 ______

| 항목 | 결과 | 메모 |
|---|---|---|
| 1 버전 0.2.0 단일 항목 | □ | |
| 1 `fitroute://` 실행 | □ | |
| 1 옛 파일 잔재 없음, 파일 3,653개 | □ | |
| 1 config.json 운영 주소 | □ | |
| 2 측면 스쿼트 횟수 (실제 __ / 화면 __) | □ | |
| 2 점수 줄 / 범위 안내 1회 | □ | |
| 2 구도 안내 / 한글 표시 | □ | |
| 3 로컬 기록 생성, 설치 폴더에 없음 | □ | |
| 4 서버 `workout_sessions` 행 | □ | |
| 4 `daily_workout_summary` 증가 | □ | |
| 4 테스트 행 정리, 사전 값 복구 | □ | |
