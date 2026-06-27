from datetime import datetime

import pytest

from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.services.procurement_service import ProcurementService
from app.services.receiving_service import ReceivingService
from app.models.kenya_gov_models import PurchaseOrder


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
    org = db.session.query(Organization).filter_by(code="TEST-RECV-PARTIAL").first()
    if not org:
        org = Organization(name="Recv Org Partial", code="TEST-RECV-PARTIAL")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="recv-partial@test.org").first()
    if not user:
        user = User(email="recv-partial@test.org", username="recvpart", organisation_id=org.id, role="store_manager")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="Recv Supplier Partial", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="Recv Supplier Partial", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="RECV-P-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="RECV-P-001", name="Recv Partial Item", organisation_id=org.id, quantity=0, unit_price=5.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item


def test_partial_receipt_updates_po_status_and_stock(ctx):
    org, user, supplier, item = create_procurement_entities()

    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR Partial", [{"item_id": item.id, "quantity": 10}])
    ProcurementService.approve_purchase_request(pr.id, user.id)

    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 10, "unit_cost": 5.0}])
    ProcurementService.approve_purchase_order(po.id)

    # Receive 4 units only
    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 4, "unit_cost": 5.0}])

    # Create inspection report (passed) and approve
    iar = ReceivingService.create_inspection_report(org.id, grn.id, inspector_id=user.id, status='passed', comments='ok')
    ReceivingService.approve_grn(grn.id)

    # Reload PO and assert partial status
    po_refreshed = db.session.get(PurchaseOrder, po.id)
    # We expect PO status updated to partially_received or received
    assert po_refreshed.status in ('partially_received', 'received')

    # Verify inventory increased by 4
    refreshed_item = db.session.get(InventoryItem, item.id)
    assert refreshed_item.quantity == 4
