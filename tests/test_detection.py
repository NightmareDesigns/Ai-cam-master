"""Tests for AI object detection utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.detection.detector import Detection, detect, draw_detections, load_model
from src.detection.motion import MotionDetector


# ── Unit tests: Detection dataclass ──────────────────────────────────────────

class TestDetectionDataclass:
    def test_defaults(self):
        d = Detection(class_name="person", confidence=0.9)
        assert d.class_name == "person"
        assert d.confidence == 0.9
        assert d.bbox == (0, 0, 0, 0)

    def test_with_bbox(self):
        d = Detection(class_name="car", confidence=0.75, bbox=(10, 20, 100, 200))
        assert d.bbox == (10, 20, 100, 200)


# ── Unit tests: detect() with mocked YOLO ────────────────────────────────────

def _make_mock_result(cls_id: int, conf: float, bbox: tuple):
    """Build a minimal mock that mimics ultralytics Results."""
    box = MagicMock()
    box.cls = [MagicMock(item=lambda: cls_id)]
    box.conf = [MagicMock(item=lambda: conf)]
    box.xyxy = [
        [
            MagicMock(item=lambda: bbox[0]),
            MagicMock(item=lambda: bbox[1]),
            MagicMock(item=lambda: bbox[2]),
            MagicMock(item=lambda: bbox[3]),
        ]
    ]
    result = MagicMock()
    result.boxes = [box]
    return result


class TestDetect:
    def setup_method(self):
        """Reset global YOLO state before each test."""
        import src.detection.detector as dm
        dm._yolo_model = None
        dm._yolo_names = {}

    def test_returns_empty_when_no_model(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        results = detect(frame)
        assert results == []

    def test_with_mocked_model(self):
        import src.detection.detector as dm

        mock_model = MagicMock()
        mock_model.names = {0: "person", 2: "car"}
        mock_result = _make_mock_result(0, 0.85, (10, 20, 100, 200))
        mock_model.predict.return_value = [mock_result]

        dm._yolo_model = mock_model
        dm._yolo_names = mock_model.names

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        results = detect(frame, confidence_threshold=0.5)

        assert len(results) == 1
        assert results[0].class_name == "person"
        assert abs(results[0].confidence - 0.85) < 1e-6
        assert results[0].bbox == (10, 20, 100, 200)

    def test_tracked_classes_filter(self):
        import src.detection.detector as dm

        mock_model = MagicMock()
        mock_model.names = {0: "person", 2: "car"}

        car_result = _make_mock_result(2, 0.7, (5, 5, 50, 50))
        mock_model.predict.return_value = [car_result]
        dm._yolo_model = mock_model
        dm._yolo_names = mock_model.names

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Only track persons — should filter out the car
        results = detect(frame, tracked_classes=["person"])
        assert results == []

        # Track cars — should find it
        results = detect(frame, tracked_classes=["car"])
        assert len(results) == 1

    def test_load_model_skips_if_already_loaded(self):
        import src.detection.detector as dm

        sentinel = MagicMock()
        sentinel.names = {}
        dm._yolo_model = sentinel

        # load_model should not overwrite
        load_model("yolov8n.pt")
        assert dm._yolo_model is sentinel


# ── Unit tests: draw_detections ───────────────────────────────────────────────

class TestDrawDetections:
    def test_returns_copy(self):
        import cv2
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        dets = [Detection("person", 0.9, (5, 5, 50, 50))]
        out = draw_detections(frame, dets)
        assert out is not frame
        assert out.shape == frame.shape

    def test_no_detections(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        out = draw_detections(frame, [])
        np.testing.assert_array_equal(out, frame)


# ── Unit tests: MotionDetector ────────────────────────────────────────────────

class TestMotionDetector:
    def test_no_motion_on_static_frames(self):
        md = MotionDetector(min_area=500)
        # Feed many identical frames to build background model
        frame = np.full((480, 640, 3), 128, dtype=np.uint8)
        for _ in range(50):
            md.detect(frame)
        result = md.detect(frame)
        assert result is False

    def test_motion_on_changed_frame(self):
        md = MotionDetector(min_area=200)
        # Warm-up background with black frames
        black = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(30):
            md.detect(black)
        # Now introduce a large bright region
        bright = np.zeros((480, 640, 3), dtype=np.uint8)
        bright[100:300, 100:400] = 255
        result = md.detect(bright)
        assert result is True

    def test_reset_clears_background(self):
        md = MotionDetector()
        # Doesn't raise
        md.reset()
