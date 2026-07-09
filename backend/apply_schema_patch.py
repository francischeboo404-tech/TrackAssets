from app import create_app, db
from sqlalchemy import text

app = create_app('development')
with app.app_context():
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        tables = ['purchase_request_items', 'purchase_order_items', 'requisition_items', 'goods_receipt_items']
        for table in tables:
            cols = {row[1] for row in conn.execute(text(f'PRAGMA table_info({table})')).fetchall()}
            if 'item_type' not in cols:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN item_type VARCHAR(50)'))
                conn.execute(text(f'UPDATE {table} SET item_type = "inventory"'))
            if 'asset_id' not in cols and table != 'goods_receipt_items':
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN asset_id INTEGER'))
            if table == 'requisition_items':
                if 'warehouse_id' not in cols:
                    conn.execute(text('ALTER TABLE requisition_items ADD COLUMN warehouse_id INTEGER'))
                if 'bin_id' not in cols:
                    conn.execute(text('ALTER TABLE requisition_items ADD COLUMN bin_id INTEGER'))
            if table == 'goods_receipt_items':
                if 'warehouse_id' not in cols:
                    conn.execute(text('ALTER TABLE goods_receipt_items ADD COLUMN warehouse_id INTEGER'))
        trans.commit()
        print('schema update complete')
    except Exception:
        trans.rollback()
        raise
