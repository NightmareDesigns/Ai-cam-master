"""Camera auto-discovery utilities.

Attempts to locate network (RTSP / HTTP MJPEG) cameras and local USB webcams
so the user can add them without knowing the exact source ahead of time.
Network scanning is intentionally conservative to avoid long-running sweeps:
- Only IPv4 subnets with a small host count are scanned (default: /24 or
  smaller networks capped at ``max_hosts``).
- A small, focused set of ports is probed with short timeouts.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Iterable, List, Literal, Optional, Sequence, Set
from urllib.parse import urlparse

import cv2
import httpx
import psutil

logger = logging.getLogger(__name__)

DiscoveryType = Literal["usb", "rtsp", "http", "zmodo", "blink", "geeni"]

_RTSP_PORTS = (554, 8554, 10554, 7447)
_HTTP_PORTS = (80, 8000, 8080, 8888)
_MAX_USB_INDEX = 5
_DEFAULT_TIMEOUT = 0.75
_DEFAULT_MAX_RESULTS = 25
_DEFAULT_MAX_HOSTS = 256


@dataclass
class DiscoveredCamera:
    """Data returned by discovery routines."""

    source: str
    label: str
    type: DiscoveryType
    ip: Optional[str] = None
    port: Optional[int] = None
    evidence: Optional[str] = None


def _network_from_addr(addr: str, netmask: str, max_hosts: int) -> Optional[ipaddress.IPv4Network]:
    """Normalize an interface address + netmask into a bounded network."""
    try:
        net = ipaddress.IPv4Network(f"{addr}/{netmask}", strict=False)
    except Exception:
        return None
    # Avoid sweeping huge ranges; clamp anything larger than max_hosts to /24.
    if net.num_addresses > max_hosts:
        try:
            net = ipaddress.IPv4Network(f"{net.network_address}/24", strict=False)
        except Exception:
            return None
    return net


def _local_subnets(max_hosts: int) -> List[ipaddress.IPv4Network]:
    """Return small IPv4 networks for all non-loopback interfaces."""
    networks: List[ipaddress.IPv4Network] = []
    for _, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family != socket.AF_INET:
                continue
            if not addr.address or addr.address.startswith("127."):
                continue
            net = _network_from_addr(addr.address, addr.netmask or "255.255.255.0", max_hosts)
            if net:
                networks.append(net)
    # Deduplicate while preserving order
    seen: Set[str] = set()
    uniq = []
    for n in networks:
        if n.with_prefixlen in seen:
            continue
        uniq.append(n)
        seen.add(n.with_prefixlen)
    return uniq


def _parse_subnets(subnets: Optional[Sequence[str]], max_hosts: int) -> List[ipaddress.IPv4Network]:
    """Parse user-supplied subnet strings, applying the same bounds."""
    if not subnets:
        return _local_subnets(max_hosts)
    parsed: List[ipaddress.IPv4Network] = []
    for raw in subnets:
        raw = raw.strip()
        if not raw:
            continue
        try:
            net = ipaddress.IPv4Network(raw, strict=False)
        except Exception:
            logger.warning("Skipping invalid subnet: %s", raw)
            continue
        if net.num_addresses > max_hosts:
            logger.info("Subnet %s too large, clamping to /24 for discovery safety", raw)
            net = ipaddress.IPv4Network(f"{net.network_address}/24", strict=False)
        parsed.append(net)
    return parsed


def _discover_usb_cameras(max_index: int = _MAX_USB_INDEX) -> List[DiscoveredCamera]:
    """Probe a handful of USB indexes (0..max_index) for reachable cameras."""
    found: List[DiscoveredCamera] = []
    for idx in range(max_index + 1):
        cap = cv2.VideoCapture(idx)
        try:
            if not cap.isOpened():
                continue
            ok, _ = cap.read()
            if not ok:
                continue
            found.append(
                DiscoveredCamera(
                    source=str(idx),
                    label=f"USB Camera {idx}",
                    type="usb",
                    evidence="VideoCapture opened successfully",
                )
            )
        finally:
            cap.release()
    return found


async def _probe_rtsp(ip: str, port: int, timeout: float, path: str = "/") -> Optional[DiscoveredCamera]:
    """Attempt a minimal RTSP OPTIONS handshake to confirm responsiveness."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout,
        )
    except Exception:
        return None

    try:
        safe_path = path if path.startswith("/") else f"/{path}"
        request = f"OPTIONS rtsp://{ip}:{port}{safe_path} RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode()
        writer.write(request)
        await writer.drain()
        data = await asyncio.wait_for(reader.read(64), timeout=timeout)
        evidence = "RTSP OPTIONS responded" if data else "TCP handshake succeeded"
        return DiscoveredCamera(
            source=f"rtsp://{ip}:{port}/",
            label=f"RTSP @ {ip}:{port}",
            type="rtsp",
            ip=ip,
            port=port,
            evidence=evidence,
        )
    except Exception:
        return None
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


async def _probe_http(ip: str, port: int, timeout: float) -> Optional[DiscoveredCamera]:
    """Send a lightweight HEAD request to detect MJPEG/HTTP camera endpoints."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout,
        )
    except Exception:
        return None

    try:
        request = f"HEAD / HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n".encode()
        writer.write(request)
        await writer.drain()
        data = await asyncio.wait_for(reader.read(256), timeout=timeout)
        if not data:
            return None
        evidence = data.split(b"\r\n", 1)[0].decode(errors="ignore")
        return DiscoveredCamera(
            source=f"http://{ip}:{port}/",
            label=f"HTTP @ {ip}:{port}",
            type="http",
            ip=ip,
            port=port,
            evidence=evidence,
        )
    except Exception:
        return None
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


async def _scan_host(ip: str, timeout: float, semaphore: asyncio.Semaphore) -> List[DiscoveredCamera]:
    """Probe a single host for RTSP/HTTP endpoints."""
    results: List[DiscoveredCamera] = []
    async with semaphore:
        for port in _RTSP_PORTS:
            res = await _probe_rtsp(ip, port, timeout)
            if res:
                results.append(res)
        for port in _HTTP_PORTS:
            res = await _probe_http(ip, port, timeout)
            if res:
                results.append(res)
    return results


async def _scan_networks(
    networks: Iterable[ipaddress.IPv4Network],
    timeout: float,
    max_hosts: int,
    max_results: int,
) -> List[DiscoveredCamera]:
    """Scan provided networks for reachable camera endpoints."""
    tasks = []
    semaphore = asyncio.Semaphore(50)
    host_count = 0
    for net in networks:
        for ip in net.hosts():
            host_count += 1
            if host_count > max_hosts:
                break
            tasks.append(asyncio.create_task(_scan_host(str(ip), timeout, semaphore)))
        if host_count > max_hosts:
            break

    found: List[DiscoveredCamera] = []
    for coro in asyncio.as_completed(tasks):
        try:
            res = await coro
        except Exception:
            continue
        for item in res:
            found.append(item)
            if len(found) >= max_results:
                return found
    return found


async def probe_rtsp_url(url: str, timeout: float) -> Optional[str]:
    """Lightweight RTSP probe for an arbitrary RTSP/RTSPS URL.

    Returns a short evidence string when the socket handshake/OPTIONS
    succeeds, otherwise ``None``.
    """
    parsed = urlparse(url)
    if not parsed.hostname:
        return None
    port = parsed.port or 554
    path = parsed.path or "/"
    # Avoid leaking credentials in the probe request line
    request_url = f"rtsp://{parsed.hostname}:{port}{path}"
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(parsed.hostname, port),
            timeout=timeout,
        )
    except Exception:
        return None

    try:
        request = f"OPTIONS {request_url} RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode()
        writer.write(request)
        await writer.drain()
        data = await asyncio.wait_for(reader.read(128), timeout=timeout)
        if not data:
            return "TCP handshake succeeded"
        return data.split(b"\r\n", 1)[0].decode(errors="ignore") or "RTSP responded"
    except Exception:
        return None
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


async def probe_snapshot_url(url: str, timeout: float) -> Optional[str]:
    """Fetch a single JPEG snapshot and return evidence when reachable."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            res = await client.get(url)
    except Exception:
        return None

    if res.status_code >= 400:
        return None
    ctype = res.headers.get("content-type", "").lower()
    if "image" in ctype:
        return f"HTTP {res.status_code} {ctype}"
    return f"HTTP {res.status_code} {len(res.content)} bytes"


async def discover_cameras(
    subnets: Optional[Sequence[str]] = None,
    include_usb: bool = True,
    max_hosts: int = _DEFAULT_MAX_HOSTS,
    timeout_seconds: float = _DEFAULT_TIMEOUT,
    max_results: int = _DEFAULT_MAX_RESULTS,
) -> List[DiscoveredCamera]:
    """Discover cameras on the local machine and LAN.

    Args:
        subnets: Optional list of IPv4 subnet strings (e.g. ``"192.168.1.0/24"``).
                 If omitted, we scan the host's active interfaces, clamped to
                 small networks.
        include_usb: Whether to probe local USB indexes.
        max_hosts: Safety cap on how many hosts to sweep across all subnets.
        timeout_seconds: Socket timeout per host probe.
        max_results: Limit to avoid producing an overwhelming list.
    """
    networks = _parse_subnets(subnets, max_hosts)
    results: List[DiscoveredCamera] = []

    # USB first, since it is fast and local
    if include_usb:
        results.extend(_discover_usb_cameras())
        if len(results) >= max_results:
            return results[:max_results]

    if networks:
        try:
            net_results = await _scan_networks(
                networks,
                timeout_seconds,
                max_hosts,
                max_results - len(results),
            )
            results.extend(net_results)
        except Exception as exc:
            logger.error("Network discovery failed: %s", exc)

    # Deduplicate by source
    deduped: List[DiscoveredCamera] = []
    seen: Set[str] = set()
    for item in results:
        if item.source in seen:
            continue
        deduped.append(item)
        seen.add(item.source)
    return deduped[:max_results]
