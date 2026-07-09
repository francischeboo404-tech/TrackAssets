from app import create_app, db
from app.models.organization import Organization
from app.models.user import User
from app.models.supplier import Supplier
from app.models.inventory import InventoryItem, AuditLog
from app.services.procurement_service import ProcurementService
from app.services.receiving_service import ReceivingService
from app.services.report_analytics_service import ReportAnalyticsService

app = create_app('testing')
with app.app_context():
    db.drop_all()
    db.create_all()
    org = Organization(name='E2E Org', code='E2E-PROC-RECV')
    db.session.add(org)
    db.session.commit()
    user = User(email='e2e@test.org', username='e2e_user', organisation_id=org.id, role='admin')
    user.set_password('Password123!')
    db.session.add(user)
    db.session.commit()
    supplier = Supplier(name='E2E Supplier', organisation_id=org.id)
    db.session.add(supplier)
    db.session.commit()
    item = InventoryItem(sku='E2E-001', name='E2E Item', organisation_id=org.id, quantity=0, unit_price=100.0)
    db.session.add(item)
    db.session.commit()

    pr = ProcurementService.create_purchase_request(org.id, user.id, 'E2E purchase request', [{'item_id': item.id, 'quantity': 5}])
    ProcurementService.approve_purchase_request(pr.id, user.id)
    po = ProcurementService.create_purchase_order(org.id, pr.id, supplier.id, [{'item_id': item.id, 'quantity': 5, 'unit_cost': 100.0}])
    ProcurementService.approve_purchase_order(po.id)
    grn = ReceivingService.create_grn(org.id, po.id, received_by_id=user.id, items_data=[{'item_id': item.id, 'quantity_received': 5, 'unit_cost': 100.0}])
    iar = ReceivingService.create_inspection_report(org.id, grn.id, inspector_id=user.id, status='passed', comments='OK')
    before_qty = db.session.get(InventoryItem, item.id).quantity
    ReceivingService.approve_grn(grn.id)
    db.session.refresh(item)
    print('item quantity', item.quantity, 'unit_price', item.unit_price)
    report = ReportAnalyticsService.get_inventory_report(org.id)
    print('report', report)
    print('total_valuation', report['total_valuation'])
    print('legacy calculation', db.session.query(db.func.sum(InventoryItem.quantity * InventoryItem.unit_price)).scalar())
    print('warehouse rows', [(row.item_id, row.quantity_on_hand) for row in db.session.query(app.models.stock_levels.WarehouseStock).all()])
