"""Geeni vendor endpoints (cameras + lights)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from src.integrations.geeni import build_geeni_stream, control_geeni_light
from src.schemas.discovery import DiscoveredCamera
from src.schemas.vendors import GeeniCameraRequest, GeeniLightRequest

router = APIRouter(prefix="/api/geeni", tags=["geeni"])


@router.post("/cameras/login", response_model=List[DiscoveredCamera])
async def geeni_camera_login(payload: GeeniCameraRequest):
    """Build a Geeni RTSP URL or snapshot fallback."""
    return await build_geeni_stream(payload)


@router.post("/lights/toggle")
async def geeni_light_toggle(payload: GeeniLightRequest):
    """Toggle or set brightness for a Geeni/Tuya light over LAN."""
    try:
        status_payload = await control_geeni_light(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Geeni light control failed: {exc}",
        ) from exc
    return {"ok": True, "status": status_payload}
