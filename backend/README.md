# Backend

## Stack

- FastAPI
- Supabase PostgreSQL
- Supabase Auth
- Pydantic

AI inference 패키지와 Backend 의존성은 분리되어 있습니다. FastAPI는 자체 비밀번호나 로그인 endpoint를 만들지 않습니다.

## Database

- `profiles`: `auth.users`의 사용자별 nickname/timezone 확장 정보
- `workout_sessions`: S부터 E까지의 원본 세션. 세션마다 새 row를 생성합니다.
- `daily_workout_summary`: `(user_id, workout_date)`별 누적 합계

`record_workout_session` PostgreSQL RPC가 원본 세션 INSERT와 날짜별 summary ADD UPSERT를 한 transaction에서 처리합니다. `user_id`는 request body가 아니라 `auth.uid()`에서 가져옵니다.

SQL은 [001_initial_schema.sql](sql/001_initial_schema.sql)에 있습니다. Supabase Dashboard SQL Editor에서 내용을 검토한 후 직접 실행합니다.

## Authentication Flow

```text
React / PWA / Mobile
  -> Supabase Auth login
  -> Access Token
  -> Authorization: Bearer <token>
  -> FastAPI get_current_user
  -> Supabase auth.get_user(token)
  -> request-scoped Supabase client
  -> RLS auth.uid()
```

Service role key는 일반 사용자 요청에 사용하지 않습니다. 사용자별 client를 요청마다 생성하므로 전역 인증 상태가 섞이지 않습니다.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Process health check |
| POST | `/api/workouts` | Atomic workout session 저장 |
| GET | `/api/workouts/today` | 오늘 합계, 기록이 없으면 0 |
| GET | `/api/workouts/daily` | 날짜별 합계. 범위 생략 시 한국 기준 최근 31일 |
| GET | `/api/workouts/daily/{workout_date}` | 특정 날짜 합계 |
| GET | `/api/workouts/sessions/{workout_date}` | 특정 날짜 원본 세션 |

Workout endpoint는 모두 Supabase Bearer access token이 필요합니다.

## Local Setup

프로젝트 root에서 실행합니다.

```powershell
pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

Windows 명령 프롬프트(`cmd`)에서는 두 번째 명령 대신 `copy backend\.env.example backend\.env`를 사용합니다.

`backend/.env`에 Supabase Project URL과 anon/publishable key를 설정합니다.

```dotenv
ENVIRONMENT=development
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_ANON_OR_PUBLISHABLE_KEY
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
LOG_LEVEL=info
```

`FRONTEND_ORIGINS`는 쉼표로 구분하며 URL path와 끝의 `/` 없이 정확한 Origin만 넣습니다. 기존 `FRONTEND_ORIGIN`도 호환되지만 신규 환경은 복수형을 사용합니다. `*` wildcard는 거부됩니다.

개발 서버 실행:

```bash
uvicorn backend.app.main:app --reload
```

## Production 실행

Production에서는 `--reload`를 사용하지 않습니다. Cloud가 제공하는 `PORT`를 사용하는 entry point가 준비되어 있습니다.

```powershell
$env:ENVIRONMENT="production"
$env:PORT="8000"
python -m backend.start
```

직접 실행 명령을 등록하는 Provider에서는 다음과 같이 사용할 수도 있습니다.

```text
uvicorn backend.app.main:app --host 0.0.0.0 --port <PORT>
```

운영 환경변수 템플릿은 `.env.production.example`을 참고합니다. `SUPABASE_ANON_KEY`에는 publishable/anon key만 사용하며 service role key는 일반 사용자 API에 필요하지 않습니다. 실제 값은 이미지나 Git이 아니라 Cloud Provider의 Runtime Environment Variables에 등록합니다.

운영 CORS 예시는 다음과 같으며 trailing slash를 붙이지 않습니다.

```dotenv
FRONTEND_ORIGINS=https://fitroute.example.com
```

`GET /health`는 인증, Supabase query, DB write 없이 프로세스 상태만 빠르게 반환합니다.

## Docker

Repository root를 build context로 사용합니다.

```powershell
docker build -f backend/Dockerfile -t fitroute-backend .
docker run --rm --env-file backend/.env -e PORT=8000 -p 8000:8000 fitroute-backend
```

`docker run`의 `--env-file`은 로컬 검증용이며 파일을 이미지에 COPY하지 않습니다. 운영에서는 Provider 환경변수를 사용합니다. Container 내부는 HTTP `0.0.0.0:$PORT`로 listen하고 외부 HTTPS 종료는 배포 Provider가 담당합니다. Dockerfile은 `python:3.12-slim`, 비-root 사용자, `backend/requirements.txt`만 사용하므로 AI 모델·CUDA·OpenCV 의존성을 포함하지 않습니다.

단위 테스트:

```bash
pytest backend/tests -v
```

## Supabase 실제 연동 테스트

### 1. 테스트 사용자 생성

Supabase Dashboard에서 **Authentication → Users → Add user**를 선택합니다. 실제로 받을 수 있는 테스트 이메일과 별도의 강한 비밀번호를 사용하고, 비밀번호를 코드·문서·`.env`에 기록하지 마세요. 사용자를 만든 후 SQL Editor에서 profile trigger 결과를 확인합니다.

```sql
select id, nickname, timezone, created_at
from public.profiles
order by created_at desc;
```

생성된 `auth.users.id`와 `profiles.id`가 같고, 메타데이터에 nickname을 넣지 않았다면 `nickname`이 `NULL`인 것이 정상입니다.

### 2. FastAPI 실행 및 상태 확인

프로젝트 root에서 실행합니다.

```powershell
uvicorn backend.app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000/health`가 `{"status":"ok"}`를 반환하는지 확인합니다. Swagger는 `http://127.0.0.1:8000/docs`입니다.

### 3. Access Token 발급

새 터미널을 열고 프로젝트 root에서 실행합니다.

```powershell
python backend/scripts/get_test_token.py
```

이메일과 숨김 처리되는 비밀번호를 입력하면 User ID, Email, Access Token이 출력됩니다. 이 도구는 개발 테스트용으로만 토큰을 출력하며 refresh token은 출력하지 않습니다. Access Token도 비밀번호처럼 취급하고 터미널 기록, 화면 공유, Git에 남기지 마세요.

### 4. Workout API 실제 테스트

FastAPI가 실행 중인 상태에서 다음 명령을 실행하고, 앞 단계의 Access Token을 숨김 프롬프트에 붙여 넣습니다.

```powershell
python backend/scripts/test_workout_api.py
```

프롬프트에는 `Bearer ` 문구나 publishable/anon key가 아니라 `get_test_token.py`가 출력한 사용자 Access Token만 입력합니다. 스크립트는 `Bearer `가 실수로 포함된 경우 제거하며, JWT 형식·만료·사용자 role·Supabase 프로젝트 일치 여부를 API 요청 전에 검사합니다.

스크립트는 오늘 날짜(Asia/Seoul)에 샘플 세션 두 개를 순서대로 저장하고 다음을 확인합니다.

- 첫 세션: squat 20, stretch 120초, workout 600초
- 둘째 세션: squat 15, stretch 90초, workout 240초
- 실행 전후 합계 차이: squat 35, stretch 210초, workout 840초, session 2개
- `today`, `daily`, 날짜 상세, 원본 session 목록 조회

기존 기록이 있어도 절대 합계가 아닌 실행 전후 차이를 검증하므로 재실행할 수 있습니다. 첫 세션 하나만 저장하려면 다음처럼 실행합니다.

```powershell
python backend/scripts/test_workout_api.py --one-session
```

다른 날짜를 지정하려면 `--date 2026-09-12`를 추가합니다. 지정일이 오늘이 아니면 `/today` 비교는 생략합니다.

Table Editor에서도 확인할 수 있습니다. `workout_sessions`에는 실행한 각 세션이 별도 row로 추가되고, `daily_workout_summary`에는 사용자·날짜별 row 하나가 유지되면서 수치와 `session_count`가 더해집니다. POST는 `record_workout_session` RPC 한 번으로 두 작업을 같은 transaction에서 수행합니다.

모든 Workout 요청은 `Authorization: Bearer <access_token>`이 필요합니다. 토큰이 없거나 잘못되었거나 만료되면 `401`이며, 음수 운동값·시간 역전·timezone 없는 datetime은 `422`입니다. API는 `user_id`를 body/query로 받지 않고 JWT의 `auth.uid()`와 RLS로 사용자 범위를 제한합니다. 일반 요청에 service role key를 사용하지 않습니다.

실제 로그인과 데이터 저장은 테스트 사용자의 이메일·비밀번호가 필요한 단계이므로 사용자가 위 명령을 직접 실행해야 합니다. SQL 자동 적용, 테스트 사용자 자동 생성, 데이터 자동 삭제 및 배포는 이 테스트 도구의 범위에 포함되지 않습니다.
