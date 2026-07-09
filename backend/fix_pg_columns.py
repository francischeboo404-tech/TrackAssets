"""
Cross-DB column fix script — works on both SQLite and PostgreSQL.
Adds warehouse_id to all tables that need it, safely.
"""
from app import create_app, db
from sqlalchemy import text, inspect as sa_inspect

app = create_app()
with app.app_context():
    engine = db.engine
    is_pg = str(engine.url).startswith("postgresql")
    print("DB:", "PostgreSQL" if is_pg else "SQLite", "|", str(engine.url)[:60])
    insp = sa_inspect(engine)

    def col_exists(table, col):
        try:
            return col in [c["name"] for c in insp.get_columns(table)]
        except Exception:
            return False

    tables = [
        "audit_logs",
        "departments",
        "purchase_requests",
        "goods_receipt_notes",
    ]

    print("\n=== Adding missing warehouse_id columns ===")
    with engine.begin() as conn:
        for table in tables:
            if col_exists(table, "warehouse_id"):
                print(f"  SKIP {table}.warehouse_id (already exists)")
                continue
            try:
                if is_pg:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS warehouse_id INTEGER"))
                else:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN warehouse_id INTEGER"))
                print(f"  ADDED {table}.warehouse_id")
            except Exception as e:
                print(f"  FAIL  {table}: {e}")

    print("\n=== Creating performance indexes ===")
    idx_ops = [
        ("ix_departments_wh_id",       "departments",       "warehouse_id"),
        ("ix_audit_logs_org_created",  "audit_logs",        "organisation_id, created_at"),
        ("ix_assets_org_wh",           "assets",            "organisation_id, warehouse_id"),
        ("ix_inventory_org",           "inventory_items",   "organisation_id, is_active"),
        ("ix_wh_stock_wh_item",        "warehouse_stock",   "warehouse_id, item_id"),
    ]
    with engine.begin() as conn:
        for idx_name, tbl, cols in idx_ops:
            try:
                if is_pg:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl}({cols})"))
                else:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl}({cols})"))
                print(f"  OK: {idx_name}")
            except Exception as e:
                print(f"  SKIP {idx_name}: {str(e)[:80]}")

    print("\n=== Final verification ===")
    insp2 = sa_inspect(engine)
    for table in tables:
        has = col_exists(table, "warehouse_id")
        status = "OK" if has else "MISSING!"
        print(f"  {table}.warehouse_id => {status}")

    print("\nDone.")
