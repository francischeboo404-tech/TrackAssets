import hmac
import hashlib
import sys

# Implementation from app/utils/security.py
def generate_signed_qr(payload: str, secret: str) -> str:
    """Generate a HMAC-signed QR string to prevent tampering."""
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:12]
    return f"{payload}:{signature}"

def verify_signed_qr(signed_data: str, secret: str) -> str:
    """Verify the signature of a QR string and return the original payload."""
    if ":" not in signed_data:
        return None
        
    payload, signature = signed_data.rsplit(":", 1)
    expected = generate_signed_qr(payload, secret)
    
    if signed_data == expected:
        return payload
    return None

# Test Suite
def run_tests():
    secret = "test-secret-key-12345"
    payload = "asset:1:ASSET-001"
    
    print(f"Testing with payload: {payload}")
    signed = generate_signed_qr(payload, secret)
    print(f"Signed QR: {signed}")
    
    # 1. Valid verification
    verified = verify_signed_qr(signed, secret)
    if verified == payload:
        print("SUCCESS: Valid signature verified.")
    else:
        print(f"FAILURE: Valid signature failed verification. Got: {verified}")
        return False
        
    # 2. Tampering detection
    tampered = signed[:-1] + ("0" if signed[-1] != "0" else "1")
    print(f"Testing tampered: {tampered}")
    if verify_signed_qr(tampered, secret) is None:
        print("SUCCESS: Tampering detected.")
    else:
        print("FAILURE: Tampering allowed!")
        return False
        
    # 3. Wrong secret
    if verify_signed_qr(signed, "wrong-secret") is None:
        print("SUCCESS: Wrong secret rejected.")
    else:
        print("FAILURE: Wrong secret accepted!")
        return False
        
    return True

if __name__ == "__main__":
    if run_tests():
        print("\nSEC-01 LOGIC VERIFIED SUCCESSFULLY")
    else:
        sys.exit(1)
