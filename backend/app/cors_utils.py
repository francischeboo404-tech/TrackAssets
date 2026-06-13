"""Shared CORS helpers for cross-origin Vercel → Render deployments."""

from __future__ import annotations

import re
from typing import Iterable

from flask import current_app, make_response

VERCEL_ORIGIN_RE = re.compile(r"^https://[\w.-]+\.vercel\.app$", re.IGNORECASE)

DEFAULT_ALLOW_HEADERS = (
    "Content-Type, Authorization, X-Requested-With, X-CSRF-TOKEN, Accept"
)
DEFAULT_ALLOW_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"


def configured_origins() -> list[str]:
    raw = current_app.config.get("CORS_ORIGINS", [])
    if isinstance(raw, str):
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [o for o in raw if isinstance(o, str) and o.strip()]


def is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return True
    if VERCEL_ORIGIN_RE.match(origin):
        return True
    for allowed in configured_origins():
        if origin == allowed or origin.rstrip("/") == allowed.rstrip("/"):
            return True
    return False


def _response(body="", status: int = 200):
    """Build a response (Flask 3+ does not accept status as a second arg to make_response)."""
    resp = make_response(body)
    resp.status_code = status
    return resp


def apply_cors_headers(response, origin: str | None) -> None:
    if origin and is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers.setdefault(
        "Access-Control-Allow-Methods", DEFAULT_ALLOW_METHODS
    )
    response.headers.setdefault(
        "Access-Control-Allow-Headers", DEFAULT_ALLOW_HEADERS
    )
    response.headers.setdefault("Access-Control-Max-Age", "3600")
    response.headers.add("Vary", "Origin")


def preflight_response(methods: Iterable[str] | None = None):
    from flask import request

    origin = request.headers.get("Origin")
    if origin and not is_allowed_origin(origin):
        body = {"success": False, "message": "Origin not allowed", "status_code": 403}
        resp = _response(body, 403)
        apply_cors_headers(resp, origin)
        return resp

    resp = _response("", 204)
    if methods:
        resp.headers["Access-Control-Allow-Methods"] = ", ".join(methods)
    apply_cors_headers(resp, origin)
    return resp
