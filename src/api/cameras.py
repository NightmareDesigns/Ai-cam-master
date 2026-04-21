"""Camera CRUD API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from blinkpy.auth import BlinkTwoFARequiredError, LoginError as BlinkLoginError
from src.camera import discovery
from src.integrations.blink import fetch_blink_liveviews
from src.integrations.zmodo import build_zmodo_stream
from src.integrations.eeseecam import build_eeseecam_stream
from src.camera.manager import camera_manager
from src.database import get_db
from src.models.camera import Camera
from src.schemas.camera import CameraCreate, CameraRead, CameraUpdate
from src.schemas.discovery import DiscoveredCamera, DiscoveryRequest
from src.schemas.vendors import BlinkLoginRequest, ZmodoLoginRequest, EseeCamLoginRequest

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


def _get_or_404(camera_id: int, db: Session) -> Camera:
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if cam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return cam


@router.get("/", response_model=List[CameraRead])
def list_cameras(db: Session = Depends(get_db)):
    cameras = db.query(Camera).order_by(Camera.id).all()
    result = []
    for cam in cameras:
        data = CameraRead.model_validate(cam)
        data.is_online = camera_manager.is_online(cam.id)
        result.append(data)
    return result


@router.post("/", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    cam = Camera(**payload.model_dump())
    db.add(cam)
    db.commit()
    db.refresh(cam)
    camera_manager.add_camera(cam, db)
    data = CameraRead.model_validate(cam)
    data.is_online = camera_manager.is_online(cam.id)
    return data


@router.get("/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = _get_or_404(camera_id, db)
    data = CameraRead.model_validate(cam)
    data.is_online = camera_manager.is_online(cam.id)
    return data


@router.patch("/{camera_id}", response_model=CameraRead)
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)):
    cam = _get_or_404(camera_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(cam, field, value)
    db.commit()
    db.refresh(cam)
    camera_manager.update_camera(cam, db)
    data = CameraRead.model_validate(cam)
    data.is_online = camera_manager.is_online(cam.id)
    return data


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = _get_or_404(camera_id, db)
    camera_manager.remove_camera(cam.id)
    db.delete(cam)
    db.commit()


@router.post("/discover", response_model=List[DiscoveredCamera])
async def discover_cameras(payload: DiscoveryRequest):
    """Scan local interfaces and USB devices for cameras."""
    results = await discovery.discover_cameras(
        subnets=payload.subnets,
        include_usb=payload.include_usb,
        max_hosts=payload.max_hosts,
        timeout_seconds=payload.timeout_seconds,
        max_results=payload.max_results,
    )
    return results


@router.post("/zmodo/login", response_model=List[DiscoveredCamera])
async def zmodo_login(payload: ZmodoLoginRequest):
    """Build a Zmodo RTSP URL and optionally validate connectivity."""
    return await build_zmodo_stream(payload)


@router.post("/blink/login", response_model=List[DiscoveredCamera])
async def blink_login(payload: BlinkLoginRequest):
    """Authenticate with Blink and return liveview RTSP URLs."""
    try:
        return await fetch_blink_liveviews(payload)
    except BlinkTwoFARequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Two-factor authentication or recovery code required for Blink login.",
        )
    except BlinkLoginError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )
    except Exception as exc:  # pragma: no cover - unexpected failures
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Blink login failed: {exc}",
        ) from exc


@router.post("/eeseecam/login", response_model=List[DiscoveredCamera])
async def eeseecam_login(payload: EseeCamLoginRequest):
    """Build an EseeCam RTSP URL with snapshot fallback."""
    return await build_eeseecam_stream(payload)
