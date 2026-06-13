import json
import requests

BASE_URL = "http://localhost:5000/api"
LOGIN_URL = f"{BASE_URL}/auth/login"
SCAN_URL = f"{BASE_URL}/tracking/scan"

def test_qr_tracking():
    # 1. Login to get session
    session = requests.Session()
    login_data = {
        "email": "admin@novalite.com",  # Adjust to a real user in DB
        "password": "Password123!"
    }
    print(f"Logging in as {login_data['email']}...")
    resp = session.post(LOGIN_URL, json=login_data)
    if resp.status_code != 200:
        print(f"Login failed: {resp.json()}")
        return

    # 2. Get some asset to track
    # In a real test, we would have created an asset first.
    # Assuming org_id=1 and asset_code='AST-001'
    qr_data = "asset:1:AST-001"
    
    # 3. Simulate a scan
    scan_data = {
        "qr_data": qr_data,
        "action_type": "CHECK_IN",
        "notes": "Testing QR tracking system",
        "lat": 0.0,
        "lon": 0.0
    }
    
    print(f"Recording scan for {qr_data}...")
    resp = session.post(SCAN_URL, json=scan_data)
    
    print(f"Response status: {resp.status_code}")
    print(f"Response body: {json.dumps(resp.json(), indent=2)}")

if __name__ == "__main__":
    test_qr_tracking()
