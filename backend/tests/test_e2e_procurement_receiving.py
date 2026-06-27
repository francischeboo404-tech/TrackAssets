import pytest
from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem, AuditLog
from app.models import StockCard, SuppliesLedgerCard
from app.services.procurement_service import ProcurementService
from app.services.receiving_service import ReceivingService
from app.services.report_analytics_service import ReportAnalyticsService

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
    org = db.session.query(Organization).filter_by(code="E2E-PROC-RECV").first()
    if not org:
        org = Organization(name="E2E Org", code="E2E-PROC-RECV")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="e2e@test.org").first()
    if not user:
        user = User(email="e2e@test.org", username="e2e_user", organisation_id=org.id, role="admin")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="E2E Supplier", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="E2E Supplier", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="E2E-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="E2E-001", name="E2E Item", organisation_id=org.id, quantity=0, unit_price=100.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item


def test_e2e_procurement_receiving(ctx):
    org, user, supplier, item = create_entities()

    # Create PR and assert procurement audit
    pr = ProcurementService.create_purchase_request(org.id, user.id, "E2E purchase request", [{"item_id": item.id, "quantity": 5}])
    audit_pr = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='purchase_request', action='PR_CREATED').order_by(AuditLog.id.desc()).first()
    assert audit_pr is not None and audit_pr.module == 'procurement'

    # Approve PR
    ProcurementService.approve_purchase_request(pr.id, user.id)
    audit_pr_appr = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='purchase_request', action='PR_APPROVED').order_by(AuditLog.id.desc()).first()
    assert audit_pr_appr is not None and audit_pr_appr.module == 'procurement'

    # Create PO and approve (total = 5 * 100 = 500 < 1000 so no canvass required)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 5, "unit_cost": 100.0}])
    audit_po = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='purchase_order', action='PO_CREATED').order_by(AuditLog.id.desc()).first()
    assert audit_po is not None and audit_po.module == 'procurement'

    ProcurementService.approve_purchase_order(po.id)
    audit_po_appr = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='purchase_order', action='PO_APPROVED').order_by(AuditLog.id.desc()).first()
    assert audit_po_appr is not None and audit_po_appr.module == 'procurement'

    # Create GRN
    grn = ReceivingService.create_grn(org.id, po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 5, "unit_cost": 100.0}])
    audit_grn = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='goods_receipt_note', action='GRN_CREATED').order_by(AuditLog.id.desc()).first()
    assert audit_grn is not None and audit_grn.module == 'receiving'

    # Create inspection (passed)
    iar = ReceivingService.create_inspection_report(org.id, grn.id, inspector_id=user.id, status='passed', comments='OK')
    audit_iar = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='inspection_report', action='IAR_CREATED').order_by(AuditLog.id.desc()).first()
    assert audit_iar is not None and audit_iar.module == 'receiving'

    # Approve GRN -> should move quantities into inventory atomically
    before = db.session.get(InventoryItem, item.id)
    qty_before = before.quantity
    ReceivingService.approve_grn(grn.id)
    db.session.refresh(item)
    assert item.quantity == qty_before + 5

    # Verify StockCard and SuppliesLedgerCard reflect same quantity/value
    sc = db.session.query(StockCard).filter_by(organization_id=org.id, item_id=item.id, location_id=None).first()
    ledger = db.session.query(SuppliesLedgerCard).filter_by(organization_id=org.id, item_id=item.id, location_id=None).first()
    assert sc is not None and ledger is not None
    assert sc.quantity_on_hand == item.quantity
    assert int(ledger.quantity_on_hand) == item.quantity
    assert float(ledger.total_value) == float(item.quantity * float(item.unit_price or 0))

    # Verify stock audit was created and tagged with receiving, and references the GRN
    audit_stock = db.session.query(AuditLog).filter_by(organisation_id=org.id, entity_type='inventory_item', action='STOCK_INCREASED').order_by(AuditLog.id.desc()).first()
    assert audit_stock is not None and audit_stock.module == 'receiving'
    assert isinstance(audit_stock.details, dict)
    assert audit_stock.details.get('reference') == grn.grn_number

    # Verify analytics/report reflects inventory totals
    report = ReportAnalyticsService.get_inventory_report(org.id)
    assert report['total_units'] == int(item.quantity)
    assert float(report['total_valuation']) == float(item.quantity * float(item.unit_price or 0))
