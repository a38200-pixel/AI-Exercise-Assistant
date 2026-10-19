# 로컬 운동 기록 파일 형식 (`workout_<시작시각>.json`)

세션(Workout Session)이 끝날 때(`WorkoutSession.end()`, E 또는 Q/ESC) 한 세션당 한 파일을 저장한다. 구현: `src/workout_session.py`, 경로: `src/paths.py`의 `get_workout_log_dir()`.
**서버로 업로드하는 summary의 형식은 바꾸지 않았다.** 이 파일은 로컬 전용이며 서버로 보내지 않는다.

## 저장 위치
| 실행 | 위치 |
|---|---|
| 개발(저장소) | `data/workout_logs/` (`.gitignore`가 `*.json`, `*.tmp`를 무시) |
| 패키징(설치판, frozen) | `%LOCALAPPDATA%\FitRoute\workout_logs\` (`LOCALAPPDATA`가 없으면 `<홈>\AppData\Local\FitRoute\workout_logs\`). 설치 폴더(Program Files)에는 쓰지 않는다 |

- 파일 이름: `workout_<세션 시작 시각 YYYYMMDD_HHMMSS>.json`. 같은 초에 끝난 세션이 있으면 `_2`, `_3`을 붙여 덮어쓰지 않는다.
- 쓰기: 같은 폴더에 임시 파일(`.json.tmp`)로 쓴 뒤 교체한다(중간에 끊겨도 반쯤 쓴 `.json`은 남지 않는다). 폴더는 저장할 때 만든다.
- **저장 실패는 세션 종료와 서버 업로드를 막지 않는다.** 실패하면 경고 로그(`src.workout_session`)와 콘솔 한 줄(`[Local] Could not save the workout record: ...`)을 남기고 `WorkoutSession.last_save_error`에 사유를 둔다.
- 저장하지 않는 것: **영상, landmark(얼굴 포함) 원자료, bbox, 프레임 단위 값은 없다.** 반복 단위 판정 결과와 시각·횟수·점수만 있다. 사용자 식별 정보도 없다.

## 형식 (`schema_version` 1)
| 키 | 내용 |
|---|---|
| `schema_version` | 1 |
| `workout_date`, `started_at`, `ended_at`, `workout_seconds`, `squat_count`, `stretch_seconds` | **서버로 업로드하는 summary와 같은 필드·값** |
| `reps` | 이번 세션의 반복 후보 전부(확정·탈락·중단), 순서대로 |
| `settings` | 기록 시점의 판정 기준(`REP_MIN_SECONDS`, `REP_MIN_HIP_DROP`, `REP_MAX_ANKLE_GAP`, `REP_OTHER_EXERCISE_MAX_RATIO`, `POSTURE_*`). 임계값은 2차 실측 뒤 바뀔 수 있어 점수를 나중에 해석하려고 함께 남긴다 |

`reps[]` 한 항목:

| 키 | 내용 |
|---|---|
| `index` | 세션 안의 반복 후보 순번(1부터) |
| `rep_number` | 확정된 반복의 순번(1부터). 탈락·중단이면 null |
| `counted` | 횟수에 들어갔는가 |
| `reasons` | 탈락·중단 사유 코드 목록(`too_short`, `shallow_hip_drop`, `feet_apart`, `other_exercise`, `tracking_lost`, `lock_lost`, `no_baseline`). 확정이면 빈 목록 |
| `seconds_from_start` | 세션 시작 기준 반복 시작 시각(초) |
| `total_seconds`, `min_knee_angle`, `hip_drop_norm` | 반복 길이(초), 최저 무릎각(도), 엉덩이 하강량(다리 길이 비). 알 수 없으면 null |
| `posture` | 확정된 반복의 자세 점수, 아니면 null. 아래 |

`posture`: `total_score`(0~100), `worst_item`(`depth`/`torso_shin`/null), `capped`(교정 항목으로 총점 상한이 적용됐나), `item_status`(항목별 `normal`/`caution`/`correct`/`recorded_only`/`unavailable`), `item_scores`(항목별 점수, 판정하지 않은 항목은 null), `measures`(`depth` = 최저 무릎각, `torso_shin` = 최저점 |몸통각-정강이각|).

## 형식 버전 규칙
`format_version` 규칙(`log_format.md`)과 같다: 기존 키의 의미를 바꾸거나 없애는 호환이 깨지는 변경만 `schema_version`을 올리고, 선택 키 추가는 올리지 않는다. 읽는 쪽은 모르는 키를 무시한다.

## 예 (요약)
```json
{
  "schema_version": 1,
  "workout_date": "2026-10-19", "started_at": "2026-10-19T20:01:11+09:00", "ended_at": "2026-10-19T20:04:40+09:00",
  "workout_seconds": 209.0, "squat_count": 2, "stretch_seconds": 0.0,
  "reps": [
    {"index": 1, "rep_number": 1, "counted": true, "reasons": [], "seconds_from_start": 98.5, "total_seconds": 2.2, "min_knee_angle": 68.1, "hip_drop_norm": 0.55,
     "posture": {"total_score": 100.0, "worst_item": null, "capped": false, "item_status": {"depth": "normal", "torso_shin": "normal"},
                 "item_scores": {"depth": 100.0, "torso_shin": 100.0}, "measures": {"depth": 68.1, "torso_shin": 17.0}}},
    {"index": 2, "rep_number": null, "counted": false, "reasons": ["shallow_hip_drop"], "seconds_from_start": 124.7, "total_seconds": 1.4, "min_knee_angle": 131.0, "hip_drop_norm": 0.12, "posture": null}
  ],
  "settings": {"REP_MIN_SECONDS": 1.0, "POSTURE_DEPTH_NORMAL_MAX": 80.0, "...": "..."}
}
```
