# Runtime Performance

> **측정 시점**: v0.1.1 패키징 AI Client(2026-09-16)입니다. v0.2.0에서는 같은 방법(설치된 클라이언트의 End-to-End 실측)으로 재측정하지 않았습니다.
>
> **참고(v0.2.0, 같은 방법 아님)**: 2026-10-18~19 실측 로그의 프레임 시각으로 본 처리 속도는 중앙값 약 17 FPS입니다(1차 로그 12개(무효 세션 제외)의 중앙값 16.9~17.3, 하위 5% 14.4~15.7, 연속 세트 두 세션 중앙값 17.1·하위 5% 15.5~15.6). 개발 실행(`python -m src.main --log-sequence`)에서 landmark 로깅을 켠 조건이며(로깅이 메인 스레드에 쓰는 시간은 프레임당 중앙값 0.084ms), 설치판 측정이 아니고 방법도 달라 아래 15.84 FPS와 직접 비교할 수 없습니다. 출처: [data_quality.csv](versions/v0.2.0/analysis/field_test_1/data_quality.csv), [continuous_repro/report.md](versions/v0.2.0/analysis/continuous_repro/report.md).

최종 패키징 AI Client의 실제 Webcam 환경 측정 결과입니다.

- **End-to-End:** 15.84 FPS
- **AI Inference:** 21.20 FPS
- **평균 Inference Latency:** 47.18 ms

End-to-End FPS는 Camera 입력, AI inference, 운동 로직, 화면 렌더링 등 실제 Client 전체 처리 흐름을 포함한 값이며, Inference FPS는 YOLO26n(TensorRT 추론) → MediaPipe → XGBoost AI pipeline 처리 기준 값입니다.
