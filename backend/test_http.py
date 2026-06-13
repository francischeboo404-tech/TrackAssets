import requests
import json
from threading import Thread
import time

def run_app():
    from app import create_app
    app = create_app('testing')
    app.run(port=5000, use_reloader=False)

# Start app in background
t = Thread(target=run_app)
t.daemon = True
t.start()
time.sleep(3) # Wait for server to start

# 1. Test POST /api/inventory/
try:
    print("Testing POST /api/inventory/")
    r1 = requests.post("http://localhost:5000/api/inventory/", json={"name": "Test", "sku": "TEST-1", "unit_price": 10})
    print(f"Status: {r1.status_code}")
    print(f"Body: {r1.text[:200]}")
except Exception as e:
    print(e)

# 2. Test POST /api/inventory
try:
    print("Testing POST /api/inventory")
    r2 = requests.post("http://localhost:5000/api/inventory", json={"name": "Test", "sku": "TEST-2", "unit_price": 10})
    print(f"Status: {r2.status_code}")
    print(f"Body: {r2.text[:200]}")
except Exception as e:
    print(e)
