#!/usr/bin/env python3
"""Test dispatch and transfer operations"""
import sys
import os
os.chdir('backend')
sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.models import Organization, InventoryItem, Warehouse, WarehouseStock
from app.services.inventory_service import InventoryService
from app.services.stock_service import StockService

# Create app and context
app = create_app()

with app.app_context():
    try:
        print("=" * 60)
        print("Testing Transfer/Dispatch Operations")
        print("=" * 60)
        
        # Setup test org
        org = Organization.query.first()
        if not org:
            org = Organization(name="Test Org")
            db.session.add(org)
            db.session.commit()
        org_id = org.id
        print(f"\nUsing org: {org_id}")
        
        # Create test item with warehouse stock
        item_data = {
            "name": "Transfer Test Item",
            "code": "TT-001",
            "unit": "units",
            "unit_price": 100.0,
            "reorder_level": 10,
            "warehouse_id": None,  # Not specifying warehouse
        }
        
        inv_service = InventoryService(session=db.session)
        stock_service = StockService(session=db.session)
        
        # Create item with initial quantity
        item = inv_service.create_item(org_id, {
            **item_data,
            "quantity": 100,  # Initial stock
            "opening_stock": 0
        })
        print(f"✓ Created item: {item.id} - {item.name}")
        print(f"  Initial quantity: {stock_service.get_current_quantity(item.id)}")
        
        # Get/create warehouses for testing
        warehouse1 = Warehouse.query.filter_by(
            organisation_id=org_id, name="Warehouse 1"
        ).first()
        if not warehouse1:
            warehouse1 = Warehouse(
                organisation_id=org_id,
                name="Warehouse 1",
                location="Location 1"
            )
            db.session.add(warehouse1)
            db.session.commit()
        print(f"✓ Warehouse 1: {warehouse1.id}")
        
        warehouse2 = Warehouse.query.filter_by(
            organisation_id=org_id, name="Warehouse 2"
        ).first()
        if not warehouse2:
            warehouse2 = Warehouse(
                organisation_id=org_id,
                name="Warehouse 2",
                location="Location 2"
            )
            db.session.add(warehouse2)
            db.session.commit()
        print(f"✓ Warehouse 2: {warehouse2.id}")
        
        # Move initial quantity to warehouse 1
        print("\n--- Step 1: Transfer initial quantity to Warehouse 1 ---")
        inv_service.update_stock(
            item.id,
            org_id,
            movement_type="IN",
            quantity=100,
            warehouse_id=warehouse1.id,
            reference="INITIAL_STOCK",
            notes="Initial stock to warehouse 1"
        )
        db.session.refresh(item)
        qty_wh1 = stock_service.get_current_quantity(item.id)
        print(f"✓ After IN: Item quantity = {qty_wh1}")
        
        # Test dispatch (OUT from warehouse 1)
        print("\n--- Step 2: Dispatch 30 units from Warehouse 1 ---")
        inv_service.update_stock(
            item.id,
            org_id,
            movement_type="OUT",
            quantity=30,
            warehouse_id=warehouse1.id,
            reference="DISPATCH",
            notes="Dispatch to customer"
        )
        db.session.refresh(item)
        qty_after_dispatch = stock_service.get_current_quantity(item.id)
        print(f"✓ After dispatch: Item quantity = {qty_after_dispatch}")
        
        # Test warehouse transfer (OUT from WH1, IN to WH2)
        print("\n--- Step 3: Transfer 20 units from Warehouse 1 to Warehouse 2 ---")
        inv_service.update_stock(
            item.id,
            org_id,
            movement_type="OUT",  # Movement type must be OUT for transfers
            quantity=20,
            warehouse_id=warehouse1.id,
            destination_warehouse_id=warehouse2.id,
            reference="TRANSFER",
            notes="Transfer between warehouses"
        )
        db.session.refresh(item)
        qty_after_transfer = stock_service.get_current_quantity(item.id)
        print(f"✓ After transfer: Item quantity = {qty_after_transfer}")
        
        # Verify warehouse stock details
        print("\n--- Warehouse Stock Details ---")
        wh1_stock = WarehouseStock.query.filter_by(
            item_id=item.id, warehouse_id=warehouse1.id
        ).first()
        wh2_stock = WarehouseStock.query.filter_by(
            item_id=item.id, warehouse_id=warehouse2.id
        ).first()
        
        print(f"Warehouse 1: {wh1_stock.quantity_on_hand if wh1_stock else 0} units")
        print(f"Warehouse 2: {wh2_stock.quantity_on_hand if wh2_stock else 0} units")
        
        total = (wh1_stock.quantity_on_hand if wh1_stock else 0) + \
                (wh2_stock.quantity_on_hand if wh2_stock else 0)
        print(f"Total: {total} units")
        
        print("\n" + "=" * 60)
        print("✓ All transfer/dispatch operations successful!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.session.close()
