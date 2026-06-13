from datetime import datetime
from app import db


class Supplier(db.Model):
    """Supplier information and replenishment performance tracking."""

    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))

    # Performance metrics
    average_lead_time_days = db.Column(db.Integer, default=7)
    reliability_score = db.Column(db.Float, default=1.0)  # 0.0 to 1.0

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "organisation_id", "code", name="uq_supplier_code"
        ),
    )
