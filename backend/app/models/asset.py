from datetime import datetime
from enum import Enum

from app import db


class AssetStatus(Enum):
    """Asset status enumeration"""

    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    DISPOSED = "disposed"


class AssetCondition(Enum):
    """Asset condition enumeration"""

    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    REPAIR = "repair"
    CONDEMNED = "condemned"


class DepreciationMethod(Enum):
    """Depreciation method enumeration"""

    STRAIGHT_LINE = "straight_line"


class Asset(db.Model):
    """Asset model for tracking fixed assets"""

    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    asset_code = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(255))
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False
    )
    assigned_to = db.Column(db.String(255))
    status = db.Column(
        db.String(50), nullable=False, default=AssetStatus.REQUESTED.value
    )
    condition = db.Column(
        db.String(50), nullable=False, default=AssetCondition.NEW.value
    )
    location = db.Column(db.String(255))
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"))
    bin_id = db.Column(db.Integer, db.ForeignKey("warehouse_bins.id"))
    purchase_date = db.Column(db.Date, nullable=False)
    purchase_value = db.Column(db.Numeric(12, 2), nullable=False)
    useful_life = db.Column(db.Integer, nullable=False)
    depreciation_method = db.Column(
        db.String(50),
        nullable=False,
        default=DepreciationMethod.STRAIGHT_LINE.value,
    )
    current_value = db.Column(db.Numeric(12, 2), nullable=False)
    qr_code_data = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "organisation_id",
            "asset_code",
            name="uq_asset_org_code",
        ),
        db.UniqueConstraint(
            "organisation_id",
            "serial_number",
            name="uq_asset_org_serial",
        ),
        db.Index("ix_assets_org_id", "organisation_id"),
        db.Index("ix_assets_dept_id", "department_id"),
        db.Index("ix_assets_status", "status"),
        db.Index("ix_assets_asset_code", "asset_code"),
        db.Index("ix_assets_serial_number", "serial_number"),
    )

    audit_logs = db.relationship(
        "AssetAuditLog",
        backref="asset",
        lazy=True,
        cascade="all, delete-orphan",
    )

    # Cascade delete for transfers
    from app.models.transfer import TransferRequest

    transfer_requests = db.relationship(
        "TransferRequest",
        back_populates="asset",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def can_transition_to(self, new_status):
        """Validate state transition"""
        current = self.status
        new = new_status if isinstance(new_status, str) else new_status.value

        allowed_transitions = {
            AssetStatus.REQUESTED.value: [
                AssetStatus.APPROVED.value,
                AssetStatus.REJECTED.value,
            ],
            AssetStatus.APPROVED.value: [AssetStatus.IN_USE.value],
            AssetStatus.IN_USE.value: [
                AssetStatus.MAINTENANCE.value,
                AssetStatus.DISPOSED.value,
            ],
            AssetStatus.MAINTENANCE.value: [
                AssetStatus.IN_USE.value,
                AssetStatus.DISPOSED.value,
            ],
            AssetStatus.REJECTED.value: [
                AssetStatus.REQUESTED.value
            ],  # Allow re-requesting
            AssetStatus.DISPOSED.value: [],  # Final state
        }

        return new in allowed_transitions.get(current, [])

    def calculate_depreciation_details(self):
        """Return depreciation details for an asset"""
        if (
            self.purchase_value is None
            or self.useful_life is None
            or self.purchase_date is None
        ):
            return None

        years_used = max(
            0.0, (datetime.utcnow().date() - self.purchase_date).days / 365.25
        )
        
        from decimal import Decimal
        purchase_value_dec = Decimal(str(self.purchase_value))
        useful_life_dec = Decimal(str(self.useful_life))
        years_used_dec = Decimal(str(years_used))
        
        annual_depreciation = (
            purchase_value_dec / useful_life_dec if useful_life_dec else Decimal('0')
        )
        depreciated_value = purchase_value_dec - (
            annual_depreciation * years_used_dec
        )
        remaining_life = max(0.0, float(self.useful_life) - years_used)

        return {
            "purchase_value": float(purchase_value_dec),
            "useful_life_years": self.useful_life,
            "years_used": round(years_used, 2),
            "annual_depreciation": round(float(annual_depreciation), 2),
            "current_value": round(float(max(Decimal('0'), depreciated_value)), 2),
            "remaining_life_years": round(remaining_life, 2),
            "depreciation_method": self.depreciation_method,
        }

    def update_current_value(self):
        """Calculate current value using straight-line depreciation"""
        if self.depreciation_method != DepreciationMethod.STRAIGHT_LINE.value:
            return

        years_used = (
            datetime.utcnow().date() - self.purchase_date
        ).days / 365.25
        
        from decimal import Decimal
        purchase_value_dec = Decimal(str(self.purchase_value))
        useful_life_dec = Decimal(str(self.useful_life))
        years_used_dec = Decimal(str(years_used))
        
        annual_depreciation = purchase_value_dec / useful_life_dec if useful_life_dec else Decimal('0')
        depreciated_value = purchase_value_dec - (
            annual_depreciation * years_used_dec
        )

        self.current_value = max(Decimal('0'), depreciated_value)

    def __repr__(self):
        return f"<Asset {self.asset_code}>"


class AssetAuditLog(db.Model):
    """Audit log for asset changes"""

    __tablename__ = "asset_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(
        db.Integer, db.ForeignKey("assets.id"), nullable=False
    )
    action = db.Column(db.String(100), nullable=False)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index("ix_asset_audit_logs_asset_id", "asset_id"),
        db.Index("ix_asset_audit_logs_action", "action"),
        db.Index("ix_asset_audit_logs_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<AssetAuditLog {self.asset_id} - {self.action}>"
