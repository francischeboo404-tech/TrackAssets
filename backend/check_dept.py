from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    result = db.session.execute(text("PRAGMA table_info(departments)")).fetchall()
    cols = [r[1] for r in result]
    print("departments columns:", cols)
    print("warehouse_id present:", "warehouse_id" in cols)
