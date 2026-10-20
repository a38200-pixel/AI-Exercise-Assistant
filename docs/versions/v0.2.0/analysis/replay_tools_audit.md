# 재생·분석 도구와 실제 코드의 일치 점검 (2026-10-20)

계기: 엉덩이 이동 분석 스크립트가 실제 구현과 다른 L로 계산해, 보고한 값(1.18)과 구현 값(0.744)이 달랐다. 같은 종류의 불일치가 다른 도구에도 있는지 점검했다. 카메라는 쓰지 않았다.

## 1. 도구별 점검표

| 도구 | 쓰인 곳 | 판정을 자체 구현하는가 | 실제 src를 호출하는가 | 조치 |
|---|---|---|---|---|
| `replay_flags.replay` | 거의 모든 재생의 기반(플래그, 저FPS, 구도, 점수 분포) | 판정은 아니고 **접착 코드**를 자체 구현: 기록된 신호(평활 무릎각, 측면 판정, `leg_now`)로 RepFrame을 만든다. 잠금 다리는 로그에 기록된 값을 쓴다 | `RepTracker`, `BodyLockPolicy`, `OneEuroFilter` 실제 클래스 | 아래 2절 대조로 일치 확인, 합성 비교 테스트 추가, 프레임별 RepTracker 상태(`states`) 노출 추가 |
| `geometry_replay` | 잠금 다리 변경 검증 | 없음 | `GeometryTracker`, `track_primary_person`, `RepTracker` 전부 실제 | 반복 결과(`results`)를 반환하도록 추가 |
| `ml_condition_replay` | ML 조건 비교 | 없음 | 실제 `RepTracker`에 설정만 바꿔 넣음 | 새 조건은 기본 꺼짐으로 두어 과거 표를 그대로 재현(재실행 동일) |
| `proposal_replay` | 조합·부호 변경 재생 | `--counts`는 **조건을 자체 재계산했다** | `--signed`는 실제 `score_posture`(함수 하나만 메모리에서 교체) | `--counts`를 실제 `RepTracker` 설정(`other_max_ratio`, `max_ankle_gap_bottom`, `max_hip_shift`)으로 교체. 재실행 표 동일 |
| `leave_motion_features` | 자리 뜨는 동작 특징 | **엉덩이 이동을 자체 계산했다**(서 있을 때 L로 나눔, 구현은 반복 중 L). 나머지 특징(측면 아닌 비율, yaw, 전신 무효, bbox 높이, L 증가)은 탐색용 지표이고 판정이 아니다 | 일부 | 엉덩이 이동은 `RepResult.hip_shift_norm`을 쓰도록 교체. 다른 특징은 그대로 |
| `ankle_gap_analysis` | 발 간격 분해 | 서 있을 때 기준 창·중앙값을 **설명용으로 재구성**한다(픽셀 값을 보이려고) | 일부 | 최저점 비율은 `RepResult.ankle_gap_bottom_norm`을 옆에 같이 보인다. 서 있을 때 재구성값이 기록값과 같음은 이전에 확인(0.243, 0.831 등) |
| `posture_score_distribution` | 점수 분포 | 없음 | `replay_flags` + 실제 `score_posture` | 재실행(아래 3절) |
| `framing_replay` | 구도 안내 재생 | 안내 판정은 실제 `FramingGuide`·`classify_framing`. **반복 중(in_rep) 입력은 반복 후보의 (시작, 끝) 시각으로 근사**했다 | 일부 | 실제 `RepTracker`의 프레임별 상태(IN_REP)로 교체. 앱이 기록한 `rep.state`와 비교해 차이 프레임이 2.9%에서 0.37%(수정 전 코드로 기록된 c10만)로 줄었다 |
| `landmark_gap_analysis` | 공백 분석 | 공백 종류·자세 구간(무릎각 보간)·경계 거리 구간을 **자체 분류**한다(기술 통계, 임계값 판정이 아님) | 일부(`replay_flags`로 세트 구간) | 구도 안내 상수는 `FramingGuide` 재생(위)이 검증한다. 조치 없음 |
| `continuous_set_analysis` | 연속 세트, 저FPS | 진단 지표(반복 사이 봉우리, 서 있는 시간)를 자체 계산. 횟수는 `replay_flags` | 일부 | 지표일 뿐 판정이 아님. 저FPS 재생 재실행(아래) |
| `midset_diagnosis` | 세트 중간 누락 진단(플래그 설계 근거) | `replay_flags` 이전 형태의 자체 `simulate` 접착 코드 | `RepTracker`, `BodyLockPolicy` 실제 | 과거 진단용이며 새 결론의 근거로 쓰지 않는다. `hip_x` 인자만 맞췄다 |
| `hypothesis5_synthetic` | 평활 가설 | 합성 파형 | 실제 `OneEuroFilter` | 없음 |
| `extract_rep_fixtures` | fixture 추출 | 없음 | 실제 `measure_frame` | `hip_x` 열 추가 |
| `field_test_1_lib`, `field_test_1_analysis` | Phase 0.5 임계값 도출 | **반복 추출·지표를 전부 자체 구현** | v0.1.x `ExerciseCounter`(비교용)만 | 이후 실제 `RepTracker`가 1차 세션 1~5를 정확히 재현하는 fixture 회귀 테스트(42/42)가 있어 임계값 결론은 실제 코드로 재확인됐다. 더 이상 결정 근거로 쓰지 않음 |
| `polar_squat_angle_analysis`, `polar_phase05_verification` | Phase 0 각도 분포(학습 데이터) | **무릎각(arccos)·가까운 다리 선택을 자체 구현** | 아니오 | 실제 `knee_angle`·`select_near_leg`와 300개 무작위 입력에서 1e-6° 이내로 같고, 160°·150° 경계 판정이 같다는 테스트 추가 |
| `notice_render_benchmark` | 안내 렌더 시간 | 없음 | 실제 `main` 렌더 | 없음 |
| `plot_landmark_sequence` | 로그 그래프·요약 | 재판정 없음(로그에 기록된 값 표시) | - | 새 `rep_end` 키(최저점 발 간격, 엉덩이 이동)와 ML "기록만" 표시 추가 |

## 2. 재생 접착 코드가 실제 파이프라인과 같은가 (`replay_fidelity_check`)

`python -m scripts.analysis.replay_fidelity_check --log data/landmark_sequences/session_*.jsonl`. 같은 로그를 세 가지로 비교한다: live(로그의 `rep_end` 이벤트 = 로그를 만들 때 실제 앱이 낸 판정), G(`geometry_replay`: landmark에서 GeometryTracker + RepTracker 전부 다시), R(`replay_flags`). 로그를 만들 때의 설정(ML 상한 0.40, 새 조건 꺼짐)으로 비교했다.

- **R 대 G: 26개 로그 모두 반복 단위로 일치**(후보 수, 시작 시각, 확정 여부, 탈락 사유, 엉덩이 하강·발 간격·ML 비율). 새 기본 설정으로도 26개 일치.
- **live 대 G, live 대 R: `rep_end` 이벤트가 있는 11개 로그 중 10개 완전 일치.** 다른 하나는 c10(`171322`)이며 수정 전 코드로 기록되어 실시간 후보가 10개, 재생이 13개다(알려진 차이: 두 구조적 버그 수정 전).
- 즉 `replay_flags`는 로그에 기록된 신호를 쓰는데도 실제 파이프라인 전체를 다시 돌린 결과와 같다. 한계: 잠금 다리는 로그에 기록된 값이라, GeometryTracker 규칙을 로그를 만든 뒤 바꿨다면 `geometry_replay`로 봐야 한다.
- 저장소에 들어가는 비교 테스트: `tests/test_replay_matches_real_pipeline.py`(합성 스쿼트를 실제 앱 경로로 기록한 뒤 `replay_flags`·`geometry_replay` 재생과 `rep_end`를 반복 단위로 비교, 판정이 다르면 비교가 실패함을 확인), `tests/test_analysis_tools_use_real_formulas.py`(폴라 분석의 각도·다리 선택).

## 3. 주요 결론 재실행 (달라진 결론 없음)

| 결론 | 재실행 | 결과 |
|---|---|---|
| 2차 재생 결과 표(조합 적용) | `proposal_replay --counts`, 26개 로그 기본 설정 재생 | 모든 행이 이전 표와 같다. 비스쿼트: 1차 걷기 0·의자 3·런지 0, 2차 걷기 0·런지 0(이전 기본 1). c10 10(80.1초는 `hip_shift`로 탈락) |
| 저FPS 재생 | `continuous_set_analysis`(연속 세트 2개 + fixture 1~5, 17·12·10·8·6·5 FPS, 대응안 플래그 포함) | **전부 누락 없음**(10/10, 8/8). 사람 없음 끼워 넣기도 전부 정상. 기존 보고서의 결론 그대로 |
| 구도 안내 재생 | `framing_replay`(로그 16개, 17개) | 보고서의 표는 보고서가 만들어진 커밋(b85d7e5)에서 **정확히 재현**된다(111/108/100/86구간 등). 현재 값이 다른 것은 그 뒤 안내 코드 변경(3d9667f: 좌우를 crop 잘림 0.5로, 짧은 놓침 동안 유지)의 효과이며 이번 점검과 무관하다. 이번 수정(실제 반복 상태 사용)은 1.5초 기준 공백 포착 79.2% → 79.6%, 세트 안 안내 없는 프레임 357 → 376(6,750 중)으로 1%p 미만이다. **좌우 기준 비교표(side_report)는 17개 로그에서 숫자가 정확히 같다**(117/64%, 87/85% 등) |
| 자세 점수 분포 | `posture_score_distribution` | 반복 수, 측정값(최저 무릎각, torso_shin), 판정 상태 분포가 DEVLOG 표와 같다. 총점은 DEVLOG 표의 값과 다르지만(세션 3: 62 → 81 등) 이는 그 뒤에 결정한 깊이 점수 2단 선형 변경 때문으로 이번 점검과 무관하다 |
| 전체 테스트 | `pytest tests` | 650개 통과 |

달라지는 결론이 없어 중단 조건에 해당하지 않는다.
