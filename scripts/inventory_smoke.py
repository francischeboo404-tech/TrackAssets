"""Smoke test for inventory endpoints using Flask test client."""
import os
import sys

from datetime import datetime

from flask_jwt_extended import create_access_token

# Ensure project root is on sys.path when running the script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db


def run():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()

        from app.models import organization, user

        org = organization.Organization(name="SmokeOrg", code="SMK", description="Smoke test org")
        db.session.add(org)
        db.session.commit()

        dept = organization.Department(name="Store", code="STORE", organisation_id=org.id)
        db.session.add(dept)
        db.session.commit()

        test_user = user.User(username="smoke", email="smoke@test.local", organisation_id=org.id, role="admin")
        test_user.set_password("Password123")
        db.session.add(test_user)
        db.session.commit()

        token = create_access_token(identity=str(test_user.id), additional_claims={"organisation_id": org.id, "role": test_user.role, "username": test_user.username})

        client = app.test_client()

        # Create inventory item
        payload = {
            "name": "Paper",
            "sku": "PAPER-01",
            "description": "A4 paper",
            "quantity": 0,
            "reorder_level": 10,
            "unit_price": 2.5,
            "unit": "ream",
        }

        resp = client.post("/api/inventory", json=payload, headers={"Authorization": f"Bearer {token}"})
        print("CREATE status:", resp.status_code, resp.get_json())
        item_id = resp.get_json().get("item_id")

        # Stock IN
        resp_in = client.post(f"/api/inventory/{item_id}/stock", json={"type": "IN", "quantity": 20}, headers={"Authorization": f"Bearer {token}"})
        print("STOCK IN status:", resp_in.status_code, resp_in.get_json())

        # Stock OUT
        resp_out = client.post(f"/api/inventory/{item_id}/stock", json={"type": "OUT", "quantity": 20}, headers={"Authorization": f"Bearer {token}"})
        print("STOCK OUT status:", resp_out.status_code, resp_out.get_json())

        # Delete (should succeed since quantity is 0)
        resp_del = client.delete(f"/api/inventory/{item_id}", headers={"Authorization": f"Bearer {token}"})
        print("DELETE status:", resp_del.status_code, resp_del.get_json())


if __name__ == "__main__":
    run()
