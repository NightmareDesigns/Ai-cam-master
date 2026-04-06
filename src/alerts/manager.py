"""Alert rule evaluation and notification dispatch."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.alert_rule import AlertRule
from src.models.event import Event

logger = logging.getLogger(__name__)


class AlertManager:
    """Evaluates alert rules against new events and dispatches notifications."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._settings = get_settings()

    def evaluate(self, event: Event) -> None:
        """Check all enabled rules and fire matching ones."""
        rules = (
            self._db.query(AlertRule)
            .filter(AlertRule.enabled == True)  # noqa: E712
            .filter(
                (AlertRule.camera_id == None)  # noqa: E711  global rule
                | (AlertRule.camera_id == event.camera_id)
            )
            .all()
        )
        for rule in rules:
            if self._matches(rule, event):
                self._dispatch(rule, event)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _matches(rule: AlertRule, event: Event) -> bool:
        if rule.trigger_class == "*":
            return True
        if event.object_class and rule.trigger_class.lower() == event.object_class.lower():
            return True
        if rule.trigger_class.lower() == event.event_type.lower():
            return True
        return False

    def _dispatch(self, rule: AlertRule, event: Event) -> None:
        methods = [m.strip().lower() for m in rule.notify_via.split(",")]
        for method in methods:
            if method == "console":
                self._notify_console(rule, event)
            elif method == "email":
                self._notify_email(rule, event)
            elif method == "webhook":
                self._notify_webhook(rule, event)
            else:
                logger.warning("Unknown notification method: %s", method)

    @staticmethod
    def _notify_console(rule: AlertRule, event: Event) -> None:
        logger.warning(
            "🚨 ALERT [%s] — Camera %d | %s %s (conf=%.0f%%)",
            rule.name,
            event.camera_id,
            event.event_type,
            event.object_class or "",
            (event.confidence or 0) * 100,
        )

    def _notify_email(self, rule: AlertRule, event: Event) -> None:
        settings = self._settings
        if not (settings.smtp_host and settings.alert_email_to):
            logger.debug("Email alert skipped: SMTP not configured.")
            return
        subject = f"[AI-Cam] Alert: {rule.name}"
        body = (
            f"Camera ID: {event.camera_id}\n"
            f"Event: {event.event_type}\n"
            f"Class: {event.object_class or 'N/A'}\n"
            f"Confidence: {(event.confidence or 0):.0%}\n"
            f"Snapshot: {event.snapshot_path or 'N/A'}\n"
            f"Time: {event.occurred_at}\n"
        )
        try:
            import aiosmtplib  # type: ignore
            from email.mime.text import MIMEText

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = settings.alert_email_from or settings.smtp_user
            msg["To"] = settings.alert_email_to

            asyncio.get_event_loop().run_until_complete(
                aiosmtplib.send(
                    msg,
                    hostname=settings.smtp_host,
                    port=settings.smtp_port,
                    username=settings.smtp_user or None,
                    password=settings.smtp_password or None,
                    start_tls=True,
                )
            )
            logger.info("Email alert sent to %s", settings.alert_email_to)
        except Exception as exc:
            logger.error("Email alert failed: %s", exc)

    @staticmethod
    def _notify_webhook(rule: AlertRule, event: Event) -> None:
        if not rule.webhook_url:
            logger.debug("Webhook alert skipped: no URL configured on rule %d.", rule.id)
            return
        payload = {
            "rule": rule.name,
            "camera_id": event.camera_id,
            "event_type": event.event_type,
            "object_class": event.object_class,
            "confidence": event.confidence,
            "snapshot_path": event.snapshot_path,
            "occurred_at": str(event.occurred_at),
        }
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(rule.webhook_url, json=payload)
                resp.raise_for_status()
            logger.info("Webhook alert sent to %s (status %d).", rule.webhook_url, resp.status_code)
        except Exception as exc:
            logger.error("Webhook alert failed: %s", exc)
