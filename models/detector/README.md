# Person Detector Assets

This directory contains YOLO26n person-detection artifacts.

- `yolo26n.engine`: Windows AI Client의 우선 실행 대상인 TensorRT FP16 engine. 환경 종속 파일이므로 Git에는 포함하지 않습니다.
- `yolo26n.pt`: 개발 환경의 PyTorch fallback 및 export 입력입니다.
- `yolo26n.onnx`, `yolo26n.fp16.onnx`: 향후 fallback 검토를 위해 보존한 ONNX 자산입니다.

`scripts/export_yolo26n_tensorrt.py`가 export 진입점입니다. TensorRT engine은 생성 GPU, TensorRT와 runtime 환경에 민감하므로 모든 NVIDIA GPU에서의 호환성을 가정하지 않습니다.
