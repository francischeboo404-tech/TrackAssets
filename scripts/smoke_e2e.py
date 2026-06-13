"""End-to-end smoke test using Flask test client.

Creates a test organization, department and admin user, issues a JWT,
then POSTs to the inventory and assets create endpoints and prints results.
"""
import json
import os
import sys
from datetime import date

# Ensure backend package is importable when running from workspace root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app import create_app, db
from app.models.organization import Organization, Department
from app.models.user import User
from flask_jwt_extended import create_access_token


def run_smoke():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["DEBUG"] = True

    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Smoke Org", code="SMOKEORG")
        db.session.add(org)
        db.session.commit()

        dept = Department(organisation_id=org.id, name="IT", code="IT")
        db.session.add(dept)
        db.session.commit()

        user = User(
            organisation_id=org.id,
            username="smoke_admin",
            email="smoke@example.com",
            role="admin",
        )
        # choose a password that satisfies complexity rules
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

        token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "organisation_id": org.id,
                "role": user.role,
                "username": user.username,
            },
        )

        client = app.test_client()

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Verify token and user context
        me_resp = client.get("/api/auth/me", headers=headers)
        print("Auth me status:", me_resp.status_code)
        try:
            print(me_resp.get_json())
        except Exception:
            print(me_resp.data)

        # Double-check that org and dept exist via ORM to rule out tenant isolation issues
        print("ORM org present:", Organization.query.get(org.id) is not None)
        print("ORM dept present:", Department.query.get(dept.id) is not None)

        # Create inventory item
        inv_payload = {
            "name": "SmokeItem",
            "sku": "SMOKE-001",
            "unit_price": 1.0,
            "unit": "pcs",
            "reorder_level": 5,
        }

        inv_resp = client.post("/api/inventory", data=json.dumps(inv_payload), headers=headers)
        print("Inventory create status:", inv_resp.status_code)
        try:
            print(inv_resp.get_json())
        except Exception:
            print(inv_resp.data)

        # Create asset (requires department_id, purchase_date, purchase_value, useful_life)
        asset_payload = {
            "name": "SmokeAsset",
            "type": "Laptop",
            "department_id": dept.id,
            "purchase_date": date.today().isoformat(),
            "purchase_value": 1200.0,
            "useful_life": 3,
        }

        asset_resp = client.post("/api/assets", data=json.dumps(asset_payload), headers=headers)
        print("Asset create status:", asset_resp.status_code)
        try:
            print(asset_resp.get_json())
        except Exception:
            print(asset_resp.data)

        # Print recent audit logs for diagnostics
        from app.models import inventory as inv_mod
        from app.models import event as ev_mod
        from app.models import organization as org_mod
        from app.models.inventory import AuditLog

        recent_audits = AuditLog.query.order_by(AuditLog.id.desc()).limit(10).all()
        print("Recent audit logs:")
        for a in recent_audits:
            print(a.id, a.action, a.entity_type, a.message if hasattr(a, 'message') else a.details)

        # Direct service-level calls to see exceptions and stack traces
        from app.services.inventory_service import InventoryService
        from app.services.asset_service import AssetService

        try:
            print("Direct service create_item...")
            inv_svc = InventoryService()
            item = inv_svc.create_item(org.id, inv_payload)
            print("Direct inventory created", item.id)
        except Exception as e:
            import traceback

            print("Direct inventory create exception:")
            traceback.print_exc()

        try:
            print("Direct service create_asset...")
            asset_svc = AssetService()
            # asset_service expects a date object for purchase_date (Marshmallow normally converts)
            asset_payload_for_service = dict(asset_payload)
            asset_payload_for_service["purchase_date"] = date.fromisoformat(asset_payload_for_service["purchase_date"]) if isinstance(asset_payload_for_service.get("purchase_date"), str) else asset_payload_for_service.get("purchase_date")
            a = asset_svc.create_asset(org.id, asset_payload_for_service)
            print("Direct asset created", a.id)
        except Exception as e:
            import traceback

            print("Direct asset create exception:")
            traceback.print_exc()


if __name__ == "__main__":
    run_smoke()
