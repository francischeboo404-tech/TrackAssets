from flask import Blueprint, jsonify, request
from app import db
from app.auth_utils import get_current_organisation_id, jwt_required_with_user
from app.models.kenya_gov_models import Category

categories_bp = Blueprint("categories", __name__)


@categories_bp.route("", methods=["POST"])
@jwt_required_with_user
def create_category():
    org_id = get_current_organisation_id()
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()

    if not name:
        return jsonify({"success": False, "message": "Category name is required"}), 400

    category = Category(
        organization_id=org_id,
        name=name,
        description=description or None,
    )
    db.session.add(category)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "category": {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                    "parent_category_id": category.parent_category_id,
                },
            }
        ),
        201,
    )


@categories_bp.route("", methods=["GET"])
@jwt_required_with_user
def list_categories():
    org_id = get_current_organisation_id()
    categories = Category.query.filter_by(organization_id=org_id, is_active=True).all()
    result = [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "parent_category_id": c.parent_category_id,
        }
        for c in categories
    ]
    return jsonify({"success": True, "categories": result}), 200
