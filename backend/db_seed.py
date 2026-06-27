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
        
        print("Creating organizations (skip existing)...")
        # Upsert organizations by `code` to avoid duplicate key errors
        org1 = Organization.query.filter_by(code='TECHCORP').first()
        if not org1:
            org1 = Organization(
                name='Tech Corp',
                code='TECHCORP',
                description='Technology corporation'
            )
            db.session.add(org1)
        else:
            print("  - TECHCORP exists, using existing record")

        org2 = Organization.query.filter_by(code='MFGINC').first()
        if not org2:
            org2 = Organization(
                name='Manufacturing Inc',
                code='MFGINC',
                description='Manufacturing company'
            )
            db.session.add(org2)
        else:
            print("  - MFGINC exists, using existing record")

        db.session.commit()
        
        print("Creating departments (skip existing)...")
        def get_or_create_dept(org_id, code, name, description):
            d = Department.query.filter_by(organisation_id=org_id, code=code).first()
            if d:
                return d
            d = Department(organisation_id=org_id, name=name, code=code, description=description)
            db.session.add(d)
            db.session.commit()
            return d

        dept_it = get_or_create_dept(org1.id, 'IT', 'Information Technology', 'IT Department')
        dept_hr = get_or_create_dept(org1.id, 'HR', 'Human Resources', 'HR Department')
        dept_ops = get_or_create_dept(org2.id, 'OPS', 'Operations', 'Operations Department')
        
        print("Creating users (skip existing)...")
        def get_or_create_user(org_id, username, email, first_name, last_name, role, password):
            u = User.query.filter_by(email=email).first()
            if u:
                return u
            u = User(organisation_id=org_id, username=username, email=email, first_name=first_name, last_name=last_name, role=role)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            return u

        admin = get_or_create_user(org1.id, 'admin', 'admin@techcorp.com', 'Admin', 'User', 'admin', 'Admin123!')
        staff = get_or_create_user(org1.id, 'staff1', 'staff1@techcorp.com', 'Staff', 'One', 'staff', 'Staff123!')
        dept_head = get_or_create_user(org1.id, 'depthead', 'depthead@techcorp.com', 'Dept', 'Head', 'dept_head', 'Head123!')
        store_mgr = get_or_create_user(org2.id, 'storemmgr', 'storemgr@mfginc.com', 'Store', 'Manager', 'store_manager', 'Store123!')

        # Ensure department head relationship is set
        if dept_it.head_id != dept_head.id:
            dept_it.head_id = dept_head.id
            db.session.add(dept_it)
            db.session.commit()

        # Create global superadmin (can manage roles and system-wide settings)
        superadmin = User.query.filter_by(organisation_id=org1.id, email='frankadmin@trackit.com').first()
        if not superadmin:
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
        else:
            print("  - superadmin exists, using existing record")
        
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
            status=AssetStatus.ASSIGNED.value,
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
            status=AssetStatus.AVAILABLE.value,
            condition=AssetCondition.NEW.value,
            location='Office B',
            purchase_date=today,
            purchase_value=50000.00,
            useful_life=5,
            current_value=50000.00
        )
        
        asset1.update_current_value()
        
        try:
            db.session.add_all([asset1, asset2])
            db.session.commit()
        except Exception as e:
            # Some environments may have an older schema; log and continue
            print("  - Skipping asset creation due to schema mismatch:", str(e))
            db.session.rollback()
        
        print("Creating inventory items (skip existing)...")
        def get_or_create_item(org_id, sku, name, description, quantity, reorder_level, unit_price, unit):
            it = InventoryItem.query.filter_by(organisation_id=org_id, sku=sku).first()
            if it:
                return it
            it = InventoryItem(
                organisation_id=org_id,
                name=name,
                sku=sku,
                description=description,
                quantity=quantity,
                reorder_level=reorder_level,
                unit_price=unit_price,
                unit=unit,
            )
            db.session.add(it)
            db.session.commit()
            return it

        inv1 = get_or_create_item(org1.id, 'PAPER-A4', 'Office Paper A4', 'White paper 80gsm', 500, 100, 2500.00, 'box')
        inv2 = get_or_create_item(org1.id, 'INK-BLK', 'Printer Cartridges', 'Black ink cartridges', 5, 10, 3500.00, 'piece')
        
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
