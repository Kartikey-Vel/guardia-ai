from fastapi import APIRouter, Depends, HTTPException, Body, status, BackgroundTasks, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.api.tweety_auth import get_current_user, User
from src.db.porky_mongo import get_events_collection
from src.utils.tasmanian_logger import setup_logger
from src.api.bugs_notify import broadcast_security_alert
from bson import ObjectId

router = APIRouter()
logger = setup_logger(__name__)

class ThreatLevel(BaseModel):
    level: str = Field(..., description="Threat level (low, medium, high)")
    score: float = Field(..., description="Confidence score", ge=0.0, le=1.0)

class SecurityEvent(BaseModel):
    event_id: Optional[str] = None
    event_type: str = Field(..., description="Type of security event detected")
    description: str = Field(..., description="Description of the event")
    threat_level: ThreatLevel
    location: str = Field(..., description="Location where event was detected")
    timestamp: datetime = Field(default_factory=datetime.now)
    video_clip_url: Optional[str] = None
    audio_clip_url: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SecurityEvent)
async def create_event(
    event: SecurityEvent = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
):
    """Create a new security event."""
    events_collection = await get_events_collection()
    
    event_dict = event.dict(exclude_unset=True)
    event_dict["created_by"] = current_user.username
    
    # Insert into MongoDB and get the inserted ID
    result = await events_collection.insert_one(event_dict)
    event_dict["event_id"] = str(result.inserted_id)
    
    logger.info(f"New security event created: {event.event_type} with priority {event.threat_level.level}")
    
    # Broadcast the event via WebSocket in the background
    background_tasks.add_task(
        broadcast_security_alert, 
        {
            "event_type": event.event_type,
            "description": event.description,
            "threat_level": event.threat_level.dict(),
            "location": event.location,
            "event_id": str(result.inserted_id)
        }
    )
    
    return event_dict

@router.get("/", response_model=List[SecurityEvent])
async def get_events(
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[str] = None,
    threat_level: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user)
):
    """Get list of security events with optional filtering."""
    events_collection = await get_events_collection()
    
    # Build filter query
    query = {}
    if event_type:
        query["event_type"] = event_type
    if threat_level:
        query["threat_level.level"] = threat_level
    if acknowledged is not None:
        query["acknowledged"] = acknowledged
    
    # Determine sort order
    sort_direction = -1 if sort_order.lower() == "desc" else 1
    
    # Fetch events from MongoDB
    cursor = events_collection.find(query).skip(skip).limit(limit).sort(sort_by, sort_direction)
    events = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string for each event
    for event in events:
        event["event_id"] = str(event.pop("_id"))
    
    return events

@router.get("/{event_id}", response_model=SecurityEvent)
async def get_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific security event by ID."""
    events_collection = await get_events_collection()
    
    try:
        # Try to convert to ObjectId (MongoDB's ID type)
        object_id = ObjectId(event_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid event ID format")
    
    event = await events_collection.find_one({"_id": object_id})
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event["event_id"] = str(event.pop("_id"))
    return event

@router.put("/{event_id}/acknowledge", response_model=SecurityEvent)
async def acknowledge_event(
    event_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge a security event."""
    events_collection = await get_events_collection()
    
    try:
        # Try to convert to ObjectId
        object_id = ObjectId(event_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid event ID format")
    
    # Update the event in MongoDB
    now = datetime.now()
    result = await events_collection.update_one(
        {"_id": object_id},
        {"$set": {
            "acknowledged": True,
            "acknowledged_by": current_user.username,
            "acknowledged_at": now
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get the updated event
    event = await events_collection.find_one({"_id": object_id})
    event["event_id"] = str(event.pop("_id"))
    
    logger.info(f"Event {event_id} acknowledged by {current_user.username}")
    
    # Broadcast the acknowledgment via WebSocket in the background
    background_tasks.add_task(
        broadcast_security_alert, 
        {
            "type": "event_acknowledged",
            "event_id": event_id,
            "acknowledged_by": current_user.username,
            "acknowledged_at": now.isoformat()
        }
    )
    
    return event

@router.get("/stats/summary", response_model=dict)
async def get_event_stats(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user)
):
    """Get summary statistics of security events."""
    events_collection = await get_events_collection()
    
    # Calculate the date for filtering events
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Get counts by threat level
    threat_levels = ["low", "medium", "high"]
    threat_stats = {}
    
    for level in threat_levels:
        count = await events_collection.count_documents({
            "threat_level.level": level,
            "timestamp": {"$gte": cutoff_date}
        })
        threat_stats[level] = count
    
    # Get counts by event type
    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_date}}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    event_type_cursor = events_collection.aggregate(pipeline)
    event_type_stats = {doc["_id"]: doc["count"] async for doc in event_type_cursor}
    
    # Get acknowledgement stats
    acknowledged_count = await events_collection.count_documents({
        "acknowledged": True,
        "timestamp": {"$gte": cutoff_date}
    })
    
    unacknowledged_count = await events_collection.count_documents({
        "acknowledged": False,
        "timestamp": {"$gte": cutoff_date}
    })
    
    return {
        "period_days": days,
        "total_events": sum(threat_stats.values()),
        "by_threat_level": threat_stats,
        "by_event_type": event_type_stats,
        "acknowledged": acknowledged_count,
        "unacknowledged": unacknowledged_count
    }
