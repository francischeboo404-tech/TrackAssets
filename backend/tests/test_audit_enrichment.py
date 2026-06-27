import unittest
from app import create_app, db
from flask import request
from app.models.organization import Organization
from app.models.inventory import InventoryItem, StockMovement, AuditLog
from app.models.user import User
from app.services.inventory_service import InventoryService

class TestAuditEnrichment(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.org_id = 1
        org = Organization(id=self.org_id, name="Test Org", code="TESTORG")
        db.session.add(org)
        db.session.commit()

        # Create user
        user = User(organisation_id=self.org_id, username="audituser", email="audit@example.com", role="employee")
        user.set_password("Password1!")
        db.session.add(user)
        db.session.commit()

        # Inventory item
        self.item = InventoryItem(organisation_id=self.org_id, name="Audit Item", sku="AUD-001", quantity=5, unit_price=1.0)
        db.session.add(self.item)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_audit_includes_user_agent(self):
        movements = [{"item_id": self.item.id, "type": "IN", "quantity": 3, "warehouse_id": None, "reference": "AUD-1"}]

        # Use test request context with a User-Agent header
        headers = {"User-Agent": "UnitTest-Agent/1.0"}
        with self.app.test_request_context('/', headers=headers):
            InventoryService(session=db.session).update_stock_batch(self.org_id, movements)

        # Verify AuditLog created and contains user_agent in details
        audit = db.session.query(AuditLog).filter(AuditLog.organisation_id == self.org_id).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(audit)
        self.assertIsNotNone(audit.details)
        self.assertIn('user_agent', audit.details)
        self.assertEqual(audit.details['user_agent'], 'UnitTest-Agent/1.0')

if __name__ == '__main__':
    unittest.main()
