"""Run staging verification SQL checks against the configured DB.

Usage:
  PYTHONPATH=backend python backend/scripts/staging_verification.py --config production

This script uses the app factory to connect via the project's SQLAlchemy
`db` object. It runs a set of verification queries (table/column checks,
counts of missing backfill values, reconciliation samples) and prints
results. Some queries are Postgres-specific and will be skipped when
running against SQLite (e.g., JSON operator queries, pg_indexes).
"""
import argparse
import sys
from textwrap import indent

from app import create_app, db
from sqlalchemy import text


QUERIES = {
    "table_presence": (
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'audit_logs' LIMIT 1;",
        "one",
    ),
    "columns_reference_user_agent": (
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name IN ('reference','user_agent');",
        "all",
    ),
    "missing_reference_count": (
        "SELECT count(*) as missing_reference FROM audit_logs WHERE reference IS NULL OR trim(reference) = '';",
        "one",
    ),
    "missing_user_agent_count": (
        "SELECT count(*) as missing_user_agent FROM audit_logs WHERE user_agent IS NULL OR trim(user_agent) = '';",
        "one",
    ),
    "sample_backfilled_candidates": (
        # Postgres JSON operators ->>, ? are used here
        "SELECT id, details->>'reference' AS details_reference, details->>'user_agent' AS details_user_agent, reference, user_agent, action, created_at FROM audit_logs WHERE (reference IS NULL OR trim(reference) = '') AND (details ? 'reference' OR details ? 'user_agent') ORDER BY id DESC LIMIT 50;",
        "all",
    ),
    "pg_indexes_audit_logs": (
        "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'audit_logs';",
        "all",
    ),
    "inventory_vs_ledger_mismatches": (
        "SELECT i.id AS item_id, i.name, i.quantity AS item_quantity, COALESCE(SUM(CASE WHEN sm.type='IN' THEN sm.quantity ELSE -sm.quantity END),0) AS ledger_total FROM inventory_items i LEFT JOIN stock_movements sm ON sm.item_id = i.id GROUP BY i.id HAVING i.quantity != COALESCE(SUM(CASE WHEN sm.type='IN' THEN sm.quantity ELSE -sm.quantity END),0) LIMIT 200;",
        "all",
    ),
    "stock_cards_mismatches": (
        "SELECT sc.id, sc.item_id, sc.quantity_on_hand, COALESCE(SUM(CASE WHEN sm.type='IN' THEN sm.quantity ELSE -sm.quantity END),0) AS computed_qoh FROM stock_cards sc LEFT JOIN stock_movements sm ON sm.item_id = sc.item_id AND sm.warehouse_id = sc.location_id GROUP BY sc.id HAVING sc.quantity_on_hand != COALESCE(SUM(CASE WHEN sm.type='IN' THEN sm.quantity ELSE -sm.quantity END),0) LIMIT 200;",
        "all",
    ),
    "supplies_ledger_mismatches": (
        "SELECT s.id, s.item_id, s.quantity_on_hand, COALESCE(SUM(CASE WHEN sm.type='IN' THEN sm.quantity ELSE -sm.quantity END),0) AS computed_qoh FROM supplies_ledger_cards s LEFT JOIN stock_movements sm ON sm.item_id = s.item_id AND sm.warehouse_id = s.location_id GROUP BY s.id HAVING s.quantity_on_hand != COALESCE(SUM(CASE WHEN sm.type='IN' THEN sm.quantity ELSE -sm.quantity END),0) LIMIT 200;",
        "all",
    ),
    "recent_qr_scan_audits": (
        "SELECT id, action, entity_type, entity_id, reference, user_agent, created_at FROM audit_logs WHERE action LIKE 'QR_SCAN_%' ORDER BY created_at DESC LIMIT 50;",
        "all",
    ),
}


def run_query(key, sql, fetch):
    print(f"-- {key} --")
    try:
        res = db.session.execute(text(sql))
        if fetch == "one":
            row = res.fetchone()
            print(row)
        else:
            rows = res.fetchall()
            print(f"Rows: {len(rows)}")
            for r in rows[:10]:
                print(r)
            if len(rows) > 10:
                print(f"... (showing 10 of {len(rows)})")
    except Exception as e:
        print(indent(f"skipped or error: {e}", "  "))


def main(config_name: str):
    app = create_app(config_name)
    with app.app_context():
        print(f"Running staging verification (config={config_name})")
        # Basic health check via app endpoint
        try:
            res = db.session.execute(text("SELECT 1"))
            print("DB connection: OK")
        except Exception as e:
            print(f"DB connection failed: {e}")
            sys.exit(2)

        for k, (sql, fetch) in QUERIES.items():
            run_query(k, sql, fetch)
            print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Staging verification checks for TrackIT")
    parser.add_argument("--config", default=None, help="Flask config name (production/testing)")
    args = parser.parse_args()
    cfg = args.config or None
    main(cfg)
