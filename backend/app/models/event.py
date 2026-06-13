from datetime import datetime
from app import db


class SystemEvent(db.Model):
    """Event log for cross-process real-time synchronization."""

    __tablename__ = "system_events"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=True
    )
    event_type = db.Column(db.String(100), nullable=False)
    data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.event_type,
            "data": self.data,
            "timestamp": self.created_at.isoformat(),
        }
