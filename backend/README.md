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
| GET | `/api/workouts/daily` | `start_date`~`end_date` 날짜별 합계 |
| GET | `/api/workouts/daily/{workout_date}` | 특정 날짜 합계 |
| GET | `/api/workouts/sessions/{workout_date}` | 특정 날짜 원본 세션 |

Workout endpoint는 모두 Supabase Bearer access token이 필요합니다.

## Local Setup

프로젝트 root에서 실행합니다.

```bash
pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

`backend/.env`에 Supabase Project URL과 anon/publishable key를 설정합니다.

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_ANON_OR_PUBLISHABLE_KEY
FRONTEND_ORIGIN=http://localhost:5173
```

서버 실행:

```bash
uvicorn backend.app.main:app --reload
```

테스트:

```bash
pytest backend/tests -v
```

실제 Supabase 연결, SQL 자동 실행, 사용자 생성, DB insert와 배포는 이 scaffold에 포함되지 않습니다.

