"""Camera ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # RTSP URL, USB index (e.g. "0"), or HTTP MJPEG URL
    source: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    detect_objects: Mapped[bool] = mapped_column(Boolean, default=True)
    detect_motion: Mapped[bool] = mapped_column(Boolean, default=True)
    record_on_event: Mapped[bool] = mapped_column(Boolean, default=True)
    # Optional: lat/lon for map view
    location_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    events: Mapped[list] = relationship(
        "Event", back_populates="camera", cascade="all, delete-orphan"
    )
    alert_rules: Mapped[list] = relationship(
        "AlertRule", back_populates="camera", cascade="all, delete-orphan"
    )
