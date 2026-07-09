from datetime import datetime, timedelta

import bcrypt

from flask import Blueprint, current_app, jsonify, request

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
)

from flask_limiter.util import get_remote_address
from app import limiter

from app import db
from app.audit_service import AuditService
from app.errors import AuthenticationError, ConflictError, ValidationError
from app.models import user, token
from app.tenant_utils import get_user_by_id, public_schema
from app.validation import (
    UserLoginSchema,
    UserRegistrationSchema,
    OrganizationRegistrationSchema,
    validate_input,
)
from app.cors_utils import preflight_response

auth_bp = Blueprint("auth", __name__)

# Rate limiting for auth endpoints
# Use application-wide rate limiter


@auth_bp.route("/register-org", methods=["OPTIONS"])
def register_org_options():
    """CORS preflight — must not require JWT or rate limits."""
    return preflight_response(["POST", "OPTIONS"])


@auth_bp.route("/register-org", methods=["POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register_org():
    """Register a new institution and its admin."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError(
            "Invalid request body",
            {"_schema": ["JSON body with registration fields is required"]},
        )

    validated_data, errors = validate_input(OrganizationRegistrationSchema, data)
    if errors:
        current_app.logger.info("register-org validation failed: %s", errors)
        summary = "; ".join(
            f"{field}: {msgs[0] if isinstance(msgs, list) else msgs}"
            for field, msgs in errors.items()
        )
        raise ValidationError(summary or "Validation failed", errors)

    # 1. Check if organization already exists
    from app.models.organization import Organization
    if Organization.query.filter_by(code=validated_data["org_code"]).first():
        raise ConflictError("Organization code already registered")
    
    if Organization.query.filter_by(name=validated_data["org_name"]).first():
        raise ConflictError("Organization name already in use")

    # 2. Check if admin user already exists
    if user.User.query.filter_by(email=validated_data["admin_email"]).first():
        raise ConflictError("Admin email already registered")

    # 3. Create new organization
    new_org = Organization(
        name=validated_data["org_name"],
        code=validated_data["org_code"],
        description=validated_data.get("org_description"),
    )
    db.session.add(new_org)
    db.session.flush()  # To get new_org.id

    # 4. Create Tenant Schema (Multi-tenancy isolation)
    from app.tenant_utils import create_tenant_schema
    if not create_tenant_schema(new_org.id):
        db.session.rollback()
        return jsonify({"error": "Failed to initialize secure data schema for institution"}), 500

    # 5. Create Admin user
    new_admin = user.User(
        organisation_id=new_org.id,
        username=validated_data["admin_username"],
        email=validated_data["admin_email"],
        first_name=validated_data.get("admin_first_name"),
        last_name=validated_data.get("admin_last_name"),
        role="admin",
    )

    # Hash password
    password_bytes = validated_data["admin_password"].encode("utf-8")
    salt = bcrypt.gensalt(rounds=current_app.config["BCRYPT_LOG_ROUNDS"])
    new_admin.password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    db.session.add(new_admin)
    db.session.commit()

    # Audit log
    AuditService.log_authentication_event(
        "ORG_REGISTERED",
        new_admin.id,
        {
            "org_name": new_org.name,
            "org_code": new_org.code,
            "admin_email": new_admin.email,
        },
    )

    return (
        jsonify(
            {
                "message": "Institution registered successfully",
                "org_id": new_org.id,
                "admin_id": new_admin.id,
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["OPTIONS"])
def login_options():
    return preflight_response(["POST", "OPTIONS"])


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    """Authenticate user and return JWT tokens."""
    data = request.get_json()

    # Validate input
    validated_data, errors = validate_input(UserLoginSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Find user in shared public schema (tenant schemas shadow this table)
    with public_schema():
        user_obj = user.User.query.filter_by(email=validated_data["email"]).first()
    if not user_obj or not user_obj.is_active:
        raise AuthenticationError("Invalid credentials")

    # Check if account is locked
    if user_obj.locked_until and user_obj.locked_until > datetime.utcnow():
        raise AuthenticationError(
            f"Account is locked. Try again after {user_obj.locked_until.strftime('%H:%M:%S')}"
        )

    # Verify password
    password_bytes = validated_data["password"].encode("utf-8")
    hashed_bytes = user_obj.password_hash.encode("utf-8")
    if not bcrypt.checkpw(password_bytes, hashed_bytes):
        # Increment failed attempts
        user_obj.failed_login_attempts += 1
        if user_obj.failed_login_attempts >= 5:
            # Lock for 15 minutes
            user_obj.locked_until = datetime.utcnow() + timedelta(minutes=15)
            user_obj.failed_login_attempts = 0  # Reset after locking
            db.session.commit()
            raise AuthenticationError(
                "Too many failed attempts. Account locked for 15 minutes."
            )

        db.session.commit()
        raise AuthenticationError("Invalid credentials")

    # Reset failed attempts on successful login
    user_obj.failed_login_attempts = 0
    user_obj.locked_until = None
    user_obj.last_login = datetime.utcnow()
    db.session.commit()

    # Create tokens
    access_token = create_access_token(
        identity=str(user_obj.id),
        additional_claims={
            "organisation_id": user_obj.organisation_id,
            "role": user_obj.role,
            "username": user_obj.username,
        },
    )
    refresh_token = create_refresh_token(identity=str(user_obj.id))

    # Audit log
    AuditService.log_authentication_event(
        "USER_LOGIN",
        user_obj.id,
        {
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
        },
    )

    response = jsonify(
        {
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user_obj.id,
                "username": user_obj.username,
                "email": user_obj.email,
                "role": user_obj.role,
                "organisation_id": user_obj.organisation_id,
            },
        }
    )

    # Set cookies for web clients
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

    return response, 200


@auth_bp.route("/refresh", methods=["OPTIONS"])
def refresh_options():
    return preflight_response(["POST", "OPTIONS"])


@auth_bp.route("/refresh", methods=["POST"])
@limiter.limit("30 per minute", methods=["POST"])
def refresh_access_token():
    """Refresh access token using refresh cookie or Authorization header."""
    verify_jwt_in_request(refresh=True, optional=True)
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"refreshed": False, "authenticated": False}), 200

    user_obj = get_user_by_id(user_id)

    if not user_obj or not user_obj.is_active:
        return jsonify({"refreshed": False, "authenticated": False}), 200

    # Create new access token
    access_token = create_access_token(
        identity=str(user_obj.id),
        additional_claims={
            "organisation_id": user_obj.organisation_id,
            "role": user_obj.role,
            "username": user_obj.username,
        },
    )

    # Audit log
    AuditService.log_authentication_event("TOKEN_REFRESH", user_obj.id)

    response = jsonify(
        {
            "message": "Token refreshed",
            "refreshed": True,
            "authenticated": True,
            "access_token": access_token,
        }
    )

    set_access_cookies(response, access_token)
    return response, 200


@auth_bp.route("/logout", methods=["OPTIONS"])
def logout_options():
    return preflight_response(["POST", "OPTIONS"])


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Logout user and blacklist tokens."""
    user_id = get_jwt_identity()
    jwt_data = get_jwt()

    # Add token to blacklist
    jti = jwt_data["jti"]
    token_type = jwt_data["type"]
    expires = datetime.fromtimestamp(jwt_data["exp"])

    blacklisted_token = token.TokenBlacklist(
        jti=jti,
        token_type=token_type,
        user_id=int(user_id),
        expires_at=expires,
    )
    db.session.add(blacklisted_token)
    db.session.commit()

    # Audit log
    AuditService.log_authentication_event(
        "USER_LOGOUT",
        user_id,
        {
            "token_issued_at": jwt_data.get("iat"),
            "token_expires_at": jwt_data.get("exp"),
        },
    )

    response = jsonify({"message": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.route("/me", methods=["OPTIONS"])
def me_options():
    return preflight_response(["GET", "OPTIONS"])


@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    """Get current user information. Returns 200 with authenticated=false when logged out."""
    verify_jwt_in_request(optional=True)
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"authenticated": False, "user": None}), 200

    user_obj = get_user_by_id(user_id)

    if not user_obj:
        return jsonify({"authenticated": False, "user": None}), 200

    return (
        jsonify(
            {
                "authenticated": True,
                "id": user_obj.id,
                "username": user_obj.username,
                "email": user_obj.email,
                "first_name": user_obj.first_name,
                "last_name": user_obj.last_name,
                "role": user_obj.role,
                "organisation_id": user_obj.organisation_id,
                "is_active": user_obj.is_active,
                "last_login": (
                    user_obj.last_login.isoformat()
                    if user_obj.last_login
                    else None
                ),
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# Password Reset (1-minute expiry)
# ---------------------------------------------------------------------------

@auth_bp.route("/forgot-password", methods=["OPTIONS"])
def forgot_password_options():
    return preflight_response(["POST", "OPTIONS"])


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3 per hour", methods=["POST"])
def forgot_password():
    """
    Request a password-reset link.

    Body: { "email": "user@example.com" }

    A time-limited token (TTL = PASSWORD_RESET_TOKEN_TTL_SECONDS, default 60 s)
    is generated, its SHA-256 hash stored, and a reset link emailed to the user.
    The response is always 200 to avoid email enumeration.
    """
    import hashlib
    import secrets
    from app.logging_utils import log_security_event
    from app.models.token import PasswordResetToken

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        # Always 200 — do not reveal whether email exists
        return jsonify({"message": "If that email is registered, a reset link has been sent."}), 200

    ttl_seconds = current_app.config.get("PASSWORD_RESET_TOKEN_TTL_SECONDS", 60)
    expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

    with public_schema():
        user_obj = user.User.query.filter_by(email=email, is_active=True).first()

    if not user_obj:
        # Constant-time response — do not reveal whether user exists
        log_security_event("FORGOT_PASSWORD_UNKNOWN_EMAIL", email=email)
        return jsonify({"message": "If that email is registered, a reset link has been sent."}), 200

    # Invalidate any existing unused tokens for this user
    PasswordResetToken.query.filter_by(user_id=user_obj.id, used_at=None).delete()

    # Generate a secure random token and store its SHA-256 hash
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    reset_token = PasswordResetToken(
        user_id=user_obj.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.session.add(reset_token)
    db.session.commit()

    # Build the reset link pointing at the frontend
    frontend_url = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={raw_token}"

    # Send email (best-effort — failure does not abort the request)
    try:
        from flask_mail import Message
        from app import mail

        msg = Message(
            subject="TrackIT — Password Reset (expires in 1 minute)",
            recipients=[user_obj.email],
            body=(
                f"Hello {user_obj.first_name or user_obj.username},\n\n"
                f"You requested a password reset for your TrackIT account.\n\n"
                f"Click the link below to reset your password "
                f"(valid for {ttl_seconds} seconds only):\n\n"
                f"{reset_link}\n\n"
                f"If you did not request this, please ignore this email "
                f"and contact your administrator immediately.\n\n"
                f"— TrackIT Security Team"
            ),
        )
        mail.send(msg)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("Password-reset email failed: %s", exc)

    log_security_event(
        "FORGOT_PASSWORD_REQUESTED",
        user_id=user_obj.id,
        email=email,
        expires_at=expires_at.isoformat(),
        ip=request.remote_addr,
    )
    AuditService.log_authentication_event(
        "PASSWORD_RESET_REQUESTED",
        user_obj.id,
        {"email": email, "ip_address": request.remote_addr, "expires_at": expires_at.isoformat()},
    )

    return jsonify({"message": "If that email is registered, a reset link has been sent."}), 200


@auth_bp.route("/reset-password", methods=["OPTIONS"])
def reset_password_options():
    return preflight_response(["POST", "OPTIONS"])


@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5 per minute", methods=["POST"])
def reset_password():
    """
    Consume a password-reset token and set a new password.

    Body: { "token": "<raw_token>", "new_password": "<new_password>" }

    The token is valid for PASSWORD_RESET_TOKEN_TTL_SECONDS (default 60 s).
    Once used, the token is marked as consumed and cannot be reused.
    """
    import hashlib
    from app.logging_utils import log_security_event
    from app.models.token import PasswordResetToken

    data = request.get_json(silent=True) or {}
    raw_token = (data.get("token") or "").strip()
    new_password = data.get("new_password", "")

    if not raw_token or not new_password:
        raise ValidationError("Both 'token' and 'new_password' are required.")

    if len(new_password) < 8:
        raise ValidationError("Password must be at least 8 characters.")

    # Hash the incoming token to compare against stored hash
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    reset_token = PasswordResetToken.query.filter_by(
        token_hash=token_hash, used_at=None
    ).first()

    if not reset_token:
        log_security_event("RESET_PASSWORD_INVALID_TOKEN", ip=request.remote_addr)
        raise ValidationError("Invalid or already-used reset token.")

    if not reset_token.is_valid():
        # Token expired — 1 minute has elapsed
        log_security_event(
            "RESET_PASSWORD_EXPIRED_TOKEN",
            user_id=reset_token.user_id,
            ip=request.remote_addr,
        )
        raise ValidationError(
            "This password reset link has expired (1-minute limit). "
            "Please request a new one."
        )

    user_obj = reset_token.user
    if not user_obj or not user_obj.is_active:
        raise ValidationError("User account is not active.")

    # Hash and apply the new password
    password_bytes = new_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=current_app.config["BCRYPT_LOG_ROUNDS"])
    user_obj.password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    # Mark token as used
    reset_token.used_at = datetime.utcnow()

    # Invalidate all active sessions by clearing locked_until and failed attempts
    user_obj.failed_login_attempts = 0
    user_obj.locked_until = None

    db.session.commit()

    log_security_event(
        "RESET_PASSWORD_SUCCESS",
        user_id=user_obj.id,
        ip=request.remote_addr,
    )
    AuditService.log_authentication_event(
        "PASSWORD_RESET_COMPLETED",
        user_obj.id,
        {"ip_address": request.remote_addr},
    )

    return jsonify({"message": "Password reset successfully. You can now log in."}), 200
