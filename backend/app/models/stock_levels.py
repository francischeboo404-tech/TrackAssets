from datetime import datetime
from app import db


class WarehouseStock(db.Model):
    """Warehouse-specific stock levels and thresholds for inventory items."""

    __tablename__ = "warehouse_stock"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False
    )
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=False
    )

    # Stock quantities
    quantity_on_hand = db.Column(db.Integer, nullable=False, default=0)
    quantity_reserved = db.Column(db.Integer, nullable=False, default=0)

    # Thresholds
    min_stock_level = db.Column(db.Integer, nullable=False, default=0)
    reorder_point = db.Column(db.Integer, nullable=False, default=10)
    safety_stock = db.Column(db.Integer, nullable=False, default=5)
    max_stock_level = db.Column(db.Integer, nullable=False, default=100)

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved

    __table_args__ = (
        db.UniqueConstraint(
            "item_id", "warehouse_id", name="uq_item_warehouse"
        ),
        db.CheckConstraint(
            "quantity_on_hand >= 0", name="ck_warehouse_stock_nonneg"
        ),
        db.CheckConstraint(
            "quantity_reserved >= 0", name="ck_warehouse_reserved_nonneg"
        ),
    )

    # item = db.relationship('InventoryItem', backref='warehouse_levels', lazy=True)
    warehouse = db.relationship("Warehouse", backref="stock_levels", lazy=True)
