# 연속 세트(B) 본인 확인 진행표 (한 장, 약 10분)

> **2026-10-20 안내**: 이 문서의 설정 확인 명령에 쓰인 `REP_SET_BASELINE_ENABLED`, `REP_RETURN_KNEE_ANGLE`, `REP_BOUNDARY_SIGNAL`, `BODY_LOCK_RELEASE_GRACE_SECONDS`는 기본 꺼짐 플래그와 함께 제거되어 지금 그대로 실행하면 오류가 난다. 지금 기준 확인은 `python -c "import config.settings as s; print(s.USE_REP_TRACKER, s.REP_OTHER_EXERCISE_MAX_RATIO, s.REP_MAX_ANKLE_GAP_BOTTOM, s.REP_MAX_HIP_SHIFT)"` → `True None 0.4 0.7`.

3차 실측(P02)에서 연속 세트(B)는 숫자는 10/10으로 정확했지만 서 있는 시간 중앙값이 **0.87초**라 "위에서 멈추지 않은" 연속이 아니어서 판정하지 못했다. 이 문서는 **본인이 지금 코드로 연속 세트만** 다시 확인하는 진행표다. 카메라는 사람이 직접 켠다. 전체 맥락은 `field_test_2_protocol.md` 11.2절.

> **이 결과는 "같은 사람의 새 데이터"로 기록하고 일반화 증거로 세지 않는다.** 본인은 값을 정한 데이터의 참여자이기 때문이다. 이 확인으로 말할 수 있는 것은 "지금 코드가 본인의 위에서 멈추지 않는 연속 세트를 정확히 센다"뿐이고, 새 사람에게서 검증됐다는 뜻이 아니다.
> **실측 중에는 설정·값·코드를 고치지 않는다.** 안 맞아도 고치려 하지 말고 그대로 기록한다.

참여자 코드: **`P00`** (= 본인). 동의 확인은 해당 없음(본인).

## 1. 준비 체크리스트
- [ ] **코드 동결 확인** (3차 진행표와 같은 기준): 출력이 아래와 같아야 한다. 다르면 실측하지 말고 알린다.
  - `git branch --show-current` → `feature/v0.2.0-squat-quality`
  - `git log -1 --format=%h -- src config` → **`8b749f1`**
  - `git diff --stat 3e95593 HEAD -- src config tests scripts` → **출력 없음**
  - `git status`가 깨끗해야 한다. `git rev-parse --short HEAD`를 기록표에 적는다.
- [ ] **설정 기대값**: `python -c "import config.settings as s; print(s.USE_REP_TRACKER, s.REP_SET_BASELINE_ENABLED, s.REP_RETURN_KNEE_ANGLE, s.REP_BOUNDARY_SIGNAL, s.BODY_LOCK_RELEASE_GRACE_SECONDS, s.REP_OTHER_EXERCISE_MAX_RATIO, s.REP_MAX_ANKLE_GAP_BOTTOM, s.REP_MAX_HIP_SHIFT)"` → **`True False None smoothed 0.0 None 0.4 0.7`**
- [ ] **서버 업로드가 꺼져 있는지**(이번에는 확실히 끈다): PowerShell에서 `if ($env:FITROUTE_ACCESS_TOKEN) { 'SET' } else { 'not set' }` → **`not set`** 이어야 한다. `SET`이면 `Remove-Item Env:FITROUTE_ACCESS_TOKEN`으로 이 창에서만 지우고 실행한다. 앱 시작 때 `[Cloud] FitRoute API token not configured.`가 뜨는지 본다.
- [ ] **영상 창에서 `S`, `E`, `R` 키를 누르지 않는다.** 모드 키 `0`, `1`, `2`도 누르지 않는다. 종료는 `Q` 또는 `ESC`만. (S·E는 운동 세션을 열고 닫아 요약 업로드 경로를 탄다. 누르지 않으면 세션이 열리지 않아 업로드할 것이 없다. 실수로 눌렀으면 기록표 특이사항에 적는다. 키 입력은 로그에 남는다.)
- [ ] **카메라 위치는 3차·2차와 같은 정위치**(발끝 아래 화면 높이의 4% 이상 여유, 몸 높이 60~80%, 가운데). "뒤로 물러서 주세요" 등이 뜨지 않는 자리.
- [ ] GPU 점유 없음(`nvidia-smi`), 다른 무거운 프로그램 종료, 저장소 루트에서 `conda activate vision_ai` 상태로 실행.

## 2. 실행 (연속 세트 1세션)
명령 (note에 B 확인용임이 드러난다. 재실시 때는 `try2`, `try3`로 바꾼다):
```
python -m src.main --log-sequence --session-posture normal --session-view side --session-note "P00_B_check_continuous10_try1"
```
동작 순서: **① 명령 실행 → ② 정위치에서 측면으로 서서 0.5초 이상 가만히 → ③ 스쿼트 10회 → ④ 가만히 1~2초 → ⑤ `Q`/`ESC` → ⑥ 터미널에 "실제 반복 횟수" 입력(힘들어 중간에 멈췄으면 그때까지 한 횟수).**

> ### 위에서 멈추지 말고 바로 내려가기
> 올라와서 **서 있는 자세에서 쉬지 말고 곧바로 다음 반복**으로 내려간다. 위에서 "하나, 둘" 세며 쉬는 것도 안 된다. 속도는 평소대로(정해 두지 않는다). 3차 P02는 반복 사이에 약 0.9초씩 서 있었고 그래서 유효하지 않았다. 참고값: P01의 유효한 연속은 서 있는 시간 중앙값 0.29초였다.

## 3. 끝난 뒤 확인 (2가지, 이 순서로)
1. **횟수**: PowerShell
   ```
   python scripts/analysis/plot_landmark_sequence.py --session (Get-ChildItem data\landmark_sequences\*.jsonl | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
   ```
   출력의 `counts : actual N | screen N | detected N`을 기록표에 옮긴다. 이 로그의 `events :` 줄의 `key`는 **1개(quit)** 여야 한다.
2. **서 있는 시간**:
   ```
   python -m scripts.analysis.continuous_set_analysis --log <그 로그 경로> --fixtures --fps 17 --dropout 0.3 --offsets 0.0
   ```
   출력의 **`서 있는 시간(반복 끝~다음 반복 시작): ... 중앙값 X초`** 를 기록표에 적는다.

## 4. 판정과 재실시 규칙 (확정 기준 그대로, 프로토콜 10절 B)
- **유효 조건**: 서 있는 시간 중앙값 **0.5초 미만**. 이 조건을 못 채우면 "위에서 멈추지 않은" 연속이 아니다.
- **0.5초 이상이면 다시 한다(`try2`, 그래도 0.5초 이상이면 `try3`).** 이 확인은 본인 기준으로 **처음부터 최대 3회**다(P02의 1회는 세지 않는다). 모든 시도의 로그 파일 이름을 기록표에 적는다.
- **3번째에도 0.5초 이상이면 더 하지 않고** 그 3번째 로그로 판정하며 "진짜 연속 조건 미달"로 기록한다.
- 유효한 시도에서 **검출 = 실제**(10/10 정확 일치)이면 합격, 아니면 불합격이다.
- **RELEASE.md 연속 세트 문구는 결과에 따라 아래로 정한다**(결과를 보기 전에 정한 규칙이다):

  | 결과 | 문구 |
  |---|---|
  | 유효 + 10/10 합격 | "위에서 멈추지 않는 연속 세트는 **본인과 P01 두 사람(값을 정한 데이터)에서만 확인**됐고, 새 참여자에게서는 서 있는 시간이 길어 확인되지 않았습니다." |
  | 3번 모두 유효 조건 미달 | "위에서 멈추지 않는 연속 세트는 검증되지 않았습니다." |
  | 유효 + 불합격 | 원인을 분석해 보고한다(코드는 바꾸지 않고 문구와 값 수정은 사용자가 정한다) |
- 불합격이어도 **고치려 하지 말고 그대로 기록**한다.

## 5. 기록표 (시도마다 한 줄)
머리말: 날짜 ______ / 참가자 코드 P00(본인) / 커밋 해시 ______ / 코드 동결 확인 □ / 설정 기대값 □ / 토큰 not set □ / S·E·R 안 누름 □

| 시도 | 파일 이름 | 입력한 실제 | 화면(screen) | 검출(detected) | key 개수 | 서 있는 시간 중앙값 | 유효(<0.5초)? | 특이사항 |
|---|---|---|---|---|---|---|---|---|
| try1 | | | | | | ____초 | □예 □아니오 | |
| try2 | | | | | | ____초 | □예 □아니오 | |
| try3 | | | | | | ____초 | □예 □아니오 | |

## 6. 끝나고
- [ ] 로그 원본을 `D:\FitRoute_backup\landmark_sequences_20261019\`에 복사(저장소에 올리지 않는다), manifest.csv와 README.txt에 "본인 P00, B 확인용, 같은 사람의 새 데이터" 기록.
- [ ] 분석·RELEASE.md 문구 반영은 사용자 확인 뒤에 한다. 이 확인이 끝날 때까지 코드는 바꾸지 않는다.

예상 소요: 준비 약 5분 + 시도당 약 2.5분(1~3회) = **약 8~13분**.
