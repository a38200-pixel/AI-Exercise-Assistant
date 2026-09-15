# Windows Release Metadata

`release_windows.ps1`이 R2 업로드와 원격 크기 검증을 완료한 뒤 `v<VERSION>.json`을 생성한다. `promote_windows_release.ps1`은 성공한 Production 배포 상태를 `production.json`에 기록한다.

이 디렉터리에는 version, 공개 다운로드 URL, 파일 크기, SHA-256 같은 비밀이 아닌 release 정보만 저장한다. R2 및 Vercel 인증 정보는 저장하지 않는다.
