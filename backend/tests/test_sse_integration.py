import pytest
from app import create_app, db
from app.models.organization import Organization
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


def test_sse_stream_with_query_token(app, client):
    # Create org
    org = Organization(name="SSE Org", code="SSE", description="SSE test org")
    db.session.add(org)
    db.session.commit()

    # Create public-schema user for authentication
    with public_schema():
        u = user_model.User(
            organisation_id=org.id,
            username="sse_admin",
            email="sse_admin@example.com",
            first_name="SSE",
            last_name="Admin",
            role="admin",
        )
        u.set_password("Admin123!")
        db.session.add(u)
        db.session.commit()

    # Login to obtain access_token
    login_resp = client.post("/api/auth/login", json={"email": "sse_admin@example.com", "password": "Admin123!"})
    assert login_resp.status_code == 200
    token = login_resp.get_json().get("access_token")
    assert token

    # Request SSE endpoint using access_token as query param.
    # Use unbuffered client to iterate the streaming response without blocking.
    resp = client.get(f"/api/analytics/stream?access_token={token}", headers={"Accept": "text/event-stream"}, buffered=False)
    assert resp.status_code == 200

    # The generator should yield an immediate heartbeat line. Read first chunk.
    iterator = resp.response
    first_chunk = next(iterator)
    # Ensure we received an SSE formatted chunk (heartbeat or data)
    assert b"heartbeat" in first_chunk or b"data:" in first_chunk

    # Close the iterator to avoid leaving the generator running
    try:
        iterator.close()
    except Exception:
        pass
