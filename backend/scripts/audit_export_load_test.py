"""Simple load-check for /api/audit/export using Flask test client.

This script seeds a configurable number of `AuditLog` rows and issues
several sequential requests to `/api/audit/export` using the app's test
client to measure response time and bytes returned. Designed for local
staging/CI smoke checks (not for production load testing).
"""
import argparse
import time
from datetime import datetime, timezone

from app import create_app, db
from app.models.inventory import AuditLog
from app.models.organization import Organization
from app.models.user import User
from flask_jwt_extended import create_access_token


def run_load_test(rows=5000, requests_count=3, config_name="testing"):
    app = create_app(config_name)
    with app.app_context():
        # Ensure schema exists for testing environments
        db.create_all()

        org = Organization.query.get(1)
        if not org:
            org = Organization(id=1, name="Load Test Org", code="LOAD")
            db.session.add(org)
            db.session.commit()

        admin = User.query.get(1)
        if not admin:
            admin = User(id=1, organisation_id=org.id, username="load_admin", email="admin@load", role="admin")
            admin.set_password("Password123!")
            db.session.add(admin)
            db.session.commit()

        existing = AuditLog.query.filter_by(organisation_id=org.id).count()
        to_create = max(0, rows - existing)
        if to_create > 0:
            print(f"Seeding {to_create} audit rows (total target {rows})...")
            batch = 500
            created = 0
            while created < to_create:
                chunk = min(batch, to_create - created)
                objs = []
                for i in range(chunk):
                    idx = existing + created + i
                    objs.append(
                        AuditLog(
                            organisation_id=org.id,
                            user_id=admin.id,
                            action="LOAD_TEST",
                            entity_type="inventory",
                            entity_id=idx,
                            details={"i": idx},
                            ip_address="127.0.0.1",
                            user_agent="load-check",
                            reference=f"LT-{idx}",
                            created_at=datetime.now(timezone.utc),
                        )
                    )
                db.session.bulk_save_objects(objs)
                db.session.commit()
                created += chunk
            print("Seeding complete")

        token = create_access_token(identity=str(admin.id))

        with app.test_client() as client:
            times = []
            sizes = []
            for n in range(requests_count):
                start = time.perf_counter()
                res = client.get(
                    "/api/audit/export",
                    headers={"Authorization": f"Bearer {token}"},
                )
                duration = time.perf_counter() - start
                # Join response generator to measure bytes
                data = b"".join(res.response)
                size = len(data)
                times.append(duration)
                sizes.append(size)
                print(f"Request {n+1}/{requests_count}: {duration:.3f}s, {size} bytes, status={res.status_code}")

            import statistics

            print("\nSummary:")
            print(f"Requests: {requests_count}")
            print(f"Avg time: {statistics.mean(times):.3f}s, min: {min(times):.3f}s, max: {max(times):.3f}s")
            print(f"Avg bytes: {int(statistics.mean(sizes))}, total bytes: {sum(sizes)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit export load-check (Flask test client)")
    parser.add_argument("--rows", type=int, default=1000, help="Number of audit rows to seed")
    parser.add_argument("--requests", type=int, default=3, help="Number of export requests to issue")
    parser.add_argument("--config", type=str, default="testing", help="Flask config name (testing|production)")
    args = parser.parse_args()
    run_load_test(rows=args.rows, requests_count=args.requests, config_name=args.config)
