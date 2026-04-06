"""Event Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    event_type: str
    object_class: Optional[str] = None
    confidence: Optional[float] = None
    snapshot_path: Optional[str] = None
    clip_path: Optional[str] = None
    occurred_at: datetime
