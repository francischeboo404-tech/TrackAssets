#!/usr/bin/env python
"""Database seeding script for test data"""

import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta
from app import create_app, db
from app.models.organization import Organization, Department
from app.models.user import User
from app.models.asset import Asset, AssetStatus, AssetCondition
from app.models.inventory import InventoryItem, StockMovement, StockMovementType

def seed_database():
    """Populate database with test data"""
    app = create_app('development')
    
    with app.app_context():
        # Clear existing data
        # db.drop_all()
        # db.create_all()
        
        print("Creating organizations...")
        org1 = Organization(
            name='Tech Corp',
            code='TECHCORP',
            description='Technology corporation'
        )
        org2 = Organization(
            name='Manufacturing Inc',
            code='MFGINC',
            description='Manufacturing company'
        )
        db.session.add_all([org1, org2])
        db.session.commit()
        
        print("Creating departments...")
        dept_it = Department(
            organisation_id=org1.id,
            name='Information Technology',
            code='IT',
            description='IT Department'
        )
        dept_hr = Department(
            organisation_id=org1.id,
            name='Human Resources',
            code='HR',
            description='HR Department'
        )
        dept_ops = Department(
            organisation_id=org2.id,
            name='Operations',
            code='OPS',
            description='Operations Department'
        )
        db.session.add_all([dept_it, dept_hr, dept_ops])
        db.session.commit()
        
        print("Creating users...")
        admin = User(
            organisation_id=org1.id,
            username='admin',
            email='admin@techcorp.com',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        admin.set_password('Admin123!')
        
        staff = User(
            organisation_id=org1.id,
            username='staff1',
            email='staff1@techcorp.com',
            first_name='Staff',
            last_name='One',
            role='staff'
        )
        staff.set_password('Staff123!')
        
        dept_head = User(
            organisation_id=org1.id,
            username='depthead',
            email='depthead@techcorp.com',
            first_name='Dept',
            last_name='Head',
            role='dept_head'
        )
        dept_head.set_password('Head123!')
        dept_it.head_id = dept_head.id
        
        store_mgr = User(
            organisation_id=org2.id,
            username='storemmgr',
            email='storemgr@mfginc.com',
            first_name='Store',
            last_name='Manager',
            role='store_manager'
        )
        store_mgr.set_password('Store123!')
        
        db.session.add_all([admin, staff, dept_head, store_mgr])
        db.session.commit()

        # Create global superadmin (can manage roles and system-wide settings)
        superadmin = User(
            organisation_id=org1.id,
            username='Frank',
            email='frankadmin@trackit.com',
            first_name='Frank',
            last_name='Administrator',
            role='superadmin'
        )
        superadmin.set_password('P@55w0rd123!_')
        db.session.add(superadmin)
        db.session.commit()
        
        print("Creating assets...")
        today = datetime.utcnow().date()
        purchase_date = today - timedelta(days=365)
        
        asset1 = Asset(
            organisation_id=org1.id,
            asset_code='TECH-001',
            name='Dell Laptop',
            type='IT',
            serial_number='DELL-SN-12345',
            department_id=dept_it.id,
            assigned_to='John Doe',
            status=AssetStatus.IN_USE.value,
            condition=AssetCondition.GOOD.value,
            location='Office A',
            purchase_date=purchase_date,
            purchase_value=80000.00,
            useful_life=5,
            current_value=64000.00
        )
        
        asset2 = Asset(
            organisation_id=org1.id,
            asset_code='TECH-002',
            name='HP Desktop',
            type='IT',
            serial_number='HP-SN-67890',
            department_id=dept_it.id,
            assigned_to='Jane Smith',
            status=AssetStatus.REQUESTED.value,
            condition=AssetCondition.NEW.value,
            location='Office B',
            purchase_date=today,
            purchase_value=50000.00,
            useful_life=5,
            current_value=50000.00
        )
        
        asset1.update_current_value()
        
        db.session.add_all([asset1, asset2])
        db.session.commit()
        
        print("Creating inventory items...")
        inv1 = InventoryItem(
            organisation_id=org1.id,
            name='Office Paper A4',
            sku='PAPER-A4',
            description='White paper 80gsm',
            quantity=500,
            reorder_level=100,
            unit_price=2500.00,
            unit='box'
        )
        
        inv2 = InventoryItem(
            organisation_id=org1.id,
            name='Printer Cartridges',
            sku='INK-BLK',
            description='Black ink cartridges',
            quantity=5,
            reorder_level=10,
            unit_price=3500.00,
            unit='piece'
        )
        
        db.session.add_all([inv1, inv2])
        db.session.commit()
        
        print("Creating stock movements...")
        mov1 = StockMovement(
            item_id=inv1.id,
            type=StockMovementType.IN.value,
            quantity=500,
            reference='PO-2024-001',
            notes='Initial stock',
            date=datetime.utcnow() - timedelta(days=30)
        )
        
        mov2 = StockMovement(
            item_id=inv2.id,
            type=StockMovementType.IN.value,
            quantity=10,
            reference='PO-2024-002',
            notes='Initial stock',
            date=datetime.utcnow() - timedelta(days=20)
        )
        
        mov3 = StockMovement(
            item_id=inv2.id,
            type=StockMovementType.OUT.value,
            quantity=5,
            reference='REQ-2024-001',
            notes='Used in printing',
            date=datetime.utcnow() - timedelta(days=10)
        )
        
        db.session.add_all([mov1, mov2, mov3])
        db.session.commit()
        
        print("Evaluating stock health...")
        from app.services.restock_service import RestockService
        RestockService.evaluate_stock_health(inv1.id)
        RestockService.evaluate_stock_health(inv2.id)
        db.session.commit()
        
        print("\n[OK] Database seeded successfully!")
        print(f"  Organizations: 2")
        print(f"  Departments: 3")
        print(f"  Users: 5")
        print(f"  Assets: 2")
        print(f"  Inventory Items: 2")
        print(f"  Stock Movements: 3")
        print("Test credentials:")
        print("  Admin: admin@techcorp.com / Admin123!")
        print("  Staff: staff1@techcorp.com / Staff123!")
        print("  Dept Head: depthead@techcorp.com / Head123!")
        print("  Store Mgr: storemgr@techcorp.com / Store123!")
        print("  Superadmin: frankadmin@trackit.com / P@55w0rd123!_")

if __name__ == '__main__':
    seed_database()
