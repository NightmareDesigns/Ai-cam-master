"""Live stream routes.

Provides:
- ``GET /stream/{camera_id}``  — MJPEG live stream
- ``GET /snapshot/{camera_id}`` — single latest JPEG frame
- ``WS  /ws/{camera_id}``       — WebSocket JPEG frame push
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse

from src.camera.manager import camera_manager
from src.config import get_settings

router = APIRouter(tags=["stream"])
logger = logging.getLogger(__name__)

_BOUNDARY = b"frame"
_MJPEG_CONTENT_TYPE = f"multipart/x-mixed-replace; boundary={_BOUNDARY.decode()}"


# ── MJPEG stream ─────────────────────────────────────────────────────────────


async def _mjpeg_generator(camera_id: int):
    settings = get_settings()
    interval = 1.0 / max(settings.stream_fps, 1)
    while True:
        frame = camera_manager.get_jpeg_frame(camera_id)
        if frame:
            yield (
                b"--"
                + _BOUNDARY
                + b"\r\nContent-Type: image/jpeg\r\n\r\n"
                + frame
                + b"\r\n"
            )
        await asyncio.sleep(interval)


@router.get("/stream/{camera_id}")
async def mjpeg_stream(camera_id: int):
    if not camera_manager.is_online(camera_id):
        raise HTTPException(status_code=503, detail="Camera offline or not found")
    return StreamingResponse(
        _mjpeg_generator(camera_id), media_type=_MJPEG_CONTENT_TYPE
    )


# ── Single snapshot ──────────────────────────────────────────────────────────


@router.get("/snapshot/{camera_id}")
async def get_snapshot(camera_id: int):
    frame = camera_manager.get_jpeg_frame(camera_id)
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera offline or no frame available")
    return Response(content=frame, media_type="image/jpeg")


# ── Saved snapshot file ──────────────────────────────────────────────────────


@router.get("/snapshots/file/{filename}")
async def get_snapshot_file(filename: str):
    settings = get_settings()
    # Use os.path.basename to strip any directory components from the user-supplied
    # name, preventing path traversal attacks (e.g. "../../etc/passwd").
    safe_name = os.path.basename(filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    snap_dir = Path(settings.snapshots_dir).resolve()
    path = (snap_dir / safe_name).resolve()
    # Final guard: ensure the resolved path is inside the snapshots directory.
    try:
        path.relative_to(snap_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return Response(content=path.read_bytes(), media_type="image/jpeg")


# ── WebSocket stream ─────────────────────────────────────────────────────────


@router.websocket("/ws/{camera_id}")
async def websocket_stream(websocket: WebSocket, camera_id: int):
    await websocket.accept()
    settings = get_settings()
    interval = 1.0 / max(settings.stream_fps, 1)
    try:
        while True:
            frame = camera_manager.get_jpeg_frame(camera_id)
            if frame:
                await websocket.send_bytes(frame)
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected from camera %d", camera_id)
    except Exception as exc:
        logger.error("WebSocket error for camera %d: %s", camera_id, exc)

