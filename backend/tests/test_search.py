import unittest
from datetime import date

from app import create_app, db
from app.models.asset import Asset
from app.models.organization import Department, Organization
from app.models.user import User


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        org = Organization(id=1, name="Acme", code="ACME")
        db.session.add(org)
        dept = Department(id=1, organisation_id=1, name="IT", code="IT")
        db.session.add(dept)
        user = User(
            id=1,
            organisation_id=1,
            username="admin",
            email="a@test.com",
            role="admin",
        )
        user.set_password("Password123!")
        db.session.add(user)
        asset = Asset(
            organisation_id=1,
            asset_code="FIND-ME",
            name="Searchable Laptop",
            type="IT",
            department_id=1,
            status="approved",
            purchase_date=date.today(),
            purchase_value=500,
            useful_life=3,
            current_value=500,
        )
        db.session.add(asset)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _token(self):
        from flask_jwt_extended import create_access_token

        return create_access_token(identity="1")

    def test_global_search_finds_asset(self):
        token = self._token()
        res = self.client.get(
            "/api/search/?q=Laptop",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(any(a["code"] == "FIND-ME" for a in body["assets"]))


if __name__ == "__main__":
    unittest.main()
