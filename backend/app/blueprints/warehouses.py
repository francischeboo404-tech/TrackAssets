from flask import Blueprint, jsonify, request
from app import db
from app.auth_utils import (
    jwt_required_with_user,
    get_current_organisation_id,
    require_role,
)
from app.models.location_topology import (
    Warehouse,
    WarehouseBin,
    WarehouseZone,
    WarehouseRack,
    WarehouseShelf,
)
from app.errors import NotFoundError, ValidationError, ConflictError
from app.services.analytics_service import AnalyticsService
from app.services.warehouse_hierarchy_service import WarehouseHierarchyService
from app.services.event_bus import event_bus

warehouses_bp = Blueprint("warehouses", __name__)


@warehouses_bp.route("", methods=["GET"])
@jwt_required_with_user
def get_warehouses():
    org_id = get_current_organisation_id()
    warehouses = Warehouse.query.filter_by(organisation_id=org_id).all()
    utilization_map = {
        item["warehouse_id"]: item
        for item in AnalyticsService.get_warehouse_utilization(org_id)
    }

    payload = []
    for warehouse in warehouses:
        metrics = utilization_map.get(warehouse.id, {})
        payload.append(
            {
                "id": warehouse.id,
                "warehouse_id": warehouse.id,
                "name": warehouse.name,
                "warehouse_name": warehouse.name,
                "code": warehouse.code,
                "warehouse_code": warehouse.code,
                "address": warehouse.address,
                "is_active": warehouse.is_active,
                "is_main_warehouse": getattr(warehouse, 'is_main_warehouse', False),
                "warehouse_type": getattr(warehouse, 'warehouse_type', 'branch'),
                "hierarchy_level": getattr(warehouse, 'hierarchy_level', 1),
                "parent_warehouse_id": getattr(warehouse, 'parent_warehouse_id', None),
                "total_bins": metrics.get("total_bins", 0),
                "occupied_bins": metrics.get("occupied_bins", 0),
                "empty_bins": metrics.get("empty_bins", 0),
                "utilization_percentage": metrics.get("utilization_percentage", 0),
            }
        )

    return jsonify(payload), 200


@warehouses_bp.route("", methods=["POST"])
@jwt_required_with_user
@require_role("admin")
def create_warehouse():
    data = request.get_json(silent=True) or {}
    org_id = get_current_organisation_id()

    name = (data.get("name") or "").strip()
    code = (data.get("code") or "").strip()
    if not name or not code:
        raise ValidationError("Warehouse name and code are required")

    duplicate = Warehouse.query.filter_by(organisation_id=org_id).filter(
        db.func.lower(Warehouse.code) == code.lower()
    ).first()
    if duplicate:
        raise ValidationError("Warehouse code already exists")

    # Smart hierarchy assignment:
    # If no main warehouse exists for this org, the first new one becomes main.
    # Otherwise, new warehouses are auto-assigned as branches under main.
    existing_main = Warehouse.query.filter_by(
        organisation_id=org_id, is_main_warehouse=True
    ).first()

    if existing_main is None:
        # First warehouse — set as main
        is_main = True
        warehouse_type = 'main'
        hierarchy_level = 0
        parent_warehouse_id = None
    else:
        # Subsequent warehouses — set as branch under main
        is_main = False
        warehouse_type = 'branch'
        hierarchy_level = 1
        parent_warehouse_id = existing_main.id

    new_warehouse = Warehouse(
        organisation_id=org_id,
        name=name,
        code=code,
        address=(data.get("address") or "").strip() or None,
        is_main_warehouse=is_main,
        warehouse_type=warehouse_type,
        hierarchy_level=hierarchy_level,
        parent_warehouse_id=parent_warehouse_id,
    )
    db.session.add(new_warehouse)
    db.session.commit()

    event_bus.publish(
        "WAREHOUSE_UPDATED",
        {"warehouse_id": new_warehouse.id},
        organisation_id=org_id,
    )

    return jsonify({
        "message": "Warehouse created",
        "id": new_warehouse.id,
        "is_main_warehouse": is_main,
        "warehouse_type": warehouse_type,
    }), 201


@warehouses_bp.route("/org-summary", methods=["GET"])
@jwt_required_with_user
def get_org_warehouse_summary():
    """Org-wide multi-warehouse KPI summary for the All Warehouses hub."""
    org_id = get_current_organisation_id()
    from app.models.stock_levels import WarehouseStock
    from app.models.asset import Asset
    from app.models.organization import Department, Employee
    from app.models.kenya_gov_models import PurchaseRequest
    from sqlalchemy import func

    warehouses = Warehouse.query.filter_by(organisation_id=org_id, is_active=True).all()
    utilization_map = {
        item["warehouse_id"]: item
        for item in AnalyticsService.get_warehouse_utilization(org_id)
    }

    # Org-wide aggregates
    total_inventory_value = AnalyticsService.get_inventory_valuation(org_id)

    total_assets = Asset.query.filter_by(organisation_id=org_id).count()
    total_asset_value = db.session.query(
        func.coalesce(func.sum(Asset.current_value), 0)
    ).filter_by(organisation_id=org_id).scalar() or 0

    total_departments = Department.query.filter_by(organisation_id=org_id, is_active=True).count()
    total_employees = Employee.query.filter_by(organisation_id=org_id, is_active=True).count()
    pending_prs = PurchaseRequest.query.filter_by(organization_id=org_id, status='pending', is_active=True).count()

    warehouse_details = []
    for wh in warehouses:
        metrics = utilization_map.get(wh.id, {})
        wh_summary = AnalyticsService.get_inventory_summary(org_id, warehouse_id=wh.id)
        wh_asset_summary = AnalyticsService.get_asset_summary(org_id, warehouse_id=wh.id)
        wh_depts = Department.query.filter_by(organisation_id=org_id, warehouse_id=wh.id, is_active=True).count()

        warehouse_details.append({
            "id": wh.id,
            "name": wh.name,
            "code": wh.code,
            "address": wh.address,
            "is_main_warehouse": getattr(wh, 'is_main_warehouse', False),
            "warehouse_type": getattr(wh, 'warehouse_type', 'branch'),
            "hierarchy_level": getattr(wh, 'hierarchy_level', 1),
            "stock_units": int(wh_summary.get("total_items", 0)),
            "asset_count": int(wh_asset_summary.get("total_assets", 0)),
            "asset_value": float(wh_asset_summary.get("total_current_value", 0)),
            "department_count": wh_depts,
            "utilization_percentage": metrics.get("utilization_percentage", 0),
            "total_bins": metrics.get("total_bins", 0),
            "occupied_bins": metrics.get("occupied_bins", 0),
        })

    return jsonify({
        "total_warehouses": len(warehouses),
        "total_inventory_value": round(total_inventory_value, 2),
        "total_assets": total_assets,
        "total_asset_value": float(total_asset_value),
        "total_departments": total_departments,
        "total_employees": total_employees,
        "pending_purchase_requests": pending_prs,
        "warehouses": warehouse_details,
    }), 200




@warehouses_bp.route("/<int:warehouse_id>", methods=["PUT"])
@jwt_required_with_user
@require_role("admin")
def update_warehouse(warehouse_id):
    data = request.get_json(silent=True) or {}
    org_id = get_current_organisation_id()

    wh = Warehouse.query.filter_by(id=warehouse_id, organisation_id=org_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValidationError("Warehouse name is required")
        wh.name = name
    if "code" in data:
        code = (data.get("code") or "").strip()
        if not code:
            raise ValidationError("Warehouse code is required")
        if Warehouse.query.filter_by(organisation_id=org_id).filter(
            db.func.lower(Warehouse.code) == code.lower(), Warehouse.id != wh.id
        ).first():
            raise ValidationError("Warehouse code already exists")
        wh.code = code
    if "address" in data:
        wh.address = (data.get("address") or "").strip() or None

    db.session.commit()
    event_bus.publish("WAREHOUSE_UPDATED", {"warehouse_id": wh.id}, organisation_id=org_id)

    return jsonify({"message": "Warehouse updated", "id": wh.id}), 200


@warehouses_bp.route("/<int:warehouse_id>", methods=["DELETE"])
@jwt_required_with_user
@require_role("admin")
def delete_warehouse(warehouse_id):
    org_id = get_current_organisation_id()

    wh = Warehouse.query.filter_by(id=warehouse_id, organisation_id=org_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    wh.is_active = False
    db.session.commit()
    event_bus.publish("WAREHOUSE_DELETED", {"warehouse_id": wh.id}, organisation_id=org_id)

    return jsonify({"message": "Warehouse deleted"}), 200


@warehouses_bp.route("/<int:warehouse_id>/bins", methods=["POST"])
@jwt_required_with_user
@require_role("admin", "store_manager")
def create_bin(warehouse_id):
    data = request.get_json(silent=True) or {}
    org_id = get_current_organisation_id()

    wh = Warehouse.query.filter_by(id=warehouse_id, organisation_id=org_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    code = (data.get("code") or "").strip()
    if not code:
        raise ValidationError("Bin code is required")

    existing_bin = (
        db.session.query(WarehouseBin)
        .join(WarehouseShelf, WarehouseBin.shelf_id == WarehouseShelf.id)
        .join(WarehouseRack, WarehouseShelf.rack_id == WarehouseRack.id)
        .join(WarehouseZone, WarehouseRack.zone_id == WarehouseZone.id)
        .filter(WarehouseZone.warehouse_id == warehouse_id)
        .filter(db.func.lower(WarehouseBin.code) == code.lower())
        .first()
    )
    if existing_bin:
        raise ValidationError("Bin code already exists in this warehouse")

    zone = WarehouseZone.query.filter_by(warehouse_id=warehouse_id, name="Default Zone").first()
    if not zone:
        zone = WarehouseZone(warehouse_id=warehouse_id, name="Default Zone", code="Z1")
        db.session.add(zone)
        db.session.flush()

    rack = WarehouseRack.query.filter_by(zone_id=zone.id, code="R1").first()
    if not rack:
        rack = WarehouseRack(zone_id=zone.id, code="R1")
        db.session.add(rack)
        db.session.flush()

    shelf = WarehouseShelf.query.filter_by(rack_id=rack.id, code="S1").first()
    if not shelf:
        shelf = WarehouseShelf(rack_id=rack.id, code="S1")
        db.session.add(shelf)
        db.session.flush()

    new_bin = WarehouseBin(
        shelf_id=shelf.id,
        code=code,
        description=(data.get("description") or "").strip() or None,
        status=(data.get("status") or "available").strip() or "available",
    )
    db.session.add(new_bin)
    db.session.commit()

    event_bus.publish(
        "WAREHOUSE_UPDATED",
        {"warehouse_id": warehouse_id},
        organisation_id=org_id,
    )

    return jsonify({"message": "Bin created", "id": new_bin.id}), 201


@warehouses_bp.route("/<int:warehouse_id>/bins", methods=["GET"])
@jwt_required_with_user
def get_warehouse_bins(warehouse_id):
    org_id = get_current_organisation_id()
    wh = Warehouse.query.filter_by(id=warehouse_id, organisation_id=org_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    bins = (
        db.session.query(WarehouseBin)
        .join(WarehouseShelf, WarehouseBin.shelf_id == WarehouseShelf.id)
        .join(WarehouseRack, WarehouseShelf.rack_id == WarehouseRack.id)
        .join(WarehouseZone, WarehouseRack.zone_id == WarehouseZone.id)
        .filter(WarehouseZone.warehouse_id == warehouse_id)
        .all()
    )

    return (
        jsonify(
            [
                {
                    "id": b.id,
                    "code": b.code,
                    "status": b.status,
                    "description": b.description,
                }
                for b in bins
            ]
        ),
        200,
    )


@warehouses_bp.route("/<int:warehouse_id>/bins/<int:bin_id>", methods=["PUT"])
@jwt_required_with_user
@require_role("admin", "store_manager")
def update_bin(warehouse_id, bin_id):
    data = request.get_json(silent=True) or {}
    org_id = get_current_organisation_id()

    wh = Warehouse.query.filter_by(id=warehouse_id, organisation_id=org_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    bin_obj = (
        db.session.query(WarehouseBin)
        .join(WarehouseShelf, WarehouseBin.shelf_id == WarehouseShelf.id)
        .join(WarehouseRack, WarehouseShelf.rack_id == WarehouseRack.id)
        .join(WarehouseZone, WarehouseRack.zone_id == WarehouseZone.id)
        .filter(WarehouseZone.warehouse_id == warehouse_id, WarehouseBin.id == bin_id)
        .first()
    )
    if not bin_obj:
        raise NotFoundError("Bin not found")

    if "code" in data:
        code = (data.get("code") or "").strip()
        if not code:
            raise ValidationError("Bin code is required")
        if (
            db.session.query(WarehouseBin)
            .join(WarehouseShelf, WarehouseBin.shelf_id == WarehouseShelf.id)
            .join(WarehouseRack, WarehouseShelf.rack_id == WarehouseRack.id)
            .join(WarehouseZone, WarehouseRack.zone_id == WarehouseZone.id)
            .filter(WarehouseZone.warehouse_id == warehouse_id)
            .filter(db.func.lower(WarehouseBin.code) == code.lower())
            .filter(WarehouseBin.id != bin_id)
            .first()
        ):
            raise ValidationError("Bin code already exists in this warehouse")
        bin_obj.code = code
    if "description" in data:
        bin_obj.description = (data.get("description") or "").strip() or None
    if "status" in data:
        bin_obj.status = (data.get("status") or "available").strip() or "available"

    db.session.commit()
    event_bus.publish(
        "WAREHOUSE_UPDATED",
        {"warehouse_id": warehouse_id},
        organisation_id=org_id,
    )
    return jsonify({"message": "Bin updated", "id": bin_obj.id}), 200


@warehouses_bp.route("/<int:warehouse_id>/bins/<int:bin_id>", methods=["DELETE"])
@jwt_required_with_user
@require_role("admin", "store_manager")
def delete_bin(warehouse_id, bin_id):
    org_id = get_current_organisation_id()

    wh = Warehouse.query.filter_by(id=warehouse_id, organisation_id=org_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    bin_obj = (
        db.session.query(WarehouseBin)
        .join(WarehouseShelf, WarehouseBin.shelf_id == WarehouseShelf.id)
        .join(WarehouseRack, WarehouseShelf.rack_id == WarehouseRack.id)
        .join(WarehouseZone, WarehouseRack.zone_id == WarehouseZone.id)
        .filter(WarehouseZone.warehouse_id == warehouse_id, WarehouseBin.id == bin_id)
        .first()
    )
    if not bin_obj:
        raise NotFoundError("Bin not found")

    db.session.delete(bin_obj)
    db.session.commit()
    event_bus.publish(
        "WAREHOUSE_UPDATED",
        {"warehouse_id": warehouse_id},
        organisation_id=org_id,
    )
    return jsonify({"message": "Bin deleted"}), 200


# ============================================================================
# WAREHOUSE HIERARCHY MANAGEMENT ENDPOINTS
# ============================================================================

@warehouses_bp.route("/hierarchy/main", methods=["GET"])
@jwt_required_with_user
def get_main_warehouse():
    """Get the main warehouse for the organization"""
    org_id = get_current_organisation_id()
    
    try:
        main_warehouse = WarehouseHierarchyService.get_main_warehouse(org_id)
        return jsonify(
            WarehouseHierarchyService.get_warehouse_with_hierarchy(main_warehouse.id, org_id)
        ), 200
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


@warehouses_bp.route("/hierarchy/structure", methods=["GET"])
@jwt_required_with_user
def get_warehouse_hierarchy():
    """Get the complete warehouse hierarchy for the organization"""
    org_id = get_current_organisation_id()
    
    try:
        hierarchy = WarehouseHierarchyService.get_warehouse_hierarchy(org_id)
        return jsonify({"hierarchy": hierarchy}), 200
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


@warehouses_bp.route("/<int:warehouse_id>/set-main", methods=["PATCH"])
@jwt_required_with_user
@require_role("admin")
def set_main_warehouse(warehouse_id):
    """Set a warehouse as the main warehouse for the organization"""
    org_id = get_current_organisation_id()
    
    try:
        main_warehouse = WarehouseHierarchyService.set_main_warehouse(warehouse_id, org_id)
        event_bus.publish(
            "WAREHOUSE_HIERARCHY_CHANGED",
            {"main_warehouse_id": main_warehouse.id, "action": "set_main"},
            organisation_id=org_id
        )
        return jsonify({
            "message": "Main warehouse set successfully",
            "warehouse": WarehouseHierarchyService.get_warehouse_with_hierarchy(warehouse_id, org_id)
        }), 200
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ConflictError as e:
        return jsonify({"error": str(e)}), 409


@warehouses_bp.route("/<int:child_warehouse_id>/set-parent/<int:parent_warehouse_id>", methods=["PATCH"])
@jwt_required_with_user
@require_role("admin")
def set_warehouse_parent(child_warehouse_id, parent_warehouse_id):
    """Set the parent warehouse for a child warehouse"""
    org_id = get_current_organisation_id()
    
    try:
        child = WarehouseHierarchyService.add_child_warehouse(
            child_warehouse_id, parent_warehouse_id, org_id
        )
        event_bus.publish(
            "WAREHOUSE_HIERARCHY_CHANGED",
            {
                "child_warehouse_id": child_warehouse_id,
                "parent_warehouse_id": parent_warehouse_id,
                "action": "set_parent"
            },
            organisation_id=org_id
        )
        return jsonify({
            "message": "Warehouse parent set successfully",
            "warehouse": WarehouseHierarchyService.get_warehouse_with_hierarchy(child_warehouse_id, org_id)
        }), 200
    except (NotFoundError, ValidationError) as e:
        return jsonify({"error": str(e)}), 404
    except ConflictError as e:
        return jsonify({"error": str(e)}), 409


@warehouses_bp.route("/<int:warehouse_id>/move-to/<int:new_parent_warehouse_id>", methods=["PATCH"])
@jwt_required_with_user
@require_role("admin")
def move_warehouse(warehouse_id, new_parent_warehouse_id):
    """Move a warehouse to a different parent in the hierarchy"""
    org_id = get_current_organisation_id()
    
    try:
        warehouse = WarehouseHierarchyService.move_warehouse(
            warehouse_id, new_parent_warehouse_id, org_id
        )
        event_bus.publish(
            "WAREHOUSE_HIERARCHY_CHANGED",
            {
                "warehouse_id": warehouse_id,
                "new_parent_warehouse_id": new_parent_warehouse_id,
                "action": "move_warehouse"
            },
            organisation_id=org_id
        )
        return jsonify({
            "message": "Warehouse moved successfully",
            "warehouse": WarehouseHierarchyService.get_warehouse_with_hierarchy(warehouse_id, org_id)
        }), 200
    except (NotFoundError, ValidationError) as e:
        return jsonify({"error": str(e)}), 404
    except ConflictError as e:
        return jsonify({"error": str(e)}), 409


@warehouses_bp.route("/<int:warehouse_id>/hierarchy-info", methods=["GET"])
@jwt_required_with_user
def get_warehouse_hierarchy_info(warehouse_id):
    """Get hierarchy information for a specific warehouse"""
    org_id = get_current_organisation_id()
    
    try:
        warehouse = Warehouse.query.filter_by(id=warehouse_id, organisation_id=org_id).first()
        if not warehouse:
            raise NotFoundError("Warehouse not found")
        
        info = WarehouseHierarchyService.get_warehouse_with_hierarchy(warehouse_id, org_id)
        return jsonify(info), 200
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
