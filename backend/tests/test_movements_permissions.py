import os
import sys
import pytest
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import (
    InventoryItem,
    WarehouseStock,
    Organization,
    User,
    Warehouse,
    Department,
    Employee,
    ItemIssue,
)
from app.services.stock_service import StockService


def test_movements_list_permissions_and_filtering():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()

        org = Organization(name="Perm Org", code="PERM01")
        db.session.add(org)
        db.session.commit()

        # Create users: admin, staff (alice), dept_head (bob)
        admin = User(username='adminperm', email='adminperm@test.com', role='admin', organisation_id=org.id)
        admin.set_password('Password1!')
        alice = User(username='alice', email='alice@test.com', role='staff', organisation_id=org.id)
        alice.set_password('Password1!')
        bob = User(username='bob', email='bob@test.com', role='dept_head', organisation_id=org.id)
        bob.set_password('Password1!')
        db.session.add_all([admin, alice, bob])
        db.session.commit()

        # Create warehouse and department, make bob the head
        wh = Warehouse(name='Main WH', code='MWH-P', organisation_id=org.id)
        db.session.add(wh)
        db.session.commit()

        dept = Department(organisation_id=org.id, warehouse_id=wh.id, name='IT-P', code='ITP', head_id=bob.id)
        db.session.add(dept)
        db.session.commit()

        # Create employee
        emp = Employee(organisation_id=org.id, department_id=dept.id, name='Charlie', code='EMP900', email='charlie@test.com')
        db.session.add(emp)
        db.session.commit()

        # Create item and seed stock
        item = InventoryItem(organisation_id=org.id, name='Drill', sku='DR-900', quantity=0, reorder_level=1, unit_price=10.0, unit='pcs')
        db.session.add(item)
        db.session.commit()

        StockService(session=db.session).increase_stock(
            item_id=item.id,
            org_id=org.id,
            quantity=5,
            warehouse_id=wh.id,
            reference='INIT',
            notes='Initial'
        )
        db.session.commit()

        # Create issues: one issued by alice to dept, one issued by admin to another dept
        issue1 = ItemIssue(organisation_id=org.id, item_id=item.id, from_warehouse_id=wh.id, to_department_id=dept.id, employee_id=emp.id, quantity=1, issued_by=alice.id)
        db.session.add(issue1)
        db.session.commit()

        # Create second department and issue by admin
        dept2 = Department(organisation_id=org.id, warehouse_id=wh.id, name='Ops-P', code='OPS', head_id=None)
        db.session.add(dept2)
        db.session.commit()
        issue2 = ItemIssue(organisation_id=org.id, item_id=item.id, from_warehouse_id=wh.id, to_department_id=dept2.id, employee_id=emp.id, quantity=1, issued_by=admin.id)
        db.session.add(issue2)
        db.session.commit()

        client = app.test_client()

        # Login alice and fetch issues
        login_resp = client.post('/api/auth/login', json={'email': alice.email, 'password': 'Password1!'})
        assert login_resp.status_code == 200
        token = login_resp.get_json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        resp = client.get('/api/movements/issues', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        # Alice should only see the issue she created
        ids = [i['id'] for i in data['issues']]
        assert issue1.id in ids
        assert issue2.id not in ids

        # Login bob (dept_head) and fetch issues
        login_resp = client.post('/api/auth/login', json={'email': bob.email, 'password': 'Password1!'})
        assert login_resp.status_code == 200
        token = login_resp.get_json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        resp = client.get('/api/movements/issues', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        ids = [i['id'] for i in data['issues']]
        # Bob is head of dept, should see issue1 destined to his department
        assert issue1.id in ids
        # But should not necessarily see issue2 (different dept)
        assert issue2.id not in ids

        # Admin sees both
        login_resp = client.post('/api/auth/login', json={'email': admin.email, 'password': 'Password1!'})
        assert login_resp.status_code == 200
        token = login_resp.get_json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        resp = client.get('/api/movements/issues', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        ids = [i['id'] for i in data['issues']]
        assert issue1.id in ids and issue2.id in ids
