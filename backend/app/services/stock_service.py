from app import db
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.models.stock_levels import WarehouseStock
from app.audit_service import AuditService
from app.services.event_bus import event_bus
from datetime import datetime, timezone
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

    def increase_stock(self, item_id, org_id, quantity, warehouse_id=None, reference=None, notes=None, user_id=None, commit=True):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        # Load item with the provided session and lock row for update
        item = (
            self.session.query(InventoryItem).with_for_update().filter_by(id=item_id).first()
        )
        if not item:
            raise ValueError("Inventory item not found")

        before_qty = item.quantity
        item.quantity += quantity

        if warehouse_id:
            wh_stock = (
                self.session.query(WarehouseStock).with_for_update()
                .filter_by(item_id=item_id, warehouse_id=warehouse_id)
                .first()
            )
            if not wh_stock:
                wh_stock = WarehouseStock(item_id=item_id, warehouse_id=warehouse_id, quantity_on_hand=quantity)
                self.session.add(wh_stock)
            else:
                wh_stock.quantity_on_hand += quantity

        # Prevent duplicate posting when a reference is provided
        if reference:
            existing = (
                self.session.query(StockMovement)
                .filter_by(
                    item_id=item_id,
                    organization_id=org_id,
                    reference=reference,
                    quantity=quantity,
                    type=StockMovementType.IN.value,
                )
                .first()
            )
            if existing:
                raise ValueError("Duplicate stock movement detected")

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

        # Rich audit entry with before/after quantities and reference
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

        # Trigger health check (keeps behavior consistent with InventoryItem.add_stock)
        RestockService.evaluate_stock_health(item.id)

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
            event_bus.publish("STOCK_UPDATE", {"item_id": item.id, "movement_type": "IN", "quantity": quantity}, organisation_id=org_id)

        return item

    def decrease_stock(self, item_id, org_id, quantity, warehouse_id=None, reference=None, notes=None, user_id=None, commit=True):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        # Load and lock the item using provided session
        item = (
            self.session.query(InventoryItem).with_for_update().filter_by(id=item_id).first()
        )
        if not item:
            raise ValueError("Inventory item not found")

        if item.quantity < quantity:
            raise ValueError("Insufficient total stock")

        if warehouse_id:
            wh_stock = (
                self.session.query(WarehouseStock).with_for_update()
                .filter_by(item_id=item_id, warehouse_id=warehouse_id)
                .first()
            )
            if not wh_stock or wh_stock.quantity_on_hand < quantity:
                raise ValueError("Insufficient stock in specified warehouse")
            wh_stock.quantity_on_hand -= quantity

        before_qty = item.quantity
        item.quantity -= quantity

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
                raise ValueError("Duplicate stock movement detected")

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

        # Trigger health check (keeps behavior consistent with InventoryItem.remove_stock)
        RestockService.evaluate_stock_health(item.id)

        # Update StockCard and SuppliesLedgerCard for the affected location (OUT movement)
        location_id = warehouse_id
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
            event_bus.publish("STOCK_UPDATE", {"item_id": item.id, "movement_type": "OUT", "quantity": -quantity}, organisation_id=org_id)

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
            raise ValueError("No movements provided")

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
                raise ValueError(f"Inventory item not found: {iid}")

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
                    raise ValueError("Quantity must be greater than 0")

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
                        raise ValueError("Duplicate stock movement detected")

                # Handle IN movement
                if mtype == "IN":
                    before_qty = item.quantity
                    item.quantity += quantity

                    if warehouse_id is not None:
                        wh = wh_map.get((item_id, warehouse_id))
                        if not wh:
                            wh = WarehouseStock(item_id=item_id, warehouse_id=warehouse_id, quantity_on_hand=0)
                            self.session.add(wh)
                            # ensure it's available for later lookups
                            wh_map[(item_id, warehouse_id)] = wh
                        wh.quantity_on_hand += quantity

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
                    before_qty = item.quantity
                    if item.quantity < quantity:
                        raise ValueError("Insufficient total stock")

                    if warehouse_id is not None:
                        wh = wh_map.get((item_id, warehouse_id))
                        if not wh or wh.quantity_on_hand < quantity:
                            raise ValueError("Insufficient stock in specified warehouse")
                        wh.quantity_on_hand -= quantity

                    item.quantity -= quantity

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
                    raise ValueError("Invalid movement type")

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
                
                # Determine cost: use provided unit_cost, fallback to item.unit_price
                cost_to_use = unit_cost if unit_cost is not None else (item.unit_price or 0)
                total_value = qty_on_hand * cost_to_use
                
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

            # All movements processed successfully
            if commit:
                self.session.commit()
                # Publish aggregated event
                event_bus.publish(
                    "STOCK_UPDATE_BATCH",
                    {
                        "count": len(created_movements),
                        "movements": [
                            {
                                "item_id": mv.item_id,
                                "type": mv.type,
                                "quantity": mv.quantity,
                                "warehouse_id": mv.warehouse_id,
                                "reference": mv.reference,
                            }
                            for mv in created_movements
                        ],
                    },
                    organisation_id=org_id,
                )

            return created_movements

        except Exception:
            # Rollback if commit managed here
            if commit:
                try:
                    self.session.rollback()
                except Exception:
                    pass
            raise
