import json
from urllib import request, error

url = 'http://localhost:5000/api/auth/login'
payload = {'email': 'admin@techcorp.com', 'password': 'Admin123!'}
data = json.dumps(payload).encode('utf-8')
req = request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with request.urlopen(req, timeout=5) as r:
        body = r.read().decode('utf-8')
        print('status:', r.status)
        print('body:', body[:1000])
except error.HTTPError as e:
    print('http error:', e.code, e.read().decode('utf-8')[:1000])
except Exception as e:
    print('error:', e)
