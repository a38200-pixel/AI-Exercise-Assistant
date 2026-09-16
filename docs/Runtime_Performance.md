# Runtime Performance

최종 패키징 AI Client의 실제 Webcam 환경 측정 결과입니다.

- **End-to-End:** 15.84 FPS
- **AI Inference:** 21.20 FPS
- **평균 Inference Latency:** 47.18 ms

End-to-End FPS는 Camera 입력, AI inference, 운동 로직, 화면 렌더링 등 실제 Client 전체 처리 흐름을 포함한 값이며, Inference FPS는 YOLO26n(TensorRT 추론) → MediaPipe → XGBoost AI pipeline 처리 기준 값입니다.
