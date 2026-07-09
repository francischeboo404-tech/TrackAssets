from datetime import datetime
from enum import Enum

from app import db
from app.db_utils import transaction_retry


class StockMovementType(Enum):
    """Stock movement type enumeration"""

    IN = "IN"
    OUT = "OUT"


class InventoryItem(db.Model):
    """Inventory item model for consumable inventory"""

    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(100))
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=10)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    unit = db.Column(db.String(50))
    # Extended master-data for procurement & traceability
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    item_type = db.Column(db.String(50), default='consumable')  # consumable|asset|raw|finished|service
    status = db.Column(db.String(50), default='active')
    preferred_supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    supplier_item_reference = db.Column(db.String(255), nullable=True)
    purchase_cost = db.Column(db.Numeric(12,2), nullable=True)
    last_purchase_cost = db.Column(db.Numeric(12,2), nullable=True)
    tax_category = db.Column(db.String(100), nullable=True)
    lead_time_days = db.Column(db.Integer, nullable=True)
    # Inventory control fields (item-level defaults; warehouse-level overrides exist in WarehouseStock)
    min_stock_level = db.Column(db.Integer, nullable=True)
    max_stock_level = db.Column(db.Integer, nullable=True)
    safety_stock = db.Column(db.Integer, nullable=True)
    opening_stock = db.Column(db.Integer, nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    # Traceability flags
    batch_tracking = db.Column(db.Boolean, default=False)
    serial_tracking = db.Column(db.Boolean, default=False)
    expiry_tracking = db.Column(db.Boolean, default=False)
    qr_code_data = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "organisation_id", "sku", name="uq_inventory_org_sku"
        ),
        db.CheckConstraint(
            "quantity >= 0", name="ck_inventory_quantity_nonneg"
        ),
        db.CheckConstraint(
            "reorder_level >= 0", name="ck_inventory_reorder_nonneg"
        ),
        db.Index("ix_inventory_org_id", "organisation_id"),
        db.Index("ix_inventory_sku", "sku"),
        db.Index("ix_inventory_active", "is_active"),
        db.Index(
            "ix_inventory_low_stock_query",
            "organisation_id",
            "is_active",
            "quantity",
            "reorder_level",
        ),
    )

    stock_movements = db.relationship(
        "StockMovement",
        backref="inventory_item",
        lazy=True,
        cascade="all, delete-orphan",
    )

    # Cascade delete for warehouse levels and alerts
    warehouse_stocks = db.relationship(
        "WarehouseStock",
        backref="item",
        lazy=True,
        cascade="all, delete-orphan",
    )

    restock_alerts = db.relationship(
        "RestockAlert", backref="item", lazy=True, cascade="all, delete-orphan"
    )

    batches = db.relationship(
        "InventoryBatch", backref="item_ref", lazy=True, cascade="all, delete-orphan"
    )

    @transaction_retry(max_retries=3)
    def add_stock(self, quantity, warehouse_id=None, reference=None, notes=None):
        """Add stock (IN movement) with row-level locking and warehouse sync"""
        if quantity <= 0:
            from app.errors import ValidationError
            raise ValidationError("Quantity must be greater than 0")

        # Reload with lock
        item = InventoryItem.query.with_for_update().get(self.id)
        item.quantity += quantity

        # Update Warehouse Stock if provided
        if warehouse_id:
            from app.models.stock_levels import WarehouseStock
            wh_stock = WarehouseStock.query.with_for_update().filter_by(
                item_id=self.id, warehouse_id=warehouse_id
            ).first()
            
            if not wh_stock:
                wh_stock = WarehouseStock(
                    item_id=self.id,
                    warehouse_id=warehouse_id,
                    quantity_on_hand=quantity
                )
                db.session.add(wh_stock)
            else:
                wh_stock.quantity_on_hand += quantity

        movement = StockMovement(
            item_id=self.id,
            type=StockMovementType.IN.value,
            quantity=quantity,
            reference=reference,
            notes=notes,
            date=db.func.now(),
        )
        db.session.add(movement)

        # Trigger health check
        from app.services.restock_service import RestockService
        RestockService.evaluate_stock_health(self.id)

    @transaction_retry(max_retries=3)
    def remove_stock(self, quantity, warehouse_id=None, reference=None, notes=None):
        """Remove stock (OUT movement) with row-level locking and warehouse sync"""
        if quantity <= 0:
            from app.errors import ValidationError
            raise ValidationError("Quantity must be greater than 0")

        # Reload with lock
        item = InventoryItem.query.with_for_update().get(self.id)
        if item.quantity < quantity:
            from app.errors import ValidationError
            raise ValidationError("Insufficient total stock")

        # Update Warehouse Stock if provided
        
        if warehouse_id:
            from app.models.stock_levels import WarehouseStock
            from flask import current_app

            current_app.logger.debug(
                "remove_stock: warehouse=%s item=%s qty=%s",
                warehouse_id, self.id, quantity,
            )

            wh_stock = WarehouseStock.query.with_for_update().filter_by(
                item_id=self.id, warehouse_id=warehouse_id
            ).first()

            if wh_stock:
                current_app.logger.debug(
                    "remove_stock: on_hand=%s reserved=%s available=%s",
                    wh_stock.quantity_on_hand,
                    wh_stock.quantity_reserved,
                    wh_stock.quantity_available,
                )

            if not wh_stock or wh_stock.quantity_on_hand < quantity:
                from app.errors import ValidationError
                raise ValidationError("Insufficient stock in specified warehouse")

            wh_stock.quantity_on_hand -= quantity

        item.quantity -= quantity
        movement = StockMovement(
            item_id=self.id,
            type=StockMovementType.OUT.value,
            quantity=quantity,
            reference=reference,
            notes=notes,
            date=db.func.now(),
        )
        db.session.add(movement)

        # Trigger health check
        from app.services.restock_service import RestockService
        RestockService.evaluate_stock_health(self.id)

    def is_low_stock(self):
        """Check if stock is below reorder level"""
        return self.quantity < self.reorder_level

    def __repr__(self):
        return f"<InventoryItem {self.name}>"


class InventoryBatch(db.Model):
    """Batch records for traceability and expiry management"""

    __tablename__ = 'inventory_batches'

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    batch_number = db.Column(db.String(200), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    received_date = db.Column(db.DateTime, nullable=True)
    manufacture_date = db.Column(db.DateTime, nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    status = db.Column(db.String(50), default='available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organisation_id', 'item_id', 'batch_number', name='uq_batch_org_item_number'),
        db.CheckConstraint('quantity >= 0', name='ck_batch_quantity_nonneg'),
        db.Index('ix_inventory_batches_org_item', 'organisation_id', 'item_id'),
        db.Index('ix_inventory_batches_batch_number', 'batch_number'),
        db.Index('ix_inventory_batches_expiry', 'expiry_date'),
        db.Index('ix_inventory_batches_status', 'status'),
    )

    warehouse = db.relationship('Warehouse', backref='batches', lazy=True)
    supplier = db.relationship('Supplier', backref='batches', lazy=True)

    def is_expired(self):
        """Check if batch is expired"""
        if not self.expiry_date:
            return False
        return datetime.utcnow() > self.expiry_date

    def __repr__(self):
        return f"<InventoryBatch {self.batch_number}>"


class StockMovement(db.Model):
    """Stock movement log for inventory tracking"""

    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False
    )
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=True
    )
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=True
    )
    type = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    before_quantity = db.Column(db.Integer, nullable=True)
    after_quantity = db.Column(db.Integer, nullable=True)
    reference = db.Column(db.String(255))
    notes = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    # destination_warehouse_id: set when an OUT movement is a warehouse transfer
    destination_warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)


    __table_args__ = (
        db.CheckConstraint(
            "type IN ('IN', 'OUT')", name="ck_stock_movement_type"
        ),
        db.CheckConstraint(
            "quantity > 0", name="ck_stock_movement_qty_positive"
        ),
        db.Index("ix_stock_movements_item_id", "item_id"),
        db.Index("ix_stock_movements_org_id", "organization_id"),
        db.Index("ix_stock_movements_type", "type"),
        db.Index("ix_stock_movements_date", "date"),
        db.Index("ix_stock_movements_item_date", "item_id", "date"),
        db.Index("ix_stock_movements_org_date", "organization_id", "date"),
    )

    def __repr__(self):
        return f"<StockMovement {self.item_id} - {self.type}>"


class AuditLog(db.Model):
    """General audit log for system-wide actions"""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # warehouse_id: nullable FK enabling per-warehouse audit trail filtering
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=True
    )
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(100))
    entity_id = db.Column(db.Integer)
    reference = db.Column(db.String(255), nullable=True)
    module = db.Column(db.String(100), nullable=True)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index("ix_audit_logs_org_id", "organisation_id"),
        db.Index("ix_audit_logs_user_id", "user_id"),
        db.Index("ix_audit_logs_warehouse_id", "warehouse_id"),
        db.Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        db.Index("ix_audit_logs_action", "action"),
        db.Index("ix_audit_logs_module", "module"),
        db.Index("ix_audit_logs_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} - {self.entity_type}>"
