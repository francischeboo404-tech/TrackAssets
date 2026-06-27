import pytest

from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.models.kenya_gov_models import GoodsReceiptNote
from app.services.procurement_service import ProcurementService
from app.services.receiving_service import ReceivingService
from app.errors import ValidationError


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
    org = db.session.query(Organization).filter_by(code="TEST-IR").first()
    if not org:
        org = Organization(name="InspectionReject Org", code="TEST-IR")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="ir@test.org").first()
    if not user:
        user = User(email="ir@test.org", username="ir", organisation_id=org.id, role="store_manager")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = db.session.query(Supplier).filter_by(name="IR Supplier", organisation_id=org.id).first()
    if not supplier:
        supplier = Supplier(name="IR Supplier", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="IR-001", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku="IR-001", name="IR Item", organisation_id=org.id, quantity=0, unit_price=10.0)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item


def test_inspection_rejection_blocks_approval(ctx):
    org, user, supplier, item = create_entities()

    pr = ProcurementService.create_purchase_request(org.id, user.id, "PR IR", [{"item_id": item.id, "quantity": 3}])
    ProcurementService.approve_purchase_request(pr.id, user.id)

    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{"item_id": item.id, "quantity": 3, "unit_cost": 10.0}])
    ProcurementService.approve_purchase_order(po.id)

    grn = ReceivingService.create_grn(org.id, po_id=po.id, received_by_id=user.id, items_data=[{"item_id": item.id, "quantity_received": 3, "unit_cost": 10.0}])

    # Create failing inspection
    ReceivingService.create_inspection_report(org.id, grn.id, inspector_id=user.id, status='failed', comments='damaged')

    with pytest.raises(ValidationError):
        ReceivingService.approve_grn(grn.id)

    grn_refreshed = db.session.get(GoodsReceiptNote, grn.id)
    assert grn_refreshed.status == 'quarantine'
