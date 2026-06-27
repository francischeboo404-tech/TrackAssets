"""Reconciliation helper: compare AnalyticsService outputs to raw DB aggregates.

Run with: python backend/scripts/reconcile_reports.py

This script uses the `testing` app config and seeds deterministic sample data
so results are reproducible and safe to run locally.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func

from app import create_app, db
from app.models import InventoryItem, StockMovement
from app.models.stock_levels import WarehouseStock
from app.models.location_topology import Warehouse
from app.models.organization import Organization
from app.services.analytics_service import AnalyticsService


def seed_data(org_id=1):
    # Create a simple organisation and some items + stocks + movements
    org = Organization(id=org_id, name="Reconcile Org", code="RECON")
    db.session.add(org)
    db.session.flush()

    # Create a warehouse
    wh = Warehouse(organisation_id=org_id, name="Main WH", code="WH-1")
    db.session.add(wh)
    db.session.flush()

    # Inventory items
    item1 = InventoryItem(organisation_id=org_id, name="Item A", sku="A-1", quantity=100, unit_price=5.0)
    item2 = InventoryItem(organisation_id=org_id, name="Item B", sku="B-1", quantity=50, unit_price=2.0)
    db.session.add_all([item1, item2])
    db.session.flush()

    # Warehouse-specific stocks (simulate partial allocation)
    ws1 = WarehouseStock(item_id=item1.id, warehouse_id=wh.id, quantity_on_hand=20)
    ws2 = WarehouseStock(item_id=item2.id, warehouse_id=wh.id, quantity_on_hand=10)
    db.session.add_all([ws1, ws2])
    db.session.flush()

    # Stock movements across the last 3 days
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    movements = []
    # Day -0: 3 IN for item1, 1 OUT for item2
    for _ in range(3):
        movements.append(StockMovement(item_id=item1.id, type="IN", quantity=1, date=today + timedelta(hours=8), organization_id=org_id, warehouse_id=wh.id))
    movements.append(StockMovement(item_id=item2.id, type="OUT", quantity=1, date=today + timedelta(hours=9), organization_id=org_id, warehouse_id=wh.id))
    # Day -1: 2 IN item2
    for _ in range(2):
        movements.append(StockMovement(item_id=item2.id, type="IN", quantity=1, date=today - timedelta(days=1, hours=-10), organization_id=org_id, warehouse_id=wh.id))
    # Day -2: 1 OUT item1
    movements.append(StockMovement(item_id=item1.id, type="OUT", quantity=1, date=today - timedelta(days=2, hours=-11), organization_id=org_id, warehouse_id=None))

    db.session.add_all(movements)
    db.session.commit()

    return org, wh, [item1, item2]


def manual_inventory_summary(org_id, warehouse_id=None):
    from app.models import RestockAlert
    if warehouse_id:
        total_items = db.session.query(func.sum(WarehouseStock.quantity_on_hand)).filter(WarehouseStock.warehouse_id == warehouse_id).scalar() or 0
    else:
        total_items = db.session.query(func.sum(InventoryItem.quantity)).filter(InventoryItem.organisation_id == org_id, InventoryItem.is_active == True).scalar() or 0

    # pending alerts count
    alert_counts = db.session.query(RestockAlert.severity, func.count(RestockAlert.id)).filter_by(organisation_id=org_id, status="PENDING")
    if warehouse_id:
        alert_counts = alert_counts.filter_by(warehouse_id=warehouse_id)
    alert_counts = dict(alert_counts.group_by(RestockAlert.severity).all()) if alert_counts is not None else {}

    return {"total_items": int(total_items or 0), "alert_counts": alert_counts}


def manual_inventory_valuation(org_id, warehouse_id=None):
    if warehouse_id:
        value = db.session.query(func.sum(WarehouseStock.quantity_on_hand * InventoryItem.unit_price)).join(InventoryItem, InventoryItem.id == WarehouseStock.item_id).filter(InventoryItem.organisation_id == org_id, InventoryItem.is_active == True, WarehouseStock.warehouse_id == warehouse_id).scalar() or 0
    else:
        value = db.session.query(func.sum(InventoryItem.quantity * InventoryItem.unit_price)).filter(InventoryItem.organisation_id == org_id, InventoryItem.is_active == True).scalar() or 0
    return round(float(value or 0), 2)


def manual_movement_trends(org_id, days=7, warehouse_id=None):
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.session.query(func.date(StockMovement.date).label('day'), StockMovement.type, func.count(StockMovement.id)).join(InventoryItem).filter(InventoryItem.organisation_id == org_id, StockMovement.date >= threshold)
    if warehouse_id is not None:
        # For authoritative counts, filter StockMovement.warehouse_id
        query = query.filter(StockMovement.warehouse_id == warehouse_id)
    movements = query.group_by('day', StockMovement.type).all()

    results = {}
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        results[str(d)] = {"IN": 0, "OUT": 0}

    for day, m_type, count in movements:
        d_str = str(day)
        if d_str in results:
            results[d_str][m_type] = int(count)
        else:
            results[d_str] = {"IN": 0, "OUT": 0}
            results[d_str][m_type] = int(count)

    return results


def run_reconciliation():
    app = create_app('testing')
    ctx = app.app_context()
    ctx.push()

    # Prepare DB schema and seed data
    db.create_all()
    org, wh, items = seed_data(org_id=1)

    print("\n--- Reconciliation Report (org_id=1) ---\n")

    # Inventory summary (global)
    svc_summary = AnalyticsService.get_inventory_summary(org.id)
    manual_summary = manual_inventory_summary(org.id)
    print("Inventory Summary (global):")
    print("  AnalyticsService:", svc_summary)
    print("  Manual:", manual_summary)
    print("  Diff total_items:", int(svc_summary.get('total_items', 0)) - int(manual_summary.get('total_items', 0)))

    # Inventory valuation (global)
    svc_value = AnalyticsService.get_inventory_valuation(org.id)
    manual_value = manual_inventory_valuation(org.id)
    print("\nInventory Valuation (global):")
    print(f"  AnalyticsService: {svc_value}")
    print(f"  Manual:           {manual_value}")
    print(f"  Diff:             {round(float(svc_value) - float(manual_value), 2)}")

    # Movement trends (global)
    svc_trends = AnalyticsService.get_movement_trends(org.id, days=7)
    manual_trends = manual_movement_trends(org.id, days=7)
    print("\nMovement Trends (global):")
    print("  AnalyticsService sample:", {k: svc_trends[k] for k in list(svc_trends.keys())[:3]})
    print("  Manual sample:        ", {k: manual_trends[k] for k in list(manual_trends.keys())[:3]})

    # Warehouse-scoped comparisons
    svc_summary_wh = AnalyticsService.get_inventory_summary(org.id, warehouse_id=wh.id)
    manual_summary_wh = manual_inventory_summary(org.id, warehouse_id=wh.id)
    svc_value_wh = AnalyticsService.get_inventory_valuation(org.id, warehouse_id=wh.id)
    manual_value_wh = manual_inventory_valuation(org.id, warehouse_id=wh.id)
    svc_trends_wh = AnalyticsService.get_movement_trends(org.id, days=7, warehouse_id=wh.id)
    manual_trends_wh = manual_movement_trends(org.id, days=7, warehouse_id=wh.id)

    print("\n--- Warehouse-scoped (Main WH) ---")
    print("Inventory Summary (warehouse):")
    print("  AnalyticsService:", svc_summary_wh)
    print("  Manual:", manual_summary_wh)
    print("  Diff total_items:", int(svc_summary_wh.get('total_items', 0)) - int(manual_summary_wh.get('total_items', 0)))

    print("\nInventory Valuation (warehouse):")
    print(f"  AnalyticsService: {svc_value_wh}")
    print(f"  Manual:           {manual_value_wh}")
    print(f"  Diff:             {round(float(svc_value_wh) - float(manual_value_wh), 2)}")

    print("\nMovement Trends (warehouse):")
    print("  AnalyticsService sample:", {k: svc_trends_wh[k] for k in list(svc_trends_wh.keys())[:3]})
    print("  Manual sample:        ", {k: manual_trends_wh[k] for k in list(manual_trends_wh.keys())[:3]})

    print("\n--- End Report ---\n")

    # Cleanup
    db.session.remove()
    db.drop_all()
    ctx.pop()


if __name__ == "__main__":
    run_reconciliation()
