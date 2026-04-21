"""Schemas for camera discovery API."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, conint, confloat


class DiscoveryRequest(BaseModel):
    subnets: Optional[List[str]] = Field(
        default=None,
        description="IPv4 subnets to scan, e.g. 192.168.1.0/24. Defaults to host interfaces.",
    )
    include_usb: bool = Field(
        default=True, description="Probe local USB indexes (0-5) for webcams."
    )
    max_hosts: conint(ge=1, le=2048) = Field(
        default=256,
        description="Safety cap for how many hosts to sweep across all subnets.",
    )
    timeout_seconds: confloat(ge=0.1, le=5.0) = Field(
        default=0.75, description="Socket timeout per host probe."
    )
    max_results: conint(ge=1, le=200) = Field(
        default=25, description="Limit how many discoveries are returned."
    )


class DiscoveredCamera(BaseModel):
    source: str
    label: str
    type: Literal["usb", "rtsp", "http", "zmodo", "blink"]
    ip: Optional[str] = None
    port: Optional[int] = None
    evidence: Optional[str] = None
