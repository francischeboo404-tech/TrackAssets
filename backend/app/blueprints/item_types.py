from flask import Blueprint, jsonify, request
from app import db, limiter
from app.auth_utils import get_current_organisation_id, jwt_required_with_user
from app.models.kenya_gov_models import ItemType

item_types_bp = Blueprint("item_types", __name__)

@item_types_bp.route("", methods=["POST"])
@jwt_required_with_user
@limiter.limit("20 per minute")
def create_item_type():
    org_id = get_current_organisation_id()
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()

    if not name:
        return jsonify({"success": False, "message": "Item Type name is required"}), 400

    if len(name) > 50:
        return jsonify({"success": False, "message": "Item Type name must be 50 characters or fewer"}), 400

    existing = ItemType.query.filter(
        ItemType.organization_id == org_id,
        db.func.lower(ItemType.name) == name.lower()
    ).first()
    
    if existing:
        return jsonify({"success": False, "message": f"Item Type '{name}' already exists"}), 400

    from app.auth_utils import get_current_user_id
    user_id = get_current_user_id()

    item_type = ItemType(
        organization_id=org_id,
        name=name,
        description=description or None,
        created_by=user_id,
        updated_by=user_id,
    )
    db.session.add(item_type)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "item_type": {
                    "id": item_type.id,
                    "name": item_type.name,
                    "description": item_type.description,
                },
            }
        ),
        201,
    )


@item_types_bp.route("", methods=["GET"])
@jwt_required_with_user
@limiter.limit("100 per minute")
def list_item_types():
    org_id = get_current_organisation_id()
    
    custom_types = ItemType.query.filter_by(organization_id=org_id, is_active=True).all()
    
    predefined = [
        {"id": "consumable", "name": "Consumable", "description": "Standard consumable items"},
        {"id": "asset", "name": "Asset", "description": "Fixed assets"},
        {"id": "raw", "name": "Raw Material", "description": "Raw materials for production"},
        {"id": "finished", "name": "Finished Product", "description": "Finished products"},
        {"id": "service", "name": "Service", "description": "Non-physical services"},
        {"id": "other", "name": "Other", "description": "Other item types"},
    ]

    result = predefined + [
        {
            "id": t.name,
            "name": t.name,
            "description": t.description,
            "is_custom": True
        }
        for t in custom_types
    ]
    
    return jsonify({"success": True, "item_types": result}), 200
