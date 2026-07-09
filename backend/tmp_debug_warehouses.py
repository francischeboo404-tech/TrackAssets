from app import create_app, db
from app.models.location_topology import Warehouse, WarehouseZone, WarehouseRack, WarehouseShelf, WarehouseBin
from app.models.organization import Organization
from app.models.user import User

app = create_app('testing')
with app.app_context():
    db.drop_all()
    db.create_all()
    org = Organization(id=1, name='Storage Org', code='STO')
    db.session.add(org)
    admin = User(organisation_id=1, username='warehouse_admin', email='warehouse_admin@test.com', role='admin')
    admin.set_password('Password1!')
    db.session.add(admin)
    db.session.commit()

    warehouse = Warehouse(organisation_id=org.id, name='Central Hub', code='CH-01', address='123 Industrial Road')
    db.session.add(warehouse)
    db.session.flush()
    zone = WarehouseZone(warehouse_id=warehouse.id, name='Default Zone', code='Z1')
    db.session.add(zone); db.session.flush()
    rack = WarehouseRack(zone_id=zone.id, code='R1')
    db.session.add(rack); db.session.flush()
    shelf = WarehouseShelf(rack_id=rack.id, code='S1')
    db.session.add(shelf); db.session.flush()
    b1 = WarehouseBin(shelf_id=shelf.id, code='BIN-001', status='occupied')
    b2 = WarehouseBin(shelf_id=shelf.id, code='BIN-002', status='available')
    db.session.add_all([b1,b2]); db.session.commit()

    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=str(admin.id))

    client = app.test_client()
    resp = client.get('/api/warehouses', headers={'Authorization': f'Bearer {token}'})
    print('STATUS', resp.status_code)
    try:
        print('JSON:', resp.get_json())
    except Exception as e:
        print('GET_JSON_ERROR', e)
    print('TEXT:', resp.get_data(as_text=True))
