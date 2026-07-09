"""
Integration tests for warehouse hierarchy and inventory transfer functionality.

Tests the multi-warehouse hierarchy system where:
- Main warehouse is parent
- Other storage facilities are children
- Transfers flow through the hierarchy (parent can transfer to children, children to parent)
"""

import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.location_topology import Warehouse
from app.models.inventory import InventoryItem
from app.models.stock_levels import WarehouseStock
from app.models import Organization, User
from app.services.warehouse_hierarchy_service import WarehouseHierarchyService
from app.services.stock_service import StockService
from app.errors import ConflictError, NotFoundError, ValidationError


class TestWarehouseHierarchy:
    """Test warehouse hierarchy structure and relationships"""

    def test_set_main_warehouse(self):
        """Test setting a warehouse as main warehouse"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            # Create organization
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            # Create a test warehouse
            warehouse = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001",
                address="123 Main St"
            )
            db.session.add(warehouse)
            db.session.commit()
            
            # Set as main warehouse
            main_wh = WarehouseHierarchyService.set_main_warehouse(warehouse.id, org.id)
            
            assert main_wh.is_main_warehouse == True
            assert main_wh.warehouse_type == "main"
            assert main_wh.hierarchy_level == 0
            assert main_wh.parent_warehouse_id is None

    def test_get_main_warehouse(self):
        """Test retrieving the main warehouse for an organization"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            warehouse = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001",
                address="123 Main St"
            )
            db.session.add(warehouse)
            db.session.commit()
            
            WarehouseHierarchyService.set_main_warehouse(warehouse.id, org.id)
            
            # Retrieve main warehouse
            main_wh = WarehouseHierarchyService.get_main_warehouse(org.id)
            
            assert main_wh.id == warehouse.id
            assert main_wh.is_main_warehouse == True

    def test_add_child_warehouse(self):
        """Test adding a child warehouse to a parent"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            # Create main warehouse
            main_wh = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001"
            )
            db.session.add(main_wh)
            db.session.commit()
            
            WarehouseHierarchyService.set_main_warehouse(main_wh.id, org.id)
            
            # Create child warehouse
            child_wh = Warehouse(
                organisation_id=org.id,
                name="Branch Warehouse",
                code="BW-001"
            )
            db.session.add(child_wh)
            db.session.commit()
            
            # Add as child
            result = WarehouseHierarchyService.add_child_warehouse(child_wh.id, main_wh.id, org.id)
            
            assert result.parent_warehouse_id == main_wh.id
            assert result.warehouse_type == "storage_facility"
            assert result.hierarchy_level == 1

    def test_get_warehouse_hierarchy(self):
        """Test retrieving the complete warehouse hierarchy"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            # Create main warehouse
            main_wh = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001"
            )
            db.session.add(main_wh)
            db.session.commit()
            WarehouseHierarchyService.set_main_warehouse(main_wh.id, org.id)
            
            # Create child warehouses
            child1 = Warehouse(
                organisation_id=org.id,
                name="Branch 1",
                code="B1-001"
            )
            child2 = Warehouse(
                organisation_id=org.id,
                name="Branch 2",
                code="B2-001"
            )
            db.session.add_all([child1, child2])
            db.session.commit()
            
            WarehouseHierarchyService.add_child_warehouse(child1.id, main_wh.id, org.id)
            WarehouseHierarchyService.add_child_warehouse(child2.id, main_wh.id, org.id)
            
            # Get hierarchy
            hierarchy = WarehouseHierarchyService.get_warehouse_hierarchy(org.id)
            
            assert hierarchy["name"] == "Main Warehouse"
            assert len(hierarchy["children"]) == 2
            assert any(c["code"] == "B1-001" for c in hierarchy["children"])
            assert any(c["code"] == "B2-001" for c in hierarchy["children"])

    def test_validate_transfer_path_main_to_child(self):
        """Test that main warehouse can transfer to child"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            # Create hierarchy
            main_wh = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001"
            )
            child_wh = Warehouse(
                organisation_id=org.id,
                name="Child Warehouse",
                code="CW-001"
            )
            db.session.add_all([main_wh, child_wh])
            db.session.commit()
            
            WarehouseHierarchyService.set_main_warehouse(main_wh.id, org.id)
            WarehouseHierarchyService.add_child_warehouse(child_wh.id, main_wh.id, org.id)
            
            # This should NOT raise an exception
            result = WarehouseHierarchyService.validate_transfer_path(
                main_wh.id, child_wh.id, org.id
            )
            assert result == True

    def test_validate_transfer_path_child_to_main(self):
        """Test that child can transfer back to main"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            # Create hierarchy
            main_wh = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001"
            )
            child_wh = Warehouse(
                organisation_id=org.id,
                name="Child Warehouse",
                code="CW-001"
            )
            db.session.add_all([main_wh, child_wh])
            db.session.commit()
            
            WarehouseHierarchyService.set_main_warehouse(main_wh.id, org.id)
            WarehouseHierarchyService.add_child_warehouse(child_wh.id, main_wh.id, org.id)
            
            # This should NOT raise an exception
            result = WarehouseHierarchyService.validate_transfer_path(
                child_wh.id, main_wh.id, org.id
            )
            assert result == True

    def test_validate_transfer_path_child_to_child_fails(self):
        """Test that child cannot transfer directly to another child"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            # Create hierarchy with two children
            main_wh = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001"
            )
            child1 = Warehouse(
                organisation_id=org.id,
                name="Child 1",
                code="C1-001"
            )
            child2 = Warehouse(
                organisation_id=org.id,
                name="Child 2",
                code="C2-001"
            )
            db.session.add_all([main_wh, child1, child2])
            db.session.commit()
            
            WarehouseHierarchyService.set_main_warehouse(main_wh.id, org.id)
            WarehouseHierarchyService.add_child_warehouse(child1.id, main_wh.id, org.id)
            WarehouseHierarchyService.add_child_warehouse(child2.id, main_wh.id, org.id)
            
            # This SHOULD raise an exception
            with pytest.raises(ConflictError):
                WarehouseHierarchyService.validate_transfer_path(
                    child1.id, child2.id, org.id
                )


class TestHierarchyAwareTransfers:
    """Test inventory transfers with warehouse hierarchy enforcement"""

    def test_transfer_from_main_to_child(self):
        """Test transferring stock from main warehouse to child warehouse"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            # Create warehouses
            main_wh = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001"
            )
            child_wh = Warehouse(
                organisation_id=org.id,
                name="Child Warehouse",
                code="CW-001"
            )
            db.session.add_all([main_wh, child_wh])
            db.session.commit()
            
            WarehouseHierarchyService.set_main_warehouse(main_wh.id, org.id)
            WarehouseHierarchyService.add_child_warehouse(child_wh.id, main_wh.id, org.id)
            
            # Create inventory item
            item = InventoryItem(
                organisation_id=org.id,
                name="Test Item",
                sku="TEST-001",
                unit_price=100,
                quantity=10
            )
            db.session.add(item)
            db.session.commit()
            
            # Add stock to main warehouse
            stock = WarehouseStock(
                item_id=item.id,
                warehouse_id=main_wh.id,
                quantity_on_hand=10,
                quantity_reserved=0
            )
            db.session.add(stock)
            db.session.commit()
            
            # Transfer from main to child
            stock_service = StockService()
            result = stock_service.transfer_with_hierarchy(
                item_id=item.id,
                org_id=org.id,
                quantity=5,
                from_warehouse_id=main_wh.id,
                to_warehouse_id=child_wh.id,
                commit=True
            )
            
            # Verify transfer
            assert result["quantity"] == 5
            assert result["from_warehouse_id"] == main_wh.id
            assert result["to_warehouse_id"] == child_wh.id
            
            # Verify stock levels
            main_stock = db.session.query(WarehouseStock).filter_by(
                item_id=item.id, warehouse_id=main_wh.id
            ).first()
            child_stock = db.session.query(WarehouseStock).filter_by(
                item_id=item.id, warehouse_id=child_wh.id
            ).first()
            
            assert main_stock.quantity_on_hand == 5
            assert child_stock.quantity_on_hand == 5

    def test_transfer_insufficient_stock_fails(self):
        """Test that transfer fails when insufficient stock available"""
        app = create_app('testing')
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            org = Organization(name="Test Org", code="TEST-001")
            db.session.add(org)
            db.session.commit()
            
            # Create warehouses
            main_wh = Warehouse(
                organisation_id=org.id,
                name="Main Warehouse",
                code="MW-001"
            )
            child_wh = Warehouse(
                organisation_id=org.id,
                name="Child Warehouse",
                code="CW-001"
            )
            db.session.add_all([main_wh, child_wh])
            db.session.commit()
            
            WarehouseHierarchyService.set_main_warehouse(main_wh.id, org.id)
            WarehouseHierarchyService.add_child_warehouse(child_wh.id, main_wh.id, org.id)
            
            # Create inventory item
            item = InventoryItem(
                organisation_id=org.id,
                name="Test Item",
                sku="TEST-001",
                unit_price=100,
                quantity=5
            )
            db.session.add(item)
            db.session.commit()
            
            # Add insufficient stock
            stock = WarehouseStock(
                item_id=item.id,
                warehouse_id=main_wh.id,
                quantity_on_hand=3,
                quantity_reserved=0
            )
            db.session.add(stock)
            db.session.commit()
            
            # Try to transfer more than available
            stock_service = StockService()
            with pytest.raises(ValueError, match="Insufficient stock"):
                stock_service.transfer_with_hierarchy(
                    item_id=item.id,
                    org_id=org.id,
                    quantity=5,
                    from_warehouse_id=main_wh.id,
                    to_warehouse_id=child_wh.id,
                    commit=True
                )
