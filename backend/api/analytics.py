"""Analytics API — summary statistics and time-series trends."""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Camera, Event, get_db
from models.schemas import AnalyticsSummary, TrendPoint

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(db: Session = Depends(get_db)):
    """Return aggregate statistics across all events."""
    total = db.query(func.count(Event.id)).scalar() or 0
    reviewed = (
        db.query(func.count(Event.id))
        .filter(Event.is_reviewed == True)  # noqa: E712
        .scalar() or 0
    )
    avg_sev = db.query(func.avg(Event.severity)).scalar() or 0.0

    # Most common classification
    top_row = (
        db.query(Event.classification, func.count(Event.id).label("cnt"))
        .group_by(Event.classification)
        .order_by(func.count(Event.id).desc())
        .first()
    )
    top_cls = top_row[0] if top_row else None

    active_cams = (
        db.query(func.count(Camera.id))
        .filter(Camera.is_active == True)  # noqa: E712
        .scalar() or 0
    )

    return AnalyticsSummary(
        total_events=total,
        reviewed_events=reviewed,
        unreviewed_events=total - reviewed,
        avg_severity=round(float(avg_sev), 2),
        top_classification=top_cls,
        cameras_active=active_cams,
    )


@router.get("/trends", response_model=List[TrendPoint])
def get_trends(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """
    Return hourly event counts and average severity for the last N hours.
    Useful for dashboard sparklines and bar charts.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
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

    return [
        TrendPoint(
            hour=hour_key,
            count=len(severities),
            avg_severity=round(sum(severities) / len(severities), 2),
        )
        for hour_key, severities in sorted(buckets.items())
    ]
