# Vercel Frontend Deployment

최종 갱신: 2026-09-15
현재 React/Vite Frontend는 `toru7/fitroute` 프로젝트의 `https://fitroute-ivory.vercel.app`에 배포되어 있다.

## Project configuration

| Vercel setting | Value |
|---|---|
| Project | `fitroute` |
| Scope | `toru7` |
| Git repository | `AI-Exercise-Assistant` |
| Production branch | `main` |
| Root Directory | `frontend` |
| Framework | Vite |
| Build command | `npm run build` |
| Output directory | `dist` |
| SPA config | `frontend/vercel.json` |

## Environment variables

Production 환경에 공개 가능한 값만 등록한다.

```dotenv
VITE_SUPABASE_URL=<Supabase project URL>
VITE_SUPABASE_ANON_KEY=<publishable or anon key>
VITE_API_BASE_URL=https://fitroute-api.onrender.com
VITE_DESKTOP_CLIENT_DOWNLOAD_URL=https://<public-r2-host>/releases/v<VERSION>/FitRoute-AI-Client-Setup-<VERSION>.exe
```

`VITE_` 변수는 browser bundle에 포함된다. Service-role key, DB password, access/refresh token과 R2/Vercel credential을 넣지 않는다. 환경변수 변경 후에는 새 deployment가 필요하다.

## SPA routing

`frontend/vercel.json`은 React Router의 `/dashboard`, `/history/:date`, `/statistics`, `/profile` 직접 접근을 `/index.html`로 rewrite한다. API는 외부 Render domain으로 전송하므로 SPA rewrite와 충돌하지 않는다.

## CLI deployment scope

Vercel CLI 59.17.0의 Git project/root 처리로 Repository의 AI runtime과 Installer가 source manifest에 포함된 문제가 있었다. 현재 release workflow는 다음 두 장치를 함께 사용한다.

- native process의 실제 Working Directory: `<repo>/frontend`
- Repository root `.vercelignore`: `frontend/**` allowlist

읽기 전용 검증 명령:

```powershell
vercel deploy --dry --format=json --project fitroute --scope toru7
```

검증 결과:

```text
51 files / 325,900 bytes
frontend 외부 파일: 0
AI Client / Installer / release artifact: 0
```

`--archive`는 이 문제의 해결책으로 사용하지 않는다. 배포 source 범위를 먼저 검증한다.

## Authentication and project targeting

Promotion preflight는 `vercel whoami`와 읽기 전용 `vercel project inspect fitroute --scope toru7`을 수행한다. `.vercel/project.json`이 없어도 `--project fitroute --scope toru7`로 대상을 명시하며 자동 login, project 생성과 `vercel link`를 실행하지 않는다.

## Connected service settings

- Render `FRONTEND_ORIGINS`: `https://fitroute-ivory.vercel.app`
- Supabase Site URL/Redirect URLs: 실제 Production HTTPS origin 기준
- 개발 URL이 필요하면 Supabase Redirect allowlist에만 별도로 유지

Wildcard CORS나 변동하는 Preview URL을 Production Backend에 허용하지 않는다.

## Production smoke test

1. Landing/Login/Signup 표시
2. 로그인 후 Dashboard 이동과 session 유지
3. Dashboard/History/Statistics/Profile 실제 API 응답
4. 직접 route 접근과 새로고침 시 SPA 404 없음
5. Network 요청이 Render HTTPS API를 사용하고 Bearer 인증을 포함
6. Browser console에 CORS/mixed-content 오류 없음
7. Windows 환경에서 설치 버튼과 `fitroute://` fallback 확인

Frontend 구현과 로컬 build는 [Frontend Guide](../frontend/README.md), Windows release 승격은 [Windows Release Process](windows_release_process.md)를 참고한다.
