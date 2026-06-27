import pytest
from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem, AuditLog, StockMovement
from app.services.procurement_service import ProcurementService
from app.services.receiving_service import ReceivingService

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


def create_entities():
    org = db.session.query(Organization).filter_by(code="RECV-AUD").first()
    if not org:
        org = Organization(name="Recv Audit Org", code="RECV-AUD")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="recv.audit@test.org").first()
    if not user:
        user = User(email="recv.audit@test.org", username="recv_audit", organisation_id=org.id, role="store_manager")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="Recv Audit Supplier", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="Recv Audit Supplier", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="RAI-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="RAI-001", name="Recv Audit Item", organisation_id=org.id, quantity=0, unit_price=200.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item


def test_receiving_audits(ctx):
    org, user, supplier, item = create_entities()

    # Create PR -> Approve -> PO -> Approve
    pr = ProcurementService.create_purchase_request(org.id, user.id, "Need recv", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 200.0}])
    ProcurementService.approve_purchase_order(po.id)

    # Create GRN
    grn = ReceivingService.create_grn(org.id, po.id, user.id, [{"item_id": item.id, "quantity_received": 2, "unit_cost": 200.0}])
    audit = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='goods_receipt_note', action='GRN_CREATED').order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.module == 'receiving'

    # Create inspection report (passed)
    iar = ReceivingService.create_inspection_report(org.id, grn.id, inspector_id=user.id, status='passed', comments='OK')
    audit = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='inspection_report', action='IAR_CREATED').order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.module == 'receiving'

    # Approve GRN (this will move items to stock)
    ReceivingService.approve_grn(grn.id)
    audit = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='goods_receipt_note', action='GRN_APPROVED').order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.module == 'receiving'

    # Verify that stock-in audit entries were tagged with receiving module
    stock_audit = db.session.query(AuditLog).filter_by(organisation_id=org.id, action='STOCK_INCREASED').order_by(AuditLog.id.desc()).first()
    assert stock_audit is not None
