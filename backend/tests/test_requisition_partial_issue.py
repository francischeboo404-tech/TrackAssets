from datetime import datetime

import pytest

from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.inventory import InventoryItem
from app.services.requisition_service import RequisitionService


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


def create_requisition_entities():
    org = db.session.query(Organization).filter_by(code="TEST-RIS-PARTIAL").first()
    if not org:
        org = Organization(name="RIS Org Partial", code="TEST-RIS-PARTIAL")
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email="ris-partial@test.org").first()
    if not user:
        user = User(email="ris-partial@test.org", username="rispart", organisation_id=org.id, role="employee")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku="RIS-PI-001", organisation_id=org.id).first()
    if not item:
        # Low on stock so partial issuance will occur
        item = InventoryItem(sku="RIS-PI-001", name="RIS Partial Item", organisation_id=org.id, quantity=2, unit_price=20.0)
        db.session.add(item)
        db.session.commit()

    return org, user, item


def test_partial_requisition_issue(ctx):
    org, user, item = create_requisition_entities()

    # Request more than available (request 5, available 2)
    ris = RequisitionService.create_requisition(org.id, requester_id=user.id, items_data=[{"item_id": item.id, "quantity": 5}])
    RequisitionService.approve_requisition(ris.id, department_head_id=user.id)

    ris = RequisitionService.issue_requisition(ris.id)

    # Reload related records
    from app.models.kenya_gov_models import RequisitionItem

    ri = db.session.query(RequisitionItem).filter_by(ris_id=ris.id).first()
    refreshed_item = db.session.get(InventoryItem, item.id)

    # We should have issued only the available quantity (2)
    assert ri.quantity_issued == 2
    assert ris.status == 'partially_issued'
    assert refreshed_item.quantity == 0
