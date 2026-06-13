import unittest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import Asset, Warehouse, ScanEvent
from app.services.tracking_service import TrackingService
from app.services.anomaly_service import AnomalyService
from app.services.qr_service import QRService


class TestTrackingAI(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Setup mock data
        self.org_id = 1
        self.user_id = 1

        # Create Organization, Department, User to satisfy foreign key constraints
        from app.models.organization import Organization, Department
        from app.models.user import User

        org = Organization(id=self.org_id, name="Test Org", code="TESTORG")
        db.session.add(org)
        db.session.commit()

        dept = Department(id=1, name="IT Department", code="IT", organisation_id=self.org_id)
        db.session.add(dept)
        db.session.commit()

        user = User(id=self.user_id, username="testuser", email="test@test.com", organisation_id=self.org_id, role="staff")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

        # Warehouses
        self.wh1 = Warehouse(
            organisation_id=self.org_id, name="Warehouse A", code="WHA"
        )
        self.wh2 = Warehouse(
            organisation_id=self.org_id, name="Warehouse B", code="WHB"
        )
        db.session.add_all([self.wh1, self.wh2])
        db.session.commit()

        # Asset
        self.asset = Asset(
            organisation_id=self.org_id,
            asset_code="TEST-ASSET-001",
            name="Testing Laptop",
            type="Electronics",
            department_id=1,
            purchase_date=datetime.utcnow().date(),
            purchase_value=1000.0,
            useful_life=5,
            current_value=1000.0,
            status="approved",
        )
        db.session.add(self.asset)
        db.session.commit()
        self.qr_scan_data = QRService.ensure_asset_qr(self.asset)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_record_scan_updates_location(self):
        """Test that recording a scan updates the asset location."""
        TrackingService.record_scan(
            org_id=self.org_id,
            user_id=self.user_id,
            user_role="staff",
            qr_data=self.qr_scan_data,
            action_type="CHECK_IN",
            warehouse_id=self.wh1.id,
        )

        db.session.refresh(self.asset)
        self.assertEqual(self.asset.location, "WH: Warehouse A")

        # Verify scan event created
        event = ScanEvent.query.filter_by(item_id=self.asset.id).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.warehouse_id, self.wh1.id)

    def test_impossible_travel_anomaly(self):
        """Test detection of scans too close in time for different locations."""
        # First scan
        _, event1 = TrackingService.record_scan(
            org_id=self.org_id,
            user_id=self.user_id,
            user_role="staff",
            qr_data=self.qr_scan_data,
            action_type="CHECK_IN",
            warehouse_id=self.wh1.id,
        )

        # Simulate second scan 1 minute later at different warehouse
        # We manually adjust the timestamp for the test
        event1.timestamp = datetime.utcnow() - timedelta(minutes=5)
        db.session.commit()

        _, event2 = TrackingService.record_scan(
            org_id=self.org_id,
            user_id=self.user_id,
            user_role="staff",
            qr_data=self.qr_scan_data,
            action_type="TRANSFER",
            warehouse_id=self.wh2.id,
        )

        anomalies = AnomalyService.analyze_scan(event2)
        self.assertTrue(
            any(a["type"] == "IMPOSSIBLE_TRAVEL" for a in anomalies)
        )
        print(f"\nDetected Anomaly: {anomalies[0]['message']}")


if __name__ == "__main__":
    unittest.main()
