"""AlertRule Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AlertRuleBase(BaseModel):
    name: str
    trigger_class: str = "*"
    notify_via: str = "console"
    webhook_url: Optional[str] = None
    enabled: bool = True
    camera_id: Optional[int] = None


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger_class: Optional[str] = None
    notify_via: Optional[str] = None
    webhook_url: Optional[str] = None
    enabled: Optional[bool] = None
    camera_id: Optional[int] = None


class AlertRuleRead(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
