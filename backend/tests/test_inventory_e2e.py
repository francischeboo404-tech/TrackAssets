import sys
import os
import pytest
from datetime import datetime, timezone
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import InventoryItem, WarehouseStock, StockMovement, Organization, User, Warehouse, StockCard, SuppliesLedgerCard
from app.services.stock_service import StockService

def test_inventory_e2e():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Setup test data
        org = Organization.query.first()
        if not org:
            org = Organization(name="Test Org", code="TST01")
            db.session.add(org)
            db.session.commit()
            
        user = User.query.first()
        if not user:
            user = User(username="testuser", email="test@test.com", password_hash="123", role="admin", organisation_id=org.id)
            db.session.add(user)
            db.session.commit()
            
        warehouse = Warehouse.query.first()
        if not warehouse:
            warehouse = Warehouse(name="Main Warehouse", code="WH01", organisation_id=org.id)
            db.session.add(warehouse)
            db.session.commit()
            
        # 1. Create Item
        item = InventoryItem(
            organisation_id=org.id,
            name="Test E2E Item",
            sku=f"E2E-{int(datetime.now().timestamp())}",
            quantity=0,
            reorder_level=10,
            unit_price=100.0,
            unit="pcs",
            created_by=user.id
        )
        db.session.add(item)
        db.session.commit()
        print(f"Created Item: {item.id} - Health: {item.health_status}")
        assert item.health_status == "OUT_OF_STOCK"
        
        # 2. Restock Item (IN)
        stock_service = StockService()
        stock_service.increase_stock(
            item_id=item.id,
            org_id=org.id,
            quantity=50,
            warehouse_id=warehouse.id,
            reference="RESTOCK-001",
            notes="Initial stock",
            user_id=user.id
        )
        db.session.commit()
        
        db.session.refresh(item)
        print(f"After Restock: Qty={item.quantity}, Health={item.health_status}")
        assert item.quantity == 50
        assert item.health_status == "OPTIMAL"
        
        # Check movements
        movements = StockMovement.query.filter_by(item_id=item.id).all()
        assert len(movements) == 1
        assert movements[0].type == "IN"
        
        # Check StockCard
        sc = StockCard.query.filter_by(item_id=item.id, location_id=warehouse.id).first()
        assert sc is not None
        
        # 3. Dispatch Item (OUT)
        stock_service.decrease_stock(
            item_id=item.id,
            org_id=org.id,
            quantity=45,
            warehouse_id=warehouse.id,
            reference="DISPATCH-001",
            notes="Usage",
            user_id=user.id
        )
        db.session.commit()
        
        db.session.refresh(item)
        print(f"After Dispatch: Qty={item.quantity}, Health={item.health_status}")
        assert item.quantity == 5
        assert item.health_status == "CRITICAL" # reorder level is 10, max(1, 10//2) = 5, <= 5 is CRITICAL
        
        movements = StockMovement.query.filter_by(item_id=item.id).all()
        assert len(movements) == 2
        
        # 4. Delete Item (Soft Delete)
        item.is_active = False
        db.session.commit()
        
        print("E2E Test Passed successfully.")

if __name__ == "__main__":
    test_inventory_e2e()
