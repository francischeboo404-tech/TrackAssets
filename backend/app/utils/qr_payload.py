"""
Structured, signed QR payloads for assets and inventory.

Format (before signing):
  v1:{entity_type}:{organisation_id}:{entity_id}:{exp_unix}

Signed value: {payload}:{hmac12}
Scan URL: {TRACKING_PUBLIC_URL}?data={signed_value}
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from flask import current_app

from app.utils.security import generate_signed_qr, verify_signed_qr

PAYLOAD_VERSION = "v1"
DEFAULT_TTL_DAYS = 365


def _extract_signed_token(qr_data: str) -> str:
    """Normalize scanner input (URL, query param, or raw token)."""
    raw = (qr_data or "").strip()
    if "?data=" in raw:
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(raw)
        params = parse_qs(parsed.query)
        if params.get("data"):
            return params["data"][0]
    return raw


def build_inner_payload(
    entity_type: str,
    organisation_id: int,
    entity_id: int,
    ttl_days: Optional[int] = None,
) -> str:
    ttl = ttl_days or current_app.config.get("QR_PAYLOAD_TTL_DAYS", DEFAULT_TTL_DAYS)
    exp = int((datetime.utcnow() + timedelta(days=ttl)).timestamp())
    return f"{PAYLOAD_VERSION}:{entity_type}:{organisation_id}:{entity_id}:{exp}"


def build_signed_token(
    entity_type: str,
    organisation_id: int,
    entity_id: int,
    ttl_days: Optional[int] = None,
) -> str:
    inner = build_inner_payload(entity_type, organisation_id, entity_id, ttl_days)
    return generate_signed_qr(inner)


def build_scan_url(signed_token: str) -> str:
    base = current_app.config.get(
        "TRACKING_PUBLIC_URL", "http://localhost:5173/tracking"
    ).rstrip("/")
    return f"{base}?data={signed_token}"


def parse_verified_payload(signed_token: str) -> Tuple[str, int, int, int]:
    """
    Verify signature, expiry, and return (entity_type, org_id, entity_id, exp).
    Raises ValueError on tampering or expiry.
    """
    token = _extract_signed_token(signed_token)
    verified = verify_signed_qr(token)
    if not verified:
        raise ValueError("Invalid or tampered QR signature")

    parts = verified.split(":")
    if len(parts) != 5 or parts[0] != PAYLOAD_VERSION:
        raise ValueError("Unsupported QR payload version")

    entity_type, org_s, entity_s, exp_s = parts[1], parts[2], parts[3], parts[4]
    if entity_type not in ("asset", "inventory", "inventory_instance"):
        raise ValueError("Invalid entity type in QR payload")

    exp = int(exp_s)
    if datetime.utcnow().timestamp() > exp:
        raise ValueError("QR code has expired")

    return entity_type, int(org_s), int(entity_s), exp


def legacy_asset_code_payload(org_id: int, asset_code: str) -> str:
    """Backward-compatible inner payload used at asset creation."""
    return f"asset:{org_id}:{asset_code}"
