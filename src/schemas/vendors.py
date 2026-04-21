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
