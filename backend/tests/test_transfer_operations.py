"""
Comprehensive integration tests for transfer operations module.

Tests verify that transfer operations are fully working with the new architecture:
- warehouse as source of truth
- stock_service as mutation engine
- inventory items/assets properly tracked when dispatched
"""

import pytest
from datetime import date
from app import db, create_app
from app.models import (
    Organization,
    User,
    Department,
    InventoryItem,
    Asset,
    WarehouseStock,
    StockMovement,
)
from app.models.location_topology import Warehouse
from app.models.transfer import TransferRequest, TransferType
from app.services.stock_service import StockService
from app.services.inventory_service import InventoryService
from app.repositories.inventory_repository import InventoryRepository
from flask_jwt_extended import create_access_token


@pytest.fixture
def app_context():
    """Setup test app and database."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_org(app_context):
    """Create test organization."""
    org = Organization(name="Test Org", code="TEST-ORG", is_active=True)
    db.session.add(org)
    db.session.commit()
    return org


@pytest.fixture
def test_user(test_org):
    """Create test admin user."""
    user = User(
        username="admin_user",
        email="admin@test.com",
        password_hash="hashed_pwd",
        role="admin",
        organisation_id=test_org.id,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_departments(test_org):
    """Create test departments."""
    dept1 = Department(
        name="Warehouse",
        code="WH-001",
        organisation_id=test_org.id,
        is_active=True,
    )
    dept2 = Department(
        name="Operations",
        code="OP-001",
        organisation_id=test_org.id,
        is_active=True,
    )
    db.session.add_all([dept1, dept2])
    db.session.commit()
    return {"warehouse": dept1, "operations": dept2}


@pytest.fixture
def test_warehouses(test_org):
    """Create test warehouses."""
    wh1 = Warehouse(
        name="Main Warehouse",
        code="WH-001",
        address="Main Location",
        organisation_id=test_org.id,
        is_active=True,
    )
    wh2 = Warehouse(
        name="Secondary Warehouse",
        code="WH-002",
        address="Secondary Location",
        organisation_id=test_org.id,
        is_active=True,
    )
    db.session.add_all([wh1, wh2])
    db.session.commit()
    return {"main": wh1, "secondary": wh2}


@pytest.fixture
def test_inventory_item(test_org, test_warehouses):
    """Create test inventory item with initial stock."""
    item = InventoryItem(
        name="Test Item",
        sku="TEST-001",
        unit="units",
        unit_price=100.0,
        organisation_id=test_org.id,
        quantity=0,  # Will be set via warehouse stock
    )
    db.session.add(item)
    db.session.commit()

    # Create warehouse stock in main warehouse
    stock = WarehouseStock(
        item_id=item.id,
        warehouse_id=test_warehouses["main"].id,
        quantity_on_hand=100,
        quantity_reserved=0,
    )
    db.session.add(stock)

    # Set item quantity to match warehouse stock
    item.quantity = 100
    db.session.commit()

    return item


@pytest.fixture
def test_asset(test_org, test_departments):
    """Create test asset."""
    from datetime import date
    asset = Asset(
        name="Test Asset",
        asset_code="ASSET-001",
        type="equipment",
        organisation_id=test_org.id,
        department_id=test_departments["warehouse"].id,
        status="active",
        location="Warehouse",
        condition="new",
        purchase_date=date.today(),
        purchase_value=5000.0,
        useful_life=5,
        current_value=5000.0,
    )
    db.session.add(asset)
    db.session.commit()
    return asset


@pytest.fixture
def client_with_auth(app_context, test_user):
    """Create test client with authentication."""
    client = app_context.test_client()
    token = create_access_token(identity=str(test_user.id))
    client.default_headers = {"Authorization": f"Bearer {token}"}
    return client


class TestInventoryTransferRequest:
    """Test inventory transfer request creation."""

    def test_transfer_request_with_from_warehouse_saves_warehouse_id(
        self, client_with_auth, test_org, test_departments, test_warehouses, test_inventory_item
    ):
        """Verify that from_warehouse_id is saved in transfer request."""
        response = client_with_auth.post(
            "/api/transfers/request",
            json={
                "item_type": "inventory",
                "transfer_type": TransferType.DEPARTMENT_TO_DEPARTMENT,
                "inventory_item_id": test_inventory_item.id,
                "quantity": 50,
                "from_warehouse_id": test_warehouses["main"].id,
                "to_warehouse_id": test_warehouses["secondary"].id,
                "new_department_id": test_departments["operations"].id,
                "comment": "Testing warehouse transfer",
            },
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 201
        request_data = response.get_json()
        assert request_data["message"] == "Transfer request submitted successfully"

        # Verify transfer request saved with from_warehouse_id
        transfer_req = TransferRequest.query.filter_by(
            id=request_data["request_id"], organisation_id=test_org.id
        ).first()
        assert transfer_req is not None
        assert transfer_req.inventory_item_id == test_inventory_item.id
        assert transfer_req.quantity == 50
        assert transfer_req.from_warehouse_id == test_warehouses["main"].id
        assert transfer_req.to_warehouse_id == test_warehouses["secondary"].id
        assert transfer_req.status == "pending"

    def test_transfer_request_validates_source_warehouse_stock(
        self, client_with_auth, test_org, test_departments, test_warehouses, test_inventory_item
    ):
        """Verify that transfer request validates available stock in source warehouse."""
        response = client_with_auth.post(
            "/api/transfers/request",
            json={
                "item_type": "inventory",
                "transfer_type": TransferType.DEPARTMENT_TO_DEPARTMENT,
                "inventory_item_id": test_inventory_item.id,
                "quantity": 150,  # More than available
                "from_warehouse_id": test_warehouses["main"].id,
                "new_department_id": test_departments["operations"].id,
            },
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 400
        error_data = response.get_json()
        assert "Insufficient stock" in error_data.get("message", "")

    def test_transfer_requests_include_warehouse_tracking_details(
        self, client_with_auth, test_org, test_departments, test_warehouses, test_inventory_item, test_user
    ):
        """Verify that transfer requests return source and destination warehouse details for tracking."""
        transfer_req = TransferRequest(
            organisation_id=test_org.id,
            item_type="inventory",
            transfer_type=TransferType.DEPARTMENT_TO_DEPARTMENT,
            inventory_item_id=test_inventory_item.id,
            quantity=25,
            requested_by=test_user.id,
            from_department_id=test_departments["warehouse"].id,
            to_department_id=test_departments["operations"].id,
            from_warehouse_id=test_warehouses["main"].id,
            to_warehouse_id=test_warehouses["secondary"].id,
            status="pending",
        )
        db.session.add(transfer_req)
        db.session.commit()

        response = client_with_auth.get(
            "/api/transfers/requests",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["transfer_requests"]
        item = next((req for req in payload["transfer_requests"] if req["id"] == transfer_req.id), None)
        assert item is not None
        assert item["from_warehouse_name"] == test_warehouses["main"].name
        assert item["to_warehouse_name"] == test_warehouses["secondary"].name

    def test_in_transit_inventory_request_returns_reserved_quantity(
        self,
        client_with_auth,
        test_org,
        test_departments,
        test_warehouses,
        test_inventory_item,
        test_user,
    ):
        """Verify in-transit inventory requests include reserved quantity metadata."""
        transfer_req = TransferRequest(
            organisation_id=test_org.id,
            item_type="inventory",
            transfer_type=TransferType.DEPARTMENT_TO_DEPARTMENT,
            inventory_item_id=test_inventory_item.id,
            quantity=25,
            requested_by=test_user.id,
            from_department_id=test_departments["warehouse"].id,
            to_department_id=test_departments["operations"].id,
            from_warehouse_id=test_warehouses["main"].id,
            to_warehouse_id=test_warehouses["secondary"].id,
            status="in_transit",
        )
        db.session.add(transfer_req)
        db.session.commit()

        # Reserve the matching quantity on the source warehouse stock row
        from app.models import WarehouseStock
        stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouses["main"].id,
        ).first()
        stock.quantity_reserved = 25
        db.session.commit()

        response = client_with_auth.get(
            "/api/transfers/requests?status=in_transit",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200
        payload = response.get_json()
        item = next((req for req in payload["transfer_requests"] if req["id"] == transfer_req.id), None)
        assert item is not None
        assert item["status"] == "in_transit"
        assert item["reservation_status"] == "reserved"
        assert item["from_warehouse_reserved_quantity"] == 25


class TestInventoryTransferDispatch:
    """Test inventory transfer dispatch operations."""

    @pytest.fixture
    def pending_transfer_request(self, test_org, test_user, test_departments, test_warehouses, test_inventory_item):
        """Create a pending transfer request."""
        req = TransferRequest(
            organisation_id=test_org.id,
            item_type="inventory",
            transfer_type=TransferType.DEPARTMENT_TO_DEPARTMENT,
            inventory_item_id=test_inventory_item.id,
            quantity=50,
            requested_by=test_user.id,
            from_department_id=test_departments["warehouse"].id,
            to_department_id=test_departments["operations"].id,
            from_warehouse_id=test_warehouses["main"].id,
            to_warehouse_id=test_warehouses["secondary"].id,
            status="pending",
        )
        db.session.add(req)
        db.session.commit()
        return req

    @pytest.fixture
    def approved_transfer_request(self, pending_transfer_request, test_user):
        """Approve the transfer request."""
        pending_transfer_request.status = "approved"
        pending_transfer_request.reviewed_by = test_user.id
        pending_transfer_request.reviewed_at = db.func.now()
        db.session.commit()
        return pending_transfer_request

    def test_dispatch_marks_transfer_as_in_transit(
        self, client_with_auth, test_org, approved_transfer_request
    ):
        """Verify that dispatch marks transfer request as in_transit."""
        response = client_with_auth.post(
            f"/api/transfers/requests/{approved_transfer_request.id}/dispatch",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["message"] == "Transfer request dispatched successfully"

        # Verify transfer request status changed to in_transit
        db.session.refresh(approved_transfer_request)
        assert approved_transfer_request.status == "in_transit"

    def test_dispatch_creates_audit_log(
        self, client_with_auth, test_org, approved_transfer_request
    ):
        """Verify that dispatch creates an audit log."""
        response = client_with_auth.post(
            f"/api/transfers/requests/{approved_transfer_request.id}/dispatch",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200

        # Verify audit log created
        from app.models.inventory import AuditLog
        audit_log = AuditLog.query.filter_by(
            organisation_id=test_org.id,
            action="TRANSFER_REQUEST_DISPATCHED",
            entity_id=approved_transfer_request.id,
        ).first()
        assert audit_log is not None
        assert audit_log.details["item_type"] == "inventory"

    def test_dispatch_reserves_source_warehouse(
        self, client_with_auth, test_org, approved_transfer_request
    ):
        """Verify that dispatch reserves stock at source warehouse."""
        response = client_with_auth.post(
            f"/api/transfers/requests/{approved_transfer_request.id}/dispatch",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200

        # Verify reservation created
        from app.models.location_topology import Warehouse
        from app.models import WarehouseStock
        stock = WarehouseStock.query.filter_by(
            item_id=approved_transfer_request.inventory_item_id,
            warehouse_id=approved_transfer_request.from_warehouse_id,
        ).first()
        assert stock is not None
        assert stock.quantity_reserved >= approved_transfer_request.quantity


class TestInventoryTransferReceive:
    """Test inventory transfer receive operations."""

    @pytest.fixture
    def in_transit_transfer_request(self, test_org, test_user, test_departments, test_warehouses, test_inventory_item):
        """Create an in-transit transfer request."""
        req = TransferRequest(
            organisation_id=test_org.id,
            item_type="inventory",
            transfer_type=TransferType.DEPARTMENT_TO_DEPARTMENT,
            inventory_item_id=test_inventory_item.id,
            quantity=50,
            requested_by=test_user.id,
            from_department_id=test_departments["warehouse"].id,
            to_department_id=test_departments["operations"].id,
            from_warehouse_id=test_warehouses["main"].id,
            to_warehouse_id=test_warehouses["secondary"].id,
            status="in_transit",
        )
        db.session.add(req)
        db.session.commit()
        return req

    def test_receive_transfers_stock_between_warehouses(
        self, client_with_auth, test_org, test_warehouses, test_inventory_item, in_transit_transfer_request
    ):
        """Verify that receive transfers stock from source to destination warehouse."""
        # Initial state
        initial_main_stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouses["main"].id,
        ).first()
        assert initial_main_stock.quantity_on_hand == 100

        initial_secondary_stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouses["secondary"].id,
        ).first()
        initial_secondary_qty = initial_secondary_stock.quantity_on_hand if initial_secondary_stock else 0

        # Receive transfer
        response = client_with_auth.post(
            f"/api/transfers/requests/{in_transit_transfer_request.id}/receive",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["message"] == "Transfer request received successfully"

        # Verify stock transferred
        db.session.refresh(initial_main_stock)
        main_stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouses["main"].id,
        ).first()
        assert main_stock.quantity_on_hand == 50  # 100 - 50

        secondary_stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouses["secondary"].id,
        ).first()
        assert secondary_stock is not None
        assert secondary_stock.quantity_on_hand == initial_secondary_qty + 50

    def test_receive_marks_transfer_as_completed(
        self, client_with_auth, test_org, in_transit_transfer_request
    ):
        """Verify that receive marks transfer request as completed."""
        response = client_with_auth.post(
            f"/api/transfers/requests/{in_transit_transfer_request.id}/receive",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200

        # Verify transfer request status changed to completed
        db.session.refresh(in_transit_transfer_request)
        assert in_transit_transfer_request.status == "completed"

    def test_receive_creates_stock_movement(
        self, client_with_auth, test_org, test_inventory_item, in_transit_transfer_request
    ):
        """Verify that receive creates stock movements for tracking."""
        response = client_with_auth.post(
            f"/api/transfers/requests/{in_transit_transfer_request.id}/receive",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200

        # Verify stock movements created (OUT and IN)
        movements = StockMovement.query.filter_by(
            item_id=test_inventory_item.id,
            organization_id=test_org.id,
        ).order_by(StockMovement.date.desc()).all()

        # Should have OUT and IN movements
        assert len(movements) >= 2
        out_movement = next((m for m in movements if m.type == "OUT"), None)
        in_movement = next((m for m in movements if m.type == "IN"), None)

        assert out_movement is not None
        assert in_movement is not None
        assert out_movement.quantity == 50
        assert in_movement.quantity == 50


class TestAssetTransferOperations:
    """Test asset transfer operations."""

    @pytest.fixture
    def pending_asset_transfer(self, test_org, test_user, test_departments, test_asset):
        """Create a pending asset transfer request."""
        req = TransferRequest(
            organisation_id=test_org.id,
            item_type="asset",
            transfer_type=TransferType.DEPARTMENT_TO_DEPARTMENT,
            asset_id=test_asset.id,
            requested_by=test_user.id,
            from_department_id=test_departments["warehouse"].id,
            to_department_id=test_departments["operations"].id,
            status="pending",
        )
        db.session.add(req)
        db.session.commit()
        return req

    @pytest.fixture
    def approved_asset_transfer(self, pending_asset_transfer, test_user):
        """Approve the asset transfer request."""
        pending_asset_transfer.status = "approved"
        pending_asset_transfer.reviewed_by = test_user.id
        pending_asset_transfer.reviewed_at = db.func.now()
        db.session.commit()
        return pending_asset_transfer

    def test_asset_dispatch_marks_in_transit(
        self, client_with_auth, test_org, test_asset, approved_asset_transfer
    ):
        """Verify that asset dispatch marks it as in transit."""
        response = client_with_auth.post(
            f"/api/transfers/requests/{approved_asset_transfer.id}/dispatch",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200

        # Verify asset location changed to in transit
        db.session.refresh(test_asset)
        assert "In Transit" in test_asset.location

    def test_asset_receive_updates_department(
        self, client_with_auth, test_org, test_asset, test_departments, approved_asset_transfer
    ):
        """Verify that receiving asset updates its department."""
        # First dispatch
        approved_asset_transfer.status = "in_transit"
        db.session.commit()

        # Then receive
        response = client_with_auth.post(
            f"/api/transfers/requests/{approved_asset_transfer.id}/receive",
            headers=client_with_auth.default_headers,
        )

        assert response.status_code == 200

        # Verify asset department changed
        db.session.refresh(test_asset)
        assert test_asset.department_id == test_departments["operations"].id
        assert approved_asset_transfer.status == "completed"


class TestTransferWorkflow:
    """Test complete transfer workflows."""

    def test_complete_inventory_transfer_workflow(
        self, client_with_auth, test_org, test_user, test_departments, test_warehouses, test_inventory_item
    ):
        """Test complete inventory transfer: request -> approve -> dispatch -> receive."""
        # Step 1: Request transfer
        request_response = client_with_auth.post(
            "/api/transfers/request",
            json={
                "item_type": "inventory",
                "transfer_type": TransferType.DEPARTMENT_TO_DEPARTMENT,
                "inventory_item_id": test_inventory_item.id,
                "quantity": 30,
                "from_warehouse_id": test_warehouses["main"].id,
                "to_warehouse_id": test_warehouses["secondary"].id,
                "new_department_id": test_departments["operations"].id,
            },
            headers=client_with_auth.default_headers,
        )
        assert request_response.status_code == 201
        request_id = request_response.get_json()["request_id"]

        # Step 2: Approve transfer
        approve_response = client_with_auth.post(
            f"/api/transfers/requests/{request_id}/approve",
            json={},
            headers=client_with_auth.default_headers,
        )
        assert approve_response.status_code == 200

        # Step 3: Dispatch transfer
        dispatch_response = client_with_auth.post(
            f"/api/transfers/requests/{request_id}/dispatch",
            headers=client_with_auth.default_headers,
        )
        assert dispatch_response.status_code == 200

        # Step 4: Receive transfer
        receive_response = client_with_auth.post(
            f"/api/transfers/requests/{request_id}/receive",
            headers=client_with_auth.default_headers,
        )
        assert receive_response.status_code == 200

        # Verify final state
        transfer_req = TransferRequest.query.get(request_id)
        assert transfer_req.status == "completed"

        # Verify stock distribution
        main_stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouses["main"].id,
        ).first()
        assert main_stock.quantity_on_hand == 70  # 100 - 30

        secondary_stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouses["secondary"].id,
        ).first()
        assert secondary_stock.quantity_on_hand == 30

    def test_complete_asset_transfer_workflow(
        self, client_with_auth, test_org, test_user, test_departments, test_asset
    ):
        """Test complete asset transfer: request -> approve -> dispatch -> receive."""
        # Step 1: Request transfer
        request_response = client_with_auth.post(
            "/api/transfers/request",
            json={
                "item_type": "asset",
                "transfer_type": TransferType.DEPARTMENT_TO_DEPARTMENT,
                "asset_id": test_asset.id,
                "new_department_id": test_departments["operations"].id,
            },
            headers=client_with_auth.default_headers,
        )
        assert request_response.status_code == 201
        request_id = request_response.get_json()["request_id"]

        # Step 2: Approve transfer
        approve_response = client_with_auth.post(
            f"/api/transfers/requests/{request_id}/approve",
            json={},
            headers=client_with_auth.default_headers,
        )
        assert approve_response.status_code == 200

        # Step 3: Dispatch transfer
        dispatch_response = client_with_auth.post(
            f"/api/transfers/requests/{request_id}/dispatch",
            headers=client_with_auth.default_headers,
        )
        assert dispatch_response.status_code == 200

        # Step 4: Receive transfer
        receive_response = client_with_auth.post(
            f"/api/transfers/requests/{request_id}/receive",
            headers=client_with_auth.default_headers,
        )
        assert receive_response.status_code == 200

        # Verify final state
        db.session.refresh(test_asset)
        assert test_asset.department_id == test_departments["operations"].id

        transfer_req = TransferRequest.query.get(request_id)
        assert transfer_req.status == "completed"
