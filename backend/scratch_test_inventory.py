
import sys
import os
from flask import Flask
from app import create_app, db
from app.services.inventory_service import InventoryService
from app.repositories.inventory_repository import InventoryRepository
from app.errors import APIError

def test_inventory_creation():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Create an org first if none exists
        from app.models.organization import Organization
        org = Organization.query.first()
        if not org:
            org = Organization(name="Test Org", code="TESTORG")
            db.session.add(org)
            db.session.commit()
        
        service = InventoryService()
        
        # Test valid creation
        data = {
            "name": "Test Item",
            "sku": "TEST-SKU-1",
            "unit_price": 10.50,
            "unit": "pcs",
            "reorder_level": 5
        }
        
        try:
            item = service.create_item(org.id, data)
            print(f"Success: Created item {item.name} with SKU {item.sku}")
        except Exception as e:
            print(f"Failure: {e}")
            if hasattr(e, 'payload'):
                print(f"Payload: {e.payload}")

if __name__ == "__main__":
    test_inventory_creation()
