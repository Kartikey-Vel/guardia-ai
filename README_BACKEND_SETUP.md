# Backend Setup Guide (Windows, Linux/Ubuntu, macOS)

This guide helps any contributor scaffold and prepare the backend environment quickly.

Note:
- Backend code files are templates only right now.
- Dependencies are fully listed and can be installed immediately.

## 1) Prerequisites
- Python 3.11 recommended
- pip (bundled with Python)
- Git

## 2) Clone
```bash
git clone https://github.com/codernotme/guardia-ai.git
cd guardia-ai
```

## 3) Create Virtual Environment
### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If execution policy blocks activation:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Linux / Ubuntu / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4) Install Backend Dependencies
### Runtime only
```bash
pip install -r backend/requirements.txt
```

### Runtime + development tools
```bash
pip install -r backend/requirements-dev.txt
```

## 5) Configure Environment Variables
Copy template and edit values.

### Windows (PowerShell)
```powershell
Copy-Item backend/.env.example backend/.env
```

### Linux / Ubuntu / macOS
```bash
cp backend/.env.example backend/.env
```

Update at least:
- GEMINI_API_KEY
- GROQ_API_KEY
- HUGGINGFACE_API_KEY

## 6) Verify Installation
```bash
python -m pip --version
python -c "import fastapi, sqlalchemy, cv2, numpy; print('backend deps ok')"
```

## 7) Backend Scaffold Structure
```text
backend/
  api/
  ai/
  models/
  websocket/
  utils/
  main.py
  config.py
  database.py
  .env.example
  requirements.txt
  requirements-dev.txt
```

## 8) Common Commands
### Freeze installed versions
```bash
pip freeze > backend/requirements.lock.txt
```

### Deactivate venv
```bash
deactivate
```

## 9) Troubleshooting
### OpenCV install errors
Upgrade pip and retry:
```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
```

### Using a different Python executable
Windows:
```powershell
py -3.11 -m venv .venv
```
Linux/macOS:
```bash
python3.11 -m venv .venv
```

## 10) Next Step for Developers
Once scaffold is ready, start implementing module logic in template files under backend/.
