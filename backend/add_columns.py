import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from sqlalchemy import text

app = create_app('development')
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE inventory_items ADD COLUMN maximum_stock INTEGER;"))
        print("Added maximum_stock")
    except Exception as e:
        print(e)
        
    try:
        db.session.execute(text("ALTER TABLE inventory_items ADD COLUMN category_id INTEGER;"))
        print("Added category_id")
    except Exception as e:
        print(e)
        
    try:
        db.session.execute(text("ALTER TABLE inventory_items ADD COLUMN unit_of_measure VARCHAR(50);"))
        print("Added unit_of_measure")
    except Exception as e:
        print(e)
        
    try:
        # Check stock_movements missing columns
        db.session.execute(text("ALTER TABLE stock_movements ADD COLUMN document_number VARCHAR(100);"))
        print("Added document_number to stock_movements")
    except Exception as e:
        print(e)
        
    try:
        db.session.execute(text("ALTER TABLE stock_movements ADD COLUMN expiry_date DATETIME;"))
        print("Added expiry_date to stock_movements")
    except Exception as e:
        print(e)
        
    db.session.commit()
    print("Columns added successfully!")
