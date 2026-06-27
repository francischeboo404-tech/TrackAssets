import pytest

from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.inventory import InventoryItem
from app.services.disposal_service import DisposalService


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


def create_entities(code_suffix="DISP", role="admin"):
    org_code = f"TEST-DISP-{code_suffix}"
    org = db.session.query(Organization).filter_by(code=org_code).first()
    if not org:
        org = Organization(name=f"DISP Org {code_suffix}", code=org_code)
        db.session.add(org)
        db.session.commit()

    user = db.session.query(User).filter_by(email=f"disp-{code_suffix}@test.org").first()
    if not user:
        user = User(email=f"disp-{code_suffix}@test.org", username=f"disp{code_suffix}", organisation_id=org.id, role=role)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    item = db.session.query(InventoryItem).filter_by(sku=f"DISP-{code_suffix}", organisation_id=org.id).first()
    if not item:
        # make expensive by default so approval rules apply
        item = InventoryItem(sku=f"DISP-{code_suffix}", name="DISP Item", organisation_id=org.id, quantity=5, unit_price=60000)
        db.session.add(item)
        db.session.commit()

    return org, user, item


def test_create_and_execute_disposal(ctx):
    org, user, item = create_entities("INTG", role="admin")

    # Create disposal request
    disp = DisposalService.create_disposal_request(org.id, user.id, items_data=[{"item_id": item.id, "quantity": 1}])
    assert disp.status == 'pending'
    assert float(disp.total_value) == float(item.unit_price)

    # Approve must require finance board for expensive item
    with pytest.raises(ValueError):
        DisposalService.approve_disposal(disp.id, user.id, is_finance_board=False)

    disp = DisposalService.approve_disposal(disp.id, user.id, is_finance_board=True)
    assert disp.status == 'approved'

    # Execute disposal and verify stock decreased
    prev_qty = int(item.quantity)
    disp = DisposalService.execute_disposal(disp.id, executed_by_id=user.id)
    assert disp.status == 'executed'

    db.session.refresh(item)
    assert int(item.quantity) == prev_qty - 1


def test_disposal_endpoints(ctx):
    client = TEST_APP.test_client()
    org, user, item = create_entities("ENDPT", role="admin")

    # Login
    login = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "Password123!"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    # Create disposal via API
    resp = client.post(
        "/api/disposal/disposal-requests",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": [{"item_id": item.id, "quantity": 1}]},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    disp_id = data["disp_id"]

    # Try approving without finance board flag
    resp = client.put(
        f"/api/disposal/disposal-requests/{disp_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_finance_board": False},
    )
    assert resp.status_code == 400

    # Approve with finance board
    resp = client.put(
        f"/api/disposal/disposal-requests/{disp_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_finance_board": True},
    )
    assert resp.status_code == 200

    # Execute disposal
    resp = client.put(
        f"/api/disposal/disposal-requests/{disp_id}/execute",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
