"""Multi-camera manager.

Maintains a registry of :class:`~src.camera.stream.CameraStream` instances,
persists events to the database, and evaluates alert rules.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.camera.stream import CameraStream
from src.config import get_settings
from src.models.camera import Camera
from src.models.event import Event

logger = logging.getLogger(__name__)


class CameraManager:
    """Singleton-style manager for all active camera streams."""

    def __init__(self) -> None:
        self._streams: Dict[int, CameraStream] = {}
        self._alert_manager = None  # injected lazily to avoid circular imports

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def startup(self, db: Session) -> None:
        """Load all enabled cameras from the DB and start their streams."""
        from src.alerts.manager import AlertManager

        self._alert_manager = AlertManager(db)
        cameras = db.query(Camera).filter(Camera.enabled == True).all()  # noqa: E712
        for cam in cameras:
            self._start_camera(cam, db)
        logger.info("CameraManager started %d camera(s).", len(cameras))

    def shutdown(self) -> None:
        """Stop all streams gracefully."""
        for stream in list(self._streams.values()):
            stream.stop()
        self._streams.clear()
        logger.info("CameraManager shut down.")

    # ── camera CRUD ───────────────────────────────────────────────────────────

    def add_camera(self, cam: Camera, db: Session) -> None:
        """Start streaming a newly-added camera."""
        if cam.enabled:
            self._start_camera(cam, db)

    def remove_camera(self, camera_id: int) -> None:
        """Stop and remove a camera stream."""
        stream = self._streams.pop(camera_id, None)
        if stream:
            stream.stop()

    def update_camera(self, cam: Camera, db: Session) -> None:
        """Restart a camera stream after settings change."""
        self.remove_camera(cam.id)
        if cam.enabled:
            self._start_camera(cam, db)

    # ── queries ───────────────────────────────────────────────────────────────

    def is_online(self, camera_id: int) -> bool:
        stream = self._streams.get(camera_id)
        return stream.is_online if stream else False

    def get_jpeg_frame(self, camera_id: int) -> Optional[bytes]:
        stream = self._streams.get(camera_id)
        return stream.get_jpeg_frame() if stream else None

    def online_ids(self) -> List[int]:
        return [cid for cid, s in self._streams.items() if s.is_online]

    # ── internals ─────────────────────────────────────────────────────────────

    def _start_camera(self, cam: Camera, db: Session) -> None:
        stream = CameraStream(
            camera_id=cam.id,
            source=cam.source,
            name=cam.name,
            detect_objects=cam.detect_objects,
            detect_motion=cam.detect_motion,
            record_on_event=cam.record_on_event,
            on_event=self._make_event_handler(db),
        )
        self._streams[cam.id] = stream
        stream.start()

    def _make_event_handler(self, db: Session):
        """Return a callback that persists events and fires alerts."""

        def handler(
            camera_id: int,
            event_type: str,
            object_class: Optional[str],
            confidence: Optional[float],
            snapshot_path: Optional[str],
        ) -> None:
            try:
                event = Event(
                    camera_id=camera_id,
                    event_type=event_type,
                    object_class=object_class,
                    confidence=confidence,
                    snapshot_path=snapshot_path,
                )
                db.add(event)
                db.commit()
                db.refresh(event)
                logger.debug(
                    "Event saved: cam=%d type=%s class=%s conf=%s",
                    camera_id,
                    event_type,
                    object_class,
                    confidence,
                )
                if self._alert_manager:
                    self._alert_manager.evaluate(event)
            except Exception as exc:
                logger.error("Event handler error: %s", exc)
                db.rollback()

        return handler


# Module-level singleton
camera_manager = CameraManager()
