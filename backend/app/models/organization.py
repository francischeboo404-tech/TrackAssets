from datetime import datetime

from app import db


class Organization(db.Model):
    """Multi-tenant organization model"""

    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(512), nullable=True)
    preferences = db.Column(db.JSON, default={})
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    users = db.relationship("User", backref="organization", lazy=True)
    departments = db.relationship(
        "Department",
        backref="organization",
        lazy=True,
        cascade="all, delete-orphan",
    )
    assets = db.relationship(
        "Asset",
        backref="organization",
        lazy=True,
        cascade="all, delete-orphan",
    )
    inventory_items = db.relationship(
        "InventoryItem",
        backref="organization",
        lazy=True,
        cascade="all, delete-orphan",
    )
    audit_logs = db.relationship(
        "AuditLog",
        backref="organization",
        lazy=True,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("ix_organizations_code", "code"),
        db.Index("ix_organizations_active", "is_active"),
    )

    def __repr__(self):
        return f"<Organization {self.code}>"


class Department(db.Model):
    """Department model for organizing assets"""

    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    head_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "organisation_id", "code", name="uq_dept_org_code"
        ),
        db.Index("ix_departments_org_id", "organisation_id"),
        db.Index("ix_departments_head_id", "head_id"),
        db.Index("ix_departments_active", "is_active"),
    )

    assets = db.relationship("Asset", backref="department", lazy=True)
    head = db.relationship(
        "User", backref="headed_departments", foreign_keys=[head_id]
    )

    def __repr__(self):
        return f"<Department {self.code}>"
