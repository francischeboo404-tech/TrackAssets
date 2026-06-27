import os
# Force sqlite db to relative trackit_dev.db
os.environ["DATABASE_URL"] = "sqlite:///trackit_dev.db"

from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token
import traceback

app = create_app('development')
with app.app_context():
    user = User.query.filter_by(role='admin').first()
    if not user:
        print("No admin user found")
        exit(1)
        
    token = create_access_token(identity=str(user.id))
    
    client = app.test_client()
    
    try:
        res = client.post('/api/transfers/request', json={
            "new_department_id": 1,
            "new_location": "Test",
            "item_type": "asset",
            "asset_id": 1,
            "comment": "Testing"
        }, headers={"Authorization": f"Bearer {token}"})
        print(f"Status: {res.status_code}")
        print(f"Response: {res.get_json() or res.data}")
    except Exception as e:
        print("EXCEPTION RAISED:")
        traceback.print_exc()
