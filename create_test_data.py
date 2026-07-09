#!/usr/bin/env python3
"""Create test data: PR → PO → approve PO, then test GRN creation"""
import sys
import os
os.chdir('c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')
sys.path.insert(0, 'c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')

# Set encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app import create_app, db
from app.models.user import User
from app.models.organization import Organization
from app.models.inventory import InventoryItem
from app.models.supplier import Supplier
from app.models.kenya_gov_models import (
    PurchaseRequest, PurchaseRequestItem,
    PurchaseOrder, PurchaseOrderItem
)
from datetime import datetime, timezone

app = create_app('development')

with app.app_context():
    # Find org
    org = Organization.query.first()
    if not org:
        print("❌ No organization found")
        sys.exit(1)
    print(f"✅ Using org: {org.name} (id={org.id})")
    
    # Find user
    user = User.query.filter_by(email='admin@test.com').first()
    if not user:
        print("❌ No user found")
        sys.exit(1)
    print(f"✅ Using user: {user.email} (id={user.id})")
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()
    print(f"   Unlocked user account")
    
    # Find or create inventory items
    inv = InventoryItem.query.filter_by(organisation_id=org.id).first()
    if not inv:
        print("❌ No inventory items found, creating...")
        inv = InventoryItem(
            organisation_id=org.id,
            name="Office Paper A4",
            sku="PAPER-A4",
            description="White paper 80gsm",
            quantity=1000,
            reorder_level=100,
            unit_price=2500.00,
            unit='box'
        )
        db.session.add(inv)
        db.session.commit()
    print(f"✅ Using inventory: {inv.name} (id={inv.id}, SKU={inv.sku})")
    
    # Find or create supplier
    supplier = Supplier.query.filter_by(organisation_id=org.id).first()
    if not supplier:
        print("Creating supplier...")
        supplier = Supplier(
            organisation_id=org.id,
            name="Test Supplier",
            code="TS-001",
            email="supplier@test.com",
            phone="0123456789"
        )
        db.session.add(supplier)
        db.session.commit()
    print(f"Using supplier: {supplier.name} (id={supplier.id})")
    
    # Create PR
    print("\nCreating Purchase Request...")
    pr = PurchaseRequest(
        organization_id=org.id,
        pr_number=f"PR-{datetime.now(timezone.utc).year}-00001",
        requester_id=user.id,
        reason="Test PR for GRN workflow"
    )
    db.session.add(pr)
    db.session.commit()
    print(f"PR created: {pr.pr_number} (id={pr.id})")
    
    # Create PR item
    pr_item = PurchaseRequestItem(
        organization_id=org.id,
        pr_id=pr.id,
        item_id=inv.id,
        quantity=100,
        estimated_cost=250000.00,
        justification="Needed for office use"
    )
    db.session.add(pr_item)
    db.session.commit()
    print(f"PR item created: {inv.name} qty={pr_item.quantity}")
    
    # Create PO
    print("\nCreating Purchase Order...")
    po = PurchaseOrder(
        organization_id=org.id,
        po_number=f"PO-{datetime.now(timezone.utc).year}-00001",
        pr_id=pr.id,
        supplier_id=supplier.id,
        total_amount=250000.00,
        status='pending',
        created_by=user.id
    )
    db.session.add(po)
    db.session.commit()
    print(f"PO created: {po.po_number} (id={po.id}, status={po.status})")
    
    # Create PO item
    po_item = PurchaseOrderItem(
        organization_id=org.id,
        po_id=po.id,
        item_id=inv.id,
        quantity=100,
        unit_cost=2500.00,
        total_cost=250000.00
    )
    db.session.add(po_item)
    db.session.commit()
    print(f"PO item created: {inv.name} qty={po_item.quantity}, unit_cost={po_item.unit_cost}")
    
    # Approve PO
    print("\nApproving PO...")
    po.status = 'approved'
    po.approved_at = datetime.now(timezone.utc)
    db.session.commit()
    print(f"PO approved: {po.po_number} (status={po.status})")
    
    print(f"\nTest data ready!")
    print(f"   - PR: {pr.pr_number} (id={pr.id})")
    print(f"   - PO: {po.po_number} (id={po.id}, status=approved)")
    print(f"   - Item: {inv.name} (id={inv.id})")
    print(f"   - Supplier: {supplier.name} (id={supplier.id})")
    print(f"\n Use PO id={po.id} to test GRN creation")
