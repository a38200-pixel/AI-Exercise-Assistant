# Person detector models

This directory contains YOLO26n person-detection artifacts.

- `yolo26n.pt`: optional PyTorch model; the export script downloads/prepares it when needed.
- `yolo26n.engine`: TensorRT FP16 engine generated locally by the export script.

TensorRT engines are machine/environment-specific and ignored by Git.

