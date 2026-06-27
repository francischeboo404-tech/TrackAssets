import pytest
from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.models.kenya_gov_models import PurchaseRequest, PurchaseRequestItem
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

    item = db.session.query(InventoryItem).filter_by(sku="RECV-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="RECV-001", name="Recv Item", organisation_id=org.id, quantity=0, unit_price=500.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item


def test_missing_po(ctx):
    org, user, supplier, item = create_procurement_entities()
    with pytest.raises(NotFoundError):
        ReceivingService.create_grn(org.id, po_id=9999, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 1, "unit_cost": 500.0}])


def test_invalid_po_for_org(ctx):
    org, user, supplier, item = create_procurement_entities()
    # Create a PO under a different org
    other_org = Organization(name="Other Org", code="OTHER-01")
    db.session.add(other_org)
    db.session.commit()

    pr = ProcurementService.create_purchase_request(other_org.id, user.id, "Other PR", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    # create a supplier for the other org so the PO can be created under that org
    other_supplier = Supplier(name="Other Supplier", organisation_id=other_org.id)
    db.session.add(other_supplier)
    db.session.commit()

    po = ProcurementService.create_purchase_order(other_org.id, pr.id, other_supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 500.0}])

    with pytest.raises(ValidationError):
        ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 1, "unit_cost": 500.0}])


def test_quantity_mismatch_over_delivery(ctx):
    org, user, supplier, item = create_procurement_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for qty test", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 500.0}])

    # Try to receive more than PO quantity
    with pytest.raises(ValidationError):
        ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 3, "unit_cost": 500.0}])


def test_unit_cost_mismatch(ctx):
    org, user, supplier, item = create_procurement_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for unit cost", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 500.0}])

    # unit_cost mismatch in GRN should raise ValidationError
    with pytest.raises(ValidationError):
        ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 2, "unit_cost": 499.0}])


def test_approve_grn_without_passed_iar(ctx):
    org, user, supplier, item = create_procurement_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR for approval test", [{"item_id": item.id, "quantity": 1}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 1, "unit_cost": 500.0}])
    ProcurementService.approve_purchase_order(po.id)

    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 1, "unit_cost": 500.0}])
    # No inspection report created (or a failed one), approving should raise ValidationError
    with pytest.raises(ValidationError):
        ReceivingService.approve_grn(grn.id)


def test_successful_grn_and_approval(ctx):
    org, user, supplier, item = create_procurement_entities()
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

    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 5, "unit_cost": 500.0}])
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

