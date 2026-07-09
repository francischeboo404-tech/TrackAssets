"""Quick script to verify /api/tracking/scan endpoint with different QR formats.
Run with: python backend/scripts/verify_scan_endpoint.py
"""
import sys, os
from pathlib import Path

# Ensure backend package dir is on sys.path so `import app` works when run standalone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, db
from flask import json
from app.services.qr_service import QRService
from app.models import Asset, Warehouse
from app.models.organization import Organization, Department
from app.models.user import User

app = create_app('testing')

with app.app_context():
    db.create_all()

    # Setup minimal org, dept, user
    org = Organization(id=99, name='VTest', code='VTEST')
    db.session.add(org)
    db.session.commit()

    dept = Department(id=99, name='Ops', code='OPS', organisation_id=org.id)
    db.session.add(dept)
    db.session.commit()

    user = User(id=99, username='vtuser', email='vt@example.com', organisation_id=org.id, role='staff')
    user.set_password('Password123!')
    db.session.add(user)
    db.session.commit()

    wh = Warehouse(organisation_id=org.id, name='VWH', code='VWH')
    db.session.add(wh)
    db.session.commit()

    # Create asset
    import datetime as _dt

    asset = Asset(
        organisation_id=org.id,
        asset_code='VT-001',
        name='VT Asset',
        type='Electronics',
        department_id=dept.id,
        purchase_date=_dt.date(2020,1,1),
        purchase_value=100,
        useful_life=1,
        current_value=100,
        status='approved',
    )
    db.session.add(asset)
    db.session.commit()

    # Generate QR forms
    signed = QRService.ensure_asset_qr(asset)
    payload = QRService.get_qr_payload(org.id, 'asset', asset.id)
    legacy = payload.get('legacy_token')

    client = app.test_client()

    # Build an access token for the created user so jwt_required endpoints accept our requests
    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=str(user.id))
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}

    tests = [
        ('signed_url', signed),
        ('legacy_token', legacy),
        ('raw_asset_code', 'VT-001'),
    ]

    for name, qr in tests:
        body = {
            'qr_data': qr,
            'action_type': 'CHECK_IN',
            'warehouse_id': wh.id,
        }
        resp = client.post('/api/tracking/scan', data=json.dumps(body), headers=headers)
        print(name, 'status', resp.status_code, resp.get_json())

    # list SystemEvent entries
    from app.models.event import SystemEvent
    events = SystemEvent.query.all()
    print('SystemEvent count:', len(events))
    for e in events:
        print(e.event_type, e.data)

    db.session.remove()
    db.drop_all()
