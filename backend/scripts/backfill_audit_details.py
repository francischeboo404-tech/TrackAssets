"""Ad-hoc backfill script for AuditLog.reference and AuditLog.user_agent

Run in a safe environment (staging) before production. This script uses SQLAlchemy
and the app context to iterate rows and populate missing fields from `details`.
"""
from app import create_app, db
from app.models.inventory import AuditLog
import json
import os
import argparse


def run_backfill(batch=500, config_name=None):
    # Determine config: explicit arg, FLASK_ENV, or default to 'production'
    cfg = config_name or os.environ.get("FLASK_ENV") or "production"
    app = create_app(cfg)
    with app.app_context():
        # Ensure the audit_logs table exists before attempting to query
        if not db.engine.has_table(AuditLog.__tablename__):
            print(f"Target database (config={cfg}) does not have table '{AuditLog.__tablename__}'. Ensure migrations were applied.")
            return
        # iterate over audit logs missing reference or user_agent
        query = AuditLog.query.filter(
            db.or_(
                AuditLog.reference == None,
                AuditLog.user_agent == None,
            ),
        )
        total = query.count()
        print(f"Found {total} audit rows to inspect (config={cfg})")
        offset = 0
        while True:
            rows = query.limit(batch).offset(offset).all()
            if not rows:
                break
            for r in rows:
                updated = False
                if r.details:
                    try:
                        details = r.details if isinstance(r.details, dict) else json.loads(r.details)
                    except Exception:
                        details = None
                    if details:
                        ref = details.get('reference')
                        ua = details.get('user_agent')
                        if ref and not r.reference:
                            r.reference = ref
                            updated = True
                        if ua and not r.user_agent:
                            r.user_agent = ua
                            updated = True
                if updated:
                    db.session.add(r)
            db.session.commit()
            offset += batch
        print('Backfill complete')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill AuditLog.reference and user_agent from details')
    parser.add_argument('--batch', type=int, default=500, help='Batch size to process per transaction')
    parser.add_argument('--config', type=str, default=None, help='Flask config name (testing|development|production)')
    args = parser.parse_args()
    run_backfill(batch=args.batch, config_name=args.config)
