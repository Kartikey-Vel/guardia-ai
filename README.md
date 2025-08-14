# Guardia-AI: Real-Time Threat & Object Detection (Laptop PoC)

Lightweight, real-time person/object detection with harmful object flagging and basic behavior analysis. Optimized for low-resource laptops using frame skipping, motion filters, ROI cropping, and background threads. Local YOLOv8n for speed + optional Google Vision verification + Mediapipe pose checks.

## Features
- YOLOv8n local detection (people, common objects)
- Harmful object flagging (knife, gun, etc.) with red overlays
- Motion-aware frame processing and frame skipping
- Optional Google Vision API verification for ROIs
- Optional Mediapipe Pose for aggressive gestures (raised hands, brandishing)
- Logging to CSV/JSON and optional snapshots for harmful events
- Works with webcam or video file

## Quick Start
1) Python 3.10+
2) Create venv and install deps

```powershell
# From repo root
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

3) Optional: Google Vision
- Create a GCP project, enable Vision API, create a service account key (JSON)
- Set env var to key path before running:
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\\path\\to\\service-account.json"
```

4) Run the app (webcam default):
```powershell
python -m src.app --source 0 --frameskip 3 --show
```

Use a video file:
```powershell
python -m src.app --source "samples\\test.mp4" --frameskip 3 --show
```

5) Exit with 'q' key or window close.

## Config Highlights
- Harmful labels: see `src/config.py` (e.g., ["knife", "gun", "rifle", "sword"])
- Vision: toggle with `--vision` or env `GUARDIA_USE_VISION=1`
- Pose: toggle with `--pose` or env `GUARDIA_USE_POSE=1`
- Snapshots: set `--snapshots` to save images on harmful events

## Notes
- On first run, ultralytics downloads YOLO weights (internet required). If blocked, place weights locally and set `YOLO_WEIGHTS` env var.
- Mediapipe and OpenCV may need extra system dependencies. If pose is disabled, pipeline still runs.
- For low-spec machines, increase `--frameskip`, enable `--motion`, and reduce `--max-vision-fps`.

## License
For demo/PoC purposes. Use responsibly and comply with local laws and privacy policies.

## Flask Dashboard GUI
- Start the web dashboard (MJPEG stream + metrics + events + optional Gemini summary):

Windows PowerShell:
```powershell
. .venv\Scripts\Activate.ps1
python -m src.server
```

Git Bash:
```bash
source .venv/Scripts/activate
python -m src.server
```

Open http://localhost:5000 in your browser.

## Git Bash Quick Start
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Environment & API Setup

Google Vision API:
- In Google Cloud Console: create project -> enable Vision API
- Create service account with Vision roles; create key (JSON); download it
- Set the environment variable before running:
	- PowerShell: `$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\\path\\to\\service-account.json"`
	- Git Bash: `export GOOGLE_APPLICATION_CREDENTIALS="/c/path/to/service-account.json"`

Gemini API (optional for summaries):
- Get an API key from Google AI Studio (https://aistudio.google.com/)
- Set the environment variable:
	- PowerShell: `$env:GEMINI_API_KEY = "YOUR_KEY"`
	- Git Bash: `export GEMINI_API_KEY="YOUR_KEY"`

Other tips:
- Configure harmful labels in `src/config.py`
- Toggle Vision/Pose via flags or env vars: `GUARDIA_USE_VISION=1`, `GUARDIA_USE_POSE=1`
- Limit Vision calls per second: `--max-vision-fps 1`
