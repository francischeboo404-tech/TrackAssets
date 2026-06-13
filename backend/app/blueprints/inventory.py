from flask import Blueprint, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db
from app.auth_utils import (
    get_current_organisation_id,
    jwt_required_with_user,
    require_permission,
    require_role,
)
from app.errors import ValidationError
from app.validation import (
    InventoryItemSchema,
    StockMovementSchema,
    validate_input,
    sanitize_string,
)

# New service/repository imports
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService

# Instantiate repository and service (incremental; we'll add DI later)
_inventory_repo = InventoryRepository()
inventory_service = InventoryService(
    repository=_inventory_repo, session=db.session
)

inventory_bp = Blueprint("inventory", __name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@inventory_bp.route("", methods=["GET"])
@jwt_required_with_user
@limiter.limit("100 per minute")
def get_inventory():
    """Get all inventory items for current user's organization"""
    org_id = get_current_organisation_id()

    # Query parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = request.args.get("search")
    low_stock_only = request.args.get("low_stock_only", type=bool)

    items = inventory_service.list_items(
        org_id,
        page=page,
        per_page=per_page,
        search=search,
        low_stock_only=low_stock_only,
    )

    return (
        jsonify(
            {
                "inventory": [
                    {
                        "id": i.id,
                        "name": i.name,
                        "sku": i.sku,
                        "description": i.description,
                        "quantity": i.quantity,
                        "reorder_level": i.reorder_level,
                        "unit_price": i.unit_price,
                        "unit": i.unit,
                        "is_low_stock": i.is_low_stock(),
                        "total_value": i.quantity * i.unit_price,
                        "created_at": i.created_at.isoformat(),
                        "updated_at": i.updated_at.isoformat(),
                    }
                    for i in items.items
                ],
                "pagination": {
                    "page": items.page,
                    "per_page": items.per_page,
                    "total": items.total,
                    "pages": items.pages,
                    "has_next": items.has_next,
                    "has_prev": items.has_prev,
                },
            }
        ),
        200,
    )


@inventory_bp.route("/<int:item_id>", methods=["GET"])
@jwt_required_with_user
@limiter.limit("200 per minute")
def get_inventory_item(item_id):
    """Get specific inventory item"""
    org_id = get_current_organisation_id()

    item, recent_movements = inventory_service.get_item(item_id, org_id)

    return (
        jsonify(
            {
                "id": item.id,
                "name": item.name,
                "sku": item.sku,
                "description": item.description,
                "quantity": item.quantity,
                "reorder_level": item.reorder_level,
                "unit_price": item.unit_price,
                "unit": item.unit,
                "is_low_stock": item.is_low_stock(),
                "total_value": item.quantity * item.unit_price,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "recent_movements": [
                    {
                        "id": m.id,
                        "type": m.type,
                        "quantity": m.quantity,
                        "reference": m.reference,
                        "notes": m.notes,
                        "date": m.date.isoformat(),
                    }
                    for m in recent_movements
                ],
            }
        ),
        200,
    )


@inventory_bp.route("", methods=["POST"])
@jwt_required_with_user
@require_permission("inventory:create")
@limiter.limit("20 per minute")
def create_inventory_item():
    """Create new inventory item"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Validate input
    validated_data, errors = validate_input(InventoryItemSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Sanitize inputs
    validated_data["name"] = sanitize_string(validated_data["name"])
    if "description" in validated_data:
        validated_data["description"] = sanitize_string(
            validated_data["description"]
        )

    new_item = inventory_service.create_item(org_id, validated_data)

    return (
        jsonify(
            {
                "message": "Inventory item created successfully",
                "item_id": new_item.id,
            }
        ),
        201,
    )


@inventory_bp.route("", methods=["OPTIONS"])
def create_inventory_item_options():
    """CORS preflight for creating inventory items."""
    return ('', 204)


@inventory_bp.route("/<int:item_id>", methods=["PUT"])
@jwt_required_with_user
@require_permission("inventory:edit")
@limiter.limit("30 per minute")
def update_inventory_item(item_id):
    """Update inventory item"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Validate input
    validated_data, errors = validate_input(InventoryItemSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Sanitize inputs
    if "name" in validated_data:
        validated_data["name"] = sanitize_string(validated_data["name"])
    if "description" in validated_data:
        validated_data["description"] = sanitize_string(
            validated_data["description"]
        )

    inventory_service.update_item(item_id, org_id, validated_data)
    return jsonify({"message": "Inventory item updated successfully"}), 200


@inventory_bp.route("/<int:item_id>", methods=["OPTIONS"])
def update_inventory_item_options(item_id):
    """CORS preflight for updating/deleting inventory item."""
    return ('', 204)


@inventory_bp.route("/<int:item_id>/stock", methods=["POST"])
@jwt_required_with_user
@require_permission("inventory:stock")
@limiter.limit("50 per minute")
def update_stock(item_id):
    """Update stock levels (IN/OUT movements)"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Validate input
    validated_data, errors = validate_input(StockMovementSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    movement_type = validated_data["type"]
    quantity = validated_data["quantity"]
    warehouse_id = validated_data.get("warehouse_id")
    reference = validated_data.get("reference")
    notes = validated_data.get("notes")

    item = inventory_service.update_stock(
        item_id,
        org_id,
        movement_type,
        quantity,
        warehouse_id=warehouse_id,
        reference=reference,
        notes=notes,
    )

    return (
        jsonify(
            {
                "message": f"Stock {movement_type.lower()} successful",
                "item_id": item.id,
                "new_quantity": item.quantity,
                "movement": {
                    "type": movement_type,
                    "quantity": quantity,
                    "reference": reference,
                    "notes": notes,
                },
            }
        ),
        200,
    )


@inventory_bp.route("/<int:item_id>/stock", methods=["OPTIONS"])
def update_stock_options(item_id):
    """CORS preflight for updating stock movements."""
    return ('', 204)


@inventory_bp.route("/<int:item_id>", methods=["DELETE"])
@jwt_required_with_user
@require_permission("inventory:delete")
@limiter.limit("10 per minute")
def delete_inventory_item(item_id):
    """Delete inventory item (admin only)"""
    org_id = get_current_organisation_id()

    inventory_service.delete_item(item_id, org_id)
    return jsonify({"message": "Inventory item deleted successfully"}), 200


@inventory_bp.route("/low-stock", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_low_stock_items():
    """Get items that are below reorder level"""
    org_id = get_current_organisation_id()

    low_stock_items = inventory_service.low_stock_items(org_id)

    return (
        jsonify(
            {
                "low_stock_items": [
                    {
                        "id": i.id,
                        "name": i.name,
                        "sku": i.sku,
                        "quantity": i.quantity,
                        "reorder_level": i.reorder_level,
                        "deficit": i.reorder_level - i.quantity,
                        "unit": i.unit,
                    }
                    for i in low_stock_items
                ],
                "count": len(low_stock_items),
            }
        ),
        200,
    )


@inventory_bp.route("/stats", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_inventory_stats():
    """Get inventory statistics"""
    org_id = get_current_organisation_id()

    stats = inventory_service.stats(org_id)
    return jsonify(stats), 200
