import hmac
import hashlib
from flask import current_app


def generate_signed_qr(payload: str) -> str:
    """Generate a HMAC-signed QR string to prevent tampering."""
    secret = current_app.config.get(
        "SECRET_KEY", "default-dev-secret"
    ).encode()
    signature = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()[
        :12
    ]
    return f"{payload}:{signature}"


def verify_signed_qr(signed_data: str) -> str:
    """Verify the signature of a QR string and return the original payload."""
    if ":" not in signed_data:
        return None

    payload, signature = signed_data.rsplit(":", 1)
    expected = generate_signed_qr(payload)

    if signed_data == expected:
        return payload
    return None
