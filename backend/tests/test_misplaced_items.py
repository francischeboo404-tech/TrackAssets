"""
Test Suite: Phase 3 — Misplaced Items Detection

Tests the predict_misplaced_items() implementation for:
1. Asset misplaced detection
2. Inventory misplaced detection
3. ItemInstance misplaced detection
4. Severity scoring
5. Edge cases (no scans, stale data, correct locations)
"""

import unittest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.asset import Asset, AssetStatus
from app.models.inventory import InventoryItem
from app.models.item_instance import ItemInstance
from app.models.location_topology import Warehouse
from app.models.organization import Organization, Department
from app.models.scan_event import ScanEvent
from app.models.user import User
from app.services.anomaly_service import AnomalyService
from app.services.qr_service import QRService


class TestMisplacedItemsDetection(unittest.TestCase):
    """Test suite for misplaced items detection"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create organization
        self.org = Organization(id=1, name="Test Org", code="TESTORG")
        db.session.add(self.org)
        db.session.flush()
        self.org_id = self.org.id

        # Create departments
        self.dept_it = Department(
            id=1, name="IT Department", code="IT", organisation_id=self.org_id
        )
        self.dept_hr = Department(
            id=2, name="HR Department", code="HR", organisation_id=self.org_id
        )
        self.dept_finance = Department(
            id=3, name="Finance Department", code="FIN", organisation_id=self.org_id
        )
        db.session.add_all([self.dept_it, self.dept_hr, self.dept_finance])
        db.session.flush()

        # Create warehouses
        self.wh_it = Warehouse(
            organisation_id=self.org_id, name="IT Warehouse", code="WH-IT"
        )
        self.wh_hr = Warehouse(
            organisation_id=self.org_id, name="HR Warehouse", code="WH-HR"
        )
        self.wh_finance = Warehouse(
            organisation_id=self.org_id, name="Finance Warehouse", code="WH-FIN"
        )
        db.session.add_all([self.wh_it, self.wh_hr, self.wh_finance])
        db.session.flush()

        # Assign warehouses to departments
        self.dept_it.warehouse_id = self.wh_it.id
        self.dept_hr.warehouse_id = self.wh_hr.id
        self.dept_finance.warehouse_id = self.wh_finance.id
        db.session.commit()

        # Create user
        self.user = User(
            id=1,
            username="testuser",
            email="test@test.com",
            organisation_id=self.org_id,
            role="staff",
        )
        self.user.set_password("Password123!")
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # =========================================================================
    # ASSET TESTS
    # =========================================================================

    def test_asset_correct_location(self):
        """Asset in correct location should NOT be flagged"""
        asset = Asset(
            organisation_id=self.org_id,
            asset_code="LAPTOP-001",
            name="Test Laptop",
            type="Electronics",
            department_id=self.dept_it.id,
            assigned_department_id=self.dept_it.id,
            warehouse_id=self.wh_it.id,
            purchase_date=datetime.utcnow().date(),
            purchase_value=1000.0,
            useful_life=5,
            current_value=1000.0,
            status=AssetStatus.ASSIGNED.value,
        )
        db.session.add(asset)
        db.session.flush()

        # Scan at correct warehouse
        scan = ScanEvent(
            organisation_id=self.org_id,
            item_type="asset",
            item_id=asset.id,
            warehouse_id=self.wh_it.id,
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should NOT be flagged
        self.assertEqual(len(anomalies), 0, "Correctly located asset should not be flagged")

    def test_asset_wrong_warehouse(self):
        """Asset in wrong warehouse should be HIGH severity"""
        asset = Asset(
            organisation_id=self.org_id,
            asset_code="LAPTOP-002",
            name="Test Laptop",
            type="Electronics",
            department_id=self.dept_it.id,
            assigned_department_id=self.dept_it.id,
            warehouse_id=self.wh_it.id,  # Expected in IT warehouse
            purchase_date=datetime.utcnow().date(),
            purchase_value=1000.0,
            useful_life=5,
            current_value=1000.0,
            status=AssetStatus.ASSIGNED.value,
        )
        db.session.add(asset)
        db.session.flush()

        # Scan at wrong warehouse
        scan = ScanEvent(
            organisation_id=self.org_id,
            item_type="asset",
            item_id=asset.id,
            warehouse_id=self.wh_hr.id,  # Actually in HR warehouse!
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should be flagged as HIGH severity
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["type"], "MISPLACED_ITEM")
        self.assertEqual(anomalies[0]["severity"], "HIGH")
        self.assertEqual(anomalies[0]["item_type"], "asset")
        self.assertEqual(anomalies[0]["item_id"], asset.id)
        self.assertIn("IT Warehouse", anomalies[0]["message"])
        self.assertIn("HR Warehouse", anomalies[0]["message"])

    def test_asset_no_scan_history(self):
        """Asset with no scans should be HIGH severity"""
        asset = Asset(
            organisation_id=self.org_id,
            asset_code="CHAIR-001",
            name="Office Chair",
            type="Furniture",
            department_id=self.dept_it.id,
            assigned_department_id=self.dept_it.id,
            warehouse_id=self.wh_it.id,
            purchase_date=datetime.utcnow().date(),
            purchase_value=500.0,
            useful_life=10,
            current_value=500.0,
            status=AssetStatus.ASSIGNED.value,
        )
        db.session.add(asset)
        db.session.commit()

        # No scan created

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should be flagged as HIGH severity
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["severity"], "HIGH")
        self.assertIn("no scan history", anomalies[0]["message"].lower())

    def test_asset_stale_location(self):
        """Asset with old scan (30+ days) should adjust severity"""
        asset = Asset(
            organisation_id=self.org_id,
            asset_code="DESK-001",
            name="Office Desk",
            type="Furniture",
            department_id=self.dept_it.id,
            assigned_department_id=self.dept_it.id,
            warehouse_id=self.wh_it.id,
            purchase_date=datetime.utcnow().date(),
            purchase_value=800.0,
            useful_life=10,
            current_value=800.0,
            status=AssetStatus.ASSIGNED.value,
        )
        db.session.add(asset)
        db.session.flush()

        # Scan 45 days ago at wrong warehouse
        old_scan = ScanEvent(
            organisation_id=self.org_id,
            item_type="asset",
            item_id=asset.id,
            warehouse_id=self.wh_hr.id,
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow() - timedelta(days=45),
            user_id=self.user.id,
        )
        db.session.add(old_scan)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should still be HIGH (wrong warehouse) but message includes staleness
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["severity"], "HIGH")
        self.assertEqual(anomalies[0]["days_since_scan"], 45)
        self.assertIn("45 days ago", anomalies[0]["message"])

    def test_asset_disposed_skipped(self):
        """Disposed assets should be skipped"""
        asset = Asset(
            organisation_id=self.org_id,
            asset_code="DISPOSED-001",
            name="Old Equipment",
            type="Electronics",
            department_id=self.dept_it.id,
            warehouse_id=self.wh_hr.id,  # Wrong warehouse, but disposed
            purchase_date=datetime.utcnow().date(),
            purchase_value=100.0,
            useful_life=5,
            current_value=0.0,
            status=AssetStatus.DISPOSED.value,
        )
        db.session.add(asset)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should NOT be flagged (disposed items are skipped)
        self.assertEqual(len(anomalies), 0)

    def test_asset_assigned_to_user(self):
        """Asset assigned to user should use user's department for expected location"""
        # Create another user in HR
        hr_user = User(
            id=2,
            username="hruser",
            email="hr@test.com",
            organisation_id=self.org_id,
            role="staff",
            department_id=self.dept_hr.id,
        )
        hr_user.set_password("Password123!")
        db.session.add(hr_user)
        db.session.flush()

        asset = Asset(
            organisation_id=self.org_id,
            asset_code="PERSONAL-LAPTOP-001",
            name="Personal Laptop",
            type="Electronics",
            department_id=self.dept_it.id,  # Home is IT
            assigned_to_user_id=hr_user.id,  # Assigned to HR user
            warehouse_id=self.wh_hr.id,
            purchase_date=datetime.utcnow().date(),
            purchase_value=1000.0,
            useful_life=5,
            current_value=1000.0,
            status=AssetStatus.ASSIGNED.value,
        )
        db.session.add(asset)
        db.session.flush()

        # Scan at HR warehouse (where user's department is)
        scan = ScanEvent(
            organisation_id=self.org_id,
            item_type="asset",
            item_id=asset.id,
            warehouse_id=self.wh_hr.id,  # HR user's dept
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should NOT be flagged (correctly in user's dept warehouse)
        self.assertEqual(len(anomalies), 0)

    # =========================================================================
    # INVENTORY ITEM TESTS
    # =========================================================================

    def test_inventory_correct_location(self):
        """Inventory in correct warehouse should NOT be flagged"""
        inv = InventoryItem(
            organisation_id=self.org_id,
            name="Office Supplies",
            sku="INV-001",
            quantity=100,
            warehouse_id=self.wh_it.id,
            is_active=True,
            unit_price=10.0,
            reorder_level=20,
        )
        db.session.add(inv)
        db.session.flush()

        # Scan at correct warehouse
        scan = ScanEvent(
            organisation_id=self.org_id,
            item_type="inventory",
            item_id=inv.id,
            warehouse_id=self.wh_it.id,
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should NOT be flagged
        self.assertEqual(len(anomalies), 0)

    def test_inventory_wrong_warehouse(self):
        """Inventory in wrong warehouse should be HIGH severity"""
        inv = InventoryItem(
            organisation_id=self.org_id,
            name="Printer Paper",
            sku="INV-002",
            quantity=50,
            warehouse_id=self.wh_it.id,  # Expected in IT warehouse
            is_active=True,
            unit_price=5.0,
            reorder_level=10,
        )
        db.session.add(inv)
        db.session.flush()

        # Scan at wrong warehouse
        scan = ScanEvent(
            organisation_id=self.org_id,
            item_type="inventory",
            item_id=inv.id,
            warehouse_id=self.wh_finance.id,  # Actually in Finance!
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should be flagged as HIGH
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["severity"], "HIGH")
        self.assertEqual(anomalies[0]["item_type"], "inventory")

    def test_inventory_inactive_skipped(self):
        """Inactive inventory should be skipped"""
        inv = InventoryItem(
            organisation_id=self.org_id,
            name="Discontinued Item",
            sku="INV-003",
            quantity=0,
            warehouse_id=self.wh_finance.id,  # Wrong warehouse, but inactive
            is_active=False,
            unit_price=0.0,
            reorder_level=0,
        )
        db.session.add(inv)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should NOT be flagged
        self.assertEqual(len(anomalies), 0)

    # =========================================================================
    # ITEM INSTANCE TESTS
    # =========================================================================

    def test_item_instance_correct_location(self):
        """ItemInstance in correct location should NOT be flagged"""
        inv = InventoryItem(
            organisation_id=self.org_id,
            name="Laptop Unit",
            sku="UNIT-001",
            quantity=1,
            warehouse_id=self.wh_it.id,
            is_active=True,
            unit_price=1000.0,
            reorder_level=1,
        )
        db.session.add(inv)
        db.session.flush()

        instance = ItemInstance(
            item_id=inv.id,
            serial_number="ABC123",
            qr_code_data="QR-ABC123",
            warehouse_id=self.wh_it.id,
            status="in_stock",
        )
        db.session.add(instance)
        db.session.flush()

        # Scan at correct warehouse
        scan = ScanEvent(
            organisation_id=self.org_id,
            item_type="inventory_instance",
            item_id=instance.id,
            warehouse_id=self.wh_it.id,
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should NOT be flagged
        self.assertEqual(len(anomalies), 0)

    def test_item_instance_wrong_warehouse(self):
        """ItemInstance in wrong warehouse should be HIGH severity"""
        inv = InventoryItem(
            organisation_id=self.org_id,
            name="Laptop Unit",
            sku="UNIT-002",
            quantity=1,
            warehouse_id=self.wh_it.id,  # Expected in IT
            is_active=True,
            unit_price=1000.0,
            reorder_level=1,
        )
        db.session.add(inv)
        db.session.flush()

        instance = ItemInstance(
            item_id=inv.id,
            serial_number="XYZ789",
            qr_code_data="QR-XYZ789",
            warehouse_id=self.wh_it.id,
            status="in_stock",
        )
        db.session.add(instance)
        db.session.flush()

        # Scan at wrong warehouse
        scan = ScanEvent(
            organisation_id=self.org_id,
            item_type="inventory_instance",
            item_id=instance.id,
            warehouse_id=self.wh_finance.id,  # Wrong!
            action_type="TRANSFER",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should be flagged as HIGH
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["severity"], "HIGH")
        self.assertEqual(anomalies[0]["item_type"], "inventory_instance")

    def test_item_instance_shipped_skipped(self):
        """Shipped item instances should be skipped"""
        inv = InventoryItem(
            organisation_id=self.org_id,
            name="Shipped Unit",
            sku="UNIT-003",
            quantity=1,
            warehouse_id=self.wh_it.id,
            is_active=True,
            unit_price=500.0,
            reorder_level=1,
        )
        db.session.add(inv)
        db.session.flush()

        instance = ItemInstance(
            item_id=inv.id,
            serial_number="SHIP001",
            qr_code_data="QR-SHIP001",
            warehouse_id=self.wh_finance.id,  # Wrong warehouse, but shipped
            status="shipped",
        )
        db.session.add(instance)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should NOT be flagged
        self.assertEqual(len(anomalies), 0)

    # =========================================================================
    # SORTING AND PAGINATION TESTS
    # =========================================================================

    def test_sorting_by_severity(self):
        """Anomalies should be sorted by severity (HIGH first)"""
        # Create multiple misplaced items with different severities

        # HIGH: Wrong warehouse
        asset1 = Asset(
            organisation_id=self.org_id,
            asset_code="HIGH-001",
            name="High Priority Item",
            type="Electronics",
            department_id=self.dept_it.id,
            assigned_department_id=self.dept_it.id,
            warehouse_id=self.wh_it.id,
            purchase_date=datetime.utcnow().date(),
            purchase_value=1000.0,
            useful_life=5,
            current_value=1000.0,
            status=AssetStatus.ASSIGNED.value,
        )
        db.session.add(asset1)
        db.session.flush()

        scan1 = ScanEvent(
            organisation_id=self.org_id,
            item_type="asset",
            item_id=asset1.id,
            warehouse_id=self.wh_finance.id,  # Wrong warehouse
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan1)

        # MEDIUM: Same warehouse, different bin
        asset2 = Asset(
            organisation_id=self.org_id,
            asset_code="MEDIUM-001",
            name="Medium Priority Item",
            type="Furniture",
            department_id=self.dept_hr.id,
            assigned_department_id=self.dept_hr.id,
            warehouse_id=self.wh_hr.id,
            bin_id=10,
            purchase_date=datetime.utcnow().date(),
            purchase_value=500.0,
            useful_life=10,
            current_value=500.0,
            status=AssetStatus.ASSIGNED.value,
        )
        db.session.add(asset2)
        db.session.flush()

        scan2 = ScanEvent(
            organisation_id=self.org_id,
            item_type="asset",
            item_id=asset2.id,
            warehouse_id=self.wh_hr.id,  # Right warehouse
            bin_id=20,  # Wrong bin
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan2)
        db.session.commit()

        # Run detection
        anomalies = AnomalyService.predict_misplaced_items(self.org_id)

        # Should be sorted with HIGH first
        self.assertEqual(len(anomalies), 2)
        self.assertEqual(anomalies[0]["severity"], "HIGH")
        self.assertEqual(anomalies[1]["severity"], "MEDIUM")

    def test_limit_parameter(self):
        """Limit parameter should truncate results"""
        # Create 5 misplaced assets
        for i in range(5):
            asset = Asset(
                organisation_id=self.org_id,
                asset_code=f"ASSET-{i}",
                name=f"Asset {i}",
                type="Electronics",
                department_id=self.dept_it.id,
                assigned_department_id=self.dept_it.id,
                warehouse_id=self.wh_it.id,
                purchase_date=datetime.utcnow().date(),
                purchase_value=1000.0,
                useful_life=5,
                current_value=1000.0,
                status=AssetStatus.ASSIGNED.value,
            )
            db.session.add(asset)
            db.session.flush()

            scan = ScanEvent(
                organisation_id=self.org_id,
                item_type="asset",
                item_id=asset.id,
                warehouse_id=self.wh_finance.id,  # Wrong warehouse
                action_type="CHECK_IN",
                validation_status="verified",
                timestamp=datetime.utcnow() - timedelta(hours=i),
                user_id=self.user.id,
            )
            db.session.add(scan)

        db.session.commit()

        # Run detection with limit=3
        anomalies = AnomalyService.predict_misplaced_items(self.org_id, limit=3)

        # Should return only 3
        self.assertEqual(len(anomalies), 3)

    # =========================================================================
    # MULTI-TENANT ISOLATION TEST
    # =========================================================================

    def test_multi_tenant_isolation(self):
        """Results should only include items from requested org"""
        # Create second org
        org2 = Organization(name="Test Org 2", code="ORG2")
        db.session.add(org2)
        db.session.flush()

        # Create asset in org1
        asset1 = Asset(
            organisation_id=self.org_id,
            asset_code="ORG1-ASSET",
            name="Org1 Asset",
            type="Electronics",
            department_id=self.dept_it.id,
            assigned_department_id=self.dept_it.id,
            warehouse_id=self.wh_it.id,
            purchase_date=datetime.utcnow().date(),
            purchase_value=1000.0,
            useful_life=5,
            current_value=1000.0,
            status=AssetStatus.ASSIGNED.value,
        )
        db.session.add(asset1)
        db.session.commit()

        # Scan asset1 at wrong warehouse
        scan1 = ScanEvent(
            organisation_id=self.org_id,
            item_type="asset",
            item_id=asset1.id,
            warehouse_id=self.wh_finance.id,
            action_type="CHECK_IN",
            validation_status="verified",
            timestamp=datetime.utcnow(),
            user_id=self.user.id,
        )
        db.session.add(scan1)
        db.session.commit()

        # Query for org1
        anomalies_org1 = AnomalyService.predict_misplaced_items(self.org_id)

        # Query for org2 (empty)
        anomalies_org2 = AnomalyService.predict_misplaced_items(org2.id)

        # Should only find misplaced items in org1
        self.assertEqual(len(anomalies_org1), 1)
        self.assertEqual(len(anomalies_org2), 0)


if __name__ == "__main__":
    unittest.main()