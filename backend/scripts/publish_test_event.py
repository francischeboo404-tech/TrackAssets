import requests
import os

for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")

# use admin login to publish a simple event via an existing endpoint
login = requests.post('http://localhost:5000/api/auth/login', json={'email':'admin@techcorp.com','password':'Admin123!'}, timeout=10)
login.raise_for_status()
token = login.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

# Try to hit inventory create or a generic test endpoint if available
# POST to the correct inventory create endpoint
try:
    r = requests.post(
        'http://localhost:5000/api/inventory',
        json={'name': 'test-sse-item', 'unit_price': 1.0, 'quantity': 1},
        headers=headers,
        timeout=10,
    )
    print('publish status', r.status_code)
    try:
        print('publish body', r.json())
    except Exception:
        print('publish body (text):', r.text[:1000])
except Exception as e:
    print('publish error:', repr(e))
