"""Event ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "object_detected" | "motion" | "alert"
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # COCO class name (e.g. "person") or None for pure motion
    object_class: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Path relative to snapshots_dir
    snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Path relative to recordings_dir
    clip_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    camera: Mapped["Camera"] = relationship("Camera", back_populates="events")  # noqa: F821
