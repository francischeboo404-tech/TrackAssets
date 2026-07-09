"""
Comprehensive supply chain module tests.

Tests cover:
- Purchase Request workflow (create, approve, reject, update)
- Requisition Slip workflow (create, approve, issue, return)
- Purchase Order workflow (create, approve, reject, cancel)
- Goods Receipt Note workflow (create, inspection, approval)
- Stock verification and audit trails
- End-to-end supply chain pipelines
"""

import pytest
from datetime import date
from decimal import Decimal
from app import create_app, db
from app.models.organization import Organization, Department
from app.models.user import User
from app.models.location_topology import Warehouse
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.models.supplier import Supplier
from app.models.asset import Asset
from app.models.stock_levels import WarehouseStock
from app.models.kenya_gov_models import (
    PurchaseRequest, PurchaseRequestItem,
    RequisitionSlip, RequisitionItem,
    PurchaseOrder, PurchaseOrderItem,
    GoodsReceiptNote, GoodsReceiptItem,
    InspectionReport
)
from app.services.procurement_service import ProcurementService
from app.services.requisition_service import RequisitionService
from app.services.receiving_service import ReceivingService
from app.services.stock_service import StockService
from flask_jwt_extended import create_access_token


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
    org = Organization(name="Test Org", code="TEST")
    db.session.add(org)
    db.session.commit()
    return org


@pytest.fixture
def test_user(test_org):
    """Create test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        organisation_id=test_org.id,
        role="admin"
    )
    user.set_password("TestPassword123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_departments(test_org):
    """Create test departments."""
    dept_ops = Department(name="Operations", code="OPS", organisation_id=test_org.id)
    dept_warehouse = Department(name="Warehouse", code="WH", organisation_id=test_org.id)
    db.session.add_all([dept_ops, dept_warehouse])
    db.session.commit()
    return {"operations": dept_ops, "warehouse": dept_warehouse}


@pytest.fixture
def test_warehouse(test_org):
    """Create test warehouse."""
    warehouse = Warehouse(
        name="Main Warehouse",
        code="MW",
        organisation_id=test_org.id,
        address="123 Main St"
    )
    db.session.add(warehouse)
    db.session.commit()
    return warehouse


@pytest.fixture
def test_supplier(test_org):
    """Create test supplier."""
    supplier = Supplier(
        name="Test Supplier",
        code="TS001",
        organisation_id=test_org.id,
        email="supplier@example.com",
        phone="1234567890",
        average_lead_time_days=7,
        reliability_score=0.95
    )
    db.session.add(supplier)
    db.session.commit()
    return supplier


@pytest.fixture
def test_inventory_item(test_org, test_warehouse):
    """Create test inventory item with stock."""
    item = InventoryItem(
        name="Test Item",
        sku="TEST-001",
        unit_price=100.00,
        reorder_level=10,
        organisation_id=test_org.id,
    )
    db.session.add(item)
    db.session.commit()
    
    # Add warehouse stock
    stock = WarehouseStock(
        item_id=item.id,
        warehouse_id=test_warehouse.id,
        quantity_on_hand=50,
        quantity_reserved=0
    )
    db.session.add(stock)
    db.session.commit()
    
    return item


@pytest.fixture
def auth_headers(test_user):
    """Create JWT auth headers."""
    token = create_access_token(identity=test_user.id)
    return {"Authorization": f"Bearer {token}"}


class TestPurchaseRequestWorkflow:
    """Test PR creation, approval, rejection, and updates."""
    
    def test_create_purchase_request(self, test_org, test_user, test_inventory_item):
        """Verify PR creation saves all data."""
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[
                {
                    "item_id": test_inventory_item.id,
                    "quantity": 10,
                    "estimated_cost": 1000.00,
                    "justification": "Low stock"
                }
            ]
        )
        
        assert pr.pr_number.startswith("PR-")
        assert pr.status == "pending"
        assert pr.organization_id == test_org.id
        
        # Verify items saved
        items = PurchaseRequestItem.query.filter_by(pr_id=pr.id).all()
        assert len(items) == 1
        assert items[0].item_id == test_inventory_item.id
        assert items[0].quantity == 10
    
    def test_approve_purchase_request(self, test_org, test_user, test_inventory_item):
        """Verify PR approval updates status."""
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "estimated_cost": 1000.00}]
        )
        
        approved_pr = ProcurementService.approve_purchase_request(pr.id, department_head_id=test_user.id)
        
        assert approved_pr.status == "approved"
        assert approved_pr.department_head_id == test_user.id
        assert approved_pr.approved_at is not None

    def test_create_purchase_request_with_asset_item(self, test_org, test_user, test_departments):
        """Verify PR creation persists asset-backed items with explicit item_type."""
        asset = Asset(
            organisation_id=test_org.id,
            asset_code="AST-100",
            name="Laptop",
            type="IT",
            department_id=test_departments['operations'].id,
            purchase_date=date.today(),
            purchase_value=Decimal("1200.00"),
            useful_life=5,
            current_value=Decimal("1200.00"),
        )
        db.session.add(asset)
        db.session.commit()

        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Acquisition of fixed assets",
            items_data=[{
                "item_type": "asset",
                "asset_id": asset.id,
                "quantity": 1,
                "estimated_cost": 1200.00,
                "justification": "Needed for operations"
            }]
        )

        item = PurchaseRequestItem.query.filter_by(pr_id=pr.id).first()
        assert item is not None
        assert item.item_type == "asset"
        assert item.asset_id == asset.id
        assert item.item_id is None
    
    def test_reject_purchase_request(self, test_org, test_user, test_inventory_item):
        """Verify PR rejection."""
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "estimated_cost": 1000.00}]
        )
        
        rejected_pr = ProcurementService.reject_purchase_request(pr.id, department_head_id=test_user.id)
        
        assert rejected_pr.status == "rejected"
    
    def test_cannot_create_po_from_unapproved_pr(self, test_org, test_user, test_inventory_item, test_supplier):
        """Verify PO creation requires approved PR."""
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "estimated_cost": 1000.00}]
        )
        
        with pytest.raises(Exception):  # Should raise ValidationError
            ProcurementService.create_purchase_order(
                org_id=test_org.id,
                pr_id=pr.id,
                supplier_id=test_supplier.id,
                items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "unit_cost": 100.00, "total_cost": 1000.00}]
            )


class TestPurchaseOrderWorkflow:
    """Test PO creation, approval, and status management."""
    
    def test_create_po_from_approved_pr(self, test_org, test_user, test_inventory_item, test_supplier):
        """Verify PO creation from approved PR."""
        # Create and approve PR
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "estimated_cost": 1000.00}]
        )
        ProcurementService.approve_purchase_request(pr.id, department_head_id=test_user.id)
        
        # Create PO from approved PR
        po = ProcurementService.create_purchase_order(
            org_id=test_org.id,
            pr_id=pr.id,
            supplier_id=test_supplier.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "unit_cost": 100.00, "total_cost": 1000.00}]
        )
        
        assert po.po_number.startswith("PO-")
        assert po.status == "pending"
        assert po.pr_id == pr.id
        assert po.supplier_id == test_supplier.id
        
        # Verify PO items saved
        items = PurchaseOrderItem.query.filter_by(po_id=po.id).all()
        assert len(items) == 1
    
    def test_approve_po(self, test_org, test_user, test_inventory_item, test_supplier):
        """Verify PO approval."""
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 5, "estimated_cost": 450.00}]
        )
        ProcurementService.approve_purchase_request(pr.id, department_head_id=test_user.id)
        
        po = ProcurementService.create_purchase_order(
            org_id=test_org.id,
            pr_id=pr.id,
            supplier_id=test_supplier.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 5, "unit_cost": 90.00, "total_cost": 450.00}]
        )
        
        # Approve PO (no canvass for < KES 1000)
        approved_po = ProcurementService.approve_purchase_order(po.id, user_id=test_user.id)
        
        assert approved_po.status == "approved"
        assert approved_po.approved_at is not None


class TestRequisitionWorkflow:
    """Test RIS creation, approval, issuance, and returns."""
    
    def test_create_requisition(self, test_org, test_user, test_inventory_item):
        """Verify RIS creation."""
        ris = RequisitionService.create_requisition(
            org_id=test_org.id,
            requester_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 5, "unit_cost": 100.00}]
        )
        
        assert ris.ris_number.startswith("RIS-")
        assert ris.status == "pending"
        
        items = RequisitionItem.query.filter_by(ris_id=ris.id).all()
        assert len(items) == 1
        assert items[0].quantity_requested == 5
    
    def test_create_requisition_with_asset_item(self, test_org, test_user, test_departments):
        """Verify RIS creation persists asset-backed items with explicit item_type."""
        asset = Asset(
            organisation_id=test_org.id,
            asset_code="AST-101",
            name="Projector",
            type="IT",
            department_id=test_departments['operations'].id,
            purchase_date=date.today(),
            purchase_value=Decimal("900.00"),
            useful_life=4,
            current_value=Decimal("900.00"),
        )
        db.session.add(asset)
        db.session.commit()

        ris = RequisitionService.create_requisition(
            org_id=test_org.id,
            requester_id=test_user.id,
            items_data=[{
                "item_type": "asset",
                "asset_id": asset.id,
                "quantity": 1,
                "unit_cost": 900.00,
            }]
        )

        item = RequisitionItem.query.filter_by(ris_id=ris.id).first()
        assert item is not None
        assert item.item_type == "asset"
        assert item.asset_id == asset.id
        assert item.item_id is None

    def test_approve_requisition(self, test_org, test_user, test_inventory_item):
        """Verify RIS approval."""
        ris = RequisitionService.create_requisition(
            org_id=test_org.id,
            requester_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 5, "unit_cost": 100.00}]
        )
        
        approved_ris = RequisitionService.approve_requisition(ris.id, department_head_id=test_user.id)
        
        assert approved_ris.status == "approved"
        assert approved_ris.approved_date is not None
    
    def test_issue_requisition_decreases_warehouse_stock(self, test_org, test_user, test_inventory_item, test_warehouse):
        """Verify requisition issuance deducts stock from warehouse."""
        # Setup: Get initial stock
        initial_stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouse.id
        ).first()
        initial_qty = initial_stock.quantity_on_hand
        
        # Create and approve requisition
        ris = RequisitionService.create_requisition(
            org_id=test_org.id,
            requester_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 5, "unit_cost": 100.00, "warehouse_id": test_warehouse.id}]
        )
        RequisitionService.approve_requisition(ris.id, department_head_id=test_user.id)
        
        # Issue requisition
        issued_ris = RequisitionService.issue_requisition(ris.id)
        
        assert issued_ris.status == "issued"
        
        # Verify stock decreased
        updated_stock = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouse.id
        ).first()
        assert updated_stock.quantity_on_hand == initial_qty - 5
        
        # Verify StockMovement created
        movements = StockMovement.query.filter_by(
            item_id=test_inventory_item.id,
            reference=ris.ris_number
        ).all()
        assert len(movements) > 0
        assert any(m.type == 'OUT' for m in movements)
    
    def test_return_requisition_increases_warehouse_stock(self, test_org, test_user, test_inventory_item, test_warehouse):
        """Verify requisition return adds stock back."""
        # Create, approve, and issue RIS
        ris = RequisitionService.create_requisition(
            org_id=test_org.id,
            requester_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 5, "unit_cost": 100.00, "warehouse_id": test_warehouse.id}]
        )
        RequisitionService.approve_requisition(ris.id, department_head_id=test_user.id)
        RequisitionService.issue_requisition(ris.id)
        
        # Get stock after issue
        stock_after_issue = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouse.id
        ).first()
        qty_after_issue = stock_after_issue.quantity_on_hand
        
        # Return issued items
        returned_ris = RequisitionService.return_to_store(ris.id, returned_by_id=test_user.id)
        
        assert returned_ris.status == "returned"
        
        # Verify stock increased
        stock_after_return = WarehouseStock.query.filter_by(
            item_id=test_inventory_item.id,
            warehouse_id=test_warehouse.id
        ).first()
        assert stock_after_return.quantity_on_hand == qty_after_issue + 5


class TestGoodsReceiptNoteWorkflow:
    """Test GRN creation, inspection, and approval."""
    
    def test_create_grn_from_approved_po(self, test_org, test_user, test_inventory_item, test_supplier):
        """Verify GRN creation from approved PO."""
        # Setup: Create and approve PO
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "estimated_cost": 450.00}]
        )
        ProcurementService.approve_purchase_request(pr.id, department_head_id=test_user.id)
        
        po = ProcurementService.create_purchase_order(
            org_id=test_org.id,
            pr_id=pr.id,
            supplier_id=test_supplier.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "unit_cost": 45.00, "total_cost": 450.00}]
        )
        ProcurementService.approve_purchase_order(po.id, user_id=test_user.id)
        
        # Create GRN
        grn = ReceivingService.create_grn(
            org_id=test_org.id,
            po_id=po.id,
            received_by_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity_received": 10, "unit_cost": 45.00}],
            invoice_number="INV-001",
            delivery_note_number="DN-001"
        )
        
        assert grn.grn_number.startswith("GRN-")
        assert grn.status == "quarantine"
        assert grn.po_id == po.id
        
        items = GoodsReceiptItem.query.filter_by(grn_id=grn.id).all()
        assert len(items) == 1
        assert items[0].quantity_received == 10
    
    def test_grn_inspection_processing_adds_stock(self, test_org, test_user, test_inventory_item, test_supplier):
        """Verify GRN inspection approval adds stock."""
        # Setup: Create GRN
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "estimated_cost": 450.00}]
        )
        ProcurementService.approve_purchase_request(pr.id, department_head_id=test_user.id)
        
        po = ProcurementService.create_purchase_order(
            org_id=test_org.id,
            pr_id=pr.id,
            supplier_id=test_supplier.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "unit_cost": 45.00, "total_cost": 450.00}]
        )
        ProcurementService.approve_purchase_order(po.id, user_id=test_user.id)
        
        grn = ReceivingService.create_grn(
            org_id=test_org.id,
            po_id=po.id,
            received_by_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity_received": 10, "unit_cost": 45.00}]
        )
        
        # Get initial stock
        initial_stock = StockService(session=db.session).get_current_quantity(test_inventory_item.id)
        
        # Get GRN item and process inspection
        grn_items = GoodsReceiptItem.query.filter_by(grn_id=grn.id).all()
        
        iar = ReceivingService.process_inspection_items(
            org_id=test_org.id,
            grn_id=grn.id,
            inspector_id=test_user.id,
            items_data=[{"grn_item_id": grn_items[0].id, "quantity_accepted": 10, "quantity_rejected": 0}],
            comments="All items passed inspection"
        )
        
        assert iar.status == "passed"
        
        # Verify GRN status updated
        grn_updated = db.session.get(GoodsReceiptNote, grn.id)
        assert grn_updated.status == "approved"
        
        # Verify stock increased
        final_stock = StockService(session=db.session).get_current_quantity(test_inventory_item.id)
        assert final_stock == initial_stock + 10


class TestEndToEndSupplyChainPipeline:
    """Test complete supply chain workflows."""
    
    def test_full_procurement_pipeline_pr_to_po_to_grn_to_stock(self, test_org, test_user, test_inventory_item, test_supplier):
        """Verify complete procurement: PR → PO → GRN → Stock addition."""
        # Step 1: Create and approve PR
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Replenishment",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 20, "estimated_cost": 450.00}]
        )
        assert pr.status == "pending"
        
        pr = ProcurementService.approve_purchase_request(pr.id, department_head_id=test_user.id)
        assert pr.status == "approved"
        
        # Step 2: Create and approve PO
        po = ProcurementService.create_purchase_order(
            org_id=test_org.id,
            pr_id=pr.id,
            supplier_id=test_supplier.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 20, "unit_cost": 22.50, "total_cost": 450.00}]
        )
        assert po.status == "pending"
        
        po = ProcurementService.approve_purchase_order(po.id, user_id=test_user.id)
        assert po.status == "approved"
        
        # Step 3: Create and process GRN
        initial_stock = StockService(session=db.session).get_current_quantity(test_inventory_item.id)
        
        grn = ReceivingService.create_grn(
            org_id=test_org.id,
            po_id=po.id,
            received_by_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity_received": 20, "unit_cost": 22.50}]
        )
        assert grn.status == "quarantine"
        
        # Step 4: Process inspection and approve GRN
        grn_items = GoodsReceiptItem.query.filter_by(grn_id=grn.id).all()
        iar = ReceivingService.process_inspection_items(
            org_id=test_org.id,
            grn_id=grn.id,
            inspector_id=test_user.id,
            items_data=[{"grn_item_id": grn_items[0].id, "quantity_accepted": 20, "quantity_rejected": 0}]
        )
        
        assert iar.status == "passed"
        
        # Step 5: Verify stock increased
        final_stock = StockService(session=db.session).get_current_quantity(test_inventory_item.id)
        assert final_stock == initial_stock + 20
        
        # Verify PO status updated to received
        po_updated = db.session.get(PurchaseOrder, po.id)
        assert po_updated.status == "received"
    
    def test_full_requisition_pipeline_create_issue_return(self, test_org, test_user, test_inventory_item, test_warehouse):
        """Verify complete requisition: Create → Approve → Issue → Return."""
        initial_stock = StockService(session=db.session).get_current_quantity(test_inventory_item.id)
        
        # Step 1: Create RIS
        ris = RequisitionService.create_requisition(
            org_id=test_org.id,
            requester_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 15, "unit_cost": 100.00, "warehouse_id": test_warehouse.id}]
        )
        assert ris.status == "pending"
        
        # Step 2: Approve RIS
        ris = RequisitionService.approve_requisition(ris.id, department_head_id=test_user.id)
        assert ris.status == "approved"
        
        # Step 3: Issue RIS (should decrease stock)
        ris = RequisitionService.issue_requisition(ris.id)
        assert ris.status == "issued"
        
        stock_after_issue = StockService(session=db.session).get_current_quantity(test_inventory_item.id)
        assert stock_after_issue == initial_stock - 15
        
        # Step 4: Return items (should increase stock)
        ris = RequisitionService.return_to_store(ris.id, returned_by_id=test_user.id)
        assert ris.status == "returned"
        
        stock_after_return = StockService(session=db.session).get_current_quantity(test_inventory_item.id)
        assert stock_after_return == initial_stock


class TestSupplierRegistry:
    """Test supplier management operations."""
    
    def test_create_supplier(self, test_org):
        """Verify supplier creation."""
        supplier = Supplier(
            organisation_id=test_org.id,
            name="New Supplier",
            code="NS001",
            email="new@supplier.com",
            phone="9876543210",
            average_lead_time_days=5,
            reliability_score=0.90
        )
        db.session.add(supplier)
        db.session.commit()
        
        assert supplier.id is not None
        assert supplier.code == "NS001"
        assert supplier.reliability_score == 0.90
    
    def test_list_suppliers(self, test_org, test_supplier):
        """Verify supplier listing."""
        suppliers = Supplier.query.filter_by(organisation_id=test_org.id, is_active=True).all()
        
        assert len(suppliers) >= 1
        assert any(s.code == "TS001" for s in suppliers)


class TestStockMovementAuditTrail:
    """Test StockMovement creation and audit trail."""
    
    def test_stock_movement_created_on_requisition_issue(self, test_org, test_user, test_inventory_item, test_warehouse):
        """Verify StockMovement created when requisition issued."""
        ris = RequisitionService.create_requisition(
            org_id=test_org.id,
            requester_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 5, "unit_cost": 100.00, "warehouse_id": test_warehouse.id}]
        )
        RequisitionService.approve_requisition(ris.id, department_head_id=test_user.id)
        RequisitionService.issue_requisition(ris.id)
        
        # Verify StockMovement created
        movements = StockMovement.query.filter_by(
            item_id=test_inventory_item.id,
            reference=ris.ris_number
        ).all()
        
        assert len(movements) > 0
        assert any(m.type == 'OUT' for m in movements)
    
    def test_stock_movement_created_on_grn_approval(self, test_org, test_user, test_inventory_item, test_supplier):
        """Verify StockMovement created when GRN approved."""
        # Setup and create GRN
        pr = ProcurementService.create_purchase_request(
            org_id=test_org.id,
            requester_id=test_user.id,
            reason="Need supplies",
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "estimated_cost": 450.00}]
        )
        ProcurementService.approve_purchase_request(pr.id, department_head_id=test_user.id)
        
        po = ProcurementService.create_purchase_order(
            org_id=test_org.id,
            pr_id=pr.id,
            supplier_id=test_supplier.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity": 10, "unit_cost": 45.00, "total_cost": 450.00}]
        )
        ProcurementService.approve_purchase_order(po.id, user_id=test_user.id)
        
        grn = ReceivingService.create_grn(
            org_id=test_org.id,
            po_id=po.id,
            received_by_id=test_user.id,
            items_data=[{"item_id": test_inventory_item.id, "quantity_received": 10, "unit_cost": 45.00}]
        )
        
        # Process inspection
        grn_items = GoodsReceiptItem.query.filter_by(grn_id=grn.id).all()
        ReceivingService.process_inspection_items(
            org_id=test_org.id,
            grn_id=grn.id,
            inspector_id=test_user.id,
            items_data=[{"grn_item_id": grn_items[0].id, "quantity_accepted": 10, "quantity_rejected": 0}]
        )
        
        # Verify StockMovement created
        movements = StockMovement.query.filter_by(
            item_id=test_inventory_item.id,
            reference=grn.grn_number
        ).all()
        
        assert len(movements) > 0
        assert any(m.type == 'IN' for m in movements)
