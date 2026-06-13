from flask import Blueprint, jsonify
from app.auth_utils import (
    jwt_required_with_user,
    get_current_organisation_id,
    require_role,
)
from app.services.restock_service import RestockService
from app.services.forecasting_service import ForecastingService

restock_bp = Blueprint("restock", __name__)


@restock_bp.route("/alerts", methods=["GET"])
@jwt_required_with_user
def get_alerts():
    """Get active restocking alerts for the organization."""
    org_id = get_current_organisation_id()
    alerts = RestockService.get_pending_alerts(org_id)

    return (
        jsonify(
            [
                {
                    "id": a.id,
                    "item_id": a.item_id,
                    "organisation_id": a.organisation_id,
                    "item_name": a.item.name,
                    "warehouse_id": a.warehouse_id,
                    "warehouse_name": (
                        a.warehouse.name if a.warehouse_id else "Global"
                    ),
                    "severity": a.severity,
                    "current_qty": a.current_quantity,
                    "current_quantity": a.current_quantity,
                    "threshold": a.threshold_level,
                    "threshold_level": a.threshold_level,
                    "status": a.status,
                    "message": a.message,
                    "created_at": a.created_at.isoformat(),
                }
                for a in alerts
            ]
        ),
        200,
    )


@restock_bp.route("/recommendations/<int:item_id>", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "store_manager")
def get_recommendation(item_id):
    """Get AI-assisted replenishment recommendations for an item."""
    org_id = get_current_organisation_id()

    # Verify item ownership
    from app.models import InventoryItem

    item = InventoryItem.query.filter_by(
        id=item_id, organisation_id=org_id
    ).first()
    if not item:
        raise NotFoundError("Inventory item not found")

    days_remaining = ForecastingService.predict_days_remaining(item_id)
    suggested_qty = ForecastingService.get_replenishment_recommendation(
        item_id
    )

    return (
        jsonify(
            {
                "item_id": item_id,
                "days_until_stockout": round(days_remaining, 1),
                "suggested_reorder_quantity": suggested_qty,
                "urgency": (
                    "HIGH"
                    if days_remaining < 7
                    else "MEDIUM" if days_remaining < 14 else "LOW"
                ),
            }
        ),
        201,
    )


@restock_bp.route("/thresholds", methods=["PUT"])
@jwt_required_with_user
@require_role("admin", "store_manager")
def update_thresholds():
    """Update stock thresholds per item/warehouse from frontend."""
    data = request.get_json()
    from app.models import WarehouseStock
    from app.validation import validate_input
    from marshmallow import Schema, fields

    class ThresholdSchema(Schema):
        item_id = fields.Integer(required=True)
        warehouse_id = fields.Integer(required=True)
        min_stock = fields.Integer()
        max_stock = fields.Integer()
        reorder_point = fields.Integer()
        safety_stock = fields.Integer()

    validated_data, errors = validate_input(ThresholdSchema, data)
    if errors:
        return jsonify({"errors": errors}), 400

    stock = WarehouseStock.query.filter_by(
        item_id=validated_data["item_id"],
        warehouse_id=validated_data["warehouse_id"],
    ).first()

    if not stock:
        # Create if not exists
        stock = WarehouseStock(
            item_id=validated_data["item_id"],
            warehouse_id=validated_data["warehouse_id"],
        )
        db.session.add(stock)

    if "min_stock" in validated_data:
        stock.min_stock_level = validated_data["min_stock"]
    if "max_stock" in validated_data:
        stock.max_stock_level = validated_data["max_stock"]
    if "reorder_point" in validated_data:
        stock.reorder_point = validated_data["reorder_point"]
    if "safety_stock" in validated_data:
        stock.safety_stock = validated_data["safety_stock"]

    db.session.commit()
    return jsonify({"message": "Thresholds updated successfully"}), 200


@restock_bp.route("/thresholds", methods=["OPTIONS"])
def update_thresholds_options():
    """CORS preflight for thresholds update endpoint."""
    return ('', 204)
