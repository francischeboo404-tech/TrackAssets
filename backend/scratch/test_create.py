import requests
import json

base_url = "http://localhost:5000/api"

session = requests.Session()

# 1. Login
login_data = {
    "email": "admin@techcorp.com",
    "password": "Admin123!"
}
r = session.post(f"{base_url}/auth/login", json=login_data)
if r.status_code != 200:
    print("Login failed:", r.text)
    exit(1)

print("Login successful.")

headers = {"Content-Type": "application/json"}
csrf_token = session.cookies.get("csrf_access_token")
if csrf_token:
    headers["X-CSRF-TOKEN"] = csrf_token

session.headers.update(headers)

# 2. Test Asset Creation
asset_data = {
    "name": "Test Laptop X1",
    "type": "Hardware",
    "asset_code": "AST-12345",
    "purchase_date": "2024-01-01",
    "purchase_value": 1200,
    "useful_life": 3,
    "department_id": 1,
    "serial_number": "",
    "location": ""
}
r = session.post(f"{base_url}/assets", json=asset_data)
print("Asset Create Response:", r.status_code, r.text)

# 3. Test Inventory Creation
inventory_data = {
    "name": "Test Mouse",
    "sku": "MOUSE-01",
    "unit_price": 20.0,
    "reorder_level": 5,
    "description": "Test mouse",
    "unit": "pcs"
}
r = session.post(f"{base_url}/inventory", json=inventory_data)
print("Inventory Create Response:", r.status_code, r.text)
