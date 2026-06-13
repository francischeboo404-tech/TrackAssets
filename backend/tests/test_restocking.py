import unittest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import InventoryItem, StockMovement, RestockAlert
from app.services.inventory_service import InventoryService
from app.services.forecasting_service import ForecastingService


class TestRestocking(unittest.TestCase):
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

        self.service = InventoryService()

        # Setup item
        self.item = InventoryItem(
            organisation_id=self.org_id,
            name="Screws",
            sku="SCRW-001",
            quantity=100,
            reorder_level=50,
            unit_price=0.1,
        )
        db.session.add(self.item)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_low_stock_trigger(self):
        """Test that removing stock below reorder level triggers an alert."""
        # Reduce stock to 40 (reorder is 50)
        self.service.update_stock(self.item.id, self.org_id, "OUT", 60)

        self.assertEqual(self.item.quantity, 40)

        # Check alert
        alert = RestockAlert.query.filter_by(item_id=self.item.id).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, "LOW")
        print(f"\nAlert Created: {alert.message}")

    def test_velocity_and_forecasting(self):
        """Test velocity calculation and depletion prediction."""
        # Add 300 units out over 30 days (10/day)
        now = datetime.utcnow()
        for i in range(30):
            movement = StockMovement(
                item_id=self.item.id,
                type="OUT",
                quantity=10,
                date=now - timedelta(days=i),
            )
            db.session.add(movement)
        db.session.commit()

        velocity = ForecastingService.calculate_daily_velocity(self.item.id)
        self.assertEqual(velocity, 10.0)

        days_left = ForecastingService.predict_days_remaining(self.item.id)
        # 100 on hand / 10 per day = 10 days
        self.assertEqual(days_left, 10.0)
        print(f"Daily Velocity: {velocity}, Days Remaining: {days_left}")


if __name__ == "__main__":
    unittest.main()
