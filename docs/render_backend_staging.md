# Render Backend Staging Deployment

이 문서는 FastAPI Backend만 Render Web Service에 Docker로 배포하는 절차입니다. Frontend/Vercel, Supabase Site URL·Redirect URL, 최종 Browser CORS 연결은 이번 단계에서 변경하지 않습니다.

## 확정된 Render 설정

| Render 항목 | 입력값 |
|---|---|
| Service Type | Web Service |
| Name | `fitroute-api` |
| Runtime / Language | Docker |
| Branch | GitHub에 배포 코드를 push한 branch (`main` 권장) |
| Root Directory | 비워 둠 (Repository root) |
| Dockerfile Path | `backend/Dockerfile` |
| Docker Build Context Directory | `.` (Repository root) |
| Docker Command / Start Command | 비워 둠 (Dockerfile `CMD` 사용) |
| Region | Singapore (현재 선택지 중 한국·Seoul Supabase에 가장 가까운 지역) |
| Instance Type | 내부 Staging이면 Free 선택 가능 |
| Health Check Path | `/health` |

현재 Dockerfile은 Repository root 기준으로 `COPY backend/...`를 실행합니다. 따라서 Root Directory를 `backend`로 설정하면 안 됩니다. Dashboard에서 Docker Build Context 항목이 보이지 않으면 기본값인 Repository root를 그대로 사용합니다.

관련 Render 공식 문서:

- Docker: <https://render.com/docs/docker>
- Monorepo: <https://render.com/docs/monorepo-support>
- Web Services와 PORT: <https://render.com/docs/web-services>
- Health Checks: <https://render.com/docs/health-checks>
- Regions: <https://render.com/docs/regions>
- Free instance 제한: <https://render.com/docs/free>

## Render 환경변수

Render Dashboard의 Service Environment 설정에 다음 이름을 등록합니다. 실제 값은 Git, Dockerfile, 문서에 입력하지 않습니다.

```dotenv
ENVIRONMENT=production
SUPABASE_URL=<실제 Supabase Project URL>
SUPABASE_ANON_KEY=<현재 사용하는 Publishable 또는 Anon Key>
FRONTEND_ORIGINS=https://frontend-not-deployed.invalid
LOG_LEVEL=info
```

`https://frontend-not-deployed.invalid`는 Frontend 배포 전 임시 CORS Origin입니다. `.invalid`는 실제 서비스 Domain으로 사용되지 않는 예약 TLD이며 localhost나 wildcard를 허용하지 않습니다. PowerShell/Python API 테스트에는 Browser CORS가 적용되지 않으므로 이 상태에서도 Production API를 검증할 수 있습니다. Vercel URL이 생성된 다음 정확한 `https://...vercel.app` Origin으로 교체합니다.

다음 값은 등록하지 않습니다.

- `SUPABASE_SERVICE_ROLE_KEY`
- Database password
- 사용자 Access/Refresh Token
- `FITROUTE_ACCESS_TOKEN`

`PORT`도 직접 등록할 필요가 없습니다. Render가 Web Service에 제공하는 `PORT`를 `backend/start.py`가 읽습니다. Dockerfile의 `EXPOSE 8000`은 문서용 기본 포트일 뿐 Render의 public/host port를 고정하지 않습니다.

## Dashboard 배포 순서

Render Dashboard 화면의 명칭은 UI 업데이트에 따라 조금 달라질 수 있습니다.

1. 배포할 변경을 Git commit한 뒤 GitHub branch에 push합니다.
2. Render Dashboard에서 **New +** → **Web Service**를 선택합니다.
3. GitHub 연결을 승인하고 `AI-Exercise-Assistant` Repository의 **Connect**를 누릅니다.
4. Name을 `fitroute-api`로 입력하고 배포 branch를 선택합니다.
5. Runtime 또는 Language를 **Docker**로 선택합니다.
6. Root Directory는 비워 둡니다.
7. Dockerfile Path에 `backend/Dockerfile`을 입력합니다.
8. Docker Build Context Directory 또는 Docker Context가 보이면 `.`을 입력합니다.
9. Docker Command/Start Command는 비워 둡니다.
10. Region은 **Singapore**를 선택합니다.
11. 내부 Staging이면 **Free** instance를 선택할 수 있습니다. 15분간 inbound traffic이 없으면 sleep하고 첫 요청의 재기동에 약 1분이 걸릴 수 있습니다.
12. 위 환경변수 다섯 개를 등록합니다.
13. Advanced 또는 Health Checks에서 Health Check Path를 `/health`로 설정합니다.
14. **Create Web Service** 또는 **Deploy Web Service**를 누릅니다.

FastAPI 컨테이너에 TLS 인증서를 설치하지 않습니다. Render HTTPS endpoint가 외부 TLS를 종료하고 Container에는 HTTP로 전달합니다.

## 첫 Deploy 로그

정상 흐름에서는 다음 내용을 순서대로 확인합니다.

1. Git source checkout
2. Docker/BuildKit build 시작
3. `backend/requirements.txt` 설치
4. Image build 완료
5. Container start
6. `Application startup complete`
7. `Uvicorn running on http://0.0.0.0:<Render PORT>`
8. `/health` 성공 및 deploy live

오류별 확인 위치:

- `COPY backend/... not found`: Root Directory가 비어 있고 Docker Context가 `.`인지 확인
- Python import 오류: Dockerfile Path와 Repository에 `backend/app`, `backend/start.py`, `backend/__init__.py`가 push됐는지 확인
- Settings의 missing field 오류: `SUPABASE_URL`, `SUPABASE_ANON_KEY` 등록 확인
- `PORT must ...` 오류: 수동으로 추가한 잘못된 `PORT`를 제거
- Health check 실패: 로그에 `0.0.0.0:<PORT>` listen과 Health Check Path `/health` 확인
- 인증 API만 `401`: 새 사용자 Access Token과 Supabase project 일치 여부 확인
- Workout API만 `502`: Supabase RPC/schema/RLS 및 Render의 Supabase 환경변수 확인

## 배포 직후 검증

Render가 보여주는 실제 HTTPS Domain을 사용합니다.

```text
https://<render-domain>/health
https://<render-domain>/docs
https://<render-domain>/openapi.json
```

첫 성공 조건은 `/health`의 HTTP 200 응답입니다.

```json
{
  "status": "ok"
}
```

Swagger에서 다음 endpoint가 보이는지 확인합니다.

- `POST /api/workouts`
- `GET /api/workouts/today`
- `GET /api/workouts/daily`
- `GET /api/workouts/daily/{workout_date}`
- `GET /api/workouts/sessions/{workout_date}`

## Production Workout API Test

이 테스트는 실제 Supabase DB에 sample session 두 개를 추가하며 자동 삭제하지 않습니다.

먼저 새 사용자 Access Token을 발급합니다.

```powershell
python backend/scripts/get_test_token.py
```

PowerShell:

```powershell
$env:FITROUTE_API_BASE_URL="https://<render-domain>"
python backend/scripts/test_workout_api.py
```

Windows CMD:

```cmd
set FITROUTE_API_BASE_URL=https://<render-domain>
python backend/scripts/test_workout_api.py
```

Token 프롬프트에는 방금 발급한 사용자 Access Token만 입력합니다. Publishable/Anon key나 `Bearer ` 문구를 입력하지 않습니다.

예상 결과:

- `/health` → 200
- 최초 daily 조회 → 200
- sample 1 POST → 201
- sample 2 POST → 201
- 이후 daily/sessions 조회 → 200
- 증가량: squat `35`, stretch `210`, workout `840`, session count `2`
- 마지막 출력: `PASS: atomic summary delta is correct`

Token 없음과 잘못되거나 만료된 Token은 401이어야 합니다. 정상 Token은 RLS를 통해 해당 사용자 데이터에만 접근합니다.

## 이 단계의 중단 지점

Render Domain을 받은 뒤 `/health`, `/docs`, Production Workout API Test를 완료합니다. 이 세 가지가 통과하기 전에는 Frontend Vercel 배포로 넘어가지 않습니다.
