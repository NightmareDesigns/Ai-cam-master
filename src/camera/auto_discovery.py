"""Automated camera discovery and credential testing service.

Runs on application startup to find cameras on the network and automatically
test common credentials to identify valid camera logins.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from src.camera import discovery
from src.camera.credentials import brute_force_discovered_cameras, CameraCredentials
from src.models.camera import Camera

logger = logging.getLogger(__name__)


class AutoDiscoveryService:
    """Service for automatic camera discovery and credential testing."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run_discovery(
        self,
        db: Session,
        subnets: Optional[List[str]] = None,
        enable_brute_force: bool = True,
        auto_add_cameras: bool = True,
        max_hosts: int = 256,
        timeout: float = 2.0,
    ) -> dict:
        """Run complete camera discovery with credential testing.

        Args:
            db: Database session
            subnets: Optional list of subnets to scan
            enable_brute_force: Whether to test credentials
            auto_add_cameras: Whether to automatically add discovered cameras to DB
            max_hosts: Maximum hosts to scan
            timeout: Timeout for each probe

        Returns:
            Dictionary with discovery results and statistics
        """
        logger.info("Starting auto-discovery service...")
        stats = {
            "discovered": 0,
            "credentials_found": 0,
            "cameras_added": 0,
            "errors": 0,
        }

        try:
            # Phase 1: Discover all cameras on the network
            logger.info("Phase 1: Scanning network for cameras...")
            discovered = await discovery.discover_cameras(
                subnets=subnets,
                include_usb=True,
                include_upnp=True,
                include_mqtt=True,
                include_webrtc=True,
                include_ssdp=True,
                max_hosts=max_hosts,
                timeout_seconds=timeout,
                max_results=100,
            )
            stats["discovered"] = len(discovered)
            logger.info("Discovered %d potential cameras", len(discovered))

            # Phase 2: Brute-force credentials for network cameras
            credentials_found: List[CameraCredentials] = []
            if enable_brute_force and discovered:
                logger.info("Phase 2: Testing credentials for discovered cameras...")
                credentials_found = await brute_force_discovered_cameras(
                    discovered,
                    timeout=timeout,
                    max_concurrent=5,
                )
                stats["credentials_found"] = len(credentials_found)
                logger.info("Found valid credentials for %d cameras", len(credentials_found))

            # Phase 3: Automatically add cameras to database
            if auto_add_cameras:
                logger.info("Phase 3: Adding cameras to database...")

                # Get existing camera sources to avoid duplicates
                existing_sources = {cam.source for cam in db.query(Camera).all()}

                # Add USB cameras (no credentials needed)
                for cam in discovered:
                    if cam.type == "usb" and cam.source not in existing_sources:
                        try:
                            new_camera = Camera(
                                name=cam.label,
                                source=cam.source,
                                enabled=True,
                                detect_objects=True,
                                detect_motion=False,
                                record_on_event=False,
                            )
                            db.add(new_camera)
                            db.commit()
                            stats["cameras_added"] += 1
                            logger.info("Added USB camera: %s", cam.label)
                        except Exception as exc:
                            logger.error("Failed to add USB camera %s: %s", cam.source, exc)
                            stats["errors"] += 1
                            db.rollback()

                # Add network cameras with validated credentials
                for cred in credentials_found:
                    if cred.source not in existing_sources:
                        try:
                            # Create camera with embedded credentials
                            camera_name = f"Auto-discovered {cred.protocol.upper()} Camera"
                            if cred.protocol == "rtsp":
                                source = cred.source
                            elif cred.protocol == "http":
                                source = f"snapshot+{cred.source}"
                            elif cred.protocol == "onvif":
                                source = cred.source
                            else:
                                source = cred.source

                            new_camera = Camera(
                                name=camera_name,
                                source=source,
                                enabled=True,
                                detect_objects=True,
                                detect_motion=False,
                                record_on_event=False,
                            )
                            db.add(new_camera)
                            db.commit()
                            stats["cameras_added"] += 1
                            logger.info(
                                "Added camera with credentials: %s (user: %s)",
                                camera_name,
                                cred.username,
                            )
                        except Exception as exc:
                            logger.error("Failed to add camera %s: %s", cred.source, exc)
                            stats["errors"] += 1
                            db.rollback()

                # Add discovered cameras without credentials (user can configure later)
                for cam in discovered:
                    if cam.type not in ["usb"] and cam.source not in existing_sources:
                        # Check if we already added this via credentials
                        if not any(cred.source == cam.source for cred in credentials_found):
                            try:
                                new_camera = Camera(
                                    name=f"{cam.label} (needs credentials)",
                                    source=cam.source,
                                    enabled=False,  # Disabled until credentials are provided
                                    detect_objects=True,
                                    detect_motion=False,
                                    record_on_event=False,
                                )
                                db.add(new_camera)
                                db.commit()
                                stats["cameras_added"] += 1
                                logger.info("Added camera (disabled): %s", cam.label)
                            except Exception as exc:
                                logger.debug("Skipped camera %s: %s", cam.source, exc)
                                db.rollback()

            logger.info(
                "Auto-discovery complete: %d discovered, %d credentials found, %d cameras added",
                stats["discovered"],
                stats["credentials_found"],
                stats["cameras_added"],
            )

            return stats

        except Exception as exc:
            logger.error("Auto-discovery service error: %s", exc, exc_info=True)
            stats["errors"] += 1
            return stats

    async def run_background(
        self,
        db: Session,
        subnets: Optional[List[str]] = None,
        enable_brute_force: bool = True,
        auto_add_cameras: bool = True,
        max_hosts: int = 256,
        timeout: float = 2.0,
        interval_hours: int = 24,
    ):
        """Run discovery service in background with periodic re-scans.

        Args:
            db: Database session
            subnets: Optional list of subnets to scan
            enable_brute_force: Whether to test credentials
            auto_add_cameras: Whether to automatically add discovered cameras
            max_hosts: Maximum hosts to scan
            timeout: Timeout for each probe
            interval_hours: Hours between re-scans
        """
        self._running = True
        while self._running:
            try:
                await self.run_discovery(
                    db=db,
                    subnets=subnets,
                    enable_brute_force=enable_brute_force,
                    auto_add_cameras=auto_add_cameras,
                    max_hosts=max_hosts,
                    timeout=timeout,
                )
            except Exception as exc:
                logger.error("Background discovery error: %s", exc)

            # Wait for next scan
            await asyncio.sleep(interval_hours * 3600)

    def start_background(
        self,
        db: Session,
        subnets: Optional[List[str]] = None,
        enable_brute_force: bool = True,
        auto_add_cameras: bool = True,
        max_hosts: int = 256,
        timeout: float = 2.0,
        interval_hours: int = 24,
    ):
        """Start background discovery task.

        Args:
            db: Database session
            subnets: Optional list of subnets to scan
            enable_brute_force: Whether to test credentials
            auto_add_cameras: Whether to automatically add cameras
            max_hosts: Maximum hosts to scan
            timeout: Timeout for each probe
            interval_hours: Hours between re-scans
        """
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self.run_background(
                    db=db,
                    subnets=subnets,
                    enable_brute_force=enable_brute_force,
                    auto_add_cameras=auto_add_cameras,
                    max_hosts=max_hosts,
                    timeout=timeout,
                    interval_hours=interval_hours,
                )
            )
            logger.info("Started background auto-discovery service")

    def stop_background(self):
        """Stop background discovery task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Stopped background auto-discovery service")


# Module-level singleton
auto_discovery_service = AutoDiscoveryService()
