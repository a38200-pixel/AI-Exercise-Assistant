# FitRoute Documentation

FitRoute의 현재 구조, Production 운영, Windows 패키징과 완료된 최적화 검증 기록을 주제별로 정리한 문서 인덱스입니다. 서비스 개요와 최신 상태는 먼저 [프로젝트 README](../README.md)를 확인합니다.

## Product and architecture

- [초기 UI 시안](%EC%98%88%EC%83%81%20UI.png)
- [주요 Web 화면](FitRoute_%EC%A3%BC%EC%9A%94%ED%99%94%EB%A9%B4.png)
- [실제 운동 실행 화면](FitRoute_%EC%9A%B4%EB%8F%99_%EC%8B%A4%ED%96%89%ED%99%94%EB%A9%B4.png)
- [서비스 구조](FitRoute_서비스_구조.png)
- [시스템 흐름도](FitRoute_%EC%8B%9C%EC%8A%A4%ED%85%9C_%ED%9D%90%EB%A6%84%EB%8F%84.png)
- [최초 설치 흐름](FitRoute_%EC%B5%9C%EC%B4%88_%EC%84%A4%EC%B9%98_%ED%9D%90%EB%A6%84.png)

`docs`의 PNG 원본은 설계 및 포트폴리오 자료로 보존한다.

## Current implementation and operations

- [Frontend guide](../frontend/README.md)
- [Backend/API guide](../backend/README.md)
- [Desktop Launcher guide](../desktop_launcher/README.md)
- [Windows release metadata](../releases/windows/README.md)

## Deployment and release

- [Production deployment checklist](production_deployment_checklist.md)
- [Render Backend deployment](render_backend_staging.md)
- [Vercel Frontend deployment](vercel_frontend_staging.md)
- [Windows release process](windows_release_process.md)

## Windows desktop client

- [Desktop launcher](desktop_client_launcher.md)
- [AI Client packaging and validation record](ai_client_packaging_plan.md)
- [Windows installer](windows_installer.md)

## Completed engineering analysis

- [Bundle size analysis](ai_client_bundle_size_analysis.md)
- [Torch slimming analysis](ai_client_torch_slimming_analysis.md)
- [Runtime module trace summary](runtime_module_trace.md)

위 분석 문서는 최종 결론과 함께 과거 candidate의 성공·실패 근거를 보존한 완료 기록입니다. 기계별 절대경로가 포함되는 전체 inventory와 runtime trace 원본은 `artifacts/`에 생성되며 Git에는 포함하지 않습니다.
