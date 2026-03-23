# export_model.py
# Run once: python3 export_model.py
from ultralytics import YOLO
import os

PT_MODEL = "yolov8m.pt"
ENGINE   = "yolov8m.engine"

if os.path.exists(ENGINE):
    print(f"✅ Engine already exists: {ENGINE}")
    print("   Delete it and re-run to re-export.")
else:
    print(f"Converting {PT_MODEL} → {ENGINE}")
    print("This will take 5–10 minutes on first run...")
    model = YOLO(PT_MODEL)
    model.export(
        format="engine",
        half=True,       # FP16 — best speed/accuracy balance on Orin
        device=0,
        imgsz=640,
        workspace=4,     # GB of GPU workspace for TensorRT
    )
    print(f"✅ Done! Engine saved: {ENGINE}")