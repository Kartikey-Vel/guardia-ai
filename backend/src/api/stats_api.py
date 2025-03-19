from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from src.api.tweety_auth import get_current_user, User
from src.db.porky_mongo import get_events_collection, get_database
from src.utils.tasmanian_logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

class TimePeriodStats(BaseModel):
    period: str
    count: int
    acknowledged: int
    unacknowledged: int

class DashboardStats(BaseModel):
    total_events: int
    events_by_type: Dict[str, int]
    events_by_threat: Dict[str, int]
    events_over_time: List[TimePeriodStats]
    unacknowledged_high_priority: int

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics for security events."""
    events_collection = await get_events_collection()
    
    # Calculate the date for filtering events
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Get total event count
    total_events = await events_collection.count_documents({
        "timestamp": {"$gte": cutoff_date}
    })
    
    # Get events by type
    type_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_date}}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    type_cursor = events_collection.aggregate(type_pipeline)
    events_by_type = {doc["_id"]: doc["count"] async for doc in type_cursor}
    
    # Get events by threat level
    threat_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_date}}},
        {"$group": {"_id": "$threat_level.level", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    
    threat_cursor = events_collection.aggregate(threat_pipeline)
    events_by_threat = {doc["_id"]: doc["count"] async for doc in threat_cursor}
    
    # Get events over time (e.g., per day for the last week)
    time_stats = []
    
    # Calculate daily stats
    for i in range(days):
        day_start = datetime.now() - timedelta(days=i+1)
        day_end = datetime.now() - timedelta(days=i)
        
        # Count total events for the day
        day_count = await events_collection.count_documents({
            "timestamp": {"$gte": day_start, "$lt": day_end}
        })
        
        # Count acknowledged events for the day
        acknowledged_count = await events_collection.count_documents({
            "timestamp": {"$gte": day_start, "$lt": day_end},
            "acknowledged": True
        })
        
        # Add stats for the day
        time_stats.append(TimePeriodStats(
            period=day_start.strftime("%Y-%m-%d"),
            count=day_count,
            acknowledged=acknowledged_count,
            unacknowledged=day_count - acknowledged_count
        ))
    
    # Get count of unacknowledged high priority events
    unacknowledged_high = await events_collection.count_documents({
        "timestamp": {"$gte": cutoff_date},
        "threat_level.level": "high",
        "acknowledged": False
    })
    
    return DashboardStats(
        total_events=total_events,
        events_by_type=events_by_type,
        events_by_threat=events_by_threat,
        events_over_time=time_stats,
        unacknowledged_high_priority=unacknowledged_high
    )

@router.get("/sources")
async def get_event_sources(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user)
):
    """Get statistics about event sources."""
    events_collection = await get_events_collection()
    
    # Calculate the date for filtering events
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Get events by location
    location_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_date}}},
        {"$group": {"_id": "$location", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    location_cursor = events_collection.aggregate(location_pipeline)
    locations = [{"location": doc["_id"], "count": doc["count"]} async for doc in location_cursor]
    
    return {
        "period_days": days,
        "top_locations": locations
    }

@router.get("/trends")
async def get_event_trends(
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_user)
):
    """Get trend information for security events over time."""
    events_collection = await get_events_collection()
    
    # Calculate the date for filtering events
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # For weekly trends, group by week
    weekly_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_date}}},
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$timestamp"}, 
                    "week": {"$week": "$timestamp"}
                },
                "count": {"$sum": 1},
                "high_priority": {
                    "$sum": {"$cond": [{"$eq": ["$threat_level.level", "high"]}, 1, 0]}
                }
            }
        },
        {"$sort": {"_id.year": 1, "_id.week": 1}}
    ]
    
    weekly_cursor = events_collection.aggregate(weekly_pipeline)
    weekly_trends = []
    
    async for doc in weekly_cursor:
        # Calculate approximate date for the week (not exact but sufficient for display)
        year = doc["_id"]["year"]
        week = doc["_id"]["week"]
        # Approximate date for the start of the week
        approx_date = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w").strftime("%Y-%m-%d")
        
        weekly_trends.append({
            "period": approx_date,
            "total": doc["count"],
            "high_priority": doc["high_priority"]
        })
    
    # Calculate percentage change in events compared to previous period
    change_percentage = 0
    if len(weekly_trends) >= 2:
        current_period = sum(week["total"] for week in weekly_trends[-4:])  # Last 4 weeks
        previous_period = sum(week["total"] for week in weekly_trends[-8:-4])  # Previous 4 weeks
        
        if previous_period > 0:
            change_percentage = ((current_period - previous_period) / previous_period) * 100
    
    return {
        "period_days": days,
        "weekly_trends": weekly_trends,
        "change_percentage": round(change_percentage, 2)
    }
