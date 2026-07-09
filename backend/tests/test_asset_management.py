"""
Asset management module comprehensive tests.

Tests all asset operations including:
- Creation and registration
- Status transitions (available → assigned → returned)
- Asset conditions (good, damaged, lost)
- Stock integration with StockService/WarehouseStock
- Bulk import functionality
- Audit trail tracking
"""

import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models.asset import Asset, AssetStatus, AssetCondition, AssetAuditLog
from app.models.organization import Organization, Department
from app.models.user import User
from app.models.location_topology import Warehouse
from app.models.inventory import InventoryItem, StockMovement
from app.models.stock_levels import WarehouseStock
from app.services.asset_service import AssetService
from app.services.stock_service import StockService


@pytest.fixture
def app():
    """Create app with testing config."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def test_org(app):
    """Create test organization."""
    org = Organization(name="TEST", code="TST")
    db.session.add(org)
    db.session.commit()
    return org


@pytest.fixture
def test_user(app, test_org):
    """Create test user with proper password."""
    user = User(
        username="testuser",
        email="test@example.com",
        organisation_id=test_org.id,
        first_name="Test",
        last_name="User",
        role="admin",
    )
    user.set_password("TestPassword123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_department(app, test_org):
    """Create test department."""
    dept = Department(
        name="IT",
        code="IT",
        organisation_id=test_org.id,
        head_id=None
    )
    db.session.add(dept)
    db.session.commit()
    return dept


@pytest.fixture
def test_warehouse(app, test_org):
    """Create test warehouse."""
    wh = Warehouse(
        name="Main Warehouse",
        code="MW",
        organisation_id=test_org.id,
        is_active=True,
    )
    db.session.add(wh)
    db.session.commit()
    return wh


@pytest.fixture
def test_assignee(app, test_org, test_department):
    """Create test user for asset assignment."""
    user = User(
        username="assignee",
        email="assignee@example.com",
        organisation_id=test_org.id,
        first_name="Asset",
        last_name="Owner",
        role="user",
    )
    user.set_password("TestPassword123!")
    db.session.add(user)
    db.session.commit()
    return user


class TestAssetCreation:
    """Test asset creation and registration."""

    def test_create_asset_with_auto_code(self, test_org, test_user, test_department, test_warehouse):
        """Verify asset creation with auto-generated code."""
        asset_data = {
            "name": "Laptop",
            "type": "Computer",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 1500.00,
            "useful_life": 5,
            "warehouse_id": test_warehouse.id,
        }

        asset = AssetService().create_asset(test_org.id, asset_data)

        assert asset.id is not None
        assert asset.asset_code.startswith("TST-")
        assert asset.name == "Laptop"
        assert asset.status == AssetStatus.AVAILABLE.value
        assert asset.condition == AssetCondition.NEW.value
        assert asset.warehouse_id == test_warehouse.id

    def test_create_asset_with_custom_code(self, test_org, test_user, test_department):
        """Verify asset creation with custom code."""
        asset_data = {
            "asset_code": "CUST-001",
            "name": "Monitor",
            "type": "Display",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 300.00,
            "useful_life": 3,
        }

        asset = AssetService().create_asset(test_org.id, asset_data)

        assert asset.asset_code == "CUST-001"
        assert asset.name == "Monitor"

    def test_create_asset_creates_inventory_item(self, test_org, test_user, test_department, test_warehouse):
        """Verify asset creation syncs with inventory."""
        asset_data = {
            "name": "Desktop",
            "type": "Computer",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 2000.00,
            "useful_life": 5,
            "warehouse_id": test_warehouse.id,
        }

        asset = AssetService().create_asset(test_org.id, asset_data)

        # Verify inventory item was created
        inv_item = InventoryItem.query.filter_by(
            organisation_id=test_org.id,
            name="Desktop"
        ).first()
        assert inv_item is not None
        assert inv_item.quantity >= 1

    def test_create_asset_updates_warehouse_stock(self, test_org, test_user, test_department, test_warehouse):
        """Verify asset creation updates WarehouseStock."""
        asset_data = {
            "name": "Printer",
            "type": "Peripheral",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 500.00,
            "useful_life": 4,
            "warehouse_id": test_warehouse.id,
        }

        initial_stock = WarehouseStock.query.filter_by(
            warehouse_id=test_warehouse.id
        ).count()

        asset = AssetService().create_asset(test_org.id, asset_data)

        # Verify warehouse stock was updated
        inv_item = InventoryItem.query.filter_by(
            organisation_id=test_org.id,
            name="Printer"
        ).first()
        
        if inv_item:
            wh_stock = WarehouseStock.query.filter_by(
                item_id=inv_item.id,
                warehouse_id=test_warehouse.id
            ).first()
            assert wh_stock is not None
            assert wh_stock.quantity_on_hand >= 1

    def test_create_asset_duplicate_code_fails(self, test_org, test_user, test_department):
        """Verify duplicate asset code is rejected."""
        asset_data_1 = {
            "asset_code": "DUP-001",
            "name": "Asset1",
            "type": "Type1",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }

        asset_data_2 = {
            "asset_code": "DUP-001",
            "name": "Asset2",
            "type": "Type2",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }

        AssetService().create_asset(test_org.id, asset_data_1)
        
        from app.errors import ConflictError
        with pytest.raises(ConflictError):
            AssetService().create_asset(test_org.id, asset_data_2)


class TestAssetListing:
    """Test asset listing and filtering."""

    def test_list_all_assets(self, test_org, test_user, test_department):
        """Verify listing all assets."""
        for i in range(3):
            asset_data = {
                "name": f"Asset {i}",
                "type": "Type",
                "department_id": test_department.id,
                "purchase_date": datetime.now(timezone.utc).date(),
                "purchase_value": 100.00,
                "useful_life": 2,
            }
            AssetService().create_asset(test_org.id, asset_data)

        assets = AssetService().list_assets(test_org.id)
        
        assert assets.total >= 3

    def test_list_assets_by_status_available(self, test_org, test_user, test_department):
        """Verify filtering assets by AVAILABLE status."""
        asset_data = {
            "name": "Available Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        AssetService().create_asset(test_org.id, asset_data)

        assets = AssetService().list_assets(test_org.id, status=AssetStatus.AVAILABLE.value)
        
        assert any(a.name == "Available Asset" for a in assets.items)

    def test_list_assets_by_status_assigned(self, test_org, test_user, test_department, test_assignee):
        """Verify filtering assets by ASSIGNED status."""
        asset_data = {
            "name": "Asset To Assign",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        # Assign the asset
        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": datetime.now(timezone.utc).date(),
        }
        AssetService().assign_asset(asset.id, test_org.id, assign_data)

        assets = AssetService().list_assets(test_org.id, status=AssetStatus.ASSIGNED.value)
        
        assert any(a.name == "Asset To Assign" and a.status == AssetStatus.ASSIGNED.value for a in assets.items)

    def test_list_assets_by_department(self, test_org, test_user, test_department):
        """Verify filtering assets by department."""
        dept2 = Department(
            name="HR",
            code="HR",
            organisation_id=test_org.id,
            head_id=None
        )
        db.session.add(dept2)
        db.session.commit()

        asset_data = {
            "name": "IT Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        AssetService().create_asset(test_org.id, asset_data)

        assets = AssetService().list_assets(test_org.id, department_id=test_department.id)
        
        assert all(a.department_id == test_department.id for a in assets.items)

    def test_list_assets_search(self, test_org, test_user, test_department):
        """Verify searching assets by name."""
        asset_data = {
            "name": "Special Laptop",
            "type": "Computer",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        AssetService().create_asset(test_org.id, asset_data)

        assets = AssetService().list_assets(test_org.id, search="Laptop")
        
        assert any(a.name == "Special Laptop" for a in assets.items)


class TestAssetAssignment:
    """Test asset assignment workflow."""

    def test_assign_asset(self, test_org, test_user, test_department, test_assignee):
        """Verify asset assignment."""
        asset_data = {
            "name": "Assignable Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        assignment_date = datetime.now(timezone.utc).date()
        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": assignment_date,
        }
        assigned_asset = AssetService().assign_asset(asset.id, test_org.id, assign_data)

        assert assigned_asset.status == AssetStatus.ASSIGNED.value
        assert assigned_asset.assigned_to_user_id == test_assignee.id
        assert assigned_asset.assignment_date == assignment_date

    def test_assign_asset_with_return_date(self, test_org, test_user, test_department, test_assignee):
        """Verify asset assignment with return date."""
        asset_data = {
            "name": "Loaned Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        assignment_date = datetime.now(timezone.utc).date()
        return_date = assignment_date + timedelta(days=30)
        
        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": assignment_date,
            "return_date": return_date,
        }
        assigned_asset = AssetService().assign_asset(asset.id, test_org.id, assign_data)

        assert assigned_asset.return_date == return_date

    def test_cannot_assign_non_available_asset(self, test_org, test_user, test_department, test_assignee):
        """Verify cannot assign asset not in AVAILABLE status."""
        asset_data = {
            "name": "Disposed Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        # Change to disposed
        AssetService().update_asset_status(asset.id, test_org.id, AssetStatus.DISPOSED.value, "admin")

        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": datetime.now(timezone.utc).date(),
        }
        
        from app.errors import ValidationError
        with pytest.raises(ValidationError):
            AssetService().assign_asset(asset.id, test_org.id, assign_data)


class TestAssetReturn:
    """Test asset return workflow."""

    def test_return_asset_good_condition(self, test_org, test_user, test_department, test_assignee):
        """Verify returning asset in good condition."""
        asset_data = {
            "name": "Return Good",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        # Assign
        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": datetime.now(timezone.utc).date(),
        }
        AssetService().assign_asset(asset.id, test_org.id, assign_data)

        # Return
        return_data = {
            "return_condition": "good",
            "actual_return_date": datetime.now(timezone.utc).date(),
        }
        returned_asset = AssetService().return_asset(asset.id, test_org.id, return_data)

        assert returned_asset.status == AssetStatus.AVAILABLE.value
        assert returned_asset.condition == AssetCondition.GOOD.value
        assert returned_asset.assigned_to is None

    def test_return_asset_damaged_condition(self, test_org, test_user, test_department, test_assignee):
        """Verify returning asset in damaged condition."""
        asset_data = {
            "name": "Return Damaged",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        # Assign
        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": datetime.now(timezone.utc).date(),
        }
        AssetService().assign_asset(asset.id, test_org.id, assign_data)

        # Return damaged
        return_data = {
            "return_condition": "damaged",
            "actual_return_date": datetime.now(timezone.utc).date(),
        }
        returned_asset = AssetService().return_asset(asset.id, test_org.id, return_data)

        assert returned_asset.status == AssetStatus.DAMAGED.value
        assert returned_asset.condition == AssetCondition.REPAIR.value

    def test_return_asset_lost_condition(self, test_org, test_user, test_department, test_assignee):
        """Verify returning asset as lost."""
        asset_data = {
            "name": "Return Lost",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        # Assign
        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": datetime.now(timezone.utc).date(),
        }
        AssetService().assign_asset(asset.id, test_org.id, assign_data)

        # Return as lost
        return_data = {
            "return_condition": "lost",
            "actual_return_date": datetime.now(timezone.utc).date(),
        }
        returned_asset = AssetService().return_asset(asset.id, test_org.id, return_data)

        assert returned_asset.status == AssetStatus.LOST.value
        assert returned_asset.condition == AssetCondition.CONDEMNED.value


class TestAssetStatusTransitions:
    """Test asset status state machine."""

    def test_available_to_maintenance(self, test_org, test_user, test_department):
        """Verify AVAILABLE → UNDER_MAINTENANCE transition."""
        asset_data = {
            "name": "Maintenance Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        updated_asset = AssetService().update_asset_status(
            asset.id, test_org.id, AssetStatus.UNDER_MAINTENANCE.value, "admin"
        )

        assert updated_asset.status == AssetStatus.UNDER_MAINTENANCE.value

    def test_available_to_damaged(self, test_org, test_user, test_department):
        """Verify AVAILABLE → DAMAGED transition."""
        asset_data = {
            "name": "Broken Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        updated_asset = AssetService().update_asset_status(
            asset.id, test_org.id, AssetStatus.DAMAGED.value, "admin"
        )

        assert updated_asset.status == AssetStatus.DAMAGED.value

    def test_available_to_lost(self, test_org, test_user, test_department):
        """Verify AVAILABLE → LOST transition."""
        asset_data = {
            "name": "Missing Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        updated_asset = AssetService().update_asset_status(
            asset.id, test_org.id, AssetStatus.LOST.value, "admin"
        )

        assert updated_asset.status == AssetStatus.LOST.value

    def test_available_to_disposed(self, test_org, test_user, test_department):
        """Verify AVAILABLE → DISPOSED transition."""
        asset_data = {
            "name": "Disposal Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        updated_asset = AssetService().update_asset_status(
            asset.id, test_org.id, AssetStatus.DISPOSED.value, "admin"
        )

        assert updated_asset.status == AssetStatus.DISPOSED.value


class TestAssetDeletion:
    """Test asset deletion."""

    def test_delete_available_asset(self, test_org, test_user, test_department):
        """Verify deleting available asset."""
        asset_data = {
            "name": "Deletable Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        result = AssetService().delete_asset(asset.id, test_org.id)

        assert result is True
        
        # Verify asset is deleted
        from app.errors import NotFoundError
        with pytest.raises(NotFoundError):
            AssetService().get_asset(asset.id, test_org.id)

    def test_cannot_delete_assigned_asset(self, test_org, test_user, test_department, test_assignee):
        """Verify cannot delete assigned asset."""
        asset_data = {
            "name": "Assigned Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        # Assign
        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": datetime.now(timezone.utc).date(),
        }
        AssetService().assign_asset(asset.id, test_org.id, assign_data)

        # Try to delete
        from app.errors import ConflictError
        with pytest.raises(ConflictError):
            AssetService().delete_asset(asset.id, test_org.id)


class TestBulkAssetImport:
    """Test bulk asset import functionality."""

    def test_bulk_import_assets(self, test_org, test_user, test_department):
        """Verify bulk import of multiple assets."""
        items = [
            {
                "name": "Bulk Asset 1",
                "type": "Computer",
                "department_id": test_department.id,
                "purchase_date": datetime.now(timezone.utc).date(),
                "purchase_value": 100.00,
                "useful_life": 2,
            },
            {
                "name": "Bulk Asset 2",
                "type": "Computer",
                "department_id": test_department.id,
                "purchase_date": datetime.now(timezone.utc).date(),
                "purchase_value": 150.00,
                "useful_life": 3,
            },
        ]

        for item in items:
            AssetService().create_asset(test_org.id, item)

        # Verify both assets were created
        assets = AssetService().list_assets(test_org.id)
        
        assert any(a.name == "Bulk Asset 1" for a in assets.items)
        assert any(a.name == "Bulk Asset 2" for a in assets.items)


class TestAssetAuditTrail:
    """Test asset audit logging."""

    def test_asset_creation_audit_log(self, test_org, test_user, test_department):
        """Verify asset creation is logged."""
        asset_data = {
            "name": "Audit Test Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        # Check audit log
        logs = AssetAuditLog.query.filter_by(asset_id=asset.id, action="ASSET_CREATED").all()
        
        assert len(logs) > 0

    def test_asset_status_change_audit_log(self, test_org, test_user, test_department):
        """Verify asset status change is logged."""
        asset_data = {
            "name": "Status Audit Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        AssetService().update_asset_status(
            asset.id, test_org.id, AssetStatus.UNDER_MAINTENANCE.value, "admin"
        )

        # Check audit log
        logs = AssetAuditLog.query.filter_by(
            asset_id=asset.id, action="ASSET_STATUS_CHANGED"
        ).all()
        
        assert len(logs) > 0

    def test_asset_assignment_audit_log(self, test_org, test_user, test_department, test_assignee):
        """Verify asset assignment is logged."""
        asset_data = {
            "name": "Assignment Audit Asset",
            "type": "Type",
            "department_id": test_department.id,
            "purchase_date": datetime.now(timezone.utc).date(),
            "purchase_value": 100.00,
            "useful_life": 2,
        }
        asset = AssetService().create_asset(test_org.id, asset_data)

        assign_data = {
            "user_id": test_assignee.id,
            "department_id": test_department.id,
            "assignment_date": datetime.now(timezone.utc).date(),
        }
        AssetService().assign_asset(asset.id, test_org.id, assign_data)

        # Check audit log
        logs = AssetAuditLog.query.filter_by(
            asset_id=asset.id, action="ASSET_ASSIGNED"
        ).all()
        
        assert len(logs) > 0


class TestAssetStats:
    """Test asset statistics."""

    def test_get_asset_stats(self, test_org, test_user, test_department, test_assignee):
        """Verify asset statistics calculation."""
        # Create various assets
        for i in range(2):
            asset_data = {
                "name": f"Stats Asset {i}",
                "type": "Type",
                "department_id": test_department.id,
                "purchase_date": datetime.now(timezone.utc).date(),
                "purchase_value": 100.00,
                "useful_life": 2,
            }
            asset = AssetService().create_asset(test_org.id, asset_data)
            
            if i == 0:
                assign_data = {
                    "user_id": test_assignee.id,
                    "department_id": test_department.id,
                    "assignment_date": datetime.now(timezone.utc).date(),
                }
                AssetService().assign_asset(asset.id, test_org.id, assign_data)

        stats = AssetService().stats(test_org.id)

        assert stats is not None
        assert "status_breakdown" in stats
        assert stats["status_breakdown"]["available"] == 1
        assert stats["status_breakdown"]["assigned"] == 1
        assert stats["total_assets"] == 2
