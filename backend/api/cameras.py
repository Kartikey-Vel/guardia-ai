"""Cameras API — register, list, and stream camera snapshots."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Camera, get_db
from models.schemas import CameraCreate, CameraResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _orm_to_schema(c: Camera) -> CameraResponse:
    return CameraResponse(
        camera_id=c.camera_id,
        name=c.name,
        rtsp_url=c.rtsp_url,
        zone=c.zone,
        risk_level=c.risk_level,
        is_active=bool(c.is_active),
    )


@router.get("", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db)):
    """Return all registered cameras."""
    cameras = db.query(Camera).all()
    return [_orm_to_schema(c) for c in cameras]


@router.get("/live-frame")
def get_live_frame():
    """Return the latest frame cached by the backend video stream processor."""
    from ai.video_stream import video_stream

    snapshot = video_stream.get_latest_snapshot()
    return snapshot


@router.post("", response_model=CameraResponse, status_code=201)
def add_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    """Register a new camera source."""
    existing = db.query(Camera).filter(Camera.camera_id == payload.camera_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Camera already registered")
    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return _orm_to_schema(camera)


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return _orm_to_schema(camera)


@router.delete("/{camera_id}", status_code=204)
def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(camera)
    db.commit()
