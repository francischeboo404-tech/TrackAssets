import unittest
from datetime import date, datetime, timedelta

from app import create_app, db
from app.models.asset import Asset
from app.models.inventory import AuditLog, InventoryItem, StockMovement
from app.models.organization import Department, Organization
from app.models.scan_event import ScanEvent
from app.models.user import User
from app.services.report_analytics_service import ReportAnalyticsService


class TestReportAnalytics(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.org = Organization(id=1, name="Acme", code="ACME")
        db.session.add(self.org)
        dept = Department(id=1, organisation_id=1, name="IT", code="IT")
        db.session.add(dept)
        self.admin = User(
            id=1,
            organisation_id=1,
            username="admin",
            email="a@test.com",
            role="admin",
        )
        self.admin.set_password("Password123!")
        db.session.add(self.admin)

        asset = Asset(
            organisation_id=1,
            asset_code="A-1",
            name="Laptop",
            type="IT",
            department_id=1,
            status="in_use",
            purchase_date=date.today(),
            purchase_value=1000,
            useful_life=5,
            current_value=1000,
        )
        db.session.add(asset)

        item = InventoryItem(
            organisation_id=1,
            name="Paper",
            sku="P-1",
            quantity=5,
            reorder_level=10,
            unit_price=10,
        )
        db.session.add(item)
        db.session.flush()

        db.session.add(
            StockMovement(
                item_id=item.id,
                type="OUT",
                quantity=2,
                date=datetime.utcnow(),
            )
        )
        db.session.add(
            ScanEvent(
                organisation_id=1,
                item_type="asset",
                item_id=asset.id,
                user_id=1,
                action_type="VERIFY",
                user_role="admin",
            )
        )
        db.session.add(
            AuditLog(
                organisation_id=1,
                user_id=1,
                action="ASSET_STATUS_CHANGED",
                entity_type="asset",
                entity_id=asset.id,
                details={"new_values": {"status": "in_use"}},
            )
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _token(self):
        from flask_jwt_extended import create_access_token

        return create_access_token(identity="1")

    def test_assets_report_aggregates(self):
        data = ReportAnalyticsService.get_assets_report(1, days=30)
        self.assertEqual(data["total_count"], 1)
        self.assertTrue(any(s["code"] == "in_use" for s in data["by_status"]))
        self.assertEqual(len(data["by_department"]), 1)
        self.assertIn("utilization_rate", data)

    def test_inventory_report_aggregates(self):
        data = ReportAnalyticsService.get_inventory_report(1, days=30)
        self.assertEqual(data["total_skus"], 1)
        self.assertEqual(data["low_stock_count"], 1)
        self.assertTrue(len(data["movement_over_time"]) >= 1)
        self.assertTrue(len(data["most_consumed"]) >= 0)

    def test_tracking_report_aggregates(self):
        data = ReportAnalyticsService.get_tracking_report(1, days=30)
        self.assertGreaterEqual(data["total_scans"], 1)
        self.assertTrue(len(data["activity_frequency"]) >= 1)

    def test_dashboard_report_shape(self):
        data = ReportAnalyticsService.get_dashboard_report(1, days=30)
        self.assertIn("kpis", data)
        self.assertIn("assets", data)
        self.assertIn("inventory", data)
        self.assertEqual(data["kpis"]["total_assets"], 1)

    def test_api_returns_success_envelope(self):
        token = self._token()
        res = self.client.get(
            "/api/reports/assets?days=30",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["success"])
        self.assertIn("data", body)
        self.assertIn("message", body)
        self.assertEqual(body["data"]["total_count"], 1)

    def test_viewer_forbidden_inventory(self):
        viewer = User(
            id=2,
            organisation_id=1,
            username="view",
            email="v@test.com",
            role="viewer",
        )
        viewer.set_password("Password123!")
        db.session.add(viewer)
        db.session.commit()
        from flask_jwt_extended import create_access_token

        token = create_access_token(identity="2")
        res = self.client.get(
            "/api/reports/inventory",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
