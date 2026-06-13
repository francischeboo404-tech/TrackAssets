from datetime import datetime
from app import db
from app.models import InventoryItem, WarehouseStock, RestockAlert
from app.services.event_bus import event_bus


class RestockService:
    """Service for managing replenishment logic and stock health."""

    @staticmethod
    def evaluate_stock_health(item_id, warehouse_id=None):
        """Evaluate stock levels against thresholds and raise alerts if needed."""
        item = InventoryItem.query.get(item_id)
        if not item:
            return

        # 1. Global Check (Legacy/Fallback)
        if item.quantity <= item.reorder_level:
            RestockService._create_or_update_alert(
                item.organisation_id,
                item.id,
                None,
                item.quantity,
                item.reorder_level,
                "LOW",
            )

        # 2. Warehouse-Specific Check
        query = WarehouseStock.query.filter_by(item_id=item_id)
        if warehouse_id:
            query = query.filter_by(warehouse_id=warehouse_id)

        warehouse_levels = query.all()
        for level in warehouse_levels:
            if level.quantity_available <= level.reorder_point:
                severity = (
                    "CRITICAL"
                    if level.quantity_available <= level.min_stock_level
                    else "LOW"
                )
                if level.quantity_available <= 0:
                    severity = "OUT_OF_STOCK"

                RestockService._create_or_update_alert(
                    item.organisation_id,
                    item.id,
                    level.warehouse_id,
                    level.quantity_available,
                    level.reorder_point,
                    severity,
                )

    @staticmethod
    def _create_or_update_alert(
        org_id, item_id, warehouse_id, current_qty, threshold, severity
    ):
        """Helper to manage unique pending alerts."""
        existing = RestockAlert.query.filter_by(
            organisation_id=org_id,
            item_id=item_id,
            warehouse_id=warehouse_id,
            status="PENDING",
        ).first()

        if existing:
            existing.current_quantity = current_qty
            existing.severity = severity
            existing.updated_at = datetime.utcnow()
        else:
            alert = RestockAlert(
                organisation_id=org_id,
                item_id=item_id,
                warehouse_id=warehouse_id,
                severity=severity,
                current_quantity=current_qty,
                threshold_level=threshold,
                message=f"Stock level ({current_qty}) is below reorder point ({threshold}).",
            )
            db.session.add(alert)

        # We do not commit here to allow the calling service (e.g. InventoryService)
        # to manage the session's transaction lifecycle and atomic commits.

        # Real-time Broadcast
        event_bus.publish(
            "RESTOCK_ALERT",
            {
                "item_id": item_id,
                "warehouse_id": warehouse_id,
                "severity": severity,
                "current_qty": current_qty,
            },
            organisation_id=org_id,
        )

    @staticmethod
    def get_pending_alerts(org_id):
        """Get all active replenishment alerts."""
        return (
            RestockAlert.query.filter_by(
                organisation_id=org_id, status="PENDING"
            )
            .order_by(RestockAlert.created_at.desc())
            .all()
        )
