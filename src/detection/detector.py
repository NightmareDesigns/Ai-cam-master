"""YOLOv8-based object detector.

The detector is a singleton loaded once at application startup to avoid
reloading the model weights on every frame.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy import so the app can start without ultralytics if detection is disabled.
_yolo_model = None
_yolo_names: dict[int, str] = {}


@dataclass
class Detection:
    """A single object detection result."""

    class_name: str
    confidence: float
    # Bounding box in (x1, y1, x2, y2) pixel coordinates
    bbox: tuple[int, int, int, int] = field(default_factory=lambda: (0, 0, 0, 0))


def load_model(model_path: str = "yolov8n.pt") -> None:
    """Load (or re-use) the YOLO model.  Thread-safe via GIL."""
    global _yolo_model, _yolo_names
    if _yolo_model is not None:
        return
    try:
        from ultralytics import YOLO  # type: ignore

        logger.info("Loading YOLO model: %s", model_path)
        _yolo_model = YOLO(model_path)
        _yolo_names = _yolo_model.names  # dict[int, str]
        logger.info("YOLO model loaded. Classes: %d", len(_yolo_names))
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to load YOLO model: %s", exc)
        _yolo_model = None


def detect(
    frame: np.ndarray,
    confidence_threshold: float = 0.45,
    tracked_classes: Optional[List[str]] = None,
) -> List[Detection]:
    """Run inference on a single BGR frame and return detections.

    Args:
        frame: OpenCV BGR image as a numpy array.
        confidence_threshold: Minimum confidence to keep a detection.
        tracked_classes: If provided, only return detections whose class name
            is in this list.  Pass ``None`` or an empty list to return all.

    Returns:
        List of :class:`Detection` objects.
    """
    if _yolo_model is None:
        return []

    results = _yolo_model.predict(frame, conf=confidence_threshold, verbose=False)
    detections: List[Detection] = []

    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            cls_name = _yolo_names.get(cls_id, str(cls_id)).lower()
            if tracked_classes and cls_name not in tracked_classes:
                continue
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = (int(v.item()) for v in box.xyxy[0])
            detections.append(
                Detection(
                    class_name=cls_name,
                    confidence=conf,
                    bbox=(x1, y1, x2, y2),
                )
            )

    return detections


def draw_detections(frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
    """Draw bounding boxes and labels on a copy of *frame*."""
    import cv2

    out = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        label = f"{det.class_name} {det.confidence:.0%}"
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            out,
            label,
            (x1, max(y1 - 6, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
    return out
