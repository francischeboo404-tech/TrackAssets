"""Apply schema fixes directly to Supabase PostgreSQL."""
import os
from dotenv import load_dotenv
load_dotenv()

db_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_PROD")
if not db_url:
    print("No DATABASE_URL found")
    exit(1)

print("Connecting to:", db_url[:50])

from sqlalchemy import create_engine, text, inspect as sa_inspect

engine = create_engine(db_url, connect_args={"connect_timeout": 15, "sslmode": "require"})

with engine.connect() as conn:
    print("Connected!")
    
    # Check current column status
    r = conn.execute(text("""
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_name IN ('audit_logs','departments','purchase_requests','goods_receipt_notes')
        AND column_name = 'warehouse_id'
        ORDER BY table_name
    """))
    existing = {row[0] for row in r}
    print("Already have warehouse_id:", existing)

    tables_needing = {'audit_logs','departments','purchase_requests','goods_receipt_notes'} - existing

with engine.begin() as conn:
    for table in tables_needing:
        try:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS warehouse_id INTEGER"))
            print(f"ADDED: {table}.warehouse_id")
        except Exception as e:
            print(f"FAIL {table}: {e}")

    # Performance indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_org_created ON audit_logs(organisation_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_wh_id ON audit_logs(warehouse_id)",
        "CREATE INDEX IF NOT EXISTS ix_departments_wh_id ON departments(warehouse_id)",
        "CREATE INDEX IF NOT EXISTS ix_purchase_requests_wh_id ON purchase_requests(warehouse_id)",
        "CREATE INDEX IF NOT EXISTS ix_assets_org_wh ON assets(organisation_id, warehouse_id)",
        "CREATE INDEX IF NOT EXISTS ix_inventory_org ON inventory_items(organisation_id, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_wh_stock_wh_item ON warehouse_stock(warehouse_id, item_id)",
    ]
    for idx in indexes:
        try:
            conn.execute(text(idx))
            print(f"OK index: {idx.split('EXISTS ')[1].split(' ON')[0]}")
        except Exception as e:
            print(f"SKIP index: {str(e)[:80]}")

print("\nSupabase PostgreSQL schema update complete.")
