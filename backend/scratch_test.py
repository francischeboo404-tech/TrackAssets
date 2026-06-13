import requests
import json

base_url = 'http://localhost:5000/api'

# 1. Login
login_data = {
    'email': 'admin@techcorp.com',
    'password': 'Admin123!'
}
r = requests.post(f'{base_url}/auth/login', json=login_data)
if r.status_code != 200 or not r.json().get('success', True):
    print("Login failed:", r.text)
    exit(1)

access_token_cookie = r.cookies.get('access_token_cookie')
csrf_token = r.cookies.get('csrf_access_token')

cookies = {
    'access_token_cookie': access_token_cookie
}
headers = {
    'Content-Type': 'application/json',
    'X-CSRF-TOKEN': csrf_token
}

# Test filtering
r_all = requests.get(f'{base_url}/assets', headers=headers, cookies=cookies)
print("All Assets:", len(r_all.json().get('assets', [])))

r_app = requests.get(f'{base_url}/assets?status=approved', headers=headers, cookies=cookies)
print("Approved Assets:", len(r_app.json().get('assets', [])))

r_in_use = requests.get(f'{base_url}/assets?status=in_use', headers=headers, cookies=cookies)
print("In Use Assets:", len(r_in_use.json().get('assets', [])))

r_search = requests.get(f'{base_url}/assets?search=TECH', headers=headers, cookies=cookies)
print("Search TECH:", len(r_search.json().get('assets', [])))
