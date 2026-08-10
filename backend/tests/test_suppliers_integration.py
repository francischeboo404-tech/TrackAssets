import pytest
from app import create_app, db
from app.models.organization import Organization
from app.models import supplier as supplier_model
from app.models import user as user_model
from app.tenant_utils import public_schema


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_supplier_crud_flow(app, client):
    # Create org
    org = Organization(name="Test Suppliers Organization", code="TEST-ORG-001")
    db.session.add(org)
    db.session.commit()

    # Create a public-schema admin user for auth
    with public_schema():
        u = user_model.User(
            organisation_id=org.id,
            username="test_supplier_admin",
            email="admin@supplierstest.com",
            first_name="Test",
            last_name="Admin",
            role="admin",
        )
        u.set_password("TestPassword123!")
        db.session.add(u)
        db.session.commit()

    # Login
    login_resp = client.post("/api/auth/login", json={"email": "admin@supplierstest.com", "password": "TestPassword123!"})
    assert login_resp.status_code == 200
    token = login_resp.get_json().get("access_token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}

    # Create supplier
    payload = {
        "name": "Acme Manufacturing Ltd",
        "code": "ACME-001",
        "email": "contact@acmemfg.com",
        "phone": "+254700000000"
    }
    res = client.post("/api/suppliers", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.get_json()
    sup_id = data["supplier"]["id"]

    # List suppliers and assert present
    res = client.get("/api/suppliers", headers=headers)
    assert res.status_code == 200
    suppliers = res.get_json().get("suppliers") or []
    assert any(s.get("id") == sup_id for s in suppliers)

    # Update supplier
    update_payload = {"phone": "+254711111111"}
    res = client.put(f"/api/suppliers/{sup_id}", json=update_payload, headers=headers)
    assert res.status_code == 200

    # Verify DB updated
    sup = supplier_model.Supplier.query.get(sup_id)
    assert sup.phone == "+254711111111"

    # Delete (deactivate) supplier
    res = client.delete(f"/api/suppliers/{sup_id}", headers=headers)
    assert res.status_code == 200

    sup = supplier_model.Supplier.query.get(sup_id)
    assert sup is not None and sup.is_active is False
