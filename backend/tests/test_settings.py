import io
import unittest

from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.services.settings_service import SettingsService


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.org = Organization(
            id=1, name="Acme Corp", code="ACME", preferences={"currency": "KES"}
        )
        db.session.add(self.org)
        self.admin = User(
            id=1,
            organisation_id=1,
            username="admin1",
            email="admin@test.com",
            role="admin",
        )
        self.admin.set_password("Password123!")
        db.session.add(self.admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _token(self, user):
        with self.app.app_context():
            from flask_jwt_extended import create_access_token

            return create_access_token(identity=str(user.id))

    def test_export_csv_uses_valid_fields(self):
        from app.models.asset import Asset
        from app.models.organization import Department
        from datetime import date

        dept = Department(
            id=1, organisation_id=1, name="IT", code="IT"
        )
        db.session.add(dept)
        asset = Asset(
            organisation_id=1,
            asset_code="ACME-001",
            name="Laptop",
            type="IT",
            department_id=1,
            status="approved",
            purchase_date=date.today(),
            purchase_value=1000,
            useful_life=5,
            current_value=1000,
        )
        db.session.add(asset)
        db.session.commit()

        csv_out = SettingsService.export_csv(1)
        self.assertIn("ACME-001", csv_out)
        self.assertIn("Approved", csv_out)
        self.assertNotIn("barcode", csv_out)
        self.assertTrue(csv_out.startswith("\ufeff"))
        self.assertIn("TrackIT", csv_out)
        self.assertIn("Asset Code", csv_out)

    def test_update_preferences_whitelist(self):
        org = SettingsService.get_organization(1)
        SettingsService.update_organization(
            org,
            {
                "preferences": {
                    "currency": "USD",
                    "malicious_key": "hack",
                    "critical_alerts": False,
                }
            },
            1,
            1,
        )
        db.session.refresh(org)
        self.assertEqual(org.preferences.get("currency"), "USD")
        self.assertNotIn("malicious_key", org.preferences)

    def test_get_settings_requires_admin(self):
        staff = User(
            organisation_id=1,
            username="staff1",
            email="staff@test.com",
            role="staff",
        )
        staff.set_password("Password123!")
        db.session.add(staff)
        db.session.commit()

        token = self._token(staff)
        res = self.client.get(
            "/api/settings/organization",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
