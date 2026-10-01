# Repository Structure

FitRoute 프로젝트의 주요 디렉터리와 루트 파일 구조입니다. 각 항목은 웹 서비스, AI Client, Windows 배포 및 기술 문서를 역할별로 구분합니다.

```text
AI-Exercise-Assistant/
├─ frontend/                 # React + Vite 기반 웹 애플리케이션
├─ backend/                  # FastAPI API, Supabase 연동, SQL 및 테스트
├─ src/                      # AI Client 실행 소스 코드
├─ desktop_launcher/         # Windows Launcher 및 사용자 인증
├─ packaging/ai_client/      # PyInstaller 설정 및 빌드·분석 도구
├─ installer/                # Inno Setup 설정 및 설치 파일 구성
├─ models/                   # 탐지, Pose 및 분류 모델 파일
├─ config/                   # AI 실행 환경 설정
├─ scripts/                  # 환경 설정 및 Windows Release 자동화 스크립트
├─ tests/                    # AI Client 및 Launcher 테스트
├─ releases/windows/         # Windows 버전별 Release metadata 및 Production 상태
├─ data/workout_logs/        # 로컬 운동 기록 저장용 디렉터리
├─ docs/                     # 아키텍처, 배포 및 기술 문서
├─ requirements.txt          # AI 개발 환경 의존성
├─ .vercelignore             # Vercel 배포 대상 제외·제한 설정
└─ README.md                 # 프로젝트 메인 문서
```
