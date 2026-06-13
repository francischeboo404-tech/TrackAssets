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
from app.errors import NotFoundError
from app.services.event_bus import event_bus

warehouses_bp = Blueprint("warehouses", __name__)


@warehouses_bp.route("", methods=["GET"])
@jwt_required_with_user
def get_warehouses():
    org_id = get_current_organisation_id()
    warehouses = Warehouse.query.filter_by(organisation_id=org_id).all()
    return (
        jsonify(
            [
                {
                    "id": w.id,
                    "name": w.name,
                    "code": w.code,
                    "is_active": w.is_active,
                }
                for w in warehouses
            ]
        ),
        200,
    )


@warehouses_bp.route("", methods=["POST"])
@jwt_required_with_user
@require_role("admin")
def create_warehouse():
    data = request.get_json()
    org_id = get_current_organisation_id()

    new_warehouse = Warehouse(
        organisation_id=org_id,
        name=data["name"],
        code=data["code"],
        address=data.get("address"),
    )
    db.session.add(new_warehouse)
    db.session.commit()
    
    event_bus.publish("WAREHOUSE_UPDATED", {"warehouse_id": new_warehouse.id}, organisation_id=org_id)

    return (
        jsonify({"message": "Warehouse created", "id": new_warehouse.id}),
        201,
    )


@warehouses_bp.route("/<int:warehouse_id>", methods=["PUT"])
@jwt_required_with_user
@require_role("admin")
def update_warehouse(warehouse_id):
    data = request.get_json()
    org_id = get_current_organisation_id()

    wh = Warehouse.query.filter_by(id=warehouse_id, organisation_id=org_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    if "name" in data:
        wh.name = data["name"]
    if "code" in data:
        wh.code = data["code"]
    if "address" in data:
        wh.address = data["address"]

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
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Ensure warehouse exists and belongs to org
    wh = Warehouse.query.filter_by(
        id=warehouse_id, organisation_id=org_id
    ).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    # Simplify for MVP: if zone/rack/shelf doesn't exist, create defaults
    zone = WarehouseZone.query.filter_by(
        warehouse_id=warehouse_id, name="Default Zone"
    ).first()
    if not zone:
        zone = WarehouseZone(
            warehouse_id=warehouse_id, name="Default Zone", code="Z1"
        )
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
        code=data["code"],
        description=data.get("description"),
        status="available",
    )
    db.session.add(new_bin)
    db.session.commit()
    
    event_bus.publish("WAREHOUSE_UPDATED", {"warehouse_id": warehouse_id}, organisation_id=org_id)

    return jsonify({"message": "Bin created", "id": new_bin.id}), 201


@warehouses_bp.route("/<int:warehouse_id>/bins", methods=["GET"])
@jwt_required_with_user
def get_warehouse_bins(warehouse_id):
    org_id = get_current_organisation_id()
    # Check warehouse ownership
    wh = Warehouse.query.filter_by(
        id=warehouse_id, organisation_id=org_id
    ).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    # Custom join to fetch all bins for the warehouse
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
