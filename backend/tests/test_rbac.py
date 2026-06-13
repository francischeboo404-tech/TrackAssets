import unittest

from app import create_app, db
from app.errors import AuthorizationError
from app.models.organization import Department, Organization
from app.models.user import User
from app.rbac import (
    assert_can_transition_status,
    assert_not_read_only,
    can_transition_status,
    filter_analytics_payload,
)


class TestRBAC(unittest.TestCase):
    def test_viewer_cannot_transition(self):
        self.assertFalse(can_transition_status("viewer", "requested", "approved"))
        with self.assertRaises(AuthorizationError):
            assert_not_read_only("viewer")

    def test_dept_head_can_approve(self):
        self.assertTrue(can_transition_status("dept_head", "requested", "approved"))
        self.assertFalse(can_transition_status("dept_head", "approved", "in_use"))

    def test_staff_can_assign_in_use(self):
        self.assertTrue(can_transition_status("staff", "approved", "in_use"))
        self.assertFalse(can_transition_status("staff", "in_use", "disposed"))

    def test_admin_dispose(self):
        self.assertTrue(can_transition_status("admin", "in_use", "disposed"))

    def test_analytics_viewer_scope(self):
        payload = {
            "inventory": {"total_items": 5},
            "assets": {"total_assets": 2, "status_breakdown": {}},
            "insights": ["secret"],
            "currency": "KES",
        }
        scoped = filter_analytics_payload("viewer", payload)
        self.assertNotIn("insights", scoped)
        self.assertEqual(scoped.get("scope"), "read_only")


class TestAssetStatusRBACIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        org = Organization(id=1, name="Test Org", code="TST")
        db.session.add(org)
        dept = Department(id=1, organisation_id=1, name="IT", code="IT")
        db.session.add(dept)

        self.viewer = User(
            organisation_id=1,
            username="viewer1",
            email="viewer@test.com",
            role="viewer",
        )
        self.viewer.set_password("Password1!")
        self.dept_head = User(
            organisation_id=1,
            username="head1",
            email="head@test.com",
            role="dept_head",
        )
        self.dept_head.set_password("Password1!")
        db.session.add_all([self.viewer, self.dept_head])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, user):
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token

            return create_access_token(identity=str(user.id))

    def test_viewer_blocked_on_status_change(self):
        from app.models.asset import Asset
        from datetime import date

        asset = Asset(
            organisation_id=1,
            asset_code="TST-001",
            name="Laptop",
            type="Hardware",
            department_id=1,
            status="requested",
            purchase_date=date.today(),
            purchase_value=1000,
            useful_life=5,
            current_value=1000,
        )
        db.session.add(asset)
        db.session.commit()

        token = self._login(self.viewer)
        res = self.client.put(
            f"/api/assets/{asset.id}/status",
            json={"status": "approved"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
