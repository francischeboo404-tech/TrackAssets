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

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

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
limiter = Limiter(key_func=get_remote_address)


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
