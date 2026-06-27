#!/usr/bin/env python3
"""Test DB connectivity using SQLAlchemy engine from the Flask app config."""
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from app import create_app, db
from sqlalchemy import text

env = os.environ.get("FLASK_ENV", "production")
app = create_app(env)

with app.app_context():
    url = app.config.get("SQLALCHEMY_DATABASE_URI")
    print("Using DB URL:", url)
    try:
        # Simple check
        res = db.session.execute(text("SELECT 1"))
        print("DB connectivity OK ->", list(res))
    except Exception as e:
        print("DB connectivity failed:", e)
        raise
