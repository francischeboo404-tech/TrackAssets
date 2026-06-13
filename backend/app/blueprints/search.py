from flask import Blueprint, jsonify, request
from app import db
from app.auth_utils import jwt_required_with_user, get_current_organisation_id
from app.models import Asset, InventoryItem, User, Department

search_bp = Blueprint("search", __name__)

@search_bp.route("/", methods=["GET"])
@jwt_required_with_user
def global_search():
    """Global search across multiple entities."""
    org_id = get_current_organisation_id()
    query = request.args.get("q", "").strip()
    
    if not query or len(query) < 2:
        return jsonify({"assets": [], "inventory": [], "users": [], "departments": []}), 200

    search_pattern = f"%{query}%"
    terms = query.split()

    # --- Phase 1: Search Base Entities & Gather IDs for IN operations ---
    
    # Departments (Match ALL terms)
    dept_filters = [
        Department.organisation_id == org_id,
        Department.is_active == True
    ]
    for term in terms:
        term_pattern = f"%{term}%"
        dept_filters.append(db.or_(
            Department.name.ilike(term_pattern),
            Department.code.ilike(term_pattern)
        ))

    departments_query = Department.query.filter(*dept_filters).all()
    dept_ids = [d.id for d in departments_query]

    # Users (Match ALL terms)
    user_filters = [
        User.organisation_id == org_id,
        User.is_active == True
    ]
    for term in terms:
        term_pattern = f"%{term}%"
        user_filters.append(db.or_(
            User.username.ilike(term_pattern),
            User.email.ilike(term_pattern),
            User.first_name.ilike(term_pattern),
            User.last_name.ilike(term_pattern)
        ))

    users_query = User.query.filter(*user_filters).all()
    user_names = [f"{u.first_name} {u.last_name}" for u in users_query]

    # --- Phase 2: Search Cross-Entities ---

    # Search Assets (Match ALL terms)
    asset_filters = [
        Asset.organisation_id == org_id,
        Asset.status != "disposed",
    ]
    
    # Each term must match at least one field
    for term in terms:
        term_pattern = f"%{term}%"
        term_conditions = [
            Asset.name.ilike(term_pattern),
            Asset.asset_code.ilike(term_pattern),
            Asset.serial_number.ilike(term_pattern)
        ]
        # Include matches from related dept/user if they matched the term
        # (Simplified: if any dept matched the whole query, include its assets)
        # But per-term logic is more robust.
        asset_filters.append(db.or_(*term_conditions))

    # Add broad matches for found departments/users
    final_asset_conditions = [db.and_(*asset_filters)]
    if dept_ids:
        final_asset_conditions.append(Asset.department_id.in_(dept_ids))
    if user_names:
        final_asset_conditions.append(Asset.assigned_to.in_(user_names))

    assets_query = (
        Asset.query.outerjoin(Department)
        .filter(
            Asset.organisation_id == org_id,
            Asset.status != "disposed",
            db.or_(*final_asset_conditions),
        )
        .limit(10)
        .all()
    )

    # Search Inventory (Match ALL terms)
    inventory_filters = [
        InventoryItem.organisation_id == org_id,
        InventoryItem.is_active == True
    ]
    for term in terms:
        term_pattern = f"%{term}%"
        inventory_filters.append(db.or_(
            InventoryItem.name.ilike(term_pattern),
            InventoryItem.sku.ilike(term_pattern),
            InventoryItem.description.ilike(term_pattern)
        ))

    inventory_query = InventoryItem.query.filter(*inventory_filters).limit(10).all()

    # --- Phase 3: Format and Return ---
    
    return jsonify({
        "assets": [{"id": a.id, "name": a.name, "code": a.asset_code, "type": "Asset"} for a in assets_query[:5]],
        "inventory": [{"id": i.id, "name": i.name, "code": i.sku, "type": "Inventory"} for i in inventory_query[:5]],
        "users": [{"id": u.id, "name": f"{u.first_name} {u.last_name}", "code": u.email, "type": "User"} for u in users_query[:5]],
        "departments": [{"id": d.id, "name": d.name, "code": d.code, "type": "Department"} for d in departments_query[:5]]
    }), 200
