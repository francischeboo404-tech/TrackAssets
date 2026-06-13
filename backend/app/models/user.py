from datetime import datetime

import bcrypt
from flask_login import UserMixin

from app import db


class User(UserMixin, db.Model):
    """User model with Flask-Login integration"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    role = db.Column(db.String(50), nullable=False, default="staff")
    phone_number = db.Column(db.String(20))
    department = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "organisation_id", "username", name="uq_user_org_username"
        ),
        db.UniqueConstraint(
            "organisation_id", "email", name="uq_user_org_email"
        ),
        db.Index("ix_users_org_id", "organisation_id"),
        db.Index("ix_users_email", "email"),
        db.Index("ix_users_role", "role"),
    )

    audit_logs = db.relationship("AuditLog", backref="user", lazy=True)

    def set_password(self, password):
        """Hash and set password with complexity requirements"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in password):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )
        if not any(c.islower() for c in password):
            raise ValueError(
                "Password must contain at least one lowercase letter"
            )
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            raise ValueError(
                "Password must contain at least one special character"
            )

        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password_bytes, salt).decode(
            "utf-8"
        )

    def check_password(self, password):
        """Verify password"""
        password_bytes = password.encode("utf-8")
        hashed_bytes = self.password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def has_permission(self, permission):
        """
        Check if user has specific permission.
        Format: 'resource:action' (e.g., 'assets:edit')
        """
        # Superadmin has full access
        if self.role == "superadmin":
            return True

        role_permissions = {
            "admin": [
                "*:*",
                "inventory:delete",
                "assets:dispose",
            ],
            "store_manager": [
                "assets:*",
                "inventory:create",
                "inventory:edit",
                "inventory:stock",
                "transfers:*",
                "warehouses:*",
                "analytics:view",
                "users:view",
                "reports:view",
            ],
            "staff": [
                "assets:view",
                "assets:create",
                "assets:edit",
                "assets:transition",
                "inventory:view",
                "inventory:stock",
                "transfers:create",
                "transfers:view",
                "warehouses:view",
            ],
            "dept_head": [
                "assets:view",
                "assets:approve",
                "assets:transition",
                "transfers:approve",
                "transfers:create",
                "transfers:view",
                "reports:view",
            ],
            "viewer": [
                "assets:view", "inventory:view", "warehouses:view", "reports:view"
            ],
            "auditor": [
                "assets:view", "inventory:view", "audit:view", "reports:view"
            ]
        }
        
        allowed_permissions = role_permissions.get(self.role, [])
        
        if "*:*" in allowed_permissions:
            return True
            
        if permission in allowed_permissions:
            return True
            
        # Check for resource-level wildcards (e.g., 'assets:*')
        resource, action = permission.split(':')
        if f"{resource}:*" in allowed_permissions:
            return True
            
        return False

    def __repr__(self):
        return f"<User {self.username}>"
