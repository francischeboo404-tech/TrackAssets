"""HTTP smoke test: register org, login, create inventory and asset via HTTP.

Run this after starting backend (default http://127.0.0.1:5000).
"""
import json
import time
from datetime import date

import requests

BASE = "http://127.0.0.1:5000"


def run():
    s = requests.Session()

    # 1) Register org + admin
    reg_payload = {
        "org_name": "SmokeOrgHTTP",
        "org_code": "SMOKEHTTP",
        "org_description": "Smoke test org",
        "admin_username": "smoke_http_admin",
        "admin_email": "smoke_http@example.com",
        "admin_password": "Admin123!",
    }

    r = s.post(f"{BASE}/api/auth/register-org", json=reg_payload)
    print("register-org", r.status_code, r.text)
    if r.status_code not in (200, 201):
        print("Register failed, aborting")
        return

    # 2) Login
    login_payload = {"email": reg_payload["admin_email"], "password": reg_payload["admin_password"]}
    r = s.post(f"{BASE}/api/auth/login", json=login_payload)
    print("login", r.status_code, r.text)
    if r.status_code not in (200,):
        print("Login failed, aborting")
        return

    # Give server a moment
    time.sleep(0.2)

    # 3) Create inventory
    # Flask-JWT-Extended sets CSRF cookie; fetch it and send in header for POSTs
    csrf_token = s.cookies.get('csrf_access_token') or s.cookies.get('csrf_refresh_token')
    headers = {}
    if csrf_token:
        headers['X-CSRF-TOKEN'] = csrf_token

    inv_payload = {
        "name": "HTTP-SMOKE-ITEM",
        "sku": "HTTPSMOKE-001",
        "unit_price": 2.5,
        "unit": "pcs",
        "reorder_level": 3,
    }
    r = s.post(f"{BASE}/api/inventory", json=inv_payload, headers=headers)
    print("create inventory", r.status_code, r.text)

    # 4) Create asset (need department id). Fetch departments or create via ORM endpoint if exists.
    # Try to get departments list
    r_depts = s.get(f"{BASE}/api/departments")
    dept_id = None
    if r_depts.status_code == 200:
        try:
            data = r_depts.json()
            if isinstance(data, dict) and "departments" in data and data["departments"]:
                dept_id = data["departments"][0].get("id")
        except Exception:
            pass

    # If no department, create one via /api/departments if available
    if not dept_id:
        dept_payload = {"name": "IT", "code": "IT"}
        r = s.post(f"{BASE}/api/departments", json=dept_payload, headers=headers)
        print("create department", r.status_code, r.text)
        try:
            dept_id = r.json().get("department_id") or (r.json().get("id") if isinstance(r.json(), dict) else None)
        except Exception:
            dept_id = None

    asset_payload = {
        "name": "HTTP-SMOKE-ASSET",
        "type": "Laptop",
        "department_id": dept_id,
        "purchase_date": date.today().isoformat(),
        "purchase_value": 999.0,
        "useful_life": 3,
    }

    r = s.post(f"{BASE}/api/assets", json=asset_payload, headers=headers)
    print("create asset", r.status_code, r.text)


if __name__ == "__main__":
    run()
