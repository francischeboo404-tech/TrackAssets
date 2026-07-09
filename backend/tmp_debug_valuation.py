from app import create_app, db
from app.models.inventory import InventoryItem
from app.models.organization import Organization
from app.services.analytics_service import AnalyticsService
from app.services.report_analytics_service import ReportAnalyticsService

app = create_app('testing')
with app.app_context():
    db.drop_all()
    db.create_all()
    org = Organization(id=1, name='Acme', code='ACME')
    db.session.add(org)
    item = InventoryItem(organisation_id=1, name='Paper', sku='P-1', quantity=5, reorder_level=10, unit_price=10)
    db.session.add(item)
    db.session.commit()
    print('item', item.id, item.quantity, item.unit_price)
    print('legacy', db.session.query(db.func.sum(InventoryItem.quantity * InventoryItem.unit_price)).scalar())
    print('analytics', AnalyticsService.get_inventory_valuation(1), type(AnalyticsService.get_inventory_valuation(1)))
    report = ReportAnalyticsService.get_inventory_report(1)
    print('report total_units', report['total_units'])
    print('report total_valuation', report['total_valuation'], type(report['total_valuation']))
