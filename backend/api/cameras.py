"""Cameras API — register, list, and snapshot camera streams."""

import base64
import logging
from typing import List

import cv2
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


@router.get("/{camera_id}/snapshot")
def get_snapshot(camera_id: str, db: Session = Depends(get_db)):
    """
    Capture a single frame from the camera's video source and return it
    as a base64-encoded JPEG data URI.

    For webcam sources (no RTSP URL) index 0 is used automatically.
    """
    camera = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    rtsp_url = camera.rtsp_url if camera else None

    source = rtsp_url if rtsp_url else 0
    try:
        cap = cv2.VideoCapture(source)
        ret, frame = cap.read()
        cap.release()
    except Exception as exc:
        logger.error("Snapshot capture failed for cam=%s: %s", camera_id, exc)
        return {"frame": None, "error": str(exc), "camera_id": camera_id}

    if not ret or frame is None:
        return {"frame": None, "error": "Camera read failed", "camera_id": camera_id}

    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    b64 = base64.b64encode(buffer).decode()
    return {
        "frame": f"data:image/jpeg;base64,{b64}",
        "camera_id": camera_id,
    }
