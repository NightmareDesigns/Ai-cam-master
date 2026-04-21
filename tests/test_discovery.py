"""Tests for camera discovery utilities and API endpoint."""

from __future__ import annotations

from typing import List

import pytest

from src.camera import discovery


class TestDiscoveryHelpers:
    def test_parse_subnets_clamps_large_networks(self):
        nets = discovery._parse_subnets(["10.0.0.0/16"], max_hosts=256)
        assert str(nets[0]) == "10.0.0.0/24"

    def test_parse_subnets_skips_invalid(self):
        nets = discovery._parse_subnets(["invalid-net"], max_hosts=256)
        assert nets == []


class TestDiscoveryAPI:
    def test_discover_endpoint_uses_stub(self, monkeypatch, client):
        """Ensure the API surfaces discovery results and respects request body."""

        async def fake_discover(
            subnets=None,
            include_usb=True,
            include_upnp=True,
            max_hosts=256,
            timeout_seconds=1.5,
            max_results=50,
        ) -> List[dict]:
            assert include_usb is False
            assert include_upnp is True
            assert subnets == ["192.168.1.0/24"]
            assert max_results == 2
            return [
                {
                    "source": "rtsp://192.168.1.10:554/",
                    "label": "Mock RTSP",
                    "type": "rtsp",
                    "ip": "192.168.1.10",
                    "port": 554,
                    "evidence": "mocked",
                }
            ]

        monkeypatch.setattr("src.api.cameras.discovery.discover_cameras", fake_discover)

        r = client.post(
            "/api/cameras/discover",
            json={"subnets": ["192.168.1.0/24"], "include_usb": False, "max_results": 2},
        )
        assert r.status_code == 200
        data = r.json()
        assert data[0]["source"] == "rtsp://192.168.1.10:554/"
        assert data[0]["type"] == "rtsp"
