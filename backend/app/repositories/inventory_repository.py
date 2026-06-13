from app import db
from app.models import inventory
from app.models import stock_levels
from app.models import location_topology


class InventoryRepository:
    """Repository encapsulating ORM queries for inventory items."""

    def list_items(
        self, org_id, page=1, per_page=50, search=None, low_stock_only=False
    ):
        query = inventory.InventoryItem.query.filter_by(
            organisation_id=org_id, is_active=True
        )

        if search:
            query = query.outerjoin(stock_levels.WarehouseStock).outerjoin(
                location_topology.Warehouse, stock_levels.WarehouseStock.warehouse_id == location_topology.Warehouse.id
            ).filter(
                db.or_(
                    inventory.InventoryItem.name.ilike(f"%{search}%"),
                    inventory.InventoryItem.sku.ilike(f"%{search}%"),
                    inventory.InventoryItem.description.ilike(f"%{search}%"),
                    location_topology.Warehouse.name.ilike(f"%{search}%"),
                )
            )

        if low_stock_only:
            query = query.filter(
                inventory.InventoryItem.quantity
                <= inventory.InventoryItem.reorder_level
            )
        query = query.order_by(inventory.InventoryItem.created_at.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_item(self, item_id, org_id):
        return inventory.InventoryItem.query.filter_by(
            id=item_id, organisation_id=org_id, is_active=True
        ).first()

    def get_recent_movements(self, item_id, org_id, limit=10):
        return (
            inventory.StockMovement.query.join(inventory.InventoryItem)
            .filter(
                inventory.InventoryItem.id == item_id,
                inventory.InventoryItem.organisation_id == org_id,
            )
            .order_by(inventory.StockMovement.date.desc())
            .limit(limit)
            .all()
        )

    def exists_sku(self, org_id, sku):
        if not sku:
            return False
        return (
            inventory.InventoryItem.query.filter_by(
                sku=sku, organisation_id=org_id
            ).first()
            is not None
        )

    def create_item(self, org_id, data, session=None):
        sess = session or db.session
        new_item = inventory.InventoryItem(
            organisation_id=org_id,
            name=data["name"],
            sku=data.get("sku"),
            description=data.get("description"),
            quantity=data.get("quantity", 0),
            reorder_level=data.get("reorder_level", 10),
            unit_price=data["unit_price"],
            unit=data.get("unit", "pcs"),
        )
        sess.add(new_item)
        return new_item

    def update_item(self, item, update_fields):
        for field, value in update_fields.items():
            setattr(item, field, value)
        item.updated_at = db.func.now()
        return item

    def soft_delete_item(self, item):
        item.is_active = False
        return item

    def low_stock_items(self, org_id):
        return inventory.InventoryItem.query.filter(
            inventory.InventoryItem.organisation_id == org_id,
            inventory.InventoryItem.is_active == True,
            inventory.InventoryItem.quantity
            <= inventory.InventoryItem.reorder_level,
        ).all()

    def stats(self, org_id):
        total_items = inventory.InventoryItem.query.filter_by(
            organisation_id=org_id, is_active=True
        ).count()

        total_value_result = (
            db.session.query(
                db.func.sum(
                    inventory.InventoryItem.quantity
                    * inventory.InventoryItem.unit_price
                )
            )
            .filter_by(organisation_id=org_id, is_active=True)
            .scalar()
        )

        total_value = total_value_result or 0

        low_stock_count = inventory.InventoryItem.query.filter(
            inventory.InventoryItem.organisation_id == org_id,
            inventory.InventoryItem.is_active == True,
            inventory.InventoryItem.quantity
            <= inventory.InventoryItem.reorder_level,
        ).count()

        # recent movements summary (last 30 days)
        from datetime import datetime, timedelta

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        recent_movements = (
            db.session.query(
                inventory.StockMovement.type,
                db.func.sum(inventory.StockMovement.quantity),
            )
            .join(inventory.InventoryItem)
            .filter(
                inventory.InventoryItem.organisation_id == org_id,
                inventory.StockMovement.date >= thirty_days_ago,
            )
            .group_by(inventory.StockMovement.type)
            .all()
        )

        movements_summary = {
            movement_type: qty for movement_type, qty in recent_movements
        }

        return {
            "total_items": total_items,
            "total_value": total_value,
            "low_stock_count": low_stock_count,
            "recent_movements": {
                "stock_in": movements_summary.get("IN", 0),
                "stock_out": movements_summary.get("OUT", 0),
            },
        }
