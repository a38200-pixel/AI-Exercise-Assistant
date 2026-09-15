# FitRoute Documentation

프로젝트의 설계, 배포, Windows 패키징과 검증 기록을 주제별로 정리한 문서 인덱스다.

## Product and architecture

- [서비스 UI 시안](UI.png)
- [서비스 구조](FiteRoute_서비스_구조.png)
- [시스템 흐름도](FitRoute_시스템%20흐름도.png)
- [아키텍처 다이어그램](FitRoute_아키텍쳐_다이어그램.png)
- [전체 흐름 다이어그램](전체%20흐름%20다이어그램.png)

`docs`의 PNG 원본은 설계 및 포트폴리오 자료로 보존한다.

## Deployment

- [Production deployment checklist](production_deployment_checklist.md)
- [Render backend staging](render_backend_staging.md)
- [Vercel frontend staging](vercel_frontend_staging.md)
- [Backend operations](../backend/README.md)

## Windows desktop client

- [Desktop launcher](desktop_client_launcher.md)
- [AI Client packaging plan](ai_client_packaging_plan.md)
- [Windows installer](windows_installer.md)

## Bundle optimization

- [Bundle size analysis](ai_client_bundle_size_analysis.md)
- [Torch slimming analysis](ai_client_torch_slimming_analysis.md)
- [Runtime module trace summary](runtime_module_trace.md)

전체 module inventory와 runtime trace 같은 기계별 원시 보고서는 `artifacts/`에 생성되며 Git에는 포함하지 않는다. 저장소에는 재현 스크립트와 검토 가능한 요약 문서만 유지한다.
