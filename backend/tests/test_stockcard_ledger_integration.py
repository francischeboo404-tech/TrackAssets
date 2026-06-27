import unittest
from datetime import datetime
from app import create_app, db
from app.models import StockCard, SuppliesLedgerCard
from app.models.inventory import InventoryItem
from app.models.organization import Organization
from app.models.supplier import Supplier
from app.models.kenya_gov_models import PurchaseOrder, PurchaseOrderItem
from app.services.inventory_service import InventoryService
from app.services.receiving_service import ReceivingService
from app.services.requisition_service import RequisitionService
from app.services.disposal_service import DisposalService


class TestStockCardLedgerIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.org_id = 1
        org = Organization(id=self.org_id, name="Test Org", code="TESTORG")
        db.session.add(org)
        db.session.commit()

        # Create a test user to satisfy foreign key references (requester, receiver)
        from app.models.user import User
        user = User(organisation_id=self.org_id, username="testuser", email="test@example.com", role="employee")
        user.set_password("Password1!")
        db.session.add(user)
        db.session.commit()

        # Supplier for GRN flows
        supplier = Supplier(organisation_id=self.org_id, name="Test Supplier", code="SUP1")
        db.session.add(supplier)
        db.session.commit()

        # Inventory item used across scenarios (create before PO items)
        self.item = InventoryItem(
            organisation_id=self.org_id,
            name="Test Item",
            sku="TEST-001",
            quantity=50,
            unit_price=10.0,
        )
        db.session.add(self.item)
        db.session.commit()

        # Purchase Order for GRN flows
        po = PurchaseOrder(organization_id=self.org_id, po_number="PO-1", supplier_id=supplier.id, total_amount=0.0, status='approved')
        db.session.add(po)
        db.session.commit()
        self.po = po

        # Add a PO item so GRN/receiving tests can validate against the PO
        po_item = PurchaseOrderItem(
            organization_id=self.org_id,
            po_id=po.id,
            item_id=self.item.id,
            quantity=7,
            unit_cost=10.0,
            total_cost=7 * 10.0,
        )
        db.session.add(po_item)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_batch_movements_create_cards(self):
        movements = [
            {"item_id": self.item.id, "type": "OUT", "quantity": 5, "warehouse_id": None, "reference": "BATCH-X"},
            {"item_id": self.item.id, "type": "IN", "quantity": 10, "warehouse_id": None, "reference": "BATCH-Y"},
        ]

        InventoryService(session=db.session).update_stock_batch(self.org_id, movements)

        sc = db.session.query(StockCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()
        ledger = db.session.query(SuppliesLedgerCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()

        self.assertIsNotNone(sc)
        self.assertIsNotNone(ledger)
        # Quantity: start 50 -5 +10 = 55
        item = db.session.get(InventoryItem, self.item.id)
        self.assertEqual(item.quantity, 55)
        self.assertEqual(sc.quantity_on_hand, 55)
        self.assertEqual(int(ledger.quantity_on_hand), 55)
        self.assertEqual(float(ledger.total_value), 55 * float(item.unit_price))

    def test_receiving_approval_updates_cards(self):
        # Create GRN with one item
        items_data = [{"item_id": self.item.id, "quantity_received": 7, "unit_cost": 10.0}]
        grn = ReceivingService.create_grn(self.org_id, self.po.id, received_by_id=1, items_data=items_data)
        # Add inspection report and approve
        ReceivingService.create_inspection_report(self.org_id, grn.id, inspector_id=1, status="passed", comments="ok")
        ReceivingService.approve_grn(grn.id)

        sc = db.session.query(StockCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()
        ledger = db.session.query(SuppliesLedgerCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()

        self.assertIsNotNone(sc)
        self.assertIsNotNone(ledger)
        item = db.session.get(InventoryItem, self.item.id)
        # start 50 +7 = 57
        self.assertEqual(item.quantity, 57)
        self.assertEqual(sc.quantity_on_hand, 57)

    def test_requisition_issue_updates_cards(self):
        # Create RIS for 3 units
        items = [{"item_id": self.item.id, "quantity": 3}]
        ris = RequisitionService.create_requisition(self.org_id, requester_id=1, items_data=items)
        RequisitionService.approve_requisition(ris.id, department_head_id=1)
        RequisitionService.issue_requisition(ris.id)

        sc = db.session.query(StockCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()
        ledger = db.session.query(SuppliesLedgerCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()

        self.assertIsNotNone(sc)
        self.assertIsNotNone(ledger)
        item = db.session.get(InventoryItem, self.item.id)
        # start 50 -3 = 47 (note: other tests run in isolation due to setUp/tearDown)
        self.assertEqual(item.quantity, 47)
        self.assertEqual(sc.quantity_on_hand, 47)

    def test_disposal_execution_updates_cards(self):
        # Create disposal request for 4 units
        items = [{"item_id": self.item.id, "quantity": 4, "reason": "damaged"}]
        disp = DisposalService.create_disposal_request(self.org_id, requester_id=1, items_data=items)
        DisposalService.approve_disposal(disp.id, approver_id=1, is_finance_board=False)
        DisposalService.execute_disposal(disp.id)

        sc = db.session.query(StockCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()
        ledger = db.session.query(SuppliesLedgerCard).filter_by(organization_id=self.org_id, item_id=self.item.id, location_id=None).first()

        self.assertIsNotNone(sc)
        self.assertIsNotNone(ledger)
        item = db.session.get(InventoryItem, self.item.id)
        # start 50 -4 = 46
        self.assertEqual(item.quantity, 46)
        self.assertEqual(sc.quantity_on_hand, 46)


if __name__ == "__main__":
    unittest.main()
