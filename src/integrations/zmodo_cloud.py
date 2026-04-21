"""Zmodo Cloud integration for accessing cameras via user.zmodo.com / meshare.com."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

import aiohttp

from src.camera.discovery import DiscoveredCamera
from src.schemas.vendors import ZmodoCloudLoginRequest

logger = logging.getLogger(__name__)


class ZmodoCloudClient:
    """Async client for Zmodo/MeShare cloud API."""

    # Try multiple endpoints for resilience
    LOGIN_ENDPOINTS = [
        "https://11-app-mop.meshare.com/user/user_login",
        "https://12-app-mop.meshare.com/user/user_login",
    ]
    REFRESH_ENDPOINT = "https://11-app-mop.meshare.com/user/refresh_login"
    STREAM_BASE = "https://flv.meshare.com/live"

    def __init__(self, email: str, password: str, timeout: float = 10.0):
        self.email = email
        self.password = password
        self.timeout = timeout
        self.token: Optional[str] = None
        self.login_cert: Optional[str] = None
        self.mng_address: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def login(self) -> bool:
        """Authenticate with Zmodo cloud and obtain session token."""
        password_hash = hashlib.md5(self.password.encode()).hexdigest()

        payload = {
            "email": self.email,
            "password": password_hash,
            "client": "1",  # App client (no captcha)
            "platform": "2",  # Platform identifier
            "app_version": "5.0",
            "client_version": "7.0.2",
            "language": "en",
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # Try each login endpoint until one succeeds
        for endpoint in self.LOGIN_ENDPOINTS:
            try:
                async with self._session.post(
                    endpoint,
                    data=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "Zmodo login endpoint %s returned status %d", endpoint, resp.status
                        )
                        continue

                    data = await resp.json()

                    if data.get("code") != 0:
                        error_msg = data.get("msg", "Unknown error")
                        logger.error("Zmodo login failed: %s", error_msg)
                        if "endpoint" in str(error_msg).lower():
                            # Try next endpoint
                            continue
                        raise ValueError(f"Zmodo login failed: {error_msg}")

                    self.token = data.get("token")
                    self.login_cert = data.get("login_cert")

                    # Extract management address from host_list
                    host_list = data.get("host_list", {})
                    self.mng_address = host_list.get("mng_address")

                    if not self.token or not self.mng_address:
                        logger.error("Missing token or mng_address in login response")
                        continue

                    logger.info("Successfully logged in to Zmodo cloud via %s", endpoint)
                    return True

            except asyncio.TimeoutError:
                logger.warning("Timeout connecting to %s", endpoint)
                continue
            except Exception as e:
                logger.warning("Error with endpoint %s: %s", endpoint, e)
                continue

        raise ConnectionError("Failed to connect to any Zmodo cloud endpoint")

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Fetch list of cameras/devices from Zmodo cloud."""
        if not self.token or not self.mng_address:
            raise ValueError("Not authenticated. Call login() first.")

        payload = {"token": self.token, "start": 0, "count": 999}

        try:
            async with self._session.post(
                f"{self.mng_address}/device/device_list",
                data=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Device list request failed with status {resp.status}")

                data = await resp.json()

                if data.get("code") != 0:
                    error_msg = data.get("msg", "Unknown error")
                    raise ValueError(f"Failed to get device list: {error_msg}")

                return data.get("data", [])

        except asyncio.TimeoutError:
            raise TimeoutError("Timeout fetching device list from Zmodo cloud")

    def build_stream_url(
        self, physical_id: str, quality: str = "hd", include_audio: bool = True
    ) -> str:
        """Build FLV stream URL for a camera.

        Args:
            physical_id: Device physical ID from device list
            quality: 'sd' (480p) or 'hd' (1080p)
            include_audio: Include audio in stream

        Returns:
            HTTPS FLV stream URL
        """
        if not self.token:
            raise ValueError("Not authenticated. Call login() first.")

        media_type = 2 if quality.lower() == "hd" else 1

        params = {
            "devid": physical_id,
            "token": self.token,
            "media_type": media_type,
            "channel": 0,
            "has_audio": 1 if include_audio else 0,
        }

        return f"{self.STREAM_BASE}?{urlencode(params)}"


async def fetch_zmodo_cloud_cameras(payload: ZmodoCloudLoginRequest) -> List[DiscoveredCamera]:
    """Authenticate with Zmodo cloud and return available camera streams.

    Args:
        payload: Zmodo cloud login credentials and options

    Returns:
        List of discovered cameras with FLV stream URLs
    """
    results: List[DiscoveredCamera] = []

    async with ZmodoCloudClient(
        payload.email, payload.password, timeout=payload.timeout_seconds
    ) as client:
        # Authenticate
        try:
            await client.login()
        except (ConnectionError, ValueError) as e:
            logger.error("Zmodo cloud login failed: %s", e)
            raise ValueError(f"Zmodo cloud authentication failed: {e}") from e

        # Fetch devices
        try:
            devices = await client.get_devices()
        except (ValueError, TimeoutError) as e:
            logger.error("Failed to fetch Zmodo devices: %s", e)
            raise ValueError(f"Failed to fetch Zmodo cameras: {e}") from e

        if not devices:
            logger.warning("No Zmodo cameras found in account")
            return results

        # Limit to max_cameras
        devices = devices[: payload.max_cameras]

        # Build stream URLs for each camera
        for device in devices:
            physical_id = device.get("physical_id")
            device_name = device.get("name") or device.get("device_name") or "Unknown Camera"
            device_type = device.get("type", "")

            if not physical_id:
                logger.warning("Device missing physical_id: %s", device)
                continue

            # Build stream URL
            try:
                stream_url = client.build_stream_url(
                    physical_id, quality=payload.quality, include_audio=True
                )

                results.append(
                    DiscoveredCamera(
                        source=stream_url,
                        label=f"Zmodo Cloud: {device_name}",
                        type="zmodo_cloud",
                        evidence=f"Cloud FLV stream ({payload.quality.upper()}, device type: {device_type})",
                    )
                )

                logger.info("Added Zmodo cloud camera: %s", device_name)

            except Exception as e:
                logger.warning("Failed to build stream URL for %s: %s", device_name, e)
                continue

    return results
