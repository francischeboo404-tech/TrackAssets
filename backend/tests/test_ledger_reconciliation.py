import unittest
from datetime import datetime
from app import create_app, db
from app.models import StockCard, SuppliesLedgerCard
from app.models.inventory import InventoryItem
from app.models.kenya_gov_models import VarianceReport
from app.models.location_topology import Warehouse
from app.models.stock_levels import WarehouseStock
from app.models.organization import Organization
from app.services.ledger_service import LedgerService
from app.services.inventory_service import InventoryService


class TestLedgerReconciliation(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.org_id = 1
        org = Organization(id=self.org_id, name="Test Org", code="TESTORG")
        db.session.add(org)
        db.session.commit()

        # Create a test user to satisfy foreign key references
        from app.models.user import User

        user = User(organisation_id=self.org_id, username="testuser", email="test@example.com", role="employee")
        user.set_password("Password1!")
        db.session.add(user)
        db.session.commit()

        # Inventory item used for reconciliation. The item quantity is intentionally stale
        # relative to warehouse stock so variance resolution must reconcile from warehouse totals.
        self.item = InventoryItem(
            organisation_id=self.org_id,
            name="Recon Item",
            sku="RECON-001",
            quantity=150,
            unit_price=5.0,
        )
        db.session.add(self.item)
        db.session.commit()

        self.warehouse = Warehouse(
            organisation_id=self.org_id,
            name="MAIN WAREHOUSE",
            code="MAIN",
            is_active=True,
        )
        db.session.add(self.warehouse)
        db.session.commit()

        self.warehouse_stock = WarehouseStock(
            item_id=self.item.id,
            warehouse_id=self.warehouse.id,
            quantity_on_hand=100,
            quantity_reserved=0,
        )
        db.session.add(self.warehouse_stock)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_variance_resolution_applies_stock_and_creates_cards(self):
        # Physical count shows 92 (variance -8)
        vr = VarianceReport(
            organization_id=self.org_id,
            report_number="VR-001",
            item_id=self.item.id,
            location_id=None,
            system_quantity=100,
            physical_quantity=92,
            variance=-8,
            reason="count mismatch",
        )
        db.session.add(vr)
        db.session.commit()

        # Resolve the variance via the LedgerService which should use StockService.apply_batch
        LedgerService().resolve_variance(vr.id, resolved_by_id=1)

        # Reload item and ledger/card entries
        item = db.session.get(InventoryItem, self.item.id)

        sc = db.session.query(StockCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()
        ledger = db.session.query(SuppliesLedgerCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()

        self.assertIsNotNone(sc, "StockCard should be created on variance resolution")
        self.assertIsNotNone(ledger, "SuppliesLedgerCard should be created on variance resolution")

        # Quantity should reflect physical count
        self.assertEqual(item.quantity, 92)
        self.assertEqual(sc.quantity_on_hand, 92)
        self.assertEqual(int(ledger.quantity_on_hand), 92)

        # Verify audit log reference exists for the variance report (if AuditService is invoked)
        from app.models.inventory import AuditLog

        audit = db.session.query(AuditLog).filter_by(reference="VR-001").first()
        self.assertIsNotNone(audit)


if __name__ == "__main__":
    unittest.main()
