import pytest
from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.services.procurement_service import ProcurementService
from app.errors import ValidationError, NotFoundError, ConflictError
from datetime import datetime, timezone


TEST_APP = None


def setup_module(module):
    global TEST_APP
    TEST_APP = create_app('testing')
    with TEST_APP.app_context():
        db.create_all()


def teardown_module(module):
    global TEST_APP
    if TEST_APP is None:
        TEST_APP = create_app('testing')
    with TEST_APP.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def ctx():
    global TEST_APP
    if TEST_APP is None:
        TEST_APP = create_app('testing')
        with TEST_APP.app_context():
            db.create_all()
    with TEST_APP.app_context():
        yield


def create_base_entities():
    # Idempotent create or get
    org = db.session.query(Organization).filter_by(code="TEST-01").first()
    if not org:
        org = Organization(name="Test Org", code="TEST-01")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="proc@test.org").first()
    if not user:
        user = User(email="proc@test.org", username="proc", organisation_id=org.id, role="admin")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="ACME Supplies", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="ACME Supplies", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="ITM-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="ITM-001", name="Test Item", organisation_id=org.id, quantity=100, unit_price=100.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item


def test_invalid_pr_for_po(ctx):
    org, user, supplier, item = create_base_entities()
    with pytest.raises(NotFoundError):
        ProcurementService.create_purchase_order(org.id, pr_id=9999, supplier_id=supplier.id, items_data=[{"item_id": item.id, "quantity": 1, "unit_cost": 100.0}])


def test_unapproved_pr_for_po(ctx):
    org, user, supplier, item = create_base_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "Need item", [{"item_id": item.id, "quantity": 5}])
    with pytest.raises(ValidationError):
        ProcurementService.create_purchase_order(org.id, pr_id=pr.id, supplier_id=supplier.id, items_data=[{"item_id": item.id, "quantity": 1, "unit_cost": 100.0}])


def test_duplicate_po_creation_blocked(ctx):
    org, user, supplier, item = create_base_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "Need items", [{"item_id": item.id, "quantity": 5}])
    ProcurementService.approve_purchase_request(pr.id, user.id)

    po1 = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 100.0}])
    assert po1 is not None

    with pytest.raises(ConflictError):
        ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 1, "unit_cost": 100.0}])


def test_successful_po_creation(ctx):
    org, user, supplier, item = create_base_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "Need items", [{"item_id": item.id, "quantity": 5}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 3, "unit_cost": 150.0}])
    assert po is not None
    assert po.pr_id == pr.id
    assert float(po.total_amount) == 3 * 150.0


def test_list_purchase_orders_can_filter_receivable_statuses(ctx):
    org, user, supplier, item = create_base_entities()

    approved_pr = ProcurementService.create_purchase_request(org.id, user.id, "Approved request", [{"item_id": item.id, "quantity": 4}])
    ProcurementService.approve_purchase_request(approved_pr.id, user.id)
    approved_po = ProcurementService.create_purchase_order(org.id, approved_pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 120.0}])
    ProcurementService.approve_purchase_order(approved_po.id, user.id)

    pending_pr = ProcurementService.create_purchase_request(org.id, user.id, "Pending request", [{"item_id": item.id, "quantity": 4}])
    ProcurementService.approve_purchase_request(pending_pr.id, user.id)
    ProcurementService.create_purchase_order(org.id, pending_pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 100.0}])

    receivable_pos = ProcurementService.list_purchase_orders(org.id, statuses=["approved", "partially_received", "received"])

    assert len(receivable_pos) == 1
    assert receivable_pos[0].id == approved_po.id
    assert receivable_pos[0].status == "approved"


def test_po_item_exceeds_pr_quantity(ctx):
    org, user, supplier, item = create_base_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "Need small amount", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    with pytest.raises(ValidationError):
        ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 3, "unit_cost": 100.0}])

def test_supplier_org_mismatch(ctx):
    org, user, supplier, item = create_base_entities()
    # Create a different organisation and supplier belonging to it
    other_org = Organization(name="Other Org", code="OTHER-01")
    db.session.add(other_org)
    db.session.commit()
    other_supplier = Supplier(name="Other Supplies", organisation_id=other_org.id)
    db.session.add(other_supplier)
    db.session.commit()

    pr = ProcurementService.create_purchase_request(org.id, user.id, "Need items", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    with pytest.raises(ValidationError):
        ProcurementService.create_purchase_order(org.id, pr.id, other_supplier.id, [{"item_id": item.id, "quantity": 1, "unit_cost": 100.0}])

def test_supplier_inactive(ctx):
    org, user, supplier, item = create_base_entities()
    supplier.is_active = False
    db.session.commit()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "Need items", [{"item_id": item.id, "quantity": 1}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    with pytest.raises(NotFoundError):
        ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 1, "unit_cost": 100.0}])

def test_pr_belongs_to_another_org(ctx):
    org, user, supplier, item = create_base_entities()
    # Create a separate organisation and item for it
    other_org = Organization(name="Other Org 2", code="OTHER-02")
    db.session.add(other_org)
    db.session.commit()
    other_user = User(email="other@org.org", username="other", organisation_id=other_org.id, role="admin")
    other_user.set_password("Password123!")
    db.session.add(other_user)
    db.session.commit()
    other_item = InventoryItem(sku="ITM-OTHER-001", name="Other Item", organisation_id=other_org.id, quantity=10, unit_price=10.0)
    db.session.add(other_item)
    db.session.commit()

    pr = ProcurementService.create_purchase_request(other_org.id, other_user.id, "External PR", [{"item_id": other_item.id, "quantity": 1}])
    ProcurementService.approve_purchase_request(pr.id, other_user.id)
    with pytest.raises(ValidationError):
        ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": other_item.id, "quantity": 1, "unit_cost": 10.0}])


def test_archived_pr_for_po(ctx):
    org, user, supplier, item = create_base_entities()
    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR to archive", [{"item_id": item.id, "quantity": 2}])
    # simulate archival
    pr.status = 'archived'
    db.session.commit()
    with pytest.raises(ValidationError):
        ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 1, "unit_cost": 100.0}])
