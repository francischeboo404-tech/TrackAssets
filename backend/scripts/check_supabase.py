import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()
os.environ["FLASK_ENV"] = "production"

from app import create_app
from sqlalchemy import create_engine, text

app = create_app("production")
db_url = app.config["SQLALCHEMY_DATABASE_URI"]

engine = create_engine(db_url)
with engine.connect() as conn:
    print("--- Tables in public schema ---")
    result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
    tables = [row[0] for row in result]
    for table in tables:
        print(table)
    
    if "alembic_version" in tables:
        print("\n--- Alembic version ---")
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        for row in result:
            print(row[0])
