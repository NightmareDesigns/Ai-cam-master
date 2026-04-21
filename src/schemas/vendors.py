"""Schemas for vendor-specific camera integrations."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, conint, confloat


class ZmodoLoginRequest(BaseModel):
    host: str = Field(..., description="IP or hostname of the Zmodo camera.")
    username: str = Field(..., description="Zmodo camera username.")
    password: str = Field(..., description="Zmodo camera password.")
    port: conint(ge=1, le=65535) = Field(
        default=10554, description="RTSP port (commonly 10554 on Zmodo)."
    )
    channel: conint(ge=0, le=8) = Field(
        default=0, description="Channel index (0 for single-lens cameras)."
    )
    transport: Literal["tcp", "udp"] = Field(
        default="tcp", description="RTSP transport to use in the URL."
    )
    mode: Literal["rtsp", "jpeg"] = Field(
        default="rtsp", description="Use RTSP (default) or snapshot-only JPEG mode."
    )
    http_port: conint(ge=1, le=65535) = Field(
        default=80, description="HTTP port for snapshot fallback when RTSP is locked."
    )
    snapshot_path: str = Field(
        default="/cgi-bin/net_jpeg.cgi",
        description="Path used when fetching JPEG snapshots from Zmodo.",
    )
    fallback_to_snapshot: bool = Field(
        default=True,
        description="If RTSP fails, try snapshot URL instead of returning nothing.",
    )
    timeout_seconds: confloat(ge=0.1, le=5.0) = Field(
        default=1.0, description="Socket timeout when validating the RTSP endpoint."
    )


class BlinkLoginRequest(BaseModel):
    username: str = Field(..., description="Blink account email/username.")
    password: str = Field(..., description="Blink account password.")
    two_factor_code: Optional[str] = Field(
        default=None,
        description="6-digit 2FA code when prompted by Blink.",
    )
    timeout_seconds: confloat(ge=1.0, le=30.0) = Field(
        default=10.0, description="Timeout for Blink API and liveview calls."
    )
    max_cameras: conint(ge=1, le=32) = Field(
        default=16, description="Limit how many Blink cameras are returned."
    )


class GeeniCameraRequest(BaseModel):
    host: str = Field(..., description="IP or hostname of the Geeni camera.")
    username: str = Field(default="admin", description="Geeni camera username.")
    password: str = Field(default="", description="Geeni camera password.")
    port: conint(ge=1, le=65535) = Field(
        default=554, description="RTSP port (commonly 554 on Geeni/Tuya cameras)."
    )
    stream_path: str = Field(
        default="live/main",
        description="Path portion of the RTSP URL (e.g. live/main or stream_0).",
    )
    mode: Literal["rtsp", "jpeg"] = Field(
        default="rtsp", description="Use RTSP (default) or snapshot-only JPEG mode."
    )
    http_port: conint(ge=1, le=65535) = Field(
        default=80, description="HTTP port for snapshot fallback."
    )
    snapshot_path: str = Field(
        default="/cgi-bin/snapshot.cgi",
        description="Path used when fetching JPEG snapshots from Geeni cameras.",
    )
    fallback_to_snapshot: bool = Field(
        default=True,
        description="If RTSP probe fails, attempt a JPEG snapshot URL instead.",
    )
    timeout_seconds: confloat(ge=0.1, le=5.0) = Field(
        default=1.5, description="Timeout for probing RTSP or HTTP endpoints."
    )


class GeeniLightRequest(BaseModel):
    device_id: str = Field(..., description="Tuya/Geeni device ID for the bulb.")
    local_key: str = Field(..., description="Local key for LAN control.")
    ip: str = Field(..., description="LAN IP address of the light.")
    state: Optional[bool] = Field(
        default=True, description="Turn light on (true) or off (false)."
    )
    brightness: Optional[conint(ge=1, le=100)] = Field(
        default=None, description="Optional brightness percentage (1-100)."
    )
    protocol_version: str = Field(
        default="3.3", description="Tuya protocol version (often 3.3 or 3.4)."
    )
