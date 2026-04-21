"""Tests for REST API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from blinkpy.auth import BlinkTwoFARequiredError


# ── Camera endpoints ─────────────────────────────────────────────────────────

class TestCamerasAPI:
    def test_list_cameras_empty(self, client: TestClient):
        r = client.get("/api/cameras/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_camera(self, client: TestClient):
        payload = {
            "name": "Test Cam",
            "source": "0",
            "detect_objects": True,
            "detect_motion": True,
        }
        r = client.post("/api/cameras/", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Test Cam"
        assert data["source"] == "0"
        assert "id" in data

    def test_get_camera(self, client: TestClient):
        # Create first
        r = client.post(
            "/api/cameras/",
            json={"name": "Cam A", "source": "rtsp://192.168.1.1/stream"},
        )
        cam_id = r.json()["id"]
        # Fetch
        r2 = client.get(f"/api/cameras/{cam_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == cam_id

    def test_get_camera_not_found(self, client: TestClient):
        r = client.get("/api/cameras/9999")
        assert r.status_code == 404

    def test_update_camera(self, client: TestClient):
        r = client.post("/api/cameras/", json={"name": "Old", "source": "0"})
        cam_id = r.json()["id"]
        r2 = client.patch(f"/api/cameras/{cam_id}", json={"name": "New Name"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"

    def test_delete_camera(self, client: TestClient):
        r = client.post("/api/cameras/", json={"name": "Del Cam", "source": "0"})
        cam_id = r.json()["id"]
        r2 = client.delete(f"/api/cameras/{cam_id}")
        assert r2.status_code == 204
        r3 = client.get(f"/api/cameras/{cam_id}")
        assert r3.status_code == 404


class TestVendorIntegrations:
    def test_zmodo_login_uses_helper(self, monkeypatch, client: TestClient):
        captured = {}

        async def fake_build(payload):
            captured["payload"] = payload
            return [{"source": "rtsp://u:p@10.0.0.5:10554/tcp/av0_0", "label": "Zmodo", "type": "zmodo"}]

        monkeypatch.setattr("src.api.cameras.build_zmodo_stream", fake_build)

        r = client.post(
            "/api/cameras/zmodo/login",
            json={
                "host": "10.0.0.5",
                "username": "user",
                "password": "pass",
                "channel": 1,
                "port": 10554,
                "transport": "tcp",
            },
        )
        assert r.status_code == 200
        assert captured["payload"].host == "10.0.0.5"
        assert r.json()[0]["type"] == "zmodo"

    def test_blink_login_requires_twofa(self, monkeypatch, client: TestClient):
        async def fake_fetch(payload):
            raise BlinkTwoFARequiredError

        monkeypatch.setattr("src.api.cameras.fetch_blink_liveviews", fake_fetch)
        r = client.post(
            "/api/cameras/blink/login",
            json={"username": "user@example.com", "password": "secret"},
        )
        assert r.status_code == 401
        assert "Two-factor" in r.json()["detail"]

    def test_blink_login_success(self, monkeypatch, client: TestClient):
        async def fake_fetch(payload):
            return [{"source": "rtsps://example/live", "label": "Blink Cam", "type": "blink"}]

        monkeypatch.setattr("src.api.cameras.fetch_blink_liveviews", fake_fetch)
        r = client.post(
            "/api/cameras/blink/login",
            json={"username": "user@example.com", "password": "secret", "two_factor_code": "123456"},
        )
        assert r.status_code == 200
        assert r.json()[0]["type"] == "blink"

    def test_geeni_camera_login(self, monkeypatch, client: TestClient):
        captured = {}

        async def fake_build(payload):
            captured["payload"] = payload
            return [{"source": "rtsp://admin:pass@10.0.0.9/live/main", "label": "Geeni", "type": "geeni"}]

        monkeypatch.setattr("src.api.geeni.build_geeni_stream", fake_build)

        r = client.post(
            "/api/geeni/cameras/login",
            json={
                "host": "10.0.0.9",
                "username": "admin",
                "password": "pass",
                "stream_path": "live/main",
                "port": 554,
            },
        )
        assert r.status_code == 200
        assert captured["payload"].host == "10.0.0.9"
        assert r.json()[0]["type"] == "geeni"

    def test_geeni_light_toggle(self, monkeypatch, client: TestClient):
        async def fake_control(payload):
            return {"device_id": payload.device_id, "on": payload.state}

        monkeypatch.setattr("src.api.geeni.control_geeni_light", fake_control)

        r = client.post(
            "/api/geeni/lights/toggle",
            json={
                "device_id": "abc123",
                "local_key": "key123",
                "ip": "10.0.0.15",
                "state": True,
            },
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ── Events endpoints ─────────────────────────────────────────────────────────

class TestEventsAPI:
    def _create_camera(self, client):
        r = client.post("/api/cameras/", json={"name": "EV Cam", "source": "0"})
        return r.json()["id"]

    def test_list_events_empty(self, client: TestClient):
        r = client.get("/api/events/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_events_filter_by_camera(self, client: TestClient):
        r = client.get("/api/events/?camera_id=999")
        assert r.status_code == 200
        assert r.json() == []

    def test_events_filter_by_type(self, client: TestClient):
        r = client.get("/api/events/?event_type=motion")
        assert r.status_code == 200

    def test_events_pagination(self, client: TestClient):
        r = client.get("/api/events/?limit=5&offset=0")
        assert r.status_code == 200


# ── Alert rules endpoints ─────────────────────────────────────────────────────

class TestAlertRulesAPI:
    def test_list_rules_empty(self, client: TestClient):
        r = client.get("/api/alerts/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_rule(self, client: TestClient):
        payload = {
            "name": "Person Alert",
            "trigger_class": "person",
            "notify_via": "console",
        }
        r = client.post("/api/alerts/", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Person Alert"
        assert data["trigger_class"] == "person"

    def test_get_rule(self, client: TestClient):
        r = client.post(
            "/api/alerts/",
            json={"name": "R", "trigger_class": "*", "notify_via": "console"},
        )
        rule_id = r.json()["id"]
        r2 = client.get(f"/api/alerts/{rule_id}")
        assert r2.status_code == 200

    def test_get_rule_not_found(self, client: TestClient):
        r = client.get("/api/alerts/9999")
        assert r.status_code == 404

    def test_update_rule(self, client: TestClient):
        r = client.post(
            "/api/alerts/",
            json={"name": "Old", "trigger_class": "*", "notify_via": "console"},
        )
        rule_id = r.json()["id"]
        r2 = client.patch(f"/api/alerts/{rule_id}", json={"enabled": False})
        assert r2.status_code == 200
        assert r2.json()["enabled"] is False

    def test_delete_rule(self, client: TestClient):
        r = client.post(
            "/api/alerts/",
            json={"name": "Del", "trigger_class": "*", "notify_via": "console"},
        )
        rule_id = r.json()["id"]
        r2 = client.delete(f"/api/alerts/{rule_id}")
        assert r2.status_code == 204


# ── Web UI page routes ────────────────────────────────────────────────────────

class TestWebPages:
    def test_index_returns_html(self, client: TestClient):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_cameras_page(self, client: TestClient):
        r = client.get("/cameras")
        assert r.status_code == 200

    def test_events_page(self, client: TestClient):
        r = client.get("/events")
        assert r.status_code == 200

    def test_settings_page(self, client: TestClient):
        r = client.get("/settings")
        assert r.status_code == 200
