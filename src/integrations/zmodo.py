"""Zmodo camera helpers."""

from __future__ import annotations

from typing import List

from src.camera.discovery import DiscoveredCamera, probe_rtsp_url, probe_snapshot_url
from src.schemas.vendors import ZmodoLoginRequest


async def build_zmodo_stream(payload: ZmodoLoginRequest) -> List[DiscoveredCamera]:
    """Construct and optionally validate a Zmodo stream URL.

    Newer Zmodo firmware versions often lock RTSP. When ``mode`` is ``jpeg`` or
    when RTSP probing fails and ``fallback_to_snapshot`` is enabled, we return
    a snapshot-based source that the app can poll.
    """
    path = f"{payload.transport}/av{payload.channel}_0"
    rtsp_url = f"rtsp://{payload.username}:{payload.password}@{payload.host}:{payload.port}/{path}"

    def _build_snapshot_url() -> str:
        snap_path = payload.snapshot_path
        if not snap_path.startswith("/"):
            snap_path = f"/{snap_path}"
        return f"http://{payload.username}:{payload.password}@{payload.host}:{payload.http_port}{snap_path}"

    # Prefer RTSP unless the caller explicitly asks for JPEG-only
    if payload.mode == "rtsp":
        evidence = await probe_rtsp_url(rtsp_url, payload.timeout_seconds)
        if evidence:
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
        if not payload.fallback_to_snapshot:
            return [
                DiscoveredCamera(
                    source=rtsp_url,
                    label=f"Zmodo @ {payload.host}",
                    type="zmodo",
                    ip=payload.host,
                    port=int(payload.port),
                    evidence="RTSP URL constructed; no response (check IP/credentials/port)",
                )
            ]

    snapshot_url = _build_snapshot_url()
    snap_evidence = await probe_snapshot_url(snapshot_url, payload.timeout_seconds)
    if not snap_evidence:
        snap_evidence = "Snapshot URL constructed; no response (camera may block local access)."

    return [
        DiscoveredCamera(
            source=f"snapshot+{snapshot_url}",
            label=f"Zmodo @ {payload.host}",
            type="zmodo",
            ip=payload.host,
            port=int(payload.http_port),
            evidence=snap_evidence,
        )
    ]
