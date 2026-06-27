import urllib.request
import json

# 1. Login
req = urllib.request.Request('http://localhost:5000/api/auth/login', 
                             data=json.dumps({"email": "depthead@techcorp.com", "password": "password"}).encode('utf-8'),
                             headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req)
    cookies = resp.headers.get_all('Set-Cookie')
    cookie_str = "; ".join([c.split(';')[0] for c in cookies]) if cookies else ""
    
    # 2. Test Purchase Orders
    req2 = urllib.request.Request('http://localhost:5000/api/procurement/purchase-orders', headers={'Cookie': cookie_str})
    try:
        resp2 = urllib.request.urlopen(req2)
        print("PO Status: 200")
    except urllib.error.HTTPError as e:
        print(f"PO Status: {e.code}")
        print(e.read().decode('utf-8'))
        
    # 3. Test Goods Receipts
    req3 = urllib.request.Request('http://localhost:5000/api/receiving/goods-receipts', headers={'Cookie': cookie_str})
    try:
        resp3 = urllib.request.urlopen(req3)
        print("GR Status: 200")
    except urllib.error.HTTPError as e:
        print(f"GR Status: {e.code}")
        print(e.read().decode('utf-8'))
        
except Exception as e:
    print(f"Login failed: {e}")
