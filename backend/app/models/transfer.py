from datetime import datetime

from app import db


class TransferRequest(db.Model):
    """Transfer request model for assets requiring approval."""

    __tablename__ = "transfer_requests"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    item_type = db.Column(db.String(20), default="asset")  # 'asset' or 'inventory'
    asset_id = db.Column(
        db.Integer, db.ForeignKey("assets.id"), nullable=True
    )
    inventory_item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=True
    )
    quantity = db.Column(db.Integer, default=1)
    requested_by = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    from_department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False
    )
    to_department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False
    )
    requested_location = db.Column(db.String(255))
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    to_bin_id = db.Column(db.Integer, db.ForeignKey("warehouse_bins.id"))
    comment = db.Column(db.String(1000))
    status = db.Column(db.String(50), nullable=False, default="pending")
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    review_comments = db.Column(db.String(1000))
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    __table_args__ = (
        db.Index("ix_transfer_requests_org_id", "organisation_id"),
        db.Index("ix_transfer_requests_asset_id", "asset_id"),
        db.Index("ix_transfer_requests_inventory_id", "inventory_item_id"),
        db.Index("ix_transfer_requests_item_type", "item_type"),
        db.Index("ix_transfer_requests_status", "status"),
        db.Index("ix_transfer_requests_requested_by", "requested_by"),
        db.Index("ix_transfer_requests_from_dept", "from_department_id"),
        db.Index("ix_transfer_requests_to_dept", "to_department_id"),
        db.Index("ix_transfer_requests_requested_at", "requested_at"),
    )

    asset = db.relationship(
        "Asset", back_populates="transfer_requests", lazy=True
    )
    inventory_item = db.relationship(
        "InventoryItem", lazy=True
    )
    requester = db.relationship("User", foreign_keys=[requested_by])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
    from_department = db.relationship(
        "Department", foreign_keys=[from_department_id]
    )
    to_department = db.relationship(
        "Department", foreign_keys=[to_department_id]
    )

    def __repr__(self):
        return (
            f"<TransferRequest asset_id={self.asset_id} status={self.status}>"
        )
