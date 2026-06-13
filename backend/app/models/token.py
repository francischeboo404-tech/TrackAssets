from datetime import datetime
from app import db


class TokenBlacklist(db.Model):
    """Token blacklist for JWT invalidation"""

    __tablename__ = "token_blacklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<TokenBlacklist {self.jti}>"


class PasswordResetToken(db.Model):
    """Secure password reset token with TTL"""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(
        db.String(255), nullable=False, unique=True, index=True
    )
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)

    user = db.relationship("User", backref="reset_tokens", lazy=True)

    def is_valid(self):
        """Check if token is not expired and not used"""
        return self.used_at is None and datetime.utcnow() < self.expires_at

    def __repr__(self):
        return f"<PasswordResetToken user={self.user_id} expires={self.expires_at}>"
