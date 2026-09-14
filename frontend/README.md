# FitRoute Frontend

AI Exercise Assistant의 운동 기록 웹 UI입니다. 첨부된 `docs/UI.png`를 디자인 기준으로 삼아 짙은 포레스트 내비게이션, 라임 포인트, 밝은 데이터 패널과 모바일 하단 내비게이션으로 구성했습니다.

## Tech Stack

- React, Vite, TypeScript
- React Router
- Supabase Auth (`@supabase/supabase-js`)
- Tailwind CSS
- Recharts, Lucide React, date-fns

## Environment Variables

```powershell
Copy-Item .env.example .env
```

`frontend/.env`에 다음 값을 설정합니다.

```dotenv
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_ANON_OR_PUBLISHABLE_KEY
VITE_API_BASE_URL=http://127.0.0.1:8000
```

로컬에서 8000 포트를 `vmnat` 등이 사용 중이면 Backend를 8001로 실행하고 `VITE_API_BASE_URL=http://127.0.0.1:8001`로 설정합니다. Frontend에는 publishable/anon key만 사용하며 service role key는 절대 넣지 않습니다. `.env`는 Git에서 제외됩니다.

## Install / Run / Build

```powershell
cd frontend
npm install
npm run dev
```

```powershell
npm run build
npm run lint
```

개발 서버는 기본적으로 `http://localhost:5173`에서 실행됩니다.

## Production Build와 Preview

운영 템플릿 `.env.production.example`의 placeholder를 참고해 Hosting Provider의 환경변수에 다음 세 값만 등록합니다.

```dotenv
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_KEY
VITE_API_BASE_URL=https://fitroute-api.onrender.com
```

`VITE_` 변수는 Browser bundle에 포함됩니다. 따라서 Supabase publishable/anon key만 허용되며 service role key, DB password, access/refresh token 또는 Backend secret을 넣으면 안 됩니다.

Production에서 `VITE_API_BASE_URL`이 없으면 localhost로 fallback하지 않고 환경변수 누락 오류를 표시합니다. localhost 기본값은 개발 모드에서만 사용합니다.

```powershell
npm run build
npm run preview -- --host 127.0.0.1
```

`dist/`는 Git에 포함하지 않고 Hosting Provider가 build command로 생성하게 합니다. 일반 root domain 배포를 가정하므로 Vite `base`는 기본 `/`를 유지합니다.

## SPA Routing

React Router 경로(`/dashboard`, `/history/:date`, `/statistics`, `/profile`)를 직접 새로고침해도 `index.html`로 fallback되어야 합니다.

- Vercel: `vercel.json`의 SPA rewrite가 모든 직접 경로를 `/index.html`로 전달합니다.
- Netlify: 프로젝트 확정 후 `/*  /index.html  200` redirect 규칙을 설정합니다.

Frontend Staging Provider는 Vercel로 확정되었으며 `frontend/vercel.json`이 Production SPA fallback을 담당합니다.

Vercel Frontend Staging의 Dashboard 입력값과 배포 후 CORS/Auth 절차는 [Vercel Frontend Staging Deployment](../docs/vercel_frontend_staging.md)를 참고합니다.

배포 URL이 나온 뒤 Supabase Dashboard의 Authentication → URL Configuration에서 Site URL과 Redirect URLs를 실제 HTTPS Frontend domain으로 변경해야 합니다. 개발용 `http://localhost:5173`도 필요한 동안 허용 목록에 유지합니다.

## Authentication and API Flow

로그인과 회원가입은 Supabase Auth를 직접 사용합니다. 앱 시작 시 `getSession()`, 인증 변경 시 `onAuthStateChange()`로 세션을 관리합니다. FastAPI 요청 직전에 Supabase SDK의 현재 session에서 access token을 가져와 `Authorization: Bearer <token>` 헤더로 전달합니다. 비밀번호나 토큰을 별도 localStorage key 또는 console에 기록하지 않습니다.

```text
Login / Sign Up → Supabase Auth → SDK Session → Access Token → FastAPI → RLS
```

401이면 로그인 화면으로 이동하고, 네트워크 오류와 Backend 오류는 민감한 내부 정보 없이 안내합니다.

## Routes

| Route | Description | Auth |
|---|---|---|
| `/` | Landing | Public |
| `/login` | Login | Public |
| `/signup` | Sign Up | Public |
| `/dashboard` | Today summary, weekly chart, recent sessions | Required |
| `/history` | Monthly calendar and selected-date summary | Required |
| `/history/:date` | Daily summary and original session timeline | Required |
| `/statistics` | Weekly/monthly aggregate and trend | Required |
| `/profile` | Account and read-only settings | Required |

## Backend Connection

FastAPI는 별도 터미널에서 프로젝트 root를 기준으로 실행합니다.

```powershell
uvicorn backend.app.main:app --reload --port 8001
```

Dashboard는 `/api/workouts/today`, 최근 7일 `/api/workouts/daily`, 최근 날짜 `/api/workouts/sessions/{date}`를 사용합니다. History는 월 단위 daily API와 날짜 상세를, Statistics는 daily API의 실제 응답을 사용합니다. 운동값은 화면에 hardcoding하지 않습니다.

## Responsive Design

- Desktop: 고정 Sidebar와 밝은 데이터 workspace
- Tablet: 유동형 카드 grid
- Mobile: 다크 운동 시간 ring, 2열 요약 카드, fixed bottom navigation과 safe-area padding
- 모든 데이터 화면에 skeleton, empty, retry error state 제공

브라우저의 운동 시작 버튼은 Python AI 프로그램 안내만 표시합니다. 목표값, AI confidence, 프로필 수정처럼 Backend 데이터가 없는 기능은 demo 또는 Coming Soon으로 명시합니다.
