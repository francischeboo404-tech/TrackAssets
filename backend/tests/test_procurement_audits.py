import pytest
from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem, AuditLog
from app.services.procurement_service import ProcurementService

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
    org = db.session.query(Organization).filter_by(code="PROC-AUDIT").first()
    if not org:
        org = Organization(name="Proc Audit Org", code="PROC-AUDIT")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="proc.audit@test.org").first()
    if not user:
        user = User(email="proc.audit@test.org", username="proc_audit", organisation_id=org.id, role="admin")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="Audit Supplier", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="Audit Supplier", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="PAI-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="PAI-001", name="Audit Item", organisation_id=org.id, quantity=10, unit_price=50.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item


def test_procurement_audits(ctx):
    org, user, supplier, item = create_base_entities()

    # Create PR and expect audit
    pr = ProcurementService.create_purchase_request(org.id, user.id, "Need audit", [{"item_id": item.id, "quantity": 2}])
    audit = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='purchase_request', action='PR_CREATED').order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.module == 'procurement'
    assert audit.user_id == user.id

    # Approve PR
    ProcurementService.approve_purchase_request(pr.id, user.id)
    audit = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='purchase_request', action='PR_APPROVED').order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.module == 'procurement'

    # Create PO and expect audit
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 1, "unit_cost": 50.0}])
    audit = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='purchase_order', action='PO_CREATED').order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.module == 'procurement'

    # Approve PO and expect audit
    ProcurementService.approve_purchase_order(po.id)
    audit = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='purchase_order', action='PO_APPROVED').order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.module == 'procurement'
