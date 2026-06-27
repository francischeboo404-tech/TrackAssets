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


def create_entities(code_suffix="CANCEL", role="employee"):
    org_code = f"TEST-RIS-{code_suffix}"
    org = db.session.query(Organization).filter_by(code=org_code).first()
    if not org:
        org = Organization(name=f"RIS Cancel Org {code_suffix}", code=org_code)
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email=f"ris-cancel-{code_suffix}@test.org").first()
    if not user:
        user = User(email=f"ris-cancel-{code_suffix}@test.org", username=f"riscancel{code_suffix}", organisation_id=org.id, role=role)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku=f"RIS-C-{code_suffix}", organisation_id=org.id).first()
    if not item:
        item = InventoryItem(sku=f"RIS-C-{code_suffix}", name="RIS Cancel Item", organisation_id=org.id, quantity=10, unit_price=5.0)
        db.session.add(item)
        db.session.commit()

    return org, user, item


def test_cancel_pending_requisition(ctx):
    org, user, item = create_entities("PENDING")

    ris = RequisitionService.create_requisition(org.id, requester_id=user.id, items_data=[{"item_id": item.id, "quantity": 2}])

    ris = RequisitionService.cancel_requisition(ris.id, cancelled_by_id=user.id)

    assert ris.status == 'cancelled'


def test_cannot_cancel_issued_requisition(ctx):
    org, user, item = create_entities("ISSUED")

    ris = RequisitionService.create_requisition(org.id, requester_id=user.id, items_data=[{"item_id": item.id, "quantity": 3}])
    RequisitionService.approve_requisition(ris.id, department_head_id=user.id)

    # Issue successfully (item quantity 10 allows issuance)
    ris = RequisitionService.issue_requisition(ris.id)

    with pytest.raises(ValueError):
        RequisitionService.cancel_requisition(ris.id, cancelled_by_id=user.id)


def test_cancel_ris_endpoint(ctx):
    """Integration test for the cancel endpoint using the auth token."""
    client = TEST_APP.test_client()
    org, user, item = create_entities("ENDPT")

    ris = RequisitionService.create_requisition(org.id, requester_id=user.id, items_data=[{"item_id": item.id, "quantity": 1}])

    # Login to obtain access token
    login = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "Password123!"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    # Call cancel endpoint
    resp = client.post(
        f"/api/requisition/issue-slips/{ris.id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ris_id"] == ris.id
    assert data["message"] == 'RIS cancelled'


def test_return_ris_endpoint(ctx):
    """Integration test for returning issued items via the API endpoint."""
    client = TEST_APP.test_client()
    org, user, item = create_entities("RETURN", role="store_manager")

    ris = RequisitionService.create_requisition(org.id, requester_id=user.id, items_data=[{"item_id": item.id, "quantity": 2}])
    RequisitionService.approve_requisition(ris.id, department_head_id=user.id)

    # Issue successfully
    ris = RequisitionService.issue_requisition(ris.id)
    assert ris.status in ("issued", "partially_issued")

    login = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "Password123!"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    # Return the issued quantity
    resp = client.post(
        f"/api/requisition/issue-slips/{ris.id}/return",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": [{"item_id": item.id, "quantity": 2}]},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ris_id"] == ris.id
    assert data["message"] == 'RIS returned'

    # Verify requisition item's issued quantity reset and inventory restored
    from app.models.kenya_gov_models import RequisitionItem
    from app.models.inventory import InventoryItem

    req_item = db.session.query(RequisitionItem).filter_by(ris_id=ris.id, item_id=item.id).first()
    assert int(req_item.quantity_issued or 0) == 0

    inv = db.session.get(InventoryItem, item.id)
    # original create_entities set quantity=10
    assert int(inv.quantity) == 10
