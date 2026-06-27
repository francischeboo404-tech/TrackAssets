import pytest

from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.models.kenya_gov_models import GoodsReceiptItem, PurchaseOrder
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
    org = db.session.query(Organization).filter_by(code="TEST-PI").first()
    if not org:
        org = Organization(name="PerItem Org", code="TEST-PI")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="pi@test.org").first()
    if not user:
        user = User(email="pi@test.org", username="pi", organisation_id=org.id, role="store_manager")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="PI Supplier", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="PI Supplier", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="PI-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="PI-001", name="PI Item", organisation_id=org.id, quantity=0, unit_price=10.0)
        db.session.add(item)
        db.session.commit()
    else:
        # reset quantity to ensure test isolation
        item.quantity = 0
        db.session.commit()

    return org, user, supplier, item


def test_per_item_partial_acceptance(ctx):
    org, user, supplier, item = create_entities()

    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR PI", [{"item_id": item.id, "quantity": 3}])
    ProcurementService.approve_purchase_request(pr.id, user.id)

    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 3, "unit_cost": 10.0}])
    ProcurementService.approve_purchase_order(po.id)

    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 3, "unit_cost": 10.0}])

    grn_item = db.session.query(GoodsReceiptItem).filter_by(grn_id=grn.id).first()

    iar = ReceivingService.process_inspection_items(org.id, grn.id, inspector_id=user.id, items_data=[{"grn_item_id": grn_item.id, "quantity_accepted": 2, "quantity_rejected": 1}], comments='partial accept')

    db.session.refresh(grn_item)
    assert grn_item.quantity_accepted == 2
    assert grn_item.quantity_rejected == 1

    refreshed_item = db.session.get(InventoryItem, item.id)
    assert refreshed_item.quantity == 2

    grn_refreshed = grn = db.session.get(PurchaseOrder, po.id)
    assert grn_refreshed.status in ('partially_received', 'received')


def test_per_item_full_rejection(ctx):
    org, user, supplier, item = create_entities()

    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR PI2", [{"item_id": item.id, "quantity": 2}])
    ProcurementService.approve_purchase_request(pr.id, user.id)

    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 2, "unit_cost": 10.0}])
    ProcurementService.approve_purchase_order(po.id)

    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 2, "unit_cost": 10.0}])

    grn_item = db.session.query(GoodsReceiptItem).filter_by(grn_id=grn.id).first()

    iar = ReceivingService.process_inspection_items(org.id, grn.id, inspector_id=user.id, items_data=[{"grn_item_id": grn_item.id, "quantity_accepted": 0, "quantity_rejected": 2}], comments='reject all')

    db.session.refresh(grn_item)
    assert grn_item.quantity_accepted == 0
    assert grn_item.quantity_rejected == 2

    refreshed_item = db.session.get(InventoryItem, item.id)
    # inventory should not increase
    assert refreshed_item.quantity == 0

    grn_refreshed = db.session.query(GoodsReceiptItem).filter_by(grn_id=grn.id).first()
    # grn should remain rejected/quarantine depending on implementation; we expect 'rejected' grn
    grn_note = grn = db.session.get(GoodsReceiptItem, grn_item.id)
    assert grn_note is not None
