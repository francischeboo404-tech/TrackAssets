import unittest

from app import create_app, db
from app.models.location_topology import Warehouse, WarehouseBin, WarehouseRack, WarehouseShelf, WarehouseZone
from app.models.organization import Organization
from app.models.user import User


class TestStorageFacilitiesCRUD(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

        self.org = Organization(id=1, name="Storage Org", code="STO")
        db.session.add(self.org)
        self.admin = User(
            organisation_id=1,
            username="warehouse_admin",
            email="warehouse_admin@test.com",
            role="admin",
        )
        self.admin.set_password("Password1!")
        db.session.add(self.admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, user):
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token

            return create_access_token(identity=str(user.id))

    def test_warehouse_listing_returns_summary_metrics_and_address(self):
        warehouse = Warehouse(
            organisation_id=self.org.id,
            name="Central Hub",
            code="CH-01",
            address="123 Industrial Road",
        )
        db.session.add(warehouse)
        db.session.flush()

        zone = WarehouseZone(warehouse_id=warehouse.id, name="Default Zone", code="Z1")
        db.session.add(zone)
        db.session.flush()

        rack = WarehouseRack(zone_id=zone.id, code="R1")
        db.session.add(rack)
        db.session.flush()

        shelf = WarehouseShelf(rack_id=rack.id, code="S1")
        db.session.add(shelf)
        db.session.flush()

        bin_a = WarehouseBin(shelf_id=shelf.id, code="BIN-001", status="occupied")
        bin_b = WarehouseBin(shelf_id=shelf.id, code="BIN-002", status="available")
        db.session.add_all([bin_a, bin_b])
        db.session.commit()

        token = self._login(self.admin)
        response = self.client.get(
            "/api/warehouses",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # API returns a standardized envelope with 'data'
        self.assertTrue(isinstance(payload, dict))
        data = payload.get("data", [])
        self.assertTrue(isinstance(data, list))
        self.assertEqual(data[0]["name"], "Central Hub")
        self.assertEqual(data[0]["address"], "123 Industrial Road")
        self.assertEqual(data[0]["total_bins"], 2)
        self.assertEqual(data[0]["occupied_bins"], 1)
        self.assertEqual(data[0]["empty_bins"], 1)
        self.assertEqual(data[0]["utilization_percentage"], 50.0)

    def test_admin_can_update_and_delete_storage_bins(self):
        warehouse = Warehouse(
            organisation_id=self.org.id,
            name="North Hub",
            code="NH-01",
            address="10 North Avenue",
        )
        db.session.add(warehouse)
        db.session.flush()

        zone = WarehouseZone(warehouse_id=warehouse.id, name="Default Zone", code="Z1")
        db.session.add(zone)
        db.session.flush()

        rack = WarehouseRack(zone_id=zone.id, code="R1")
        db.session.add(rack)
        db.session.flush()

        shelf = WarehouseShelf(rack_id=rack.id, code="S1")
        db.session.add(shelf)
        db.session.flush()

        bin_item = WarehouseBin(shelf_id=shelf.id, code="BIN-100", description="Initial")
        db.session.add(bin_item)
        db.session.commit()

        token = self._login(self.admin)
        update_response = self.client.put(
            f"/api/warehouses/{warehouse.id}/bins/{bin_item.id}",
            json={"code": "BIN-200", "description": "Updated", "status": "occupied"},
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(update_response.status_code, 200)
        db.session.refresh(bin_item)
        self.assertEqual(bin_item.code, "BIN-200")
        self.assertEqual(bin_item.description, "Updated")
        self.assertEqual(bin_item.status, "occupied")

        delete_response = self.client.delete(
            f"/api/warehouses/{warehouse.id}/bins/{bin_item.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(delete_response.status_code, 200)
        self.assertIsNone(db.session.get(WarehouseBin, bin_item.id))


if __name__ == "__main__":
    unittest.main()
