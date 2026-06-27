import os
import sys
from dotenv import load_dotenv

# Setup environment to run Flask app context
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
os.environ['FLASK_APP'] = 'run.py'

from app import create_app, db
from app.models.user import User
from app.models.organization import Organization
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.models.kenya_gov_models import StockCard, SuppliesLedgerCard, PurchaseRequest, PurchaseOrder, GoodsReceiptNote, InspectionReport
from app.services.procurement_service import ProcurementService
from app.services.receiving_service import ReceivingService
from app.services.inventory_service import InventoryService
from sqlalchemy.orm import sessionmaker

def verify_procurement_workflow():
    app = create_app()
    with app.app_context():
        # Setup: Get Org, User, Supplier, Item
        print("--- Fetching Base Data ---")
        org = Organization.query.first()
        if not org:
            print("No organization found. Please seed the database first.")
            return

        admin = User.query.filter_by(role='admin').first()
        po_officer = User.query.filter_by(role='procurement_officer').first()
        supplier = Supplier.query.first()
        if not supplier:
            supplier = Supplier(organisation_id=org.id, name="Test Supplier", code="SUP-001", email="test@supplier.com", phone="123456789", is_active=True)
            db.session.add(supplier)
            db.session.commit()
        
        # Create an item if none exists
        items = InventoryItem.query.filter_by(organisation_id=org.id).all()
        if not items:
            inv_service = InventoryService()
            item = inv_service.create_item(org.id, {
                "name": "Test Procurement Item",
                "sku": "PROC-001",
                "unit_price": 50.0,
                "unit": "pcs",
                "description": "Item for procurement testing"
            })
        else:
            item = items[0]

        print(f"Using Item: {item.name} (SKU: {item.sku}), initial qty: {item.quantity}")

        # 1. Create PR
        print("\n--- 1. Creating Purchase Request ---")
        pr = ProcurementService.create_purchase_request(
            org_id=org.id,
            requester_id=admin.id,
            reason="Need more stock",
            items_data=[{"item_id": item.id, "quantity": 100, "estimated_cost": 5000.0, "justification": "Low stock"}]
        )
        print(f"Created PR: {pr.pr_number} (Status: {pr.status})")
        assert pr.status == 'pending', "PR should be pending initially"

        # 2. Approve PR
        print("\n--- 2. Approving Purchase Request ---")
        pr = ProcurementService.approve_purchase_request(pr.id, admin.id)
        print(f"Approved PR: {pr.pr_number} (Status: {pr.status})")
        assert pr.status == 'approved', "PR should be approved"

        # 3. Create PO
        print("\n--- 3. Creating Purchase Order ---")
        po = ProcurementService.create_purchase_order(
            org_id=org.id,
            pr_id=pr.id,
            supplier_id=supplier.id if supplier else 1,
            items_data=[{"item_id": item.id, "quantity": 100, "unit_cost": 50.0}]
        )
        print(f"Created PO: {po.po_number} (Status: {po.status})")
        assert po.status == 'pending', "PO should be pending initially"

        # 4. Canvass Quotes (PO is 5000 KES, so > 1000 KES requires 3 quotes)
        print("\n--- 4. Adding Canvass Quotes ---")
        import datetime
        today = datetime.date.today()
        ProcurementService.add_canvass_quote(org.id, po.id, "Supplier A", "Item 1", 52.0, today)
        ProcurementService.add_canvass_quote(org.id, po.id, "Supplier B", "Item 1", 51.0, today)
        ProcurementService.add_canvass_quote(org.id, po.id, "Supplier C", "Item 1", 49.0, today)

        # 5. Approve PO
        print("\n--- 5. Approving Purchase Order ---")
        po = ProcurementService.approve_purchase_order(po.id)
        print(f"Approved PO: {po.po_number} (Status: {po.status})")
        assert po.status == 'approved', "PO should be approved"

        # 5. Receive Goods (GRN) into Quarantine
        print("\n--- 5. Receiving Goods (GRN) ---")
        grn = ReceivingService.create_grn(
            org_id=org.id,
            po_id=po.id,
            received_by_id=admin.id,
            items_data=[{"item_id": item.id, "quantity_received": 100, "unit_cost": 50.0}]
        )
        print(f"Created GRN: {grn.grn_number} (Status: {grn.status})")
        assert grn.status == 'quarantine', "GRN should be in quarantine"

        # 6. Inspection Report (IAR) -> Accept all
        print("\n--- 6. Processing Inspection Report ---")
        from app.models.kenya_gov_models import GoodsReceiptItem
        grn_items = GoodsReceiptItem.query.filter_by(grn_id=grn.id).all()
        
        iar = ReceivingService.process_inspection_items(
            org_id=org.id,
            grn_id=grn.id,
            inspector_id=admin.id,
            items_data=[{"grn_item_id": grn_items[0].id, "quantity_accepted": 100, "quantity_rejected": 0}],
            comments="Looks good"
        )
        db.session.refresh(grn)
        db.session.refresh(po)
        db.session.refresh(item)
        print(f"Processed IAR: {iar.iar_number} (IAR Status: {iar.status}, GRN Status: {grn.status}, PO Status: {po.status})")
        
        assert iar.status == 'passed', "IAR should be passed"
        assert grn.status == 'approved', "GRN should be approved after IAR"
        assert po.status == 'received', "PO should be fully received"

        print(f"New Item Qty: {item.quantity}")

        # 7. Check Stock Card & Supplies Ledger
        print("\n--- 7. Checking Ledgers ---")
        stock_card = StockCard.query.filter_by(organization_id=org.id, item_id=item.id).order_by(StockCard.id.desc()).first()
        ledger = SuppliesLedgerCard.query.filter_by(organization_id=org.id, item_id=item.id).order_by(SuppliesLedgerCard.id.desc()).first()

        print(f"Stock Card Qty: {stock_card.quantity_on_hand if stock_card else 'None'}")
        print(f"Supplies Ledger Qty: {ledger.quantity_on_hand if ledger else 'None'}, Value: {ledger.total_value if ledger else 'None'}")

        assert stock_card is not None, "Stock card should be created/updated"
        assert ledger is not None, "Ledger should be created/updated"
        assert stock_card.quantity_on_hand == item.quantity, "Stock card qty should match item qty"
        assert ledger.quantity_on_hand == item.quantity, "Ledger qty should match item qty"
        assert ledger.total_value == item.quantity * 50.0, "Ledger value should be computed accurately based on unit cost"

        print("\n--- SUCCESS! ALL PHASES PASSED ---")

if __name__ == "__main__":
    verify_procurement_workflow()
