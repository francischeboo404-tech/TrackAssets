from datetime import datetime
from sqlalchemy import text
from flask import current_app
from app import db
import time


def initialize_tenant_schema(organisation_id):
    """
    Initialize a tenant schema safely using advisory locks and a simple per-schema
    migration table. This keeps schema creation idempotent and prevents race
    conditions when multiple processes attempt to initialize the same tenant.

    This is a lightweight migration runner that records a single initial
    migration '0001_create_tables' using SQLAlchemy's create_all().
    """
    if not organisation_id:
        return False

    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    # For SQLite (dev), fall back to a single shared database using create_all
    if db_uri.startswith("sqlite"):
        # Ensure default tables exist
        with current_app.app_context():
            db.create_all()
        return True

    schema_name = f"tenant_{organisation_id:04d}"

    try:
        # 1. Create schema if not exists
        db.session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        db.session.commit()

        # 2. Acquire an advisory lock to avoid race conditions across processes
        # Prefer non-blocking try-lock to avoid indefinite blocking on startup
        lock_acquired = False
        try:
            res = db.session.execute(text("SELECT pg_try_advisory_lock(hashtext(:s)::bigint) AS acquired"), {"s": schema_name})
            row = res.fetchone()
            if row and (row[0] is True or row[0] == 1):
                lock_acquired = True
        except Exception:
            # Fallback if hashtext not available
            try:
                res = db.session.execute(text("SELECT pg_try_advisory_lock( ( ('x' || md5(:s))::bit(64)::bigint ) ) AS acquired"), {"s": schema_name})
                row = res.fetchone()
                if row and (row[0] is True or row[0] == 1):
                    lock_acquired = True
            except Exception:
                pass

        # Retry a few times with backoff before giving up to avoid long blocking
        attempts = 0
        while not lock_acquired and attempts < 10:
            attempts += 1
            time.sleep(0.5)
            try:
                res = db.session.execute(text("SELECT pg_try_advisory_lock(hashtext(:s)::bigint) AS acquired"), {"s": schema_name})
                row = res.fetchone()
                if row and (row[0] is True or row[0] == 1):
                    lock_acquired = True
                    break
            except Exception:
                try:
                    res = db.session.execute(text("SELECT pg_try_advisory_lock( ( ('x' || md5(:s))::bit(64)::bigint ) ) AS acquired"), {"s": schema_name})
                    row = res.fetchone()
                    if row and (row[0] is True or row[0] == 1):
                        lock_acquired = True
                        break
                except Exception:
                    pass

        if not lock_acquired:
            current_app.logger.warning(f"Could not acquire advisory lock for {schema_name} after {attempts} attempts; proceeding without lock (risk of race condition)")

        # 3. Ensure migration tracking table exists in the tenant schema
        # Switch search_path to the tenant schema so creations happen there
        db.session.execute(text(f"SET search_path TO {schema_name}, public"))
        db.session.commit()

        # If schema_migrations table does not exist, create it
        exists = db.session.execute(text("SELECT to_regclass('schema_migrations')")).scalar()
        if not exists:
            db.session.execute(text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE NOT NULL
                )
                """
            ))
            db.session.commit()

        # 4. Apply initial migration if missing
        row = db.session.execute(text("SELECT version FROM schema_migrations WHERE version = :v"), {"v": "0001_create_tables"}).fetchone()
        if not row:
            # Use SQLAlchemy metadata to create tables in the tenant schema (current search_path)
            # This is idempotent and safe inside the advisory lock (if acquired)
            db.create_all()

            db.session.execute(text(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (:v, now())"
            ), {"v": "0001_create_tables"})
            db.session.commit()

        # 5. Release advisory lock if we acquired it
        if lock_acquired:
            try:
                db.session.execute(text("SELECT pg_advisory_unlock(hashtext(:s)::bigint)"), {"s": schema_name})
            except Exception:
                try:
                    db.session.execute(text("SELECT pg_advisory_unlock( ( ('x' || md5(:s))::bit(64)::bigint ) )"), {"s": schema_name})
                except Exception:
                    pass
            db.session.commit()

        current_app.logger.info(f"Initialized tenant schema {schema_name}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to initialize tenant schema {schema_name}: {e}")
        try:
            if lock_acquired:
                db.session.execute(text("SELECT pg_advisory_unlock(hashtext(:s)::bigint)"), {"s": schema_name})
                db.session.commit()
        except Exception:
            # ignore
            pass
        db.session.rollback()
        return False
