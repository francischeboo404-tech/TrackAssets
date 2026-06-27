from flask import Blueprint, request, jsonify
from app import db
from app.models.supplier import Supplier
from app.auth_utils import require_role, get_current_organisation_id
from app.errors import NotFoundError, ValidationError

suppliers_bp = Blueprint("suppliers", __name__)

@suppliers_bp.route("", methods=["GET"])
@require_role("admin", "procurement_officer", "store_manager", "logistics_officer", "auditor")
def list_suppliers():
    """List all active suppliers for the current organization"""
    org_id = get_current_organisation_id()
    if not org_id:
        return jsonify({"success": False, "message": "No organization context"}), 400

    suppliers = Supplier.query.filter_by(organisation_id=org_id, is_active=True).all()
    
    result = []
    for s in suppliers:
        result.append({
            "id": s.id,
            "name": s.name,
            "code": s.code,
            "email": s.email,
            "phone": s.phone,
            "average_lead_time_days": s.average_lead_time_days,
            "reliability_score": s.reliability_score,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
        
    return jsonify({"success": True, "suppliers": result}), 200

@suppliers_bp.route("", methods=["POST"])
@require_role("admin", "procurement_officer")
def create_supplier():
    """Create a new supplier"""
    org_id = get_current_organisation_id()
    data = request.get_json() or {}
    
    name = data.get("name")
    if not name:
        raise ValidationError("Supplier name is required")
        
    code = data.get("code")
    
    # Check for existing code
    if code:
        existing = Supplier.query.filter_by(organisation_id=org_id, code=code).first()
        if existing:
            raise ValidationError(f"Supplier with code '{code}' already exists")

    supplier = Supplier(
        organisation_id=org_id,
        name=name,
        code=code,
        email=data.get("email"),
        phone=data.get("phone"),
        average_lead_time_days=data.get("average_lead_time_days", 7),
        reliability_score=data.get("reliability_score", 1.0)
    )
    
    db.session.add(supplier)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Supplier created successfully",
        "supplier": {
            "id": supplier.id,
            "name": supplier.name,
            "code": supplier.code,
            "email": supplier.email,
            "phone": supplier.phone
        }
    }), 201

@suppliers_bp.route("/<int:id>", methods=["PUT"])
@require_role("admin", "procurement_officer")
def update_supplier(id):
    """Update an existing supplier"""
    org_id = get_current_organisation_id()
    supplier = Supplier.query.filter_by(id=id, organisation_id=org_id).first()
    
    if not supplier:
        raise NotFoundError("Supplier not found")
        
    data = request.get_json() or {}
    
    if "name" in data:
        if not data["name"]:
            raise ValidationError("Supplier name cannot be empty")
        supplier.name = data["name"]
        
    if "code" in data:
        code = data["code"]
        existing = Supplier.query.filter(
            Supplier.organisation_id == org_id,
            Supplier.code == code,
            Supplier.id != id
        ).first()
        if existing:
            raise ValidationError(f"Supplier with code '{code}' already exists")
        supplier.code = code
        
    if "email" in data:
        supplier.email = data["email"]
        
    if "phone" in data:
        supplier.phone = data["phone"]
        
    if "average_lead_time_days" in data:
        supplier.average_lead_time_days = data["average_lead_time_days"]
        
    if "reliability_score" in data:
        supplier.reliability_score = data["reliability_score"]
        
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Supplier updated successfully"
    }), 200

@suppliers_bp.route("/<int:id>", methods=["DELETE"])
@require_role("admin", "procurement_officer")
def delete_supplier(id):
    """Deactivate a supplier"""
    org_id = get_current_organisation_id()
    supplier = Supplier.query.filter_by(id=id, organisation_id=org_id).first()
    
    if not supplier:
        raise NotFoundError("Supplier not found")
        
    supplier.is_active = False
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Supplier deleted successfully"
    }), 200
