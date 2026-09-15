# Windows Release Process

FitRoute Windows Desktop Client는 build/upload와 Production 반영을 분리한다. Release object는 version별로 불변이며, 스크립트는 commit, tag 또는 push를 자동 실행하지 않는다.

```text
Code
  ↓
Build → Validate → SHA-256
  ↓
Cloudflare R2 versioned upload
  ↓
Other-PC E2E test
  ↓
Vercel Production promotion
  ↓
Production
```

## Prerequisites

- Inno Setup 6 (`ISCC.exe`)
- Python과 검증된 Installer 입력 bundle
- `rclone` remote `r2`와 bucket-scoped credential
- Vercel CLI 로그인 및 `frontend/.vercel/project.json` project link
- 깨끗한 Git working tree

R2 Access Key, Secret, API token과 Vercel token은 source, metadata 또는 명령행에 넣지 않는다. 기존 rclone credential store와 Vercel CLI login을 사용한다. R2 public base URL은 공개 설정값이므로 parameter 또는 `FITROUTE_R2_PUBLIC_BASE_URL` 환경변수로 전달한다.

외부 도구는 다음 순서로 탐색하며 PATH를 영구 변경하거나 패키지를 자동 설치하지 않는다.

- rclone: PATH의 `rclone.exe`/`rclone`, `%LOCALAPPDATA%\Microsoft\WinGet\Links\rclone.exe`
- Inno Setup: PATH의 `ISCC.exe`, `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`, Program Files 경로
- Vercel: PATH의 `vercel.cmd`/`vercel`, `%APPDATA%\npm\vercel.cmd`, 사용 가능한 경우 npm global prefix

Promotion preflight는 resolve된 Vercel 실행 파일로 `vercel whoami`를 호출한다. 인증이 확인되지 않으면 Production 변경 전에 중단하며 `vercel login`을 자동 실행하지 않는다. 사용자가 직접 로그인한 뒤 다시 실행해야 한다. `-DryRun`도 executable discovery와 Vercel 인증 확인을 수행하지만 upload, 환경변수 변경이나 deploy는 수행하지 않는다.

## 1. Prepare

먼저 안전한 계획을 확인한다.

```powershell
$env:FITROUTE_R2_PUBLIC_BASE_URL='https://<public-r2-host>'
.\scripts\release_windows.ps1 -Version 0.1.1 -DryRun
```

`-DryRun`은 local validator를 실행하고 build/upload 예정 명령과 경로를 출력하지만 Installer build, R2 요청, metadata 저장 또는 Git 변경은 하지 않는다. 실제 prepare는 다음과 같다.

```powershell
.\scripts\release_windows.ps1 -Version 0.1.1
```

Prepare 단계는 다음 순서로 동작한다.

1. SemVer와 Git working tree를 검사한다.
2. release metadata와 동일 버전 local Installer가 없는지 확인한다.
3. Installer validator를 요청 version으로 실행한다.
4. R2에 동일 object가 없는지 확인한다.
5. Inno Setup에 version define을 주입해 Installer를 빌드한다.
6. filename, bytes, MiB/GiB와 SHA-256을 계산한다.
7. 아래 경로에 `--immutable`로 업로드한다.
8. remote object 존재 여부와 byte 크기를 다시 확인한다.
9. 모든 검증이 끝난 후에만 release metadata를 기록한다.

```text
r2:fitroute-downloads/releases/v0.1.1/FitRoute-AI-Client-Setup-0.1.1.exe
releases/windows/v0.1.1.json
```

대용량 전송 설정:

```text
--s3-no-check-bucket
--s3-upload-cutoff=100M
--s3-chunk-size=100M
--immutable
```

동일 version의 local Installer, metadata 또는 R2 object가 있으면 중단한다. 기존 binary를 바꾸려면 반드시 새 version을 사용한다.

Release metadata에는 다음 공개 정보만 들어간다.

```json
{
  "version": "0.1.1",
  "filename": "FitRoute-AI-Client-Setup-0.1.1.exe",
  "size_bytes": 0,
  "sha256": "<64-hex-digest>",
  "r2_object_key": "releases/v0.1.1/FitRoute-AI-Client-Setup-0.1.1.exe",
  "download_url": "https://<public-r2-host>/releases/v0.1.1/FitRoute-AI-Client-Setup-0.1.1.exe",
  "built_at": "<UTC ISO-8601>"
}
```

## 2. Test

Prepare가 성공해도 즉시 Production으로 전환하지 않는다. 별도 Windows PC에서 다음 흐름을 확인한다.

Prepare 후 생성된 `installer/installer_manifest.json`과 `releases/windows/v<VERSION>.json`을 검토한다. Promotion은 clean working tree를 요구하므로 필요한 release 변경은 사용자가 직접 commit한 뒤 진행한다. 스크립트는 commit이나 push를 대신 수행하지 않는다.

```text
웹 다운로드 → 설치 → fitroute:// 실행 → Desktop 로그인
→ Camera/AI 운동 → Render/Supabase 저장 → Dashboard 조회 → 제거
```

테스트한 binary의 SHA-256이 release metadata와 같은지 확인한다.

## 3. Promote

먼저 변경 내용을 dry-run으로 확인한다.

```powershell
.\scripts\promote_windows_release.ps1 -Version 0.1.1 -DryRun
```

첫 Production promotion에서 `releases/windows/production.json`이 아직 없다면 현재 공개 URL을 명시한다.

```powershell
.\scripts\promote_windows_release.ps1 `
  -Version 0.1.1 `
  -CurrentDownloadUrl 'https://<current-public-url>' `
  -ApproveProductionChange
```

이후에는 마지막 성공 상태에서 현재 URL을 읽는다. `-ApproveProductionChange`가 없으면 Vercel 환경변수 변경 전에 중단한다.

승인된 promotion은 다음을 수행한다.

1. `v<VERSION>.json` schema, SHA-256과 canonical object key를 검사한다.
2. R2 object의 존재 여부와 byte 크기를 metadata와 비교한다.
3. Vercel CLI 설치, 로그인과 project link를 검사한다.
4. 현재 URL과 변경할 URL을 표시한다.
5. `VITE_DESKTOP_CLIENT_DOWNLOAD_URL`의 Production 값을 갱신한다.
6. `vercel deploy --prod --yes`를 실행한다.
7. deployment URL과 실제 Frontend Production HTTP 상태를 확인한다.
8. 성공한 경우에만 `releases/windows/production.json`을 갱신한다.

## 4. Rollback

이전 release metadata와 R2 object는 삭제하지 않는다. 동일한 promotion script에 이전 version을 전달한다.

```powershell
.\scripts\promote_windows_release.ps1 -Version 0.1.0 -DryRun
.\scripts\promote_windows_release.ps1 -Version 0.1.0 -ApproveProductionChange
```

이는 R2 binary를 수정하지 않고 Vercel의 공개 다운로드 URL을 기존 version으로 되돌린 뒤 Production을 재배포한다.

## Failure policy

- validator 또는 build 실패: upload 금지
- R2 object 충돌: overwrite 없이 즉시 중단
- upload/remote size 검증 실패: metadata 완료 처리 금지
- metadata/R2 검증 실패: promotion 금지
- Vercel env update 실패: deploy 금지
- Vercel deploy/Production HTTP 검사 실패: 성공 상태 기록 금지

스크립트는 `$ErrorActionPreference = 'Stop'`을 사용한다. 자동 commit, tag, push와 R2 delete 기능은 제공하지 않는다. 필요하면 검토 후 사용자가 직접 tag를 생성한다.

```powershell
git tag v0.1.1
git push origin v0.1.1
```

## CLI references

- [rclone `copyto`](https://rclone.org/commands/rclone_copyto/)
- [rclone `lsjson`](https://rclone.org/commands/rclone_lsjson/)
- [rclone S3 `--s3-no-check-bucket`](https://rclone.org/s3/)
- [Vercel environment variables CLI](https://vercel.com/docs/cli/env)
- [Vercel deploy CLI](https://vercel.com/docs/cli/deploy)
