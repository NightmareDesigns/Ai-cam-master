"""Camera credential brute-force testing.

Attempts to authenticate with discovered cameras using common default
credentials to automatically identify valid logins.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import cv2
import httpx

logger = logging.getLogger(__name__)

# Common default credentials for IP cameras (username, password)
DEFAULT_CREDENTIALS = [
    ("admin", ""),
    ("admin", "admin"),
    ("admin", "12345"),
    ("admin", "123456"),
    ("admin", "password"),
    ("root", ""),
    ("root", "root"),
    ("root", "12345"),
    ("root", "password"),
    ("user", ""),
    ("user", "user"),
    ("default", ""),
    ("guest", ""),
    ("ubnt", "ubnt"),  # Ubiquiti
    ("admin", "888888"),  # Common Chinese cameras
    ("admin", "00000000"),
    ("admin", "1111"),
    ("admin", "1234"),
    ("admin", "9999"),
    ("administrator", ""),
    ("administrator", "administrator"),
    ("service", "service"),
    ("supervisor", "supervisor"),
    ("tech", "tech"),
    ("support", "support"),
]

# Vendor-specific common credentials
VENDOR_CREDENTIALS = {
    "axis": [("root", "pass"), ("root", "")],
    "hikvision": [("admin", "12345"), ("admin", "")],
    "dahua": [("admin", "admin"), ("admin", "")],
    "foscam": [("admin", ""), ("admin", "foscam")],
    "amcrest": [("admin", "admin"), ("admin", "")],
    "reolink": [("admin", ""), ("admin", "reolink")],
    "vivotek": [("root", ""), ("admin", "")],
    "geovision": [("admin", "admin"), ("admin", "")],
    "acti": [("admin", "123456"), ("admin", "")],
    "bosch": [("admin", ""), ("service", "service")],
    "panasonic": [("admin", "12345"), ("admin", "")],
    "samsung": [("admin", "4321"), ("admin", "")],
    "sony": [("admin", "admin"), ("admin", "")],
    "tplink": [("admin", "admin"), ("admin", "")],
    "dlink": [("admin", ""), ("admin", "admin")],
    "netgear": [("admin", "password"), ("admin", "")],
    "arlo": [("admin", "arlo"), ("admin", "")],
    "wyze": [("admin", ""), ("admin", "wyze")],
    "ring": [("admin", ""), ("admin", "ring")],
    "nest": [("admin", ""), ("admin", "nest")],
    "ubiquiti": [("ubnt", "ubnt"), ("admin", "")],
    "zmodo": [("admin", ""), ("admin", "111111")],
    "swann": [("admin", "12345"), ("admin", "")],
    "lorex": [("admin", "000000"), ("admin", "")],
    "adt": [("admin", "admin"), ("admin", "")],
    "blink": [("admin", ""), ("admin", "blink")],
    "eufy": [("admin", ""), ("admin", "eufy")],
}


@dataclass
class CameraCredentials:
    """Validated credentials for a camera."""

    source: str
    username: str
    password: str
    protocol: str  # rtsp, http, onvif
    evidence: str


async def _test_rtsp_credentials(
    ip: str, port: int, username: str, password: str, timeout: float = 2.0
) -> Optional[str]:
    """Test RTSP credentials by attempting an OPTIONS request."""
    for path in ["/", "/stream", "/stream1", "/live", "/h264", "/cam/realmonitor"]:
        rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}{path}"
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout,
            )
            try:
                request = f"OPTIONS {rtsp_url} RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode()
                writer.write(request)
                await writer.drain()
                data = await asyncio.wait_for(reader.read(128), timeout=timeout)
                if data and (b"RTSP/1.0 200" in data or b"RTSP/1.0 401" not in data):
                    return rtsp_url
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
        except Exception:
            continue
    return None


async def _test_http_credentials(
    ip: str, port: int, username: str, password: str, timeout: float = 2.0
) -> Optional[str]:
    """Test HTTP credentials by attempting various snapshot paths."""
    paths = [
        "/cgi-bin/snapshot.cgi",
        "/snapshot.cgi",
        "/cgi-bin/net_jpeg.cgi",
        "/webcapture.jpg?command=snap&channel=1",
        "/image/jpeg.cgi",
        "/tmpfs/auto.jpg",
        "/jpg/image.jpg",
        "/axis-cgi/jpg/image.cgi",
    ]

    for path in paths:
        url = f"http://{ip}:{port}{path}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    url,
                    auth=(username, password),
                    follow_redirects=True,
                )
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "").lower()
                    if "image" in content_type or len(response.content) > 1000:
                        return url
        except Exception:
            continue
    return None


async def _test_onvif_credentials(
    ip: str, port: int, username: str, password: str, timeout: float = 2.0
) -> Optional[str]:
    """Test ONVIF credentials."""
    try:
        from onvif import ONVIFCamera
    except ImportError:
        return None

    try:
        camera = ONVIFCamera(
            ip, port, username, password, f"/tmp/onvif_{ip}_{port}", no_cache=True
        )
        loop = asyncio.get_event_loop()
        device_info = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: camera.devicemgmt.GetDeviceInformation()),
            timeout=timeout,
        )
        if device_info:
            return f"onvif://{username}:{password}@{ip}:{port}"
    except Exception:
        pass
    return None


async def brute_force_credentials(
    ip: str,
    rtsp_ports: List[int] = [554, 8554, 10554],
    http_ports: List[int] = [80, 8080, 8081],
    onvif_ports: List[int] = [80, 8080],
    timeout: float = 2.0,
    max_attempts: int = 15,
) -> List[CameraCredentials]:
    """Attempt to authenticate with a camera using common credentials.

    Args:
        ip: IP address of the camera
        rtsp_ports: List of RTSP ports to try
        http_ports: List of HTTP ports to try
        onvif_ports: List of ONVIF ports to try
        timeout: Timeout for each credential test
        max_attempts: Maximum number of credential pairs to try

    Returns:
        List of validated credentials
    """
    validated: List[CameraCredentials] = []
    credentials_to_try = DEFAULT_CREDENTIALS[:max_attempts]

    # Try RTSP authentication
    for port in rtsp_ports:
        for username, password in credentials_to_try:
            try:
                result = await _test_rtsp_credentials(ip, port, username, password, timeout)
                if result:
                    validated.append(
                        CameraCredentials(
                            source=result,
                            username=username,
                            password=password,
                            protocol="rtsp",
                            evidence=f"RTSP authentication successful on port {port}",
                        )
                    )
                    logger.info(
                        "Found valid RTSP credentials for %s:%d (user: %s)",
                        ip,
                        port,
                        username,
                    )
                    # Only return first valid credential per protocol
                    break
            except Exception as exc:
                logger.debug("RTSP test failed for %s@%s:%d: %s", username, ip, port, exc)
        if any(c.protocol == "rtsp" for c in validated):
            break

    # Try HTTP authentication
    for port in http_ports:
        for username, password in credentials_to_try:
            try:
                result = await _test_http_credentials(ip, port, username, password, timeout)
                if result:
                    validated.append(
                        CameraCredentials(
                            source=result,
                            username=username,
                            password=password,
                            protocol="http",
                            evidence=f"HTTP authentication successful on port {port}",
                        )
                    )
                    logger.info(
                        "Found valid HTTP credentials for %s:%d (user: %s)",
                        ip,
                        port,
                        username,
                    )
                    break
            except Exception as exc:
                logger.debug("HTTP test failed for %s@%s:%d: %s", username, ip, port, exc)
        if any(c.protocol == "http" for c in validated):
            break

    # Try ONVIF authentication
    for port in onvif_ports:
        for username, password in credentials_to_try:
            try:
                result = await _test_onvif_credentials(ip, port, username, password, timeout)
                if result:
                    validated.append(
                        CameraCredentials(
                            source=result,
                            username=username,
                            password=password,
                            protocol="onvif",
                            evidence=f"ONVIF authentication successful on port {port}",
                        )
                    )
                    logger.info(
                        "Found valid ONVIF credentials for %s:%d (user: %s)",
                        ip,
                        port,
                        username,
                    )
                    break
            except Exception as exc:
                logger.debug("ONVIF test failed for %s@%s:%d: %s", username, ip, port, exc)
        if any(c.protocol == "onvif" for c in validated):
            break

    return validated


async def brute_force_discovered_cameras(
    discovered_cameras: List,
    timeout: float = 2.0,
    max_concurrent: int = 5,
) -> List[CameraCredentials]:
    """Brute-force credentials for a list of discovered cameras.

    Args:
        discovered_cameras: List of DiscoveredCamera objects
        timeout: Timeout for each credential test
        max_concurrent: Maximum number of concurrent brute-force operations

    Returns:
        List of validated credentials
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _brute_force_with_semaphore(camera):
        async with semaphore:
            if camera.ip:
                return await brute_force_credentials(
                    camera.ip,
                    timeout=timeout,
                )
            return []

    tasks = []
    for camera in discovered_cameras:
        if camera.ip and camera.type in ["rtsp", "http", "onvif"]:
            tasks.append(_brute_force_with_semaphore(camera))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_credentials: List[CameraCredentials] = []
    for result in results:
        if isinstance(result, list):
            all_credentials.extend(result)
        elif isinstance(result, Exception):
            logger.debug("Brute-force task failed: %s", result)

    return all_credentials
