import requests

BASE_URL = "http://127.0.0.1:5000/api"
TOKEN = None

def login():
    global TOKEN
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@techcorp.com", "password": "password123"})
    if res.status_code == 200:
        TOKEN = res.json()["token"]
        print("Logged in successfully.")
    else:
        print(f"Login failed: {res.text}")

def test_asset_creation():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # Need to get a department ID first
    res = requests.get(f"{BASE_URL}/departments", headers=headers)
    dept_id = res.json()["departments"][0]["id"] if res.json().get("departments") else 1
    
    payload = {
        "name": "Test Debug Asset",
        "type": "Hardware",
        "department_id": dept_id,
        "purchase_date": "2023-01-01",
        "purchase_value": 1000.0,
        "useful_life": 5
    }
    
    res = requests.post(f"{BASE_URL}/assets", json=payload, headers=headers)
    print("Asset Creation:", res.status_code, res.text)
    if res.status_code == 201:
        return res.json()["asset"]["id"]
    return None

def test_transfer(asset_id):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    res = requests.get(f"{BASE_URL}/departments", headers=headers)
    depts = res.json().get("departments", [])
    if len(depts) < 2:
        dept_id = depts[0]["id"]
    else:
        dept_id = depts[1]["id"]
        
    payload = {
        "asset_id": asset_id,
        "new_department_id": dept_id,
        "to_warehouse_id": 1,
        "comment": "Test transfer"
    }
    
    res = requests.post(f"{BASE_URL}/transfers/request", json=payload, headers=headers)
    print("Transfer Request:", res.status_code, res.text)
    if res.status_code == 201:
        req_id = res.json()["request_id"]
        # Approve
        res = requests.post(f"{BASE_URL}/transfers/requests/{req_id}/approve", headers=headers)
        print("Transfer Approve:", res.status_code, res.text)
        # Dispatch
        res = requests.post(f"{BASE_URL}/transfers/requests/{req_id}/dispatch", headers=headers)
        print("Transfer Dispatch:", res.status_code, res.text)
        # Receive
        res = requests.post(f"{BASE_URL}/transfers/requests/{req_id}/receive", headers=headers)
        print("Transfer Receive:", res.status_code, res.text)

if __name__ == "__main__":
    login()
    if TOKEN:
        asset_id = test_asset_creation()
        if asset_id:
            test_transfer(asset_id)
