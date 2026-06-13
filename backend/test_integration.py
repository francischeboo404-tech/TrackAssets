import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"
TOKEN = None # Need to login first

def login():
    global TOKEN
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@novalite.local", "password": "password123"})
    if res.status_code == 200:
        TOKEN = res.json()["token"]
        print("Logged in successfully.")
    else:
        print(f"Login failed: {res.text}")

def test_inventory_scan():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # Let's get an inventory item first
    res = requests.get(f"{BASE_URL}/inventory", headers=headers)
    items = res.json().get("inventory", [])
    if not items:
        print("No inventory items found. Skipping scan test.")
        return
        
    item = items[0]
    sku = item["sku"]
    old_qty = item["quantity"]
    
    print(f"Testing Scan IN for SKU: {sku} (Current QTY: {old_qty})")
    
    scan_payload = {
        "qr_data": sku,
        "action_type": "CHECK_IN",
        "notes": "Test integration check-in",
        "warehouse_id": 1
    }
    
    res = requests.post(f"{BASE_URL}/tracking/scan", json=scan_payload, headers=headers)
    if res.status_code == 200:
        print("Scan IN successful:", res.json())
        
        # Verify stock increment
        res = requests.get(f"{BASE_URL}/inventory/{item['id']}", headers=headers)
        new_qty = res.json()["quantity"]
        print(f"New QTY: {new_qty} (Expected: {old_qty + 1})")
        if new_qty == old_qty + 1:
            print("SUCCESS: Stock increment verified!")
        else:
            print("ERROR: Stock increment failed.")
    else:
        print(f"Scan IN failed: {res.text}")

if __name__ == "__main__":
    login()
    if TOKEN:
        test_inventory_scan()
