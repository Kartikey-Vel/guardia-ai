# Guardia AI — Multimodal Test Cases

Use these test cases to verify the integrity of the integrated surveillance pipeline.

## 1. Visual Anomaly Detection
- **Purpose**: Verify Gemini's ability to describe suspicious visual scenes.
- **Trigger**: Run `POST /api/v1/demo/trigger` with scenario `loitering`.
- **Expected Result**: 
    - Alert appears in `AlertList`.
    - Classification: `SUSPICIOUS_LOITERING`.
    - Attribution contains `motion_score` and `detected_objects` (human).

## 2. Audio Anomaly Fusion
- **Purpose**: Verify that audio signals elevate the risk level.
- **Trigger**: Run `POST /api/v1/demo/trigger` with scenario `forced_entry`.
- **Expected Result**:
    - Alert severity >= 8 (CRITICAL).
    - Description mentions both visual motion and audio cues (e.g., "Glass breaking detected").

## 3. API Key Rotation (Quota Limit)
- **Purpose**: Ensure zero downtime when a service hits a limit.
- **Setup**: Provide an expired/invalid key first in `.env`, followed by a valid one.
- **Trigger**: Any AI analysis request.
- **Expected Result**:
    - Backend logs show `429 Client Error` for first key.
    - `KeyRotator` switches to the next available key.
    - Response is still successful after a short delay.

## 4. Real-time Dashboard Sync
- **Purpose**: Verify WebSocket data flow.
- **Test**: Open the Dashboard in two separate browser tabs.
- **Trigger**: A demo event.
- **Expected Result**: Both tabs show the new alert simultaneously without page refresh.

## 5. Metadata & Review Flow
- **Purpose**: Verify the "Source of Truth" from AI agents.
- **Action**: Click "Review" on an alert in the dashboard.
- **Expected Result**:
    - Alert persists but appears "dimmed" or checked.
    - Clicking the alert shows the full `Groq` reasoning and `Gemini` visual description.
