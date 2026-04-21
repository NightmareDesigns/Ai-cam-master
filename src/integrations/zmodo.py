"""Zmodo camera helpers."""

from __future__ import annotations

from typing import List

from src.camera.discovery import DiscoveredCamera, probe_rtsp_url
from src.schemas.vendors import ZmodoLoginRequest


async def build_zmodo_stream(payload: ZmodoLoginRequest) -> List[DiscoveredCamera]:
    """Construct and optionally validate a Zmodo RTSP URL."""
    path = f"{payload.transport}/av{payload.channel}_0"
    rtsp_url = f"rtsp://{payload.username}:{payload.password}@{payload.host}:{payload.port}/{path}"

    evidence = await probe_rtsp_url(rtsp_url, payload.timeout_seconds)
    if not evidence:
        evidence = "RTSP URL constructed; no response (check IP/credentials/port)"

    return [
        DiscoveredCamera(
            source=rtsp_url,
            label=f"Zmodo @ {payload.host}",
            type="zmodo",
            ip=payload.host,
            port=int(payload.port),
            evidence=evidence,
        )
    ]
