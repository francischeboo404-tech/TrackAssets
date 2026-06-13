from datetime import datetime
from app import db


class RestockAlert(db.Model):
    """System-generated alerts for low stock or replenishment needs."""

    __tablename__ = "restock_alerts"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False
    )
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"))

    severity = db.Column(
        db.String(20), nullable=False
    )  # LOW, CRITICAL, OUT_OF_STOCK
    status = db.Column(
        db.String(20), default="PENDING"
    )  # PENDING, DISMISSED, ORDERED

    current_quantity = db.Column(db.Integer)
    threshold_level = db.Column(db.Integer)

    message = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    __table_args__ = (
        db.Index("ix_restock_alerts_org_status", "organisation_id", "status"),
        db.Index(
            "ix_restock_alerts_org_severity",
            "organisation_id",
            "severity",
            "status",
        ),
    )

    # item = db.relationship('InventoryItem', backref='restock_alerts', lazy=True)
    warehouse = db.relationship(
        "Warehouse", backref="restock_alerts_ref", lazy=True
    )
