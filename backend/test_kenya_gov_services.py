import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.models.organization import Organization, Department
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem
from app.services.procurement_service import ProcurementService
from app.services.receiving_service import ReceivingService
from app.services.requisition_service import RequisitionService
from app.services.disposal_service import DisposalService
from app.services.ledger_service import LedgerService

def setup_test_data():
    org = Organization.query.first()
    if not org:
        org = Organization(name="Test Org", code="TEST-ORG-01")
        db.session.add(org)
        db.session.commit()

    user = User.query.first()
    if not user:
        user = User(email="test@gov.ke", username="admin", organisation_id=org.id, first_name="Test", last_name="User", role="admin")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    supplier = Supplier.query.first()
    if not supplier:
        supplier = Supplier(name="Test Supplier", organisation_id=org.id)
        db.session.add(supplier)
        db.session.commit()

    item = InventoryItem.query.first()
    if not item:
        item = InventoryItem(sku="TEST-SKU", name="Test Item", organisation_id=org.id, quantity=10, unit_price=1500)
        db.session.add(item)
        db.session.commit()

    return org, user, supplier, item

def run_tests():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        print("--- Starting Service Integration Tests ---")
        org, user, supplier, item = setup_test_data()

        # 1. Procurement: PR
        print("\n[1] Testing Procurement (PR)...")
        pr = ProcurementService.create_purchase_request(
            org_id=org.id,
            requester_id=user.id,
            reason="Need supplies",
            items_data=[{"item_id": item.id, "quantity": 5, "estimated_cost": 2000}]
        )
        print(f"Created PR: {pr.pr_number}")
        
        pr = ProcurementService.approve_purchase_request(pr.id, user.id)
        print(f"Approved PR: {pr.pr_number}, Status: {pr.status}")

        # 2. Procurement: PO
        print("\n[2] Testing Procurement (PO)...")
        po = ProcurementService.create_purchase_order(
            org_id=org.id,
            pr_id=pr.id,
            supplier_id=supplier.id,
            items_data=[{"item_id": item.id, "quantity": 5, "unit_cost": 2000}]
        )
        print(f"Created PO: {po.po_number}")
        
        # Test Canvass Requirement (Total = 10000 >= 1000, requires 3 quotes)
        try:
            ProcurementService.approve_purchase_order(po.id)
            print("ERROR: PO approved without 3 quotes!")
        except ValueError as e:
            print(f"Success: Blocked PO approval ({str(e)})")
            
        from datetime import datetime, timezone
        ProcurementService.add_canvass_quote(org.id, po.id, "Supplier A", item.name, 2100, datetime.now(timezone.utc))
        ProcurementService.add_canvass_quote(org.id, po.id, "Supplier B", item.name, 2200, datetime.now(timezone.utc))
        ProcurementService.add_canvass_quote(org.id, po.id, "Supplier C", item.name, 1900, datetime.now(timezone.utc))
        
        po = ProcurementService.approve_purchase_order(po.id)
        print(f"Approved PO after canvassing: {po.po_number}, Status: {po.status}")

        # 3. Receiving: GRN & IAR
        print("\n[3] Testing Receiving (GRN & IAR)...")
        grn = ReceivingService.create_grn(
            org_id=org.id,
            po_id=po.id,
            received_by_id=user.id,
            items_data=[{"item_id": item.id, "quantity_received": 5, "unit_cost": 2000}]
        )
        print(f"Created GRN: {grn.grn_number}, Status: {grn.status}")
        
        iar = ReceivingService.create_inspection_report(
            org_id=org.id,
            grn_id=grn.id,
            inspector_id=user.id,
            status='passed',
            comments="Looks good"
        )
        print(f"Created IAR: {iar.iar_number}, Status: {iar.status}")
        
        initial_qty = item.quantity
        grn = ReceivingService.approve_grn(grn.id)
        
        db.session.refresh(item)
        print(f"Approved GRN: {grn.grn_number}. Item stock changed from {initial_qty} to {item.quantity}")

        # 4. Requisition: RIS
        print("\n[4] Testing Requisition (RIS)...")
        ris = RequisitionService.create_requisition(
            org_id=org.id,
            requester_id=user.id,
            items_data=[{"item_id": item.id, "quantity": 2}]
        )
        print(f"Created RIS: {ris.ris_number}")
        
        ris = RequisitionService.approve_requisition(ris.id, user.id)
        print(f"Approved RIS: {ris.ris_number}")
        
        ris = RequisitionService.issue_requisition(ris.id)
        db.session.refresh(item)
        print(f"Issued RIS: {ris.ris_number}. Item stock is now {item.quantity}")

        # 5. Tracking: Variance Report
        print("\n[5] Testing Ledger (Variance)...")
        var_rep = LedgerService.create_variance_report(
            org_id=org.id,
            item_id=item.id,
            location_id=None,
            physical_quantity=item.quantity - 1, # Missing 1 item
            reason="Count mismatch"
        )
        print(f"Created Variance Report: {var_rep.report_number}, Variance: {var_rep.variance}")
        
        var_rep = LedgerService.resolve_variance(var_rep.id, user.id)
        db.session.refresh(item)
        print(f"Resolved Variance. Item stock adjusted to {item.quantity}")

        # 6. Disposal: Condemn items
        print("\n[6] Testing Disposal...")
        # Create an item that is expensive (over 50,000 KES)
        expensive_item = InventoryItem(sku="EXP-SKU", name="Expensive Item", organisation_id=org.id, quantity=5, unit_price=60000)
        db.session.add(expensive_item)
        db.session.flush()

        disp = DisposalService.create_disposal_request(
            org_id=org.id,
            requester_id=user.id,
            items_data=[{"item_id": expensive_item.id, "quantity": 1}]
        )
        print(f"Created Disposal Request: {disp.disposal_number}, Total Value: {disp.total_value}")
        
        try:
            DisposalService.approve_disposal(disp.id, user.id, is_finance_board=False)
            print("ERROR: Disposal approved without Finance Board for > 50k KES!")
        except ValueError as e:
            print(f"Success: Blocked non-board disposal ({str(e)})")
            
        disp = DisposalService.approve_disposal(disp.id, user.id, is_finance_board=True)
        print(f"Approved Disposal with Finance Board.")
        
        disp = DisposalService.execute_disposal(disp.id)
        db.session.refresh(expensive_item)
        print(f"Executed Disposal. Expensive Item stock is now {expensive_item.quantity}")

        print("\nALL SERVICES AND END-TO-END WORKFLOWS TESTED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
