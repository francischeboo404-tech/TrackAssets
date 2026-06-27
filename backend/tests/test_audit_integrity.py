import unittest
from app import create_app, db
from app.models.organization import Organization
from app.models.inventory import InventoryItem, AuditLog
from app.models.user import User
from app.services.stock_service import StockService
from datetime import datetime


class TestAuditIntegrity(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.org_id = 1
        org = Organization(id=self.org_id, name="AuditOrg", code="AUDORG")
        db.session.add(org)
        db.session.commit()

        # Create user
        self.user = User(organisation_id=self.org_id, username="audituser", email="audit@example.com", role="employee")
        self.user.set_password("Password1!")
        db.session.add(self.user)
        db.session.commit()

        # Inventory item
        self.item = InventoryItem(organisation_id=self.org_id, name="Audit Item", sku="AUD-INT-001", quantity=5, unit_price=1.0)
        db.session.add(self.item)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_stock_in_audit_contains_required_fields(self):
        # Perform a stock increase with explicit user_id and reference
        StockService(session=db.session).increase_stock(
            item_id=self.item.id,
            org_id=self.org_id,
            quantity=3,
            warehouse_id=None,
            reference="TEST-REF-001",
            notes="Unit test increase",
            user_id=self.user.id,
            commit=True,
        )

        audit = db.session.query(AuditLog).filter(AuditLog.organisation_id == self.org_id).order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(audit, "No audit log created for stock increase")
        # User and timestamp
        self.assertEqual(audit.user_id, self.user.id)
        self.assertIsNotNone(audit.created_at)
        # Action
        self.assertEqual(audit.action, "STOCK_INCREASED")
        # Reference
        self.assertEqual(audit.reference, "TEST-REF-001")
        # Module recorded
        self.assertIsNotNone(audit.module)
        # Details include previous and new values (standardized keys)
        self.assertIsNotNone(audit.details)
        self.assertIn("previous_value", audit.details)
        self.assertIn("new_value", audit.details)
        # Values sanity check
        self.assertEqual(audit.details.get("previous_value"), 5)
        self.assertEqual(audit.details.get("new_value"), 8)


if __name__ == '__main__':
    unittest.main()
