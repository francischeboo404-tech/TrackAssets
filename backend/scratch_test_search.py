import requests

base_url = "http://localhost:5000/api"

session = requests.Session()

# Login
resp = session.post(f"{base_url}/auth/login", json={"email": "admin@trackit.com", "password": "admin"})
if resp.status_code != 200:
    print("Login failed:", resp.json())
else:
    print("Login successful")
    
    # Get CSRF token from cookies
    csrf_token = session.cookies.get("csrf_access_token")
    headers = {"X-CSRF-TOKEN": csrf_token}
    
    # Search
    search_resp = session.get(f"{base_url}/search/?q=human%20resource", headers=headers)
    print("Search status:", search_resp.status_code)
    print("Search response:", search_resp.json())
