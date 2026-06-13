import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import InventoryItem, Asset, Warehouse
from app.models.stock_levels import WarehouseStock
from app.models.restock_alert import RestockAlert

app = create_app()
with app.app_context():
    print("--- INVENTORY ITEMS ---")
    items = InventoryItem.query.all()
    for item in items:
        print(f"ID: {item.id}, Name: {item.name}, Qty: {item.quantity}, Price: {item.unit_price}, Active: {item.is_active}, Org: {item.organisation_id}")
    
    print("\n--- WAREHOUSE STOCKS ---")
    wh_stocks = WarehouseStock.query.all()
    for ws in wh_stocks:
        print(f"ID: {ws.id}, ItemID: {ws.item_id}, WH_ID: {ws.warehouse_id}, QtyOnHand: {ws.quantity_on_hand}")

    print("\n--- FIXED ASSETS ---")
    assets = Asset.query.all()
    for a in assets:
        print(f"ID: {a.id}, Name: {a.name}, PurchaseVal: {a.purchase_value}, CurrentVal: {a.current_value}, Status: {a.status}, WH_ID: {a.warehouse_id}")

    print("\n--- WAREHOUSES ---")
    warehouses = Warehouse.query.all()
    for w in warehouses:
        print(f"ID: {w.id}, Name: {w.name}, Active: {w.is_active}")
