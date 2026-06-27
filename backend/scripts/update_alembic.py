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
print("Updating alembic_version...")
engine.execute(text("UPDATE alembic_version SET version_num='02359c89cba4'"))
print("Updated alembic_version to 02359c89cba4.")
