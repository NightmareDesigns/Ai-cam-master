"""EseeCloud / EseeCam helpers."""

from __future__ import annotations

from typing import List

from src.camera.discovery import DiscoveredCamera, probe_rtsp_url, probe_snapshot_url
from src.schemas.vendors import EseeCamLoginRequest


async def build_eeseecam_stream(payload: EseeCamLoginRequest) -> List[DiscoveredCamera]:
    """Build an EseeCam RTSP URL with optional snapshot fallback."""

    def _rtsp_url() -> str:
        path = payload.stream_path.lstrip("/")
        query = []
        if payload.channel:
            query.append(f"channel={payload.channel}")
        if payload.subtype is not None:
            query.append(f"subtype={payload.subtype}")
        query_str = f"?{'&'.join(query)}" if query else ""
        return f"rtsp://{payload.username}:{payload.password}@{payload.host}:{payload.port}/{path}{query_str}"

    def _snapshot_url() -> str:
        snap_path = payload.snapshot_path.format(
            channel=payload.channel,
            subtype=payload.subtype,
        )
        if not snap_path.startswith("/"):
            snap_path = f"/{snap_path}"
        return f"http://{payload.username}:{payload.password}@{payload.host}:{payload.http_port}{snap_path}"

    if payload.mode == "rtsp":
        rtsp_url = _rtsp_url()
        evidence = await probe_rtsp_url(rtsp_url, payload.timeout_seconds)
        if evidence:
            return [
                DiscoveredCamera(
                    source=rtsp_url,
                    label=f"EseeCam @ {payload.host}",
                    type="eeseecam",
                    ip=payload.host,
                    port=int(payload.port),
                    evidence=evidence,
                )
            ]
        if not payload.fallback_to_snapshot:
            return [
                DiscoveredCamera(
                    source=rtsp_url,
                    label=f"EseeCam @ {payload.host}",
                    type="eeseecam",
                    ip=payload.host,
                    port=int(payload.port),
                    evidence="RTSP URL constructed; no response (enable RTSP/ONVIF or check credentials).",
                )
            ]

    snapshot_url = _snapshot_url()
    snap_evidence = await probe_snapshot_url(snapshot_url, payload.timeout_seconds)
    if not snap_evidence:
        snap_evidence = "Snapshot URL constructed; no response (camera may block local access)."

    return [
        DiscoveredCamera(
            source=f"snapshot+{snapshot_url}",
            label=f"EseeCam @ {payload.host}",
            type="eeseecam",
            ip=payload.host,
            port=int(payload.http_port),
            evidence=snap_evidence,
        )
    ]

