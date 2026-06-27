from flask import Blueprint, jsonify, request
from flask_limiter.util import get_remote_address
from datetime import datetime
from app import limiter

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

# Use application-wide rate limiter


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
                        # expose new master-data fields for frontend and reporting
                        "category_id": getattr(i, 'category_id', None),
                        "item_type": getattr(i, 'item_type', None),
                        "status": getattr(i, 'status', None),
                        "preferred_supplier_id": getattr(i, 'preferred_supplier_id', None),
                        "supplier_item_reference": getattr(i, 'supplier_item_reference', None),
                        "purchase_cost": getattr(i, 'purchase_cost', None),
                        "last_purchase_cost": getattr(i, 'last_purchase_cost', None),
                        "tax_category": getattr(i, 'tax_category', None),
                        "lead_time_days": getattr(i, 'lead_time_days', None),
                        "min_stock_level": getattr(i, 'min_stock_level', None),
                        "max_stock_level": getattr(i, 'max_stock_level', None),
                        "safety_stock": getattr(i, 'safety_stock', None),
                        "opening_stock": getattr(i, 'opening_stock', None),
                        "unit": i.unit,
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
                "category_id": getattr(item, 'category_id', None),
                "item_type": getattr(item, 'item_type', None),
                "status": getattr(item, 'status', None),
                "preferred_supplier_id": getattr(item, 'preferred_supplier_id', None),
                "supplier_item_reference": getattr(item, 'supplier_item_reference', None),
                "purchase_cost": getattr(item, 'purchase_cost', None),
                "last_purchase_cost": getattr(item, 'last_purchase_cost', None),
                "tax_category": getattr(item, 'tax_category', None),
                "lead_time_days": getattr(item, 'lead_time_days', None),
                "min_stock_level": getattr(item, 'min_stock_level', None),
                "max_stock_level": getattr(item, 'max_stock_level', None),
                "safety_stock": getattr(item, 'safety_stock', None),
                "opening_stock": getattr(item, 'opening_stock', None),
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


@inventory_bp.route("/bulk", methods=["POST"])
@jwt_required_with_user
@require_permission("inventory:create")
@limiter.limit("5 per minute")
def bulk_import_inventory():
    """Bulk import inventory items from a parsed JSON array (max 500 rows)."""
    data = request.get_json()
    org_id = get_current_organisation_id()

    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or len(items) == 0:
        raise ValidationError("Request must include a non-empty 'items' array")

    if len(items) > 500:
        raise ValidationError("Bulk import is limited to 500 rows per request")

    results = []
    succeeded = 0
    failed = 0

    for index, row in enumerate(items):
        validated_data, errors = validate_input(InventoryItemSchema, row)
        if errors:
            failed += 1
            results.append({"row": index, "status": "error", "errors": errors})
            continue

        validated_data["name"] = sanitize_string(validated_data["name"])
        if "description" in validated_data:
            validated_data["description"] = sanitize_string(validated_data["description"])

        try:
            new_item = inventory_service.create_item(org_id, validated_data)
            succeeded += 1
            results.append({
                "row": index,
                "status": "created",
                "item_id": new_item.id,
                "sku": new_item.sku,
            })
        except Exception as e:
            db.session.rollback()
            failed += 1
            results.append({"row": index, "status": "error", "errors": {"_error": str(e)}})

    return jsonify({
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }), 207 if failed > 0 else 201


@inventory_bp.route("/bulk", methods=["OPTIONS"])
def bulk_import_inventory_options():
    """CORS preflight for bulk inventory import."""
    return ('', 204)


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


# ============ BATCH ENDPOINTS ============

# Import batch service and schema
from app.services.inventory_service import InventoryBatchService
from app.validation import InventoryBatchSchema

batch_service = InventoryBatchService(session=db.session)


@inventory_bp.route("/batches", methods=["GET"])
@jwt_required_with_user
@limiter.limit("100 per minute")
def list_batches():
    """List inventory batches for current organization"""
    org_id = get_current_organisation_id()
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = request.args.get("search")
    item_id = request.args.get("item_id", type=int)
    status = request.args.get("status")
    show_expired = request.args.get("show_expired", False, type=bool)
    
    batches = batch_service.list_batches(
        org_id, page=page, per_page=per_page, search=search,
        item_id=item_id, status=status, show_expired=show_expired
    )
    
    return jsonify({
        "batches": [
            {
                "id": b.id,
                "batch_number": b.batch_number,
                "item_id": b.item_id,
                "quantity": b.quantity,
                "warehouse_id": b.warehouse_id,
                "received_date": b.received_date.isoformat() if b.received_date else None,
                "manufacture_date": b.manufacture_date.isoformat() if b.manufacture_date else None,
                "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
                "supplier_id": b.supplier_id,
                "status": b.status,
                "is_expired": b.is_expired(),
                "created_at": b.created_at.isoformat(),
                "updated_at": b.updated_at.isoformat(),
            }
            for b in batches.items
        ],
        "pagination": {
            "page": batches.page,
            "per_page": batches.per_page,
            "total": batches.total,
            "pages": batches.pages,
            "has_next": batches.has_next,
            "has_prev": batches.has_prev,
        },
    }), 200


@inventory_bp.route("/batches/<int:batch_id>", methods=["GET"])
@jwt_required_with_user
@limiter.limit("200 per minute")
def get_batch(batch_id):
    """Get specific batch"""
    org_id = get_current_organisation_id()
    batch = batch_service.get_batch(batch_id, org_id)
    
    return jsonify({
        "id": batch.id,
        "batch_number": batch.batch_number,
        "item_id": batch.item_id,
        "quantity": batch.quantity,
        "warehouse_id": batch.warehouse_id,
        "received_date": batch.received_date.isoformat() if batch.received_date else None,
        "manufacture_date": batch.manufacture_date.isoformat() if batch.manufacture_date else None,
        "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
        "supplier_id": batch.supplier_id,
        "status": batch.status,
        "is_expired": batch.is_expired(),
        "created_at": batch.created_at.isoformat(),
        "updated_at": batch.updated_at.isoformat(),
    }), 200


@inventory_bp.route("/batches", methods=["POST"])
@jwt_required_with_user
@require_permission("inventory:create")
@limiter.limit("50 per minute")
def create_batch():
    """Create a new batch"""
    org_id = get_current_organisation_id()
    data = request.get_json() or {}
    
    validated_data, errors = validate_input(InventoryBatchSchema, data)
    if errors:
        return jsonify({"errors": errors}), 400
    
    batch = batch_service.create_batch(org_id, validated_data)
    
    return jsonify({
        "id": batch.id,
        "batch_number": batch.batch_number,
        "item_id": batch.item_id,
        "quantity": batch.quantity,
        "warehouse_id": batch.warehouse_id,
        "received_date": batch.received_date.isoformat() if batch.received_date else None,
        "manufacture_date": batch.manufacture_date.isoformat() if batch.manufacture_date else None,
        "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
        "supplier_id": batch.supplier_id,
        "status": batch.status,
        "created_at": batch.created_at.isoformat(),
        "updated_at": batch.updated_at.isoformat(),
    }), 201


@inventory_bp.route("/batches/<int:batch_id>", methods=["PUT"])
@jwt_required_with_user
@require_permission("inventory:edit")
@limiter.limit("50 per minute")
def update_batch(batch_id):
    """Update a batch"""
    org_id = get_current_organisation_id()
    data = request.get_json() or {}
    
    validated_data, errors = validate_input(InventoryBatchSchema, data, partial=True)
    if errors:
        return jsonify({"errors": errors}), 400
    
    batch = batch_service.update_batch(batch_id, org_id, validated_data)
    
    return jsonify({
        "id": batch.id,
        "batch_number": batch.batch_number,
        "item_id": batch.item_id,
        "quantity": batch.quantity,
        "warehouse_id": batch.warehouse_id,
        "received_date": batch.received_date.isoformat() if batch.received_date else None,
        "manufacture_date": batch.manufacture_date.isoformat() if batch.manufacture_date else None,
        "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
        "supplier_id": batch.supplier_id,
        "status": batch.status,
        "updated_at": batch.updated_at.isoformat(),
    }), 200


@inventory_bp.route("/batches/<int:batch_id>", methods=["DELETE"])
@jwt_required_with_user
@require_permission("inventory:delete")
@limiter.limit("50 per minute")
def delete_batch(batch_id):
    """Delete a batch"""
    org_id = get_current_organisation_id()
    result = batch_service.delete_batch(batch_id, org_id)
    return jsonify(result), 204


@inventory_bp.route("/batches/expiring", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_expiring_batches():
    """Get batches expiring within specified days"""
    org_id = get_current_organisation_id()
    days = request.args.get("days", 30, type=int)
    
    batches = batch_service.get_expiring_batches(org_id, days=days)
    
    return jsonify({
        "expiring_batches": [
            {
                "id": b.id,
                "batch_number": b.batch_number,
                "item_id": b.item_id,
                "quantity": b.quantity,
                "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
                "days_until_expiry": (b.expiry_date - datetime.utcnow()).days if b.expiry_date else None,
            }
            for b in batches
        ],
        "count": len(batches),
    }), 200


@inventory_bp.route("/batches/stats", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_batch_stats():
    """Get batch statistics"""
    org_id = get_current_organisation_id()
    stats = batch_service.batch_stats(org_id)
    return jsonify(stats), 200
