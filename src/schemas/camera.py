"""Camera Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CameraBase(BaseModel):
    name: str
    source: str
    enabled: bool = True
    detect_objects: bool = True
    detect_motion: bool = True
    record_on_event: bool = True
    location_name: Optional[str] = None


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    enabled: Optional[bool] = None
    detect_objects: Optional[bool] = None
    detect_motion: Optional[bool] = None
    record_on_event: Optional[bool] = None
    location_name: Optional[str] = None


class CameraRead(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    # Runtime status injected by the camera manager
    is_online: bool = False
