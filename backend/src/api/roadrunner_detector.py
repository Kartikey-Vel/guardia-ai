from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from src.api.tweety_auth import get_current_user, User
from src.utils.tasmanian_logger import setup_logger
import asyncio

logger = setup_logger(__name__)

router = APIRouter()

# Initialize empty detector instances (will be populated at startup)
video_detectors = {}
audio_detectors = {}

class DetectorStatus(BaseModel):
    name: str
    type: str
    is_running: bool
    config: Dict[str, Any] = {}

@router.get("/status", response_model=List[DetectorStatus])
async def get_detector_status(current_user: User = Depends(get_current_user)):
    """Get status of all AI detectors."""
    all_detectors = []
    
    # Add video detectors
    for name, detector in video_detectors.items():
        stats = detector.get_stats()
        all_detectors.append(DetectorStatus(
            name=name,
            type="video",
            is_running=stats["is_running"],
            config=stats["config"]
        ))
    
    # Add audio detectors
    for name, detector in audio_detectors.items():
        stats = detector.get_stats()
        all_detectors.append(DetectorStatus(
            name=name,
            type="audio",
            is_running=stats["is_running"],
            config=stats["config"]
        ))
    
    return all_detectors

@router.post("/{detector_type}/{detector_name}/toggle")
async def toggle_detector(
    detector_type: str,
    detector_name: str,
    enable: bool,
    current_user: User = Depends(get_current_user)
):
    """Enable or disable a specific detector."""
    if detector_type == "video":
        if detector_name not in video_detectors:
            raise HTTPException(status_code=404, detail=f"Video detector '{detector_name}' not found")
        video_detectors[detector_name].is_running = enable
        logger.info(f"Video detector '{detector_name}' {'enabled' if enable else 'disabled'} by {current_user.username}")
    elif detector_type == "audio":
        if detector_name not in audio_detectors:
            raise HTTPException(status_code=404, detail=f"Audio detector '{detector_name}' not found")
        audio_detectors[detector_name].is_running = enable
        logger.info(f"Audio detector '{detector_name}' {'enabled' if enable else 'disabled'} by {current_user.username}")
    else:
        raise HTTPException(status_code=400, detail="Invalid detector type. Must be 'video' or 'audio'")
    
    return {"status": "success", "detector": detector_name, "enabled": enable}

@router.post("/simulate/detection")
async def simulate_detection(
    detection_type: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Simulate a detection event for testing purposes."""
    from src.api.bugs_notify import broadcast_security_alert
    
    if detection_type == "motion":
        event = {
            "type": "security_alert",
            "event_type": "motion_detection",
            "description": "Simulated motion detected in restricted area",
            "threat_level": {"level": "low", "score": 0.65},
            "location": "Building A, Zone 2 (Simulated)"
        }
    elif detection_type == "weapon":
        event = {
            "type": "security_alert",
            "event_type": "weapon_detection",
            "description": "Simulated handgun detected",
            "threat_level": {"level": "high", "score": 0.92},
            "location": "Building B, Entrance (Simulated)"
        }
    elif detection_type == "gunshot":
        event = {
            "type": "security_alert",
            "event_type": "gunshot_detection",
            "description": "Simulated gunshot detected",
            "threat_level": {"level": "high", "score": 0.95},
            "location": "Parking Lot, Area C (Simulated)"
        }
    elif detection_type == "scream":
        event = {
            "type": "security_alert",
            "event_type": "scream_detection",
            "description": "Simulated scream detected",
            "threat_level": {"level": "medium", "score": 0.78},
            "location": "Building C, Floor 2 (Simulated)"
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid detection type")
    
    background_tasks.add_task(broadcast_security_alert, event)
    logger.info(f"Simulated {detection_type} detection broadcast by {current_user.username}")
    
    return {
        "status": "success",
        "message": f"Simulated {detection_type} detection event broadcast to all connected clients"
    }
