import pytest
from app import create_app, db
from app.blueprints.receiving import _serialize_datetime_value
from app.models.organization import Organization, Department
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.models.asset import Asset
from app.models.location_topology import Warehouse
from app.models.kenya_gov_models import PurchaseRequest, PurchaseRequestItem, GoodsReceiptItem
from app.services.procurement_service import ProcurementService
from app.services.receiving_service import ReceivingService
from app.errors import NotFoundError, ValidationError
from datetime import datetime, timezone

TEST_APP = None


def setup_module(module):
    global TEST_APP
    TEST_APP = create_app('testing')
    with TEST_APP.app_context():
        db.create_all()


def teardown_module(module):
    global TEST_APP
    with TEST_APP.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def ctx():
    global TEST_APP
    with TEST_APP.app_context():
        yield


def create_procurement_entities():
    org = db.session.query(Organization).filter_by(code="TEST-RECV").first()
    if not org:
        org = Organization(name="Recv Org", code="TEST-RECV")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="recv@test.org").first()
    if not user:
        user = User(email="recv@test.org", username="recv", organisation_id=org.id, role="store_manager")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="Recv Supplier", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="Recv Supplier", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    warehouse = db.session.query(Warehouse).filter_by(name="Main Warehouse", organisation_id=org.id).first()
    if not warehouse:
        warehouse = Warehouse(
            name="Main Warehouse",
            code="WH-001",
            organisation_id=org.id,
            is_main_warehouse=True,
            warehouse_type="main",
            hierarchy_level=0
        )
        db.session.add(warehouse)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="RECV-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="RECV-001", name="Recv Item", organisation_id=org.id, quantity=0, unit_price=500.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item, warehouse


def test_missing_po(ctx):
    org, user, supplier, item, warehouse = create_procurement_entities()
    with pytest.raises(NotFoundError):
        ReceivingService.create_grn(org.id, po_id=9999, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 1, "unit_cost": 500.0, "warehouse_id": warehouse.id}])


def test_invalid_po_for_org(ctx):
    org, user, supplier, item, warehouse = create_procurement_entities()
    # Create a PO under a different org
    other_org = Organization(name="Other Org", code="OTHER-01")
    db.session.add(other_org)
    db.session.commit()
    
    # Create an item for other_org to satisfy tenant isolation checks in ProcurementService
    other_item = InventoryItem(organisation_id=other_org.id, name="Other Item", sku="OTHER-SKU-001", unit_price=500.0)
    db.session.add(other_item)
    db.session.commit()

    pr = ProcurementService.create_purchase_request(other_org.id, user.id, "Other PR", [{"item_id": other_item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    # create a supplier for the other org so the PO can be created under that org
    other_supplier = Supplier(name="Other Supplier", organisation_id=other_org.id)
    db.session.add(other_supplier)
    db.session.commit()

    po = ProcurementService.create_purchase_order(other_org.id, pr.id, other_supplier.id, [{"item_id": other_item.id, "quantity": 2, "unit_cost": 500.0}])

    with pytest.raises(ValidationError):
        ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": other_item.id, "quantity_received": 1, "unit_cost": 500.0, "warehouse_id": warehouse.id}])


def test_quantity_mismatch_over_delivery(ctx):
    org, user, supplier, item, warehouse = create_procurement_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for qty test", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 500.0}])

    # Try to receive more than PO quantity
    with pytest.raises(ValidationError):
        ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 3, "unit_cost": 500.0, "warehouse_id": warehouse.id}])


def test_unit_cost_mismatch(ctx):
    org, user, supplier, item, warehouse = create_procurement_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for unit cost", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 500.0}])

    # unit_cost mismatch in GRN should raise ValidationError
    with pytest.raises(ValidationError):
        ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 2, "unit_cost": 499.0, "warehouse_id": warehouse.id}])


def test_approve_grn_without_passed_iar(ctx):
    org, user, supplier, item, warehouse = create_procurement_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for approval test", [{"item_id": item.id, "quantity": 1}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 1, "unit_cost": 500.0}])
    ProcurementService.approve_purchase_order(po.id)

    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 1, "unit_cost": 500.0, "warehouse_id": warehouse.id}])
    # No inspection report created (or a failed one), approving should raise ValidationError
    with pytest.raises(ValidationError):
        ReceivingService.approve_grn(grn.id)


def test_successful_grn_and_approval(ctx):
    org, user, supplier, item, warehouse = create_procurement_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for success", [{"item_id": item.id, "quantity": 5}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 5, "unit_cost": 500.0}])

    # Add canvass quotes (requirement for orders >= KES 1,000)
    from datetime import datetime, timezone
    ProcurementService.add_canvass_quote(org.id, po.id, "Supplier A", item.name, 510, datetime.now(timezone.utc))
    ProcurementService.add_canvass_quote(org.id, po.id, "Supplier B", item.name, 520, datetime.now(timezone.utc))
    ProcurementService.add_canvass_quote(org.id, po.id, "Supplier C", item.name, 490, datetime.now(timezone.utc))

    # Approve PO before receiving
    ProcurementService.approve_purchase_order(po.id)

    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 5, "unit_cost": 500.0, "warehouse_id": warehouse.id}])
    assert grn is not None

    # Create inspection report (passed)
    iar = ReceivingService.create_inspection_report(org.id, grn.id, inspector_id=user.id, status='passed', comments='OK')
    assert iar is not None

    # Approve GRN -> should move quantities into stock
    item_before = db.session.get(InventoryItem, item.id)
    qty_before = item_before.quantity
    ReceivingService.approve_grn(grn.id)
    db.session.refresh(item)
    assert item.quantity == qty_before + 5


def test_serialize_datetime_value_handles_strings_and_dates():
    assert _serialize_datetime_value(None) is None
    assert _serialize_datetime_value("2026-01-02") == "2026-01-02"
    assert _serialize_datetime_value(datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)) == "2026-01-02T03:04:05+00:00"


def test_asset_grn_item_is_categorized(ctx):
    org, user, supplier, item, warehouse = create_procurement_entities()
    department = db.session.query(Department).filter_by(organisation_id=org.id, code="ASSET-DPT").first()
    if not department:
        department = Department(organisation_id=org.id, name="Asset Dept", code="ASSET-DPT", warehouse_id=None)
        db.session.add(department)
        db.session.commit()

    asset = Asset(
        organisation_id=org.id,
        asset_code="AST-001",
        name="Laptop",
        type="IT",
        department_id=department.id,
        purchase_date=datetime.now(timezone.utc).date(),
        purchase_value=120000.0,
        useful_life=5,
        current_value=120000.0,
    )
    db.session.add(asset)
    db.session.commit()

    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for asset receipt", [{"item_id": item.id, "quantity": 1}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 1, "unit_cost": 500.0}])
    ProcurementService.approve_purchase_order(po.id)

    grn = ReceivingService.create_grn(
        org.id,
        po_id=po.id,
        received_by_id=user.id,
        items_data=[{
            "item_type": "asset",
            "asset_id": asset.id,
            "quantity_received": 1,
            "unit_cost": 120000.0,
            "warehouse_id": warehouse.id,
        }],
    )

    grn_item = db.session.query(GoodsReceiptItem).filter_by(grn_id=grn.id).first()
    assert grn_item is not None
    assert grn_item.item_type == "asset"
    assert grn_item.asset_id == asset.id


def test_mixed_inventory_and_asset_grn_approval_is_supported(ctx):
    org, user, supplier, item, warehouse = create_procurement_entities()
    department = db.session.query(Department).filter_by(organisation_id=org.id, code="ASSET-DPT").first()
    if not department:
        department = Department(organisation_id=org.id, name="Asset Dept", code="ASSET-DPT", warehouse_id=None)
        db.session.add(department)
        db.session.commit()

    asset = Asset(
        organisation_id=org.id,
        asset_code="AST-002",
        name="Monitor",
        type="IT",
        department_id=department.id,
        purchase_date=datetime.now(timezone.utc).date(),
        purchase_value=30000.0,
        useful_life=5,
        current_value=30000.0,
    )
    db.session.add(asset)
    db.session.commit()

    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for mixed GRN", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 500.0}])
    ProcurementService.approve_purchase_order(po.id)

    grn = ReceivingService.create_grn(
        org.id,
        po_id=po.id,
        received_by_id=user.id,
        items_data=[
            {
                "item_type": "inventory",
                "item_id": item.id,
                "quantity_received": 2,
                "unit_cost": 500.0,
                "warehouse_id": warehouse.id,
            },
            {
                "item_type": "asset",
                "asset_id": asset.id,
                "quantity_received": 1,
                "unit_cost": 30000.0,
                "warehouse_id": warehouse.id,
            },
        ],
    )

    iar = ReceivingService.create_inspection_report(org.id, grn.id, inspector_id=user.id, status="passed", comments="OK")
    assert iar is not None

    qty_before = item.quantity

    ReceivingService.approve_grn(grn.id)
    db.session.refresh(item)
    assert item.quantity == qty_before + 2
    db.session.refresh(asset)
    assert asset.status == "available"

