import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db

app = create_app('development')
with app.app_context():
    # Force creation of all tables registered in metadata
    db.create_all()
    
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("SUCCESS: Verifying Database Schema...")
    print("TABLES FOUND:")
    for table_name in tables:
        print(f"- {table_name}")
    
    required_tables = [
        'categories', 'purchase_requests', 'purchase_request_items', 
        'purchase_orders', 'purchase_order_items', 'canvass_quotes', 
        'goods_receipt_notes', 'goods_receipt_items', 'inspection_reports', 
        'requisition_slips', 'requisition_items', 'variance_reports', 
        'disposal_requests', 'disposal_items', 'roles', 'role_permissions'
    ]
    missing = [rt for rt in required_tables if rt not in tables]
    if missing:
        print(f"\nWARNING: Missing tables: {missing}")
    else:
        print("\nALL KENYAN GOVERNMENT MODULE TABLES SUCCESSFULLY CREATED AND VERIFIED!")
