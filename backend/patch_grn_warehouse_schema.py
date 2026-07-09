"""
Direct SQL patch to add warehouse_id to goods_receipt_items table
Similar to patch_grn_schema.py but for warehouse routing enhancement
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

def patch_grn_warehouse_schema():
    """Add warehouse_id column and foreign key to goods_receipt_items if not already present"""
    
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        # Use NullPool to avoid pooling issues during direct SQL operations
        engine = create_engine(db_url, poolclass=NullPool)
        
        with engine.connect() as conn:
            # Check if warehouse_id column already exists
            check_col = text("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'goods_receipt_items'
                AND column_name = 'warehouse_id'
            """)
            result = conn.execute(check_col)
            col_exists = result.scalar() > 0
            
            if col_exists:
                print("✓ warehouse_id column already exists in goods_receipt_items")
                return True
            
            # Add the warehouse_id column
            print("Adding warehouse_id column to goods_receipt_items...")
            add_col = text("""
                ALTER TABLE goods_receipt_items
                ADD COLUMN warehouse_id INTEGER
            """)
            conn.execute(add_col)
            print("✓ warehouse_id column added")
            
            # Add foreign key constraint
            print("Adding foreign key constraint...")
            add_fk = text("""
                ALTER TABLE goods_receipt_items
                ADD CONSTRAINT fk_grn_items_warehouse_id
                FOREIGN KEY (warehouse_id)
                REFERENCES warehouses(id)
            """)
            conn.execute(add_fk)
            print("✓ Foreign key constraint added")
            
            # Add index for performance
            print("Adding index on warehouse_id...")
            add_idx = text("""
                CREATE INDEX ix_grn_items_warehouse_id
                ON goods_receipt_items(warehouse_id)
            """)
            conn.execute(add_idx)
            print("✓ Index created")
            
            conn.commit()
            print("\n✅ Warehouse schema patch applied successfully!")
            return True
            
    except Exception as e:
        print(f"ERROR during patching: {str(e)}")
        return False

if __name__ == "__main__":
    success = patch_grn_warehouse_schema()
    exit(0 if success else 1)
