# 👨‍💻 Kartikey's Project Handoff & Testing Guide

Welcome, Kartikey. You have been assigned as the **Lead QA & System Validator** for the Guardia AI Multimodal Pipeline. Your goal is to ensure that the fusion of Vision, Motion, and Audio is seamless, resilient, and production-ready.

---

## 📂 1. System Setup & Folder Arrangement

The project is divided into a **FastAPI Backend** and a **Next.js Frontend**. Ensure your local environment is structured exactly as follows:

```text
guardia-ai/
├── backend/                # Primary AI & Logic Hub
│   ├── ai/                 # Core AI modules (Gemini, Groq, YOLO, Audio)
│   ├── .env                # Your local secrets (API keys)
│   ├── main.py             # Server entry point
│   └── requirements.txt    # Python dependencies
├── frontend/               # Dashboard UI
│   ├── .env.local          # Dashboard configuration
│   └── components/         # Real-time UI modules
└── docs/                   # System manuals
```

### Setup Steps:
1.  **Environment**: Create a Python 3.11 virtual environment.
2.  **Dependencies**: Run `pip install -r backend/requirements.txt`.
3.  **Frontend**: Run `npm install` inside the `frontend/` directory.

---

## 🔑 2. Environment Variables (.env)

This is the most critical step for the AI Key Rotation logic. **Arrange yours exactly like this in `backend/.env`**:

```env
# Google Gemini (Vision) — Use multiple for rotation
GEMINI_API_KEYS="key_1,key_2,key_3"
GEMINI_MODEL="gemini-1.5-flash"

# Groq (Fusion Reasoning) — The brain
GROQ_API_KEYS="gsk_key_1,gsk_key_2"
GROQ_MODEL="llama3-70b-8192"

# HuggingFace (Audio Detection)
HUGGINGFACE_API_KEYS="hf_token_here"

# Detection Thresholds
ALERT_THRESHOLD=6  # Severity above this triggers a broadcast
```

---

## ✅ 3. Kartikey's Testing Checklist

You are responsible for signing off on the following modules. Mark these as done incrementally:

### 🔬 [ ] AI Key Rotation Logic
- [ ] Provide 1 invalid/expired key and 1 valid key in `.env`.
- [ ] Trigger an analysis (via `/api/v1/demo/trigger`).
- [ ] **Expectation**: Backend logs show a failure on Key 1, then a successful rotation and fallback to Key 2.

### 🎥 [ ] Multimodal Fusion Accuracy
- [ ] Trigger the `forced_entry` scenario.
- [ ] **Expectation**: Verify that the final severity is **high** (8+) because it combined "broken glass" audio with "loitering" visual motion.

### 🎙️ [ ] Audio Detector Handshake
- [ ] Run the backend and watch the logs during a process loop.
- [ ] **Expectation**: Logs should show `Audio Analysis: [Label] ([Score])` whenever motion is detected.

### ⚡ [ ] Real-time Dashboard Sync
- [ ] Start the backend (`uvicorn main:app`).
- [ ] Start the frontend (`npm run dev`).
- [ ] Open the browser and trigger a demo event.
- [ ] **Expectation**: The alert appears in the `AlertList` **instantly** without a page refresh.

---

## 📝 4. Setup Guide for Production
Ensure the `NEXT_PUBLIC_API_URL` in `frontend/.env.local` points to `http://localhost:8000`. If you change the port, update the `WS_URL` in `AlertProvider.tsx`.

---

> [!IMPORTANT]
> **Your Final Task**: After completing the checklist, update the `GUARDIA_AI_SDLC.md` status to "VERIFIED BY KARTIKEY" and provide a summary of any latency bottlenecks you found.
