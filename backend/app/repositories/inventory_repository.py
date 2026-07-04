from app import db
from app.models import inventory
from app.models import stock_levels
from app.models import location_topology


class InventoryRepository:
    """Repository encapsulating ORM queries for inventory items."""

    def list_items(
        self, org_id, page=1, per_page=50, search=None, low_stock_only=False, department_id=None
    ):
        query = inventory.InventoryItem.query.filter_by(
            organisation_id=org_id, is_active=True
        )

        # If a department is provided, attempt to scope items to the department's warehouse
        if department_id:
            from app.models.organization import Department

            dept = (
                db.session.query(Department)
                .filter_by(id=department_id, organisation_id=org_id, is_active=True)
                .first()
            )
            if dept:
                if getattr(dept, 'warehouse_id', None):
                    query = query.filter(inventory.InventoryItem.warehouse_id == dept.warehouse_id)
                else:
                    # No warehouse configured for department — include items that have been
                    # issued to or returned from this department. Build a subquery union
                    # of item ids from ItemIssue and ItemReturn and restrict items to those.
                    from app.models.organization import ItemIssue, ItemReturn

                    issue_sq = (
                        db.session.query(ItemIssue.item_id.label('item_id'))
                        .filter(
                            ItemIssue.organisation_id == org_id,
                            ItemIssue.to_department_id == department_id,
                        )
                    )
                    return_sq = (
                        db.session.query(ItemReturn.item_id.label('item_id'))
                        .filter(
                            ItemReturn.organisation_id == org_id,
                            ItemReturn.from_department_id == department_id,
                        )
                    )

                    union_sq = issue_sq.union(return_sq).subquery()

                    query = query.filter(inventory.InventoryItem.id.in_(
                        db.session.query(union_sq.c.item_id)
                    ))

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
            stock_totals = (
                db.session.query(
                    stock_levels.WarehouseStock.item_id,
                    db.func.coalesce(
                        db.func.sum(stock_levels.WarehouseStock.quantity_on_hand),
                        0,
                    ).label("warehouse_qty"),
                )
                .group_by(stock_levels.WarehouseStock.item_id)
                .subquery()
            )
            query = query.outerjoin(
                stock_totals,
                stock_totals.c.item_id == inventory.InventoryItem.id,
            ).filter(
                db.func.coalesce(
                    stock_totals.c.warehouse_qty,
                    inventory.InventoryItem.quantity,
                )
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

    def exists_sku(self, org_id, sku, exclude_id=None):
        if not sku:
            return False

        normalized_sku = str(sku).strip()
        if not normalized_sku:
            return False

        query = inventory.InventoryItem.query.filter(
            inventory.InventoryItem.organisation_id == org_id,
            db.func.lower(inventory.InventoryItem.sku) == normalized_sku.lower(),
        )
        if exclude_id is not None:
            query = query.filter(inventory.InventoryItem.id != exclude_id)

        return query.first() is not None

    def create_item(self, org_id, data, session=None):
        sess = session or db.session
        new_item = inventory.InventoryItem(
            organisation_id=org_id,
            name=data["name"],
            sku=data.get("sku"),
            description=data.get("description"),
            quantity=int(data.get("quantity") or 0),
            reorder_level=data.get("reorder_level", 10),
            unit_price=data["unit_price"],
            unit=data.get("unit", "pcs"),
            # persist extended fields if provided
            category_id=data.get("category_id"),
            item_type=data.get("item_type"),
            status=data.get("status"),
            preferred_supplier_id=data.get("preferred_supplier_id"),
            supplier_item_reference=data.get("supplier_item_reference"),
            purchase_cost=data.get("purchase_cost"),
            last_purchase_cost=data.get("last_purchase_cost"),
            tax_category=data.get("tax_category"),
            lead_time_days=data.get("lead_time_days"),
            min_stock_level=data.get("min_stock_level"),
            max_stock_level=data.get("max_stock_level"),
            safety_stock=data.get("safety_stock"),
            opening_stock=None,
            warehouse_id=data.get("warehouse_id"),
            batch_tracking=data.get("batch_tracking", False),
            serial_tracking=data.get("serial_tracking", False),
            expiry_tracking=data.get("expiry_tracking", False),
        )
        sess.add(new_item)
        sess.flush()
        
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
        stock_totals = (
            db.session.query(
                stock_levels.WarehouseStock.item_id,
                db.func.coalesce(
                    db.func.sum(stock_levels.WarehouseStock.quantity_on_hand),
                    0,
                ).label("warehouse_qty"),
            )
            .group_by(stock_levels.WarehouseStock.item_id)
            .subquery()
        )
        return (
            inventory.InventoryItem.query.outerjoin(
                stock_totals,
                stock_totals.c.item_id == inventory.InventoryItem.id,
            )
            .filter(
                inventory.InventoryItem.organisation_id == org_id,
                inventory.InventoryItem.is_active == True,
                db.func.coalesce(
                    stock_totals.c.warehouse_qty,
                    inventory.InventoryItem.quantity,
                )
                <= inventory.InventoryItem.reorder_level,
            )
            .all()
        )

    def stats(self, org_id):
        total_items = inventory.InventoryItem.query.filter_by(
            organisation_id=org_id, is_active=True
        ).count()

        warehouse_value = (
            db.session.query(
                db.func.coalesce(
                    db.func.sum(
                        stock_levels.WarehouseStock.quantity_on_hand
                        * inventory.InventoryItem.unit_price
                    ),
                    0,
                )
            )
            .join(
                inventory.InventoryItem,
                stock_levels.WarehouseStock.item_id == inventory.InventoryItem.id,
            )
            .filter(
                inventory.InventoryItem.organisation_id == org_id,
                inventory.InventoryItem.is_active == True,
            )
            .scalar()
            or 0
        )

        legacy_value = (
            db.session.query(
                db.func.coalesce(
                    db.func.sum(
                        inventory.InventoryItem.quantity
                        * inventory.InventoryItem.unit_price
                    ),
                    0,
                )
            )
            .filter(
                inventory.InventoryItem.organisation_id == org_id,
                inventory.InventoryItem.is_active == True,
                ~inventory.InventoryItem.id.in_(
                    db.session.query(stock_levels.WarehouseStock.item_id).distinct()
                ),
            )
            .scalar()
            or 0
        )

        total_value = warehouse_value + legacy_value

        stock_totals = (
            db.session.query(
                stock_levels.WarehouseStock.item_id,
                db.func.coalesce(
                    db.func.sum(stock_levels.WarehouseStock.quantity_on_hand),
                    0,
                ).label("warehouse_qty"),
            )
            .group_by(stock_levels.WarehouseStock.item_id)
            .subquery()
        )

        low_stock_count = (
            inventory.InventoryItem.query.outerjoin(
                stock_totals,
                stock_totals.c.item_id == inventory.InventoryItem.id,
            )
            .filter(
                inventory.InventoryItem.organisation_id == org_id,
                inventory.InventoryItem.is_active == True,
                db.func.coalesce(
                    stock_totals.c.warehouse_qty,
                    inventory.InventoryItem.quantity,
                )
                <= inventory.InventoryItem.reorder_level,
            )
            .count()
        )

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


class InventoryBatchRepository:
    """Repository encapsulating ORM queries for inventory batches."""

    def list_batches(self, org_id, page=1, per_page=50, search=None, item_id=None, status=None, show_expired=False):
        """List batches for an organization with optional filters"""
        query = inventory.InventoryBatch.query.filter_by(organisation_id=org_id)

        if item_id:
            query = query.filter_by(item_id=item_id)

        if status:
            query = query.filter_by(status=status)

        if search:
            query = query.filter(
                db.or_(
                    inventory.InventoryBatch.batch_number.ilike(f"%{search}%"),
                )
            )

        if not show_expired:
            # Only show non-expired batches
            from datetime import datetime
            query = query.filter(
                db.or_(
                    inventory.InventoryBatch.expiry_date == None,
                    inventory.InventoryBatch.expiry_date > datetime.utcnow()
                )
            )

        query = query.order_by(inventory.InventoryBatch.created_at.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_batch(self, batch_id, org_id):
        """Get a specific batch"""
        return inventory.InventoryBatch.query.filter_by(
            id=batch_id, organisation_id=org_id
        ).first()

    def get_batch_by_number(self, batch_number, item_id, org_id):
        """Get batch by batch number and item"""
        return inventory.InventoryBatch.query.filter_by(
            batch_number=batch_number, item_id=item_id, organisation_id=org_id
        ).first()

    def create_batch(self, org_id, data, session=None):
        """Create a new batch"""
        sess = session or db.session
        new_batch = inventory.InventoryBatch(
            organisation_id=org_id,
            batch_number=data["batch_number"],
            item_id=data["item_id"],
            quantity=0,
            warehouse_id=data.get("warehouse_id"),
            received_date=data.get("received_date"),
            manufacture_date=data.get("manufacture_date"),
            expiry_date=data.get("expiry_date"),
            supplier_id=data.get("supplier_id"),
            status=data.get("status", "available"),
        )
        sess.add(new_batch)
        return new_batch

    def update_batch(self, batch, update_fields, session=None):
        """Update a batch"""
        sess = session or db.session
        for field, value in update_fields.items():
            if field in ['batch_number', 'quantity', 'warehouse_id', 'received_date', 
                        'manufacture_date', 'expiry_date', 'supplier_id', 'status']:
                setattr(batch, field, value)
        batch.updated_at = db.func.now()
        return batch

    def delete_batch(self, batch, session=None):
        """Delete a batch"""
        sess = session or db.session
        sess.delete(batch)
        return batch

    def get_expiring_batches(self, org_id, days_until_expiry=30):
        """Get batches expiring within specified days"""
        from datetime import datetime, timedelta
        future_date = datetime.utcnow() + timedelta(days=days_until_expiry)
        return inventory.InventoryBatch.query.filter(
            inventory.InventoryBatch.organisation_id == org_id,
            inventory.InventoryBatch.expiry_date.isnot(None),
            inventory.InventoryBatch.expiry_date <= future_date,
            inventory.InventoryBatch.status == 'available'
        ).order_by(inventory.InventoryBatch.expiry_date.asc()).all()

    def get_expired_batches(self, org_id):
        """Get all expired batches"""
        from datetime import datetime
        return inventory.InventoryBatch.query.filter(
            inventory.InventoryBatch.organisation_id == org_id,
            inventory.InventoryBatch.expiry_date.isnot(None),
            inventory.InventoryBatch.expiry_date < datetime.utcnow()
        ).all()

    def batch_stats(self, org_id):
        """Get batch statistics"""
        total_batches = inventory.InventoryBatch.query.filter_by(
            organisation_id=org_id
        ).count()

        total_batch_quantity = (
            db.session.query(db.func.sum(inventory.InventoryBatch.quantity))
            .filter_by(organisation_id=org_id)
            .scalar() or 0
        )

        # Count expiring soon (30 days)
        from datetime import datetime, timedelta
        future_date = datetime.utcnow() + timedelta(days=30)
        expiring_soon = inventory.InventoryBatch.query.filter(
            inventory.InventoryBatch.organisation_id == org_id,
            inventory.InventoryBatch.expiry_date.isnot(None),
            inventory.InventoryBatch.expiry_date <= future_date,
            inventory.InventoryBatch.expiry_date > datetime.utcnow()
        ).count()

        # Count expired
        expired = inventory.InventoryBatch.query.filter(
            inventory.InventoryBatch.organisation_id == org_id,
            inventory.InventoryBatch.expiry_date.isnot(None),
            inventory.InventoryBatch.expiry_date < datetime.utcnow()
        ).count()

        return {
            "total_batches": total_batches,
            "total_batch_quantity": total_batch_quantity,
            "expiring_soon_count": expiring_soon,
            "expired_count": expired,
        }
