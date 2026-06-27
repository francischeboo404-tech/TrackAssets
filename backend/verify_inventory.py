import os
import sys
import uuid
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add the backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.organization import Organization
from app.models.inventory import InventoryItem, StockMovement, AuditLog
from app.models.stock_levels import WarehouseStock
from app.models.kenya_gov_models import StockCard, SuppliesLedgerCard
from app.models.location_topology import Warehouse

def setup_test_data(app):
    with app.app_context():
        # Create a test organization
        org_name = f"Test Org DB {uuid.uuid4().hex[:8]}"
        org = Organization(name=org_name, code=f"TEST_{uuid.uuid4().hex[:8]}")
        db.session.add(org)
        db.session.commit()

        # Create a test warehouse
        wh = Warehouse(organisation_id=org.id, name="Main WH", code=f"WH_{uuid.uuid4().hex[:4]}")
        db.session.add(wh)
        db.session.commit()

        # Create Admin
        admin = User(
            username=f"admin_{uuid.uuid4().hex[:6]}",
            email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
            role="admin",
            organisation_id=org.id,
            is_active=True
        )
        admin.set_password("Password123!")
        
        # Create Store Manager
        store_manager = User(
            username=f"sm_{uuid.uuid4().hex[:6]}",
            email=f"sm_{uuid.uuid4().hex[:6]}@test.com",
            role="store_manager",
            organisation_id=org.id,
            is_active=True
        )
        store_manager.set_password("Password123!")

        # Create Employee
        employee = User(
            username=f"emp_{uuid.uuid4().hex[:6]}",
            email=f"emp_{uuid.uuid4().hex[:6]}@test.com",
            role="employee",
            organisation_id=org.id,
            is_active=True
        )
        employee.set_password("Password123!")

        db.session.add_all([admin, store_manager, employee])
        db.session.commit()

        return {
            "org_id": org.id,
            "wh_id": wh.id,
            "admin_email": admin.email,
            "sm_email": store_manager.email,
            "emp_email": employee.email
        }

def login(app, email):
    client = app.test_client()
    resp = client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})
    assert resp.status_code == 200, f"Login failed: {resp.json}"
    return client

def verify_workflow():
    app = create_app()

    print("\n--- Starting E2E Verification Workflow for Inventory (Supabase DB) ---")
    
    data = setup_test_data(app)
    
    admin_client = login(app, data["admin_email"])
    sm_client = login(app, data["sm_email"])
    emp_client = login(app, data["emp_email"])

    # STEP: Roles Verification - Create Item
    print("\n[Step 1] Attempt to Create Item as Employee")
    sku = f"SKU-{uuid.uuid4().hex[:6]}"
    payload = {
        "name": "Test Laptop",
        "sku": sku,
        "description": "A test laptop",
        "quantity": 0,
        "reorder_level": 5,
        "unit_price": 1000.00,
        "unit": "pcs"
    }
    
    resp = emp_client.post('/api/inventory', json=payload)
    assert resp.status_code == 403, f"Employee should be forbidden, got {resp.status_code}"
    print("[OK] Success: Employee forbidden from creating inventory (403)")

    # STEP: Create Item
    print("\n[Step 2] Create Item as Admin")
    resp = admin_client.post('/api/inventory', json=payload)
    assert resp.status_code == 201, f"Admin creation failed: {resp.json}"
    item_id = resp.json['item_id']  # inventory.py returns 'item_id', not 'id'
    print(f"[OK] Success: Item created via Admin (ID: {item_id})")

    # STEP: Edit Item
    print("\n[Step 3] Edit Item as Admin")
    resp = admin_client.put(f'/api/inventory/{item_id}', json={"name": "Updated Laptop", "unit_price": 1200.00})
    assert resp.status_code == 200, f"Admin edit failed: {resp.json}"
    print(f"[OK] Success: Item edited (Name -> Updated Laptop)")

    # STEP: Restock Item as Store Manager
    print("\n[Step 4] Restock (Stock Update) as Store Manager")
    resp = sm_client.post(f'/api/inventory/{item_id}/stock', json={
        "type": "IN",
        "quantity": 10,
        "warehouse_id": data["wh_id"],
        "reference": "PO-12345"
    })
    assert resp.status_code == 200, f"Restock failed: {resp.json}"
    print(f"[OK] Success: Stock increased by 10")

    # STEP: Verifications in Database
    print("\n[Step 5] Verify Database State")
    with app.app_context():
        # Inventory Quantity Update
        item = InventoryItem.query.get(item_id)
        assert item.quantity == 10, f"Expected qty 10, got {item.quantity}"
        print("[OK] Success: Inventory Quantity Updated globally to 10")

        # Health Status Updated
        assert item.health_status == "OPTIMAL", f"Expected OPTIMAL, got {item.health_status}"
        print("[OK] Success: Health Status updated to OPTIMAL")

        # Stock Movement Created
        movement = StockMovement.query.filter_by(item_id=item_id).first()
        assert movement is not None and movement.quantity == 10
        print("[OK] Success: Stock Movement row created")

        # Stock Card Updated
        card = StockCard.query.filter_by(item_id=item_id).first()
        assert card is not None and card.quantity_on_hand == 10
        print("[OK] Success: Stock Card updated")

        # Supplies Ledger Updated
        ledger = SuppliesLedgerCard.query.filter_by(item_id=item_id).first()
        assert ledger is not None and ledger.quantity_on_hand == 10
        print("[OK] Success: Supplies Ledger Updated")

        # Audit Log Created
        audit = AuditLog.query.filter_by(entity_id=item_id, entity_type="inventory_item").all()
        assert len(audit) >= 2, "Expected audit logs for Create, Edit, Stock"
        print(f"[OK] Success: {len(audit)} Audit Log entries found for this item")

    # STEP: Dashboard Updated
    print("\n[Step 6] Dashboard Stats Verification")
    resp = admin_client.get('/api/inventory/stats')
    assert resp.status_code == 200
    stats = resp.json
    assert stats['total_items'] >= 1
    assert float(stats['total_value']) >= 12000.00  # 10 * 1200
    print(f"[OK] Success: Dashboard Stats correctly reflects changes (Total Value: {stats['total_value']})")

    # STEP: Delete/Archive
    print("\n[Step 7] Delete/Archive as Employee (Should Fail)")
    resp = emp_client.delete(f'/api/inventory/{item_id}')
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    print("[OK] Success: Employee forbidden from deleting (403)")

    print("\n[Step 8] Delete/Archive as Admin (But has stock)")
    resp = admin_client.delete(f'/api/inventory/{item_id}')
    assert resp.status_code == 409, f"Expected 409 due to stock, got {resp.status_code}"
    print("[OK] Success: System blocked deletion of item with active stock (409)")

    print("\n[Step 9] Dispatch Stock to 0")
    resp = sm_client.post(f'/api/inventory/{item_id}/stock', json={
        "type": "OUT",
        "quantity": 10,
        "warehouse_id": data["wh_id"],
        "reference": "DISPATCH-1"
    })
    assert resp.status_code == 200

    with app.app_context():
        item = InventoryItem.query.get(item_id)
        assert item.health_status == "OUT_OF_STOCK"
        print("[OK] Success: Stock dispatched to 0, Health Status is OUT_OF_STOCK")

    print("\n[Step 10] Delete/Archive as Admin")
    resp = admin_client.delete(f'/api/inventory/{item_id}')
    assert resp.status_code == 200, f"Delete failed: {resp.json}"
    print("[OK] Success: Item deleted/archived successfully")

    # STEP: Restore
    print("\n[Step 11] Restore Item as Admin")
    resp = admin_client.post(f'/api/inventory/{item_id}/restore')
    assert resp.status_code == 200, f"Restore failed: {resp.json}"
    print("[OK] Success: Item restored successfully")

    print("\n--- [OK] All Steps Verified Successfully! ---")

if __name__ == "__main__":
    verify_workflow()
