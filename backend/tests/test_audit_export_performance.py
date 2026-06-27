import unittest
from datetime import datetime, timezone
from app import create_app, db
from app.models.inventory import AuditLog
from app.models.organization import Organization
from app.models.user import User


class TestAuditExportPerformance(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.org = Organization(id=1, name="Perf Org", code="PERF")
        db.session.add(self.org)
        self.admin = User(id=1, organisation_id=1, username="admin", email="admin@perf", role="admin")
        self.admin.set_password("Password123!")
        db.session.add(self.admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _token(self, user):
        from flask_jwt_extended import create_access_token

        return create_access_token(identity=str(user.id))

    def test_export_streams_large_result_set(self):
        # Seed many audit logs
        N = 1000
        rows = []
        for i in range(N):
            a = AuditLog(
                organisation_id=1,
                user_id=1,
                action="TEST_ACTION",
                entity_type="inventory",
                entity_id=i,
                details={"i": i},
                ip_address="127.0.0.1",
                user_agent="perf-test",
                reference=f"REF-{i}",
                created_at=datetime.now(timezone.utc),
            )
            rows.append(a)
        db.session.bulk_save_objects(rows)
        db.session.commit()

        token = self._token(self.admin)
        res = self.client.get(
            "/api/audit/export",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(res.status_code, 200)
        data = b"".join(res.response)
        # Should start with BOM + TrackIT brand
        self.assertTrue(data.startswith(b"\xef\xbb\xbfTrackIT"))
        # Ensure some rows were exported
        self.assertIn(b"TEST_ACTION", data)


if __name__ == "__main__":
    unittest.main()
