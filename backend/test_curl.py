import requests
from dotenv import load_dotenv
load_dotenv()
from app import create_app
from flask_jwt_extended import create_access_token

app = create_app('development')
with app.app_context():
    token = create_access_token('21', additional_claims={'organisation_id': 1, 'role': 'admin'})

res = requests.get('http://localhost:5000/api/inventory', headers={'Authorization': f'Bearer {token}'})
print(res.json())
