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
| `event` | 2026-10-18 | 2 | 선택 | `rep_end`, `rep_merge_suspect`, `lock` (RepTracker 진단) |
| `footer` | 2026-10-19 | 2 (유지) | 선택 | 종료 시 입력한 실제 반복 횟수·특이사항과 화면 카운트. `end` 바로 앞 한 줄. `--log-sequence`로 Q/ESC 종료한 대화형 실행에서만 |

## 버전 이력
- **1** (2026-10-12): session / frame / end.
- **2** (2026-10-18): `frame`에 `rep`(RepTracker 상태·안내 사유)와 `lock.detail` 필드 추가, `event` 줄 추가. 읽는 쪽은 1과 2를 모두 읽는다.
- 2 유지 (2026-10-19): `footer` 줄 추가(`app_reps`, `mode`, `actual_reps`, `actual_status`, `note`, `prompt`). 기존 줄은 그대로.
