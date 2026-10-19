# v0.2.0 DEVLOG

> 내부 기록용. 추가 전용(append-only): 이전 항목은 수정하거나 지우지 않는다.
> 결정이 바뀌면 새 항목에 "변경: 이전 결정 → 새 결정, 이유"로 남긴다.

---

## 2026-10-12 · Phase 0 — 사전 확인

### 수행 내용
- 저장소의 버전 문자열 위치 조사
- 0.1.0 / 0.1.1의 기존 문서·태그·CHANGELOG 존재 여부 확인
- v0.2.0 문서 골격 생성 (`docs/versions/v0.2.0/DEVLOG.md`, `RELEASE.md`, 루트 `CHANGELOG.md`)
- 분석 대상 데이터(`data/processed/polar_mediapipe/dataset.csv`, `failed_samples.csv`) 위치 확인

### 버전 문자열 위치
| 위치 | 값 | 컴포넌트 | 비고 |
|---|---|---|---|
| `installer/FitRouteAIClient.iss:3` (`MyAppVersion` 기본값) | 0.1.0 | Windows Installer (AI Client + Launcher) | 빌드 시 `/DMyAppVersion=`으로 덮어씀 |
| `installer/build_installer.ps1:5` (`$Version` 기본값) | 0.1.0 | Installer 빌드 스크립트 | 릴리스 시 `-Version` 인자로 전달 |
| `installer/validate_installer_inputs.py:24` (`DEFAULT_VERSION`) | 0.1.0 | Installer 입력 검증기 | `--version` 기본값. `.iss` 기본값과 일치 검증 로직(130행 부근)이 있어 함께 올려야 함 |
| `installer/installer_manifest.json:4` | 0.1.1 | Installer 빌드 산출 manifest | 빌드 시 `--write-manifest`로 재생성되는 산출물 |
| `releases/windows/production.json:2` | 0.1.1 | 현재 Production 포인터 | **promote 단계에서만 변경**. 릴리스 전 수정 금지 |
| `releases/windows/v0.1.1.json` | 0.1.1 | 불변 release metadata | 수정 금지. 0.2.0은 `release_windows.ps1`이 `v0.2.0.json`을 새로 생성 |
| `frontend/package.json:4`, `package-lock.json:3,9` | 0.1.0 | Frontend | 웹 앱 버전. AI Client 변경과 무관 |
| `scripts/release_windows.ps1`, `promote_windows_release.ps1` | (인자) | 릴리스 자동화 | 버전은 `-Version` 인자로 받음. 하드코딩 없음 |

- `src/`, `config/`, `backend/app/`, `desktop_launcher/`에는 `__version__` 또는 버전 상수가 **없음**.
- `pyproject.toml`, `setup.py`는 **없음**.
- 설치된 AI Client가 자기 버전을 런타임에 알 수 있는 경로는 현재 없음 (Installer 메타데이터에만 존재).

### 기존 버전 문서 현황
- `git tag -l` 결과: **태그 없음** (v0.1.0, v0.1.1 모두 미생성. `release_windows.ps1`이 태그 명령만 출력하는 방식)
- `CHANGELOG.md`: **없음**
- `docs/versions/`: **없음**
- 버전 이력은 `README.md`의 Version History 표(v0.1.0, v0.1.1), `docs/windows_release_process.md`, `releases/windows/v0.1.1.json`에만 존재
- v0.1.0 metadata는 저장소에 없음 (`docs/windows_release_process.md`에 명시)
- 과거 버전 문서는 임의로 만들지 않음. CHANGELOG의 0.1.0/0.1.1 항목은 README Version History 표 기준 요약안을 Phase 5에서 제안.

### 분석 데이터 위치 확인 — 미해결
- 저장소에 `data/processed/`가 없음 (`data/`에는 `workout_logs/`만 존재).
- `Documents/`, `Downloads/`, `Desktop/` 아래에서 `dataset.csv`, `failed_samples.csv`를 찾지 못함.
- `Documents/GitHub/` 내 다른 저장소(`subway-crowding-route`)에는 무관한 `data/processed/`만 있음.
- **Phase 0의 1~4번 분석은 데이터 경로 확인 전까지 진행 불가.**

### 결정과 근거
- 분석 스크립트를 컬럼 구조를 보지 않고 작성하면 추측이 되므로, 데이터 확인 후 작성한다. (확신 높음)

### 시도했다가 버린 접근
- 없음

### 임계값 변경 이력
- 없음

### 테스트 결과
- 해당 없음 (코드 변경 없음)

### 남은 문제
- 데이터 파일 경로 필요
- 학습 파이프라인의 정확한 위치(별도 저장소 추정)와 6개 메타 컬럼 정의 확인 필요

---

## 2026-10-12 · Phase 0 — 학습 데이터 분석 (데이터 확보 후, 위 "미해결" 해소)

### 데이터 출처 (경로는 이 PC 기준. 원본은 읽기 전용, 저장소로 복사하지 않음)
기준 폴더: `D:\LDH_PRG_CV\2_vision_ai\Pose_actionrecognition\data` (별도 학습 저장소)

| 파일 (`processed/polar_mediapipe/`) | 행 수 | 크기(bytes) | 수정일 |
|---|---|---|---|
| dataset.csv | 33,994 | 88,744,868 | 2026-09-11 14:09:57 |
| failed_samples.csv | 1,330 | 97,601 | 2026-09-11 14:09:57 |
| classes.json | 9 클래스 | 110 | 2026-09-11 13:41:24 |

- classes.json 순서는 FitRoute `models/classifier/classes.json`과 동일 (squat, run, sit, stretch, walk, jump, bendover, stand, lying).
- 같은 폴더의 `extraction_summary.json`: MediaPipe 0.10.35, `pose_landmarker_full.task`, bbox padding 0.30, 검출/존재 confidence 0.20. FitRoute 런타임(`config/settings.py`)과 같은 padding·confidence.
- 추출 스크립트: 학습 저장소 `02_extract_mediapipe_landmarks.py` (crop 복원식의 근거).
- 분석 스크립트: `scripts/analysis/polar_squat_angle_analysis.py` (`--data-dir` 필수, 기본값 없음. 누락 시 argparse 에러로 종료함을 확인).
  실행: `python scripts/analysis/polar_squat_angle_analysis.py --data-dir <data 폴더>` (conda `vision_ai` 환경, 파일 약 10만 개를 읽어 약 10분 소요)
- 결과물: `docs/versions/v0.2.0/analysis/` (phase0_report.md, knee_angle_hist.png, side_ratio_hist.png, knee_angle_percentiles.csv, failed_by_class.csv)

### 1. 메타데이터 6개 컬럼
| 컬럼 | 의미 |
|---|---|
| sample_id | `{split}__{이미지 stem}__person_{n}` 고유키 (중복 없음) |
| image_name | 원본 이미지 파일명 `p1_NNNNN.jpg` (행마다 고유: 33,994 / 33,994) |
| person_index | 한 이미지 안의 사람 번호. **전부 0** |
| split | train 20,397 / val 6,808 / test 6,789 |
| class_id | 0~8 (classes.json 인덱스) |
| label | 클래스명 |

이후 132 feature = 33 landmark × (x, y, z, visibility). 컬럼 구조는 FitRoute `pose_classifier.py`의 `EXPECTED_FEATURE_NAMES`와 같다.

- **시간 순서 정보: 없음.** 영상 ID·프레임 번호 컬럼이 없고, `p1_NNNNN`은 전체 이미지에 매긴 일련번호(정지 이미지 데이터셋)다. Annotations JSON의 `originalname`(예: `[stand]_getty_p8_...jpg`)도 스톡 사진 파일명이라 시퀀스가 아니다.
  → **POLAR로는 반복 분할(RepTracker)의 동작을 검증할 수 없다.** 프레임 단위 각도 분포만 볼 수 있다. 시퀀스 검증은 합성 테스트와 Phase 4 실제 로깅 데이터에 의존한다.
- **crop 픽셀 w, h 복원: 가능, 검증 완료.** `labels/*.txt`(YOLO bbox) + `Annotations/*.json`(원본 width/height)에 학습 저장소와 동일한 padding 식(round-half-even, 경계 clamp)을 적용.
  검증: 성공+실패 합 35,324행의 crop 통계(w/h 각각 min/mean/max, 6개 값)가 `extraction_summary.json`과 **전부 일치**. 무작위 1,500장에서 annotation 크기와 `cv2.imread` 실제 크기도 모두 같았다(불일치 0, 가로세로 뒤바뀜 0).

### 2. 측면 필터
- 비율 = |왼쪽 어깨 x − 오른쪽 어깨 x| ÷ 어깨 중점~엉덩이 중점 거리. 모두 복원한 crop 픽셀 좌표(x·w, y·h)로 계산.
- 주 임계값 **0.35는 임시 초기값** (근거 없는 선택. 아래 분포 참고).

| 클래스 | 전체 | ≤0.25 | ≤0.35 | ≤0.50 |
|---|---|---|---|---|
| stand | 4,572 | 430 | 619 (13.5%) | 1,056 (23.1%) |
| squat | 3,943 | 688 | 956 (24.2%) | 1,391 (35.3%) |

- stand의 비율은 0.65 부근에 뚜렷한 봉우리(정면/비스듬한 사진이 대부분으로 추정), squat는 0~0.5 구간이 평평하고 0.85 부근에 또 하나의 봉우리. **측면과 비측면 사이에 깔끔한 골짜기가 없어** 임계값은 경계가 흐린 선택이다. (squat 시 몸통 기울기로 투영 길이가 줄어 비율이 커졌을 가능성은 검증하지 않음 — 확신 낮음)
- 측면 필터 후 표본이 stand 619, squat 956으로 줄어 백분위는 표본 수와 함께 봐야 한다.

### 3. 무릎각 분포 (가까운 쪽 다리 = hip+knee+ankle visibility 합이 큰 쪽, 단위 도)
| 클래스 | 부분집합 | n | p5 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| stand | 전체 | 4572 | 146.2 | 171.6 | 176.1 | 178.3 | 179.7 |
| stand | 측면(≤0.35) | 619 | 114.0 | 158.2 | 170.5 | 175.9 | 179.2 |
| stand | 측면+visibility≥0.5 | 382 | 135.1 | 161.9 | 172.3 | 176.7 | 179.4 |
| squat | 전체 | 3943 | 18.0 | 38.5 | 59.5 | 98.9 | 165.4 |
| squat | 측면(≤0.35) | 956 | 19.1 | 32.3 | 45.2 | 70.9 | 159.8 |
| squat | 측면+visibility≥0.5 | 691 | 21.8 | 31.7 | 42.1 | 58.3 | 110.1 |

(`측면+visibility`는 지시문에 없던 보조 부분집합: 다리·몸통 관절 visibility ≥ 0.5.) 히스토그램: `analysis/knee_angle_hist.png`

해석(이 데이터에서 읽히는 것만):
- **POLAR의 squat 클래스는 깊은 스쿼트에 치우쳐 있다.** 측면 기준 squat 중앙값 42~45°, 75퍼센타일 58~71°. 90~150°(하프 스쿼트 범위)에는 squat 표본이 적다. → 배경의 "하프 스쿼트가 squat로 분류되지 않을 가능성" 우려와 같은 방향의 증거. 다만 90~150° 구간의 정확한 비율은 계산하지 않았다.
- **stand 라벨도 무릎이 완전히 펴져 있지 않다.** 측면 stand의 p25가 158~162°, p5가 114~135°. 초기 임계값 STANDING ≥160°는 이 데이터의 측면 stand 약 25%를 "서 있음"으로 보지 않는다. POLAR 라벨 잡음일 수 있고 실제 신호와 다를 수 있어 **임계값 조정은 Phase 4 실측 이후로 미룬다.** (확신 낮음)
- 정지 이미지 분포라서 DESCENDING 진입(150°)·히스테리시스 값의 직접 근거는 되지 못한다.

**landmark가 crop(0~1) 밖에 있는 비율**: stand는 knee 24%, ankle 34%, squat는 knee 약 3%, ankle 약 7%. stand crop은 세로로 길고(높이 중앙값 457, h/w 중앙값 2.0) 다리가 crop 밖으로 외삽된 샘플이 많다. 원인은 확인하지 못했다(bbox가 발목에서 잘렸거나 MediaPipe 외삽 추정). 런타임도 같은 bbox+30% crop을 쓰므로 실제 환경에서도 생길 수 있다. → **Phase 1에서 landmark의 crop 이탈 여부를 신뢰도 조건에 포함할지 검토.** (추정, 확신 낮음)

### 4. failed_samples.csv 클래스 분포
실패 사유는 1,330건 전부 `pose_not_detected`. 전체 실패율 3.77% (1,330 / 35,324).

| 클래스 | 실패 | 실패율 | 실패 점유율 | 전체 샘플 점유율 |
|---|---|---|---|---|
| bendover | 353 | 9.13% | 26.5% | 10.9% |
| squat | 310 | 7.29% | 23.3% | 12.0% |
| lying | 191 | 5.33% | 14.4% | 10.1% |
| walk | 91 | 2.76% | 6.8% | 9.3% |
| sit | 105 | 2.06% | 7.9% | 14.4% |
| stretch | 67 | 2.02% | 5.0% | 9.4% |
| jump | 64 | 1.80% | 4.8% | 10.1% |
| stand | 84 | 1.80% | 6.3% | 13.2% |
| run | 65 | 1.76% | 4.9% | 10.4% |

- **squat에 실패가 몰려 있다**(점유율 23.3% vs 샘플 12.0%, 실패율은 평균의 약 1.9배). 다만 bendover가 더 높고, 세 클래스(bendover/squat/lying)가 실패의 64.2%를 차지한다(샘플 비중 33.1%). 몸이 접히거나 누운 자세에서 MediaPipe가 더 자주 실패하는 패턴.
- 실패한 squat의 crop은 성공보다 작고 납작하다(높이 p10 116 vs 203, h/w 중앙값 1.2 vs 1.3). split 분포는 train 203 / test 56 / val 51로 한쪽에 치우치지 않는다.
- 함의: POLAR squat 클래스는 "검출에 성공한 쉬운 squat"만 남은 표본이라 생존 편향이 있을 수 있다. (추정, 확신 낮음)

### 결정과 근거
- Phase 0 결론: **반복 분할을 무릎각 시계열로 하는 설계를 뒷받침하는 정황**(squat 클래스의 깊은 쪽 치우침, 정지 이미지라 시퀀스 검증 불가). 설계 결정은 변경하지 않음.
- 측면 임계값 0.35, visibility 0.5는 임시 초기값. 확정 근거 없음 (확신 낮음).
- 검증 대상 집합 착오: 처음에 dataset.csv(성공 33,994행)만으로 대조해 평균이 불일치(width_mean 290.90 vs 291.56 등)했으나, 요약 통계는 성공+실패 전체 기준이었다. 복원식 자체는 문제가 없었고, 스크립트의 대조 대상을 성공+실패로 고쳐 전부 일치함을 확인했다.

### 시도했다가 버린 접근
- 성공 샘플만으로 crop 통계를 대조 → 위 사유로 불일치처럼 보였음. 이미지 크기 불일치 가설(EXIF 회전 등)은 1,500장 표본으로 기각.

### 임계값 변경 이력
- 이번 Phase에서 settings.py 상수 변경 없음. 분석용 임시값만 사용: 측면 비율 0.35(민감도 0.25/0.50 병기), visibility 0.5.

### 테스트 결과
- 단위 테스트 없음(분석 스크립트만 추가, `src/` 변경 없음). `--data-dir` 누락 시 에러 종료 확인. crop 복원은 extraction_summary.json과 6개 통계 일치로 검증.

### 남은 문제
- 90~150° 구간 squat 비율 미계산 (하프 스쿼트 증거를 정량화하려면 추가 필요).
- stand crop의 landmark 이탈 원인 미확인.
- POLAR 이미지가 같은 촬영본의 연속 사진일 가능성(`originalname`의 `-002` 같은 접미사)은 확인하지 않음. split 간 누출과 관련될 수 있으나 이번 분석 범위 밖.

---

## 2026-10-12 · 버전 관리 결정 및 이력 확인

### 사용자 확정 결정
- 제품 버전 = AI Client Windows 릴리스 버전 (`releases/windows/` 기준). 이번 작업은 0.2.0.
- `frontend/package.json`, `package-lock.json`: 이번 작업에서 변경하지 않는다.
- `installer_manifest.json`: 직접 수정하지 않는다. 빌드가 갱신한다.
- `production.json`: 변경하지 않는다 (promote 단계 소관).
- Installer 기본값 3곳(`.iss`, `build_installer.ps1`, `validate_installer_inputs.py`): Phase 5에서 0.2.0으로 올린다.
- git 태그는 만들지 않는다.

### 기록: 0.1.1 때 Installer 기본값이 갱신되지 않았음
- 커밋 `6d8995b`(v0.1.1.json 생성 시점)에서도 `.iss`의 `MyAppVersion` 기본값은 `0.1.0`이다 (`a5113e1`, `3b5fff5`도 동일). `build_installer.ps1`, `validate_installer_inputs.py` 기본값도 현재 0.1.0이다.
- 그런데도 0.1.1 Installer가 만들어진 이유: `release_windows.ps1`이 `-Version` 인자를 `build_installer.ps1`로 넘기고, 이것이 `iscc /DMyAppVersion=<값>`으로 `.iss` 기본값을 덮어쓴다 (`build_installer.ps1:67`).
- **결론: 릴리스 버전의 기준은 `-Version` 인자**이며 세 기본값은 직접 실행할 때의 폴백이다. 0.1.1에서 실제로 갱신된 것은 빌드 산출물 `installer_manifest.json`(0.1.1)과 `releases/windows/v0.1.1.json`이다.

### 제안 (적용하지 않음): installer_manifest.json의 git 추적 제외
- 근거: 빌드마다 `--write-manifest`로 재생성되는 산출물이고(`build_installer.ps1:75`), `release_windows.ps1:116`은 빌드 직후 그 파일의 version을 요청 버전과 대조한다. 불변 기록은 이미 `releases/windows/v<VERSION>.json`(sha256 포함)이 맡는다.
- 반대 근거(확인 필요): `docs/windows_release_process.md:103`은 Prepare 후 이 파일을 검토하고 사용자가 직접 commit한 뒤 promote(clean working tree 요구)하도록 안내한다. 추적을 끊으면 이 절차와 clean-tree 검사가 달라질 수 있다.
- 제외하려면 문서와 promote 스크립트 확인이 선행되어야 한다. 이번 작업에서는 변경하지 않는다.

### v0.1.0 / v0.1.1에 해당하는 커밋 (태그 없음, 확정 불가 → 후보와 근거)
**v0.1.0 — 후보: `3b5fff5` (2026-09-15 08:53 +0900, "create_launcher+client_ai(exe)")**
- 근거: Installer 파일과 `installer_manifest.json`(version 0.1.0)이 처음 추가된 커밋. 이후 `8887f6e`(09:38, installer_recompile)가 `.iss`에 4줄을 추가했으나 manifest는 0.1.0 그대로다.
- 대안 후보: `8887f6e` (0.1.0 상태의 마지막 Installer 변경). 둘 중 무엇이 실제 배포 빌드인지는 저장소 정보만으로 확정할 수 없다.
- 한계: v0.1.0 release metadata(`v0.1.0.json`)가 저장소에 없어(`docs/windows_release_process.md`도 명시) 빌드 시각·해시로 대조할 수 없다.

**v0.1.1 — 후보: `a5113e1` (2026-09-15 16:22 +0900, "release_workflow"), 기록 커밋: `6d8995b` (16:55)**
- 근거: `releases/windows/v0.1.1.json`의 `built_at`은 2026-09-15T07:39:40Z = 16:39:40 +0900이다. 이는 release workflow 스크립트가 추가된 `a5113e1`(16:22) 이후, `v0.1.1.json`과 manifest 0.1.1이 커밋된 `6d8995b`(16:55) 이전이다. `6d8995b`는 이 두 파일만 변경(2 files)했으므로 빌드 시점의 코드는 `a5113e1` 상태일 가능성이 높다. (빌드 시 미커밋 변경이 있었는지는 확인 불가)
- Production 반영: `d071c72` (17:41, "Create production.json").
- 참고: 이후 `3e1d62d`(17:38)에서 release 스크립트가 다시 수정되어, `a5113e1` 시점의 스크립트와 현재 스크립트는 다르다.
- **0.1.0과 0.1.1은 AI Client 소스가 동일하다**: `src/`의 마지막 변경은 `37fcc7d`(2026-09-14 16:24)이고, `8887f6e`~`6d8995b` 사이 `src/`, `config/`, `desktop_launcher/`의 소스 변경은 없다(변경은 `desktop_launcher/installer/FitRouteAIClient.iss` 삭제와 `packaging/ai_client/trace_loaded_modules.py` 수정뿐). 즉 0.1.1은 AI 동작 변경이 아니라 release workflow 정식화 릴리스다 (README Version History와 일치).

---

## 2026-10-12 · Phase 0.5 — 추가 검증 (코드 변경 없음, Phase 1 보류)

### 수행 내용
- 분석 스크립트 추가: `scripts/analysis/polar_phase05_verification.py` (`--data-dir` 필수. Phase 0 스크립트의 crop 복원·각도 계산을 재사용). `src/`는 변경하지 않음.
- 결과물: `docs/versions/v0.2.0/analysis/phase05_report.md`, `overlays/` (구간별 contact sheet 5장 + 개별 40장), `overlay_samples.csv`
- 복원 함수 검증: 새 스크립트의 crop w,h가 Phase 0에서 extraction_summary와 일치가 확인된 함수와 무작위 2,000행에서 동일.
- 사용한 모델: FitRoute `models/classifier/model_weights.xgb`. 학습 저장소의 `model_weights.xgb`와 **SHA-256 동일**(93571ABF...A99D)함을 확인.
- 소요 시간 참고: 같은 PC에서 다른 프로젝트의 학습이 동시에 돌아 디스크 I/O가 느렸음(첫 단계 약 30분+). `--cache` 옵션으로 이후 재실행은 수 분.

### 0.5-1. 무릎각 시각 검증

**방법**: 측면 필터(비율 ≤ 0.35)를 통과한 샘플에서 구간별 8개 무작위(seed 0). 원본 이미지에 YOLO bbox, +30% crop, 사용한 다리의 hip-knee-ankle, heel/foot_index, 어깨를 그리고 종횡비 보정 후(corrected)·보정 전(raw) 각도를 같이 표기. 확대 창은 padded crop ±25%.

**교차 검증(계산 버그 확인)**
- arccos 구현과 별도로 만든 atan2 구현의 각도 차이: 선택한 40개 모두 최대 **0.000000°**.
- overlay의 관절선이 사람 몸 위에 정확히 겹침 → crop 좌표 → 원본 좌표 변환도 정상.
- 보정 전/후 차이는 실제로 큼: 측면 squat |Δ| 중앙값 4.05°, p95 19.3°, 최대 40.5° / 측면 stand 중앙값 9.25°, p95 39.4°, 최대 65.6°. 즉 종횡비 보정이 없으면 틀린 각도가 나오고, 현재 계산은 보정을 적용 중. 보정 전 기준 측면 squat 중앙값 41.2°, p5 15.6° / stand 중앙값 160.5°, p5 85.4° (Phase 0 표는 보정 후 값).

**판정 기준**: (a) 사선/후면/위에서 본 시점의 2D 투영 왜곡, (b) MediaPipe landmark 오류(다리가 사진에 없거나 가려진 곳을 추정, 몸과 안 맞는 위치), (c) 각도 계산/종횡비 보정 버그, 정상 = 관절선이 몸과 일치하고 각도가 기하학적으로 맞음.
**이 판정은 내가 이미지를 눈으로 본 주관적 분류이며 구간당 n=8이라 비율은 대략치다. (확신 낮음)**

| 구간 (측면 필터 후) | 정상 | (a) | (b) | (c) |
|---|---|---|---|---|
| squat < 30° | 6 | 1 | 1 | 0 |
| squat 30~70° | 6 | 1 | 1 | 0 |
| squat 90~150° | 2 | 0 | 6 | 0 |
| squat > 150° | 0 | 1 | 7 | 0 |
| stand < 158° | 3 | 0 | 5 | 0 |

표본별 판정 (파일명 `p1_NNNNN`, 괄호는 보정 후 각도):
- squat <30°: 정상 27691(19°) 34808(23°) 13058(24°) 05020(25°) 03334(25°) 24603(29°) / (a) 07069(28°, 뒤에서 본 아이) / (b) 31956(22°, 위에서 본 모자 쓴 사람, knee·ankle visibility 0.37·0.12)
- squat 30~70°: 정상 22563(38°, 저해상도) 28847(39°) 35068(39°) 20562(40°) 35248(43°) 33338(44°) / (a) 31579(54°, 위에서 본 아이) / (b) 29313(34°, 저해상도·ankle visibility 0.45, 판정 불확실)
- squat 90~150°: 정상 03158(110°, 바벨 백스쿼트 측면) 09143(133°, 코트 입고 쪼그린 여성) / (b) 01693(108°, 앞의 개 얼굴에 landmark) 14225(112°, 뒷모습, 어깨 landmark가 머리 쪽에 쌓임) 30753(123°, hip이 knee 위치에 붙음, visibility 0.14·0.21) 13146(128°, ankle이 장갑 낀 손 위치) 08725(148°, 정면, 다리 가려짐) 19328(150°, hip이 이미지 밖으로 외삽)
- squat >150°: (a) 02921(153°, 위에서 본 쪼그림) / (b) 31638(153°) 20534(153°) 30884(164°, heel/foot_index가 몸 밖) 28712(173°, 이미지 밖) 32501(174°) 26817(178°) 24845(180°, 이미지 밖). 8개 모두 실제 자세와 맞지 않는 각도.
- stand <158°: 정상 03774(136°, 걷는 중 무릎 굴곡) 14219(141°, 한쪽 무릎 살짝 굽힘) 05494(153°) / (b) 00525(97°, 하체가 사진에 없음) 26372(110°, 상반신만) 03230(115°, 상반신만, 다리 landmark가 이미지 밖) 04656(144°, 허리 아래 잘림) 19047(148°, 다리가 자동차에 가려짐)

**결론**
- **(c) 계산·보정 버그는 발견되지 않았다.** 따라서 Phase 0 분포를 다시 뽑을 필요 없음 (판정 기준상 (c) 0건, atan2 교차 검증 0° 차이).
- **p5=19°, p50=45°의 원인**: 낮은 각도는 대부분 실제 자세다(<30° 구간 6/8, 30~70° 구간 6/8 정상). POLAR의 squat는 헬스장 스쿼트가 아니라 **쪼그려 앉기(crouch)가 많고**, 발이 엉덩이 아래에 오는 깊은 쪼그림에서는 2D hip-knee-ankle 각이 20°대까지 내려간다. "완전 굴곡 30~40°" 가정은 이런 자세에는 맞지 않는다. 낮은 쪽 분포는 신뢰해도 된다고 판단.
- **높은 쪽 꼬리는 landmark 오류가 대부분**이다. squat 90~150°는 8개 중 6개, 150° 초과는 8개 전부가 (a)/(b)로 판정. stand <158°도 8개 중 5개가 (b)(하체가 사진에 없거나 가려져 MediaPipe가 추정).
- (a) 시점 문제는 소수(squat 3/32)지만, 측면 필터(어깨 간격 비율)를 통과한 위에서 본 시점·뒷모습이 섞여 있어 **이 비율 기반 필터만으로는 측면 판별이 불충분**하다. (확신 낮음: 표본 3건)

### 0.5-2. 90~150° 구간 비율 (90 ≤ 무릎각 < 150)

| 클래스 | 범위 | n | <90° | 90~150° | ≥150° |
|---|---|---|---|---|---|
| squat | 측면 | 956 | 81.8% | **11.1% (106)** | 7.1% |
| squat | 측면+전신유효 | 538 | 91.6% | 6.9% (37) | 1.5% |
| squat | 전체 | 3,943 | 70.7% | 20.0% (787) | 9.4% |
| stand | 측면 | 619 | 2.7% | **13.9% (86)** | 83.4% |
| stand | 측면+전신유효 | 317 | 0.9% | 10.4% (33) | 88.6% |
| stand | 전체 | 4,572 | 1.0% | 5.0% (230) | 93.9% |

(`전신유효` 정의는 0.5-3 참고.) 0.5-1에서 90~150° squat의 대부분이 landmark 오류로 판정됐고, 이 비율도 전신유효 필터 후 11.1% → 6.9%로 줄어든다. 즉 **POLAR의 squat 클래스에는 실제 하프 스쿼트 표본이 거의 없다.**

**XGBoost 예측과 무릎각 구간 (측면 필터 후, 모든 정답 라벨, test split 우선)**
- 무릎각 90~150° 샘플(test n=483)의 정답 라벨은 bendover 18%, run 18.6%, lying 14.7%, jump 14.3%, sit 12.6%, stretch 6.4%, walk 7.9%, **squat 4.8%**, stand 2.7%. XGBoost 예측 중 squat는 **2.1%** (전체 split n=2,481에서 3.6%).
- 정답이 squat인 90~150° 샘플(test n=23)의 예측: **squat 17.4%**, bendover 47.8%, sit 17.4%, stretch 13.0%, lying 4.3%. 전체 split(n=106)에서는 squat 67.0%인데, train 샘플이 섞여 모델이 외운 효과가 있어 test만 신뢰한다.
- 정답이 squat인 60~90° (test n=37): squat 73.0%, sit 13.5%, bendover 10.8%. 0~60° (n=140): squat 90.0%, sit 5.0%.

**하프 스쿼트 판정 가능성 추정 (확신 낮음)**
- 이 데이터로는 신뢰할 수 있는 추정이 불가능하다. 90~150° squat 표본(test 23개)이 적고, 그 대부분이 landmark 오류라 "예측 실패"가 하프 스쿼트 때문인지 landmark 오류 때문인지 분리되지 않는다.
- 다만 방향성은 분명하다: **무릎각이 90~150°일 때 XGBoost가 squat로 답하는 경우는 드물다(2~4%).** 무릎각이 얕아질수록 squat 확률이 떨어지고(0~60° 90% → 60~90° 73% → 90~150° 17%), 예측이 틀릴 때는 **bendover/sit로** 간다. 하프 스쿼트 깊이에서 "squat" 라벨에 의존하면 반복을 놓칠 가능성이 높다. → 반복 분할을 라벨이 아닌 무릎각으로 한다는 설계 결정과 일치.
- 실제 하프 스쿼트에서의 동작은 Phase 4 로깅 데이터로만 확인 가능.

### 0.5-3. stand의 crop 이탈 원인

이탈 = 가까운 쪽 다리의 knee 또는 ankle이 crop(0~1) 밖.

| 클래스 | 그룹 | n | bbox 하단 접촉 | bbox 어느 경계든 접촉 | ankle이 crop 아래 | ankle visibility 중앙값 |
|---|---|---|---|---|---|---|
| stand | 이탈 | 1,575 (34.4%) | **73.9%** | 77.7% | 99.6% | **0.04** |
| stand | 이탈 아님 | 2,997 | 8.8% | 11.9% | 0.0% | 0.96 |
| squat | 이탈 | 302 (7.7%) | 61.6% | 79.5% | 85.4% | 0.29 |
| squat | 이탈 아님 | 3,641 | 7.8% | 15.7% | 0.0% | 0.85 |

(bbox 접촉 = 원본 YOLO bbox가 이미지 경계에 ±1px 이내. 그 밖에 padded 클램프, 방향별 비율 등은 phase05_report.md.)

- **가설 확인**: stand 이탈 샘플은 거의 전부(99.6%) ankle이 crop **아래**로 나가고, 73.9%는 bbox 하단이 이미지 경계에 닿는다(비이탈은 8.8%). ankle visibility 중앙값도 0.04(비이탈 0.96). 사진에서 다리가 잘려서 MediaPipe가 다리를 외삽한 경우가 대부분이라는 가설과 일치. 이탈이지만 bbox가 하단에 닿지 않는 약 26%는 사진 안에서 다리가 가려진 경우(0.5-1의 자동차·테이블 가림)로 추정.
- **이탈 제외 후 stand 분포** (p5/p25/p50/p75/p95):

| 부분집합 | n | p5 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|
| 전체 | 4,572 | 146.2 | 171.6 | 176.1 | 178.3 | 179.7 |
| crop 안(이탈 제외) | 2,997 | 147.4 | 171.7 | 176.0 | 178.2 | 179.6 |
| 전신유효 | 2,109 | 153.6 | 172.8 | 176.3 | 178.4 | 179.7 |
| 측면 | 619 | 114.0 | 158.2 | 170.5 | 175.9 | 179.2 |
| 측면 + crop 안 | 442 | 118.4 | 160.3 | 171.6 | 176.5 | 179.3 |
| 측면 + 전신유효 | 317 | 136.6 | 163.4 | 172.6 | 176.6 | 179.4 |

  `전신유효` = near leg의 hip/knee/ankle/heel/foot_index가 모두 crop 안 + bbox가 이미지 경계에 닿지 않음 + 해당 관절 visibility ≥ 0.5 (**임시 기준**).
- 해석: 전체 분포에서는 이탈 제외 효과가 작다(외삽된 다리도 대체로 곧게 추정돼 176°에 몰림). 하지만 측면 필터 후에서는 하위 꼬리가 달라진다(p5 114.0 → 136.6, p25 158.2 → 163.4). **초기 임계값 STANDING ≥160°에 대해**: 전신이 유효한 측면 stand의 p25가 163.4°이므로 약 75% 이상이 160° 이상이다. Phase 0 때의 "stand의 약 25%가 160° 미만"은 상당 부분 landmark 이탈 때문이었다. 단 n=317로 작고 POLAR는 정지 사진이라 확정 근거는 아니다. (확신 낮음)
- squat도 전신유효 필터를 적용하면(측면+전신유효 n=538) p5 21.6 / p25 31.6 / p50 40.2 / p75 55.8 / p95 101.5°로 낮은 쪽에 더 몰린다(Phase 0의 측면 p50 45.2°). 측면 필터를 통과한 샘플 중 전신유효를 만족하는 비율은 stand 51%(317/619), squat 56%(538/956).

### 0.5-4. 기존 코드의 비스쿼트 라벨 처리 (코드 읽기만)

**1. 라벨 흐름** (`src/main.py`)
| 순서 | 위치 | 내용 |
|---|---|---|
| 1 | `main.py:636-640` | `update_primary_person_smoothing()` → `smoothing_state` (PredictionSmoother 출력) |
| 2 | `main.py:645` | `stable_pose = smoothing_state["stable_label"]` — 원래 라벨 그대로 |
| 3 | `main.py:646` | `exercise_counter.update(stable_pose, current_time)` — **필터 없이** 카운터 입력 |
| 4 | `main.py:647-652` | `update_display_pose(stable_pose, ...)` — `ALLOWED_DISPLAY_POSES`(`main.py:51`) 적용 지점. 결과는 `display_pose`에만 저장 |
| 5 | `main.py:667-675` | `display_pose`가 `compose_workout_ui`로 전달되어 **화면 렌더링에만** 사용 |

- `ALLOWED_DISPLAY_POSES = {"stand","squat","stretch"}`는 카운터 입력 경로에 **없다.** 같은 `stable_pose`에서 갈라진 별도 분기(표시 전용)이며, 허용되지 않은 라벨은 카운터에서 값이 바뀌지 않고 원래 라벨 그대로 들어간다. 표시 쪽은 허용 외 라벨이면 직전 표시값을 유지(`main.py:234-236`).
- PredictionSmoother(`prediction_smoother.py:30-57`)는 다른 라벨이 연속 3프레임(jump 2프레임, `config/settings.py:33-36`) 나와야 stable이 바뀐다. Pose 미검출이 3프레임 초과(`MISSING_POSE_TOLERANCE_FRAMES=3`)면 `stable_label=None` (`prediction_smoother.py:66-68`)이고 카운터는 `None`을 받는다.

**2. ExerciseCounter 상태별 동작 (SQUAT 모드)** (`exercise_counter.py:96-113`)
| 상태 | stand | squat | walk/run/jump/lying/sit/bendover/stretch | None(미검출) |
|---|---|---|---|---|
| WAITING_STAND (`:98-101`) | → WAITING_SQUAT | 무시 | **무시** | 무시 |
| WAITING_SQUAT (`:104-107`) | 무시 | → WAITING_RETURN_STAND | **무시** | 무시 |
| WAITING_RETURN_STAND (`:110-113`) | **count +1**, → WAITING_SQUAT | 무시 | **무시** | 무시 |

- 상태 리셋, 반복 무효화, 타임아웃은 **코드에 없다.** 라벨로 상태를 되돌리는 경로가 없고, 상태가 바뀌는 건 위 표의 전이와 `set_mode`/`reset_*`(`:27-39, :50-67`) 뿐이다.
- 결과: `stand → squat → (walk/run/jump/lying/sit... 얼마든지) → stand`도 1회로 센다. `squat` 후 사용자가 자리를 떠나 Pose가 미검출이 되어도 `WAITING_RETURN_STAND`가 유지되어, 몇 분 뒤 돌아와 `stand`가 되면 count가 올라간다.
- 참고: count 후 상태는 WAITING_STAND가 아니라 `WAITING_SQUAT`(`:113`)이다. 즉 두 번째 반복부터는 `stand`를 다시 확인하지 않고 `squat`만 나오면 진행한다 (`test_two_squats`는 이 경우도 통과).

**3. 테스트 검증 범위** (`tests/test_exercise_counter.py`)
- 있음: 정상 1회(`:27`), squat 유지 시 1회(`:34`), stand 없이 시작 불가(`:41`), 2회(`:58`), **stretch 라벨 무시** — `stand → stretch → stretch`에서 count 0이고 이후 `squat → stand`가 1회(`:48-55`). 즉 WAITING_SQUAT 상태에서 `stretch` 하나를 무시함만 검증.
- **없음**: walk/run/jump/lying/sit/bendover 라벨 테스트 0건. WAITING_STAND·WAITING_RETURN_STAND 상태에서 다른 라벨이 들어오는 경우 0건. `None` 입력 0건. 반복 중간 이탈 후 복귀가 count되는지에 대한 테스트 0건.
- 표시 필터는 `tests/test_camera_ui.py:17-27`에서 검증(허용 외 6개 라벨은 이전 표시 유지). 카운터와는 별개.

**4. 결론 분류: "표시 필터가 카운터 뒤에 있고(독립 분기, 표시 전용), 카운터가 다른 라벨을 무시함(배제 없음)"**
- 엄밀히는 필터가 카운터의 앞도 뒤도 아니라 같은 입력에서 갈라진 표시 전용 분기이며, 카운터에는 원래 라벨이 들어간다.

**5. RepTracker의 다른 운동 배제 조건 제안 (제안만, 구현 안 함)**
- **입력 위치**: `main.py:645`의 `stable_pose`(원래 stable 라벨)를 RepTracker에 무릎각·타임스탬프와 함께 전달한다. `update_display_pose`(`main.py:647`)의 결과는 쓰지 않는다 (stand/squat/stretch 외 라벨이 이전 값으로 덮이므로 배제 판단 불가).
- **형태**: 반복 구간(DESCENDING 진입 ~ STANDING 복귀) 동안 stable 라벨별 **누적 시간**(프레임 수가 아닌 타임스탬프 기준)을 모으고, 반복 확정 시 다른 운동 라벨(`walk, run, jump, lying`) 시간 비율이 `≤ Y`일 때만 확정한다. 초과 시 반복을 폐기하고 사유(`other_exercise`)를 RepResult에 남긴다. `None`(미검출) 구간은 분모에서 제외하고 별도 필드(`pose_missing_ratio`)로 기록한다. Y는 `settings.py` 상수로 노출, 초기값은 Phase 4 로그로 정한다 (현재 근거 없음).
- **제외 라벨에 `sit`, `bendover`는 넣지 않는 것을 권장**: 0.5-2에서 정답이 squat인 샘플이 틀릴 때 `bendover`(0~60°에서 1%, 60~90° 10.8%, 90~150° 47.8%), `sit`(5.0% / 13.5% / 17.4%)로 가는 경우가 많다. 이 두 라벨을 배제하면 실제 스쿼트 반복이 탈락한다. `stretch`도 허용(표시 필터와 동일하게 운동 중 가능한 동작).
- 하단에서 라벨이 흔들리는 현상(squat 구간에 라벨이 순간 `sit`·`bendover` 등으로 바뀜)은 PredictionSmoother의 3프레임 확인이 일부 거르지만, 하단 정지 구간이 길면 stable 라벨 자체가 바뀔 수 있다. 위 비율 방식은 이 경우에도 `sit`/`bendover`를 배제하지 않으므로 영향이 없다.
- `ExerciseCounter`의 다른 운동(stretch) 동작은 변경하지 않는다. 스쿼트 모드에서만 RepTracker가 `squat_count`를 갱신하도록 하는 인터페이스는 Phase 2 착수 전에 따로 설명한다 (지시 사항 유지).

### v0.1.x의 한계 (RELEASE.md 반영 후보)
- 카운터가 `squat`/`stand` 외 라벨을 **무시만 하고 배제하지 않는다.** `stand → squat → 임의의 다른 동작 → stand`도 1회로 센다.
- 반복 중간 이탈에 대한 타임아웃·무효화가 없다. 사용자가 사라져도 `WAITING_RETURN_STAND`가 유지되어 이후 `stand`에서 count가 올라갈 수 있다.
- 스쿼트 깊이·자세 품질을 전혀 보지 않는다. 판정은 XGBoost 라벨 전이뿐이다.
- 관련 테스트가 비스쿼트 라벨 중 `stretch` 1개만 다룬다 (walk/run/jump/lying/sit/bendover 0건).
- 이 한계는 코드 읽기로 확인한 것이며, 실제 운영 중에 얼마나 오카운트가 났는지는 측정하지 않았다.

### 변경 예정 (확정 아님 — 사용자 확인 후 확정)
1. **Phase 2의 ML 보조 조건**
   - 이전: 반복 구간 내 squat 라벨 비율 ≥ X
   - 변경 예정: 반복 구간 내 **다른 운동 라벨(walk, run, jump, lying) 비율 ≤ Y** (표시 필터 적용 전 원래 라벨 기준)
   - 이유: POLAR squat 분포가 깊은 자세에 치우쳐 있어(0.5-2: 측면 전신유효 squat의 91.6%가 90° 미만) 이전 조건은 얕은 반복을 탈락시킨다.
   - 근거: 0.5-2(무릎각 90~150°에서 XGBoost의 squat 예측은 2~4%, 정답 squat도 test 기준 17%만 squat로 예측 → 얕은 반복은 squat 라벨 비율로 확인 불가), 0.5-4(카운터는 현재 다른 라벨을 배제하지 않음 → 배제 조건은 새로 필요, 원래 라벨은 `main.py:645`에서 얻음, 표시 필터 이후 값은 못 씀).
   - 부가: `sit`/`bendover`는 배제 라벨에서 제외 권장(0.5-4 제안 참고).
2. **Phase 1에 전신 가시성 검사 추가**
   - hip/knee/ankle/heel/foot_index가 crop 안에 있고 visibility가 기준 이상이며, YOLO bbox가 프레임 경계에 닿지 않을 때만 각도를 유효로 처리. 무효이면 품질 판정을 하지 않고 "전신이 보이게 서주세요" 표시.
   - 근거: 0.5-3 (stand의 34.4%가 knee/ankle crop 이탈, 그중 73.9%가 bbox 하단 접촉, ankle visibility 중앙값 0.04 vs 0.96) + 0.5-1 (squat >150° 8/8, 90~150° 6/8, stand <158° 5/8이 landmark 오류).
   - 기준값(visibility 0.5, bbox 경계 허용 오차 ±1px)은 임시 초기값. POLAR 정지 사진에는 해당 조건을 만족하는 측면 표본이 적어(측면 stand 51%, squat 56%만 만족) 기준 조정 근거로는 약하다. Phase 4 로그로 재검토.
3. **측면 시점 판별 시점**
   - STANDING 상태(반복 시작 시점)에서만 판별하고 반복 중에는 결과를 고정. 사용할 다리 선택도 같은 시점에 고정.
   - 근거: 0.5-1에서 측면 필터를 통과한 위/뒤에서 본 샘플(squat 3/32) 확인. 어깨 간격 비율만으로 시점을 판별하면 쪼그린 자세에서 몸통 투영 길이가 줄어 불안정하므로, 직립 상태에서 판별해 고정하는 것이 적합하다. (확신 낮음: 쪼그림 자세에서의 불안정은 가설이며 측정하지 않음)
4. 위 3가지와 별개로 **측면 판별 방식 자체가 어깨 비율만으로 충분한지는 미확정**이다. 0.5-1에서 비율을 통과한 비측면 샘플이 확인되었고 비율 분포에도 깔끔한 경계가 없었다(Phase 0). 대안(예: hip·knee·ankle의 z/깊이 정보, 어깨-엉덩이 선의 기울기 등)은 아직 검증하지 않았다.

### 버전 관련 (사용자 확정)
- `installer_manifest.json`: git 추적 유지. 현재 문서화된 Prepare/promote 절차(`docs/windows_release_process.md:103`)를 바꾸지 않는다. 위 "git 추적 제외 제안"은 **철회**한다.
- v0.1.0/v0.1.1 커밋 후보 기록은 현재 상태로 충분.

### 결정과 근거
- (c) 버그 없음 → Phase 0 분포 재산출 불필요. Phase 0 표의 해석만 보정(낮은 각도는 실제 자세, 높은 각도 꼬리는 landmark 오류).
- 설계 결정(반복 분할은 무릎각 시계열, ML 라벨은 보조)은 유지하며 보조 조건 방식만 위 "변경 예정"으로 제안.

### 시도했다가 버린 접근
- overlay를 전체 이미지 + 여백으로 그린 첫 버전은 사람이 작아 관절선을 구분하기 어려워, 사람이 있는 crop ±25% 확대 창으로 바꿨다 (스크립트 수정 후 재실행).
- 병렬로 보낸 편집 중 하나가 훅에 막혀 일부만 적용되어 `NameError`가 났고, 나머지를 다시 적용해 해결했다.

### 임계값 변경 이력
- `settings.py` 상수 변경 없음. 분석용 임시값만 사용: 측면 비율 0.35, visibility 0.5, bbox 경계 허용 ±1px, 전신유효 기준(위 정의).

### 테스트 결과
- 단위 테스트 없음(분석 스크립트만 추가). `src/`·`tests/` 변경 없음이므로 기존 테스트 영향 없음(이번 단계에서 실행하지는 않았다).
- 분석 스크립트 내부 검증: crop 복원 일치, atan2 독립 구현 대비 최대 차이 0.000000°.

### 남은 문제
- overlay 판정은 눈으로 본 주관적 분류, 구간당 n=8. 비율은 대략치.
- 하프 스쿼트의 XGBoost 판정 가능성은 POLAR로 정량화 불가. 실제 하프 스쿼트 영상 로깅이 필요(Phase 4).
- 측면 판별 방식의 대안 미검증.
- POLAR가 스톡 사진 중심이라 실제 웹캠 환경 분포와 다를 수 있음.

---

## 2026-10-12 · 설계 확정, Phase 순서 변경, Phase 3 계획 교체 (Phase 0.5 결과 확인 후)

사용자가 Phase 0.5 결과를 확인하고 아래를 확정했다. 위 "변경 예정" 항목들이 이 항목으로 **확정**된다.

### 확정 (이전 "변경 예정" → 확정)
1. **ML 보조 조건** (변경 예정 1 → 확정)
   - 입력: `main.py:645`의 원래 stable 라벨(표시 필터 적용 전).
   - 반복 구간의 라벨별 누적 시간(타임스탬프 기준)을 집계하고, `walk, run, jump, lying` 누적 비율 ≤ Y일 때만 반복을 확정한다. Y는 `settings.py` 상수, **초기값은 임시**.
   - `sit`, `bendover`는 배제 목록에서 제외한다(실제 squat가 오분류되는 대상이므로. 0.5-2: 정답 squat의 예측이 틀릴 때 bendover/sit로 감).
   - `stretch`는 **미정**. 배제 목록에 넣지 않고, Phase 4 로그의 반복 구간 라벨 분포를 본 뒤 결정한다.
   - 이전 조건("squat 라벨 비율 ≥ X")은 폐기.
2. **전신 가시성 검사** (변경 예정 2 → 확정): hip/knee/ankle/heel/foot_index가 crop 안에 있고 visibility가 기준 이상이며 YOLO bbox가 프레임 경계에 닿지 않을 때만 각도를 유효로 처리. 무효이면 품질 판정을 하지 않는다. 기준값(visibility 0.5, 경계 허용 ±1px)은 임시 초기값.
3. **측면 판별 시점** (변경 예정 3 → 확정): STANDING 상태(반복 시작 시점)에서 판별하고 반복 중에는 결과를 고정한다. 사용할 다리 선택도 같은 시점에 고정.
4. **측면 판별 방식** (변경 예정 4(미확정) → 구조 확정)
   - 판별 로직을 교체 가능한 함수/클래스로 분리한다.
   - 신호 3개를 모두 계산해 로그에 남긴다: (a) 어깨 비율(기존), (b) world landmarks의 좌우 hip 벡터로 추정한 yaw, (c) 코 visibility(뒷모습 배제).
   - 판정은 우선 **(a)+(c)**로 하고 **(b)는 기록만** 한다.
   - 최종 판정 방식과 임계값은 Phase 4 실측 후 결정한다.
5. **POLAR 데이터의 역할 종료**
   - `STANDING ≥ 160°`는 측면+전신유효 stand의 p25(163.4°, n=317)를 근거로 초기값을 유지한다.
   - 나머지 임계값(하강 진입, 깊이, 상체, 뒤꿈치, Y)은 POLAR로 정하지 않고 **Phase 4 실측으로 정한다.** (POLAR는 정지 사진·스톡 위주라 분포가 실제 웹캠 환경과 다르고, 0.5-1에서 landmark 오류가 큰 비중으로 확인됨)

### 변경: Phase 순서
- 이전: Phase 1 → 2 → 3 → 4 → 5
- 새 순서: **Phase 1 → Phase 4(로깅) → 실측 → Phase 2 → Phase 3 → Phase 5**
- 이유: 남은 임계값이 모두 실측 데이터에 의존하므로, RepTracker(Phase 2)와 품질 판정(Phase 3)을 쓰기 전에 로그부터 확보한다.
- Phase 1 완료 후 사용자 확인을 받고 Phase 4를 진행한다. Phase 2·3은 실측 후 사용자 지시로 진행한다.

### 변경: Phase 3 계획 교체
이전 Phase 3(등급 good/shallow/torso_lean/heel_lift, 반복 종료 시 한 줄 피드백)을 아래로 **대체**한다. **지금은 구현하지 않고 기록만 한다.** 구현은 Phase 4 실측 후 사용자 지시로 진행.

**3-1. 항목별 판정 (기준)**
- 반복 확정 시 `RepResult`(dataclass)에 항목별 `status`(정상/주의/교정)와 측정값을 담는다. 판정 항목은 3개만:
  - `depth`: 최저 무릎각 (보조: 엉덩이 y vs 무릎 y, 기록만)
  - `torso_shin`: 최저점 기준 |몸통각 − 정강이각| (절대 몸통각 임계값 사용 금지)
  - `heel`: heel y 상승량
- 판정하지 않는 것:
  - **템포(하강/상승 시간)**: 판정·점수·화면 피드백에서 제외. 중량과 깊이에 따라 정상 속도 범위가 크게 달라지기 때문. 단 `RepResult`와 로그에는 하강 시간, 상승 시간, 최저점 체류 시간을 **진단용 원자료**로 기록한다.
  - 무릎이 발끝을 넘는 것, 허리 굽음(butt wink).
- 각 항목의 정상/주의/교정 경계값은 `settings.py` 상수로 두고, 값은 Phase 4 실측으로 정한다.

**3-2. 자세 점수 (표시용, 3-1에서 파생)**
- 3-1의 판정 항목 3개만 점수에 반영. 템포 관련 값은 점수 계산에 사용 금지.
- 항목별 측정값을 0~100으로 선형 매핑: 정상 경계 이내 = 100, 교정 경계 바깥 = 0, 사이는 선형.
- 총점 = 항목 점수의 가중 평균. 가중치는 `settings.py`에 노출하고 DEVLOG에 근거와 함께 기록.
- `RepResult`에 `total_score`, `item_scores`, `worst_item`(가장 많이 감점된 항목)을 포함.
- 교정 항목이 하나라도 있으면 총점 상한을 둔다(상한값은 `settings.py`).
- 명칭: 코드·화면·문서 모두 **"자세 점수"**. "정확도"라는 표현은 사용 금지.

**3-3. 화면 표시**
- 반복 종료 시 한 줄: 자세 점수 + `worst_item`에 대한 피드백 문구 (예: "78점 · 더 깊게 앉아보세요").
- 전신 무효 또는 측면 아님이면 점수를 표시하지 않고 안내 문구만 표시.

**3-4. 테스트**
- 항목별 경계값 직전/직후 → 판정과 점수 기대값 일치
- 교정 항목 존재 시 총점 상한 적용
- `worst_item` 선택이 가장 감점이 큰 항목과 일치
- 하강/상승 시간만 극단적으로 다른 두 반복(나머지 동일) → 판정과 점수 동일

**범위 밖 (후속 버전 후보)**: 템포 기반 판정, 바운스 감지, 기준 반복 템플릿과의 궤적 유사도(DTW 등).

### 문서 정리
- `CHANGELOG.md`: 사용자에게 영향이 있는 변경만 기록한다. Phase 0에서 넣었던 분석 스크립트 항목(`scripts/analysis/polar_squat_angle_analysis.py`)은 **삭제**했다(사용자 영향 없음). 분석 스크립트는 DEVLOG에만 기록한다.
- `RELEASE.md`: "왜 바꿨나"에 v0.1.x의 한계(다른 동작이 끼어도 1회로 카운트, 하프 스쿼트의 라벨 의존)를 반영한다.

### 기준선
- Phase 1 시작 전 관련 기존 테스트(`test_exercise_counter`, `test_prediction_smoothing`, `test_camera_ui`, `test_workout_session`) **26 passed** (conda `vision_ai`, pytest 9.1.1).

---

## 2026-10-12 · Phase 1 — 기하 계산 모듈

### 수행 내용
- 신규 `src/pose_geometry.py`, 신규 `tests/test_pose_geometry.py`, `config/settings.py`에 상수 블록 추가.
- 문서: DEVLOG(위 확정 항목), RELEASE.md "왜 바꿨나" 갱신(v0.1.x의 한계 2가지), CHANGELOG에서 Phase 0 분석 스크립트 항목 삭제(사용자 영향 없음).
- **기존 동작 코드는 변경하지 않았다**(`main.py`, `pose_estimator.py`, `exercise_counter.py` 등 무변경). 새 모듈은 아직 어디에도 연결되지 않았고 Phase 4(로깅)에서 연결한다. 따라서 이 Phase는 사용자에게 보이는 변화가 없다(CHANGELOG 항목 없음).

### 구현한 것 (`src/pose_geometry.py`)
| 항목 | 내용 |
|---|---|
| 좌표 보정 | `to_pixel_points`: 정규화 x,y × crop(w,h). 보정 계수는 `analyze_frame`이 매 프레임 `crop_bbox`로 계산 |
| 각도 | `knee_angle`(hip-knee-ankle), `torso_angle`(hip→shoulder와 수직), `shin_angle`(ankle→knee와 수직). 모두 atan2 기반, 길이 0인 선분이면 `None` |
| 다리 선택 | `select_near_leg`: hip+knee+ankle visibility 합이 큰 쪽(동점이면 왼쪽). `analyze_frame(leg=...)`로 고정된 다리를 지정 |
| 전신 가시성 | `check_full_body`: 사용 다리의 hip/knee/ankle/heel/foot_index가 crop 안, visibility ≥ 하한, 원래 YOLO bbox가 프레임 어느 경계에도 안 닿을 때만 유효. 무효 사유를 코드로 반환(`outside_crop:left_ankle`, `low_visibility:…`, `bbox_touches_frame:bottom` 등) |
| 시점 신호 | `ViewSignals`: (a) `shoulder_ratio`, (b) `hip_yaw_deg`, (c) `nose_visibility`. 셋 다 항상 계산 |
| 시점 판정 | `ViewClassifier` Protocol(교체 가능) + 기본 구현 `ShoulderNoseViewClassifier`(**(a)+(c)만 사용, (b)는 기록만**). 사유 코드 반환(`shoulders_wide`, `nose_hidden`, `shoulder_ratio_unavailable`) |
| 고정 | `BodyLock`: STANDING에서 `acquire` → 다리·시점 판정을 반복 끝(`release`)까지 유지. `quality_enabled`: 잠금 시점이 측면이고 현재 프레임 전신이 유효할 때만 True |
| 평활화 | `OneEuroFilter(value, timestamp)`: 타임스탬프(초) 간격으로만 계산. 같은 시각·역행 타임스탬프는 상태를 바꾸지 않음. 기존 `PredictionSmoother`는 재사용하지 않음 |
| 통합 진입점 | `analyze_frame(...) -> FrameGeometry` (각도 3종, 전신 판정, 시점 신호·판정, 사용 다리) |

(b)의 정의: 좌우 hip의 world 벡터에서 `atan2(|Δz|, |Δx|)`. **0° = 정면/후면, 90° = 측면.** 절댓값을 쓰므로 world 좌표계의 부호 규약에 의존하지 않는다.

### `config/settings.py`에 추가한 상수 (모두 **임시 초기값**, Phase 4 실측 후 확정)
| 상수 | 값 | 근거 |
|---|---|---|
| `MIN_LANDMARK_VISIBILITY` | 0.5 | Phase 0 분석의 임시값을 그대로 사용. 확정 근거 없음 |
| `FRAME_BORDER_TOLERANCE_PX` | 1 | Phase 0.5의 bbox 경계 접촉 판정 허용 오차와 동일 |
| `SIDE_VIEW_MAX_SHOULDER_RATIO` | 0.35 | Phase 0의 임시값. 측면/비측면 분포에 깔끔한 경계가 없었음 |
| `SIDE_VIEW_MIN_NOSE_VISIBILITY` | 0.5 | 근거 없음(뒷모습 배제용 임시값) |
| `ONE_EURO_MIN_CUTOFF` / `ONE_EURO_BETA` / `ONE_EURO_D_CUTOFF` | 1.0 / 0.02 / 1.0 | 근거 없음. 무릎각 변화 약 100°/s를 가정한 임시값 |
- 이번 Phase에 쓰이지 않는 값(STANDING ≥160°, 하강 진입, Y 등)은 해당 Phase(RepTracker)에서 추가한다. STANDING ≥160°의 초기값은 위 확정 항목 5에 기록되어 있다.

### 결정과 근거
- **(a)는 visibility로 거르지 않는다.** Phase 0과 같은 정의를 유지한다. 측면 사진에서는 먼 쪽 어깨의 visibility가 낮은 경우가 흔해, 걸러내면 측면을 놓칠 수 있다고 판단. (확신 낮음: 측정하지 않은 가정)
- **`BodyLock.acquire`는 전신이 유효한 프레임에서만 잠근다.** 지시에 명시되지 않은 설계 판단이다. STANDING 프레임에서 다리가 crop 밖/저가시성이면 다리 선택과 시점 판별이 믿을 수 없어서 그런 프레임으로 잠그면 반복 전체가 오염된다. 이 경우 RepTracker가 잠그지 못한 채 대기하고 "전신이 보이게 서주세요"를 표시하게 된다. (확신 중간)
- **몸통각·정강이각은 좌우 방향을 구분하지 않는 0~180° 값**으로 정의했다. Phase 3의 `|몸통각 − 정강이각|`이 스쿼트에서 앞으로 숙이는 방향이 같은 쪽이라는 가정에 기댄다. 방향이 다른 경우(상체를 뒤로 젖힘 등)를 구분할 필요가 있는지는 Phase 4 로그를 보고 판단한다. (확신 낮음)
- **(b) yaw의 신뢰도는 미검증이다.** 실제 MediaPipe world landmark에서 hip 벡터의 z 성분이 시점 판별에 쓸 만큼 안정적인지 아직 모른다. 그래서 판정에 쓰지 않고 기록만 한다(확정 사항 4). (확신 낮음)
- `PoseEstimator.extract`는 현재 `pose_landmarks`만 반환하고 `pose_world_landmarks`를 버린다. **(b) 로깅을 위해 Phase 4에서 world landmarks를 함께 반환하도록 추가 변경이 필요하다**(이번 Phase에서는 기존 코드 무변경 원칙으로 하지 않음).
- `analyze_frame`이 받는 `crop_bbox`는 `main.py`의 `padded_bbox`, `person_bbox`는 원래 `bbox`에 해당한다(`main.py:94-99`). 프레임 크기는 `frame.shape`.

### 시도했다가 버린 접근
- 첫 테스트 자세는 무릎을 수평·수직 선분(직각)으로 만들었는데, **직각은 가로세로 비를 바꿔도 각이 변하지 않아 종횡비 보정 누락을 잡지 못했다.** "보정 없이 계산하면 각도가 달라진다"는 보조 테스트가 실패해서 발견. 정강이를 비스듬히 둔 자세(무릎각 약 106.7°, 정강이각 약 16.7°, 몸통각 45°)로 바꿨다.
- 변이 검사: `to_pixel_points`의 보정을 일부러 제거하면 보정에 민감한 테스트 3개(`test_angles_match_known_geometry`, `test_same_pose_gives_same_angles_for_different_crop_aspect_ratios`, `test_side_view_is_accepted`)가 모두 실패함을 확인했다. 즉 이 테스트들은 실제로 보정 누락을 잡는다.

### 임계값 변경 이력
- 신규 상수 6개 추가(위 표). 이전 값 없음.

### 테스트 결과
- `tests/test_pose_geometry.py`: **37 passed** (종횡비가 다른 두 crop에서 같은 각도, 발목 crop 이탈·bbox 상/하/좌/우 접촉·허용 오차·저가시성 → 무효, 측면/정면/뒷모습 판정, (b) 기록만 하고 판정에 불영향, 분류기 교체, 다리·시점 고정, One Euro의 노이즈 감소·스텝 추종·불규칙 간격·중복 타임스탬프·지연).
- AI Client `tests/` 전체: **122 passed** = 기존 85 + 신규 37. 기존 `test_exercise_counter.py` 8개 포함 모두 통과.
- 참고: README는 "Python test suite 122 tests passed"라고 쓰고 있다. 이번 측정에서 기존 `tests/`는 85개였으므로, README의 122는 다른 범위(예: backend 포함)를 센 값일 가능성이 있다. 확인하지 않았다. Phase 5에서 README를 갱신할 때 재측정이 필요하다.

### 남은 문제
- (b) yaw와 (c) 코 visibility가 실제 웹캠 영상에서 얼마나 쓸 만한지는 Phase 4 로그로 확인해야 한다.
- 몸통각·정강이각의 방향 정보(부호) 필요 여부 미확정.
- `main.py`와의 연결, `PoseEstimator`의 world landmarks 반환은 Phase 4 범위.

---

## 2026-10-12 · Phase 1 수정 (사용자 확인 후) 및 README 테스트 수 확인

### README의 "122 tests passed" 확인
- **이번 세션에서 README는 수정되지 않았다.** `git diff README.md` 0줄, `git status`에 변경 없음, 마지막 수정은 `f26902f`(2026-10-01).
- "122"는 `1187eb3`(2026-09-17)에서 README에 들어갔다. **범위는 `tests/`(85개) + `backend/tests`(37개) = 122개**다. 실측: `tests/`(이번 세션 신규 파일 제외) 85 passed, `backend/tests` 37 passed.
- 이번 세션의 신규 테스트 37개(`test_pose_geometry`, Phase 1 당시)가 backend 테스트 수 37과 같았을 뿐 **우연의 일치**다. 따라서 위 Phase 1 항목의 "README는 다른 범위(예: backend 포함)를 센 값일 가능성"이 **맞았음이 확인**되었다(그때는 확인하지 않았다고 적었다).
- 현재 수치: `tests/` **172 passed** + `backend/tests` 37 passed = 209. Phase 5에서 README를 갱신할 때 이 두 범위를 구분해 재측정해야 한다.

### 수정 1: 전신 가시성 검사의 경계 조건
- 이전: bbox가 프레임 어느 경계에 닿아도 무효.
- 변경: **하단·좌·우 경계만 무효.** 상단 접촉은 무효 사유가 아니며 `FullBodyCheck.notes`(`bbox_touches_frame:top`)에만 남긴다. 대신 **사용하는 쪽 어깨(shoulder)의 visibility가 기준 이상**일 것을 유효 조건에 추가(`low_visibility:left_shoulder` 등).
- 이유: 머리가 화면 위로 잘리는 경우는 흔하고, 스쿼트 판정에는 어깨~발끝만 필요하다.
- 테스트: 상단만 닿고 어깨~발 모두 유효 → 유효(허용 오차 1px 포함), 상단+하단 접촉이면 하단 사유만 무효 사유, 어깨 visibility 낮음 → 무효, 반대쪽(먼 쪽) 어깨는 검사하지 않음.

### 수정 2: 보는 방향(facing)과 부호 있는 각도
- `facing_direction`: **선택한 다리의 heel→foot_index의 x 방향**으로 사용자가 보는 방향(left/right)을 정한다. 발끝과 뒤꿈치의 x가 같으면 None.
- 부호 있는 각도 추가: `torso_angle_signed`(어깨가 엉덩이보다 앞 = **앞으로 숙임 = 양수**), `shin_angle_signed`(무릎이 발목보다 앞 = 양수). 기존 무부호 각도(`torso_angle`, `shin_angle`)는 유지하고 **둘 다 로그에 남긴다.**
- `BodyLock`이 다리와 **facing을 함께 고정**한다. `analyze_frame(leg=, facing=)`으로 고정값을 넘기면 반복 중 발끝 landmark가 흔들려도 부호가 뒤집히지 않는다.
- 테스트: 같은 자세를 좌우 반전하면 부호 있는 각도가 동일(두 crop 모두), 앞으로 숙임/무릎이 앞으로 나감 = 양수·반대 = 음수, facing 불명이면 부호 있는 값만 None, 잠금 후 facing 유지.
- 참고: 테스트용 예시 자세(SIDE_POSE)에서 정강이각은 음수(-16.7°)다. 무릎이 발목보다 **뒤**에 있는 자세이기 때문이며 정의대로의 값이다.

### 승인된 판단으로 기록
- **`BodyLock`은 전신이 유효한 프레임에서만 잠근다**(Phase 1에서 내가 한 판단)는 사용자가 **승인**했다.
- 이번에 같은 원칙으로 한 가지를 추가했다(**사용자 미확인**): facing을 정할 수 없는 프레임(`facing is None`)에서도 잠그지 않는다. 방향 없이 잠그면 그 반복 전체에서 부호 있는 각도를 쓸 수 없기 때문이다. (확신 중간. 이의가 있으면 되돌린다.)

### 테스트 결과
- `tests/test_pose_geometry.py`: **48 passed**(수정 전 37).

---

## 2026-10-12 · Phase 4 — Landmark 시퀀스 로깅

### 수행 내용
| 구분 | 파일 |
|---|---|
| 선행 변경 | `src/pose_estimator.py`: `extract()`가 `PoseExtraction(landmarks, world_landmarks)`를 반환 |
| 신규 | `src/geometry_tracker.py`(무릎각 평활화 + 임시 잠금 정책), `src/sequence_logger.py`(JSONL 기록, 스레드, `SequenceRecorder`), `scripts/analysis/plot_landmark_sequence.py` |
| 연결 | `src/main.py`: CLI 인자, 로깅 연결, 벤치마크 출력에 로깅 시간 한 줄, `person_results`에 `world_landmarks` 추가 |
| 설정 | `config/settings.py`: `STANDING_KNEE_ANGLE`, `BODY_LOCK_MISSING_RELEASE_SECONDS`, `SEQUENCE_LOGGING_ENABLED`, `LANDMARK_SEQUENCE_DIR`, `SEQUENCE_LOG_FLUSH_INTERVAL_SECONDS`, `SEQUENCE_LOG_QUEUE_SIZE` |
| 그 외 | `.gitignore`(`data/landmark_sequences/*`, `.gitkeep`만 추적), `data/landmark_sequences/.gitkeep` |
| 테스트 | `tests/test_pose_estimator_output.py`(5), `tests/test_sequence_logger.py`(29), `tests/test_plot_landmark_sequence.py`(5) |
- **CHANGELOG에는 넣지 않았다.** 사용자에게 보이는 변화가 없다(진단용이며 기본 꺼짐, 새 CLI 옵션은 개발자용).

### 선행 변경: world landmarks와 XGBoost 입력
- `extract()`는 이전과 **같은 `pose_landmarks[0]` 객체**를 `PoseExtraction.landmarks`로 반환하고, `pose_world_landmarks[0]`(개수가 33개일 때만)을 `world_landmarks`로 추가한다. 없으면 None. 호출처는 `main.py` 한 곳이었다.
- `main.py`는 분류기에 `extraction.landmarks`만 넘긴다. world landmarks는 로그에만 쓰인다.
- **분류기 입력이 변경 전과 같음을 테스트로 확인했다**: `extract()`가 반환한 landmarks 객체가 원본과 동일 객체이고, `PoseClassifier.create_features` 결과가 변경 전 방식(각 landmark의 x, y, z, visibility를 MediaPipe 순서로 펼친 132개, float32, shape (1,132))과 `np.array_equal`이며, world landmarks 값을 바꾸거나 없애도 feature가 동일하다. 모델 파일 없이 동작한다(`PoseClassifier.__new__`로 생성자 생략).

### 기록 형식 (`data/landmark_sequences/session_<시작시각>[_자세][_시점].jsonl`, 세션당 1개)
줄 단위 JSON. **`session`(첫 줄) → `frame`(프레임마다) → `end`(정상 종료 시)**.
- `session`: `format_version`, `started_at`(tz 포함 ISO), `time_base`, `metadata`(의도한 자세 `normal/shallow/torso_lean/heel_lift`, 카메라 시점 `side/oblique/front`, 메모), **`settings`(그 시점의 settings.py 임계값 스냅샷, 경로 제외)**, `runtime`(detector backend, 분류 클래스, 운동 모드, python, platform), `landmark_names`(33개).
- `frame`: `i`(프레임 번호, 버려진 프레임은 번호의 공백으로 드러남), `t`(프레임을 읽은 직후)·`t_logic`(운동 로직 실행 시각, 둘 다 로깅 시작 기준 초), `frame_size`, `person`, `person_confidence`, `yolo_bbox`, `crop_bbox`, `landmarks`(정규화 33×[x,y,z,visibility]), `world_landmarks`(33×[x,y,z,visibility]), `geometry`(`leg`, `facing`, `knee`, `torso`, `shin`, `torso_signed`, `shin_signed`, `knee_smoothed`, `standing`, `leg_now`, `facing_now`), `full_body`(`valid`, `reasons`, `notes`), `view`((a)`shoulder_ratio`, (b)`hip_yaw_deg`, (c)`nose_visibility`, `is_side`, `reasons`), `lock`(`locked`, `leg`, `facing`, `view_is_side`, `view_reasons`, `event`), `labels`(`raw`/`raw_confidence`: 프레임 예측, `stable`/`stable_confidence`: **표시 필터 전 원래 stable 라벨**, `candidate`, `candidate_count`, `missing_count`, `display`/`display_confidence`: 표시 라벨).
- 사람이나 Pose를 놓친 프레임도 한 줄로 남긴다(`person`/`landmarks`가 null). 시간축이 끊기지 않게 하기 위해서다.
- `end`: `frames_offered/written/dropped/invalid`, `write_error`.
- 실측 크기: 프레임당 약 3.0~3.5 KB(landmark 정규화+world 포함, 소수 5자리).

### 형식과 성능 설계
- **별도 스레드가 쓰고(`daemon`), 큐가 가득 차면 프레임을 버린다.** `log_frame()`은 `put_nowait`만 하므로 파이프라인을 절대 기다리게 하지 않는다. 큐 크기 4096(settings).
- **중간에 종료돼도 앞부분이 남는다**: 헤더는 시작 즉시 flush, 이후 1초마다 flush. 닫지 않은 파일을 읽는 테스트와 잘린 마지막 줄을 견디는 분석 스크립트 테스트가 있다.
- 직렬화할 수 없는 프레임(NaN 등)은 그 프레임만 건너뛰고 계속 기록, 디스크 오류 등으로 쓰기가 실패하면 **기록만 멈추고 운동 파이프라인은 계속**(예외 한 번만 알림). `SequenceRecorder`가 예외를 삼킨다.

### 임시 잠금 정책 (`GeometryTracker`) — 지시에 없던 설계 판단, 확인 요청
- 문제: RepTracker가 없는 상태에서 "BodyLock 상태(잠금/해제, 다리, facing)"를 로그에 남기려면 누군가 잠가야 한다.
- 결정: **서 있는 동안(평활화한 무릎각 ≥ 160°, 전신 유효, facing 확인)은 프레임마다 잠금을 갱신하고, 내려가기 시작하면 마지막 서 있던 프레임의 값을 유지한다.** RepTracker가 STANDING에서 잠그고 반복 중 고정하는 동작을 반복 구간 없이 흉내 낸 것. Pose를 2초 이상 놓치면 해제한다(임시값).
- `geometry`(잠금 기준)와 별도로 `leg_now`/`facing_now`(그 프레임만 본 값)를 같이 남겨 **잠금 정책이 올바른지 사후에 검증**할 수 있다. 평활화는 전신이 유효한 프레임의 무릎각에만 적용한다(`knee`는 항상 raw로 기록).
- Phase 2에서 RepTracker가 대체한다. (확신 중간)

### 세션 메타데이터
- CLI: `--log-sequence`(기본 꺼짐), `--session-posture {normal,shallow,torso_lean,heel_lift}`, `--session-view {side,oblique,front}`, `--session-note 메모`. 메타데이터 옵션은 `--log-sequence` 없이 쓰면 오류. 설정 파일 방식은 만들지 않았다(CLI로 충분하다고 판단).

### FPS 측정 (로깅 끔/켬, 이 PC의 웹캠, 20초 + 30프레임 워밍업, 번갈아 2회)
| 실행 | 로깅 | Processed | End-to-End FPS | Inference FPS | 평균 추론 시간(ms) | 로깅 평균(ms/프레임) | 버려진 프레임 |
|---|---|---|---|---|---|---|---|
| off1 | 끔 | 177 | 8.81 | 21.31 | 46.92 | - | - |
| on1 | 켬 | 343 | 17.08 | 20.59 | 48.57 | 0.451 | 0 |
| off2 | 끔 | 209 | 10.44 | 16.00 | 62.52 | - | - |
| on2 | 켬 | 169 | 8.38 | 19.58 | 51.08 | 0.584 | 0 |
- **로깅이 메인 루프에 더하는 시간은 프레임당 0.45~0.58 ms로 평균 추론 시간(47~63 ms)의 약 1%다.** 이 값은 landmark가 있는 프레임(로그 기준 304/373, 199/199프레임)의 기하 계산과 기록 생성 비용을 포함한다.
- **로깅 켬/끔의 FPS 차이는 이 측정으로는 구분할 수 없다.** 같은 설정(끔)끼리도 End-to-End FPS가 8.81 vs 10.44, 평균 추론 시간이 46.9 vs 62.5 ms로 달라 노이즈가 로깅 비용보다 훨씬 크다. End-to-End FPS(8.4~17.1)는 세 번 모두 Inference FPS(16~21)보다 낮아 카메라 읽기 대기가 지배적이었던 것으로 보이며(원인 미확인), 사람의 자세에 따라 MediaPipe 시간도 달랐다(26~45 ms).
- 따라서 결론은 "**로깅 오버헤드 약 0.5 ms/프레임, 프레임 버림 0**"이고 "FPS 영향 없음"을 입증하는 측정은 아니다. 실제 스쿼트 영상에서의 정밀한 A/B는 사용자가 직접 진행하는 실측에서 확인하는 것을 권한다. 측정 중 카메라 앞에는 사람이 정면을 보고 앉아 있었고(전신 아님, 누구인지는 로그로 알 수 없다) 영상은 저장하지 않았다.
- 측정 로그 2개는 얼굴 landmark를 포함하므로 분석 후 **삭제했다**(git 제외 폴더).

### 첫 실제 로그에서 확인한 것 (측정용 로그 2개, 정면을 보고 앉은 사람)
- 사람 검출 100%, 전신 유효 **0%**, 잠금 0%. 무효 사유는 `bbox_touches_frame:right`, `outside_crop:*`·`low_visibility:*`(오른쪽 또는 왼쪽 다리). 하체가 프레임에 없는 상황에서 **전신 가시성 검사가 의도대로 거부**했다.
- 시점 신호: 어깨 비율 중앙값 0.79~1.02, **hip yaw 중앙값 5.4~14.2°**(정면에 가까움), 코 visibility 중앙값 0.99~1.0, 측면 판정은 0~10%. 정면으로 앉은 상황과 (a)(b) 두 신호가 **일치**했다. (b)가 이 한 번의 관찰에서는 쓸 만해 보이나 표본 하나라 결론은 아니다.
- 이 상황에서 라벨 stable은 대부분 `lying`이었다(책상 앞 앉은 상반신). 분류기가 상반신만 보이는 입력에서 틀린 라벨을 내는 한 예다.
- `world_landmarks`는 landmark가 있는 모든 프레임에서 기록되었다.

### 기본 꺼짐과 패키징 확인
- `SEQUENCE_LOGGING_ENABLED = False`, `parse_arguments([]).log_sequence`는 False(테스트).
- **런처는 `--exercise`, `--auto-start-session`만 만들어 넘기며**(`desktop_launcher/launcher.py:196-212`) 로깅 옵션을 만들 수 없다. URL에 추가 쿼리를 붙이면 거부된다(테스트로 고정). 환경변수로 켜는 경로는 없다.
- PyInstaller spec(`packaging/**/*.spec`)과 Installer 파일(`installer/*.iss`, `*.json`)에 `landmark_sequences`가 없고(테스트), spec의 `datas`는 `models/`뿐이다. 새 모듈은 `main.py`가 정적으로 import하므로 번들에 포함된다. matplotlib을 쓰는 분석 스크립트는 `scripts/`에만 있다.
- **한계**: 실제 PyInstaller 빌드 산출물을 만들어 실행해 보지는 않았다. 위는 설정·런처·spec의 정적 확인이다. Phase 5 릴리스 빌드 후 `--diagnose-runtime`과 함께 확인하는 것을 권한다.

### 분석 스크립트 (`scripts/analysis/plot_landmark_sequence.py`)
- `--session <jsonl>`(필수), `--out-dir`(기본 세션 옆 `plots/`), `--max-gap`. 출력 PNG 2장: `*_timeline.png`(무릎각 raw/평활화 + STANDING 기준선 + BodyLock 구간, 부호 있는/없는 몸통·정강이각, heel/foot_index y, 라벨 3줄(stable·raw·display), 시점 신호 (a)(b)(c)), `*_labels.png`(stable 라벨 시간 분포: 전체/전신 유효/무릎 150° 미만).
- 전신 무효 구간(빨강)과 사람 없음(회색)을 칠하고, 공백이 긴 곳은 선을 끊으며 라벨 시간에서 제외한다. 잘린 마지막 줄을 견딘다. 요약(프레임 수, 버려진 프레임, FPS, 유효·잠금 비율, 라벨 시간)을 출력한다.
- 합성 세션(반복 3회, 사람 미검출 구간, 뒤꿈치 들림 6px, 걷기 라벨)으로 그래프를 만들어 눈으로 확인했다.

### 교체된 Phase 3 대비: 원자료 확인
| Phase 3에 필요한 것 | 로그의 어디에 있는가 | 확인 |
|---|---|---|
| 타임스탬프 | `t`(프레임 읽은 직후), `t_logic` — 로깅 시작 기준 초, 1e-5초 단위 | 실측 프레임 간격이 그대로 남음(테스트) |
| 하강·상승·최저점 체류 시간 | `t` + `geometry.knee`(raw)/`knee_smoothed` + `geometry.standing`으로 도출 가능. 최저점 시각을 무릎각 최소에서 복원(테스트) | 반복 구간 판정 자체는 Phase 2 |
| 깊이 `depth` | `geometry.knee`, 보조: 엉덩이 y vs 무릎 y → `landmarks`의 hip/knee y + `crop_bbox` | 프레임 픽셀로 복원 가능 |
| `torso_shin` | `geometry.torso_signed/shin_signed`(+ 무부호 `torso/shin`) 프레임별 | 있음 |
| `heel` 상승량 | `landmarks`의 heel(29,30)/foot_index(31,32) y + **프레임마다 달라지는 `crop_bbox`** → `crop_y1 + y × crop_h`로 프레임 픽셀 복원 | **crop이 달라도 같은 값으로 복원됨을 테스트로 확인**(정규화 y만으로는 프레임 간 비교가 안 되므로 crop 기록이 필수) |
| 체격 정규화(필요 시) | hip/knee/ankle landmark(다리 길이), `yolo_bbox` | 있음 |
| 유효성·시점·잠금 맥락 | `full_body`, `view`, `lock` | 있음 |
| 프레임 누락 파악 | `i`의 공백 + `end.frames_dropped`, 놓친 프레임도 한 줄 | 있음 |
- **빠진 것(의도적 또는 이후 판단)**: 프레임별 처리 시간(`t`의 간격으로 추정 가능), 반복 구간·최저점 같은 파생값(Phase 2), 주 사용자가 아닌 다른 사람(파이프라인과 같이 가장 큰 bbox 한 명만 기록).
- 카메라 자체의 캡처 시각은 알 수 없다. `t`는 `camera.read()`가 돌아온 직후의 `perf_counter` 값이라 카메라 지연과 프레임 버퍼링은 포함하지 않는다. 템포는 판정에 쓰지 않고 진단용이므로 허용 가능하다고 판단.

### 임계값 변경 이력
- 신규 상수: `STANDING_KNEE_ANGLE = 160.0`(확정 항목 5의 초기값), `BODY_LOCK_MISSING_RELEASE_SECONDS = 2.0`(임시, 근거 없음), `SEQUENCE_LOG_FLUSH_INTERVAL_SECONDS = 1.0`, `SEQUENCE_LOG_QUEUE_SIZE = 4096`. 이전 값 없음.

### 테스트 결과
- `tests/` **172 passed**(이전 기준 85 + `test_pose_geometry` 48 + `test_pose_estimator_output` 5 + `test_sequence_logger` 29 + `test_plot_landmark_sequence` 5). `backend/tests` 37 passed. 기존 `test_exercise_counter.py` 8개 포함 모두 통과.
- 테스트 작성 중 시나리오 오류 3건을 고쳤다(구현 버그 아님): "오른쪽 다리가 더 잘 보임"을 왼쪽 visibility 0.4로 만들어 잠근 다리가 무효가 되는 시나리오(→ 왼쪽 0.6, 오른쪽 1.0), One Euro 기대값 107±3(→ 손계산 111.5°가 맞음, 조건을 "빠른 샘플링은 크게 뒤처지고 1초 뒤엔 원값 근처"로 수정).

### 남은 문제
- 임시 잠금 정책은 Phase 2의 RepTracker가 대체해야 한다.
- 로그에는 얼굴 landmark(코·눈·귀·입)가 포함된다. 영상은 저장하지 않고 로컬(git 제외)에만 남지만, 실측 로그를 외부로 공유할 때는 주의가 필요하다.
- frozen 빌드에서 로깅을 켜면 설치 폴더 옆 `data/`에 쓰려 한다(`get_app_root()` 기준). 기본 꺼짐이라 일반 사용에는 영향이 없다.
- End-to-End FPS의 큰 변동(카메라 읽기 대기 추정)은 원인을 확인하지 않았다.

---

## 2026-10-12 · Phase 4 후속 — 카메라 사용 규칙, 얼굴 landmark 기본 제외, 승인 기록 (실측 전 수정)

### 카메라 사용 규칙 (사용자 지시)
- **카메라/웹캠을 직접 실행하는 측정은 사용자의 명시적 허락 없이 하지 않는다.** 이후 작업은 코드 수정과 카메라 없는 테스트(합성 landmark, 가짜 landmarker)로 한다. 실측은 사용자가 직접 진행한다.
- 경위 기록: Phase 4의 FPS 측정(로깅 끔/켬 비교)은 "로깅 켰을 때와 껐을 때의 FPS를 측정해 보고하라"는 지시에 따라 이 PC의 웹캠을 실행해 수행했다. 그때 카메라 실행 자체에 대한 별도의 명시적 허락은 받지 않았다. 앞으로는 카메라를 여는 모든 실행(`src.main` 실행, `--benchmark-seconds` 포함)을 허락 없이 하지 않는다. (카메라를 열지 않는 확인이라도 불필요하면 `src.main`을 실행하지 않고, 옵션 값은 코드에서 읽는다.)

### 얼굴 landmark(0~10번)를 기본으로 저장하지 않는다
- 대상: MediaPipe landmark 0~10번(코, 양쪽 눈 3점씩, 귀, 입). **정규화 landmark와 world landmark 모두** 좌표를 저장하지 않는다.
- 형식: 행은 33개를 그대로 유지해 인덱스가 `landmark_names`와 맞는다. 얼굴 행의 값은 `[null, null, null, null]`이다. **예외로 코(0번)의 visibility만** 정규화 landmark 행 0번에 남긴다(`[null, null, null, 0.77]` 꼴). 시점 신호 (c)는 `view.nose_visibility`에도 따로 기록된다. world landmark의 얼굴 행은 visibility까지 전부 null.
- 옵션: **`--log-face-landmarks`**(기본 꺼짐, `settings.SEQUENCE_LOG_FACE_LANDMARKS = False`). 얼굴 좌표 전체가 필요할 때만 켠다. `--log-sequence` 없이 쓰면 오류. 켜면 시작 시 콘솔에 "face landmark coordinates INCLUDED"를 출력하고, 헤더의 `options.face_landmarks`에 사용 여부를 남긴다.
- 영향 없음 확인: 각도, 전신 유효, 시점 신호, 잠금 상태는 메모리 안의 전체 landmark로 계산하므로 얼굴 저장 여부와 무관하다(같은 입력에서 `geometry/full_body/view/lock/labels`가 옵션 켬/끔에서 동일함을 테스트). 몸 landmark(11~32번) 값도 동일. 분석 스크립트는 몸 인덱스(heel, foot_index, hip, knee)만 읽어 영향이 없다.
- 테스트(기본 설정에서 얼굴 좌표가 로그에 없음): ① 기록 한 줄에서 얼굴 11개 행이 모두 null(코 visibility만 예외), ② 얼굴에 식별 가능한 값(정규화 0.31415/0.27182/-0.1618, world 0.07771/-0.08882/0.09993)을 넣고 `SequenceRecorder` 기본값으로 쓴 **파일 전체 텍스트에 그 값들이 없음**, ③ 같은 입력을 옵션을 켜면 파일에 나타남(위 검사가 의미 있다는 확인), ④ 코 visibility가 `view`에 남음, ⑤ 설정·CLI 기본값 False와 `--log-sequence` 요구, ⑥ `main`의 연결 함수가 옵션을 기록기와 헤더에 전달함(카메라 없이 `start_sequence_recording`만 실행).
- 변이 검사: 마스킹을 일부러 끄면 ①과 ②가 실패함을 확인했다.
- 한계: 얼굴 좌표를 빼도 몸 landmark와 bbox만으로 개인을 식별할 수 없다고 단정하지는 못한다. 이 변경은 얼굴 좌표라는 가장 민감한 부분을 기본에서 제외하는 것이다. 이전 항목의 "남은 문제: 로그에 얼굴 landmark 포함"은 이 항목으로 대체된다. 이전 측정 로그 2개는 이미 삭제되었으므로 기존 파일 영향은 없다.
- 형식 호환: 행 구조(33×4)와 `format_version`(1)은 그대로이고 헤더에 `options` 키만 추가되었다. 배포 전이고 보존된 로그가 없어 버전을 올리지 않았다.

### 승인 기록 (사용자)
- **facing을 정할 수 없는 프레임에서는 BodyLock을 잠그지 않는다**는 판단: **승인**. (Phase 4 항목에서 "사용자 미확인"으로 적은 것을 확정)
- **임시 잠금 정책**(서 있는 동안 프레임마다 갱신하고 내려가기 시작하면 유지, Pose를 2초 이상 놓치면 해제): **승인**. Phase 2에서 RepTracker가 대체한다.

### 세션 옵션과 실행 예시 (코드에서 읽은 값, 카메라 실행 없이 확인)
- `--session-posture` (의도한 자세): `normal`(정상), `shallow`(얕음), `torso_lean`(상체 숙임), `heel_lift`(뒤꿈치 들림)
- `--session-view` (카메라 시점): `side`(측면), `oblique`(사선), `front`(정면)
- 그 외: `--session-note "메모"`, `--log-face-landmarks`(기본 꺼짐). 이 세션 옵션들은 모두 `--log-sequence`가 있어야 한다. `--benchmark-seconds N`은 N초 측정 후 자동 종료하는 기존 옵션이다.
- 예시(저장소 루트에서, **사용자가 직접 실행**):
  - `python -m src.main --log-sequence --session-posture normal --session-view side`
  - `python -m src.main --log-sequence --session-posture shallow --session-view side --session-note "2세트"`
  - `python -m src.main --log-sequence --session-posture torso_lean --session-view oblique`
  - `python -m src.main --log-sequence --session-posture heel_lift --session-view side`
  - 얼굴 좌표까지 필요할 때만: `python -m src.main --log-sequence --session-posture normal --session-view side --log-face-landmarks`
  - 로그 확인: `python scripts/analysis/plot_landmark_sequence.py --session data/landmark_sequences/session_<시각>_<자세>_<시점>.jsonl`
- 종료는 영상 창에서 `Q` 또는 `ESC`. 파일은 `data/landmark_sequences/session_<시작시각>_<자세>_<시점>.jsonl`로 저장된다.

### 테스트 결과
- `tests/` **181 passed**(172 + 신규 9: 얼굴 landmark 관련), `backend/tests` 37 passed. 카메라는 실행하지 않았다.

---

## 2026-10-18 · 실측 1차(field_test_1) 로그 분석 — 분석과 제안까지, Phase 2는 시작하지 않음

### 실측 개요
- 일시: 2026-10-18 13:55 ~ 14:28, 측면·사선·정면 웹캠, 로그 13개(`data/landmark_sequences/`, 원본 수정 없음). 이번 분석에서 카메라는 실행하지 않았다.
- 세션 구성: 0(시험, 임계값 산출 금지), 1(평행 10회), 2(깊게 8), 3(얕음 8), 4(상체 숙임 8), 5(뒤꿈치 들림 8), 6(사선 5), 7(정면 5), 8a(걷기), 8b(의자 3동작), 8c(런지 3동작), 9(반대 방향 5).
- **무효 파일**: `session_20261018_140223_normal_side.jsonl`(14:02:23, 일정표 14:03과 −37초). 메모가 `parallel`로 세션 1(14:04:55)과 같아 시각으로만 구분. 전신 유효 23%, 평활 무릎각 46초 공백, 반복 3회. 분석 제외.
- 스크립트 `scripts/analysis/field_test_1_analysis.py`, `field_test_1_lib.py` 추가. 결과·그래프·반복별 지표 CSV·상세 보고서: `docs/versions/v0.2.0/analysis/field_test_1/` (`report.md`).

### 분석 결과 요약
- **v0.1.x 기준선**: `stable` 라벨을 기존 `ExerciseCounter`에 재투입하면 화면 카운트가 기록된 7개 세션이 모두 일치(2:7, 3:5, 4:7, 7:2, 8a:0, 8b:2, 8c:1). 나머지 재계산: 세션 1 6/10, 5 5/8, 6 5/5, 9 0/5. 원인: 올라온 뒤 `stand` 라벨이 안 나온다(`bendover`/`run`). 반대 방향(9)은 `stand`가 한 번도 안 나와 0회.
- **반복 추출(160/150, 이동 구간 제외)**: 세션 1~5는 실제와 일치. **세션 9는 6회 검출 vs 사용자 5회**: 로그의 6회는 모양이 같은 정상 스쿼트라 사용자 확인 필요. 데이터를 본 뒤 정한 선택 2가지(보간 1.5초, transit 규칙)는 report.md 4장에 공개.
- **depth**: AUC 1.00, 정상 ≤ 80°, 주의 80~95°, 교정 > 95°(교정선은 가정). 세션 2 감점 없음(8/8 정상).
- **torso_shin**: AUC 1.00/0.997, 정상 ≤ 25°, 교정 ≥ 35°. 얕은 스쿼트(3)가 5/8회 주의(depth와 이중 감점 가능).
- **heel**: 세션 5가 정상과 구분되지 않음(AUC 0.45~0.68), 세션 9에서 방향 의존 +약 10px. **판정선 확정 불가, 보류 권장.**
- **세션 9**: 부호 있는 각도는 양수·같은 크기로 정상 작동. 세션 1과는 몸통각이 4° 달랐으나 세션 2와는 구분 안 됨.
- **비스쿼트**: 3장 규칙이 걷기 17, 의자 3, 런지 3(+끝 이동 1)을 반복으로 잡음. 길이 ≥ 1.0초, 엉덩이 하강 ≥ 0.25, 양발 간격 ≤ 0.25 L(측면 전용), 몸통 ≥ 30°, sit 비율 ≤ 0.25 조합이 정상 48회 탈락 0, 비스쿼트 잔존 0. 체류 시간(여유 0.08초)과 좌우 무릎 차이(세션 9 6회 탈락)는 부적합.
- **ML**: `jump`는 정상 반복의 하강 17%·상승 22%라 배제 목록에서 제외 권장, 목록은 walk+run+lying, Y=0.40(정상 최대 0.28 vs 비스쿼트 최소 0.49). `stretch`는 근거 없음. 기하 조건이 더 안정적, ML은 2차 방어선.
- **시점**: (a)+(c)와 (b) 모두 완전 분리(AUC 1.00). (b) 승격 근거 없음(승격 시 55°). 세션 7에서 BodyLock이 **잡혔다**(서 있는 프레임 100%, view_is_side 0%).
- **세션 0 BodyLock**: 원인은 `GeometryTracker`에 비측면 해제가 없고 서 있는 동안 매 프레임 재잠금(정면 프레임 값으로 갱신, 다리·방향 7회 뒤집힘). 설계 제안: 측면 0.5초 연속이면 획득, STANDING 중 비측면 0.4초 연속이면 해제, 반복 중 고정, 측면 프레임에서만 다리·방향 갱신.

### 결정과 근거
- 위 모든 값은 한 사람·하루·세션당 5~10회 기준의 **초기값 제안**이며 **사용자 확인 전까지 코드와 settings.py에 반영하지 않았다.** 확인 요청 목록은 report.md 10장.
- 세션 0은 임계값에 쓰지 않았다(jump 비율 재확인, BodyLock 확인에만 사용).

### 임계값 변경 이력
- 변경 없음(제안만).

### 테스트 결과
- `src/`와 `config/` 변경 없음. 기존 테스트는 이번 작업에서 다시 실행하지 않았다. 분석 스크립트에는 단위 테스트를 만들지 않았다(일회성 분석, 실제 로그로 실행해 확인).

### 남은 문제
- heel 판정은 재측정 없이는 정할 수 없다. 사용자 결정 필요.
- 세션 9 횟수(5 vs 6) 확인 필요.

---

## 2026-10-18 · 결정 확정, 비스쿼트 조건 ablation, Phase 2(RepTracker) 구현

### 사용자 확정 (실측 1차 분석 확인 후)
- **세션 9의 횟수: 불확실** (사용자는 5회로 기억하나 6회일 가능성도 있음). 로그는 모양이 같은 정상 스쿼트 6회를 보여 준다. **세션 9는 검출 횟수 검증에서 제외하고 각도 검증(부호 있는 각도, 반대 방향)에만 쓴다.** 회귀 테스트도 같은 원칙이다(`actual_squats = null`, 횟수 단언 없음).
- **반복 추출**: 1.5초 보간을 채택한다. 이동 구간 규칙(짧거나 끊긴 후보가 core 밖이면 제외)은 **데이터를 본 뒤 정한 값**임을 명시한다(세션 2의 1.25초 공백, 세션 시작·끝에서 나온 가짜 후보 4개를 보고 정함). 온라인 구현(RepTracker)은 이 규칙 대신 "반복 길이 ≥ 1.0초"를 확정 조건으로 쓰며 같은 후보들이 탈락한다.
- **ML 배제 목록(확정)**: `walk, run, lying`. `jump` 제외. Y = 0.40. `stretch`는 넣지 않는다. **기하 조건이 1차, ML은 2차.**
- **BodyLock(확정)**: 측면 판정 0.5초 연속 시 잠금, STANDING 중 비측면 0.4초 연속 시 해제, 반복 중 고정, 다리·방향은 측면 프레임에서만 갱신. **측면이 아니면 잠그지 않는다**(세션 7처럼 정면에서 잠기면 안 됨).

### 1. 비스쿼트 배제 조건 ablation (구현 전 분석, `analysis/field_test_1/ablation_*.csv`)
정상 = 세션 1~5, 9의 transit 제외 48회(여기서 세션 9는 조건의 타당성만 본다). 조건: 길이 ≥ 1.0초, 엉덩이 하강 ≥ 0.25, 서 있을 때 양발 간격 ≤ 0.25 L, 몸통 숙임 ≥ 30°, sit 비율 ≤ 0.25.

**조건 하나만 뺐을 때** (정상 탈락 / 걷기·의자·런지 잔존)

| 규칙 | 정상 탈락 | 8a 걷기 | 8b 의자 | 8c 런지 |
|---|---|---|---|---|
| 5개 전부 | 0/48 | 0/17 | 0/3 | 0/3 |
| 길이 뺌 | 0 | 0 | 0 | 0 |
| 엉덩이 하강 뺌 | 0 | 0 | 0 | 0 |
| 양발 간격 뺌 | 0 | 0 | 0 | 0 |
| 몸통 뺌 | 0 | 0 | 0 | 0 |
| sit 뺌 | 0 | 0 | 0 | 0 |
| **확정 3개(길이 + 엉덩이 하강 + 양발 간격)** | **0** | **0** | **3 (의자는 걸러내지 않기로 함)** | **0** |
| 확정 3개에서 길이 뺌 | 0 | 0 | 3 | 0 |
| 확정 3개에서 엉덩이 하강 뺌 | 0 | 0 | 3 | 0 |
| 확정 3개에서 **양발 간격 뺌** | 0 | 0 | 3 | **3** |

- 5개일 때는 어느 하나를 빼도 걷기·런지가 남지 않는다. 조건들이 서로 겹쳐 보호하고 있었기 때문이다. **3개로 줄이면 겹침이 줄어** 걷기는 길이·엉덩이 하강 둘 중 하나가, **런지는 양발 간격 하나만** 막는다(양발 간격을 빼면 런지 3개가 남는다).

**조건별 여유(margin)** (기준값까지 거리. 정상은 기준 안쪽 최악값, 비스쿼트는 기준을 통과하는 쪽에 가장 가까운 후보)

| 조건 | 기준 | 정상 최악값(기준과의 여유) | 걷기 최근접(여유) | 의자 최근접 | 런지 최근접(여유) |
|---|---|---|---|---|---|
| 길이 ≥ 1.0초 | 1.0 | 2.06 (1.06) | 0.82 (**0.19**) | 4.76 (통과) | 2.99 (통과) |
| 엉덩이 하강 ≥ 0.25 | 0.25 | 0.34 (0.09) | 0.07 (**0.18**) | 0.45 (통과) | 0.59 (통과) |
| 양발 간격 ≤ 0.25 L | 0.25 | 0.05 (0.20) | 0.006 (통과) | 0.006 (통과) | 0.55 (**0.30**) |
| *(제거)* 몸통 ≥ 30° | 30 | 39.3 (9.3) | 8.0 (22.0) | −2.5 (32.5) | 20.5 (**9.5**) |
| *(제거)* sit ≤ 0.25 | 0.25 | 0.00 (0.25) | 0.00 (통과) | 0.51 (0.26) | 0.00 (통과) |

- 걷기를 막는 두 조건의 여유는 0.19초와 0.18(다리 길이 비)로 좁다. 런지의 양발 간격은 0.30으로 가장 넓다. 몸통 조건은 런지에서 정상 쪽 여유(9.3°)와 비스쿼트 쪽 여유(9.5°)가 같아 틈이 좁고, 몸통을 세우는 스쿼트를 탈락시키는 문제가 있어 제거한다.

### 2. 배제 조건 결정 (확정)
- **제거: 몸통 숙임 ≥ 30°.** 상체가 꼿꼿한 정상 스쿼트(고블릿, 프론트 등)를 탈락시킨다. torso_shin 판정과도 충돌한다.
- **제거: sit 비율 ≤ 0.25.** sit은 실제 스쿼트가 오분류되는 대상이라 배제 목록에서 뺀 라벨이므로 일관성을 유지한다.
- **유지: 길이 ≥ 1.0초, 엉덩이 하강 ≥ 0.25(걷기 배제), 양발 간격 ≤ 0.25 L(런지 배제, 측면 전용).**
- **의자 앉았다 일어나기는 위 조건으로 걸러지지 않으므로 거르지 않는다.** 박스 스쿼트와 동작이 같다. RELEASE.md의 한계에 "의자·박스를 이용한 동작도 스쿼트로 셀 수 있음"을 기록했다. 회귀 테스트가 이 동작(세션 8b: 3회 셈)을 고정해 둔다.
- **게이트 확인**: 유지한 3개 조건으로 걷기·런지가 남지 않았다(위 표). 따라서 Phase 2로 진행했다.

### 3. Phase 3 계획 수정 (구현은 Phase 2 이후, 사용자 확인 후)
이전 계획(3-1~3-4, 항목 3개)을 아래로 **수정**한다. 구현하지 않았다.
- 판정 항목을 **depth, torso_shin 두 개**로 줄인다. **heel은 판정·점수·화면에서 제외하고 원자료만 기록**한다(RepResult의 `heel_rise_bottom_px/_norm`). 이유: 뒤꿈치 세션이 정상과 구분되지 않음(AUC 0.45~0.68), 방향에 따른 약 10px 치우침.
- depth: 정상 ≤ 80°, 교정 ≥ 95° (교정선은 가정). torso_shin: 정상 ≤ 25°, 교정 ≥ 35° (교정선은 가정).
- **depth가 교정이면 torso_shin은 판정하지 않고 기록만 한다**(얕은 반복의 이중 감점 방지).
- 점수(3-2)는 두 항목만 반영한다. 템포는 이전과 같이 판정·점수에 쓰지 않는다. 화면 표시(3-3)와 테스트(3-4)는 두 항목 기준으로 바꾼다.
- 모든 값은 초기값이며 **2차 실측으로 검증한 뒤 확정**한다.

### 4. Phase 2 구현
| 구분 | 파일 |
|---|---|
| 신규 | `src/rep_tracker.py`(RepTracker, RepFrame, RepMeasures, RepResult, `measure_frame`, `track_primary_person`) |
| 수정 | `src/geometry_tracker.py`(BodyLock 정책 교체, `reset()`), `src/exercise_counter.py`(RepTracker 주입), `src/sequence_logger.py`(`record(geometry=)`), `src/main.py`(연결), `config/settings.py`(상수) |
| 테스트 | `tests/test_rep_tracker.py`(신규), `tests/test_sequence_logger.py`·`tests/test_plot_landmark_sequence.py`(잠금 정책 변경에 맞춰 8개 수정, 정책 테스트 추가) |
| fixture | `tests/fixtures/rep_sessions/session_{1,2,3,4,5,8a,8b,8c,9}.json`(총 약 808 KB) + 추출 스크립트 `scripts/analysis/extract_rep_fixtures.py` |

**ExerciseCounter ↔ RepTracker 인터페이스** (이전 DEVLOG의 "Phase 2 착수 전에 설명" 항목에 대한 설명)
- `ExerciseCounter(rep_tracker=None)`. `rep_tracker`가 있고 **squat 모드**일 때만 `update(stable_pose, current_time, rep_frame)`가 `RepTracker.update(rep_frame, stable_pose)`를 부르고, **확정된 반복(`RepResult.counted`)만** `squat_count`를 올린다. 탈락·중단된 반복은 `last_rep_result`에만 남는다.
- `rep_tracker`가 없으면 v0.1.x와 같이 stable 라벨 `stand → squat → stand`로 센다(기존 테스트 유지).
- stretch 모드와 `ExerciseCounter`의 다른 동작은 바꾸지 않았다. `set_mode`, `reset_current_exercise`, `reset_all_exercises`는 RepTracker도 초기화한다(진행 중인 반복 버림).
- `get_status()`에 `rep_guidance`(`need_side_standing`/`ready`/`in_rep`)와 `last_rep`을 추가했다(화면은 아직 쓰지 않음, Phase 3용).
- 입력 `RepFrame`은 `main`이 `track_primary_person()`으로 만든다: 프레임당 `GeometryTracker.update` 한 번(무릎각 평활화, BodyLock) + `measure_frame`(엉덩이·뒤꿈치 y, 다리 길이, 양발 간격, 프레임 픽셀).

**RepTracker 동작** (상수는 모두 `config/settings.py`)
- 상태: `WAITING_LOCK`(측면으로 서서 잠금 대기) → `STANDING` → `IN_REP` → 완료 시 `STANDING`.
- 반복: 평활 무릎각 ≥ 160°이던 뒤 < 150° → 다시 ≥ 160°. 서 있을 때 기준값(엉덩이·뒤꿈치 y, 다리 길이, 양발 간격)은 내려가기 직전 1.0초의 중앙값.
- 확정: 길이 ≥ 1.0초, 엉덩이 하강 ≥ 0.25, 양발 간격 ≤ 0.25 L, ML 비율(walk+run+lying) ≤ 0.40. 탈락 사유는 `too_short`, `shallow_hip_drop`, `feet_apart`, `other_exercise`, `no_baseline`.
- 중단: 반복 중 잠금이 풀리면 `lock_lost`, 평활 무릎각이 1.5초 넘게 비면 `tracking_lost`.
- `RepResult`에는 확정에 쓰지 않는 원자료도 남긴다: 최저점 몸통·정강이 부호 있는 각, heel 상승량, 하강·체류·상승 시간, 라벨별 시간, 놓침 비율.

**지시에 없던 설계 판단 (확인 요청)**
1. **기하 분석은 squat 모드이거나 로깅 중일 때만 실행**한다(`main`). 꺼져 있다 켜질 때는 `GeometryTracker.reset()`으로 오래된 잠금·평활화를 버린다.
2. **측면이 아니면 반복을 세지 않는다**(잠금이 걸리지 않으므로). 정면·사선에서는 카운트가 0으로 남고 **화면 안내 문구는 아직 없다**(Phase 3의 3-3). v0.1.x는 정면에서 5회 중 2회를 셌으므로, Phase 3 전까지는 사용자에게 "카운트가 안 올라가는" 상태로 보일 수 있다.
3. 온라인 구현은 이동 구간 규칙 대신 길이 ≥ 1.0초 조건으로 같은 후보를 거른다(세션 1~5에서 탈락한 것은 모두 `too_short`).
4. `GeometryTracker`의 잠금 정책을 교체해 기존 테스트 8개가 깨졌고, 의도(잠금 획득·반복 중 고정·다음 서 있는 프레임 갱신·놓침 해제·놓침 타이머)를 유지한 채 새 정책(측면 0.5초 연속)에 맞게 고쳤다. 정책 자체의 테스트를 추가했다(정면 미잠금, 깜빡임, 0.4초 해제, 짧은 돌아섬 유지, 비측면 프레임이 다리·방향을 못 바꿈, 반복 중 시점 변화 무시, 놓침이 연속성을 끊음, reset).
5. 로그의 잠금 이벤트에 `released_view`가 추가되었다(`format_version`은 그대로, 값만 늘었다).
6. ML 비율의 분모는 라벨 `None`(미검출) 시간을 뺀 시간이다. 라벨이 전혀 없으면 비율 0으로 보고 `pose_missing_ratio`로만 남긴다.

**회귀 테스트와 ablation 재확인** (`tests/test_rep_tracker.py`, fixture는 판정에 쓰는 값만: 평활 무릎각, 라벨, 잠금·다리·방향, 부호 있는 각, 엉덩이·뒤꿈치 y, 다리 길이, 양발 간격. **얼굴 landmark와 landmark 배열은 없다**, 테스트가 이를 확인)
- 세션 1~5: 검출 10, 8, 8, 8, 8회로 **실제 횟수와 일치**(탈락한 것은 세션 앞뒤 `too_short` 후보뿐). 8a, 8c는 0회(8a는 `too_short`, 8c는 `feet_apart`).
- 8b(의자)는 3회로 센다(알려진 한계를 고정). 세션 9는 횟수를 단언하지 않고 반대 방향의 부호 있는 각도(몸통 > 30°, 정강이 > 15°, 모두 양수, facing=right)만 검증한다.
- 한쪽 조건만 켠 재생(`GEOMETRY_ONLY`, `ML_ONLY`, 같은 fixture):

| 설정 | s1 | s2 | s3 | s4 | s5 | 8a | 8b | 8c | s9 |
|---|---|---|---|---|---|---|---|---|---|
| 실제 | 10 | 8 | 8 | 8 | 8 | 0 | - | 0 | - |
| 확정(기하 + ML) | 10 | 8 | 8 | 8 | 8 | 0 | 3 | 0 | 6 |
| ML 끔(기하 3개만) | 10 | 8 | 8 | 8 | 8 | 0 | 3 | 0 | 6 |
| ML 끔, 길이 뺌 | 10 | **9** | 8 | 8 | 8 | 0 | 3 | 0 | 6 |
| ML 끔, 양발 간격 뺌 | 10 | 8 | 8 | 8 | 8 | 0 | 3 | **3** | 6 |
| 기하 전부 끔(ML만) | 10 | 8 | 8 | 8 | 8 | 0 | 3 | 0 | 6 |

  기하 조건만으로도, ML 조건만으로도 걷기·런지는 걸러진다(서로 겹쳐서 보호). 길이 조건은 세션 2 끝의 돌아섬 굴곡을, 양발 간격은 런지를 막는 유일한 기하 조건이다. 엉덩이 하강은 이 데이터에서 길이와 겹쳐 단독 기여가 보이지 않는다(그래도 사용자 확정대로 유지). 이 관계를 `test_geometry_conditions_alone_are_enough_without_the_ml_condition` 등 4개 테스트가 고정한다.

### 임계값 변경 이력
- 신규(모두 field_test_1 한 사람·하루 기반 **초기값**): `BODY_LOCK_ACQUIRE_SIDE_SECONDS = 0.5`, `BODY_LOCK_RELEASE_NONSIDE_SECONDS = 0.4`, `REP_DESCENT_KNEE_ANGLE = 150.0`, `REP_MAX_GAP_SECONDS = 1.5`, `REP_MIN_SECONDS = 1.0`, `REP_MIN_HIP_DROP = 0.25`, `REP_MAX_ANKLE_GAP = 0.25`, `REP_OTHER_EXERCISE_LABELS = (walk, run, lying)`, `REP_OTHER_EXERCISE_MAX_RATIO = 0.40`, `REP_BASELINE_SECONDS = 1.0`, `REP_BOTTOM_PLATEAU_DEGREES = 10.0`. `STANDING_KNEE_ANGLE = 160.0`, `BODY_LOCK_MISSING_RELEASE_SECONDS = 2.0`은 그대로.
- 제거·미반영: 몸통 ≥ 30°, sit 비율 ≤ 0.25(조건에 넣지 않음). Phase 3의 depth·torso_shin 경계는 아직 `settings.py`에 넣지 않았다.

### 테스트 결과
- 구현 전 기준선: `tests/` 181 passed, `backend/tests` 37 passed.
- 구현 후: `tests/` **240 passed**, `backend/tests` 37 passed(합계 277). 카메라는 실행하지 않았다. 실제 `src.main` 실행(웹캠)으로 통합을 확인하지는 않았다(사용자 허락 필요). `main`의 연결은 `track_primary_person`·`ExerciseCounter`의 단위 테스트로만 검증했다.

### 남은 과제
- **2차 실측 필요**: 이번 실측 데이터는 값을 정하는 데 썼으므로 릴리스 전에 다른 날, 가능하면 다른 사람으로 검증한다. 임계값(길이 1.0초, 엉덩이 하강 0.25, 양발 간격 0.25, Y 0.40, 잠금 0.5/0.4초, depth·torso_shin 경계)은 모두 이 한 사람의 데이터에서 나왔다.
- 정면·사선에서 안내 문구가 없다(Phase 3).
- 양발 간격 조건은 측면 전용이며 런지를 막는 유일한 기하 조건이라 2차 실측에서 우선 확인한다(걷기·런지·의자 3회씩만 있음).
- 의자·박스 동작은 센다(한계). heel은 판정하지 않는다(재측정은 선택).
- 세션 9의 실제 횟수는 불확실한 채로 둔다.

---

## 2026-10-18 · Phase 2 후속: 엉덩이 하강 임계값 조정, 안내 문구(Phase 2로 당김), v0.1.x 전환 스위치, 테스트 수정 내역

### 승인 기록 (사용자)
- **기하 분석을 squat 모드 또는 로깅 중에만 실행하고 켜질 때 `reset()`을 호출**하는 설계: **승인.**
- **ExerciseCounter ↔ RepTracker 인터페이스 설명을 DEVLOG로 대신한 것: 승인.**

### 1. 엉덩이 하강 임계값 0.25 → 0.20
**문제**: 0.25는 정상 쪽 여유가 0.09, 걷기 쪽 여유가 0.18로 정상 쪽에 치우쳐서, 하프 스쿼트보다 조금 얕은 반복이 "얕음" 판정(Phase 3) 없이 아예 세지지 않을 위험이 있었다.

**분포** (온라인 RepTracker 재생값, 길이 ≥ 1.0초인 후보 = 실제 반복, 조건을 모두 끈 상태에서 측정)

| 세션 | 반복 수 | 엉덩이 하강 최소 (몇 번째) | 중앙값 | 최대 |
|---|---|---|---|---|
| 1 평행 | 10 | 0.535 (2번째) | 0.550 | 0.600 |
| 2 깊게 | 8 | 0.611 (1번째) | 0.644 | 0.679 |
| **3 얕음** | 8 | **0.331 (8번째)** | 0.382 | 0.428 |
| 4 상체 숙임 | 8 | 0.418 (4번째) | 0.481 | 0.512 |
| 5 뒤꿈치 들림 | 8 | 0.492 (4번째) | 0.538 | 0.608 |
| 9 반대 방향 | 6 | 0.573 (4번째) | 0.581 | 0.594 |

- **가장 얕은 정상 반복: 세션 3의 8번째, 엉덩이 하강 0.331, 최저 무릎각 약 100°.** 그다음은 세션 3의 6번째(0.341, 102°), 5번째와 7번째(0.342), 1번째(0.382). 얕은 5개가 모두 세션 3이다(세션 9를 빼도 같다).
- **걷기(세션 8a) 최대: 0.085**(후보 14개 중). 의자 0.39~0.45, 런지 0.55~0.59는 모두 높아서 이 임계값과 무관하다.
- 두 값의 중앙은 0.208이다. **0.20으로 정했다**(요청 범위 0.18~0.20 안에서 중앙에 가장 가깝다). 여유는 정상 쪽 0.131, 걷기 쪽 0.115로 균형이 잡힌다(0.18이면 0.151/0.095, 0.19이면 0.141/0.105).
- 참고: 오프라인 분석(report.md)의 값은 정상 최소 0.341, 걷기 최대 0.074였다. 온라인은 기준값을 "내려가기 직전 1초 서 있는 프레임"의 중앙값으로 구해 약 0.01 차이가 난다. 임계값은 온라인(실제 동작) 값으로 정했다.
- **외삽(참고용)**: 48개 반복에서 엉덩이 하강 ≈ 0.0070 × (175 − 최저 무릎각) − 0.180 (r = 0.95). 이 관계로 0.20은 최저 무릎각 약 120°, 이전 0.25는 약 113°에 해당한다. **데이터는 무릎 57~102°, 하강 0.33~0.68 범위뿐이라 120° 부근은 외삽이며 검증되지 않았다.**
- 회귀 테스트(세션 1~5 횟수 10, 8, 8, 8, 8, 8a·8c 0회)는 그대로 통과한다. 변경 후 한쪽 조건만 켠 재생도 같은 결과다. 엉덩이 하강 0.22(무릎 125°)인 합성 반복은 세어지고 0.15는 `shallow_hip_drop`으로 탈락하는 테스트를 추가했다.
- **쿼터 스쿼트 데이터는 없다.** 가장 얕은 실측이 무릎 약 100°(하프)라서, 0.20이 쿼터 스쿼트를 올바르게 세는지는 알 수 없다.

### 정정: 이전 ablation의 "길이 조건" 결론
- 앞선 항목의 재생 표("ML 끔, 길이 뺌 → 세션 2가 9회")는 **fixture에 기록된 옛 임시 정책의 잠금값**으로 재생한 결과다. 새 BodyLock 정책(측면 0.5초 연속 획득, 서 있을 때 비측면 0.4초 해제)으로 다시 재생하면 **세션 1 시작과 세션 2 끝의 이동 굴곡은 잠금이 없는 구간이라 후보로 잡히지도 않는다.** 그래서 "길이 조건은 세션 2 끝의 돌아섬 굴곡을 막는 유일한 조건"이라는 설명은 새 정책에서는 맞지 않다.
- **새 정책에서 확인한 관계**(ML 끔, 기하만): 길이와 엉덩이 하강은 **서로 겹쳐서 보호**한다. 하나만 있어도 세션 5 끝의 0.23초 굴곡과 걷기(8a)가 걸러지고(8회, 0회), 둘 다 빼면 9회, 13회가 된다. 양발 간격을 빼면 런지가 3회 남는다(런지를 막는 유일한 기하 조건).
- 회귀 테스트도 이에 맞게 고쳤다(아래 3번의 목록 참고).

### 2. 안내 문구 (Phase 3에서 Phase 2 범위로 당김, 점수·피드백은 여전히 Phase 3)
- squat 모드에서 BodyLock이 `LOCK_GUIDANCE_DELAY_SECONDS`(초기값 2.0초) 넘게 잡히지 않으면 화면 영상 아래쪽 띠에 사유별 한 줄을 보인다. **잠금이 잡히면 바로 지운다.**
  - 측면이 아님 → "카메라 쪽으로 옆모습이 보이게 서주세요"
  - 전신 무효 → "발끝까지 화면에 들어오게 서주세요"
- 사유 판정(`RepTracker.notice`, `get_status()["rep_notice"]`): 잠금이 안 잡힌 동안 프레임마다 사유를 정한다(전신 무효가 우선, 아니면 측면 아님, 둘 다 아니면 사유 없음). **최근 지연 시간 동안 가장 많았던 사유**를 안내한다. 가장 많은 것이 "사유 없음"(측면이고 전신이 보이지만 아직 0.5초가 안 지남)이면 안내하지 않는다. 사람이 없는 프레임은 사유가 아니고, 지연 시간보다 오래 없으면 처음부터 센다. 반복 중(잠금 유지)에는 나오지 않는다.
- **한글 렌더링(지시에 없던 판단, 확인 요청)**: UI의 `cv2.putText`(HERSHEY 폰트)는 한글을 그리지 못한다. 안내 한 줄만 **Pillow + `malgun.ttf`**(Windows 기본 한글 폰트)로 그리고, Pillow나 한글 폰트를 못 찾으면 **영어 문구**("TURN SIDEWAYS TO THE CAMERA", "STAND SO YOUR FEET ARE IN VIEW")로 대체한다. 합성 프레임으로 한글·영어 대체·문구 없음 세 경우를 눈으로 확인했다.
  - 한계: Pillow(12.2.0)는 `packaging/ai_client/requirements-lock.txt`에는 있지만 `requirements.txt`에는 없고 앱 코드가 직접 쓴 적이 없다. **PyInstaller 빌드에 Pillow가 들어가는지, 설치 환경에 `malgun.ttf`가 있는지는 확인하지 못했다**(빌드는 만들어 보지 않았다). 못 찾으면 영어 문구로 나온다. `requirements.txt`에 pillow를 넣을지는 결정하지 않았다.
- 문구 위치는 영상 영역 아래 반투명 띠이며 오른쪽 패널(카운트 등)은 건드리지 않는다. 실제 카메라 화면의 가독성은 확인하지 못했다(사용자 확인).
- 실측 신호로 확인(새 BodyLockPolicy로 재생):
  - 정면(세션 7): 잠금이 한 번도 안 걸리고, 9.4초부터 반복 구간 내내 "측면 아님". 5회를 해도 0회.
  - 사선(세션 6): 잠금이 10.7초에 한 번 걸렸다가 0.4초 뒤(11.1초) 해제되고(옆을 지나가는 순간), 13.2초부터 반복 구간 내내 "측면 아님". 0회.
  - 측면(세션 1~5): 잠금이 걸리면 문구가 사라지고 잠긴 동안 항상 없다. 잠기기 전 자리 잡는 동안(약 4~5초부터)에는 "전신 무효" 안내가 먼저 뜬다. 세션 1은 끝에서 돌아서면 해제(58.4초, 66.8초)되고 이후 "전신 무효"가 뜬다.
- 새 fixture 세션 6(사선), 7(정면)을 추가했고, 모든 fixture에 `side_now`, `valid`, `facing_now`, `leg_now` 컬럼을 넣었다.

### 3. 기존 테스트 수정 내역 (잠금 정책 교체로 깨진 8개 + 보강 1개 + 이번에 바꾼 Phase 2 테스트 1개)
공통 이유: 이전 테스트는 "서 있는 **첫 프레임**에 잠금이 걸린다"는 임시 정책을 전제로 했다. 새 정책은 측면 판정이 0.5초 이어져야 잠그므로 준비 단계를 `locked_tracker()`(0.0초, 0.5초 두 프레임)로 바꿨다. 파일은 모두 `tests/test_sequence_logger.py`(별도 표기 외).

| # | 테스트 이름(바뀐 이름) | 이전 단언 | 새 단언 | 바꾼 이유 | 원래 의도가 검증되는 곳 |
|---|---|---|---|---|---|
| 1 | `test_lock_is_acquired_while_standing` → `test_lock_is_acquired_only_after_the_side_view_holds` | 첫 서 있는 프레임에서 `locked` True, (leg, facing) = (left, right), `event == "acquired"`, `view.is_side`, 다음 프레임 `event None` | 첫 프레임과 0.45초에는 `locked` False. **0.5초 프레임에서** 같은 leg·facing·event·view 단언. 다음 프레임 `event None` | 획득 시점이 0.5초 뒤로 바뀜 | 같은 테스트의 0.5초 단계(획득 내용은 동일), 정면 미잠금은 `test_a_front_view_is_never_locked` |
| 2 | `test_lock_is_frozen_once_the_user_starts_descending` | 서 있는 프레임 한 번 뒤 내려가는 프레임: `standing` False, `event None`, 잠근 leg·facing 유지, `geometry.leg == "left"`, `geometry_now.leg == "right"` | **같은 단언**. 준비만 `locked_tracker()`, 내려가는 시각 0.55초 | 준비 단계가 0.5초 필요 | 같은 테스트. 반복 중 시점 변화는 `test_a_view_change_during_the_rep_does_not_release_the_lock`(신규) |
| 3 | `test_lock_is_refreshed_on_the_next_standing_frame` → `..._next_side_standing_frame` | 다시 서면 `standing`, `event == "changed"`, leg right | **같은 단언**. 준비만 `locked_tracker()`. 이름에 "side" 추가 | 준비. 갱신이 이제 "측면 프레임"에서만 일어남 | 같은 테스트. 비측면 프레임이 갱신 못 함은 `test_lock_leg_and_facing_are_not_updated_by_non_side_frames`(신규) |
| 4 | `test_lock_is_released_after_the_pose_is_missing_for_long_enough` | 서 있는 프레임 뒤 놓침 1.0초 유지, 2.5초 유지, 3.1초 `released_missing`, 해제 뒤 평활화 초기화 | **같은 단언**. 준비만 `locked_tracker(missing_release_seconds=2.0)` | 준비 | 같은 테스트 |
| 5 | `test_seeing_the_person_again_resets_the_missing_timer` | 놓침 1.0 → 다시 보임 1.5 → 놓침 3.0 `locked` True | **같은 단언**. 준비만 변경 | 준비 | 같은 테스트 |
| 6 | `test_frame_record_contains_everything_the_analysis_needs` | 첫 프레임 기록에서 `lock.locked`·leg·facing 단언 포함 전부 | **같은 단언**. 기록 대상 프레임을 0.5초 프레임(잠금이 걸린 프레임)으로 | 첫 프레임은 아직 안 잠김 | 같은 테스트 |
| 7 | `test_recorder_logs_labels_lock_and_geometry_per_frame` | 서 있는 프레임 1개 + 사람 없는 프레임 1개. 첫 프레임 `locked` True·leg·facing·무릎각·라벨, 둘째 프레임 `person` False, `locked` True | 서 있는 프레임 3개(0.10, 0.35, 0.60초) + 사람 없는 프레임. **첫 프레임 `locked` False(새 단언), 셋째 프레임 `locked` True·`event "acquired"`·leg·facing**, 무릎각·라벨·시간 순서는 첫/셋째 프레임에서 같은 단언, 놓침 프레임 단언 동일 | 첫 프레임은 아직 안 잠김 | 같은 테스트 |
| 8 | `tests/test_plot_landmark_sequence.py::test_series_recovers_what_the_tempo_and_heel_analysis_needs` | `series["valid"].all() and series["locked"].all()` | `valid.all()` 그리고 **`not locked[0]` 그리고 `locked[0.6초 이후].all()`** | 처음 0.5초는 설계상 잠기지 않음 | 같은 테스트(잠금 열이 로그에서 복원되고 반복 중에도 유지됨) |
| 9 | `test_invalid_body_does_not_lock_or_smooth` (**깨지지 않았지만 보강**) | 한 프레임을 넣고 `valid` False, 평활값 None, `standing` False, `locked` False | 30프레임(1초)을 넣고 같은 단언 | 새 정책에서는 한 프레임만 보면 "0.5초 전이라 안 잠긴 것"과 구분이 안 되어 단언이 무의미해지므로 | 같은 테스트(더 강해짐) |
| 10 | `tests/test_rep_tracker.py::test_the_minimum_duration_is_what_removes_the_transit_dip_without_ml` (Phase 2에서 만든 테스트, 이번에 교체) | ML 끈 상태에서 길이 조건을 끄면 세션 2가 8 → 9회 | 삭제. 새 정책에서는 맞지 않아 `..._already_keeps_session_start_and_end_dips_out`(세션 1·2의 이동 굴곡이 후보로도 안 잡힘)과 `..._duration_and_hip_drop_each_alone_reject...`(세션 5 끝 굴곡·걷기를 하나만 있어도 거르고 둘 다 빼면 9회, 13회)로 대체 | 위 "정정" 참고 | 대체한 두 테스트 |

- **검증 범위가 줄어든 테스트: 없다.** 8번(`locked.all()` → 0.6초 이후)은 문장은 약해 보이지만 처음 0.5초가 잠기지 않는다는 단언을 더했고, 1~7번은 단언을 그대로 두고 준비 단계만 바꿨거나 단언을 더했다. 9번은 강해졌다.
- 그 밖에 이번 작업에서 **회귀 재생 방식**이 바뀌었다: `tests/test_rep_tracker.py`의 fixture 재생이 이전에는 로그에 기록된 옛 잠금값을 썼지만, 이제 로그의 신호(평활 무릎각, 프레임별 측면 판정, 전신 유효)를 새 `BodyLockPolicy`에 넣어 잠금을 다시 정한다. 결과 횟수(10, 8, 8, 8, 8, 0, 0)는 같다. 새 정책 전체가 실제 신호로 검증되는 대신, 로그 시점의 `lock_leg`/`lock_facing`은 쓰지 않고 프레임의 `leg_now`/`facing_now`를 쓴다.

### 4. v0.1.x 전환 스위치
- `settings.USE_REP_TRACKER`(기본 **True**). False면 `create_exercise_counter()`가 RepTracker 없이 만들어 v0.1.x(stable 라벨 `stand → squat → stand`)로 센다. 이때 로깅이 아니면 기하 분석도 하지 않아 v0.1.x와 같고, 안내 문구도 나오지 않는다. 로깅 중이면 로그에는 계속 잠금·각도를 남긴다.
- 위해 `main`에 `create_exercise_counter()`와 `run_geometry()`(기하 분석을 돌릴지 판단과 reset)를 분리했다. 둘 다 실행 시점의 설정값을 읽는다. `GeometryTracker`의 잠금 판단은 신호만 받는 `BodyLockPolicy`로 분리했다(동작은 그대로, 기존 정책 테스트가 그대로 통과).
- **두 설정에서 전체 테스트 통과**: 실행기가 pytest 시작 전에 `config.settings.USE_REP_TRACKER`를 바꿔 돌렸다. True: 319 passed, False: 319 passed, 기본값(무수정): 319 passed (`tests/` 282 + `backend/tests` 37). 스위치 자체의 테스트도 있다(기본 켜짐은 실행값이 아니라 `settings.py` 소스의 기본값으로 확인, 꺼짐이면 라벨로 세고 켜짐이면 라벨만으로는 안 셈, 꺼짐이면 기하 분석이 안 돎, 로깅 중이면 계속 돎).
- **로깅 헤더의 임계값 스냅샷에 포함됨을 확인**: `settings_snapshot()`이 대문자 상수를 자동으로 담는다. 테스트가 `USE_REP_TRACKER`(실행 중 값), `LOCK_GUIDANCE_DELAY_SECONDS`, `REP_MIN_HIP_DROP`(0.20) 등이 스냅샷과 실제 기록 파일 헤더(`header["settings"]`)에 있는지 확인한다.
- 이 변경은 변이 검사로도 확인했다: 안내를 끔, 지연 무시, 잠금 후에도 안 지움, 시점 변화로 안 풂, 즉시 획득, 임계값 0.25로 복귀 — 6가지 모두 테스트가 실패했다.

### 임계값 변경 이력
- `REP_MIN_HIP_DROP`: **0.25 → 0.20** (근거: 정상 최소 0.331(세션 3 8번째), 걷기 최대 0.085, 중앙 0.208. 쿼터 스쿼트 검증 없음).
- 신규: `USE_REP_TRACKER = True`, `LOCK_GUIDANCE_DELAY_SECONDS = 2.0`(초기값, 근거 없음: 사용자 지정).
- 그 외 값은 그대로.

### 테스트 결과
- `tests/` **282 passed**(이전 240 + `test_lock_notice.py` 41개 + `test_rep_tracker.py` 순증 1개), `backend/tests` 37 passed, 합계 319. `USE_REP_TRACKER` True/False 둘 다, 기본값에서도 통과. 카메라는 실행하지 않았다.
- 실시간 통합 확인(웹캠, 한글 안내 가독성, 실제 잠금 타이밍)은 사용자가 직접 한다.

### 남은 과제
- **2차 실측에 쿼터 스쿼트 세션을 추가해야 한다.** 엉덩이 하강 0.20이 쿼터 스쿼트(무릎 약 120~140° 부근, 외삽)를 세고 걷기와 구분하는지, "얕음" 판정(Phase 3)과 어떻게 이어지는지는 이 데이터로 알 수 없다. 다른 날, 가능하면 다른 사람으로 하프·쿼터·정상 깊이를 모두 포함한다.
- 한글 안내의 패키징 확인(Pillow 포함 여부, 한글 폰트), `requirements.txt`에 pillow를 넣을지 결정.
- 사선 구간에서 잠금이 0.4초 걸렸다가 풀리는 현상(옆을 지나는 순간)이 있다. 반복에는 영향이 없지만 2차 실측에서 확인한다.
- 앞선 항목의 남은 과제는 그대로다(2차 실측, 양발 간격 우선 확인, 의자 한계, heel 미판정, 세션 9 횟수 불확실).

---

## 2026-10-18 · 실시간 확인 결과와 "세트 중간 누락" 진단 (Phase 3 보류, 카운트 판정은 바꾸지 않음)

### 실시간 확인 결과 (사용자가 직접 실행)
- **통과 항목(모두 정상)**: 하프 스쿼트 5회 카운트, 정면 안내 문구, 전신 안내 문구, 한글 가독성, 문구 표시 시 끊김 없음.
- **문제**: 측면 정상 스쿼트를 총 **7회** 수행, **5회 카운트**. 1~3번째 정상, **4~5번째 2회 누락**, 6~7번째 다시 정상.
  - 처음 3회가 세졌으므로 "잠금 전 시작" 문제는 아니고 **세트 중간에 생긴 문제**다.
  - 이 증상은 아래 어느 원인으로도 같은 모양(화면 카운트가 4·5번째에서 안 오르고 6, 7번째에 오름)이 된다. 예를 들어 4·5번째가 160°까지 못 올라와 6번째와 한 반복으로 합쳐지면 카운트는 3 → (4·5번째 정지) → 6번째 끝에서 4 → 7번째 끝에서 5가 되어, 사용자 관찰과 구분되지 않는다(합성 시퀀스로 확인: 7회 중 5회).
- 사용자가 세운 가설(우선순위 순): (1) 반복 사이에 160°까지 안 펴서 4·5번째가 합쳐짐, (2) 세트 중간 잠금 해제 후 재잠금까지 누락, (3) 4·5번째의 walk/run/lying 비율이 0.40 초과.
- **지시에 없던 가설 (4)** 도 같이 본다(아래 2·3번): 쉬지 않고 이어지는 반복에서 엉덩이 기준 높이가 낮게 잡혀 `shallow_hip_drop`으로 탈락.
- RELEASE.md, CHANGELOG.md는 수정하지 않았다(지시).

### 1. 진단 로깅 추가 (카운트 판정은 그대로, 로그 구조만 변경: format_version 2)
- **프레임마다**: `rep`(`state` = WAITING_LOCK / STANDING / IN_REP, `notice`), `lock.detail`(해제·재잠금 상세). RepTracker를 안 쓰면 `rep`는 null.
- **event 줄**(해당 프레임 바로 뒤, 시각은 세션 시작 기준 초):
  - `rep_end`: 반복 후보가 끝날 때마다(확정·탈락·중단). 시작·끝·최저점 시각, `counted`, `reasons`, 각 조건의 측정값(`total_seconds`, `hip_drop_norm`, `ankle_gap_norm`, `other_exercise_ratio`, `pose_missing_ratio`, `min_knee`, `label_seconds`)과 그 기준값(`limits`), `timeout`(무릎각이 1.5초 넘게 비어 중단된 경우. **반복 길이의 상한은 코드에 없다**), `merge_suspects`(그 반복 안의 합쳐짐 의심 횟수).
  - `rep_merge_suspect`: IN_REP 중 무릎각이 직전 최저점보다 20° 이상 올라온 뒤 최고점보다 10° 이상 다시 내려가면(복귀 각도에 닿지 못한 채) 기록. **올라온 최대 무릎각**(`peak_knee`), 복귀 각도까지 모자란 각도(`peak_shortfall`), 직전 최저점·시각을 함께 남긴다(상수 `REP_MERGE_RISE_DEGREES = 20`, `REP_MERGE_DROP_DEGREES = 10`, 진단 전용).
  - `lock`: 획득(`acquired`), 갱신(`changed`), 해제(`released_view`, `released_missing`). 해제는 **사유와 지속 시간**(`reason` = non_side / person_missing, `seconds` = 비측면·놓침이 이어진 시간), 해제 뒤 다시 잠기면 **해제되어 있던 시간**(`unlocked_seconds`)과 이전 해제 사유.
  - `end` 줄에 `events_written`, `events_dropped`.
- **읽는 쪽 호환**: `plot_landmark_sequence.py`는 format_version 1과 2를 모두 읽고(그 외 버전은 거부), v1 로그에는 새 요소를 그리지 않는다. `field_test_1_lib.py`의 로더는 `event` 줄을 건너뛰므로 그대로 읽는다.
- **그래프**(`*_timeline.png`): RepTracker 상태 띠(회색 WAITING_LOCK / 청록 STANDING / 주황 IN_REP), 반복 후보(확정 = 초록, 탈락 = 빨강 + 사유 글자), 합쳐짐 의심 지점(보라 점선 + `peak N`), 잠금 해제 구간(아래 주황 띠 + 사유·초). 터미널에도 event를 한 줄씩 보여 준다(측정값과 기준값을 나란히).
- 합성 로그(합쳐짐과 잠금 해제를 일부러 넣음)로 그래프를 눈으로 확인했다.
- 테스트(`tests/test_rep_diagnostics.py` 20개): 각 이벤트 내용(확정·탈락·중단·JSON 안전), 합쳐짐 의심(올라온 최대 각도, ±3° 흔들림과 15° 오르내림은 의심 아님, 세션 1~5 정상 반복은 의심 0건), 잠금 해제·재잠금 상세, `rep_diagnostics()`, 로그 왕복(상태·이벤트·시각 변환·`end` 집계), **v1 로그 읽기**(v2 로그에서 v2 요소를 빼 v1 모양으로 만들어 읽고 그래프까지), 알 수 없는 버전 거부.
- **기존 테스트 2개를 고쳤다**: `test_logger_writes_header_frames_and_end_in_one_file`(`format_version == 1` → 2), `test_recorder_logs_labels_lock_and_geometry_per_frame`(프레임 목록에 새 `event` 줄이 끼어들어, 프레임만 골라 읽고 잠금 이벤트 줄이 한 개(`acquired`)임을 단언 추가. 기존 단언은 그대로).
- 임시 처리: 이벤트는 프레임과 같은 큐로 쓰이고 가득 차면 버린다(프레임 버림과 같은 방식, `events_dropped`로 알 수 있음).

### 2. 기존 실측 로그로 가능한 점검 (`scripts/analysis/midset_diagnosis.py`, `analysis/field_test_1/midset/`)
입력은 fixture(세션 1~5, 9)이고 새 BodyLockPolicy와 RepTracker로 재생했다. **한계: 이 실측 세션들은 반복 사이에 1.4~2.5초 서 있는 구간이 있다(가장 짧은 것 0.89초). 이번 실시간 확인처럼 쉬지 않고 이어지는 세트는 데이터에 없다.**
- **반복 사이 무릎각 최대값(복귀 각도 160°까지 올라왔는가)** — 세션 1~5, 반복 사이 37곳:
  - 최소 **176.3°**(세션 1의 7번째 뒤), 중앙값 178.7°, 최대 179.4°. **160°에 가장 가까웠던 값도 여유가 16.3°다.** 160° 미만으로 끝난 반복은 한 번도 없다.
  - 반복 순서가 뒤로 갈수록 약간 낮아지는 경향은 있다(전체 Spearman ρ = −0.42, p = 0.011). 하지만 크기는 작다: 세션 1 전반 178.7° → 후반 178.1°, 세션 2 179.3° → 177.8°, 세션 3·4·5는 거의 같음(1° 안팎).
  - 160° 이상에 머문 시간은 최소 0.66초(세션 2의 1번째 뒤), 대부분 1~2.4초. 반복 사이 서 있는 시간(앞 반복 끝 ~ 다음 반복 시작)은 0.89~2.5초이고 후반이 짧아지는 세션(세션 1: 1.87 → 1.54초)이 있다.
  - 그래프: `peaks_by_order.png`.
- **세트 중간 잠금 해제**: 세션 1~5, 9 모두 **세트 중간에 잠금이 풀린 적이 없다.** 해제는 전부 마지막 반복 뒤 돌아서는 구간이다(9건, 모두 사유 non_side, 지속 0.41~0.71초). 사유 person_missing 해제는 없다. 재잠금까지 걸린 시간 0.89, 1.0, 2.05초.
- **정상 반복의 walk/run/lying 비율**(48개): 최대 **0.265**(세션 9의 3번째, `run` 라벨이 서 있는 자세에 붙음), 세션 1~5만 보면 최대 0.223. **0.30을 넘은 반복 0개, 0.40까지 여유 최소 0.135.** 반복 순서별 평균은 0.00~0.08로 세트 후반에 오르는 경향이 없다.
- **합성 시퀀스로 확인한 것(실측이 아니다)**: 쉬지 않고 이어지는 반복에서 4·5번째가 158°까지만 올라오면 현재 규칙은 7회 중 **5회**로 센다(4·5·6번째가 한 반복으로 합쳐짐). 같은 합성 세트에서 **다음 반복의 엉덩이 하강이 0.03~0.04 작게 측정**된다(깊은 반복 0.55 → 0.51, 얕은 반복 0.24 → 0.21): 쉬지 않으면 완료 직후 160° 근처의 몇 프레임으로 기준 높이를 잡기 때문이다(가설 4의 근거).

### 3. 원인별 대응안 (제안만, 구현하지 않음)
**구분 신호**(새 로그에서)

| 가설 | 로그 신호 |
|---|---|
| 1. 160°까지 못 펴서 합쳐짐 | 프레임의 `rep.state`가 4·5번째 사이에서도 계속 IN_REP. **`rep_merge_suspect` 이벤트**(`peak_knee` < 160, `peak_shortfall` 양수)가 4·5번째 부근에 있고, 뒤따르는 **`rep_end` 하나가 평소의 2~3배 길이**(`total_seconds`)이며 `merge_suspects` ≥ 1, `counted` True. 카운트는 합쳐진 반복의 **끝에서 한 번만** 오른다. |
| 2. 세트 중간 잠금 해제 | `lock` 이벤트 `released_view`/`released_missing`(사유·`seconds`)가 반복 사이에 있고, 그 뒤 `acquired`(`unlocked_seconds`). 프레임의 `rep.state`가 WAITING_LOCK. 그 구간의 반복은 **`rep_end` 자체가 없다**(후보가 안 생김). `notice`는 2초 전이라 안 뜰 수 있다. |
| 3. ML 비율 초과 | 4·5번째 각각에 **`rep_end` REJECTED(other_exercise)**, `other_exercise_ratio` > 0.40, `label_seconds`에서 walk/run/lying 비중이 보인다. 반복마다 별개의 짧은 `rep_end`. |
| 4. 엉덩이 기준 높이 하락(새 가설) | `rep_end` REJECTED(**shallow_hip_drop**), `hip_drop_norm`이 0.20에 근접(0.15~0.20), 앞 반복과의 서 있는 간격이 짧다. |

세 가지 모두 같은 카운트 모양을 만들므로 **원인이 로그로 확인되기 전에는 코드를 바꾸지 않는 것을 권한다.** 아래는 각 대응안과 기존 fixture(세션 1~5, 6, 7, 8a~8c, 9) 회귀 영향이다(`variants_*.csv`, `synthetic_return_angle.csv`, `valley_boundary_candidates.csv`).

**가설 1 대응안**
- *A. 복귀 각도를 낮춘다*(내려감 각도도 함께 낮춰야 히스테리시스가 유지됨): fixture 회귀 — 복귀/내려감 155/150, 150/140에서 **횟수 전부 그대로**(세션 1~5 = 10, 8, 8, 8, 8, 사선·정면 0, 걷기 0, 런지 0, 세션 9 = 6). 145/135, 140/130에서는 의자(8b)가 3 → 2회로 바뀐다(스쿼트 데이터는 안 바뀜). 합성 세트(4·5번째가 X도까지만 올라옴): X = 158은 155/150이 해결, X = 150은 145/135가 해결(150/140은 못 함), X = 140은 145/135로도 해결되지 않음(복귀 각도를 140 아래로 내려야 함), 4회가 155에서 멈추는 피로 시나리오는 150/140이 해결. **즉 필요한 값은 이번 로그의 `peak_knee`가 정한다.** **부작용**: 복귀를 덜 편 상태에서 인정하면 다음 반복의 엉덩이 기준이 더 낮아져 하강량이 작게 측정된다(합성: 150/140에서 얕은 반복의 하강 0.24 → 0.16~0.20으로 `shallow_hip_drop` 탈락). 그래서 복귀 각도를 낮추려면 **서 있을 때의 엉덩이 기준을 세트 단위로(잠금 후 서 있던 프레임의 중앙값 등) 잡는 변경이 함께 필요하다.** 걷기·이동 굴곡: 복귀 각도를 낮춰도 걷기(8a) 후보는 길이·엉덩이 하강 조건에서 그대로 전부 탈락(0회).
- *B. "상승 후 일정 각도 이상 회복 + 각속도 부호 전환"으로 경계를 잡는다*: 평활 무릎각 골짜기(바닥)를 prominence로 세어 근사했다. 150° 아래 골짜기 수(확정 조건 적용 전 후보): prominence 40°에서 세션 1~5 = 10, 10, 9, 8, 9(현재 확정 10, 8, 8, 8, 8 — 차이는 끝 이동 굴곡), 사선 5, 정면 5, **걷기 17**, 의자 3, 런지 3, 반대 방향 6. prominence 60°에서 세션 2~4가 현재 확정과 같아진다. 걷기는 어느 prominence에서도 15~17개 후보가 생기며 이를 막는 것은 지금과 같은 길이·엉덩이 하강·양발 간격 조건이다(**경계 방식만 바꾸고 이 조건들을 그대로 두면 걷기·런지 보호는 유지되지만, 이 조합을 끝까지 구현해 재생한 것은 아니다**). 장점: 세트 중간에 160°에 못 닿는 반복을 분리할 수 있다. 단점: prominence 기준값을 새로 정해야 하고 각속도 부호 전환은 평활 신호의 잡음에 민감하다.

**가설 2 대응안**
- 반복 사이의 짧은 해제를 허용하는 **유예**: 예) 세트가 진행 중(마지막 반복이 끝난 지 N초 이내)이면 비측면 해제를 0.4초 → 0.8~1.2초로 늦춘다. 해제 사유별로 처리를 다르게: `non_side`(돌아섬 또는 오검출)는 유예, `person_missing`(2초)은 그대로 두거나 더 길게(4초).
- fixture 회귀: 비측면 해제 0.4/0.8/1.2/2.0초, 놓침 해제 4초 모두 **횟수 전부 그대로**(세트 중간 해제가 한 번도 없어서). **사선·정면(6, 7)은 그대로 0회**(측면 전용 유지). 위험: 세트 끝에서 돌아설 때 해제가 늦어진다(실측 돌아섬은 0.41~0.71초).

**가설 3 대응안**
- *A. Y 완화*(0.40 → 0.5~0.7): fixture 회귀 — **모든 세션의 횟수가 그대로**(Y = 0.4~0.7 동일). 걷기·런지는 기하 조건이 막는다(런지의 ML 비율 0.49~0.56은 Y = 0.5에서 일부 통과하지만 양발 간격이 막음).
- *B. ML을 보조(기록·경고)로만 쓴다*(기하 조건이 1차): ML을 완전히 끈 재생도 **모든 횟수가 그대로**다. 잃는 것은 이번 데이터에 없는 동작(달리기·눕기)에 대한 방어선이다. 절충: ML은 `run`/`lying`이 반복 구간의 절반을 넘을 때만 탈락시키는 식으로 상한을 높게(0.6 이상) 두기.
- 근거: 실측 정상 반복의 ML 비율 최대 0.265(여유 0.135), 순서에 따른 상승 없음. 가설 3이 맞다면 라벨 분포가 실측과 크게 다른 환경이라는 뜻이라 `label_seconds`를 보고 정해야 한다.

**가설 4 대응안**: 서 있을 때의 엉덩이 기준을 반복마다 직전 1초가 아니라 **세트 단위의 서 있는 기준**(잠금 후 서 있던 프레임의 중앙값 또는 완전히 섰을 때의 값)으로 잡는다. 이 변경은 가설 1의 A안과 겹친다. fixture 영향: 반복 사이 서 있는 시간이 1.4초 이상이라 기준이 거의 같아 횟수는 그대로일 것으로 보이지만 **재생해 확인하지는 않았다.**

### 4. 진단 계획 (사용자 실행 → 내가 분석)
1. 사용자가 로깅을 켜고 같은 상황(측면 정상 스쿼트를 **쉬지 않고 연속 7~10회**)을 재현한다.
   예) `python -m src.main --log-sequence --session-posture normal --session-view side --session-note "continuous10"` (얼굴 landmark는 기본으로 저장하지 않음, 카메라 실행은 사용자).
2. `python scripts/analysis/plot_landmark_sequence.py --session data/landmark_sequences/<파일>.jsonl`로 그래프와 event 목록을 본다(어떤 가설인지 위 "구분 신호"로 판정).
3. 결과를 보고 원인을 확정한 뒤 대응안을 정해 사용자 확인을 받고 구현한다. Phase 3은 그 뒤.

### 임계값 변경 이력
- 신규(진단 전용, 카운트에 영향 없음): `REP_MERGE_RISE_DEGREES = 20.0`, `REP_MERGE_DROP_DEGREES = 10.0`. 그 외 값은 그대로.

### 테스트 결과
- `tests/` **302 passed**(이전 282 + `test_rep_diagnostics.py` 20개), `backend/tests` 37 passed, 합계 339. `USE_REP_TRACKER` 꺼짐에서도 339 passed. 카운트 판정은 바뀌지 않았다(세션 1~5 횟수 회귀 테스트가 그대로 통과). 카메라는 실행하지 않았다.
- 테스트 실행 시간이 들쭉날쭉했다(5초 ~ 85초): 사용자 말대로 다른 학습 프로세스가 돌아가는 영향으로 보고 코드 문제로 보지 않았다.

### 남은 과제
- 연속 7~10회 재현 로그로 원인 확정(위 4번), 확정 후 대응안 선택.
- 이전 항목들의 남은 과제는 그대로다(2차 실측에 쿼터 스쿼트 포함, 한글 안내 패키징, 의자 한계, heel 미판정, 세션 9 횟수 불확실).

---

## 2026-10-19 · 커밋 전 점검과 저장소 정리 (브랜치 `feature/v0.2.0-squat-quality`)

### 점검 결과 (변경·추적 안 된 파일 161개, 13.8MB)
- **커밋 제외 3종류**
  1. **POLAR overlay 이미지 45개(5.3MB, `analysis/overlays/`)**: POLAR 사진 위에 랜드마크·bbox를 그린 이미지다. 한 장을 열어 보니 사진 속에 **식별 가능한 인물(어린이 포함)** 이 있고 데이터셋 라이선스 문제도 있어 올리지 않는다.
  2. **샘플 단위 CSV 1개(`overlay_samples.csv`)**: POLAR sample_id별 무릎각·가시성·near_leg 행이다. 집계표(`failed_by_class.csv`, `knee_angle_percentiles.csv`)는 제외 대상이 아니다.
  3. **실측 세션별 그래프 26개(5.5MB, `field_test_1/plots/session_*.png`)**: 로그 1개를 그대로 그린 시간축 그래프다. 사진·얼굴은 없지만 **로그 1:1 렌더링이라 스크립트로 다시 만들 수 있고, 재실행마다 바뀌는 바이너리라 저장소가 불어난다**(사용자 결정).
- **이미 제외되어 있던 것**: 실측 로그 원본 `data/landmark_sequences/*.jsonl` 13개(약 35MB, 얼굴 landmark 미저장이지만 로컬 전용)와 `data/landmark_sequences/plots/`, `backend/.env`, `__pycache__`. 로그의 복사본이 저장소 안 다른 위치에 있는지 전수 검색했고 없었다. 실측 영상·스크린샷·분석 캐시(`.pkl`, `.npz`, `.parquet`)도 없었다.
- **비밀 정보**: 후보 텍스트 81개를 검색했고 실제 키·토큰은 없었다(`test_sequence_logger.py`의 supabase 값은 테스트용 가짜 값).
- **커밋 대상 판단**: 소스·테스트·분석 스크립트·문서, 집계 그래프 9개, 집계표, `tests/fixtures/rep_sessions/`(11개 파일, 합계 1,187,949바이트, 얼굴 좌표·원본 landmark 없음을 기존 테스트가 확인).
  - 남은 이미지 9개: `knee_angle_hist`, `side_ratio_hist`, `threshold_metric_distributions`, `nonsquat_features`, `ml_label_share_by_phase`, `view_signals`, `session0_turn_lock`, `rep_extraction_overview`, `peaks_by_order`. 이 중 **`rep_extraction_overview`(13개 세션을 한 장에)와 `session0_turn_lock`(세션 0의 한 구간)은 성격상 로그 렌더링에 가깝다**. 파일명 규칙(`session_*.png`)에 걸리지 않아 남겼고, 사진·얼굴은 없다.
- **5MB 이상 파일**: 이번에 추가되는 파일 중에는 없다.

### `.gitignore` 적용 내용
- 적용: `docs/versions/*/analysis/overlays/`, `docs/versions/*/analysis/*_samples.csv`, `scripts/analysis/.cache/`, `docs/versions/*/analysis/.cache/`, `.pytest_cache/`.
- **범위 축소**: `*.pkl`, `*.npz`, `*.parquet`은 전역 규칙 대신 분석 폴더로 한정(`scripts/analysis/**/*`, `docs/versions/*/analysis/**/*`).
- **추가**: `docs/versions/*/analysis/field_test_*/plots/session_*.png`(세션별 그래프. 같은 폴더의 집계 그래프는 커밋).
- 적용 결과: `git status` 161건 → 89건(overlay 45 + 샘플 CSV 1 + 세션별 그래프 26 = 72건이 빠짐).
- **문서 안의 `D:\LDH_PRG_CV\...` 경로는 수정하지 않는다**(사용자명이 없는 데이터 출처 기록이고 DEVLOG는 추가 전용이다). 위치: DEVLOG, `phase05_report.md`, `phase0_report.md`.

### 백업이 필요한 것 (저장소가 보관하지 않음)
- **실측 로그 원본**(`data/landmark_sequences/session_*.jsonl` 13개)과 **POLAR overlay 이미지 45개 + 샘플 CSV**는 버전 관리 밖(작업 폴더의 로컬 디스크)에만 있다. 세션별 그래프도 로그가 있어야 다시 만들 수 있다. **별도 백업이 필요하다**(분실하면 field_test_1의 로그 기반 재분석과 overlay 확인을 다시 할 수 없다). 저장소 안에는 분석에 쓴 판정용 값만 `tests/fixtures/rep_sessions/`에 남는다.

### 이번 범위 밖 (후속 검토)
- 이미 추적 중인 대용량 파일: `docs/FitRoute-AI-Exercise-Assistant.pptx` 26.0MB, `models/detector/yolo26n.onnx` 9.5MB, `models/pose/pose_landmarker_full.task` 9.0MB, `models/detector/yolo26n.pt` 5.3MB. 건드리지 않았다. **Git LFS 또는 릴리스 첨부로 옮길지는 추후 검토 후보**다(이미 히스토리에 들어 있어 옮겨도 저장소 크기는 줄지 않는다). 무시된 큰 파일: `desktop_launcher/dist/FitRouteLauncher.exe` 60.5MB, `models/detector/yolo26n.engine` 7.4MB, 무시된 폴더 `dist_candidate_protoc` 약 4.9GB, `installer_output` 약 4.5GB.

### 커밋 구조와 이유
- 이번에 Phase 1~4와 후속 작업을 쌓아 두었다가 한 번에 커밋하게 되었다(아래 규칙으로 방지한다).
- **의존 순서 때문에 기능마다 테스트를 같은 커밋에 넣지 못했다**: `main.py`가 새 모듈 전부를 import하고, `test_rep_tracker.py`가 `test_sequence_logger.py`의 헬퍼를 import하며, `test_sequence_logger.py`가 `src.main`을 import한다. 그래서 **소스를 의존 순서로 먼저 커밋하고(각 커밋 시점에 그때 존재하는 테스트가 통과하도록), 새 테스트와 fixture는 그 뒤에 묶었다.** 한 파일 안에 여러 기능이 섞인 `settings.py`는 상수 블록별로 나눠 각 커밋 시점의 버전을 스테이징했고, `main.py`는 안내 문구(UI) 부분만 따로 나눴다. 새 파일(`rep_tracker.py`, `sequence_logger.py` 등)은 초안 단계의 이전 버전을 복원하지 않고 최종 내용으로 커밋했다(그래서 RepTracker 커밋에 안내 사유와 진단 이벤트 코드가 함께 들어 있다).
- 각 커밋은 임시 worktree(깨끗한 체크아웃)에서 `tests/`와 `backend/tests`를 돌려 확인했다. **깨끗한 체크아웃에서는 기준선(`main`의 HEAD)에서도 `tests/test_paths.py::test_development_model_files_exist_at_configured_paths` 1건이 실패한다**(gitignore된 `models/detector/yolo26n.engine` 파일을 요구하는 환경 의존 테스트, 이번 변경과 무관). 모든 커밋이 이 1건 외에는 전부 통과했고 마지막 커밋 시점에는 338 passed + 이 1건이다(작업 폴더에서는 engine 파일이 있어 339 passed).
- 한 가지 알려진 문제: `analysis/phase05_report.md`가 제외한 `overlays/*.jpg`를 이미지 링크로 걸고 있어 저장소에서는 그 링크가 깨진다(내용은 수정하지 않았다).
- push와 main 병합은 하지 않았다.

### 앞으로의 규칙
- **각 Phase 또는 의미 있는 작업 단위가 끝날 때마다 커밋한다.** 이번처럼 변경을 쌓아두지 않는다. 커밋은 사용자 확인 전에는 push·병합하지 않는다.

---

## 2026-10-19 · 가설 5 사전 검증 (합성)

- 휴지 없는 연속 합성 무릎각(봉우리 162·165·170°, 바닥 85°, 주기 2.5·2.0·1.5 s, FPS 8·15·30, 샘플 위상 2종)을 현재 One Euro 파라미터로 평활해 봉우리가 얼마나 깎이는지 쟀다. 결과표와 해석: `analysis/hypothesis5_synthetic.md`, 재생: `python -m scripts.analysis.hypothesis5_synthetic --markdown`.
- **160°에 못 미치는 조건은 1개**(봉우리 162° · FPS 8 · 주기 1.5 s, 평활 봉우리 159.3°). 165° 이상은 전 조건 통과. 깎임은 FPS 30에서 0.5~0.8°, 15에서 0.9~1.7°, 8에서 1.6~2.7°.
- 실측 로그의 처리 속도는 중앙값 약 17 FPS라 깎임은 약 1.0~1.5°다. **평활 단독으로는 원본 봉우리가 160~162°일 때만 문제**가 되고, 그보다 낮으면 원본이 이미 못 닿는 것이라 가설 1(복귀 각도)이다. 재현 로그의 `knee`(원본)와 `knee_smoothed`의 반복 사이 최대값을 비교하면 가려진다.

---

## 2026-10-19 · 대응안 후보 4개를 플래그 뒤에 구현 (기본 꺼짐)

세트 중간 누락(실시간 7회 중 5회) 진단에서 나온 대응안을 `config/settings.py`의 플래그로 구현했다. **기본값은 모두 꺼짐이라 카운트 판정의 기본 동작은 바뀌지 않는다.** 재현 로그의 원인이 확인되기 전에 어느 것을 켤지 정하지 않는다.

| 플래그 | 가설 | 내용 |
|---|---|---|
| `REP_SET_BASELINE_ENABLED` (+`_WINDOW_SECONDS` 30, `_MIN_SAMPLES` 5, `_HIP_PERCENTILE` 25) | 4 | 서 있을 때 기준값(엉덩이·뒤꿈치 y, 다리 길이, 양발 간격)을 직전 1초가 아니라 잠금이 유지되는 동안 최근 30 s의 완전히 선(무릎각 ≥160°) 프레임에서 잡는다. 엉덩이 y는 높은 쪽 25% 분위수. 프레임이 부족하면 직전 1초로 복귀. 잠금이 풀리거나 중단되면 비운다 |
| `REP_RETURN_KNEE_ANGLE` (None=꺼짐, 후보 155) | 1 | 반복이 끝나는 복귀 무릎각을 160°에서 내린다. 150° 초과·160° 이하만 허용(아니면 ValueError). **복귀를 낮추면 끝나는 프레임의 엉덩이가 더 낮아 하강량이 모자라므로 세트 기준 높이를 자동으로 함께 켠다** |
| `REP_BOUNDARY_SIGNAL` (`smoothed`/`light`/`raw`, `_LIGHT_MIN_CUTOFF` 4.0) | 5 | 반복 경계(내려감·복귀) 판정에만 가벼운 평활 또는 원본 무릎각을 쓴다. STANDING 판정(잠금 정책)과 최저점 계산은 기존 평활값 그대로. `GeometryTracker`가 `TrackedFrame.knee_angle_boundary`를 만들고 `RepFrame.knee_boundary`로 전달한다(없으면 평활값) |
| `BODY_LOCK_RELEASE_GRACE_SECONDS` (0=꺼짐, 후보 0.6) | 2 | 잠금 해제 기준 0.4 s에 이 시간을 더한다 |

- **fixture 변경**: `knee_raw`(평활 전 무릎각) 열을 끝에 추가했다. 나머지 열은 재추출 전후 비교로 동일함을 확인했다. 얼굴 landmark·원본 landmark는 여전히 없다(기존 테스트가 확인). 로그 형식(`format_version`)은 바뀌지 않는다(원본 `knee`는 이미 기록되고 있었다).
- **재생 스크립트**: `python -m scripts.analysis.replay_flags --matrix [--log <재현 로그>]`로 플래그 조합을 바로 재생한다(`--set-baseline --return-angle 155 --lock-grace 0.6 --boundary light` 개별 지정도 가능).
- **회귀 결과**(`analysis/flag_replay_matrix.md`): 정확도 세션 1~5는 모든 플래그에서 횟수와 시작 시각이 그대로이고, 정면·사선·걷기·런지는 0회 유지. `raw`만 의자 세션(8b)에서 3→2회로 바뀌고 런지에서 합쳐짐 의심이 6건 생겨 권장하지 않는다. 잠금 유예는 해제를 10→5회로 줄이지만 세션 끝 이동이 탈락 후보로 하나 더 남는다(센 횟수 영향 없음).
- **한계**: 기존 fixture는 반복 사이 휴지가 있어 이 플래그들의 효과(누락 감소)는 이 데이터로 확인할 수 없다. 합성 연속 세트 테스트에서만 효과를 확인했다. 효과 검증은 연속 세트 재현 로그로 한다.
- 테스트: `tests/test_rep_flags.py`(기본 꺼짐 확인, 플래그별 합성 세트, 경계 신호 모드, 잠금 유예, fixture 회귀 × 플래그 6종, 재생 스크립트와 기존 시뮬레이션 일치).

---

## 2026-10-19 · Phase 3 중 반복 경계와 무관한 부분 (1): Pillow 의존성, 안내 렌더링 캐시

### Pillow 의존성과 패키징 확인
- `requirements.txt`에 `pillow==12.2.0`을 추가했다(개발 환경 `vision_ai`와 빌드 환경 `fitroute_build` 모두 12.2.0 설치 확인. 지금까지는 ultralytics의 간접 의존성으로만 들어와 있었다).
- 기준 spec(`packaging/ai_client/FitRouteAIClient.spec`): `excludes`에 PIL이 없다. 한글 렌더링의 `from PIL import ...`는 함수 안 import라 정적 분석에 기대지 않도록 `hiddenimports`에 `PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFont`를 명시했다. spec이 문법상 파싱되는 것까지만 확인했고 **실제 PyInstaller 빌드는 하지 않았다**(시간이 오래 걸리고 요청 범위 밖). `FitRouteAIClient.optimized*.spec` 3개는 후보 실험용이라 손대지 않았다. 다음 빌드 때 프리즈된 앱에서 안내 문구가 한글로 나오는지 확인해야 한다.
- 폰트: `C:/Windows/Fonts/malgun.ttf`(Windows 기본 맑은 고딕)를 찾고 없으면 macOS/Linux 후보, 그래도 없으면 영어 문구로 대체한다. **폰트 파일은 번들하지 않는다**(라이선스, 용량). Windows 외 환경에서 한글이 나올지는 보장하지 않는다.
- 테스트(`tests/test_lock_notice.py`): Pillow import 실패(ImportError 시뮬레이션), 폰트 파일 없음, 매 프레임 폰트 파일 탐색을 하지 않는지(후보 수만큼만 호출) 각각 영어로 대체되고 앱이 계속 도는지 확인한다.

### 안내 문구 렌더링 캐시
- 이전: 안내가 떠 있는 동안 **매 프레임** 띠 영역을 PIL 이미지로 바꾸고 폰트로 글자를 그린 뒤 다시 BGR로 변환했다.
- 지금: 문구·띠 크기·폰트가 바뀔 때만 글자를 그려 알파 레이어(`_notice_text_layer`, `lru_cache`)로 두고, 프레임마다 **영상 위에 정수 연산으로 합성만** 한다. 영상 내용은 캐시에 들어가지 않는다(밝기가 다른 프레임에서 확인). 폰트가 없으면 레이어를 만들지 않고 영어 문구를 쓴다.
- 이전 방식과의 출력 차이: 픽셀 최대 1(반올림), 달라진 픽셀 0.112%.
- **처리 시간 비교**(`python -m scripts.analysis.notice_render_benchmark`, 합성 프레임 600개 640x480+HUD, 한글 폰트 있음, 안내 없음/이전/현재를 프레임마다 순서를 돌려 측정). 측정 중 이 PC에서 다른 학습 프로세스가 돌고 있어 절대값은 흔들리고 **상대 비교만 의미가 있다.**

| 구분 | 이전(매 프레임 PIL) | 현재(캐시 합성) |
|---|---|---|
| 안내 띠 그리기만, 중앙값 | 6.95 ms | 3.74 ms |
| 안내 띠 그리기만, 평균 | 9.47 ms | 5.78 ms |
| HUD 전체, 중앙값(안내 없음 5.44 ms) | 13.39 ms | 9.77 ms |
| 안내로 늘어난 시간(중앙값) | 7.95 ms | 4.33 ms |

  띠 그리기는 약 46% 줄었다. 남은 시간의 대부분은 반투명 띠(`addWeighted`)와 합성의 영역 연산이고 영상(60fps 이하)에서 문제가 되는 크기는 아니다. 안내는 BodyLock이 2초 넘게 안 잡힐 때만 뜨므로 평소 프레임에는 영향이 없다.

---

## 2026-10-19 · Phase 3 중 반복 경계와 무관한 부분 (2): 자세 점수 계산 모듈 (순수 함수만)

`src/posture_score.py`와 `tests/test_posture_score.py`를 추가했다. **RepTracker·화면에는 연결하지 않았다**(호출하는 곳은 테스트뿐). 임계값은 `config/settings.py`의 `POSTURE_*` 상수다.

| 항목 | 측정값 | 정상 | 교정 | 점수 |
|---|---|---|---|---|
| depth | 최저점 무릎각 | ≤ 80° | ≥ 95° (가정) | 정상 100, 교정 0, 사이 선형 |
| torso_shin | 최저점의 \|몸통각 − 정강이각\|(부호 있는 각도) | ≤ 25° | ≥ 35° (가정) | 같음 |

- 규칙: **depth가 교정이면 torso_shin은 판정하지 않고 기록만 한다**(`recorded_only`, 값은 `measures`에 남고 점수·총점에서 빠짐). heel과 템포는 입력 자체가 없다(원자료는 RepResult에만). 결측 항목은 `unavailable`이고 총점은 판정된 항목만으로 계산, 둘 다 없으면 총점 None.
- **가중치** `POSTURE_WEIGHT_DEPTH = POSTURE_WEIGHT_TORSO_SHIN = 0.5`. 근거: 두 항목 모두 field_test_1에서 분리도가 거의 1.0(AUC 1.00 / 0.997)이라 한쪽을 더 무겁게 볼 데이터가 없다. 2차 실측 뒤 조정한다.
- **총점 상한** `POSTURE_SCORE_CAP_WITH_CORRECTION = 50`: 교정 항목이 있으면 총점이 이 값을 넘지 못한다. **가중치가 같으면 교정 항목이 0점이라 자연 최댓값이 이미 50이라서 현재 설정에서는 상한이 실제로 걸리는 경우가 없다.** 가중치를 바꿔도 상한이 지켜지도록 둔 안전장치이고(테스트는 가중치를 0.9/0.1로 기울여 확인), 상한을 더 낮추는 것은 2차 실측 뒤 정한다. 값 자체도 가정이다.
- `worst_item`: 가중 감점(가중치 × (100 − 점수))이 가장 큰 항목, 동점이면 depth, 감점이 없으면 None.
- `feedback_line()`: "78점 · 더 깊게 앉아보세요" 형식의 한 줄. 점수가 없으면 None(안내 문구만 보이는 경우), 감점이 없으면 점수만. 문구는 임시다. 명칭은 코드·화면·문서 모두 "자세 점수"(`SCORE_LABEL`)이고 "정확도"는 쓰지 않는다(테스트가 소스를 확인).
- 테스트 37개: 경계값 직전·직후(80/80.01, 94.99/95, 25/25.01, 34.99/35), 선형 중간·단조 감소, 가중 평균, depth 교정 시 torso_shin 기록만, 얕은 반복의 이중 감점 없음, 상한 적용·비적용, worst_item 선택·동점·가중치에 따른 변화, 결측 처리, 한 줄 피드백, 입력에 템포·heel이 없음, 설정값 확인.
- 아직 안 한 것: RepTracker가 반복 확정 시 점수를 계산해 `RepResult`에 `total_score`/`item_scores`/`worst_item`을 담는 일, 화면의 한 줄 피드백(3-3), 점수·상태의 로그 기록. 반복 경계(대응안)가 정해진 뒤 사용자 지시로 진행한다.

---

## 2026-10-19 · 종료 시 실제 반복 횟수 입력 (footer), `--log-sequence` 전용

2차 실측의 정답 기록용이다. 소리 내어 세기는 쓰지 않는다(실측 환경 제약). **카운트 판정과 화면 동작은 바뀌지 않는다.**

- **동작**: `--log-sequence`로 실행해 **Q/ESC로 종료했을 때만**, 창을 닫은 뒤 터미널에서 "실제 반복 횟수"(Enter로 건너뛰기)와 "특이사항(선택)"을 묻는다. 정수 0~1000만 받고 잘못 입력하면 3번까지 다시 묻는다. 입력은 로그의 `end` 바로 앞 `footer` 줄로 남는다: `app_reps`(화면 카운트), `mode`, `actual_reps`, `actual_status`(`entered` / `not_entered`), `note`, `prompt`(`answered` / `skipped` / `unavailable`).
- **미입력**: 건너뜀·잘못된 입력 3회·입력 스트림 종료·Ctrl+C는 `actual_reps = null`, `actual_status = not_entered`. 분석 도구는 이를 "미입력"으로 보여 준다. 횟수를 받은 뒤 입력이 끊기면 받은 것은 남긴다.
- **묻지 않는 경우**: 로깅을 켜지 않은 일반 실행(recorder가 None, `main()` 안에 `input()` 호출이 없음을 AST로 테스트), 벤치마크 시간 종료·예외 종료(Q/ESC가 아님), **패키징(frozen) 빌드**(묻지도 footer를 쓰지도 않음), 터미널이 아닌 입력(IDE 등: 묻지 않고 화면 카운트만 담은 `not_entered` footer를 남김).
- **읽는 쪽**: `plot_landmark_sequence.py`가 footer를 읽어 터미널 요약에 `counts : actual 7 | screen 5 | detected 5 (differs by -2)` 한 줄, 그래프 제목에 같은 내용(메모 제외)을 보인다. actual은 사용자 입력, screen은 앱이 센 횟수(footer), detected는 로그의 확정된 `rep_end` 수다. `replay_flags.py`는 footer의 `actual_reps`/`note`를 정답으로 쓴다.
- **format_version 판단: 2를 유지했다.**
  - 이유: footer는 새 **줄 종류**일 뿐 기존 줄(session/frame/event/end)의 필드와 의미를 바꾸지 않는다. 읽는 쪽은 알 수 없는 줄 종류를 건너뛰고(`plot_landmark_sequence`, `field_test_1_lib`, `extract_rep_fixtures` 모두 확인), footer 유무는 줄 자체로 알 수 있다. 값은 선택 사항(없으면 "실제 횟수를 모르는 로그")이라 판독 규칙이 달라지는 것이 아니다.
  - 버전을 올리면 현재 v2만 받는 읽는 쪽 도구를 전부 고쳐야 하고 얻는 것이 없다. v1→v2를 올린 이유는 `frame`의 필드 추가와 `event` 줄이 로그 해석(상태 띠, 잠금 이벤트)에 필요했기 때문이다.
  - `end`의 집계(`frames_written`, `events_written`)에는 footer가 들어가지 않는다(테스트). 형식이 더 바뀌어 읽는 쪽 규칙이 달라지면 그때 3으로 올린다.
- 테스트(`tests/test_session_footer.py` 26개): 입력값·메모 기록, 0 허용, 건너뜀(메모는 유지), 잘못된 입력 재질문·3회 포기, 메모 길이 제한, EOF/Ctrl+C, 비대화형·패키징에서 묻지 않음, footer가 `end` 앞에 오고 프레임 집계에 안 들어감, 버전 유지, close 뒤 footer 거부, `finish_sequence_log`(기록·미입력·로깅 꺼짐·Q/ESC 아님·패키징·터미널 아님·질문 중 예외에도 로그는 닫힘), `main()`이 `input()`을 직접 쓰지 않고 `quit_requested`로만 호출, 그래프 스크립트의 footer 읽기·표시, `replay_flags`의 정답 읽기.

---

## 2026-10-19 · 2차 실측 프로토콜 문서, 0.2.0 범위 결정

### 2차 실측 프로토콜 (`field_test_2_protocol.md`)
`docs/versions/v0.2.0/field_test_2_protocol.md`를 작성했다(진행하는 사람과 보조자용). 내용:
- **세션표 15개**: 1차 세션(정상·깊게·얕게·상체 숙임·뒤꿈치·사선·정면·반대 방향·걷기·의자·런지)을 대부분 5회 이하로 다시 하고, 새로 **연속 세트 정상 10회 + 빠르게 5회**(반복 사이 휴지 없음), **쿼터 스쿼트 5회**, **상체가 꼿꼿한 스쿼트 5회**를 넣었다. 세션별 실행 명령(`--session-posture/--session-view/--session-note "P01_..."`), 기록표 양식, 머리말 칸(커밋 해시, 설정 변경 여부, 동의 확인).
- **정답 기록**: 소리 내어 세기는 쓰지 않는다. 기본은 종료 시 실제 횟수 입력(footer), 가능하면 보조자가 몸의 동작만 보고 따로 센다. **입력값과 보조자 기록이 다르면 둘 다 남기고 그 세션은 "정답 불확실"로 표시해 정확도 집계에서 제외**한다(1차 세션 9와 같은 처리).
- **분석은 최종 설정으로 재생**한다. 임계값은 1차 값을 고정한 채 2차 로그에 적용한 결과를 먼저 보고하고, 값을 바꾸거나 플래그를 켜는 결정은 그 뒤에 사용자 확인으로 한다(2차 데이터에 맞춰 다시 맞추면 검증이 되지 않는다).
- **연속 세트 세션을 넣은 이유**: 1차 실측은 반복 사이에 0.9~2.5초 휴지가 있어 실제 사용 패턴과 달랐다. 실시간 확인의 누락(연속 7회 중 5회)은 휴지 없는 사용에서 나왔고 1차 데이터로는 재현할 수 없었다.
- **다른 사람 참여 시**: 동의(영상 저장 안 함, **얼굴 좌표 미저장**이므로 `--log-face-landmarks` 금지, 화면 캡처 금지, 번호로만 구분·이름 금지, 중단·삭제 요청 가능), 미성년자·부상자 제외, 로그는 저장소에 올리지 않고 별도 백업.
- 문서 작성 중 코드에서 확인한 사실: **S(세션 시작)와 R(초기화)은 화면 카운트를 0으로 되돌린다**(카운트는 세션을 시작하지 않아도 센다). 그래서 실측 중 S/E/R을 누르지 않도록 적었다.

### 0.2.0 범위 결정
- **0.2.0은 클라이언트만 바꾼다.** 자세 점수는 **화면과 로컬 기록에만** 둔다.
- **Supabase 스키마, 백엔드 API, 대시보드 표시는 0.3.0 후보**로 미룬다.
- 이유: 판정 임계값(depth/torso_shin 경계, 가중치, 총점 상한 등)이 **2차 실측 뒤 바뀔 수 있다.** 지금 서버 스키마와 API에 점수를 넣으면 값의 의미가 바뀔 때 저장된 데이터와 서버·대시보드를 함께 고쳐야 하고, 이미 저장된 점수를 다시 해석할 수 없다.
- `RELEASE.md`의 "사용 조건과 한계"에 "자세 점수는 서버에 저장되지 않습니다"를 추가했다(이번에는 지시에 따라 이 한 줄만 수정).
