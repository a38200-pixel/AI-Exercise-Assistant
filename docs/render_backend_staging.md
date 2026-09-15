# Render Backend Deployment

최종 갱신: 2026-09-15
현재 FastAPI Backend는 `https://fitroute-api.onrender.com`에 Docker Web Service로 배포되어 있다.

## Deployment configuration

| Render setting | Value |
|---|---|
| Service | `fitroute-api` |
| Runtime | Docker |
| Production branch | `main` |
| Root Directory | 비움 (Repository root) |
| Dockerfile | `backend/Dockerfile` |
| Docker build context | `.` |
| Start command | Dockerfile `CMD` |
| Health check | `/health` |

Dockerfile이 Repository root 기준으로 `backend/...`를 복사하므로 Render Root Directory를 `backend`로 설정하지 않는다. Container는 `backend/start.py`를 통해 Render가 제공한 `PORT`를 읽고 `0.0.0.0:$PORT`에서 실행된다.

## Runtime environment

Render Dashboard에만 다음 값을 등록한다.

```dotenv
ENVIRONMENT=production
SUPABASE_URL=<Supabase project URL>
SUPABASE_ANON_KEY=<publishable or anon key>
FRONTEND_ORIGINS=https://fitroute-ivory.vercel.app
LOG_LEVEL=info
```

`PORT`는 Render가 제공한다. Service-role key, DB password, 사용자 access/refresh token과 `FITROUTE_ACCESS_TOKEN`은 등록하지 않는다. FastAPI container에 TLS 인증서를 넣지 않으며 Render endpoint가 HTTPS를 종료한다.

## Deploy and recovery

1. 변경사항을 검증하고 GitHub의 배포 branch에 반영한다.
2. Render가 `backend/Dockerfile`로 image를 build하는지 확인한다.
3. 로그에서 Uvicorn이 `0.0.0.0:<PORT>`에 listen하는지 확인한다.
4. `/health`가 HTTP 200인지 확인한다.
5. 인증된 Workout API와 Frontend CORS를 smoke test한다.

문제 발생 시 마지막 정상 commit으로 재배포하되 Supabase schema나 사용자 데이터를 자동 삭제하지 않는다.

## API verification

```text
https://fitroute-api.onrender.com/health
https://fitroute-api.onrender.com/docs
https://fitroute-api.onrender.com/openapi.json
```

Workout API 실제 검증은 사용자 access token을 숨김 프롬프트로 입력한다.

```powershell
$env:FITROUTE_API_BASE_URL='https://fitroute-api.onrender.com'
python backend/scripts/test_workout_api.py
```

예상 결과는 health `200`, session POST `201`, 조회 API `200`이며 두 sample session의 증가량은 squat 35, stretch 210초, workout 840초, session 2개다. 이 테스트는 실제 DB row를 생성하고 자동 삭제하지 않는다.

## Troubleshooting

| Symptom | Check |
|---|---|
| `COPY backend/... not found` | Root Directory가 비어 있고 build context가 `.`인지 확인 |
| Settings missing field | `SUPABASE_URL`, `SUPABASE_ANON_KEY` 확인 |
| Health check failure | Provider `PORT`와 `/health` 확인 |
| Workout `401` | 사용자 token 만료 및 Supabase project 일치 확인 |
| Workout `502` | RPC/schema/RLS와 Supabase 환경변수 확인 |
| 첫 요청 지연 | Render instance cold start 여부 확인 |

Backend의 schema, 인증과 로컬 실행은 [Backend Guide](../backend/README.md), 전체 운영 gate는 [Production Checklist](production_deployment_checklist.md)를 참고한다.
