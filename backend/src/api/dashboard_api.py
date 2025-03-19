from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from src.api.tweety_auth import get_current_user, User
from src.db.porky_mongo import get_events_collection
from src.utils.tasmanian_logger import setup_logger
from src.api.roadrunner_detector import video_detectors, audio_detectors

router = APIRouter()
logger = setup_logger(__name__)

class SystemStatus(BaseModel):
    system_status: str
    ai_modules: Dict[str, bool]
    events_24h: int
    alerts: int
    detectors_online: int
    detectors_offline: int
    last_updated: str

@router.get("/status", response_model=SystemStatus)
async def get_system_status(current_user: User = Depends(get_current_user)):
    """Get the current status of the entire system for the main dashboard."""
    events_collection = await get_events_collection()
    
    # Count events in the last 24 hours
    cutoff_date = datetime.now() - timedelta(days=1)
    events_24h = await events_collection.count_documents({
        "timestamp": {"$gte": cutoff_date}
    })
    
    # Count unacknowledged alerts (treat as active alerts)
    alerts = await events_collection.count_documents({
        "acknowledged": False
    })
    
    # Check AI detector status
    detectors_online = 0
    detectors_offline = 0
    ai_modules = {}
    
    for name, detector in video_detectors.items():
        ai_modules[f"video_{name}"] = detector.is_running
        if detector.is_running:
            detectors_online += 1
        else:
            detectors_offline += 1
    
    for name, detector in audio_detectors.items():
        ai_modules[f"audio_{name}"] = detector.is_running
        if detector.is_running:
            detectors_online += 1
        else:
            detectors_offline += 1
    
    # Determine overall system status
    system_status = "operational"
    if detectors_offline > 0:
        if detectors_online > 0:
            system_status = "degraded"
        else:
            system_status = "offline"
    
    return SystemStatus(
        system_status=system_status,
        ai_modules=ai_modules,
        events_24h=events_24h,
        alerts=alerts,
        detectors_online=detectors_online,
        detectors_offline=detectors_offline,
        last_updated=datetime.now().isoformat()
    )

@router.get("/recent-events")
async def get_recent_events(
    limit: int = Query(5, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """Get the most recent security events for dashboard display."""
    events_collection = await get_events_collection()
    
    # Get the most recent events
    cursor = events_collection.find().sort("timestamp", -1).limit(limit)
    events = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string for each event
    for event in events:
        event["id"] = str(event.pop("_id"))
    
    return events

@router.get("/threat-summary")
async def get_threat_summary(current_user: User = Depends(get_current_user)):
    """Get a summary of threats for quick dashboard visualization."""
    events_collection = await get_events_collection()
    
    # Time periods for analysis
    cutoff_24h = datetime.now() - timedelta(days=1)
    cutoff_7d = datetime.now() - timedelta(days=7)
    cutoff_30d = datetime.now() - timedelta(days=30)
    
    # Count high priority threats in different time periods
    high_24h = await events_collection.count_documents({
        "timestamp": {"$gte": cutoff_24h},
        "threat_level.level": "high"
    })
    
    high_7d = await events_collection.count_documents({
        "timestamp": {"$gte": cutoff_7d},
        "threat_level.level": "high"
    })
    
    high_30d = await events_collection.count_documents({
        "timestamp": {"$gte": cutoff_30d},
        "threat_level.level": "high"
    })
    
    # Calculate trend (percentage change from previous period)
    trend_7d = 0
    previous_7d = await events_collection.count_documents({
        "timestamp": {"$gte": cutoff_7d - timedelta(days=7), "$lt": cutoff_7d},
        "threat_level.level": "high"
    })
    
    if previous_7d > 0:
        trend_7d = ((high_7d - previous_7d) / previous_7d) * 100
    
    return {
        "high_priority_24h": high_24h,
        "high_priority_7d": high_7d,
        "high_priority_30d": high_30d,
        "trend_7d": round(trend_7d, 1)
    }
