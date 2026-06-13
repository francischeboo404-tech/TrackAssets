import unittest
from app import create_app, db
from app.models.inventory import InventoryItem
from app.services.inventory_service import InventoryService


class TestStabilization(unittest.TestCase):
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
        self.item = InventoryItem(
            organisation_id=self.org_id,
            name="<b>Dangerous Item</b>",
            sku="TOOL-001",
            quantity=10,
            unit_price=100.0,
        )
        db.session.add(self.item)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_sanitization(self):
        # This test should normally be at the blueprint level,
        # but we can verify our fix by passing data through a "stabilized" flow
        # In a real environment, we'd use a TestClient
        from app.validation import sanitize_string

        dirty_name = "<script>alert('xss')</script>Safe Name"
        clean_name = sanitize_string(dirty_name)
        self.assertNotIn("<script>", clean_name)
        self.assertEqual(clean_name, "scriptalert('xss')/scriptSafe Name")

    def test_cascade_deletion(self):
        from app.models.restock_alert import RestockAlert

        alert = RestockAlert(
            item_id=self.item.id, organisation_id=self.org_id, severity="low"
        )
        db.session.add(alert)
        db.session.commit()

        # Now delete the item (must have 0 stock for service.delete_item, but we test DB level)
        db.session.delete(self.item)
        db.session.commit()

        # Alert should be gone
        remaining_alerts = RestockAlert.query.filter_by(
            item_id=self.item.id
        ).all()
        self.assertEqual(len(remaining_alerts), 0)


if __name__ == "__main__":
    unittest.main()
