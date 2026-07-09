"""
AlertService — multi-channel alert delivery.

Supported channels (all opt-in via environment variables):
  • Application logger  (always active)
  • Slack webhook       (set SLACK_ALERT_WEBHOOK_URL)
  • Email via SMTP      (set ALERT_EMAIL_TO + MAIL_* vars)

Usage:
    AlertService.send_alert("Disk almost full", level="WARNING")
    AlertService.log_critical_error(exc, endpoint="/api/inventory")
    AlertService.send_security_alert("Rate limit exceeded", context={...})
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)


def _post_slack(webhook_url: str, message: str, level: str) -> None:
    """Fire-and-forget Slack webhook post (runs in background thread)."""
    try:
        import urllib.request

        colour_map = {
            "CRITICAL": "#FF0000",
            "ERROR": "#FF6600",
            "WARNING": "#FFA500",
            "INFO": "#36A64F",
        }
        colour = colour_map.get(level.upper(), "#888888")
        payload = json.dumps(
            {
                "attachments": [
                    {
                        "color": colour,
                        "title": f"[TrackIT] {level.upper()} Alert",
                        "text": message,
                        "footer": "TrackIT AlertService",
                        "ts": datetime.now(timezone.utc).timestamp(),
                    }
                ]
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            if resp.status not in (200, 204):
                logger.warning("Slack alert returned HTTP %s", resp.status)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Slack alert delivery failed: %s", exc)


def _send_email_alert(recipients: list[str], subject: str, body: str) -> None:
    """Send alert email using Flask-Mail (best-effort)."""
    try:
        from flask_mail import Message  # type: ignore

        # Import the mail extension lazily to avoid circular imports
        from app import mail  # type: ignore

        msg = Message(subject=subject, recipients=recipients, body=body)
        mail.send(msg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email alert delivery failed: %s", exc)


class AlertService:
    """Service for handling system-wide alerts and critical notifications."""

    # --------------------------------------------------------------------------
    # Core alert dispatcher
    # --------------------------------------------------------------------------

    @staticmethod
    def send_alert(
        message: str,
        level: str = "ERROR",
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Dispatch an alert through all configured channels.

        Args:
            message: Human-readable alert message.
            level:   Severity — CRITICAL | ERROR | WARNING | INFO.
            context: Optional dict of additional contextual data.
        """
        severity = level.upper()
        ctx_str = f" | Context: {context}" if context else ""
        alert_msg = f"[SYSTEM ALERT] [{severity}] {message}{ctx_str}"

        # 1) Application logger (always)
        log_fn = {
            "CRITICAL": current_app.logger.critical,
            "ERROR": current_app.logger.error,
            "WARNING": current_app.logger.warning,
            "INFO": current_app.logger.info,
        }.get(severity, current_app.logger.error)
        log_fn(alert_msg)

        # 2) Slack webhook (optional)
        slack_url = current_app.config.get("SLACK_ALERT_WEBHOOK_URL")
        if slack_url:
            threading.Thread(
                target=_post_slack,
                args=(slack_url, alert_msg, severity),
                daemon=True,
            ).start()

        # 3) Email alert (optional)
        alert_email_to = current_app.config.get("ALERT_EMAIL_TO", "")
        recipients = [e.strip() for e in alert_email_to.split(",") if e.strip()]
        if recipients and severity in ("CRITICAL", "ERROR"):
            subject = f"[TrackIT {severity}] {message[:80]}"
            body = f"{alert_msg}\n\nTimestamp: {datetime.now(timezone.utc).isoformat()}"
            if context:
                body += f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"
            threading.Thread(
                target=_send_email_alert,
                args=(recipients, subject, body),
                daemon=True,
            ).start()

    # --------------------------------------------------------------------------
    # Convenience helpers
    # --------------------------------------------------------------------------

    @staticmethod
    def log_critical_error(
        error: Exception, endpoint: str | None = None
    ) -> None:
        """Log and alert on a critical system failure (e.g. unhandled 500)."""
        message = f"Critical error: {type(error).__name__}: {str(error)}"
        context = {"endpoint": endpoint} if endpoint else None
        AlertService.send_alert(message, level="CRITICAL", context=context)

    @staticmethod
    def send_security_alert(
        event: str,
        context: dict[str, Any] | None = None,
        level: str = "WARNING",
    ) -> None:
        """
        Raise a security-specific alert (auth failures, rate limits, etc.).

        Args:
            event:   Short event label, e.g. "RATE_LIMIT_EXCEEDED".
            context: Dict with ip, endpoint, user_id, etc.
            level:   Severity override (default WARNING).
        """
        message = f"[SECURITY] {event}"
        AlertService.send_alert(message, level=level, context=context)
