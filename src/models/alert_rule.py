"""AlertRule ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Object class to trigger on, e.g. "person". "*" = any detection.
    trigger_class: Mapped[str] = mapped_column(String(64), nullable=False, default="*")
    # Notification methods: comma-separated "email", "webhook", "console"
    notify_via: Mapped[str] = mapped_column(String(256), nullable=False, default="console")
    # Optional webhook URL
    webhook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # None means rule applies to all cameras
    camera: Mapped["Camera | None"] = relationship("Camera", back_populates="alert_rules")  # noqa: F821
