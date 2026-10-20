# Landmark 시퀀스 로그 형식 (`data/landmark_sequences/*.jsonl`)

한 줄에 JSON 하나. 구현: `src/sequence_logger.py`. 읽는 쪽(`scripts/analysis/*`)은 **알 수 없는 줄 종류를 건너뛴다.**

## 버전 규칙
**호환이 깨지는 변경만 `format_version`을 올린다.** 기존 줄을 바꾸지 않는 선택적 줄 종류 추가는 버전을 유지하고, 아래 표에 줄 종류와 추가 시점을 기록한다.

## 줄 종류
| 줄 종류 (`type`) | 추가 시점 | 버전 | 필수 | 내용 |
|---|---|---|---|---|
| `session` | 2026-10-12 (Phase 4) | 1 | 첫 줄 | 시작 시각, 메타데이터(자세·시점·note), 설정 스냅샷, 옵션(`face_landmarks`), 실행 환경 |
| `frame` | 2026-10-12 (Phase 4) | 1 | 프레임마다 | landmark 33개(정규화·world), 각도, 전신 유효, 시점 신호, 잠금, 라벨. 얼굴 좌표는 기본 미저장 |
| `end` | 2026-10-12 (Phase 4) | 1 | 정상 종료 시 마지막 줄 | 프레임·이벤트 집계, 버린 수, 기록 오류 |
| `event` | 2026-10-18 | 2 | 선택 | `rep_end`, `rep_merge_suspect`, `lock` (RepTracker 진단), `key` (키 입력, 2026-10-19 추가) |
| `footer` | 2026-10-19 | 2 (유지) | 선택 | 종료 시 입력한 실제 반복 횟수·특이사항과 화면 카운트. `end` 바로 앞 한 줄. `--log-sequence`로 Q/ESC 종료한 대화형 실행에서만 |

## 버전 이력
- **1** (2026-10-12): session / frame / end.
- **2** (2026-10-18): `frame`에 `rep`(RepTracker 상태·안내 사유)와 `lock.detail` 필드 추가, `event` 줄 추가. 읽는 쪽은 1과 2를 모두 읽는다.
- 2 유지 (2026-10-19): `event`(`rep_end`)에 선택 키 `posture`(확정된 반복의 자세 점수: `total`, `worst_item`, `capped`, `item_status`, `item_scores`, `measures`; 탈락·중단이면 null) 추가. 기존 키는 그대로.
- 2 유지 (2026-10-19): `frame.rep`에 선택 키 `framing`(그 프레임에 화면에 뜬 구도 안내 코드 `move_back`/`move_center` 또는 null) 추가. 기존 키(`state`, `notice`)는 그대로.
- 2 유지 (2026-10-19): `footer` 줄 추가(`app_reps`, `mode`, `actual_reps`, `actual_status`, `note`, `prompt`). 기존 줄은 그대로.
- 2 유지 (2026-10-19): `event`에 새 `kind` = `key` 추가(키 입력 기록). 새 줄 종류가 아니라 기존 `event` 줄의 새 kind라서 `type`/`kind`를 모르는 읽는 쪽은 건너뛴다. 키는 `quit`(Q/ESC; `session_active`), `session_start`(S; `applied`. **시작하면 화면 카운트가 0으로 돌아간다**), `session_end`(E; `applied`), `mode`(0/1/2; `to`), `reset`(R) 중 카운트·세션에 영향을 주는 것만 남는다. 모든 `key` 이벤트에 `key`, `t`(로깅 시작 기준 초), `mode`(누르기 **전** 모드), `squat_count`(누르기 **전** 화면 카운트)가 있다. 업로드 재시도(P)와 기능 없는 키는 남기지 않는다. 기존 키와 줄은 그대로. (사용 이유: 2차 실측 세션 4에서 확정 반복 6개인데 화면 카운트가 5였으나 R/S 입력을 로그로 확인할 수 없었다.)
- 2 유지 (2026-10-19): `event`(`rep_end`)에 선택 키 `ankle_gap_bottom_norm`(최저점 양발 간격/L), `hip_shift_norm`(반복 중 엉덩이 x 이동/반복 중 L 중앙값) 추가, `limits`에 `max_ankle_gap_bottom`, `max_hip_shift` 추가. `limits.other_max_ratio`는 기본이 null(ML 라벨 비율은 확정 조건이 아니라 `other_exercise_ratio`·`label_seconds`로 기록만 한다). 새 탈락 사유 코드 `feet_apart_bottom`, `hip_shift`. 기존 키는 그대로이고 옛 로그는 새 키가 없을 뿐이라 읽는 쪽이 건너뛴다.
