from datetime import datetime
from app import db


class ItemInstance(db.Model):
    """Specific physical instance of an inventory item (Serialized Inventory)"""

    __tablename__ = "inventory_item_instances"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False
    )
    serial_number = db.Column(db.String(255), unique=True)
    qr_code_data = db.Column(db.String(500), unique=True, nullable=False)

    # Current location (denormalized for performance, but sync'd with scan events)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    bin_id = db.Column(db.Integer, db.ForeignKey("warehouse_bins.id"))

    status = db.Column(
        db.String(50), default="in_stock"
    )  # in_stock, in_transit, allocated, shipped, lost
    condition = db.Column(db.String(50), default="new")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    item = db.relationship("InventoryItem", backref="instances", lazy=True)
    warehouse = db.relationship("Warehouse", backref="items_here", lazy=True)
    bin = db.relationship("WarehouseBin", backref="items_here", lazy=True)
