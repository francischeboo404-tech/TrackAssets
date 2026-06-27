#!/usr/bin/env python3
"""Apply Alembic migrations using the Flask app configuration.

This script will load the Flask app for the requested environment (default: production)
and set the alembic config sqlalchemy.url to the app's SQLALCHEMY_DATABASE_URI, then
run `alembic upgrade head` programmatically.

Usage:
    python scripts/apply_migrations.py --env production
"""
import os
import sys
from pathlib import Path
import argparse

# Ensure repo root on path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from alembic.config import Config
from alembic import command
from app import create_app

parser = argparse.ArgumentParser()
parser.add_argument("--env", default=os.environ.get("FLASK_ENV", "production"), help="Flask env to load (production|development)")
args = parser.parse_args()

flask_env = args.env
print(f"Loading app for environment: {flask_env}")
app = create_app(flask_env)

with app.app_context():
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        print("No SQLALCHEMY_DATABASE_URI configured; aborting")
        sys.exit(2)

    alembic_ini = str(repo_root.joinpath("alembic.ini"))
    print("Using alembic.ini =>", alembic_ini)
    cfg = Config(alembic_ini)
    # Ensure alembic uses the app DB URL
    cfg.set_main_option("sqlalchemy.url", db_url)
    # Ensure alembic script_location points to the repository's migrations folder
    # (use absolute path to avoid resolving relative to current working dir)
    migrations_path = str(repo_root.joinpath("migrations"))
    cfg.set_main_option("script_location", migrations_path)

    print("Applying migrations to:", db_url)
    try:
        from alembic.util import CommandError

        try:
            command.upgrade(cfg, "head")
        except CommandError as ce:
            # If multiple heads exist, attempt to upgrade all heads
            msg = str(ce)
            if "Multiple head revisions" in msg or "Multiple heads are present" in msg:
                print("Multiple heads detected; upgrading all heads (heads)")
                command.upgrade(cfg, "heads")
            else:
                raise

        print("Migrations applied successfully")
    except Exception as e:
        print("Failed to apply migrations:", e)
        raise
