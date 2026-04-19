# Guardia AI — Project Handover Notes

## 🎯 Current Milestone: MVP Complete
Guardia AI is now at a production-ready MVP stage with a fully functional multimodal pipeline and real-time dashboard.

## 🚀 Accomplishments
- **Multimodal IQ**: Integrated Vision (Gemini), Audio (HuggingFace), and Motion (OpenCV) with Groq-powered reasoning.
- **Service Resilience**: Implemented automatic API key rotation for Gemini, Groq, and HuggingFace to bypass quota limits.
- **Real-time Pipeline**: Established a WebSocket bridge (`/ws/alerts`) that pushes live security events directly to the Next.js frontend.
- **Premium Frontend**: Rebuilt the dashboard with a glassmorphic aesthetic using HeroUI v3 and real-time state management.

## 📁 Key File Map
- **Backend Core**: `backend/ai/pipeline.py` (Orchestrates all agents).
- **Frontend Logic**: `frontend/components/providers/AlertProvider.tsx` (WebSocket consumer).
- **API Definition**: `frontend/lib/api-client.ts` (Typed backend communication).
- **AI Modules**: `backend/ai/` (Contains gemini, groq, audio, and yolo logic).

## 🛠 Next Steps (Post-MVP)
1. **Persistent Streaming**: Integrate real RTSP stream decoding using `FFmpeg` or `aiortc` for the frontend.
2. **Database Persistence**: Fully migrate the in-memory demo registry to a PostgreSQL instance for historical log tracking.
3. **Hardware Integration**: Implement local audio sampling on the edge device to feed the `AudioDetector`.

## ⚠️ Known Notes
- The current video feeds in the dashboard are **simulated visuals** while the AI logic performs **real analysis** on underlying frame buffers.
- Ensure the backend is running (`uvicorn main:app --reload`) before starting the frontend to avoid WebSocket connection errors.
