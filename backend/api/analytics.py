"""Analytics API — summary statistics and time-series trends.

TASK-042: Optimised queries + enriched response fields for dashboard.
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Camera, Event, get_db

router = APIRouter()


@router.get(
    "/summary",
    summary="Analytics summary",
    description="Aggregate statistics: total events, severity breakdown, top threats, and today's alert count.",
)
def get_summary(db: Session = Depends(get_db)):
    """Return aggregate statistics across all events."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total = db.query(func.count(Event.id)).scalar() or 0
    reviewed = (
        db.query(func.count(Event.id))
        .filter(Event.is_reviewed == True)  # noqa: E712
        .scalar() or 0
    )
    avg_sev = db.query(func.avg(Event.severity)).scalar() or 0.0

    total_alerts_today = (
        db.query(func.count(Event.id))
        .filter(Event.timestamp >= today_start)
        .scalar() or 0
    )
    high_severity_count = (
        db.query(func.count(Event.id))
        .filter(Event.severity >= 7)
        .scalar() or 0
    )

    # Most common classification
    top_row = (
        db.query(Event.classification, func.count(Event.id).label("cnt"))
        .group_by(Event.classification)
        .order_by(func.count(Event.id).desc())
        .first()
    )
    top_cls = top_row[0] if top_row else None

    # Classification breakdown
    cls_rows = (
        db.query(Event.classification, func.count(Event.id).label("cnt"))
        .group_by(Event.classification)
        .order_by(func.count(Event.id).desc())
        .all()
    )
    classification_breakdown = {row[0]: row[1] for row in cls_rows}

    active_cams = (
        db.query(func.count(Camera.id))
        .filter(Camera.is_active == True)  # noqa: E712
        .scalar() or 0
    )

    # Build hourly buckets for today's sparkline
    today_events = (
        db.query(Event)
        .filter(Event.timestamp >= today_start)
        .all()
    )
    alerts_by_hour = {}
    for e in today_events:
        h = e.timestamp.strftime("%H:00")
        alerts_by_hour[h] = alerts_by_hour.get(h, 0) + 1

    return {
        # Core fields (original schema)
        "total_events": total,
        "reviewed_events": reviewed,
        "unreviewed_events": total - reviewed,
        "avg_severity": round(float(avg_sev), 2),
        "top_classification": top_cls,
        "cameras_active": active_cams,
        # Extended fields for dashboard (TASK-042)
        "total_alerts_today": total_alerts_today,
        "high_severity_count": high_severity_count,
        "classification_breakdown": classification_breakdown,
        "alerts_by_hour": alerts_by_hour,
    }


@router.get(
    "/trends",
    summary="Hourly event trends",
    description=(
        "Hourly event counts and average severity. "
        "Accepts `period` (24h/7d/30d) or `hours` (integer)."
    ),
)
def get_trends(
    period: str = Query(default="24h", description="Period: 24h, 7d, 30d"),
    hours: int = Query(default=0, ge=0, description="Override: number of hours (0 = use period)"),
    db: Session = Depends(get_db),
):
    """Return hourly event counts for sparklines and bar charts."""
    # Parse period string OR use hours override
    if hours > 0:
        num_hours = hours
    else:
        period_map = {"24h": 24, "7d": 168, "30d": 720}
        num_hours = period_map.get(period, 24)

    since = datetime.utcnow() - timedelta(hours=num_hours)
    events = (
        db.query(Event)
        .filter(Event.timestamp >= since)
        .order_by(Event.timestamp.asc())
        .all()
    )

    # Group by UTC hour bucket
    buckets: dict[str, list[int]] = {}
    for event in events:
        hour_key = event.timestamp.strftime("%Y-%m-%dT%H:00")
        if hour_key not in buckets:
            buckets[hour_key] = []
        buckets[hour_key].append(event.severity)

    data_points = [
        {
            "hour": hour_key,
            "count": len(severities),
            "avg_severity": round(sum(severities) / len(severities), 2),
        }
        for hour_key, severities in sorted(buckets.items())
    ]

    return {
        "period": period if hours == 0 else f"{hours}h",
        "num_hours": num_hours,
        "data_points": data_points,
    }


@router.get(
    "/cameras",
    summary="Per-camera statistics",
    description="Event count and average severity grouped by camera.",
)
def camera_stats(db: Session = Depends(get_db)):
    """Return per-camera event statistics."""
    rows = (
        db.query(
            Event.camera_id,
            func.count(Event.id).label("event_count"),
            func.avg(Event.severity).label("avg_severity"),
            func.max(Event.severity).label("max_severity"),
        )
        .group_by(Event.camera_id)
        .order_by(func.count(Event.id).desc())
        .all()
    )
    return [
        {
            "camera_id": row[0],
            "event_count": row[1],
            "avg_severity": round(float(row[2]), 2) if row[2] else 0.0,
            "max_severity": row[3] or 0,
        }
        for row in rows
    ]
