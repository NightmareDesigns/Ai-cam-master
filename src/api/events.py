"""Events API routes."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.event import Event
from src.schemas.event import EventRead

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/", response_model=List[EventRead])
def list_events(
    camera_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    object_class: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Event)
    if camera_id is not None:
        q = q.filter(Event.camera_id == camera_id)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if object_class:
        q = q.filter(Event.object_class == object_class)
    if since:
        q = q.filter(Event.occurred_at >= since)
    return q.order_by(Event.occurred_at.desc()).offset(offset).limit(limit).all()
