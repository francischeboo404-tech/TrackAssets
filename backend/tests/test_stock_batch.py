import unittest
from app import create_app, db
from app.models import InventoryItem, StockMovement
from app.services.inventory_service import InventoryService
from app.models.organization import Organization
from app.errors import ConflictError

class TestStockBatch(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.org_id = 1
        org = Organization(id=self.org_id, name="Test Org", code="TESTORG")
        db.session.add(org)
        db.session.commit()

        self.item1 = InventoryItem(
            organisation_id=self.org_id,
            name="Item One",
            sku="ITM-001",
            quantity=10,
            unit_price=1.0,
        )
        self.item2 = InventoryItem(
            organisation_id=self.org_id,
            name="Item Two",
            sku="ITM-002",
            quantity=20,
            unit_price=2.0,
        )
        db.session.add(self.item1)
        db.session.add(self.item2)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_batch_success(self):
        movements = [
            {"item_id": self.item1.id, "type": "IN", "quantity": 5, "warehouse_id": None, "reference": "BATCH-1"},
            {"item_id": self.item2.id, "type": "OUT", "quantity": 8, "warehouse_id": None, "reference": "BATCH-2"},
        ]

        InventoryService(session=db.session).update_stock_batch(self.org_id, movements)

        i1 = db.session.get(InventoryItem, self.item1.id)
        i2 = db.session.get(InventoryItem, self.item2.id)

        self.assertEqual(i1.quantity, 15)
        self.assertEqual(i2.quantity, 12)

        count = db.session.query(StockMovement).filter(StockMovement.organization_id == self.org_id).count()
        self.assertEqual(count, 2)

    def test_batch_rollback_on_failure(self):
        movements = [
            {"item_id": self.item1.id, "type": "IN", "quantity": 5, "warehouse_id": None, "reference": "BATCH-3"},
            {"item_id": self.item2.id, "type": "OUT", "quantity": 9999, "warehouse_id": None, "reference": "BATCH-4"},
        ]

        with self.assertRaises(ConflictError):
            InventoryService(session=db.session).update_stock_batch(self.org_id, movements)

        # Ensure no partial changes were committed
        i1 = db.session.get(InventoryItem, self.item1.id)
        self.assertEqual(i1.quantity, 10)

        count = db.session.query(StockMovement).filter(StockMovement.organization_id == self.org_id).count()
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
