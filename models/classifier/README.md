# Pose Classifier Assets

현재 AI Client가 사용하는 XGBoost 자세 분류 자산입니다.

- `models/classifier/model_weights.xgb`
- `models/classifier/classes.json`

`classes.json`은 학습 당시 class 순서를 유지해야 합니다. 현재 label은 `squat`, `run`, `sit`, `stretch`, `walk`, `jump`, `bendover`, `stand`, `lying`이며, AI Client는 33개 landmark에서 만든 132개 feature로 분류합니다. 모델을 교체할 때는 두 파일을 함께 검증해야 합니다.
