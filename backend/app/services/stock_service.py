from app import db
from app.errors import ValidationError, NotFoundError
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.models.stock_levels import WarehouseStock
from app.audit_service import AuditService
from app.services.event_bus import event_bus
from datetime import datetime, timezone
from sqlalchemy import func
from app.services.restock_service import RestockService
from app.models import StockCard, SuppliesLedgerCard


class StockService:
    """Centralized stock mutation helper.

    This is a lightweight skeleton for Phase 3. It provides atomic
    increase/decrease operations and ensures movements, warehouse levels,
    audit logs, and events are written consistently. Callers may pass an
    explicit session if they want the operation to be part of a larger
    transactional unit.
    """

    def __init__(self, session=None):
        self.session = session or db.session


    def get_current_quantity(self, item_id: int) -> int:
        """Return the current stock total derived from warehouse stock rows."""
        total_quantity = (
            self.session.query(
                func.coalesce(func.sum(WarehouseStock.quantity_on_hand), 0)
            )
            .filter(WarehouseStock.item_id == item_id)
            .scalar()
        )

        if int(total_quantity or 0) == 0:
            warehouse_row_count = (
                self.session.query(func.count(WarehouseStock.id))
                .filter(WarehouseStock.item_id == item_id)
                .scalar()
            )
            if warehouse_row_count == 0:
                item = (
                    self.session.query(InventoryItem)
                    .filter_by(id=item_id)
                    .first()
                )
                if item:
                    return int(item.quantity or 0)

        return int(total_quantity or 0)

    def get_warehouse_stock(self, item_id: int, warehouse_id: int, create_if_missing: bool = False):
        if warehouse_id is None:
            return None
        wh_stock = (
            self.session.query(WarehouseStock)
            .with_for_update()
            .filter_by(item_id=item_id, warehouse_id=warehouse_id)
            .first()
        )
        if wh_stock is None and create_if_missing:
            wh_stock = WarehouseStock(
                item_id=item_id,
                warehouse_id=warehouse_id,
                quantity_on_hand=0,
                quantity_reserved=0,
            )
            self.session.add(wh_stock)
        return wh_stock

    def get_warehouse_available(self, item_id: int, warehouse_id: int) -> int:
        wh_stock = (
            self.session.query(WarehouseStock)
            .filter_by(item_id=item_id, warehouse_id=warehouse_id)
            .first()
        )
        if not wh_stock:
            return 0
        return wh_stock.quantity_on_hand - wh_stock.quantity_reserved

    def _recalculate_item_quantity(self, item_id: int):
        """
        Synchronize InventoryItem.quantity with WarehouseStock.

        WarehouseStock is the single source of truth.

        This method:
        - never commits
        - never creates stock movements
        - never publishes events
        - never writes audit logs

        It ONLY synchronizes the cached aggregate quantity.
        """

        item = (
            self.session.query(InventoryItem)
            .with_for_update()
            .filter_by(id=item_id)
            .first()
        )

        if item is None:
            raise NotFoundError(f"Inventory item {item_id} does not exist.")

        item.quantity = self.get_current_quantity(item_id)
        self.session.flush()

        return item.quantity

    def increase_stock(self, item_id, org_id, quantity, warehouse_id=None, reference=None, notes=None, user_id=None, module=None, commit=True, destination_warehouse_id=None):
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        # Load item with the provided session and lock row for update
        item = (
            self.session.query(InventoryItem).with_for_update().filter_by(id=item_id).first()
        )
        if not item:
            raise NotFoundError("Inventory item not found")

        before_qty = self.get_current_quantity(item.id)

        if warehouse_id is not None:
            wh_stock = (
                self.session.query(WarehouseStock).with_for_update()
                .filter_by(item_id=item_id, warehouse_id=warehouse_id)
                .first()
            )
            if not wh_stock:
                wh_stock = WarehouseStock(
                    item_id=item_id,
                    warehouse_id=warehouse_id,
                    quantity_on_hand=quantity,
                    quantity_reserved=0,
                )
                self.session.add(wh_stock)
            else:
                wh_stock.quantity_on_hand += quantity

            # Recalculate item-level quantity from warehouse totals when using warehouse stock
            self._recalculate_item_quantity(item.id)
        else:
            # Legacy support for stock movements without a warehouse context.
            item.quantity += quantity
            self.session.flush()

        self.session.flush()


        
        after_qty = self.get_current_quantity(item.id)

        # Prevent duplicate posting when a reference is provided
        if reference:
            existing = (
                self.session.query(StockMovement)
                .filter_by(
                    item_id=item_id,
                    organization_id=org_id,
                    warehouse_id=warehouse_id,
                    reference=reference,
                    quantity=quantity,
                    type=StockMovementType.IN.value,
                )
                .first()
            )
            if existing:
                raise ValidationError("Duplicate stock movement detected")

        movement = StockMovement(
            item_id=item.id,
            organization_id=org_id,
            type=StockMovementType.IN.value,
            quantity=quantity,
            before_quantity=before_qty,
            after_quantity=after_qty,
            warehouse_id=warehouse_id,
            destination_warehouse_id=destination_warehouse_id,
            reference=reference,
            notes=notes,
            date=datetime.now(timezone.utc),
        )
        if user_id:
            movement.created_by = user_id
        self.session.add(movement)

        # Rich audit entry with before/after quantities and reference
        AuditService.log_action(
            action="STOCK_INCREASED",
            entity_type="inventory_item",
            entity_id=item.id,
            details={
                "previous_quantity": before_qty,
                "new_quantity": after_qty,
                "previous_value": before_qty,
                "new_value": after_qty,
                "quantity_change": quantity,
                "warehouse_id": warehouse_id,
                "reference": reference,
                "notes": notes,
            },
            user_id=user_id,
            organisation_id=org_id,
            module=module or "inventory",
            session=self.session,
        )

        # Update StockCard and SuppliesLedgerCard for the affected location
        location_id = warehouse_id
        # Determine accurate quantity_on_hand (warehouse-level if provided)
        if location_id:
            wh = (
                self.session.query(WarehouseStock).with_for_update()
                .filter_by(item_id=item_id, warehouse_id=location_id)
                .first()
            )
            qty_on_hand = wh.quantity_on_hand if wh else item.quantity
        else:
            qty_on_hand = item.quantity

        stock_card = (
            self.session.query(StockCard).with_for_update()
            .filter_by(organization_id=org_id, item_id=item_id, location_id=location_id)
            .first()
        )
        if not stock_card:
            stock_card = StockCard(
                organization_id=org_id,
                item_id=item_id,
                location_id=location_id,
                stock_card_number=f"SC-{org_id}-{item_id}-{location_id or 'G'}",
                quantity_on_hand=qty_on_hand,
                last_received_date=(datetime.now(timezone.utc) if quantity > 0 else None),
            )
            self.session.add(stock_card)
        else:
            stock_card.quantity_on_hand = qty_on_hand
            if quantity > 0:
                stock_card.last_received_date = datetime.now(timezone.utc)
        ledger = (
            self.session.query(SuppliesLedgerCard).with_for_update()
            .filter_by(organization_id=org_id, item_id=item_id, location_id=location_id)
            .first()
        )
        total_value = (qty_on_hand * (item.unit_price or 0))
        if not ledger:
            ledger = SuppliesLedgerCard(
                organization_id=org_id,
                item_id=item_id,
                location_id=location_id,
                ledger_number=f"SL-{org_id}-{item_id}-{location_id or 'G'}",
                quantity_on_hand=qty_on_hand,
                total_value=total_value,
                last_received_date=(datetime.now(timezone.utc) if quantity > 0 else None),
            )
            self.session.add(ledger)
        else:
            ledger.quantity_on_hand = qty_on_hand
            ledger.total_value = total_value
            if quantity > 0:
                ledger.last_received_date = datetime.now(timezone.utc)

        if commit:
            self.session.commit()
            # Health check runs AFTER commit so it doesn't open a nested transaction
            RestockService.evaluate_stock_health(item.id)
            event_bus.publish("STOCK_UPDATE", {"item_id": item.id, "movement_type": "IN", "quantity": quantity}, organisation_id=org_id)
            from app.services.report_analytics_service import ReportAnalyticsService
            ReportAnalyticsService.invalidate_cache(org_id)

        return item

    def decrease_stock(self, item_id, org_id, quantity, warehouse_id=None, reference=None, notes=None, user_id=None, module=None, commit=True, destination_warehouse_id=None):
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        # Load and lock the item using provided session
        item = (
            self.session.query(InventoryItem).with_for_update().filter_by(id=item_id).first()
        )
        if not item:
            raise NotFoundError("Inventory item not found")

        self._recalculate_item_quantity(item.id)
        self.session.flush()

        before_qty = self.get_current_quantity(item.id)

        if before_qty < quantity:
            raise ValidationError("Insufficient total stock")

        if warehouse_id is not None:
            wh_stock = self.get_warehouse_stock(item_id, warehouse_id, create_if_missing=False)
            if not wh_stock:
                raise ValidationError("No stock exists in the specified warehouse")

            available_qty = wh_stock.quantity_on_hand - wh_stock.quantity_reserved
            if available_qty < quantity:
                raise ValidationError(
                    "Insufficient available stock in the specified warehouse"
                )

            wh_stock.quantity_on_hand -= quantity
            self._recalculate_item_quantity(item.id)
            self.session.flush()
        else:
            # No warehouse specified — deduct from item quantity directly
            item.quantity = max(0, item.quantity - quantity)
            self.session.flush()

        after_qty = self.get_current_quantity(item.id)

        # Prevent duplicate posting when a reference is provided
        if reference:
            existing = (
                self.session.query(StockMovement)
                .filter_by(
                    item_id=item_id,
                    organization_id=org_id,
                    warehouse_id=warehouse_id,
                    reference=reference,
                    quantity=quantity,
                    type=StockMovementType.OUT.value,
                )
                .first()
            )
            if existing:
                raise ValidationError("Duplicate stock movement detected")

        movement = StockMovement(
            item_id=item.id,
            organization_id=org_id,
            type=StockMovementType.OUT.value,
            quantity=quantity,
            before_quantity=before_qty,
            after_quantity=after_qty,
            warehouse_id=warehouse_id,
            destination_warehouse_id=destination_warehouse_id,
            reference=reference,
            notes=notes,
            date=datetime.now(timezone.utc),
        )
        if user_id:
            movement.created_by = user_id
        self.session.add(movement)

        AuditService.log_action(
            action="STOCK_DECREASED",
            entity_type="inventory_item",
            entity_id=item.id,
            details={
                "previous_quantity": before_qty,
                "new_quantity": after_qty,
                "previous_value": before_qty,
                "new_value": after_qty,
                "quantity_change": -quantity,
                "warehouse_id": warehouse_id,
                "reference": reference,
                "notes": notes,
            },
            user_id=user_id,
            organisation_id=org_id,
            module=module or "inventory",
            session=self.session,
        )

        # Update StockCard and SuppliesLedgerCard for the affected location (OUT movement)
        location_id = warehouse_id
        if location_id is not None:
            wh = (
                self.session.query(WarehouseStock).with_for_update()
                .filter_by(item_id=item_id, warehouse_id=location_id)
                .first()
            )
            qty_on_hand = wh.quantity_on_hand if wh else 0
        else:
            qty_on_hand = item.quantity

        stock_card = (
            self.session.query(StockCard).with_for_update()
            .filter_by(organization_id=org_id, item_id=item_id, location_id=location_id)
            .first()
        )
        if not stock_card:
            stock_card = StockCard(
                organization_id=org_id,
                item_id=item_id,
                location_id=location_id,
                stock_card_number=f"SC-{org_id}-{item_id}-{location_id or 'G'}",
                quantity_on_hand=qty_on_hand,
                last_issued_date=(datetime.now(timezone.utc) if quantity > 0 else None),
            )
            self.session.add(stock_card)
        else:
            stock_card.quantity_on_hand = qty_on_hand
            if quantity > 0:
                stock_card.last_issued_date = datetime.now(timezone.utc)

        ledger = (
            self.session.query(SuppliesLedgerCard).with_for_update()
            .filter_by(organization_id=org_id, item_id=item_id, location_id=location_id)
            .first()
        )
        total_value = (qty_on_hand * (item.unit_price or 0))
        if not ledger:
            ledger = SuppliesLedgerCard(
                organization_id=org_id,
                item_id=item_id,
                location_id=location_id,
                ledger_number=f"SL-{org_id}-{item_id}-{location_id or 'G'}",
                quantity_on_hand=qty_on_hand,
                total_value=total_value,
                last_issued_date=(datetime.now(timezone.utc) if quantity > 0 else None),
            )
            self.session.add(ledger)
        else:
            ledger.quantity_on_hand = qty_on_hand
            ledger.total_value = total_value
            if quantity > 0:
                ledger.last_issued_date = datetime.now(timezone.utc)

        if commit:
            self.session.commit()
            # Health check runs AFTER commit so it doesn't open a nested transaction
            RestockService.evaluate_stock_health(item.id)
            event_bus.publish("STOCK_UPDATE", {"item_id": item.id, "movement_type": "OUT", "quantity": -quantity}, organisation_id=org_id)
            from app.services.report_analytics_service import ReportAnalyticsService
            ReportAnalyticsService.invalidate_cache(org_id)
        return item

    def apply_batch(self, org_id, movements, user_id=None, commit=True):
        """Apply a batch of stock movements atomically.

        movements: list of dicts with keys:
          - item_id (int)
          - type ("IN"|"OUT")
          - quantity (numeric)
          - warehouse_id (optional)
          - reference (optional)
          - notes (optional)

        The operation locks involved rows, validates availability, writes
        StockMovement rows, updates WarehouseStock and InventoryItem
        quantities, updates StockCard/SuppliesLedgerCard and emits a single
        aggregated event after commit.
        """
        if not movements or not isinstance(movements, (list, tuple)):
            raise ValidationError("No movements provided")

        # Collect unique item ids and warehouse ids to lock deterministically
        item_ids = sorted({int(m.get("item_id")) for m in movements})
        warehouse_ids = sorted({m.get("warehouse_id") for m in movements if m.get("warehouse_id") is not None})

        # Lock all affected inventory items
        items = (
            self.session.query(InventoryItem).with_for_update()
            .filter(InventoryItem.id.in_(item_ids))
            .all()
        )
        item_map = {i.id: i for i in items}
        for iid in item_ids:
            if iid not in item_map:
                raise NotFoundError(f"Inventory item not found: {iid}")

        # Lock existing warehouse stocks for affected items/warehouses
        wh_map = {}
        if warehouse_ids:
            whs = (
                self.session.query(WarehouseStock).with_for_update()
                .filter(WarehouseStock.item_id.in_(item_ids), WarehouseStock.warehouse_id.in_(warehouse_ids))
                .all()
            )
            wh_map = {(w.item_id, w.warehouse_id): w for w in whs}

        created_movements = []
        try:
            for m in movements:
                item_id = int(m.get("item_id"))
                mtype = m.get("type")
                quantity = m.get("quantity")
                warehouse_id = m.get("warehouse_id")
                reference = m.get("reference")
                notes = m.get("notes")
                unit_cost = m.get("unit_cost")

                if quantity is None or quantity <= 0:
                    raise ValidationError("Quantity must be greater than 0")

                item = item_map[item_id]

                # Duplicate detection when reference provided
                if reference:
                    existing = (
                        self.session.query(StockMovement)
                        .filter_by(
                            item_id=item_id,
                            organization_id=org_id,
                            reference=reference,
                            quantity=quantity,
                            type=(StockMovementType.IN.value if mtype == "IN" else StockMovementType.OUT.value),
                            warehouse_id=warehouse_id,
                        )
                        .first()
                    )
                    if existing:
                        raise ValidationError("Duplicate stock movement detected")

                # Use authoritative current quantity when calculating before/after values
                before_qty = self.get_current_quantity(item.id)
                if warehouse_id is None:
                    item.quantity = before_qty

                # Handle IN movement
                if mtype == "IN":
                    if warehouse_id is None:
                        item.quantity = before_qty + quantity
                    else:
                        item.quantity += quantity

                    if warehouse_id is not None:
                        wh = wh_map.get((item_id, warehouse_id))
                        if not wh:
                            wh = WarehouseStock(item_id=item_id, warehouse_id=warehouse_id, quantity_on_hand=0)
                            self.session.add(wh)
                            # ensure it's available for later lookups
                            wh_map[(item_id, warehouse_id)] = wh
                        wh.quantity_on_hand += quantity
                        item.quantity = self._recalculate_item_quantity(item.id)

                    movement = StockMovement(
                        item_id=item.id,
                        organization_id=org_id,
                        type=StockMovementType.IN.value,
                        quantity=quantity,
                        before_quantity=before_qty,
                        after_quantity=item.quantity,
                        warehouse_id=warehouse_id,
                        reference=reference,
                        notes=notes,
                        date=datetime.now(timezone.utc),
                    )
                    if user_id:
                        movement.created_by = user_id
                    self.session.add(movement)
                    created_movements.append(movement)

                    AuditService.log_action(
                        action="STOCK_INCREASED",
                        entity_type="inventory_item",
                        entity_id=item.id,
                        details={
                            "previous_quantity": before_qty,
                            "new_quantity": item.quantity,
                            "quantity_change": quantity,
                            "warehouse_id": warehouse_id,
                            "reference": reference,
                            "notes": notes,
                        },
                        user_id=user_id,
                        organisation_id=org_id,
                        session=self.session,
                    )

                    RestockService.evaluate_stock_health(item.id)

                # Handle OUT movement
                elif mtype == "OUT":
                    if before_qty < quantity:
                        raise ValidationError("Insufficient total stock")

                    if warehouse_id is not None:
                        wh = wh_map.get((item_id, warehouse_id))
                        if not wh or wh.quantity_on_hand < quantity:
                            raise ValidationError("Insufficient stock in specified warehouse")
                        wh.quantity_on_hand -= quantity
                        item.quantity = self._recalculate_item_quantity(item.id)
                    else:
                        item.quantity = before_qty - quantity

                    movement = StockMovement(
                        item_id=item.id,
                        organization_id=org_id,
                        type=StockMovementType.OUT.value,
                        quantity=quantity,
                        before_quantity=before_qty,
                        after_quantity=item.quantity,
                        warehouse_id=warehouse_id,
                        reference=reference,
                        notes=notes,
                        date=datetime.now(timezone.utc),
                    )
                    if user_id:
                        movement.created_by = user_id
                    self.session.add(movement)
                    created_movements.append(movement)

                    AuditService.log_action(
                        action="STOCK_DECREASED",
                        entity_type="inventory_item",
                        entity_id=item.id,
                        details={
                            "previous_quantity": before_qty,
                            "new_quantity": item.quantity,
                            "quantity_change": -quantity,
                            "warehouse_id": warehouse_id,
                            "reference": reference,
                            "notes": notes,
                        },
                        user_id=user_id,
                        organisation_id=org_id,
                        session=self.session,
                    )

                    RestockService.evaluate_stock_health(item.id)

                else:
                    raise ValidationError("Invalid movement type")

                # Update StockCard and SuppliesLedgerCard for the affected location
                location_id = warehouse_id
                if location_id is not None:
                    wh = (
                        self.session.query(WarehouseStock).with_for_update()
                        .filter_by(item_id=item_id, warehouse_id=location_id)
                        .first()
                    )
                    qty_on_hand = wh.quantity_on_hand if wh else item.quantity
                else:
                    qty_on_hand = item.quantity

                stock_card = (
                    self.session.query(StockCard).with_for_update()
                    .filter_by(organization_id=org_id, item_id=item_id, location_id=location_id)
                    .first()
                )
                if not stock_card:
                    stock_card = StockCard(
                        organization_id=org_id,
                        item_id=item_id,
                        location_id=location_id,
                        stock_card_number=f"SC-{org_id}-{item_id}-{location_id or 'G'}",
                        quantity_on_hand=qty_on_hand,
                    )
                    # Set last_received/issued appropriately
                    if mtype == "IN":
                        stock_card.last_received_date = datetime.now(timezone.utc)
                    else:
                        stock_card.last_issued_date = datetime.now(timezone.utc)
                    self.session.add(stock_card)
                else:
                    stock_card.quantity_on_hand = qty_on_hand
                    if mtype == "IN":
                        stock_card.last_received_date = datetime.now(timezone.utc)
                    else:
                        stock_card.last_issued_date = datetime.now(timezone.utc)

                ledger = (
                    self.session.query(SuppliesLedgerCard).with_for_update()
                    .filter_by(organization_id=org_id, item_id=item_id, location_id=location_id)
                    .first()
                )
                total_value = qty_on_hand * (item.unit_price or 0)
                if not ledger:
                    ledger = SuppliesLedgerCard(
                        organization_id=org_id,
                        item_id=item_id,
                        location_id=location_id,
                        ledger_number=f"SL-{org_id}-{item_id}-{location_id or 'G'}",
                        quantity_on_hand=qty_on_hand,
                        total_value=total_value,
                    )
                    if mtype == "IN":
                        ledger.last_received_date = datetime.now(timezone.utc)
                    else:
                        ledger.last_issued_date = datetime.now(timezone.utc)
                    self.session.add(ledger)
                else:
                    ledger.quantity_on_hand = qty_on_hand
                    ledger.total_value = total_value
                    if mtype == "IN":
                        ledger.last_received_date = datetime.now(timezone.utc)
                    else:
                        ledger.last_issued_date = datetime.now(timezone.utc)

        except Exception as e:
            if commit:
                self.session.rollback()
            raise

        if commit:
            self.session.commit()
            event_bus.publish(
                "BATCH_STOCK_UPDATE",
                {"count": len(created_movements), "org_id": org_id},
                organisation_id=org_id
            )

        return created_movements

    def transfer_with_hierarchy(
        self,
        item_id: int,
        org_id: int,
        quantity: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        user_id: int = None,
        reference: str = None,
        notes: str = None,
        commit: bool = True
    ):
        """
        Transfer stock between warehouses enforcing hierarchy rules.
        
        Business Rules (SAP-like):
        - Main warehouse can transfer to any child directly
        - Child can transfer to parent (main warehouse)
        - Child cannot transfer directly to another child (must go through parent)
        
        This method:
        1. Validates warehouse hierarchy relationship
        2. Decreases stock at source warehouse
        3. Increases stock at destination warehouse
        4. Creates audit trail
        5. Updates stock cards and ledgers
        """
        from app.services.warehouse_hierarchy_service import WarehouseHierarchyService
        from app.models.location_topology import Warehouse
        
        # Validate transfer is allowed by hierarchy
        WarehouseHierarchyService.validate_transfer_path(
            from_warehouse_id, to_warehouse_id, org_id
        )
        
        # Get source warehouse stock
        source_stock = (
            self.session.query(WarehouseStock)
            .with_for_update()
            .filter_by(item_id=item_id, warehouse_id=from_warehouse_id)
            .first()
        )
        
        if not source_stock or source_stock.quantity_on_hand < quantity:
            raise ValidationError(
                f"Insufficient stock in source warehouse. Available: {source_stock.quantity_on_hand if source_stock else 0}, Requested: {quantity}"
            )
        
        # Get or create destination warehouse stock
        dest_stock = (
            self.session.query(WarehouseStock)
            .with_for_update()
            .filter_by(item_id=item_id, warehouse_id=to_warehouse_id)
            .first()
        )
        
        if not dest_stock:
            dest_stock = WarehouseStock(
                item_id=item_id,
                warehouse_id=to_warehouse_id,
                quantity_on_hand=0,
                quantity_reserved=0
            )
            self.session.add(dest_stock)
        
        # Get item and capture before state
        item = (
            self.session.query(InventoryItem)
            .with_for_update()
            .filter_by(id=item_id)
            .first()
        )
        
        if not item:
            raise NotFoundError("Inventory item not found")
        
        before_qty = self.get_current_quantity(item_id)
        before_source = source_stock.quantity_on_hand
        before_dest = dest_stock.quantity_on_hand
        
        # Perform transfer
        source_stock.quantity_on_hand -= quantity
        dest_stock.quantity_on_hand += quantity
        
        # Recalculate global quantity
        self._recalculate_item_quantity(item_id)
        self.session.flush()
        
        after_qty = self.get_current_quantity(item_id)
        
        # Create outbound movement record
        out_movement = StockMovement(
            item_id=item_id,
            organization_id=org_id,
            type=StockMovementType.OUT.value,
            quantity=quantity,
            before_quantity=before_qty,
            after_quantity=after_qty,
            warehouse_id=from_warehouse_id,
            destination_warehouse_id=to_warehouse_id,
            reference=reference,
            notes=notes or f"Transfer to warehouse {to_warehouse_id}",
            date=datetime.now(timezone.utc)
        )
        
        if user_id:
            out_movement.created_by = user_id
        
        self.session.add(out_movement)
        
        # Create inbound movement record
        in_movement = StockMovement(
            item_id=item_id,
            organization_id=org_id,
            type=StockMovementType.IN.value,
            quantity=quantity,
            before_quantity=before_qty,
            after_quantity=after_qty,
            warehouse_id=to_warehouse_id,
            destination_warehouse_id=from_warehouse_id,
            reference=reference,
            notes=notes or f"Receipt from warehouse {from_warehouse_id}",
            date=datetime.now(timezone.utc)
        )
        
        if user_id:
            in_movement.created_by = user_id
        
        self.session.add(in_movement)
        
        # Audit log
        source_wh = self.session.query(Warehouse).filter_by(id=from_warehouse_id).first()
        dest_wh = self.session.query(Warehouse).filter_by(id=to_warehouse_id).first()
        
        AuditService.log_action(
            action="STOCK_TRANSFERRED_BETWEEN_WAREHOUSES",
            entity_type="inventory_item",
            entity_id=item_id,
            details={
                "item_name": item.name,
                "item_sku": item.sku,
                "quantity": quantity,
                "from_warehouse_id": from_warehouse_id,
                "from_warehouse_name": source_wh.name if source_wh else "Unknown",
                "from_previous_quantity": before_source,
                "from_new_quantity": source_stock.quantity_on_hand,
                "to_warehouse_id": to_warehouse_id,
                "to_warehouse_name": dest_wh.name if dest_wh else "Unknown",
                "to_previous_quantity": before_dest,
                "to_new_quantity": dest_stock.quantity_on_hand,
                "reference": reference,
                "notes": notes
            },
            user_id=user_id,
            organisation_id=org_id,
            session=self.session
        )
        
        # Update stock cards for both locations
        for location_id in [from_warehouse_id, to_warehouse_id]:
            wh = (
                self.session.query(WarehouseStock)
                .filter_by(item_id=item_id, warehouse_id=location_id)
                .first()
            )
            qty_on_hand = wh.quantity_on_hand if wh else 0
            
            stock_card = (
                self.session.query(StockCard)
                .with_for_update()
                .filter_by(organization_id=org_id, item_id=item_id, location_id=location_id)
                .first()
            )
            
            if not stock_card:
                stock_card = StockCard(
                    organization_id=org_id,
                    item_id=item_id,
                    location_id=location_id,
                    stock_card_number=f"SC-{org_id}-{item_id}-{location_id}",
                    quantity_on_hand=qty_on_hand
                )
                if location_id == to_warehouse_id:
                    stock_card.last_received_date = datetime.now(timezone.utc)
                else:
                    stock_card.last_issued_date = datetime.now(timezone.utc)
                self.session.add(stock_card)
            else:
                stock_card.quantity_on_hand = qty_on_hand
                if location_id == to_warehouse_id:
                    stock_card.last_received_date = datetime.now(timezone.utc)
                else:
                    stock_card.last_issued_date = datetime.now(timezone.utc)
            
            # Update supplies ledger
            ledger = (
                self.session.query(SuppliesLedgerCard)
                .with_for_update()
                .filter_by(organization_id=org_id, item_id=item_id, location_id=location_id)
                .first()
            )
            
            total_value = qty_on_hand * (item.unit_price or 0)
            
            if not ledger:
                ledger = SuppliesLedgerCard(
                    organization_id=org_id,
                    item_id=item_id,
                    location_id=location_id,
                    ledger_number=f"SL-{org_id}-{item_id}-{location_id}",
                    quantity_on_hand=qty_on_hand,
                    total_value=total_value
                )
                if location_id == to_warehouse_id:
                    ledger.last_received_date = datetime.now(timezone.utc)
                else:
                    ledger.last_issued_date = datetime.now(timezone.utc)
                self.session.add(ledger)
            else:
                ledger.quantity_on_hand = qty_on_hand
                ledger.total_value = total_value
                if location_id == to_warehouse_id:
                    ledger.last_received_date = datetime.now(timezone.utc)
                else:
                    ledger.last_issued_date = datetime.now(timezone.utc)
        
        if commit:
            self.session.commit()
            RestockService.evaluate_stock_health(item_id)
            event_bus.publish(
                "STOCK_TRANSFERRED",
                {
                    "item_id": item_id,
                    "from_warehouse_id": from_warehouse_id,
                    "to_warehouse_id": to_warehouse_id,
                    "quantity": quantity
                },
                organisation_id=org_id
            )
        
        return {
            "item_id": item_id,
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id,
            "quantity": quantity,
            "status": "transferred"
        }
