# FitRoute Production Deployment Checklist

최종 갱신: 2026-09-15
상태: **Frontend, Backend, Auth/Database, Windows Installer 배포 및 타 PC E2E 검증 완료**

## Production endpoints

| Component | Production |
|---|---|
| Frontend | `https://fitroute-ivory.vercel.app` |
| Backend | `https://fitroute-api.onrender.com` |
| Auth / Database | Supabase Auth + PostgreSQL + RLS |
| Windows Installer | Cloudflare R2 versioned object |

실제 credential과 `.env` 값은 Git 또는 문서에 저장하지 않는다.

## Verified state

- [x] Render Docker Backend가 Provider `PORT`로 `0.0.0.0`에서 실행됨
- [x] `/health`, `/docs`, `/openapi.json` 응답 확인
- [x] 인증된 Workout POST와 Today/Daily/Session 조회 확인
- [x] Supabase 원본 session과 daily summary atomic 누적 확인
- [x] Vercel React/Vite Production build 및 SPA rewrite 적용
- [x] Production 회원가입·로그인과 보호 route 확인
- [x] Render API → Supabase → Web Dashboard 조회 확인
- [x] Windows Web download → Installer → `fitroute://` → Launcher → AI Client 실행 확인
- [x] 별도 Windows PC에서 Camera/AI 운동과 cloud 저장 확인
- [x] uninstall 시 설치 tree, protocol과 Desktop credential 정리 확인
- [x] Vercel deployment manifest를 `frontend/**` 51 files / 325,900 bytes로 제한

## Backend configuration

```dotenv
ENVIRONMENT=production
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_KEY
FRONTEND_ORIGINS=https://fitroute-ivory.vercel.app
LOG_LEVEL=info
```

- `FRONTEND_ORIGINS`에는 path와 trailing slash가 없는 정확한 HTTPS Origin만 사용한다.
- wildcard CORS, service-role key, DB password와 사용자 token을 사용하지 않는다.
- `/health`는 인증·DB write 없이 process 상태만 반환한다.

## Frontend configuration

```dotenv
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_KEY
VITE_API_BASE_URL=https://fitroute-api.onrender.com
VITE_DESKTOP_CLIENT_DOWNLOAD_URL=https://<public-r2-host>/releases/v<VERSION>/FitRoute-AI-Client-Setup-<VERSION>.exe
```

`VITE_` 값은 browser bundle에 포함되므로 공개 가능한 URL과 publishable key만 허용한다. `frontend/vercel.json`은 React Router 직접 접근을 `/index.html`로 rewrite한다.

## Windows release gate

새 version을 공개하기 전에 다음 순서를 지킨다.

1. SemVer, Git clean 상태와 Installer 입력을 검증한다.
2. Installer를 build하고 size/SHA-256을 계산한다.
3. version별 R2 경로에 `--immutable`로 업로드한다.
4. remote object와 release metadata를 대조한다.
5. 별도 Windows PC에서 download/install/protocol/auth/camera/save/uninstall을 검증한다.
6. `promote_windows_release.ps1 -DryRun`으로 변경 계획을 확인한다.
7. 명시적 승인 후 Vercel 환경변수와 Production deploy를 반영한다.
8. Production HTTP 확인이 성공한 경우에만 `production.json`을 갱신한다.

상세 절차는 [Windows Release Process](windows_release_process.md)를 따른다.

## Security review

- [x] 실제 Backend/Frontend env와 build output은 Git 제외
- [x] Docker image에 env 파일과 AI runtime 미포함
- [x] Launcher password 미저장, refresh token만 Credential Manager에 저장
- [x] access token은 child environment로만 전달
- [x] release metadata에는 공개 URL, version, size와 SHA-256만 기록
- [x] Vercel/R2 credential을 명령 출력과 문서에서 제외

## Remaining release concerns

- Windows Installer는 아직 code signing되지 않아 SmartScreen 경고가 발생할 수 있다.
- TensorRT engine은 GPU/driver/runtime 호환성 제약이 있다.
- v0.1.1 최초 실행의 첫 운동 저장 실패 가능성은 [루트 README Known Issue](../README.md#16-known-issue)에 기록되어 있다.

## Regression smoke test

- Backend health와 인증 없는 Workout API의 `401`
- 로그인, session 복원과 보호 route
- Dashboard/History/Statistics 실제 API 응답
- 직접 URL 새로고침의 SPA fallback
- Windows protocol/Auth/Camera/TensorRT/MediaPipe/XGBoost
- Workout `POST 201`, Supabase row와 Dashboard 증가
- 모바일 Web UI와 HTTPS mixed-content/CORS 오류
