from app import create_app, db
from app.models import Organization, Warehouse
from app.services.inventory_service import InventoryService
from app.services.stock_service import StockService

app = create_app('testing')
with app.app_context():
    db.drop_all()
    db.create_all()

    org = Organization(name='Test', code='T1')
    db.session.add(org)
    db.session.commit()

    wh = Warehouse(name='Main', code='WH1', organisation_id=org.id)
    db.session.add(wh)
    db.session.commit()

    svc = InventoryService(session=db.session)
    ss = StockService(session=db.session)

    item1 = svc.create_item(org.id, {
        'name': 'Q5',
        'sku': 'Q5',
        'quantity': 5,
        'reorder_level': 1,
        'unit_price': 10.0,
        'unit': 'pcs',
        'warehouse_id': wh.id,
    })
    db.session.refresh(item1)
    print('item1 id:', item1.id)
    print('item1.quantity:', item1.quantity)
    print('item1.opening_stock:', item1.opening_stock)
    print('item1 current qty:', ss.get_current_quantity(item1.id))

    item2 = svc.create_item(org.id, {
        'name': 'O50',
        'sku': 'O50',
        'quantity': 0,
        'reorder_level': 1,
        'unit_price': 10.0,
        'unit': 'pcs',
        'opening_stock': 50,
        'warehouse_id': wh.id,
    })
    db.session.refresh(item2)
    print('item2 id:', item2.id)
    print('item2.quantity:', item2.quantity)
    print('item2.opening_stock:', item2.opening_stock)
    print('item2 current qty:', ss.get_current_quantity(item2.id))

    from app.services.inventory_service import InventoryService as InvService
    item_list = InvService(session=db.session).list_items(org.id)
    for i in item_list.items:
        print('list item', i.id, 'name', i.name, 'item.quantity', i.quantity, 'stock_service', ss.get_current_quantity(i.id))

    # Create a user for API auth and verify inventory endpoint
    from app.models import User
    user = User(username='tester', email='tester@example.com', role='admin', organisation_id=org.id)
    user.set_password('Password1!')
    db.session.add(user)
    db.session.commit()
    client = app.test_client()
    login_resp = client.post('/api/auth/login', json={'email': 'tester@example.com', 'password': 'Password1!'})
    print('login status', login_resp.status_code, login_resp.get_json())
    if login_resp.status_code != 200:
        raise SystemExit('Login failed')
    token = login_resp.get_json().get('access_token')
    inv_resp = client.get('/api/inventory', headers={'Authorization': f'Bearer {token}'})
    print('inventory api status', inv_resp.status_code)
    print(inv_resp.get_json())
