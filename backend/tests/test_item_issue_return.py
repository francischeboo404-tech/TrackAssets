import sys
import os
import pytest
from datetime import datetime
from sqlalchemy import inspect, text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import InventoryItem, WarehouseStock, Organization, User, Warehouse, Department, Employee, ItemIssue, ItemReturn, StockCard, SuppliesLedgerCard
from app.models.asset import Asset
from app.services.stock_service import StockService
from app.movement_schema import ensure_movement_schema_columns


def test_movement_schema_auto_heals_missing_columns():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.session.execute(text("""
            CREATE TABLE item_issues (
                id INTEGER PRIMARY KEY,
                organisation_id INTEGER NOT NULL,
                item_id INTEGER,
                from_warehouse_id INTEGER,
                to_department_id INTEGER,
                employee_id INTEGER,
                quantity INTEGER NOT NULL,
                reference VARCHAR(100),
                notes TEXT,
                issued_by INTEGER,
                issued_date DATETIME,
                is_active BOOLEAN,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        db.session.execute(text("""
            CREATE TABLE item_returns (
                id INTEGER PRIMARY KEY,
                organisation_id INTEGER NOT NULL,
                item_id INTEGER,
                from_department_id INTEGER,
                to_warehouse_id INTEGER,
                employee_id INTEGER,
                quantity INTEGER NOT NULL,
                condition VARCHAR(50),
                remarks TEXT,
                reference VARCHAR(100),
                returned_by INTEGER,
                return_date DATETIME,
                is_active BOOLEAN,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        db.session.commit()

        ensure_movement_schema_columns(app)

        inspector = inspect(db.engine)
        issue_columns = {column['name'] for column in inspector.get_columns('item_issues')}
        return_columns = {column['name'] for column in inspector.get_columns('item_returns')}
        assert 'asset_id' in issue_columns
        assert 'item_type' in issue_columns
        assert 'asset_id' in return_columns
        assert 'item_type' in return_columns


def test_issue_and_return_flow():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Setup org, admin user
        dummy_org = Organization(name='Dummy Org', code='DUMMY01')
        org = Organization(name='Flow Org', code='FLOW01')
        db.session.add_all([dummy_org, org])
        db.session.commit()

        admin = User(username='adminflow', email='adminflow@test.com', role='admin', organisation_id=org.id)
        admin.set_password('Password1!')
        db.session.add(admin)
        db.session.commit()
        assert admin.id != org.id

        # Create warehouse and department and employee
        wh = Warehouse(name='Main WH', code='MWH', organisation_id=org.id)
        db.session.add(wh)
        db.session.commit()

        dept = Department(organisation_id=org.id, warehouse_id=wh.id, name='IT', code='IT')
        db.session.add(dept)
        db.session.commit()

        emp = Employee(organisation_id=org.id, department_id=dept.id, name='Alice', code='EMP001', email='alice@test.com')
        db.session.add(emp)
        db.session.commit()

        # Create item and seed stock
        item = InventoryItem(organisation_id=org.id, name='Screwdriver', sku='SD-001', quantity=0, reorder_level=1, unit_price=5.0, unit='pcs')
        db.session.add(item)
        db.session.commit()

        StockService(session=db.session).increase_stock(
            item_id=item.id,
            org_id=org.id,
            quantity=10,
            warehouse_id=wh.id,
            reference='INIT',
            notes='Initial stock',
        )
        db.session.commit()

        # Login to get token
        client = app.test_client()
        login_resp = client.post('/api/auth/login', json={'email': admin.email, 'password': 'Password1!'})
        assert login_resp.status_code == 200
        access_token = login_resp.get_json()['access_token']

        headers = {'Authorization': f'Bearer {access_token}'}

        # Issue item
        issue_payload = {
            'item_id': item.id,
            'from_warehouse_id': wh.id,
            'to_department_id': dept.id,
            'employee_id': emp.id,
            'quantity': 3,
            'reference': 'ISSUE-TEST',
            'notes': 'Issued for task'
        }
        issue_resp = client.post('/api/movements/issue', json=issue_payload, headers=headers)
        assert issue_resp.status_code == 201
        issue_data = issue_resp.get_json()
        assert 'issue_id' in issue_data

        issued_record = ItemIssue.query.filter_by(id=issue_data['issue_id']).first()
        assert issued_record is not None
        assert issued_record.issued_by == admin.id

        # Check stock decreased
        stock_row = WarehouseStock.query.filter_by(item_id=item.id, warehouse_id=wh.id).first()
        assert stock_row.quantity_on_hand == 7

        # Verify stock card and ledger reflect the issue
        stock_card_issue = StockCard.query.filter_by(organization_id=org.id, item_id=item.id, location_id=wh.id).first()
        ledger_issue = SuppliesLedgerCard.query.filter_by(organization_id=org.id, item_id=item.id, location_id=wh.id).first()
        assert stock_card_issue is not None
        assert ledger_issue is not None
        assert stock_card_issue.quantity_on_hand == 7
        assert int(ledger_issue.quantity_on_hand) == 7

        # Return item
        return_payload = {
            'item_id': item.id,
            'from_department_id': dept.id,
            'to_warehouse_id': wh.id,
            'employee_id': emp.id,
            'quantity': 2,
            'condition': 'good',
            'remarks': 'Returned after use',
            'reference': 'RETURN-TEST'
        }
        return_resp = client.post('/api/movements/return', json=return_payload, headers=headers)
        assert return_resp.status_code == 201
        return_data = return_resp.get_json()
        assert 'return_id' in return_data

        # Check stock increased
        stock_row = WarehouseStock.query.filter_by(item_id=item.id, warehouse_id=wh.id).first()
        assert stock_row.quantity_on_hand == 9

        # Verify stock card and ledger reflect the return
        stock_card_return = StockCard.query.filter_by(organization_id=org.id, item_id=item.id, location_id=wh.id).first()
        ledger_return = SuppliesLedgerCard.query.filter_by(organization_id=org.id, item_id=item.id, location_id=wh.id).first()
        assert stock_card_return is not None
        assert ledger_return is not None
        assert stock_card_return.quantity_on_hand == 9
        assert int(ledger_return.quantity_on_hand) == 9

        # Check records exist
        assert ItemIssue.query.filter_by(id=issue_data['issue_id']).first() is not None
        assert ItemReturn.query.filter_by(id=return_data['return_id']).first() is not None

        history_resp = client.get('/api/movements/history', headers=headers)
        assert history_resp.status_code == 200
        history_data = history_resp.get_json()
        assert 'issues' in history_data
        assert 'returns' in history_data
        assert len(history_data['issues']) >= 1
        assert len(history_data['returns']) >= 1


def test_asset_issue_and_return_flow():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name='Asset Flow Org', code='ASSETFLOW01')
        db.session.add(org)
        db.session.commit()

        admin = User(username='assetadmin', email='assetadmin@test.com', role='admin', organisation_id=org.id)
        admin.set_password('Password1!')
        db.session.add(admin)
        db.session.commit()

        warehouse = Warehouse(name='Asset WH', code='AWH', organisation_id=org.id)
        db.session.add(warehouse)
        db.session.commit()

        department = Department(organisation_id=org.id, warehouse_id=warehouse.id, name='Finance', code='FIN')
        db.session.add(department)
        db.session.commit()

        employee = Employee(organisation_id=org.id, department_id=department.id, name='Bob', code='EMP002', email='bob@test.com')
        db.session.add(employee)
        db.session.commit()

        asset = Asset(
            organisation_id=org.id,
            asset_code='AST-1001',
            name='Laptop',
            type='IT',
            department_id=department.id,
            purchase_date=datetime.utcnow().date(),
            purchase_value=1000.00,
            useful_life=36,
            current_value=1000.00,
            status='available',
            condition='good',
            warehouse_id=warehouse.id,
        )
        db.session.add(asset)
        db.session.commit()

        client = app.test_client()
        login_resp = client.post('/api/auth/login', json={'email': admin.email, 'password': 'Password1!'})
        assert login_resp.status_code == 200
        headers = {'Authorization': f"Bearer {login_resp.get_json()['access_token']}"}

        issue_resp = client.post('/api/movements/issue', json={
            'item_type': 'asset',
            'asset_id': asset.id,
            'from_warehouse_id': warehouse.id,
            'to_department_id': department.id,
            'employee_id': employee.id,
            'quantity': 1,
            'reference': 'AST-ISSUE',
            'notes': 'Laptop issued'
        }, headers=headers)
        assert issue_resp.status_code == 201
        issue_data = issue_resp.get_json()
        issue_record = ItemIssue.query.filter_by(id=issue_data['issue_id']).first()
        assert issue_record is not None
        assert issue_record.asset_id == asset.id
        assert issue_record.item_type == 'asset'

        return_resp = client.post('/api/movements/return', json={
            'item_type': 'asset',
            'asset_id': asset.id,
            'from_department_id': department.id,
            'to_warehouse_id': warehouse.id,
            'employee_id': employee.id,
            'quantity': 1,
            'condition': 'good',
            'remarks': 'Returned after use',
            'reference': 'AST-RETURN'
        }, headers=headers)
        assert return_resp.status_code == 201
        return_data = return_resp.get_json()
        return_record = ItemReturn.query.filter_by(id=return_data['return_id']).first()
        assert return_record is not None
        assert return_record.asset_id == asset.id
        assert return_record.item_type == 'asset'
