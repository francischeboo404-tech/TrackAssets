from flask import Blueprint, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db
from app.audit_service import AuditService
from app.auth_utils import (
    get_current_organisation_id,
    jwt_required_with_user,
    require_role,
)
from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import organization, user
from app.validation import DepartmentSchema, validate_input
from app.services.event_bus import event_bus

departments_bp = Blueprint("departments", __name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@departments_bp.route("", methods=["GET"])
@jwt_required_with_user
@limiter.limit("100 per minute")
def get_departments():
    """Get all departments for current user's organization"""
    org_id = get_current_organisation_id()

    # Query parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = request.args.get("search")

    query = organization.Department.query.filter_by(
        organisation_id=org_id, is_active=True
    )

    if search:
        query = query.outerjoin(organization.Department.head).filter(
            db.or_(
                organization.Department.name.ilike(f"%{search}%"),
                organization.Department.code.ilike(f"%{search}%"),
                user.User.first_name.ilike(f"%{search}%"),
                user.User.last_name.ilike(f"%{search}%"),
                user.User.username.ilike(f"%{search}%"),
            )
        )

    departments = query.paginate(page=page, per_page=per_page, error_out=False)

    result = []
    for dept in departments.items:
        dept_data = {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "description": dept.description,
            "is_active": dept.is_active,
            "created_at": dept.created_at.isoformat(),
            "updated_at": dept.updated_at.isoformat(),
            "asset_count": len(dept.assets),
        }

        if dept.head:
            dept_data["head"] = {
                "id": dept.head.id,
                "username": dept.head.username,
                "first_name": dept.head.first_name,
                "last_name": dept.head.last_name,
            }

        result.append(dept_data)

    return (
        jsonify(
            {
                "departments": result,
                "pagination": {
                    "page": departments.page,
                    "per_page": departments.per_page,
                    "total": departments.total,
                    "pages": departments.pages,
                    "has_next": departments.has_next,
                    "has_prev": departments.has_prev,
                },
            }
        ),
        200,
    )


@departments_bp.route("/<int:dept_id>", methods=["GET"])
@jwt_required_with_user
@limiter.limit("200 per minute")
def get_department(dept_id):
    """Get specific department"""
    org_id = get_current_organisation_id()

    dept = organization.Department.query.filter_by(
        id=dept_id, organisation_id=org_id, is_active=True
    ).first()

    if not dept:
        raise NotFoundError("Department not found")

    return (
        jsonify(
            {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "description": dept.description,
                "is_active": dept.is_active,
                "created_at": dept.created_at.isoformat(),
                "updated_at": dept.updated_at.isoformat(),
                "head": (
                    {
                        "id": dept.head.id,
                        "username": dept.head.username,
                        "first_name": dept.head.first_name,
                        "last_name": dept.head.last_name,
                    }
                    if dept.head
                    else None
                ),
                "asset_count": len(dept.assets),
                "assets": [
                    {
                        "id": asset.id,
                        "asset_code": asset.asset_code,
                        "name": asset.name,
                        "status": asset.status,
                    }
                    for asset in dept.assets[:10]
                ],  # Limit to first 10 assets
            }
        ),
        200,
    )


@departments_bp.route("", methods=["POST"])
@jwt_required_with_user
@require_role("admin")
@limiter.limit("20 per minute")
def create_department():
    """Create new department (admin only)"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Validate input
    validated_data, errors = validate_input(DepartmentSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Check if department code already exists
    if organization.Department.query.filter_by(
        code=validated_data["code"], organisation_id=org_id
    ).first():
        raise ConflictError("Department code already exists")

    # Check if head user exists and belongs to organization
    head_id = validated_data.get("head_id")
    if head_id:
        head_user = user.User.query.filter_by(
            id=head_id, organisation_id=org_id, is_active=True
        ).first()
        if not head_user:
            raise ValidationError("Invalid department head")
    else:
        head_id = None

    # Create department
    new_dept = organization.Department(
        organisation_id=org_id,
        name=validated_data["name"],
        code=validated_data["code"],
        description=validated_data.get("description"),
        head_id=head_id,
    )

    db.session.add(new_dept)
    db.session.commit()

    # Audit log
    AuditService.log_department_change(
        new_dept,
        "DEPARTMENT_CREATED",
        details={"code": new_dept.code, "name": new_dept.name},
    )
    
    event_bus.publish("DEPARTMENT_UPDATED", {"department_id": new_dept.id}, organisation_id=org_id)

    return (
        jsonify(
            {
                "message": "Department created successfully",
                "department_id": new_dept.id,
            }
        ),
        201,
    )


@departments_bp.route("", methods=["OPTIONS"])
def create_department_options():
    """CORS preflight for creating departments."""
    return ('', 204)


@departments_bp.route("/<int:dept_id>", methods=["PUT"])
@jwt_required_with_user
@require_role("admin")
@limiter.limit("30 per minute")
def update_department(dept_id):
    """Update department (admin only)"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    dept = organization.Department.query.filter_by(
        id=dept_id, organisation_id=org_id, is_active=True
    ).first()

    if not dept:
        raise NotFoundError("Department not found")

    # Store old values for audit
    old_values = {
        "name": dept.name,
        "code": dept.code,
        "description": dept.description,
        "head_id": dept.head_id,
    }

    # Update fields
    updatable_fields = ["name", "description"]

    for field in updatable_fields:
        if field in data:
            setattr(dept, field, data[field])

    # Update code if provided (check uniqueness)
    if "code" in data and data["code"] != dept.code:
        if organization.Department.query.filter_by(
            code=data["code"], organisation_id=org_id
        ).first():
            raise ConflictError("Department code already exists")
        dept.code = data["code"]

    # Update head if provided
    if "head_id" in data:
        if data["head_id"] is None:
            dept.head_id = None
        else:
            head_user = user.User.query.filter_by(
                id=data["head_id"], organisation_id=org_id, is_active=True
            ).first()
            if not head_user:
                raise ValidationError("Invalid department head")
            dept.head_id = data["head_id"]

    dept.updated_at = db.func.now()
    db.session.commit()

    # Audit log
    new_values = {
        "name": dept.name,
        "code": dept.code,
        "description": dept.description,
        "head_id": dept.head_id,
    }
    AuditService.log_department_change(
        dept,
        "DEPARTMENT_UPDATED",
        details={"old_values": old_values, "new_values": new_values},
    )

    event_bus.publish("DEPARTMENT_UPDATED", {"department_id": dept.id}, organisation_id=org_id)

    return jsonify({"message": "Department updated successfully"}), 200


@departments_bp.route("/<int:dept_id>", methods=["OPTIONS"])
def update_department_options(dept_id):
    """CORS preflight for updating/deleting a department."""
    return ('', 204)


@departments_bp.route("/<int:dept_id>", methods=["DELETE"])
@jwt_required_with_user
@require_role("admin")
@limiter.limit("10 per minute")
def delete_department(dept_id):
    """Delete department (admin only)"""
    org_id = get_current_organisation_id()

    dept = organization.Department.query.filter_by(
        id=dept_id, organisation_id=org_id, is_active=True
    ).first()

    if not dept:
        raise NotFoundError("Department not found")

    # Check if department has assets
    if dept.assets:
        raise ConflictError("Cannot delete department with assigned assets")

    # Soft delete
    dept.is_active = False
    db.session.commit()

    # Audit log
    AuditService.log_department_change(
        dept,
        "DEPARTMENT_DELETED",
        details={"code": dept.code, "name": dept.name},
    )

    event_bus.publish("DEPARTMENT_UPDATED", {"department_id": dept.id}, organisation_id=org_id)

    return jsonify({"message": "Department deleted successfully"}), 200


@departments_bp.route("/stats", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_department_stats():
    """Get department statistics"""
    org_id = get_current_organisation_id()

    # Get department counts and asset assignments
    departments = organization.Department.query.filter_by(
        organisation_id=org_id, is_active=True
    ).all()

    stats = []
    total_assets = 0

    for dept in departments:
        asset_count = len(dept.assets)
        total_assets += asset_count

        stats.append(
            {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "asset_count": asset_count,
                "has_head": dept.head is not None,
            }
        )

    return (
        jsonify(
            {
                "total_departments": len(departments),
                "total_assets": total_assets,
                "departments": stats,
            }
        ),
        200,
    )
