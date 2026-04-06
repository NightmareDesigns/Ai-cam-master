"""Individual camera stream worker.

Each ``CameraStream`` runs a background thread that:
  1. Opens the video source (RTSP / USB / HTTP).
  2. Decodes frames.
  3. Runs motion detection and/or object detection.
  4. Persists events to the database.
  5. Saves snapshot JPEG files when events are triggered.
  6. Maintains a ring-buffer of recent frames for MJPEG streaming.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.config import get_settings
from src.detection import detector as det_module
from src.detection.motion import MotionDetector

logger = logging.getLogger(__name__)

# Maximum number of JPEG frames buffered per camera (for live streaming)
_FRAME_BUFFER_SIZE = 3


class CameraStream:
    """Manages capture + AI analysis for a single camera source."""

    def __init__(
        self,
        camera_id: int,
        source: str,
        name: str,
        detect_objects: bool = True,
        detect_motion: bool = True,
        record_on_event: bool = True,
        on_event=None,  # Callable[[int, str, str | None, float | None, str | None], None]
    ) -> None:
        self.camera_id = camera_id
        self.source = source
        self.name = name
        self.detect_objects = detect_objects
        self.detect_motion = detect_motion
        self.record_on_event = record_on_event
        self._on_event = on_event  # callback(camera_id, event_type, class_name, conf, snap)

        self._settings = get_settings()
        self._motion_detector = MotionDetector()
        self._frame_buffer: deque[bytes] = deque(maxlen=_FRAME_BUFFER_SIZE)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_online = False
        self._last_motion_alert = 0.0
        self._last_object_alert: dict[str, float] = {}

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def is_online(self) -> bool:
        return self._is_online

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name=f"cam-{self.camera_id}", daemon=True
        )
        self._thread.start()
        logger.info("Camera %d (%s) stream started.", self.camera_id, self.name)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._is_online = False
        logger.info("Camera %d (%s) stream stopped.", self.camera_id, self.name)

    def get_jpeg_frame(self) -> Optional[bytes]:
        """Return the latest JPEG frame, or ``None`` if not available."""
        with self._lock:
            if self._frame_buffer:
                return self._frame_buffer[-1]
        return None

    # ── internal capture loop ─────────────────────────────────────────────────

    def _run(self) -> None:
        reconnect_delay = 2
        while not self._stop_event.is_set():
            cap = self._open_capture()
            if cap is None:
                self._is_online = False
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30)
                continue

            reconnect_delay = 2
            self._is_online = True
            self._motion_detector.reset()
            self._process_stream(cap)
            cap.release()
            if not self._stop_event.is_set():
                logger.warning("Camera %d lost connection, reconnecting…", self.camera_id)
                self._is_online = False
                time.sleep(2)

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        src = self.source
        # Allow integer USB camera index as string, e.g. "0"
        if src.isdigit():
            src = int(src)
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            logger.warning("Cannot open camera %d source: %s", self.camera_id, self.source)
            return None
        # Prefer low-latency RTSP buffer
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _process_stream(self, cap: cv2.VideoCapture) -> None:
        settings = self._settings
        target_interval = 1.0 / max(settings.stream_fps, 1)
        cooldown = settings.alert_cooldown_seconds
        tracked = settings.tracked_classes_list

        while not self._stop_event.is_set():
            t_start = time.monotonic()
            ok, frame = cap.read()
            if not ok or frame is None:
                break

            annotated = frame.copy()

            # ── Object detection ──────────────────────────────────────────
            if self.detect_objects:
                detections = det_module.detect(
                    frame,
                    confidence_threshold=settings.detection_confidence,
                    tracked_classes=tracked or None,
                )
                if detections:
                    annotated = det_module.draw_detections(annotated, detections)
                    for d in detections:
                        last = self._last_object_alert.get(d.class_name, 0.0)
                        if time.time() - last >= cooldown:
                            self._last_object_alert[d.class_name] = time.time()
                            snap = self._save_snapshot(annotated, d.class_name)
                            if self._on_event:
                                self._on_event(
                                    self.camera_id,
                                    "object_detected",
                                    d.class_name,
                                    d.confidence,
                                    snap,
                                )

            # ── Motion detection ──────────────────────────────────────────
            if self.detect_motion:
                if self._motion_detector.detect(frame):
                    if time.time() - self._last_motion_alert >= cooldown:
                        self._last_motion_alert = time.time()
                        snap = self._save_snapshot(annotated, "motion")
                        if self._on_event:
                            self._on_event(
                                self.camera_id, "motion", None, None, snap
                            )

            # ── Encode frame to JPEG and buffer ────────────────────────────
            quality = settings.stream_jpeg_quality
            ok2, encoded = cv2.imencode(
                ".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            if ok2:
                with self._lock:
                    self._frame_buffer.append(encoded.tobytes())

            # Throttle to target FPS
            elapsed = time.monotonic() - t_start
            sleep_for = target_interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _save_snapshot(self, frame: np.ndarray, label: str) -> Optional[str]:
        """Save an annotated frame as JPEG and return the relative path."""
        try:
            snap_dir = Path(self._settings.snapshots_dir)
            snap_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            filename = f"cam{self.camera_id}_{label}_{ts}.jpg"
            full_path = snap_dir / filename
            cv2.imwrite(str(full_path), frame)
            return filename
        except Exception as exc:
            logger.error("Snapshot save failed: %s", exc)
            return None
