#!/usr/bin/env python3
"""Reset user lock and print purchase orders to debug GRN issue"""
import sys
import os
os.chdir('c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')
sys.path.insert(0, 'c:\\Users\\fivid\\Desktop\\Nova Lite Limited\\TrackIT-main\\backend')

from app import create_app, db
from app.models.user import User
from app.models.kenya_gov_models import PurchaseOrder, PurchaseOrderItem

app = create_app('development')

with app.app_context():
    # Reset user lock
    user = User.query.filter_by(email='depthead@techcorp.com').first()
    if user:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        print(f"✅ User {user.email} unlocked")
    
    # List purchase orders
    print("\n📋 Purchase Orders:")
    pos = PurchaseOrder.query.all()
    for po in pos:
        print(f"  ID={po.id}, PO#={po.po_number}, Status={po.status}, Amount={po.total_amount}")
        # List items for this PO
        items = PurchaseOrderItem.query.filter_by(po_id=po.id).all()
        for item in items:
            print(f"    - Item {item.item_id}: qty={item.quantity}, unit_cost={item.unit_cost}")
