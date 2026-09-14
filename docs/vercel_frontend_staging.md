# Vercel Frontend Staging Deployment

이 문서는 현재 React/Vite Frontend를 Vercel의 고정 Production Domain에 내부 Staging 용도로 배포하는 절차입니다. UI, Backend, Database와 RLS는 변경하지 않습니다.

## 확정된 Vercel 설정

| Vercel 항목 | 설정값 |
|---|---|
| Project Name | `fitroute` (`fitroute-web`, `fitroute-staging` 대체 가능) |
| Git Repository | `AI-Exercise-Assistant` |
| Production Branch | `main` |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Install Command | 기본값 사용 (override 끔) |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| SPA Configuration | `frontend/vercel.json` |

`frontend/` 안에 `package.json`, `package-lock.json`, `vite.config.ts`, `src/`, `index.html`이 있으므로 이 디렉터리가 Vercel Project Root입니다. Vite Preset이 자동 감지되면 Build Command와 Output Directory도 override하지 않고 감지된 기본값을 사용합니다.

관련 공식 문서:

- Vercel Monorepo: <https://vercel.com/docs/monorepos>
- Vercel Build 설정: <https://vercel.com/docs/builds/configure-a-build>
- Vite SPA 배포: <https://vercel.com/docs/frameworks/frontend/vite>
- Vercel 환경변수: <https://vercel.com/docs/environment-variables>
- Supabase Redirect URLs: <https://supabase.com/docs/guides/auth/redirect-urls>

## Vercel 환경변수

Project 생성 화면 또는 **Project → Settings → Environment Variables**에 다음 세 개를 등록합니다. 이번 내부 Staging은 고정된 Production Domain을 사용하므로 우선 **Production** 환경에 적용합니다.

```dotenv
VITE_SUPABASE_URL=<실제 Supabase Project URL>
VITE_SUPABASE_ANON_KEY=<현재 사용하는 Publishable 또는 Anon Key>
VITE_API_BASE_URL=https://fitroute-api.onrender.com
```

`VITE_` 변수는 Browser bundle에 포함됩니다. 다음 값은 절대 등록하지 않습니다.

- Supabase secret/service-role key
- Database password
- 사용자 Access/Refresh Token
- `FITROUTE_ACCESS_TOKEN`

Production에서 `VITE_API_BASE_URL`이 누락되면 Frontend는 localhost로 연결하지 않고 환경변수 누락 오류를 표시합니다. 개발 모드에서만 기존 `http://127.0.0.1:8000` 기본값을 유지합니다. API URL 끝의 `/`는 제거한 뒤 `/api/...` 경로를 결합하므로 이중 slash나 중복 `/api`가 생기지 않습니다.

환경변수를 추가하거나 변경한 뒤에는 새 Deployment를 실행해야 반영됩니다. Preview Deployment를 별도로 사용하려면 같은 세 값을 Preview 환경에도 명시적으로 등록해야 합니다. 이번 단계에서는 변동하는 Preview URL을 CORS에 wildcard로 허용하지 않고 Project의 고정 Production Domain을 사용합니다.

## SPA Routing

React Router가 `BrowserRouter`를 사용하므로 Vercel에서 직접 경로를 새로고침할 때 `index.html`로 rewrite해야 합니다. `frontend/vercel.json`은 Vercel의 Vite SPA 권장 설정을 사용합니다.

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

이 Frontend에는 Vercel Functions나 `/api` 정적 endpoint가 없으며 API 요청은 외부 Render Domain으로 직접 전송되므로 현재 rewrite와 충돌하지 않습니다. Vite가 생성한 실제 asset은 Vercel의 파일 시스템에서 정상 제공됩니다.

## Dashboard 배포 순서

Vercel Dashboard 명칭은 UI 업데이트에 따라 조금 달라질 수 있습니다.

1. 현재 변경을 commit하고 GitHub `main` branch에 push합니다.
2. Vercel Dashboard에서 **Add New… → Project**를 선택합니다.
3. GitHub 연결을 승인하고 `AI-Exercise-Assistant` Repository의 **Import**를 누릅니다.
4. Project Name을 `fitroute`로 입력합니다. 이미 사용 중이면 `fitroute-web` 또는 `fitroute-staging`을 사용합니다.
5. Framework Preset이 **Vite**인지 확인합니다.
6. Root Directory의 **Edit**를 눌러 `frontend`를 선택합니다.
7. Build Command가 `npm run build`인지 확인합니다. Vite 자동 설정이면 Override를 켜지 않습니다.
8. Output Directory가 `dist`인지 확인합니다. Vite 자동 설정이면 Override를 켜지 않습니다.
9. Install Command는 기본 자동 감지를 사용하고 Override하지 않습니다.
10. Environment Variables에 위 세 값을 추가하고 적용 환경을 **Production**으로 선택합니다.
11. **Deploy**를 누릅니다.
12. Build log에서 dependency install, `tsc -b`, `vite build`, deployment 완료를 확인합니다.
13. 생성된 고정 Production URL을 기록합니다. 실제 URL을 추측해서 설정하지 않습니다.

## Vercel URL 생성 직후 설정

예시가 아니라 Vercel이 실제 발급한 정확한 Origin을 사용합니다. 끝에 `/`를 붙이지 않습니다.

### 1. Render CORS

Render의 `fitroute-api` Service에서 **Environment**로 이동하여 다음 값을 바꿉니다.

```dotenv
FRONTEND_ORIGINS=https://<실제-vercel-domain>
```

기존 `https://frontend-not-deployed.invalid`를 교체하고 Render 재배포가 완료될 때까지 기다립니다. `*`, localhost, 변동하는 Preview URL은 추가하지 않습니다.

### 2. Supabase Auth URL

Supabase Dashboard의 **Authentication → URL Configuration**에서 다음을 설정합니다.

```text
Site URL: https://<실제-vercel-domain>
Redirect URLs: https://<실제-vercel-domain>/**
```

현재 이메일/비밀번호 Login은 redirect 없이 직접 Session을 생성하므로 기존 테스트 사용자의 로그인만 확인할 때 Site URL 변경은 필수가 아닙니다. 그러나 Signup 코드는 `emailRedirectTo`를 지정하지 않으므로 이메일 확인이 활성화된 새 회원가입의 기본 복귀 주소로 Supabase Site URL이 사용됩니다. 고정 Production Domain을 Staging의 대표 URL로 사용할 예정이라면 Vercel URL 생성 후 Site URL도 해당 주소로 변경하는 것이 맞습니다.

로컬 이메일 확인 흐름도 계속 필요하면 Redirect URLs에 `http://localhost:5173/**`를 별도로 유지할 수 있습니다. Production Render CORS에는 localhost를 추가하지 않습니다.

## Browser End-to-End Test

같은 Supabase 테스트 사용자로 로그인하여 다음을 확인합니다.

1. `/` Landing 표시
2. `/login`, `/signup` 표시
3. 로그인 후 `/dashboard` 이동
4. Dashboard에 2026-09-14 실제 workout summary 표시
5. `/history`와 `/history/2026-09-14` 표시
6. `/statistics`, `/profile` 표시
7. Browser 새로고침 후 Session 유지
8. 주소창에서 `/dashboard` 직접 접근 시 404 없음
9. 로그아웃 후 보호 경로가 `/login`으로 이동
10. 로그인하지 않은 상태에서 보호 경로 접근 차단

Browser DevTools → Network에서 다음을 확인합니다.

- Request URL이 `https://fitroute-api.onrender.com/api/...`
- Authorization request header가 `Bearer` 형식으로 존재
- Access Token 실제 값은 복사하거나 보고서에 기록하지 않음
- API response가 200
- Browser Console에 CORS 또는 mixed-content 오류가 없음

Render CORS 변경 후 다른 임의 Origin에는 `Access-Control-Allow-Origin`이 제공되지 않아야 합니다.

## 이 단계의 중단 지점

Vercel Production URL을 확보한 뒤 Render CORS와 Supabase URL을 연결하고 Browser End-to-End를 검증합니다. 그 결과가 성공하기 전에는 Landing 이미지 또는 Camera Exercise UI 개편으로 넘어가지 않습니다.
