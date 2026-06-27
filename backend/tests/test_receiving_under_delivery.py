import pytest

from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.models.kenya_gov_models import PurchaseOrder
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
    org = db.session.query(Organization).filter_by(code="TEST-UD").first()
    if not org:
        org = Organization(name="UnderDelivery Org", code="TEST-UD")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="ud@test.org").first()
    if not user:
        user = User(email="ud@test.org", username="ud", organisation_id=org.id, role="store_manager")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="UD Supplier", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="UD Supplier", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="UD-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="UD-001", name="UD Item", organisation_id=org.id, quantity=0, unit_price=5.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item


def test_under_delivery_allowed(ctx):
    org, user, supplier, item = create_entities()

    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR UD", [{"item_id": item.id, "quantity": 10}])
    ProcurementService.approve_purchase_request(pr.id, user.id)

    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 10, "unit_cost": 5.0}])
    ProcurementService.approve_purchase_order(po.id)

    # Receive less than ordered (7 of 10)
    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 7, "unit_cost": 5.0}])
    ReceivingService.create_inspection_report(org.id, grn.id, inspector_id=user.id, status='passed', comments='ok')
    ReceivingService.approve_grn(grn.id)

    po_refreshed = db.session.get(PurchaseOrder, po.id)
    assert po_refreshed.status == 'partially_received'

    refreshed_item = db.session.get(InventoryItem, item.id)
    assert refreshed_item.quantity == 7
