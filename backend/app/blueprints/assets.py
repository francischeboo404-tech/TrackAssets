from flask import Blueprint, g, jsonify, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db
from app.auth_utils import (
    get_current_organisation_id,
    jwt_required_with_user,
    require_permission,
    require_role,
)
from app.rbac import (
    assert_not_read_only,
    assert_can_transition_status,
    get_available_transitions,
)
from app.errors import AuthorizationError, NotFoundError, ValidationError
from app.models import asset
from app.validation import (
    AssetSchema,
    AssetStatusUpdateSchema,
    validate_input,
    sanitize_string,
)

# New service/repository imports
from app.repositories.asset_repository import AssetRepository
from app.services.asset_service import AssetService

# Instantiate repository and service (temporary wiring; will DI later)
_asset_repo = AssetRepository()
asset_service = AssetService(repository=_asset_repo, session=db.session)

from app.utils.qr_generator import generate_nova_sticker
from app.utils.bulk_qr import generate_bulk_qr_pdf

assets_bp = Blueprint("assets", __name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@assets_bp.route("", methods=["GET"])
@jwt_required_with_user
@limiter.limit("100 per minute")
def get_assets():
    """Get all assets for current user's organization"""
    org_id = get_current_organisation_id()

    # Query parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    status = request.args.get("status")
    department_id = request.args.get("department_id", type=int)
    search = request.args.get("search")

    assets = asset_service.list_assets(
        org_id,
        page=page,
        per_page=per_page,
        status=status,
        department_id=department_id,
        search=search,
    )

    return (
        jsonify(
            {
                "assets": [
                    {
                        "id": a.id,
                        "asset_code": a.asset_code,
                        "name": a.name,
                        "type": a.type,
                        "serial_number": a.serial_number,
                        "department_id": a.department_id,
                        "department_name": (
                            a.department.name if a.department else None
                        ),
                        "assigned_to": a.assigned_to,
                        "status": a.status,
                        "condition": a.condition,
                        "location": a.location,
                        "warehouse_id": a.warehouse_id,
                        "bin_id": a.bin_id,
                        "purchase_date": (
                            a.purchase_date.isoformat()
                            if a.purchase_date
                            else None
                        ),
                        "purchase_value": a.purchase_value,
                        "current_value": a.current_value,
                        "useful_life": a.useful_life,
                        "qr_code_data": a.qr_code_data,
                        "created_at": a.created_at.isoformat(),
                        "updated_at": a.updated_at.isoformat(),
                    }
                    for a in assets.items
                ],
                "pagination": {
                    "page": assets.page,
                    "per_page": assets.per_page,
                    "total": assets.total,
                    "pages": assets.pages,
                    "has_next": assets.has_next,
                    "has_prev": assets.has_prev,
                },
            }
        ),
        200,
    )


@assets_bp.route("/<int:asset_id>", methods=["GET"])
@jwt_required_with_user
@limiter.limit("200 per minute")
def get_asset(asset_id):
    """Get specific asset"""
    org_id = get_current_organisation_id()

    asset_obj = asset.Asset.query.filter_by(
        id=asset_id, organisation_id=org_id
    ).first()

    if not asset_obj:
        raise NotFoundError("Asset not found")

    return (
        jsonify(
            {
                "id": asset_obj.id,
                "asset_code": asset_obj.asset_code,
                "name": asset_obj.name,
                "type": asset_obj.type,
                "serial_number": asset_obj.serial_number,
                "department_id": asset_obj.department_id,
                "department_name": (
                    asset_obj.department.name if asset_obj.department else None
                ),
                "assigned_to": asset_obj.assigned_to,
                "status": asset_obj.status,
                "condition": asset_obj.condition,
                "location": asset_obj.location,
                "warehouse_id": asset_obj.warehouse_id,
                "bin_id": asset_obj.bin_id,
                "purchase_date": (
                    asset_obj.purchase_date.isoformat()
                    if asset_obj.purchase_date
                    else None
                ),
                "purchase_value": asset_obj.purchase_value,
                "current_value": asset_obj.current_value,
                "useful_life": asset_obj.useful_life,
                "qr_code_data": asset_obj.qr_code_data,
                "created_at": asset_obj.created_at.isoformat(),
                "updated_at": asset_obj.updated_at.isoformat(),
            }
        ),
        200,
    )


@assets_bp.route("", methods=["POST"])
@jwt_required_with_user
@require_permission("assets:create")
@limiter.limit("20 per minute")
def create_asset():
    """Create new asset"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Validate input
    validated_data, errors = validate_input(AssetSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Sanitize inputs
    validated_data["name"] = sanitize_string(validated_data["name"])
    if "assigned_to" in validated_data:
        validated_data["assigned_to"] = sanitize_string(
            validated_data["assigned_to"]
        )
    if "location" in validated_data:
        validated_data["location"] = sanitize_string(
            validated_data["location"]
        )

    new_asset = asset_service.create_asset(org_id, validated_data)

    return (
        jsonify(
            {"message": "Asset created successfully", "asset_id": new_asset.id}
        ),
        201,
    )


@assets_bp.route("", methods=["OPTIONS"])
def create_asset_options():
    """CORS preflight for creating assets."""
    return ('', 204)


@assets_bp.route("/<int:asset_id>", methods=["PUT"])
@jwt_required_with_user
@require_permission("assets:edit")
@limiter.limit("30 per minute")
def update_asset(asset_id):
    """Update asset"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Validate input
    validated_data, errors = validate_input(AssetSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Sanitize inputs
    if "name" in validated_data:
        validated_data["name"] = sanitize_string(validated_data["name"])
    if "assigned_to" in validated_data:
        validated_data["assigned_to"] = sanitize_string(
            validated_data["assigned_to"]
        )
    if "location" in validated_data:
        validated_data["location"] = sanitize_string(
            validated_data["location"]
        )

    asset_service.update_asset(
        asset_id, org_id, validated_data, user_role=g.user.role
    )
    return jsonify({"message": "Asset updated successfully"}), 200


@assets_bp.route("/<int:asset_id>", methods=["OPTIONS"])
def update_asset_options(asset_id):
    """CORS preflight for updating/deleting an asset."""
    return ('', 204)


@assets_bp.route("/<int:asset_id>/transitions", methods=["GET"])
@jwt_required_with_user
def get_asset_transitions(asset_id):
    """List allowed status transitions for the current user's role."""
    org_id = get_current_organisation_id()
    asset_obj = asset_service.get_asset(asset_id, org_id)
    transitions = get_available_transitions(g.user.role, asset_obj.status)
    return jsonify({"current_status": asset_obj.status, "transitions": transitions}), 200


@assets_bp.route("/<int:asset_id>/status", methods=["PUT"])
@jwt_required_with_user
@limiter.limit("30 per minute")
def update_asset_status(asset_id):
    """Update asset status with RBAC-enforced transitions."""
    data = request.get_json()
    org_id = get_current_organisation_id()

    assert_not_read_only(g.user.role, "change asset status")

    validated_data, errors = validate_input(AssetStatusUpdateSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    new_status = validated_data["status"]
    asset_obj = asset_service.get_asset(asset_id, org_id)
    assert_can_transition_status(g.user.role, asset_obj.status, new_status)

    asset_obj = asset_service.update_asset_status(
        asset_id,
        org_id,
        new_status,
        current_user_role=g.user.role,
        comments=validated_data.get("comments"),
    )

    return (
        jsonify(
            {
                "message": "Asset status updated successfully",
                "old_status": validated_data.get("old_status", None),
                "new_status": asset_obj.status,
            }
        ),
        200,
    )


@assets_bp.route("/<int:asset_id>/status", methods=["OPTIONS"])
def update_asset_status_options(asset_id):
    """CORS preflight for updating asset status."""
    return ('', 204)


@assets_bp.route("/<int:asset_id>", methods=["DELETE"])
@jwt_required_with_user
@require_role("admin")
@limiter.limit("10 per minute")
def delete_asset(asset_id):
    """Delete asset (admin only)"""
    org_id = get_current_organisation_id()

    asset_service.delete_asset(asset_id, org_id)
    return jsonify({"message": "Asset deleted successfully"}), 200


@assets_bp.route("/stats", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_asset_stats():
    """Get asset statistics for organization"""
    org_id = get_current_organisation_id()
    stats_data = asset_service.stats(org_id)

    return (
        jsonify(stats_data),
        200,
    )


@assets_bp.route("/<int:asset_id>/qr-sticker", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_qr_sticker(asset_id):
    """Generate and return a branded QR PNG sticker"""
    org_id = get_current_organisation_id()
    asset_obj = asset_service.get_asset(asset_id, org_id)

    # Use the signed data for the QR
    sticker_io = generate_nova_sticker(
        qr_data=asset_obj.qr_code_data,
        asset_code=asset_obj.asset_code,
        asset_name=asset_obj.name,
    )

    return send_file(
        sticker_io,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"sticker_{asset_obj.asset_code}.png",
    )


@assets_bp.route("/bulk-qr", methods=["GET"])
@jwt_required_with_user
def get_bulk_qr():
    """Generate a bulk PDF of QR stickers"""
    org_id = get_current_organisation_id()
    
    # Optional filtering by IDs
    asset_ids = request.args.getlist("ids", type=int)
    
    assets_data = asset_service.get_bulk_qr_data(org_id, asset_ids)
    
    pdf_buffer = generate_bulk_qr_pdf(assets_data)
    
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="bulk_qr_stickers.pdf"
    )
