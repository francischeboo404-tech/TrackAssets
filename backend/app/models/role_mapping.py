from datetime import datetime, timezone
from app import db


class RoleMapping(db.Model):
    __tablename__ = 'role_mappings'

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    role = db.Column(db.String(100), nullable=False, unique=True)
    label = db.Column(db.String(255), nullable=True)
    permissions = db.Column(db.JSON(), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'role': self.role,
            'label': self.label,
            'permissions': self.permissions or [],
        }
