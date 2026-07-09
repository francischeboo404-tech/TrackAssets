"""
Logging configuration for TrackIT.

Features:
  • Rotating file handlers: trackit.log (all INFO+) and errors.log (ERROR+)
  • security.log — dedicated rotating handler for auth/security events
  • Request-ID (UUID) injected into every log record inside a request context
  • Vercel / read-only filesystem fallback (stdout only)
"""
import logging
import os
import uuid
from logging.handlers import RotatingFileHandler

from flask import g, has_request_context, request


class RequestFormatter(logging.Formatter):
    """Formatter that injects request context fields into every record."""

    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
            record.request_id = getattr(g, "request_id", "-")
            record.method = request.method
        else:
            record.url = "-"
            record.remote_addr = "-"
            record.request_id = "-"
            record.method = "-"
        return super().format(record)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def configure_logging(app):
    """Configure production logging with rotating files and a security channel."""

    # ── Inject request-ID into every request ──────────────────────────────
    @app.before_request
    def _assign_request_id():
        g.request_id = str(uuid.uuid4())

    if app.debug or app.testing:
        # Development: basic console logging is sufficient
        return

    # ── Vercel / read-only filesystem ─────────────────────────────────────
    if os.environ.get("VERCEL") == "1":
        import sys
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(
            RequestFormatter(
                "[%(asctime)s] [%(request_id)s] %(levelname)s %(remote_addr)s"
                " %(method)s %(url)s — %(message)s"
            )
        )
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("TrackIT Management System startup (Vercel Mode)")
        return

    # ── Create log directory ───────────────────────────────────────────────
    log_dir = os.environ.get("LOG_DIR", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    _fmt_request = RequestFormatter(
        "[%(asctime)s] [%(request_id)s] %(remote_addr)s %(method)s %(url)s\n"
        "%(levelname)s in %(module)s: %(message)s"
    )
    _fmt_plain = logging.Formatter(
        "[%(asctime)s] [%(request_id)s] %(levelname)s: %(message)s"
        " [in %(pathname)s:%(lineno)d]"
    )

    # ── General application log (INFO+) ───────────────────────────────────
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "trackit.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
    )
    file_handler.setFormatter(_fmt_request)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    # ── Error log (ERROR+) ────────────────────────────────────────────────
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "errors.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=20,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(_fmt_plain)
    app.logger.addHandler(error_handler)

    # ── Security log (WARNING+ on the 'security' logger) ─────────────────
    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.WARNING)
    security_handler = RotatingFileHandler(
        os.path.join(log_dir, "security.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=30,  # Keep more rotation copies for audit trail
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s: %(message)s"
        )
    )
    security_logger.addHandler(security_handler)
    # Propagate to root so it also appears in trackit.log
    security_logger.propagate = True

    app.logger.setLevel(logging.INFO)
    app.logger.info("TrackIT Management System startup")


def log_security_event(event: str, **kwargs) -> None:
    """
    Convenience function to write a structured entry to security.log.

    Usage:
        log_security_event("LOGIN_FAILED", ip=request.remote_addr, email="x@y.com")
    """
    security_logger = logging.getLogger("security")
    details = " ".join(f"{k}={v}" for k, v in kwargs.items())
    security_logger.warning("[%s] %s", event, details)
