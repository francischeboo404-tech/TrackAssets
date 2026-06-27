from flask import Blueprint, jsonify
from app.auth_utils import get_current_organisation_id, require_role
from app.models.kenya_gov_models import Category

categories_bp = Blueprint("categories", __name__)

@categories_bp.route("", methods=["GET"])
@require_role("admin", "procurement_officer", "store_manager", "logistics_officer", "auditor")
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
