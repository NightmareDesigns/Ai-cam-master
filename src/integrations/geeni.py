"""Geeni (Tuya-based) camera and light helpers."""

from __future__ import annotations

import asyncio
from typing import List

from src.camera.discovery import DiscoveredCamera, probe_rtsp_url, probe_snapshot_url
from src.schemas.vendors import GeeniCameraRequest, GeeniLightRequest


async def build_geeni_stream(payload: GeeniCameraRequest) -> List[DiscoveredCamera]:
    """Build a Geeni/Tuya camera URL with RTSP or snapshot fallback."""

    def _rtsp_url() -> str:
        path = payload.stream_path.lstrip("/")
        return f"rtsp://{payload.username}:{payload.password}@{payload.host}:{payload.port}/{path}"

    def _snapshot_url() -> str:
        snap_path = payload.snapshot_path
        if not snap_path.startswith("/"):
            snap_path = f"/{snap_path}"
        return f"http://{payload.username}:{payload.password}@{payload.host}:{payload.http_port}{snap_path}"

    # Try RTSP unless caller prefers JPEG-only
    if payload.mode == "rtsp":
        rtsp_url = _rtsp_url()
        evidence = await probe_rtsp_url(rtsp_url, payload.timeout_seconds)
        if evidence:
            return [
                DiscoveredCamera(
                    source=rtsp_url,
                    label=f"Geeni @ {payload.host}",
                    type="geeni",
                    ip=payload.host,
                    port=int(payload.port),
                    evidence=evidence,
                )
            ]
        if not payload.fallback_to_snapshot:
            return [
                DiscoveredCamera(
                    source=rtsp_url,
                    label=f"Geeni @ {payload.host}",
                    type="geeni",
                    ip=payload.host,
                    port=int(payload.port),
                    evidence="RTSP URL constructed; no response (camera may be cloud-only).",
                )
            ]

    snapshot_url = _snapshot_url()
    snap_evidence = await probe_snapshot_url(snapshot_url, payload.timeout_seconds)
    if not snap_evidence:
        snap_evidence = "Snapshot URL constructed; no response (camera may be cloud-only)."

    return [
        DiscoveredCamera(
            source=f"snapshot+{snapshot_url}",
            label=f"Geeni @ {payload.host}",
            type="geeni",
            ip=payload.host,
            port=int(payload.http_port),
            evidence=snap_evidence,
        )
    ]


async def control_geeni_light(payload: GeeniLightRequest) -> dict:
    """Toggle or adjust a Geeni/Tuya smart light via TinyTuya."""

    # Import lazily so unit tests can mock without requiring the library
    import tinytuya

    def _execute():
        device = tinytuya.BulbDevice(
            payload.device_id,
            payload.ip,
            payload.local_key,
            version=payload.protocol_version,
        )
        device.set_socketPersistent(True)
        if payload.state is True:
            device.turn_on()
        elif payload.state is False:
            device.turn_off()
        if payload.brightness is not None:
            device.set_brightness_percentage(int(payload.brightness))
        status = device.status() or {}
        status.update({"device_id": payload.device_id})
        return status

    return await asyncio.to_thread(_execute)
