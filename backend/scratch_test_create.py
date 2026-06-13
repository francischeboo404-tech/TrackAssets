import sys
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.services.asset_service import AssetService
from app.services.inventory_service import InventoryService
from app.models import organization, user
from datetime import datetime

app = create_app('development')

with app.app_context():
    try:
        # Create a dummy org and user if not exists
        org = organization.Organization.query.first()
        if not org:
            org = organization.Organization(name="Test Org", code="TST")
            db.session.add(org)
            db.session.commit()
            print(f"Created org {org.id}")
        
        dept = organization.Department.query.first()
        if not dept:
            dept = organization.Department(name="Test Dept", code="TD", organisation_id=org.id)
            db.session.add(dept)
            db.session.commit()
            print(f"Created dept {dept.id}")
            
        print("Initial DB counts:")
        print("Assets:", db.session.execute("SELECT count(*) FROM assets").scalar())
        print("Inventory:", db.session.execute("SELECT count(*) FROM inventory_items").scalar())

        # Test Asset creation
        asset_svc = AssetService()
        data = {
            "name": "Test Asset",
            "type": "Hardware",
            "purchase_date": datetime.utcnow().date(),
            "purchase_value": 1000.0,
            "useful_life": 5,
            "department_id": dept.id,
            "asset_code": "TST-001"
        }
        print("Calling create_asset...")
        new_asset = asset_svc.create_asset(org.id, data)
        print(f"Success! Asset ID: {new_asset.id}")
        
        print("Final DB counts:")
        print("Assets:", db.session.execute("SELECT count(*) FROM assets").scalar())
        print("Inventory:", db.session.execute("SELECT count(*) FROM inventory_items").scalar())
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
