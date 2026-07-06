import sys
import os
import pytest
from datetime import datetime, timezone
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import InventoryItem, WarehouseStock, StockMovement, Organization, User, Warehouse, Department, StockCard, SuppliesLedgerCard
from app.services.inventory_service import InventoryService
from app.services.stock_service import StockService


def test_get_inventory_does_not_shadow_inventory_service(monkeypatch):
    app = create_app('testing')
    with app.app_context():
        from app.blueprints import inventory as inventory_module
        import app.services.stock_service as stock_service_module

        class DummyItem:
            def __init__(self):
                self.id = 1
                self.name = "Sample Item"
                self.sku = "SKU-1"
                self.description = ""
                self.quantity = 3
                self.reorder_level = 1
                self.unit_price = 2.5
                self.unit = "pcs"
                self.created_at = datetime.now(timezone.utc)
                self.updated_at = datetime.now(timezone.utc)
                self.category_id = None
                self.item_type = None
                self.status = None
                self.preferred_supplier_id = None
                self.supplier_item_reference = None
                self.purchase_cost = None
                self.last_purchase_cost = None
                self.tax_category = None
                self.lead_time_days = None
                self.min_stock_level = None
                self.max_stock_level = None
                self.safety_stock = None
                self.opening_stock = None
                self.warehouse_id = None

            def is_low_stock(self):
                return False

        class DummyPaginatedResult:
            def __init__(self):
                self.page = 1
                self.per_page = 50
                self.total = 1
                self.pages = 1
                self.has_next = False
                self.has_prev = False
                self.items = [DummyItem()]

        class DummyStockService:
            def __init__(self, session=None):
                self.session = session

            def get_current_quantity(self, item_id):
                return 3

        def fake_list_items(org_id, page=1, per_page=50, search=None, low_stock_only=False):
            return DummyPaginatedResult()

        monkeypatch.setattr(inventory_module, "get_current_organisation_id", lambda: 1)
        inventory_module.inventory_service.list_items = fake_list_items
        monkeypatch.setattr(stock_service_module, "StockService", DummyStockService)

        view_func = inventory_module.get_inventory
        while hasattr(view_func, "__wrapped__"):
            view_func = view_func.__wrapped__

        with app.test_request_context("/api/inventory?page=1"):
            response = view_func()

        assert response[1] == 200


def test_inventory_endpoint_filters_items_by_department_warehouse(monkeypatch):
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Dept Filter Org", code="TST03")
        db.session.add(org)
        db.session.commit()

        warehouse_a = Warehouse(name="Operations Warehouse", code="WH03A", organisation_id=org.id)
        warehouse_b = Warehouse(name="Finance Warehouse", code="WH03B", organisation_id=org.id)
        db.session.add_all([warehouse_a, warehouse_b])
        db.session.commit()

        department = Department(
            organisation_id=org.id,
            warehouse_id=warehouse_a.id,
            name="Operations",
            code="OPS",
        )
        db.session.add(department)
        db.session.commit()

        matching_item = InventoryItem(
            organisation_id=org.id,
            name="Operations Item",
            sku="OPS-001",
            quantity=5,
            reorder_level=1,
            unit_price=10.0,
            unit="pcs",
            warehouse_id=warehouse_a.id,
        )
        other_item = InventoryItem(
            organisation_id=org.id,
            name="Finance Item",
            sku="FIN-001",
            quantity=3,
            reorder_level=1,
            unit_price=10.0,
            unit="pcs",
            warehouse_id=warehouse_b.id,
        )
        db.session.add_all([matching_item, other_item])
        db.session.commit()

        from app.blueprints import inventory as inventory_module
        monkeypatch.setattr(inventory_module, "get_current_organisation_id", lambda: org.id)

        view_func = inventory_module.get_inventory
        while hasattr(view_func, "__wrapped__"):
            view_func = view_func.__wrapped__

        with app.test_request_context(f"/api/inventory?department_id={department.id}"):
            response = view_func()

        payload = response[0].get_json() if isinstance(response, tuple) else response.get_json()
        returned_ids = {item["id"] for item in payload["inventory"]}

        assert response[1] == 200 if isinstance(response, tuple) else response.status_code == 200
        assert returned_ids == {matching_item.id}


def test_inventory_service_returns_refreshed_quantity_after_stock_update():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Test Org", code="TST02")
        db.session.add(org)
        db.session.commit()

        warehouse = Warehouse(name="Main Warehouse", code="WH02", organisation_id=org.id)
        db.session.add(warehouse)
        db.session.commit()

        item = InventoryItem(
            organisation_id=org.id,
            name="Refreshed Quantity Item",
            sku="REFRESH-001",
            quantity=0,
            reorder_level=5,
            unit_price=100.0,
            unit="pcs",
        )
        db.session.add(item)
        db.session.commit()

        updated_item = InventoryService().update_stock(
            item_id=item.id,
            org_id=org.id,
            movement_type="IN",
            quantity=50,
            warehouse_id=warehouse.id,
            reference="TEST-ADD-50",
            notes="Regression test",
        )

        assert updated_item.quantity == 50
        assert db.session.query(InventoryItem).get(item.id).quantity == 50


def test_delete_inventory_item_fails_when_stock_remaining():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Test Org", code="TST07")
        db.session.add(org)
        db.session.commit()

        warehouse = Warehouse(name="Main Warehouse", code="WH07", organisation_id=org.id)
        db.session.add(warehouse)
        db.session.commit()

        item = InventoryItem(
            organisation_id=org.id,
            name="Delete Stock Item",
            sku="DEL-001",
            quantity=0,
            reorder_level=1,
            unit_price=10.0,
            unit="pcs",
        )
        db.session.add(item)
        db.session.commit()

        StockService(session=db.session).increase_stock(
            item_id=item.id,
            org_id=org.id,
            quantity=5,
            warehouse_id=warehouse.id,
            reference="INITIAL-DELETE-STOCK",
            notes="Initial stock",
        )
        db.session.commit()

        with pytest.raises(Exception) as excinfo:
            InventoryService(session=db.session).delete_item(item.id, org.id)

        assert "remaining stock" in str(excinfo.value)


def test_admin_can_force_delete_inventory_item_with_stock():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Test Org", code="TST08")
        db.session.add(org)
        db.session.commit()

        user = User(username="adminuser", email="admin@test.com", role="admin", organisation_id=org.id)
        user.set_password("Password1!")
        db.session.add(user)
        db.session.commit()

        warehouse = Warehouse(name="Main Warehouse", code="WH08", organisation_id=org.id)
        db.session.add(warehouse)
        db.session.commit()

        item = InventoryItem(
            organisation_id=org.id,
            name="Force Delete Item",
            sku="FORCE-001",
            quantity=0,
            reorder_level=1,
            unit_price=10.0,
            unit="pcs",
        )
        db.session.add(item)
        db.session.commit()

        StockService(session=db.session).increase_stock(
            item_id=item.id,
            org_id=org.id,
            quantity=8,
            warehouse_id=warehouse.id,
            reference="INITIAL-FORCE-STOCK",
            notes="Initial stock",
        )
        db.session.commit()

        response = app.test_client().delete(
            f"/api/inventory/{item.id}/force",
            headers={"Authorization": f"Bearer {app.test_client().post('/api/auth/login', json={'email': 'admin@test.com', 'password': 'Password1!'}).get_json()['access_token']}"},
        )

        assert response.status_code == 200
        db.session.refresh(item)
        assert item.is_active is False
        assert item.quantity == 0
        stock_row = db.session.query(WarehouseStock).filter_by(item_id=item.id, warehouse_id=warehouse.id).first()
        assert stock_row.quantity_on_hand == 0
        assert stock_row.quantity_reserved == 0


def test_transfer_stock_updates_source_and_destination_warehouse_balances():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Test Org", code="TST06")
        db.session.add(org)
        db.session.commit()

        source_warehouse = Warehouse(name="Source Warehouse", code="WH06A", organisation_id=org.id)
        destination_warehouse = Warehouse(name="Destination Warehouse", code="WH06B", organisation_id=org.id)
        db.session.add_all([source_warehouse, destination_warehouse])
        db.session.commit()

        item = InventoryItem(
            organisation_id=org.id,
            name="Transfer Item",
            sku="TRANSFER-001",
            quantity=0,
            reorder_level=1,
            unit_price=10.0,
            unit="pcs",
        )
        db.session.add(item)
        db.session.commit()

        StockService(session=db.session).increase_stock(
            item_id=item.id,
            org_id=org.id,
            quantity=10,
            warehouse_id=source_warehouse.id,
            reference="INITIAL-TRANSFER-STOCK",
            notes="Initial stock",
        )

        InventoryService(session=db.session).update_stock(
            item_id=item.id,
            org_id=org.id,
            movement_type="OUT",
            quantity=3,
            warehouse_id=source_warehouse.id,
            destination_warehouse_id=destination_warehouse.id,
            reference="TRANSFER-001",
            notes="Warehouse transfer",
        )

        db.session.refresh(item)
        assert item.quantity == 10

        source_stock = db.session.query(WarehouseStock).filter_by(item_id=item.id, warehouse_id=source_warehouse.id).first()
        destination_stock = db.session.query(WarehouseStock).filter_by(item_id=item.id, warehouse_id=destination_warehouse.id).first()
        assert source_stock.quantity_on_hand == 7
        assert destination_stock.quantity_on_hand == 3

        movements = db.session.query(StockMovement).filter_by(item_id=item.id).order_by(StockMovement.id).all()
        assert len(movements) == 3
        assert movements[0].type == "IN"
        assert movements[0].warehouse_id == source_warehouse.id
        assert movements[1].type == "OUT"
        assert movements[1].destination_warehouse_id == destination_warehouse.id
        assert movements[2].type == "IN"
        assert movements[2].warehouse_id == destination_warehouse.id
        assert movements[2].destination_warehouse_id is None


def test_update_item_allows_same_sku_for_existing_item():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Test Org", code="TST04")
        db.session.add(org)
        db.session.commit()

        item = InventoryItem(
            organisation_id=org.id,
            name="Editable Item",
            sku="EDIT-001",
            quantity=10,
            reorder_level=5,
            unit_price=100.0,
            unit="pcs",
        )
        db.session.add(item)
        db.session.commit()

        InventoryService(session=db.session).update_item(
            item.id,
            org.id,
            {"name": "Editable Item Updated", "sku": "EDIT-001"},
        )

        db.session.refresh(item)
        assert item.name == "Editable Item Updated"
        assert item.sku == "EDIT-001"


def test_create_item_uses_opening_stock_as_warehouse_movement_not_item_master_data():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Test Org", code="TST03")
        db.session.add(org)
        db.session.commit()

        warehouse = Warehouse(name="Main Warehouse", code="WH03", organisation_id=org.id)
        db.session.add(warehouse)
        db.session.commit()

        item = InventoryService(session=db.session).create_item(
            org.id,
            {
                "name": "Opening Stock Item",
                "sku": "OPEN-001",
                "quantity": 0,
                "reorder_level": 5,
                "unit_price": 100.0,
                "unit": "pcs",
                "opening_stock": 50,
                "warehouse_id": warehouse.id,
            },
        )

        db.session.refresh(item)
        assert item.quantity == 50
        assert item.opening_stock is None


def test_create_inventory_accepts_other_item_type():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Test Org", code="TST05")
        db.session.add(org)
        db.session.commit()

        user = User(username="tester", email="tester@test.com", role="admin", organisation_id=org.id)
        user.set_password("Password1!")
        db.session.add(user)
        db.session.commit()

        warehouse = Warehouse(name="Main Warehouse", code="WH05", organisation_id=org.id)
        db.session.add(warehouse)
        db.session.commit()

        client = app.test_client()
        login = client.post(
            "/api/auth/login",
            json={"email": "tester@test.com", "password": "Password1!"},
        )
        assert login.status_code == 200
        token = login.get_json()["access_token"]

        response = client.post(
            "/api/inventory",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test Other Item",
                "sku": "OTHER-001",
                "quantity": 1,
                "reorder_level": 1,
                "unit_price": 10,
                "unit": "pcs",
                "item_type": "other",
                "warehouse_id": warehouse.id,
            },
        )

        assert response.status_code == 201
        payload = response.get_json()
        assert payload["item_id"] is not None


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
        )
        db.session.add(item)
        db.session.commit()
        print(f"Created Item: {item.id}")
        assert item.quantity == 0
        
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
        print(f"After Restock: Qty={item.quantity}")
        assert item.quantity == 50
        
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
        print(f"After Dispatch: Qty={item.quantity}")
        assert item.quantity == 5
        
        movements = StockMovement.query.filter_by(item_id=item.id).all()
        assert len(movements) == 2
        
        # 4. Delete Item (Soft Delete)
        item.is_active = False
        db.session.commit()
        
        print("E2E Test Passed successfully.")

if __name__ == "__main__":
    test_inventory_e2e()
