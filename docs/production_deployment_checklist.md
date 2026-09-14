# FitRoute Production Deployment Checklist

이 문서는 배포 준비와 실제 배포 시 확인할 항목을 분리합니다. 현재 단계에서는 Cloud 리소스 생성이나 Dashboard 설정 변경을 수행하지 않습니다.

## 1. Backend 준비

- [x] FastAPI Production entry point가 `PORT`를 읽는다.
- [x] Production 실행에서 `--reload`를 사용하지 않는다.
- [x] 서버는 Container 내부 `0.0.0.0:$PORT`에서 listen한다.
- [x] `/health`는 인증·DB·외부 API 없이 `{"status":"ok"}`를 반환한다.
- [x] `FRONTEND_ORIGINS`를 쉼표 기준의 안전한 Origin 목록으로 파싱한다.
- [x] wildcard CORS를 허용하지 않는다.
- [x] 기존 `FRONTEND_ORIGIN`을 하위 호환한다.
- [x] 사용자 Bearer Token + RLS 구조를 유지하며 service role을 추가하지 않는다.
- [x] Client 오류 응답에 traceback, DB 오류, token 또는 Supabase key를 포함하지 않는다.
- [x] Staging Backend Provider로 Render를 선택한다.

## 2. Backend 환경변수

Cloud Runtime Environment Variables에만 설정합니다.

```dotenv
ENVIRONMENT=production
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_KEY
FRONTEND_ORIGINS=https://YOUR_FRONTEND_DOMAIN
LOG_LEVEL=info
PORT=8000
```

- [ ] 실제 값을 Provider secret/environment 설정에 등록한다.
- [ ] `FRONTEND_ORIGINS`에는 path와 trailing slash 없는 HTTPS Origin만 등록한다.
- [ ] service role, DB password, 사용자 Access Token을 등록하지 않는다.

## 3. Docker

- [x] `python:3.12-slim`을 사용한다.
- [x] `backend/requirements.txt`만 설치한다.
- [x] 비-root `app` 사용자로 실행한다.
- [x] AI 모델, TensorRT, MediaPipe, OpenCV와 dataset을 이미지에서 제외한다.
- [x] secret을 Dockerfile에 하드코딩하지 않는다.
- [x] `.dockerignore`로 Git, env, model, data, Frontend build를 제외한다.
- [x] Docker Desktop + WSL2 환경에서 실제 image build를 완료했다.
- [x] `8001:8000` Container 실행과 `/health`, `/docs`, `/openapi.json` 200을 확인했다.

```powershell
docker build -f backend/Dockerfile -t fitroute-backend .
docker run --rm --env-file backend/.env -e PORT=8000 -p 8001:8000 fitroute-backend
```

## 4. Frontend 준비

- [x] `VITE_API_BASE_URL`은 `src/lib/api.ts` 한 곳에서 읽는다.
- [x] Supabase URL과 publishable key는 Vite 환경변수에서 읽는다.
- [x] `npm run build`와 `npm run lint`가 통과한다.
- [x] Vite `base`는 root `/` 기본값을 유지한다.
- [x] `dist/`와 실제 env 파일은 Git에서 제외한다.
- [ ] Frontend Provider를 선택한다: Vercel / Netlify.
- [ ] Build command를 `npm run build`, output directory를 `dist`로 설정한다.
- [ ] `VITE_API_BASE_URL`을 배포된 HTTPS Backend URL로 설정한다.

공개 가능한 Vite 변수만 등록합니다.

```dotenv
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_KEY
VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

## 5. SPA Routing

- [x] Local production preview에서 `/dashboard`, `/history/2026-09-12`, `/statistics`, `/profile` 직접 접근이 200을 반환한다.
- [ ] Vercel 선택 시 비정적 경로를 `/index.html`로 rewrite한다.
- [ ] Netlify 선택 시 `/* /index.html 200` fallback을 설정한다.
- [ ] 실제 Hosting에서 `/dashboard` 직접 접속과 새로고침을 확인한다.
- [ ] 실제 Hosting에서 `/history/2026-09-12`, `/statistics`, `/profile` 직접 접속을 확인한다.

Provider 선택 전에는 중복 설정 파일을 만들지 않습니다.

## 6. Supabase Production Auth

실제 Frontend URL이 확정된 후 Dashboard에서 수행합니다.

- [ ] Authentication → URL Configuration의 Site URL을 실제 HTTPS Frontend URL로 설정한다.
- [ ] Redirect URLs에 실제 Frontend URL 패턴을 추가한다.
- [ ] 개발 중이면 `http://localhost:5173` 허용 여부를 확인한다.
- [ ] Email Confirmation 정책을 확인한다.
- [ ] Password Policy를 확인한다.
- [ ] User Signup 허용 정책을 확인한다.
- [ ] Frontend가 publishable/anon key만 사용하는지 다시 확인한다.
- [ ] RLS와 Security Advisor 결과를 확인한다.

## 7. Secrets와 로그

- [x] `backend/.env`, `frontend/.env`, `*.env.local`, build output을 Git에서 제외한다.
- [x] `.env.example`과 `.env.production.example`에는 placeholder만 둔다.
- [x] Backend는 Authorization header와 token을 출력하지 않는다.
- [x] Frontend는 access token을 console에 출력하지 않는다.
- [x] Docker image에 env 파일을 COPY하지 않는다.
- [ ] 과거에 노출된 임시 Access Token이 만료됐는지 확인한다.
- [ ] 배포 직전 Git history와 staged diff를 다시 secret scan한다.

## 8. 실제 배포 순서

1. [ ] FastAPI Backend를 Dockerfile 기반으로 배포한다.
2. [ ] `GET https://BACKEND_DOMAIN/health`가 200인지 확인한다.
3. [ ] Production API URL을 확보한다.
4. [ ] Frontend의 `VITE_API_BASE_URL`을 해당 API URL로 설정한다.
5. [ ] React Production build를 배포한다.
6. [ ] HTTPS Frontend domain을 확보한다.
7. [ ] Backend `FRONTEND_ORIGINS`를 정확한 Frontend Origin으로 설정하고 재배포한다.
8. [ ] Supabase Site URL과 Redirect URLs를 설정한다.
9. [ ] Production 회원가입·로그인·로그아웃을 확인한다.
10. [ ] Today, History, Date Detail, Statistics API 조회를 확인한다.
11. [ ] Python AI Client의 `FITROUTE_API_BASE_URL`을 Production API로 변경한다.
12. [ ] 실제 Session 종료 저장과 Dashboard 반영을 확인한다.

Render Backend Staging의 확정 설정과 Dashboard 절차는 [Render Backend Staging Deployment](render_backend_staging.md)를 참고합니다.

## 9. Production Smoke Test

- [ ] `/health` 200
- [ ] 허용된 Frontend Origin CORS 성공
- [ ] 임의 Origin CORS 거부
- [ ] 로그인 없는 Workout API 401
- [ ] 로그인 후 Today API 200
- [ ] Workout Session POST 201
- [ ] Supabase 원본 row와 daily summary 누적 확인
- [ ] React 새로고침 후 새 기록 표시
- [ ] 직접 URL 새로고침 시 SPA 404 없음
- [ ] 모바일 화면과 HTTPS mixed-content 오류 없음
