#!/usr/bin/env python
# Quick training on coco128 to produce a ready-to-use ONNX model for the app.
# Uses YOLOv8n for a fast baseline; swap model path as desired.

from __future__ import annotations
import os
from pathlib import Path

try:
    from ultralytics import YOLO
except Exception as e:
    print("[ERR] Ultralytics not installed. pip install ultralytics")
    raise


def main() -> int:
    # Prefer GPU if explicitly set via env; otherwise default to CPU.
    device_env = os.environ.get("GUARDIA_DEVICE", "cpu").lower()
    device = "cuda" if device_env == "cuda" else "cpu"
    model = YOLO("yolov8n.pt")  # small and fast baseline

    # Train briefly on coco128 (demo dataset bundled by Ultralytics)
    # This is a quick starter; for custom data, point data= to your dataset.yaml
    results = model.train(
        data="coco128.yaml",
        epochs=int(os.environ.get("GUARDIA_TRAIN_EPOCHS", 5)),
        imgsz=int(os.environ.get("YOLO_IMGSZ", 640)),
        device=device,
        batch=int(os.environ.get("GUARDIA_TRAIN_BATCH", 16)),
        project="runs",
        name="detect_train",
        exist_ok=True,
    )

    # Export to ONNX for edge runtime
    export_res = model.export(
        format="onnx",
        opset=12,
        dynamic=True,
        imgsz=int(os.environ.get("YOLO_IMGSZ", 640)),
    )

    # Ultralytics typically writes to runs/detect/exp*/weights/best.onnx
    # Resolve the newest best.onnx
    runs_dir = Path("runs")
    best = None
    if runs_dir.exists():
        exps = sorted(runs_dir.glob("**/weights/best.onnx"), key=lambda p: p.stat().st_mtime, reverse=True)
        if exps:
            best = exps[0]
    if best:
        print(f"[OK] Exported ONNX: {best}")
    else:
        print("[WARN] Could not locate best.onnx; check runs/detect folders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
