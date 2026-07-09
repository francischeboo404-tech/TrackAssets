from app import db
from app.models import inventory
from app.models.location_topology import Warehouse
from app.models.stock_levels import WarehouseStock
from app.audit_service import AuditService
from app.repositories.inventory_repository import InventoryRepository
from app.errors import NotFoundError, ConflictError, ValidationError
from app.db_utils import transaction_retry
from app.services.event_bus import event_bus
from app.services.qr_service import QRService
from flask import current_app
from app.services.stock_service import StockService
from app.models.location_topology import Warehouse

class InventoryService:
    """Service layer for inventory business logic.

    This service manages transaction boundaries and uses the repository for
    data access. It does not alter response shapes — controllers remain
    responsible for formatting responses.
    """
    

        

    def __init__(self, repository: InventoryRepository = None, session=None):
        self.repo = repository or InventoryRepository()
        self.session = session or db.session

    def list_items(
        self, org_id, page=1, per_page=50, search=None, low_stock_only=False, department_id=None, warehouse_id=None
    ):
        return self.repo.list_items(
            org_id,
            page=page,
            per_page=per_page,
            search=search,
            low_stock_only=low_stock_only,
            department_id=department_id,
            warehouse_id=warehouse_id,
        )

    def get_item(self, item_id, org_id):
        item = self.repo.get_item(item_id, org_id)
        if not item:
            raise NotFoundError("Inventory item not found")
        movements = self.repo.get_recent_movements(item_id, org_id)
        return item, movements

    # ------------------------------------------------------------------
    # Warehouse resolution helper
    # ------------------------------------------------------------------
    def _resolve_warehouse_id(self, org_id: int, validated_data: dict) -> int | None:
        """Return a concrete warehouse_id for the organisation.

        Resolution order:
        1. ``warehouse_name`` in data  → look up by name (case-insensitive)
        2. ``warehouse_id`` in data    → use directly after confirming it exists
        3. Neither present             → return None

        Raises ValidationError with a friendly message if the name or ID
        cannot be matched to an active warehouse in this organisation.
        """
        warehouse_name = (validated_data.get("warehouse_name") or "").strip()
        warehouse_id   = validated_data.get("warehouse_id")

        if warehouse_name:
            wh = (
                db.session.query(Warehouse)
                .filter(
                    Warehouse.organisation_id == org_id,
                    Warehouse.is_active == True,
                    db.func.upper(Warehouse.name) == warehouse_name.upper(),
                )
                .first()
            )
            if not wh:
                raise ValidationError(
                    f"Warehouse '{warehouse_name}' not found in your organisation. "
                    "Check the name matches exactly (e.g. 'MAIN WAREHOUSE')."
                )
            return wh.id

        if warehouse_id:
            wh = (
                db.session.query(Warehouse)
                .filter_by(id=warehouse_id, organisation_id=org_id, is_active=True)
                .first()
            )
            if not wh:
                raise ValidationError(
                    f"Warehouse ID {warehouse_id} not found in your organisation."
                )
            return wh.id

        return None

    @transaction_retry(max_retries=3)
    def create_item(self, org_id, validated_data):
        current_app.logger.debug(
            "create_item called",
            extra={"org_id": org_id, "data_keys": list(validated_data.keys())},
        )

        # business validations (uniqueness)
        if self.repo.exists_sku(org_id, validated_data.get("sku")):
            current_app.logger.warning(
                "create_item: sku conflict",
                extra={"sku": validated_data.get("sku")},
            )
            raise ConflictError("SKU already exists")

        # Resolve warehouse — prefer name lookup, fall back to ID, else None
        resolved_warehouse_id = self._resolve_warehouse_id(org_id, validated_data)

        # Inject resolved ID so the repository stores it on the item record
        if resolved_warehouse_id:
            validated_data = {**validated_data, "warehouse_id": resolved_warehouse_id}

        requested_quantity = int(validated_data.get("quantity") or 0)
        opening_stock = int(validated_data.get("opening_stock") or 0)
        if "opening_stock" in validated_data:
            validated_data = {k: v for k, v in validated_data.items() if k != "opening_stock"}

        if resolved_warehouse_id is not None and "quantity" in validated_data:
            # Warehouse stock is the source of truth for on-hand inventory.
            # When an initial warehouse is provided, quantity should be created
            # via a warehouse movement rather than stored only on the item row.
            validated_data = {k: v for k, v in validated_data.items() if k != "quantity"}

        item = self.repo.create_item(
            org_id, validated_data, session=self.session
        )

        if resolved_warehouse_id is not None and requested_quantity > 0 and opening_stock > 0:
            raise ValidationError(
                "Provide either quantity or opening_stock, not both, when creating an inventory item with a warehouse."
            )

        if requested_quantity > 0 and resolved_warehouse_id is not None:
            StockService(session=self.session).increase_stock(
                item_id=item.id,
                org_id=org_id,
                quantity=requested_quantity,
                warehouse_id=resolved_warehouse_id,
                reference="INITIAL_STOCK",
                notes="Initial stock quantity",
                commit=False,
            )
        elif opening_stock > 0:
            if not resolved_warehouse_id:
                raise ValidationError(
                    "Opening stock requires a warehouse. "
                    "Add a 'warehouse_name' column with the warehouse name "
                    "(e.g. 'MAIN WAREHOUSE') or provide a valid warehouse_id."
                )

            StockService(session=self.session).increase_stock(
                item_id=item.id,
                org_id=org_id,
                quantity=opening_stock,
                warehouse_id=resolved_warehouse_id,
                reference="OPENING_STOCK",
                notes="Initial opening balance",
                commit=False,
            )

        QRService.ensure_inventory_qr(item)
        # Audit log (added to same session)
        AuditService.log_inventory_change(
            item,
            "INVENTORY_ITEM_CREATED",
            reference="Initial creation",
            session=self.session,
        )
        try:
            self.session.commit()
        except Exception as e:
            current_app.logger.error(
                "create_item: commit failed", extra={"error": str(e)}
            )
            self.session.rollback()
            raise

        event_bus.publish("INVENTORY_CREATED", {"item_id": item.id, "sku": item.sku}, organisation_id=org_id)
        current_app.logger.info(
            "create_item: success",
            extra={"item_id": item.id, "sku": item.sku},
        )

        return item

    @transaction_retry(max_retries=3)
    def update_item(self, item_id, org_id, data):
        # Reload with lock
        item = (
            inventory.InventoryItem.query.with_for_update()
            .filter_by(id=item_id, organisation_id=org_id, is_active=True)
            .first()
        )
        if not item:
            raise NotFoundError("Inventory item not found")

        # Check SKU uniqueness if changing
        if "sku" in data:
            incoming_sku = (data.get("sku") or "").strip()
            current_sku = (item.sku or "").strip()
            if incoming_sku != current_sku:
                if self.repo.exists_sku(org_id, incoming_sku, exclude_id=item.id):
                    raise ConflictError("SKU already exists")

        old_values = {
            k: getattr(item, k)
            for k in [
                "name",
                "sku",
                "description",
                "reorder_level",
                "unit_price",
                "unit",
            ]
        }

        # include newly added fields in auditable old values
        for extra in [
            "category_id",
            "item_type",
            "status",
            "preferred_supplier_id",
            "supplier_item_reference",
            "purchase_cost",
            "last_purchase_cost",
            "tax_category",
            "lead_time_days",
            "min_stock_level",
            "max_stock_level",
            "safety_stock",
            "opening_stock",
            "warehouse_id",
            "batch_tracking",
            "serial_tracking",
            "expiry_tracking",
        ]:
            old_values[extra] = getattr(item, extra, None)

        if "quantity" in data:
            raise ValidationError(
                "Quantity cannot be edited directly; use stock movements"
            )

        if data.get("reorder_level") is not None and data["reorder_level"] < 0:
            raise ValidationError("Reorder level cannot be negative")
        if data.get("unit_price") is not None and data["unit_price"] < 0:
            raise ValidationError("Unit price cannot be negative")

        try:
            updatable_fields = {
                k: data[k]
                for k in [
                    "name",
                    "description",
                    "reorder_level",
                    "unit_price",
                    "unit",
                    # allow updates to extended fields
                    "category_id",
                    "item_type",
                    "status",
                    "preferred_supplier_id",
                    "supplier_item_reference",
                    "purchase_cost",
                    "last_purchase_cost",
                    "tax_category",
                    "lead_time_days",
                    "min_stock_level",
                    "max_stock_level",
                    "safety_stock",
                    "opening_stock",
                    "warehouse_id",
                    "batch_tracking",
                    "serial_tracking",
                    "expiry_tracking",
                ]
                if k in data
            }
            self.repo.update_item(item, updatable_fields)
            if "sku" in data:
                item.sku = data["sku"]

            AuditService.log_action(
                action="INVENTORY_ITEM_UPDATED",
                entity_type="inventory_item",
                entity_id=item.id,
                details={
                    "old_values": old_values,
                    "new_values": {
                        k: getattr(item, k) for k in old_values.keys()
                    },
                },
                organisation_id=org_id,
                session=self.session,
            )
            self.session.commit()
            
            # Re-evaluate stock health in case thresholds or quantities were modified manually
            from app.services.restock_service import RestockService
            RestockService.evaluate_stock_health(item.id)
            
            event_bus.publish("INVENTORY_UPDATED", {"item_id": item.id}, organisation_id=org_id)
            
            return item
        except Exception:
            self.session.rollback()
            raise

    @transaction_retry(max_retries=3)
    def update_stock(
        self,
        item_id,
        org_id,
        movement_type,
        quantity,
        warehouse_id=None,
        destination_warehouse_id=None,
        reference=None,
        notes=None,
    ):
        # Reload with lock (Fixes ARC-006)
        item = (
            inventory.InventoryItem.query.with_for_update()
            .filter_by(id=item_id, organisation_id=org_id)
            .first()
        )
        if not item:
            raise NotFoundError("Inventory item not found")

        try:
            stock_service = StockService(session=self.session)

            # Handle warehouse transfer: decrease from source, increase to destination
            if destination_warehouse_id is not None:
                if movement_type != "OUT":
                    raise ValidationError(
                        "Warehouse transfers must use movement type 'OUT' from source warehouse"
                    )
                if not warehouse_id:
                    raise ValidationError(
                        "Source warehouse_id is required for transfers"
                    )

                source_wh = (
                    self.session.query(Warehouse)
                    .filter_by(id=warehouse_id, organisation_id=org_id, is_active=True)
                    .first()
                )
                destination_wh = (
                    self.session.query(Warehouse)
                    .filter_by(id=destination_warehouse_id, organisation_id=org_id, is_active=True)
                    .first()
                )
                if not source_wh:
                    raise ValidationError("Source warehouse not found for this organisation")
                if not destination_wh:
                    raise ValidationError("Receiving warehouse not found for this organisation")
                if warehouse_id == destination_warehouse_id:
                    raise ValidationError("Source and receiving warehouse must be different")
                
                # Decrease from source warehouse
                stock_service.decrease_stock(
                    item_id=item.id,
                    org_id=org_id,
                    quantity=quantity,
                    warehouse_id=warehouse_id,
                    reference=reference or "TRANSFER_OUT",
                    notes=notes or f"Transfer to warehouse {destination_warehouse_id}",
                    destination_warehouse_id=destination_warehouse_id,
                    commit=False,
                )
                
                # Increase to destination warehouse
                stock_service.increase_stock(
                    item_id=item.id,
                    org_id=org_id,
                    quantity=quantity,
                    warehouse_id=destination_warehouse_id,
                    reference=reference or "TRANSFER_IN",
                    notes=notes or f"Transfer from warehouse {warehouse_id}",
                    commit=False,
                )
                
                action = "STOCK_TRANSFERRED"
                qty_change = 0  # Net change is zero for transfers
                
            elif movement_type == "IN":
                stock_service.increase_stock(
                    item_id=item.id,
                    org_id=org_id,
                    quantity=quantity,
                    warehouse_id=warehouse_id,
                    reference=reference,
                    notes=notes,
                    commit=False,
                )
                action = "STOCK_INCREASED"
                qty_change = quantity

            elif movement_type == "OUT":
                # Validate destination != source for transfers
                if destination_warehouse_id and destination_warehouse_id == warehouse_id:
                    raise ValueError("Source and destination warehouse must be different")

                stock_service.decrease_stock(
                    item_id=item.id,
                    org_id=org_id,
                    quantity=quantity,
                    warehouse_id=warehouse_id,
                    destination_warehouse_id=destination_warehouse_id,
                    reference=reference,
                    notes=notes,
                    commit=False,
                )

                # If a destination warehouse is specified, this is a transfer:
                # atomically receive the same quantity at the destination.
                if destination_warehouse_id:
                    transfer_ref = f"TRANSFER-IN:{reference}" if reference else None
                    transfer_notes = f"Transfer received from warehouse {warehouse_id}. {notes or ''}" .strip()
                    stock_service.increase_stock(
                        item_id=item.id,
                        org_id=org_id,
                        quantity=quantity,
                        warehouse_id=destination_warehouse_id,
                        reference=transfer_ref,
                        notes=transfer_notes,
                        commit=False,
                    )

                action = "STOCK_TRANSFERRED" if destination_warehouse_id else "STOCK_DECREASED"
                qty_change = -quantity

            else:
                raise ValidationError("Invalid movement type")

            AuditService.log_inventory_change(
                item,
                action,
                quantity_change=qty_change,
                reference=reference or "Manual adjustment",
                session=self.session,
            )

            self.session.commit()
            self.session.refresh(item)
            item.quantity = StockService(session=self.session).get_current_quantity(item.id)
            self.session.refresh(item)

            from app.services.restock_service import RestockService
            RestockService.evaluate_stock_health(item.id)

            event_bus.publish(
                "STOCK_UPDATE",
                {"item_id": item.id, "movement_type": movement_type, "quantity": qty_change},
                organisation_id=org_id,
            )
            from app.services.report_analytics_service import ReportAnalyticsService
            ReportAnalyticsService.invalidate_cache(org_id)

            return item
        except Exception as e:
            current_app.logger.exception(e)

            self.session.rollback()

            raise

    @transaction_retry(max_retries=3)
    def reserve_stock(self, item_id, org_id, quantity, warehouse_id=None, reference=None):
        """Reserve quantity on a WarehouseStock row to prevent double allocation.

        This updates `quantity_reserved` on the WarehouseStock row with a
        row-level lock and writes an audit entry. It commits the change.
        """
        if quantity is None or quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")

        wh = (
            self.session.query(WarehouseStock).with_for_update()
            .filter_by(item_id=item_id, warehouse_id=warehouse_id)
            .first()
        )
        if not wh:
            raise NotFoundError("No stock exists in the specified warehouse")

        available = wh.quantity_on_hand - (wh.quantity_reserved or 0)
        if available < quantity:
            raise ValidationError("Insufficient available stock in the specified warehouse")

        prev_reserved = wh.quantity_reserved or 0
        wh.quantity_reserved = prev_reserved + quantity
        self.session.flush()

        AuditService.log_action(
            action="STOCK_RESERVED",
            entity_type="inventory_item",
            entity_id=item_id,
            details={
                "warehouse_id": warehouse_id,
                "quantity": quantity,
                "previous_reserved": prev_reserved,
                "new_reserved": wh.quantity_reserved,
                "reference": reference,
            },
            organisation_id=org_id,
            session=self.session,
        )

        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return wh

    @transaction_retry(max_retries=3)
    def unreserve_stock(self, item_id, org_id, quantity, warehouse_id=None, reference=None):
        """Remove reserved quantity from a WarehouseStock row.

        Ensures reserved quantity does not go negative and writes an audit entry.
        """
        if quantity is None or quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")

        wh = (
            self.session.query(WarehouseStock).with_for_update()
            .filter_by(item_id=item_id, warehouse_id=warehouse_id)
            .first()
        )
        if not wh:
            # Nothing to unreserve
            return None

        prev_reserved = wh.quantity_reserved or 0
        wh.quantity_reserved = max(0, prev_reserved - quantity)
        self.session.flush()

        AuditService.log_action(
            action="STOCK_UNRESERVED",
            entity_type="inventory_item",
            entity_id=item_id,
            details={
                "warehouse_id": warehouse_id,
                "quantity": quantity,
                "previous_reserved": prev_reserved,
                "new_reserved": wh.quantity_reserved,
                "reference": reference,
            },
            organisation_id=org_id,
            session=self.session,
        )

        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return wh


    @transaction_retry(max_retries=3)
    def update_stock_batch(
        self,
        org_id,
        movements,
        user_id=None,
        module=None,
    ):
        """
        Batch stock update used during GRN approval.
        """

        updated_items = []

        for movement in movements:

            item = (
                inventory.InventoryItem.query
                .with_for_update()
                .filter_by(
                    id=movement["item_id"],
                    organisation_id=org_id
                )
                .first()
            )

            if not item:
                raise NotFoundError(
                    f"Inventory item {movement['item_id']} not found"
                )

            qty = int(movement["quantity"])
            movement_type = movement.get("type", "IN")

            if movement_type == "IN":
                StockService(session=self.session).increase_stock(
                    item_id=item.id,
                    org_id=org_id,
                    quantity=qty,
                    warehouse_id=movement.get("warehouse_id"),
                    reference=movement.get("reference"),
                    notes=movement.get("notes"),
                    commit=False,
                )
                audit_action = "STOCK_INCREASED"
                qty_change = qty
            elif movement_type == "OUT":
                try:
                    StockService(session=self.session).decrease_stock(
                        item_id=item.id,
                        org_id=org_id,
                        quantity=qty,
                        warehouse_id=movement.get("warehouse_id"),
                        reference=movement.get("reference"),
                        notes=movement.get("notes"),
                        commit=False,
                    )
                except ValidationError as e:
                    # Surface as a ConflictError for callers expecting conflict semantics
                    raise ConflictError(str(e))
                audit_action = "STOCK_DECREASED"
                qty_change = -qty
            else:
                raise ValidationError("Invalid movement type")

            if movement.get("unit_cost") is not None:
                item.last_purchase_cost = movement["unit_cost"]

                if not item.purchase_cost:
                    item.purchase_cost = movement["unit_cost"]

            AuditService.log_inventory_change(
                item,
                audit_action,
                quantity_change=qty_change,
                reference=movement.get("reference"),
                module=module,
                session=self.session,
            )

            updated_items.append(item.id)

        self.session.flush()

        event_bus.publish(
            "STOCK_BATCH_UPDATED",
            {
                "items": updated_items
            },
            organisation_id=org_id,
        )

        return updated_items


    @transaction_retry(max_retries=3)
    def delete_item(self, item_id, org_id):
        item = self.repo.get_item(item_id, org_id)
        if not item:
            raise NotFoundError("Inventory item not found")

        # Use StockService to compute the authoritative current quantity
        try:
            current_qty = StockService(session=self.session).get_current_quantity(item.id)
        except Exception:
            # Fallback to the quantity on the item row if StockService is unavailable
            current_qty = getattr(item, 'quantity', 0) or 0

        if current_qty > 0:
            raise ConflictError(f"Cannot delete item with remaining stock ({current_qty} units).")

        self.repo.soft_delete_item(item)
        AuditService.log_inventory_change(
            item,
            "INVENTORY_ITEM_DELETED",
            reference="Soft delete",
            session=self.session,
        )
        self.session.commit()
        
        event_bus.publish("INVENTORY_DELETED", {"item_id": item_id}, organisation_id=org_id)
        
        return item

    @transaction_retry(max_retries=3)
    def force_delete_item(self, item_id, org_id):
        item = self.repo.get_item(item_id, org_id)
        if not item:
            raise NotFoundError("Inventory item not found")

        current_qty = 0
        warehouse_rows = self.session.query(WarehouseStock).filter_by(item_id=item.id).all()
        try:
            current_qty = StockService(session=self.session).get_current_quantity(item.id)
        except Exception:
            current_qty = getattr(item, 'quantity', 0) or 0

        if current_qty > 0:
            warehouse_rows_cleared = []
            for wh_stock in warehouse_rows:
                previous_quantity = wh_stock.quantity_on_hand
                previous_reserved = wh_stock.quantity_reserved
                if previous_quantity != 0 or previous_reserved != 0:
                    warehouse_rows_cleared.append(
                        {
                            "warehouse_id": wh_stock.warehouse_id,
                            "previous_quantity": previous_quantity,
                            "previous_reserved": previous_reserved,
                        }
                    )
                    wh_stock.quantity_on_hand = 0
                    wh_stock.quantity_reserved = 0

            # Preserve an audit trail for the forced deletion and the stock zeroing.
            AuditService.log_action(
                action="INVENTORY_ITEM_FORCE_DELETED",
                entity_type="inventory_item",
                entity_id=item.id,
                details={
                    "previous_quantity": current_qty,
                    "new_quantity": 0,
                    "reference": "Force delete with remaining stock",
                    "warehouse_rows_cleared": warehouse_rows_cleared,
                },
                organisation_id=org_id,
                session=self.session,
            )

        self.repo.soft_delete_item(item)
        item.quantity = 0

        self.session.commit()
        event_bus.publish("INVENTORY_FORCE_DELETED", {"item_id": item.id, "previous_quantity": current_qty}, organisation_id=org_id)
        return item

    def low_stock_items(self, org_id):
        return self.repo.low_stock_items(org_id)

    def stats(self, org_id):
        return self.repo.stats(org_id)


class InventoryBatchService:
    """Service layer for inventory batch operations"""

    def __init__(self, batch_repo=None, session=None):
        from app.repositories.inventory_repository import InventoryBatchRepository
        self.batch_repo = batch_repo or InventoryBatchRepository()
        self.item_repo = InventoryRepository()
        self.session = session or db.session

    def list_batches(self, org_id, page=1, per_page=50, search=None, item_id=None, status=None, show_expired=False):
        """List batches with filters"""
        return self.batch_repo.list_batches(
            org_id, page=page, per_page=per_page, search=search, 
            item_id=item_id, status=status, show_expired=show_expired
        )

    def get_batch(self, batch_id, org_id):
        """Get a specific batch"""
        batch = self.batch_repo.get_batch(batch_id, org_id)
        if not batch:
            raise NotFoundError("Batch not found")
        return batch

    @transaction_retry(max_retries=3)
    def create_batch(self, org_id, validated_data):
        """Create a new batch"""
        current_app.logger.debug(
            "create_batch called",
            extra={"org_id": org_id, "item_id": validated_data.get("item_id")}
        )

        # Validate item exists
        item = self.item_repo.get_item(validated_data["item_id"], org_id)
        if not item:
            raise NotFoundError("Inventory item not found")

        # Check batch number uniqueness
        existing = self.batch_repo.get_batch_by_number(
            validated_data["batch_number"], 
            validated_data["item_id"], 
            org_id
        )
        if existing:
            raise ConflictError("Batch number already exists for this item")

        batch = self.batch_repo.create_batch(org_id, validated_data, session=self.session)
        
        AuditService.log_action(
            action="BATCH_CREATED",
            entity_type="inventory_batch",
            entity_id=batch.id,
            details={
                "batch_number": batch.batch_number,
                "item_id": batch.item_id,
                "quantity": batch.quantity,
                "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None
            },
            organisation_id=org_id,
            session=self.session,
        )

        try:
            self.session.commit()
        except Exception as e:
            current_app.logger.error("create_batch: commit failed", extra={"error": str(e)})
            self.session.rollback()
            raise

        event_bus.publish(
            "BATCH_CREATED", 
            {"batch_id": batch.id, "batch_number": batch.batch_number, "item_id": batch.item_id},
            organisation_id=org_id
        )

        current_app.logger.info("create_batch: success", extra={"batch_id": batch.id})
        return batch

    @transaction_retry(max_retries=3)
    def update_batch(self, batch_id, org_id, validated_data):
        """Update a batch"""
        batch = self.batch_repo.get_batch(batch_id, org_id)
        if not batch:
            raise NotFoundError("Batch not found")

        old_values = {
            k: getattr(batch, k) for k in ["batch_number", "quantity", "status", "expiry_date"]
        }

        updatable_fields = {
            k: validated_data[k]
            for k in ["batch_number", "quantity", "warehouse_id", "status", "expiry_date"]
            if k in validated_data
        }

        try:
            self.batch_repo.update_batch(batch, updatable_fields, session=self.session)

            AuditService.log_action(
                action="BATCH_UPDATED",
                entity_type="inventory_batch",
                entity_id=batch.id,
                details={
                    "old_values": old_values,
                    "new_values": {k: getattr(batch, k) for k in old_values.keys()}
                },
                organisation_id=org_id,
                session=self.session,
            )

            self.session.commit()
            
            event_bus.publish(
                "BATCH_UPDATED",
                {"batch_id": batch.id, "batch_number": batch.batch_number},
                organisation_id=org_id
            )

            return batch
        except Exception:
            self.session.rollback()
            raise

    @transaction_retry(max_retries=3)
    def delete_batch(self, batch_id, org_id):
        """Delete a batch"""
        batch = self.batch_repo.get_batch(batch_id, org_id)
        if not batch:
            raise NotFoundError("Batch not found")

        batch_id_temp = batch.id
        batch_number = batch.batch_number

        try:
            self.batch_repo.delete_batch(batch, session=self.session)

            AuditService.log_action(
                action="BATCH_DELETED",
                entity_type="inventory_batch",
                entity_id=batch_id_temp,
                details={"batch_number": batch_number},
                organisation_id=org_id,
                session=self.session,
            )

            self.session.commit()
            
            event_bus.publish(
                "BATCH_DELETED",
                {"batch_id": batch_id_temp, "batch_number": batch_number},
                organisation_id=org_id
            )

            return {"message": "Batch deleted successfully"}
        except Exception:
            self.session.rollback()
            raise

    def get_expiring_batches(self, org_id, days=30):
        """Get batches expiring within specified days"""
        return self.batch_repo.get_expiring_batches(org_id, days_until_expiry=days)

    def get_expired_batches(self, org_id):
        """Get all expired batches"""
        return self.batch_repo.get_expired_batches(org_id)

    def batch_stats(self, org_id):
        """Get batch statistics"""
        return self.batch_repo.batch_stats(org_id)
