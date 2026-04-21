"""Blink cloud integration helpers."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import List

from blinkpy.auth import Auth, BlinkTwoFARequiredError, LoginError, TokenRefreshFailed
from blinkpy.blinkpy import Blink, BlinkSetupError

from src.camera.discovery import DiscoveredCamera
from src.schemas.vendors import BlinkLoginRequest

logger = logging.getLogger(__name__)


async def fetch_blink_liveviews(payload: BlinkLoginRequest) -> List[DiscoveredCamera]:
    """Authenticate with Blink and return liveview RTSP URLs."""
    login_data = {"username": payload.username, "password": payload.password}
    blink = Blink()
    # Preserve the session created by Blink but inject credentials and disable prompts
    blink.auth = Auth(
        login_data=login_data,
        no_prompt=True,
        session=blink.auth.session,
    )

    try:
        try:
            await asyncio.wait_for(blink.start(), timeout=payload.timeout_seconds)
        except BlinkTwoFARequiredError:
            twofa = payload.two_factor_code or payload.two_factor_recovery_code
            if not twofa:
                raise
            ok = await blink.auth.complete_2fa_login(twofa)
            if not ok:
                raise LoginError("Invalid Blink 2FA or recovery code")
            await asyncio.wait_for(blink.start(), timeout=payload.timeout_seconds)
        except (LoginError, BlinkSetupError, TokenRefreshFailed) as exc:
            raise LoginError(f"Blink login failed: {exc}") from exc

        try:
            await asyncio.wait_for(
                blink.refresh(force=True), timeout=payload.timeout_seconds
            )
        except Exception as exc:  # pragma: no cover - defensive catch for API quirks
            logger.error("Blink refresh failed: %s", exc)
            raise

        results: List[DiscoveredCamera] = []
        for cam in list(blink.cameras.values())[: payload.max_cameras]:
            try:
                url = await asyncio.wait_for(
                    cam.get_liveview(),
                    timeout=payload.timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning("Timed out starting Blink liveview for %s", cam.name)
                continue
            except NotImplementedError as exc:
                logger.warning(
                    "Blink camera %s does not support liveview: %s", cam.name, exc
                )
                continue
            except Exception as exc:  # pragma: no cover - passthrough for API glitches
                logger.warning("Blink liveview error for %s: %s", cam.name, exc)
                continue
            if not url:
                continue
            results.append(
                DiscoveredCamera(
                    source=url,
                    label=f"Blink {cam.name or cam.camera_id}",
                    type="blink",
                    evidence="Blink liveview RTSP",
                )
            )

        return results
    finally:
        with contextlib.suppress(Exception):
            await blink.auth.session.close()
