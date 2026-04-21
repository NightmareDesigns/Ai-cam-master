"""Tests for camera stream utilities and alert manager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from src.config import Settings


# ── CameraStream ──────────────────────────────────────────────────────────────

class TestCameraStream:
    def _make_stream(self, **kwargs):
        from src.camera.stream import CameraStream

        defaults = dict(
            camera_id=1,
            source="0",
            name="Test",
            detect_objects=True,
            detect_motion=True,
            record_on_event=False,
            on_event=None,
        )
        defaults.update(kwargs)
        return CameraStream(**defaults)

    def test_initial_state(self):
        stream = self._make_stream()
        assert stream.is_online is False
        assert stream.get_jpeg_frame() is None

    def test_stop_when_not_started_is_safe(self):
        stream = self._make_stream()
        stream.stop()  # should not raise

    def test_save_snapshot_returns_filename(self, tmp_path):
        stream = self._make_stream()
        # Patch settings to use tmp_path
        with patch("src.camera.stream.get_settings") as mock_settings:
            s = MagicMock()
            s.snapshots_dir = str(tmp_path)
            mock_settings.return_value = s
            # re-create stream so it picks up the patched settings
            stream2 = self._make_stream()
            stream2._settings = s
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            result = stream2._save_snapshot(frame, "person")
            assert result is not None
            assert result.endswith(".jpg")
            assert (tmp_path / result).exists()

    def test_save_snapshot_returns_none_on_error(self):
        stream = self._make_stream()
        stream._settings = MagicMock()
        stream._settings.snapshots_dir = "/nonexistent_dir_xyz/sub"
        # Make mkdir fail by patching Path.mkdir
        with patch("src.camera.stream.Path.mkdir", side_effect=PermissionError("denied")):
            result = stream._save_snapshot(np.zeros((10, 10, 3), dtype=np.uint8), "test")
        assert result is None

    def test_snapshot_capture_reads_frame(self, monkeypatch):
        from src.camera.stream import SnapshotCapture

        frame = np.zeros((4, 4, 3), dtype=np.uint8)
        ok, buf = cv2.imencode(".jpg", frame)
        assert ok

        class DummyResponse:
            def __init__(self, content):
                self.content = content

            def raise_for_status(self):
                return None

        monkeypatch.setattr(
            "src.camera.stream.requests.get", lambda url, timeout=3.0: DummyResponse(buf.tobytes())
        )

        cap = SnapshotCapture("http://example/snapshot.jpg")
        assert cap.isOpened()
        ok, decoded = cap.read()
        assert ok is True
        assert decoded is not None


# ── AlertManager ─────────────────────────────────────────────────────────────

class TestAlertManager:
    def _make_manager(self, db=None):
        from src.alerts.manager import AlertManager

        if db is None:
            db = MagicMock()
        return AlertManager(db)

    def _make_rule(self, trigger_class="*", camera_id=None, notify_via="console", enabled=True):
        from src.models.alert_rule import AlertRule

        rule = MagicMock(spec=AlertRule)
        rule.trigger_class = trigger_class
        rule.camera_id = camera_id
        rule.notify_via = notify_via
        rule.enabled = enabled
        rule.webhook_url = None
        rule.name = "Test Rule"
        rule.id = 1
        return rule

    def _make_event(self, event_type="object_detected", object_class="person", confidence=0.9, camera_id=1):
        from src.models.event import Event

        ev = MagicMock(spec=Event)
        ev.event_type = event_type
        ev.object_class = object_class
        ev.confidence = confidence
        ev.camera_id = camera_id
        ev.snapshot_path = None
        ev.occurred_at = "2024-01-01T00:00:00"
        return ev

    def test_matches_wildcard(self):
        mgr = self._make_manager()
        rule = self._make_rule(trigger_class="*")
        ev = self._make_event(object_class="dog")
        assert mgr._matches(rule, ev) is True

    def test_matches_specific_class(self):
        mgr = self._make_manager()
        rule = self._make_rule(trigger_class="person")
        assert mgr._matches(rule, self._make_event(object_class="person")) is True
        assert mgr._matches(rule, self._make_event(object_class="car")) is False

    def test_matches_event_type(self):
        mgr = self._make_manager()
        rule = self._make_rule(trigger_class="motion")
        ev = self._make_event(event_type="motion", object_class=None)
        assert mgr._matches(rule, ev) is True

    def test_notify_console_logs(self, caplog):
        import logging
        mgr = self._make_manager()
        rule = self._make_rule(notify_via="console")
        ev = self._make_event()
        with caplog.at_level(logging.WARNING, logger="src.alerts.manager"):
            mgr._notify_console(rule, ev)
        assert "ALERT" in caplog.text

    def test_notify_webhook_skips_without_url(self):
        mgr = self._make_manager()
        rule = self._make_rule(notify_via="webhook")
        rule.webhook_url = None
        ev = self._make_event()
        # Should not raise
        mgr._notify_webhook(rule, ev)

    def test_notify_webhook_posts(self):
        import httpx

        mgr = self._make_manager()
        rule = self._make_rule(notify_via="webhook")
        rule.webhook_url = "https://example.com/hook"
        ev = self._make_event()

        with patch("src.alerts.manager.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            mgr._notify_webhook(rule, ev)
            mock_client.post.assert_called_once()


# ── CameraManager ─────────────────────────────────────────────────────────────

class TestCameraManager:
    def test_is_online_returns_false_for_unknown(self):
        from src.camera.manager import CameraManager

        mgr = CameraManager()
        assert mgr.is_online(999) is False

    def test_get_jpeg_frame_returns_none_for_unknown(self):
        from src.camera.manager import CameraManager

        mgr = CameraManager()
        assert mgr.get_jpeg_frame(999) is None

    def test_online_ids_empty(self):
        from src.camera.manager import CameraManager

        mgr = CameraManager()
        assert mgr.online_ids() == []

    def test_remove_nonexistent_camera_is_safe(self):
        from src.camera.manager import CameraManager

        mgr = CameraManager()
        mgr.remove_camera(999)  # should not raise
