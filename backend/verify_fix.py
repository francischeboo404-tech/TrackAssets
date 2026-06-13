
import sys
import os
from flask import Flask
from app import create_app, db
from app.services.inventory_service import InventoryService
from app.services.asset_service import AssetService
from app.models.organization import Organization, Department
from app.models.inventory import InventoryItem
from app.models.asset import Asset
from app.models.stock_levels import WarehouseStock
from datetime import datetime

def verify_fixes():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        
        # 1. Setup Org and Dept
        org = Organization.query.first()
        if not org:
            org = Organization(name="Verify Org", code="VORG")
            db.session.add(org)
            db.session.commit()
        
        dept = Department.query.filter_by(organisation_id=org.id).first()
        if not dept:
            dept = Department(name="IT", code="IT", organisation_id=org.id)
            db.session.add(dept)
            db.session.commit()

        inventory_service = InventoryService()
        asset_service = AssetService()

        print("\n--- Testing SKU with Space ---")
        sku_data = {
            "name": "Laptop Space Test",
            "sku": "LAPTOP 001",
            "unit_price": 1000.0,
            "unit": "pcs"
        }
        try:
            item = inventory_service.create_item(org.id, sku_data)
            print(f"[PASS] SKU with space created: {item.sku}")
        except Exception as e:
            print(f"[FAIL] SKU with space failed: {e}")

        print("\n--- Testing Asset-Inventory Sync ---")
        asset_name = "MacBook Pro M3"
        asset_data = {
            "name": asset_name,
            "type": "Hardware",
            "asset_code": "MAC-M3-001",
            "department_id": dept.id,
            "purchase_date": datetime.utcnow().date(),
            "purchase_value": 250000.0,
            "useful_life": 3
        }
        
        # Before count
        inv_item_before = InventoryItem.query.filter_by(organisation_id=org.id, name=asset_name).first()
        qty_before = inv_item_before.quantity if inv_item_before else 0
        print(f"Inventory quantity before: {qty_before}")
        
        try:
            new_asset = asset_service.create_asset(org.id, asset_data)
            print(f"[PASS] Asset created: {new_asset.asset_code}")
            
            inv_item_after = InventoryItem.query.filter_by(organisation_id=org.id, name=asset_name).first()
            qty_after = inv_item_after.quantity if inv_item_after else 0
            print(f"Inventory quantity after: {qty_after}")
            
            if qty_after == qty_before + 1:
                print("[PASS] Inventory synced successfully")
            else:
                print(f"[FAIL] Inventory sync mismatch: expected {qty_before + 1}, got {qty_after}")
        except Exception as e:
            print(f"[FAIL] Asset creation failed: {e}")

        print("\n--- Testing Warehouse Stock Sync ---")
        # Create a warehouse
        from app.models.location_topology import Warehouse
        wh = Warehouse.query.first()
        if not wh:
            wh = Warehouse(name="Main Store", code="MAIN", organisation_id=org.id)
            db.session.add(wh)
            db.session.commit()
        
        test_item = InventoryItem.query.filter_by(organisation_id=org.id).first()
        if test_item:
            print(f"Testing adjustment for item: {test_item.name}")
            initial_qty = test_item.quantity
            
            try:
                inventory_service.update_stock(
                    item_id=test_item.id,
                    org_id=org.id,
                    movement_type="IN",
                    quantity=10,
                    warehouse_id=wh.id,
                    reference="WH-SYNC-TEST"
                )
                
                # Check WarehouseStock
                wh_stock = WarehouseStock.query.filter_by(item_id=test_item.id, warehouse_id=wh.id).first()
                if wh_stock and wh_stock.quantity_on_hand >= 10:
                    print(f"[PASS] Warehouse stock updated: {wh_stock.quantity_on_hand}")
                else:
                    print(f"[FAIL] Warehouse stock not updated correctly: {wh_stock.quantity_on_hand if wh_stock else 'None'}")
                
                if test_item.quantity == initial_qty + 10:
                    print(f"[PASS] Global quantity updated: {test_item.quantity}")
                else:
                    print(f"[FAIL] Global quantity mismatch: expected {initial_qty + 10}, got {test_item.quantity}")
                    
            except Exception as e:
                print(f"[FAIL] Warehouse stock update failed: {e}")

if __name__ == "__main__":
    verify_fixes()
