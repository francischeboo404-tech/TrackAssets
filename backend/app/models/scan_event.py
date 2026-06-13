from datetime import datetime
from app import db


class ScanEvent(db.Model):
    """Record of a QR scan event for an item (Asset or Inventory Item Instance)"""

    __tablename__ = "scan_events"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )

    # Polymorphic-ish item link (could use generic foreign keys, but explicit is fine here)
    item_type = db.Column(
        db.String(20), nullable=False
    )  # 'asset' or 'inventory_instance'
    item_id = db.Column(db.Integer, nullable=False)

    # Location where scan occurred
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    bin_id = db.Column(db.Integer, db.ForeignKey("warehouse_bins.id"))

    # Who and what
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    device_id = db.Column(db.String(255))  # ID of scanning device/mobile

    # Action
    action_type = db.Column(
        db.String(50), nullable=False
    )  # CHECK_IN, CHECK_OUT, TRANSFER, AUDIT, VERIFY

    user_role = db.Column(db.String(50))
    previous_state = db.Column(db.JSON)
    new_state = db.Column(db.JSON)
    validation_status = db.Column(
        db.String(20), nullable=False, default="verified"
    )  # verified | rejected | duplicate
    scan_fingerprint = db.Column(db.String(64), index=True)

    # Context
    notes = db.Column(db.String(500))
    latitude = db.Column(db.Float)  # For GPS-assisted tracking
    longitude = db.Column(db.Float)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        db.Index("ix_scan_events_item", "item_type", "item_id"),
        db.Index(
            "ix_scan_events_org_timestamp", "organisation_id", "timestamp"
        ),
        db.Index("ix_scan_events_user_id", "user_id"),
    )
