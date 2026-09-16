# Release Workflow

## Release Workflow

```text
Prepare
  ↓
Installer Build
  ↓
SHA-256 / Size Verification
  ↓
R2 Immutable Upload
  ↓
Release Metadata
  ↓
Separate Windows PC E2E Test
  ↓
Promote
  ↓
Vercel Production Deploy
  ↓
Production HTTP Verification
```

---

## Release 원칙

- `SemVer` 기반 version 관리
- R2 object를 버전별 경로에 저장
- 동일 version overwrite 금지 (`--immutable`)
- Production 반영 전 별도 Windows PC E2E 수행
- Promote는 명시적인 승인 후에만 실행
- 이전 version metadata와 R2 object를 이용해 rollback 가능
- 성공한 deploy와 HTTP 검증 이후에만 `production.json` 갱신
