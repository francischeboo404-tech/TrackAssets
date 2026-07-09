#!/usr/bin/env python3
"""Debug script to test goods-receipts POST endpoint"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Step 1: Login to get token
print("Step 1: Logging in...")
login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
    "email": "admin@test.com",
    "password": "Admin@123456"
})
print(f"Login status: {login_response.status_code}")
if login_response.status_code != 200:
    print(f"Login error: {login_response.json()}")
    exit(1)

login_data = login_response.json()
token = login_data.get('access_token')
if not token:
    print(f"No token received: {login_data}")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}
print(f"Got token: {token[:20]}...")

# Step 2: Get list of purchase orders
print("\nStep 2: Fetching purchase orders...")
po_response = requests.get(f"{BASE_URL}/api/procurement/purchase-orders", headers=headers)
print(f"PO fetch status: {po_response.status_code}")
if po_response.status_code != 200:
    print(f"PO fetch error: {po_response.json()}")
    exit(1)

po_data = po_response.json()
purchase_orders = po_data.get('purchase_orders', [])
print(f"Found {len(purchase_orders)} purchase orders")

if not purchase_orders:
    print("No purchase orders found - cannot test GRN creation")
    exit(1)

# Find an approved PO
approved_po = None
for po in purchase_orders:
    if po['status'] == 'approved':
        approved_po = po
        break

if not approved_po:
    print(f"No approved POs found. Available statuses:")
    for po in purchase_orders[:5]:
        print(f"  - PO {po['id']}: {po.get('po_number', 'N/A')} - {po['status']}")
    print("\nTrying first PO anyway...")
    approved_po = purchase_orders[0]

po_id = approved_po['id']
print(f"Using PO {po_id} (status: {approved_po['status']})")

# Get PO details to see items
print(f"\nStep 3: Getting PO details...")
po_detail_response = requests.get(f"{BASE_URL}/api/procurement/purchase-orders/{po_id}", headers=headers)
print(f"PO detail status: {po_detail_response.status_code}")
if po_detail_response.status_code != 200:
    print(f"PO detail error: {po_detail_response.json()}")
    exit(1)

po_detail = po_detail_response.json()
print(f"PO details: {json.dumps(po_detail, indent=2, default=str)}")

# Get inventory items
print(f"\nStep 4: Getting inventory items...")
inv_response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
print(f"Inventory status: {inv_response.status_code}")
if inv_response.status_code != 200:
    print(f"Inventory error: {inv_response.json()}")
    exit(1)

inv_data = inv_response.json()
inventory = inv_data.get('inventory', [])
print(f"Found {len(inventory)} inventory items")

# Step 5: Try creating a GRN with valid payload
print(f"\nStep 5: Creating GRN...")

# Use first item from PO if available, otherwise first inventory item
item_id = None
if po_detail.get('items') and len(po_detail['items']) > 0:
    item_id = po_detail['items'][0]['item_id']
    print(f"Using item from PO: {item_id}")
elif inventory and len(inventory) > 0:
    item_id = inventory[0]['id']
    print(f"Using inventory item: {item_id}")
else:
    print("No items available!")
    exit(1)

grn_payload = {
    "po_id": po_id,
    "items": [
        {
            "item_id": item_id,
            "quantity_received": 5,
            "unit_cost": 100.00,
            "expiry_date": None
        }
    ],
    "invoice_number": "INV-TEST-001",
    "delivery_note_number": "DN-TEST-001"
}

print(f"Payload: {json.dumps(grn_payload, indent=2)}")

grn_response = requests.post(f"{BASE_URL}/api/receiving/goods-receipts", 
    headers=headers, 
    json=grn_payload
)
print(f"\nGRN creation status: {grn_response.status_code}")
print(f"Response: {json.dumps(grn_response.json(), indent=2)}")

if grn_response.status_code != 201:
    print("\n❌ GRN creation failed!")
    error_data = grn_response.json()
    print(f"Error: {error_data.get('message', 'Unknown error')}")
    if 'errors' in error_data:
        for e in error_data['errors']:
            print(f"  - {e}")
else:
    print("\n✅ GRN created successfully!")
