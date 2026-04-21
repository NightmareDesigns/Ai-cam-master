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

DiscoveryType = Literal["usb", "rtsp", "http", "zmodo", "blink", "geeni", "eeseecam", "onvif", "upnp", "rtmp", "webrtc", "mqtt", "sip", "coap", "ssdp"]

# Expanded port lists to cover more camera manufacturers
_RTSP_PORTS = (554, 8554, 10554, 7447, 88, 5000, 37777, 34567, 9000)
_HTTP_PORTS = (80, 8000, 8080, 8888, 81, 82, 85, 8081, 9000, 10000)
_ONVIF_PORTS = (80, 8080, 8899, 5000, 10080)
_RTMP_PORTS = (1935, 1936, 8935)
_SIP_PORTS = (5060, 5061)
_COAP_PORTS = (5683, 5684)
_MAX_USB_INDEX = 5
_DEFAULT_TIMEOUT = 1.5  # Increased from 0.75 for better camera detection
_DEFAULT_MAX_RESULTS = 50  # Increased from 25
_DEFAULT_MAX_HOSTS = 256

# Common RTSP paths used by various camera manufacturers
_COMMON_RTSP_PATHS = [
    "/",
    "/stream",
    "/stream1",
    "/live",
    "/live/ch00_0",
    "/h264",
    "/h264/ch1/main/av_stream",
    "/cam/realmonitor",
    "/user=admin&password=&channel=1&stream=0.sdp",
    "/video.mjpg",
    "/mediastream/live",
    "/11",
    "/onvif1",
    "/media/video1",
]


@dataclass
class DiscoveredCamera:
    """Data returned by discovery routines."""

    source: str
    label: str
    type: DiscoveryType
    ip: Optional[str] = None
    port: Optional[int] = None
    evidence: Optional[str] = None


def _network_from_addr(addr: str, netmask: str, max_hosts: int, allow_full_sweep: bool = False) -> Optional[ipaddress.IPv4Network]:
    """Normalize an interface address + netmask into a bounded network."""
    try:
        net = ipaddress.IPv4Network(f"{addr}/{netmask}", strict=False)
    except Exception:
        return None
    # Avoid sweeping huge ranges unless full sweep mode is enabled
    if not allow_full_sweep and net.num_addresses > max_hosts:
        try:
            net = ipaddress.IPv4Network(f"{net.network_address}/24", strict=False)
        except Exception:
            return None
    return net


def _local_subnets(max_hosts: int, allow_full_sweep: bool = False) -> List[ipaddress.IPv4Network]:
    """Return small IPv4 networks for all non-loopback interfaces."""
    networks: List[ipaddress.IPv4Network] = []
    for _, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family != socket.AF_INET:
                continue
            if not addr.address or addr.address.startswith("127."):
                continue
            net = _network_from_addr(addr.address, addr.netmask or "255.255.255.0", max_hosts, allow_full_sweep)
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


def _parse_subnets(subnets: Optional[Sequence[str]], max_hosts: int, allow_full_sweep: bool = False) -> List[ipaddress.IPv4Network]:
    """Parse user-supplied subnet strings, applying the same bounds."""
    if not subnets:
        return _local_subnets(max_hosts, allow_full_sweep)
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
        if not allow_full_sweep and net.num_addresses > max_hosts:
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


async def _probe_onvif(ip: str, port: int, timeout: float) -> Optional[DiscoveredCamera]:
    """Probe for ONVIF/WS-Discovery enabled cameras."""
    try:
        from onvif import ONVIFCamera
        from zeep.exceptions import Fault
    except ImportError:
        logger.debug("ONVIF support not available (onvif-zeep not installed)")
        return None

    try:
        # Try to create an ONVIF camera connection
        camera = ONVIFCamera(ip, port, "admin", "", f"/tmp/onvif_{ip}_{port}", no_cache=True)

        # Try to get device information with a short timeout
        loop = asyncio.get_event_loop()
        device_info = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: camera.devicemgmt.GetDeviceInformation()),
            timeout=timeout
        )

        manufacturer = getattr(device_info, 'Manufacturer', 'Unknown')
        model = getattr(device_info, 'Model', 'Unknown')

        return DiscoveredCamera(
            source=f"onvif://{ip}:{port}",
            label=f"ONVIF @ {ip}:{port} ({manufacturer} {model})",
            type="onvif",
            ip=ip,
            port=port,
            evidence=f"ONVIF device: {manufacturer} {model}",
        )
    except (Fault, Exception):
        return None


async def _discover_upnp_cameras(timeout: float) -> List[DiscoveredCamera]:
    """Discover cameras via UPnP/SSDP protocol."""
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
        from zeroconf.asyncio import AsyncZeroconf
    except ImportError:
        logger.debug("UPnP/mDNS support not available (zeroconf not installed)")
        return []

    discovered: List[DiscoveredCamera] = []

    class CameraListener(ServiceListener):
        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info:
                addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
                for addr in addresses:
                    discovered.append(
                        DiscoveredCamera(
                            source=f"http://{addr}:{info.port}/",
                            label=f"UPnP Device @ {addr}:{info.port}",
                            type="upnp",
                            ip=addr,
                            port=info.port,
                            evidence=f"mDNS service: {name}",
                        )
                    )

    try:
        aiozc = AsyncZeroconf()
        zc = await aiozc.zeroconf

        # Search for common camera service types and related services
        service_types = [
            "_rtsp._tcp.local.",
            "_axis-video._tcp.local.",
            "_onvif._tcp.local.",
            "_http._tcp.local.",
            "_airplay._tcp.local.",          # Some cameras support AirPlay
            "_raop._tcp.local.",             # Remote Audio Output Protocol (related to AirPlay)
            "_dacp._tcp.local.",             # Digital Audio Control Protocol
            "_ipp._tcp.local.",              # Internet Printing Protocol (some camera printers)
            "_scanner._tcp.local.",          # Scanner services
            "_camera._tcp.local.",           # Generic camera service
            "_nvr._tcp.local.",              # Network Video Recorder
            "_dvr._tcp.local.",              # Digital Video Recorder
        ]

        browsers = []
        listener = CameraListener()

        for service_type in service_types:
            browsers.append(ServiceBrowser(zc, service_type, listener))

        # Wait for discovery
        await asyncio.sleep(timeout)

        await aiozc.async_close()

    except Exception as exc:
        logger.debug(f"UPnP discovery failed: {exc}")

    return discovered


async def _probe_rtmp(ip: str, port: int, timeout: float) -> Optional[DiscoveredCamera]:
    """Probe for RTMP streaming servers."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout,
        )
    except Exception:
        return None

    try:
        # RTMP handshake starts with C0+C1 (0x03 + 1536 bytes)
        # We just check if the port is open and responsive
        writer.close()
        await writer.wait_closed()
        return DiscoveredCamera(
            source=f"rtmp://{ip}:{port}/live",
            label=f"RTMP @ {ip}:{port}",
            type="rtmp",
            ip=ip,
            port=port,
            evidence="RTMP port open",
        )
    except Exception:
        return None
    finally:
        with contextlib.suppress(Exception):
            writer.close()
            await writer.wait_closed()


async def _probe_sip(ip: str, port: int, timeout: float) -> Optional[DiscoveredCamera]:
    """Probe for SIP/VoIP cameras."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout,
        )
    except Exception:
        return None

    try:
        # Send SIP OPTIONS request
        request = f"OPTIONS sip:{ip}:{port} SIP/2.0\r\nVia: SIP/2.0/TCP {ip}\r\nTo: sip:{ip}\r\nFrom: sip:scanner@localhost\r\nCall-ID: scan123\r\nCSeq: 1 OPTIONS\r\n\r\n".encode()
        writer.write(request)
        await writer.drain()
        data = await asyncio.wait_for(reader.read(256), timeout=timeout)
        if data and b"SIP" in data:
            return DiscoveredCamera(
                source=f"sip://{ip}:{port}",
                label=f"SIP Camera @ {ip}:{port}",
                type="sip",
                ip=ip,
                port=port,
                evidence="SIP protocol detected",
            )
    except Exception:
        return None
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
    return None


async def _probe_coap(ip: str, port: int, timeout: float) -> Optional[DiscoveredCamera]:
    """Probe for CoAP IoT cameras."""
    try:
        import aiocoap
        from aiocoap import Context, Message, GET
    except ImportError:
        logger.debug("CoAP support not available (aiocoap not installed)")
        return None

    try:
        context = await Context.create_client_context()
        request = Message(code=GET, uri=f"coap://{ip}:{port}/.well-known/core")

        response = await asyncio.wait_for(
            context.request(request).response,
            timeout=timeout
        )

        if response.payload:
            return DiscoveredCamera(
                source=f"coap://{ip}:{port}/",
                label=f"CoAP Device @ {ip}:{port}",
                type="coap",
                ip=ip,
                port=port,
                evidence=f"CoAP device discovered",
            )
    except Exception:
        return None
    finally:
        with contextlib.suppress(Exception):
            await context.shutdown()
    return None


async def _discover_mqtt_cameras(timeout: float) -> List[DiscoveredCamera]:
    """Discover cameras via MQTT (Home Assistant auto-discovery pattern)."""
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        logger.debug("MQTT support not available (paho-mqtt not installed)")
        return []

    discovered: List[DiscoveredCamera] = []

    def on_message(client, userdata, msg):
        """Callback for MQTT messages."""
        try:
            import json
            payload = json.loads(msg.payload.decode())
            # Look for camera devices in Home Assistant auto-discovery format
            if 'device_class' in payload and payload['device_class'] == 'camera':
                stream_url = payload.get('stream_source') or payload.get('entity_picture')
                if stream_url:
                    discovered.append(
                        DiscoveredCamera(
                            source=stream_url,
                            label=f"MQTT Camera: {payload.get('name', 'Unknown')}",
                            type="mqtt",
                            evidence=f"MQTT topic: {msg.topic}",
                        )
                    )
        except Exception as exc:
            logger.debug(f"MQTT message parse error: {exc}")

    # Try common MQTT brokers on localhost and common IPs
    brokers = ["localhost", "127.0.0.1", "192.168.1.1"]

    for broker in brokers:
        try:
            client = mqtt.Client()
            client.on_message = on_message
            client.connect(broker, 1883, 60)
            # Subscribe to Home Assistant auto-discovery topics
            client.subscribe("homeassistant/camera/#")
            client.subscribe("camera/#")
            client.loop_start()
            await asyncio.sleep(timeout)
            client.loop_stop()
            client.disconnect()
            if discovered:
                break
        except Exception:
            continue

    return discovered


async def _discover_webrtc_cameras(timeout: float) -> List[DiscoveredCamera]:
    """Discover WebRTC-enabled cameras via mDNS."""
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
        from zeroconf.asyncio import AsyncZeroconf
    except ImportError:
        logger.debug("WebRTC discovery requires zeroconf")
        return []

    discovered: List[DiscoveredCamera] = []

    class WebRTCListener(ServiceListener):
        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info:
                addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
                for addr in addresses:
                    # WebRTC cameras often expose signaling servers
                    discovered.append(
                        DiscoveredCamera(
                            source=f"webrtc://{addr}:{info.port}/",
                            label=f"WebRTC Camera @ {addr}:{info.port}",
                            type="webrtc",
                            ip=addr,
                            port=info.port,
                            evidence=f"mDNS service: {name}",
                        )
                    )

    try:
        aiozc = AsyncZeroconf()
        zc = await aiozc.zeroconf

        # WebRTC-related service types
        service_types = [
            "_webrtc._tcp.local.",
            "_webrtc._udp.local.",
            "_stun._tcp.local.",
            "_turn._tcp.local.",
        ]

        browsers = []
        listener = WebRTCListener()

        for service_type in service_types:
            browsers.append(ServiceBrowser(zc, service_type, listener))

        await asyncio.sleep(timeout)
        await aiozc.async_close()

    except Exception as exc:
        logger.debug(f"WebRTC discovery failed: {exc}")

    return discovered


async def _discover_ssdp_cameras(timeout: float) -> List[DiscoveredCamera]:
    """Enhanced SSDP/UPnP-AV discovery for NVR/DVR systems."""
    discovered: List[DiscoveredCamera] = []

    # SSDP multicast address
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900

    # M-SEARCH request for media devices
    msearch_request = "\r\n".join([
        "M-SEARCH * HTTP/1.1",
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}",
        "MAN: \"ssdp:discover\"",
        "MX: 2",
        "ST: urn:schemas-upnp-org:device:MediaServer:1",
        "",
        ""
    ]).encode()

    try:
        # Create UDP socket for SSDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        # Send M-SEARCH request
        sock.sendto(msearch_request, (SSDP_ADDR, SSDP_PORT))

        # Collect responses
        end_time = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < end_time:
            try:
                data, addr = sock.recvfrom(2048)
                response = data.decode(errors='ignore')

                # Parse LOCATION header
                if 'LOCATION:' in response or 'Location:' in response:
                    for line in response.split('\n'):
                        if line.lower().startswith('location:'):
                            location = line.split(':', 1)[1].strip()
                            parsed = urlparse(location)
                            if parsed.hostname:
                                discovered.append(
                                    DiscoveredCamera(
                                        source=f"http://{parsed.hostname}:{parsed.port or 80}/",
                                        label=f"SSDP Media Device @ {parsed.hostname}",
                                        type="ssdp",
                                        ip=parsed.hostname,
                                        port=parsed.port or 80,
                                        evidence="UPnP MediaServer discovered",
                                    )
                                )
                            break
                await asyncio.sleep(0.1)
            except socket.timeout:
                break
            except Exception:
                continue

        sock.close()
    except Exception as exc:
        logger.debug(f"SSDP discovery failed: {exc}")

    return discovered


async def _scan_host(ip: str, timeout: float, semaphore: asyncio.Semaphore) -> List[DiscoveredCamera]:
    """Probe a single host for RTSP/HTTP/ONVIF/RTMP/SIP/CoAP endpoints."""
    results: List[DiscoveredCamera] = []
    async with semaphore:
        # Probe RTSP ports
        for port in _RTSP_PORTS:
            res = await _probe_rtsp(ip, port, timeout)
            if res:
                results.append(res)
        # Probe HTTP ports
        for port in _HTTP_PORTS:
            res = await _probe_http(ip, port, timeout)
            if res:
                results.append(res)
        # Probe ONVIF ports
        for port in _ONVIF_PORTS:
            res = await _probe_onvif(ip, port, timeout)
            if res:
                results.append(res)
        # Probe RTMP ports
        for port in _RTMP_PORTS:
            res = await _probe_rtmp(ip, port, timeout)
            if res:
                results.append(res)
        # Probe SIP ports
        for port in _SIP_PORTS:
            res = await _probe_sip(ip, port, timeout)
            if res:
                results.append(res)
        # Probe CoAP ports
        for port in _COAP_PORTS:
            res = await _probe_coap(ip, port, timeout)
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
    include_upnp: bool = True,
    include_mqtt: bool = True,
    include_webrtc: bool = True,
    include_ssdp: bool = True,
    max_hosts: int = _DEFAULT_MAX_HOSTS,
    timeout_seconds: float = _DEFAULT_TIMEOUT,
    max_results: int = _DEFAULT_MAX_RESULTS,
    allow_full_sweep: bool = False,
) -> List[DiscoveredCamera]:
    """Discover cameras on the local machine and LAN.

    Args:
        subnets: Optional list of IPv4 subnet strings (e.g. ``"192.168.1.0/24"``).
                 If omitted, we scan the host's active interfaces, clamped to
                 small networks.
        include_usb: Whether to probe local USB indexes.
        include_upnp: Whether to use UPnP/mDNS discovery (zeroconf).
        include_mqtt: Whether to scan for MQTT-based cameras.
        include_webrtc: Whether to scan for WebRTC cameras.
        include_ssdp: Whether to use SSDP/UPnP-AV discovery for NVR/DVR.
        max_hosts: Safety cap on how many hosts to sweep across all subnets.
        timeout_seconds: Socket timeout per host probe.
        max_results: Limit to avoid producing an overwhelming list.
        allow_full_sweep: If True, scans full subnet ranges without /24 limitation.
    """
    networks = _parse_subnets(subnets, max_hosts, allow_full_sweep)
    results: List[DiscoveredCamera] = []

    # USB first, since it is fast and local
    if include_usb:
        results.extend(_discover_usb_cameras())
        if len(results) >= max_results:
            return results[:max_results]

    # Start all discovery methods in parallel
    tasks = []

    # UPnP/mDNS discovery
    if include_upnp:
        tasks.append(asyncio.create_task(_discover_upnp_cameras(timeout_seconds * 2)))

    # MQTT discovery
    if include_mqtt:
        tasks.append(asyncio.create_task(_discover_mqtt_cameras(timeout_seconds * 2)))

    # WebRTC discovery
    if include_webrtc:
        tasks.append(asyncio.create_task(_discover_webrtc_cameras(timeout_seconds * 2)))

    # SSDP/UPnP-AV discovery
    if include_ssdp:
        tasks.append(asyncio.create_task(_discover_ssdp_cameras(timeout_seconds * 2)))

    # Network scanning for RTSP/HTTP/ONVIF/RTMP/SIP/CoAP
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

    # Collect all parallel discovery results
    for task in tasks:
        try:
            task_results = await task
            results.extend(task_results)
        except Exception as exc:
            logger.error("Discovery task failed: %s", exc)

    # Deduplicate by source
    deduped: List[DiscoveredCamera] = []
    seen: Set[str] = set()
    for item in results:
        if item.source in seen:
            continue
        deduped.append(item)
        seen.add(item.source)
    return deduped[:max_results]
