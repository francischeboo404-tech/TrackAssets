from flask import Blueprint, g, jsonify, request
from app import db
from app.auth_utils import (
    jwt_required_with_user,
    get_current_organisation_id,
    require_role,
)
from app.models.user import User
from app.errors import NotFoundError, ValidationError
from app.audit_service import AuditService

from app.validation import UserRegistrationSchema, validate_input, sanitize_string
import bcrypt
from flask import current_app

users_bp = Blueprint("users", __name__)


@users_bp.route("", methods=["POST"])
@jwt_required_with_user
@require_role("admin")
def create_user():
    """Create a new user within the organization (Admin only)"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Validate input
    validated_data, errors = validate_input(UserRegistrationSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Force the organization ID to match the Admin's organization
    validated_data["organisation_id"] = org_id

    # Check if user already exists
    if User.query.filter_by(email=validated_data["email"]).first():
        raise ValidationError("Email already registered")

    if User.query.filter_by(
        username=validated_data["username"], organisation_id=org_id
    ).first():
        raise ValidationError("Username already taken in this organization")

    # Create new user
    new_user = User(
        organisation_id=org_id,
        username=validated_data["username"],
        email=validated_data["email"],
        first_name=validated_data.get("first_name"),
        last_name=validated_data.get("last_name"),
        role=validated_data.get("role", "staff"),
        phone_number=validated_data.get("phone_number"),
        department=validated_data.get("department"),
    )

    # Hash password
    password_bytes = validated_data["password"].encode("utf-8")
    salt = bcrypt.gensalt(rounds=current_app.config["BCRYPT_LOG_ROUNDS"])
    new_user.password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    db.session.add(new_user)
    db.session.commit()

    # Audit log
    AuditService.log_action(
        action="USER_CREATED",
        entity_type="user",
        entity_id=new_user.id,
        details={
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
        },
        organisation_id=org_id,
    )

    return (
        jsonify(
            {
                "message": "User created successfully",
                "user_id": new_user.id,
            }
        ),
        201,
    )


@users_bp.route("", methods=["GET"])
@jwt_required_with_user
@require_role("admin")
def get_users():
    """List all users in the organization (Admin only)"""
    org_id = get_current_organisation_id()

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = User.query.filter_by(organisation_id=org_id)

    # Filter by search query if provided
    search_query = request.args.get("q")
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                User.role.ilike(search_pattern),
            )
        )

    # Filter by role if provided
    role_filter = request.args.get("role")
    if role_filter:
        query = query.filter_by(role=role_filter)

    pagination_obj = query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    return (
        jsonify(
            {
                "users": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "email": u.email,
                        "role": u.role,
                        "is_active": u.is_active,
                        "last_login": (
                            u.last_login.isoformat() if u.last_login else None
                        ),
                    }
                    for u in pagination_obj.items
                ],
                "pagination": {
                    "page": pagination_obj.page,
                    "per_page": pagination_obj.per_page,
                    "total": pagination_obj.total,
                    "pages": pagination_obj.pages,
                    "has_next": pagination_obj.has_next,
                    "has_prev": pagination_obj.has_prev,
                },
            }
        ),
        200,
    )


@users_bp.route("/<int:user_id>/role", methods=["PUT"])
@jwt_required_with_user
@require_role("admin")
def update_user_role(user_id):
    """Update a user's role"""
    data = request.get_json()
    new_role = data.get("role")
    org_id = get_current_organisation_id()

    if new_role not in [
        "admin",
        "staff",
        "dept_head",
        "store_manager",
    ]:
        raise ValidationError("Invalid role")

    user_obj = User.query.filter_by(id=user_id, organisation_id=org_id).first()
    if not user_obj:
        raise NotFoundError("User not found")

    old_role = user_obj.role
    user_obj.role = new_role
    db.session.commit()

    AuditService.log_action(
        action="USER_ROLE_UPDATED",
        entity_type="user",
        entity_id=user_id,
        details={"old_role": old_role, "new_role": new_role},
        organisation_id=org_id,
    )

    return jsonify({"message": f"User role updated to {new_role}"}), 200


@users_bp.route("/<int:user_id>/status", methods=["PUT"])
@jwt_required_with_user
@require_role("admin")
def toggle_user_status(user_id):
    """Deactivate/Activate a user"""
    data = request.get_json()
    is_active = data.get("is_active")
    org_id = get_current_organisation_id()

    user_obj = User.query.filter_by(id=user_id, organisation_id=org_id).first()
    if not user_obj:
        raise NotFoundError("User not found")

    # Prevent self-deactivation
    if user_obj.id == g.user.id:
        raise ValidationError("Cannot deactivate yourself")

    user_obj.is_active = is_active
    db.session.commit()

    AuditService.log_action(
        action="USER_STATUS_TOGGLED",
        entity_type="user",
        entity_id=user_id,
        details={"is_active": is_active},
        organisation_id=org_id,
    )

    return jsonify({"message": "User status updated"}), 200
