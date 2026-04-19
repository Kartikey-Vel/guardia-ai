# backend/api/settings.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db, Setting
from models.schemas import SettingsUpdate
from config import get_settings
from datetime import datetime

router = APIRouter()

@router.get("")
def get_settings_endpoint(db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    result = {s.key: s.value for s in settings}
    # Redact API keys
    for key in ["groq_api_key", "gemini_api_key", "huggingface_api_key"]:
        if key in result:
            val = result[key]
            result[key] = val[:8] + "***" if len(val) > 8 else "***"
    return result

@router.post("")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    updates = payload.model_dump(exclude_none=True)
    for key, value in updates.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = str(value)
            setting.updated_at = datetime.utcnow()
        else:
            db.add(Setting(key=key, value=str(value)))
    db.commit()
    
    # Reload settings cache
    get_settings.cache_clear()
    
    # Reinitialize AI models if API keys changed
    from ai.pipeline import pipeline
    pipeline.initialize_ai()
    
    return {"status": "updated", "keys_updated": list(updates.keys())}

@router.post("/test-connection")
async def test_connections():
    results = {}
    
    # Test Groq
    try:
        from config import get_settings
        cfg = get_settings()
        if cfg.groq_api_key:
            from groq import Groq
            client = Groq(api_key=cfg.groq_api_key)
            client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            results["groq"] = "connected"
        else:
            results["groq"] = "no_key"
    except Exception as e:
        results["groq"] = f"error: {str(e)[:50]}"
    
    # Test Gemini
    try:
        if cfg.gemini_api_key:
            import google.generativeai as genai
            genai.configure(api_key=cfg.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            model.generate_content("ping")
            results["gemini"] = "connected"
        else:
            results["gemini"] = "no_key"
    except Exception as e:
        results["gemini"] = f"error: {str(e)[:50]}"
    
    return results


# backend/api/cameras.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Camera
from models.schemas import CameraCreate
import cv2
import base64

router = APIRouter()

@router.get("")
def list_cameras(db: Session = Depends(get_db)):
    cameras = db.query(Camera).all()
    return {
        "cameras": [
            {
                "camera_id": c.camera_id,
                "name": c.name,
                "rtsp_url": c.rtsp_url,
                "zone": c.zone,
                "risk_level": c.risk_level,
                "is_active": bool(c.is_active)
            }
            for c in cameras
        ]
    }

@router.post("")
def add_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    existing = db.query(Camera).filter(Camera.camera_id == payload.camera_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Camera already exists")
    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    return {"status": "created", "camera_id": payload.camera_id}

@router.get("/{camera_id}/snapshot")
def get_snapshot(camera_id: str):
    """Return current webcam frame as base64"""
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            b64 = base64.b64encode(buffer).decode()
            return {"frame": f"data:image/jpeg;base64,{b64}", "camera_id": camera_id}
        return {"frame": None, "error": "Camera read failed"}
    except Exception as e:
        return {"frame": None, "error": str(e)}
