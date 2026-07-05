import unittest
from app import create_app, db
from app.services.analytics_service import AnalyticsService
from app.models import InventoryItem, StockMovement, Warehouse, WarehouseStock
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

        self.warehouse = Warehouse(
            organisation_id=self.org_id,
            name="Main Warehouse",
            code="MAIN",
            is_active=True,
        )
        db.session.add(self.warehouse)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_inventory_valuation(self):
        valuation = AnalyticsService.get_inventory_valuation(self.org_id)
        # 100 * 5.0 = 500
        self.assertEqual(valuation, 500.0)

    def test_inventory_summary_uses_warehouse_stock_for_org_level(self):
        # Create a separate org and stale item quantity with warehouse stock present.
        from app.models.organization import Organization

        other_org = Organization(name="Other Org", code="OTHER01")
        db.session.add(other_org)
        db.session.commit()

        item2 = InventoryItem(
            organisation_id=other_org.id,
            name="Stale Item",
            sku="STALE-001",
            quantity=1000,
            unit_price=10.0,
        )
        db.session.add(item2)
        db.session.commit()

        other_wh = Warehouse(
            organisation_id=other_org.id,
            name="Other Warehouse",
            code="OTHER",
            is_active=True,
        )
        db.session.add(other_wh)
        db.session.commit()

        wh_stock = WarehouseStock(
            item_id=item2.id,
            warehouse_id=other_wh.id,
            quantity_on_hand=20,
            quantity_reserved=0,
        )
        db.session.add(wh_stock)
        db.session.commit()

        summary = AnalyticsService.get_inventory_summary(other_org.id)
        self.assertEqual(summary["total_items"], 20)

    def test_inventory_valuation_uses_warehouse_stock_for_org_level(self):
        # Create a separate org and stale item quantity with warehouse stock present.
        from app.models.organization import Organization

        other_org = Organization(name="Other Org", code="OTHER01")
        db.session.add(other_org)
        db.session.commit()

        item2 = InventoryItem(
            organisation_id=other_org.id,
            name="Stale Item",
            sku="STALE-001",
            quantity=1000,
            unit_price=10.0,
        )
        db.session.add(item2)
        db.session.commit()

        other_wh = Warehouse(
            organisation_id=other_org.id,
            name="Other Warehouse",
            code="OTHER",
            is_active=True,
        )
        db.session.add(other_wh)
        db.session.commit()

        wh_stock = WarehouseStock(
            item_id=item2.id,
            warehouse_id=other_wh.id,
            quantity_on_hand=20,
            quantity_reserved=0,
        )
        db.session.add(wh_stock)
        db.session.commit()

        valuation = AnalyticsService.get_inventory_valuation(other_org.id)
        self.assertEqual(valuation, 200.0)

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
