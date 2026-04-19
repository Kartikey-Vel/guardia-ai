"""Events API — CRUD endpoints for security event records."""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import Event, get_db
from models.schemas import EventCreate, EventResponse, EventReviewUpdate

router = APIRouter()


def _orm_to_schema(e: Event) -> EventResponse:
    return EventResponse(
        event_id=e.event_id,
        timestamp=e.timestamp,
        camera_id=e.camera_id,
        classification=e.classification,
        severity=e.severity,
        confidence=e.confidence,
        description=e.description,
        attribution=e.attribution,
        ai_model=e.ai_model,
        is_reviewed=bool(e.is_reviewed),
        frame_path=e.frame_path,
        motion_score=e.motion_score,
    )


@router.get("", response_model=List[EventResponse])
def list_events(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    camera_id: Optional[str] = None,
    reviewed: Optional[bool] = None,
    min_severity: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Return paginated list of security events with optional filters."""
    q = db.query(Event)
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    if reviewed is not None:
        q = q.filter(Event.is_reviewed == reviewed)
    if min_severity is not None:
        q = q.filter(Event.severity >= min_severity)
    events = q.order_by(Event.timestamp.desc()).offset(skip).limit(limit).all()
    return [_orm_to_schema(e) for e in events]


@router.get("/recent", response_model=List[EventResponse])
def recent_events(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Return the N most recent events."""
    events = (
        db.query(Event)
        .order_by(Event.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [_orm_to_schema(e) for e in events]


@router.post("", response_model=EventResponse, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    """Persist a new event (called by the AI pipeline)."""
    event = Event(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        camera_id=payload.camera_id,
        classification=payload.classification,
        severity=payload.severity,
        confidence=payload.confidence,
        description=payload.description,
        attribution=payload.attribution,
        ai_model=payload.ai_model,
        frame_path=payload.frame_path,
        motion_score=payload.motion_score,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _orm_to_schema(event)


@router.patch("/{event_id}/review", response_model=EventResponse)
def mark_reviewed(
    event_id: str,
    payload: EventReviewUpdate,
    db: Session = Depends(get_db),
):
    """Mark an event as reviewed / unreviewed."""
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.is_reviewed = payload.is_reviewed
    db.commit()
    db.refresh(event)
    return _orm_to_schema(event)


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: str, db: Session = Depends(get_db)):
    """Hard-delete an event record."""
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
