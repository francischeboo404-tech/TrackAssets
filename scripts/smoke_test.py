"""
Non-destructive smoke tests for TrackIT backend/frontend.

Usage:
  TARGET_BASE=https://trackit-uxil.onrender.com FRONTEND_URL=https://track-it-gamma-blue.vercel.app python scripts/smoke_test.py

This script checks:
- GET /health
- OPTIONS preflight for /api/auth/register-org
- GET /api/auth/me (expect 401 or success:false)
- GET frontend root URL

Exit code 0 on all checks passing, non-zero otherwise.
"""
import os
import sys
import time
import json
import requests

TARGET_BASE = os.environ.get("TARGET_BASE", "https://trackit-uxil.onrender.com")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://track-it-gamma-blue.vercel.app")
TIMEOUT = 15

errors = []

def check_health():
    url = f"{TARGET_BASE}/health"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        print('[health] GET', url, 'status=', r.status_code)
        if r.status_code not in (200, 503):
            errors.append(('health', r.status_code, r.text))
    except Exception as e:
        errors.append(('health', 'exception', str(e)))


def check_options_register():
    url = f"{TARGET_BASE}/api/auth/register-org"
    headers = {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'POST',
    }
    try:
        r = requests.options(url, headers=headers, timeout=TIMEOUT)
        print('[options] OPTIONS', url, 'status=', r.status_code)
        acao = r.headers.get('Access-Control-Allow-Origin')
        allow = r.headers.get('Access-Control-Allow-Methods')
        print('  headers:', 'ACAO=', acao, 'Allow=', allow)
        if r.status_code != 200:
            errors.append(('options_register', r.status_code, r.text))
    except Exception as e:
        errors.append(('options_register', 'exception', str(e)))


def check_auth_me():
    url = f"{TARGET_BASE}/api/auth/me"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        print('[auth/me] GET', url, 'status=', r.status_code)
        try:
            data = r.json()
        except Exception:
            data = r.text
        print('  resp:', data)
        # Accept 200 with {'success': False, 'status_code':401} OR 401/200
        if isinstance(data, dict) and data.get('success') is False:
            # ok as unauthenticated
            pass
        elif r.status_code in (200, 401):
            pass
        else:
            errors.append(('auth_me', r.status_code, data))
    except Exception as e:
        errors.append(('auth_me', 'exception', str(e)))


def check_frontend_root():
    url = FRONTEND_URL
    try:
        r = requests.get(url, timeout=TIMEOUT)
        print('[frontend] GET', url, 'status=', r.status_code)
        if r.status_code != 200:
            errors.append(('frontend_root', r.status_code, r.text[:200]))
    except Exception as e:
        errors.append(('frontend_root', 'exception', str(e)))


def main():
    print('Target base:', TARGET_BASE)
    print('Frontend URL:', FRONTEND_URL)

    check_health()
    time.sleep(0.5)
    check_options_register()
    time.sleep(0.5)
    check_auth_me()
    time.sleep(0.5)
    check_frontend_root()

    if errors:
        print('\nSMOKE TESTS FAILED:')
        for e in errors:
            print('-', e)
        sys.exit(2)
    else:
        print('\nSMOKE TESTS PASSED')
        sys.exit(0)

if __name__ == '__main__':
    main()
