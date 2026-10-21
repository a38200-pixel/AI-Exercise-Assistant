# 대응안 후보 플래그: fixture 회귀 결과 (기본 꺼짐)

세트 중간 누락 진단(`DEVLOG.md`의 2026-10-19 기록)에서 나온 대응안을 **설정 플래그 뒤에 구현**했다. 기본값은 모두 꺼짐이라 기본 동작은 바뀌지 않는다
(기본 설정의 기존 테스트는 변경 없이 통과). 이 문서는 플래그를 켰을 때 기존 실측 fixture(field_test_1)의 결과가 바뀌는지 본 것이다.

| 플래그 (config/settings.py) | 대응하는 가설 | 켜면 |
|---|---|---|
| `REP_SET_BASELINE_ENABLED` | 4. 휴지 없는 세트에서 서 있는 기준 높이가 낮아짐 | 기준값을 직전 1초가 아니라 잠금이 유지되는 동안(최근 30 s)의 완전히 선 프레임(무릎각 ≥160°)에서 잡는다. 엉덩이 y는 높은 쪽 25% 분위수, 나머지는 중앙값. 프레임이 5개 미만이면 직전 1초로 되돌아간다 |
| `REP_RETURN_KNEE_ANGLE` (예: 155) | 1. 봉우리가 160°에 못 닿음 | 반복이 끝나는 복귀 기준을 160°에서 내린다(150° 초과 160° 이하). **세트 기준 높이가 자동으로 함께 켜진다** |
| `REP_BOUNDARY_SIGNAL` (`light`/`raw`) | 5. 평활이 봉우리를 깎음 | 반복 경계(내려감·복귀)만 가벼운 평활(min_cutoff 4.0) 또는 원본 무릎각으로 판정한다. 잠금 정책의 STANDING 판정과 최저점은 기존 평활값 그대로 |
| `BODY_LOCK_RELEASE_GRACE_SECONDS` (예: 0.6) | 2. 세트 중간 잠금 해제 | 비측면이 이어져 잠금을 푸는 기준 0.4 s에 이 시간을 더한다 |

## 재생 방법

```
python -m scripts.analysis.replay_flags --matrix --markdown               # fixture 세션 1~5, 7, 8a~8c
python -m scripts.analysis.replay_flags --matrix --sessions 6 9           # 사선·정면·방향 반전
python -m scripts.analysis.replay_flags --log data/landmark_sequences/<재현 로그>.jsonl --matrix
python -m scripts.analysis.replay_flags --set-baseline --return-angle 155 --lock-grace 0.6 --boundary light --log <로그>
```

프리셋: off(기본) / baseline(세트 기준 높이) / return155(복귀 155°) / light / raw(경계 신호) / grace0.6(잠금 유예 0.6 s) / all(baseline+return155+light+grace0.6).

## 결과 (fixture 세션 1~5, 7, 8a~8c)
센 횟수/실제 횟수. Δ = 꺼짐(기본)과 센 반복이 다름(개수 또는 시작 시각 0.5초 초과 차이).
| 세션(노트) | off | baseline | return155 | light | raw | grace0.6 | all |
|---|---|---|---|---|---|---|---|
| 1(parallel) | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| 2(deep) | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| 3 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| 4 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| 5 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| 7 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |
| 8a(nonsquat_walk) | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| 8b(nonsquat_chair) | 3/? | 3/? | 3/? | 3/? | 2/? Δ | 3/? | 3/? |
| 8c(nonsquat_lunge_stretch) | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |

| 프리셋 | 탈락 사유 합계(세션 전체) | 잠금 해제 합계 | 합쳐짐 의심 합계 |
|---|---|---|---|
| off | feet_apart=4, other_exercise=18, shallow_hip_drop=15, too_short=15 | 10 | 0 |
| baseline | feet_apart=4, other_exercise=18, shallow_hip_drop=15, too_short=15 | 10 | 0 |
| return155 | feet_apart=4, other_exercise=18, shallow_hip_drop=15, too_short=15 | 10 | 0 |
| light | feet_apart=4, other_exercise=18, shallow_hip_drop=15, too_short=15 | 10 | 0 |
| raw | feet_apart=3, other_exercise=18, shallow_hip_drop=14, too_short=15 | 10 | 6 |
| grace0.6 | feet_apart=4, other_exercise=19, shallow_hip_drop=15, too_short=16 | 5 | 0 |
| all | feet_apart=4, other_exercise=19, shallow_hip_drop=15, too_short=16 | 5 | 0 |

## 추가 세션 (사선 6, 방향 반전 9)
센 횟수/실제 횟수. Δ = 꺼짐(기본)과 센 반복이 다름(개수 또는 시작 시각 0.5초 초과 차이).
| 세션(노트) | off | baseline | return155 | light | raw | grace0.6 | all |
|---|---|---|---|---|---|---|---|
| 6 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |
| 9(facing_reversed) | 6/? | 6/? | 6/? | 6/? | 6/? | 6/? | 6/? |

## 해석
- **정확도 세션(1~5)은 모든 플래그에서 센 횟수와 반복 시작 시각이 그대로다.** 이 fixture는 반복 사이에 0.9~2.5 s 휴지가 있어 직전 1초 기준 높이와 160° 복귀가 모두 충분히 확보된 데이터라, 대응안이 정상 반복을 건드리지 않는다는 회귀 확인일 뿐 **누락이 줄어드는지는 이 데이터로 확인할 수 없다.**
- 세션 7(정면)·6(사선)은 측면이 아니라 어느 설정에서도 0회다. 걷기(8a)·런지(8c)는 어느 플래그에서도 세지 않는다.
- 세션 8b(의자 앉았다 일어나기, 알려진 한계로 세는 동작)만 `raw`에서 3회→2회로 바뀐다. 두 번째 반복(21.4 s)이 이웃 반복과 합쳐졌다(탈락 사유 없음). 원본 신호는 요동이 커서 반복 경계가 흔들린다.
  합쳐짐 의심(진단 이벤트)도 `raw`에서만 생기며 6건 모두 런지(8c)에서 나왔다. 정확도 세션(1~5)에서는 `raw`도 영향이 없지만, 잡음이 있는 신호를 경계에 쓰는 것이라 `raw`보다 `light`가 안전한 후보다.
- 잠금 유예 0.6 s: 잠금 해제가 10회→5회로 줄고(세션 1: 2→0, 세션 3: 1→0, 8a: 1→0 등) 센 반복은 모든 세션에서 같다. 부작용으로 **잠금이 더 오래 유지되어 세션 2의 끝 구간 이동이 반복 후보가 되나, 길이(too_short)와 ML(other_exercise)로 탈락한다**(센 횟수에는 영향 없음, 탈락 후보 +1).
- 합성 연속 세트(`tests/test_rep_flags.py`)에서는 기본 설정이 7회 중 1회만 세는 상황(봉우리 158° 또는 봉우리에서 엉덩이가 0.12 낮은 세트)을 각각 복귀 155°, 세트 기준 높이를 켜면 7회로 센다. 실제 효과는 연속 세트 재현 로그로 확인해야 한다.
