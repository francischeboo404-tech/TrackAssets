import os

# Ensure local requests don't get hijacked by system proxies or HTTPS upgrades
for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")

import requests
import sys

try:
    login = requests.post(
        'http://localhost:5000/api/auth/login',
        json={'email': 'admin@techcorp.com', 'password': 'Admin123!'},
        timeout=10,
    )
    print('login status', login.status_code)
    login.raise_for_status()
    token = login.json().get('access_token')
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'text/event-stream',
    }

    # Start a streaming GET and wait for the first SSE data line.
    # Use a reasonable read timeout so the probe doesn't hang forever if no events are produced.
    try:
        r = requests.get(
            'http://localhost:5000/api/analytics/stream',
            headers=headers,
            stream=True,
            timeout=(5, 30),
        )
    except Exception as e:
        print('error during stream request (connect):', repr(e))
        r = None

    if not r:
        print('no stream response object (connect failed)')
        sys.exit(1)

    print('stream status', r.status_code)
    print('content-type:', r.headers.get('content-type'))

    if r.status_code != 200:
        # Non-streaming response (likely JSON error)
        print('body snippet:', r.text[:4000])
        sys.exit(1)

    # Iterate lines until we get a data: line or until timeout
    import time
    start = time.time()
    timeout_seconds = 20
    try:
        for line in r.iter_lines(decode_unicode=True):
            if line:
                # SSE lines often come as 'data: {...}'
                print('line:', line)
                if line.startswith('data:'):
                    print('received event:', line[len('data:'):].strip())
                    break
            if time.time() - start > timeout_seconds:
                print('timed out waiting for SSE data')
                break
    except Exception as e:
        print('error while streaming:', repr(e))
except Exception as e:
    print('error during request:', repr(e))
