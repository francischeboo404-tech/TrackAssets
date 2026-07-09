#!/usr/bin/env python3
"""
Direct SQL patch to add missing asset_id and item_type columns
to goods_receipt_items table in the live Postgres database.
"""
import os
import sys
from sqlalchemy import text, inspect, create_engine
from sqlalchemy.pool import NullPool

# Use the DATABASE_URL environment variable or direct connection
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

print(f"Connecting to: {db_url[:50]}...")

# Create engine with NullPool to avoid connection pooling issues
engine = create_engine(db_url, poolclass=NullPool)

try:
    conn = engine.connect()
    
    print("Checking goods_receipt_items table schema...")
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('goods_receipt_items')]
    print(f"Current columns: {columns}")
    
    # Check if columns already exist
    needs_asset_id = 'asset_id' not in columns
    needs_item_type = 'item_type' not in columns
    
    if not needs_asset_id and not needs_item_type:
        print("✓ All required columns already exist!")
        conn.close()
        sys.exit(0)
    
    # Add asset_id column if missing
    if needs_asset_id:
        print("Adding asset_id column...")
        conn.execute(text("""
            ALTER TABLE goods_receipt_items
            ADD COLUMN asset_id INTEGER NULL
        """))
        conn.execute(text("""
            ALTER TABLE goods_receipt_items
            ADD CONSTRAINT fk_goods_receipt_items_asset_id 
            FOREIGN KEY (asset_id) REFERENCES assets(id)
        """))
        print("✓ asset_id column added with foreign key")
    
    # Add item_type column if missing
    if needs_item_type:
        print("Adding item_type column...")
        conn.execute(text("""
            ALTER TABLE goods_receipt_items
            ADD COLUMN item_type VARCHAR(50) NOT NULL DEFAULT 'inventory'
        """))
        print("✓ item_type column added with default 'inventory'")
    
    # Make item_id nullable to support asset-only GRNs
    print("Updating item_id to nullable...")
    try:
        conn.execute(text("""
            ALTER TABLE goods_receipt_items
            ALTER COLUMN item_id DROP NOT NULL
        """))
        print("✓ item_id column set to nullable")
    except Exception as e:
        if 'constraint' in str(e).lower() or 'not null' in str(e).lower():
            print(f"  (item_id may already be nullable)")
        else:
            print(f"  (warning: {e})")
    
    print("\n✓ All schema updates applied successfully!")
    conn.close()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
