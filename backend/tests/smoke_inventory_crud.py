import os
import requests
import json

BASE = os.environ.get("TRACKIT_BASE_URL", "http://localhost:5000")
ADMIN_EMAIL = os.environ.get("TRACKIT_SMOKE_ADMIN", "admin@techcorp.com")
ADMIN_PASSWORD = os.environ.get("TRACKIT_SMOKE_PASSWORD", "changeme")


def login():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    r.raise_for_status()
    data = r.json()
    return data["access_token"]


def test_inventory_crud_flow():
    token = login()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create an item
    payload = {
        "name": "SMOKE_ITEM",
        "sku": "SMOKE-001",
        "unit": "pcs",
        "reorder_level": 5,
    }
    r = requests.post(f"{BASE}/api/inventory", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    item = r.json()
    item_id = item["id"]

    # Update item
    r = requests.put(f"{BASE}/api/inventory/{item_id}", headers=headers, json={"name": "SMOKE_ITEM_UPDATED"})
    assert r.status_code == 200, r.text

    # Add stock IN
    r = requests.post(
        f"{BASE}/api/inventory/{item_id}/stock",
        headers=headers,
        json={"type": "IN", "quantity": 10, "reference": "smoke-test"},
    )
    assert r.status_code == 200, r.text

    # Get item and check stock
    r = requests.get(f"{BASE}/api/inventory/{item_id}", headers=headers)
    assert r.status_code == 200, r.text
    item = r.json()
    assert item.get("quantity", 0) >= 10

    # Soft delete
    r = requests.delete(f"{BASE}/api/inventory/{item_id}", headers=headers)
    assert r.status_code == 200, r.text

    # Restore
    r = requests.post(f"{BASE}/api/inventory/{item_id}/restore", headers=headers)
    assert r.status_code == 200, r.text

    # Cleanup: permanently delete if endpoint exists
    # Note: Not all environments expose hard-delete; ignore 404s
    requests.delete(f"{BASE}/api/inventory/{item_id}/permanent", headers=headers)
