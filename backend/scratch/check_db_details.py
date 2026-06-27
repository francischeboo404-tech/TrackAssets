from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models.inventory import InventoryItem, StockMovement
from app.models.organization import Organization, Department
from app.models.user import User

app = create_app('development')

with app.app_context():
    # Let's check what organizations exist
    print("--- Organizations ---")
    orgs = Organization.query.all()
    for o in orgs:
        print(f"ID={o.id}, Name={o.name}, Code={o.code}")
        
    print("\n--- Users ---")
    users = User.query.all()
    for u in users:
        print(f"ID={u.id}, Username={u.username}, Email={u.email}, Role={u.role}, OrgID={u.organisation_id}")
        
    print("\n--- Departments ---")
    depts = Department.query.all()
    for d in depts:
        print(f"ID={d.id}, Name={d.name}, Code={d.code}, OrgID={d.organisation_id}")

    print("\n--- Warehouses ---")
    # Let's inspect the warehouses table if it exists
    from sqlalchemy import text
    try:
        res = db.session.execute(text("SELECT id, name, code, organisation_id FROM warehouses")).fetchall()
        for r in res:
            print(f"ID={r[0]}, Name={r[1]}, Code={r[2]}, OrgID={r[3]}")
        print(f"Total Warehouses: {len(res)}")
    except Exception as e:
        print("Error reading warehouses table:", e)

    print("\n--- Inventory Items ---")
    items = InventoryItem.query.all()
    for i in items:
        print(f"ID={i.id}, Name={i.name}, SKU={i.sku}, Qty={i.quantity}, Reorder={i.reorder_level}, Health={i.health_status}, OrgID={i.organisation_id}")

    print("\n--- Stock Movements ---")
    movements = StockMovement.query.all()
    for m in movements:
        print(f"ID={m.id}, ItemID={m.item_id}, Type={m.type}, Qty={m.quantity}, Reference={m.reference}, WarehouseID={m.warehouse_id}, OrgID={m.organization_id}")
