from app import create_app, db
from sqlalchemy import text
from dotenv import load_dotenv
load_dotenv()

app = create_app()
with app.app_context():
    try:
        db.session.execute(text('ALTER TABLE purchase_orders ADD COLUMN ris_id INTEGER REFERENCES requisition_slips(id);'))
        db.session.commit()
        print("Successfully added ris_id to purchase_orders")
    except Exception as e:
        print("Migration error (might already exist):", e)
