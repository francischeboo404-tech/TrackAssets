import unittest
from app import create_app, db
from app.services.analytics_service import AnalyticsService
from app.models import InventoryItem, StockMovement
from datetime import datetime


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.org_id = 1
        # Create Organization to satisfy foreign key constraint
        from app.models.organization import Organization
        org = Organization(id=self.org_id, name="Test Org", code="TESTORG")
        db.session.add(org)
        db.session.commit()

        # Create mock data
        self.item = InventoryItem(
            organisation_id=self.org_id,
            name="Test Bolt",
            sku="BOLT-001",
            quantity=100,
            unit_price=5.0,
        )
        db.session.add(self.item)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_inventory_valuation(self):
        valuation = AnalyticsService.get_inventory_valuation(self.org_id)
        # 100 * 5.0 = 500
        self.assertEqual(valuation, 500.0)

    def test_movement_trends(self):
        # Create 5 IN movements today
        for _ in range(5):
            m = StockMovement(
                item_id=self.item.id,
                type="IN",
                quantity=1,
                date=datetime.utcnow(),
            )
            db.session.add(m)
        db.session.commit()

        trends = AnalyticsService.get_movement_trends(self.org_id)
        today = str(datetime.utcnow().date())
        self.assertIn(today, trends)
        self.assertEqual(trends[today]["IN"], 5)


if __name__ == "__main__":
    unittest.main()
