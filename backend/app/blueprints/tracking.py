from flask import Blueprint, g, jsonify, request
from marshmallow import Schema, fields

from app.auth_utils import get_current_organisation_id, jwt_required_with_user
from app.errors import ValidationError
from app.services.anomaly_service import AnomalyService
from app.services.qr_service import QRService
from app.services.tracking_service import TrackingService
from app.validation import sanitize_string, validate_input

tracking_bp = Blueprint("tracking", __name__)


def _serialize_item_status(item, item_type):
    if item_type == "inventory":
        return "active" if getattr(item, "is_active", True) else "inactive"
    return getattr(item, "status", "unknown")


class ScanRequestSchema(Schema):
    qr_data = fields.String(required=True)
    action_type = fields.String(required=True)
    warehouse_id = fields.Integer()
    bin_id = fields.Integer()
    device_id = fields.String()
    notes = fields.String()
    lat = fields.Float()
    lon = fields.Float()


class VerifyRequestSchema(Schema):
    qr_data = fields.String(required=True)


@tracking_bp.route("/qr/<string:entity_type>/<int:entity_id>", methods=["GET"])
@jwt_required_with_user
def get_entity_qr(entity_type, entity_id):
    """Generate or return signed QR payload for an asset or inventory item."""
    org_id = get_current_organisation_id()
    payload = QRService.get_qr_payload(org_id, entity_type, entity_id)
    return jsonify(payload), 200


@tracking_bp.route("/scan/verify", methods=["POST"])
@jwt_required_with_user
def verify_scan():
    """Verify QR authenticity without mutating state (viewer-safe)."""
    data = request.get_json() or {}
    validated, errors = validate_input(VerifyRequestSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    org_id = get_current_organisation_id()
    result = TrackingService.verify_scan(
        org_id, g.user.id, g.user.role, validated["qr_data"]
    )
    return jsonify(result), 200


@tracking_bp.route("/scan", methods=["POST"])
@jwt_required_with_user
def record_scan():
    """Process a QR scan: validate, log immutable event, apply state if permitted."""
    data = request.get_json()
    org_id = get_current_organisation_id()

    validated_data, errors = validate_input(ScanRequestSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    if "notes" in validated_data:
        validated_data["notes"] = sanitize_string(validated_data["notes"])

    item, event = TrackingService.record_scan(
        org_id=org_id,
        user_id=g.user.id,
        user_role=g.user.role,
        **validated_data,
    )

    history = TrackingService.get_history(org_id, event.item_type, item.id)
    anomalies = AnomalyService.analyze_scan(event)

    return (
        jsonify(
            {
                "message": "Scan recorded successfully",
                "scan_event_id": event.id,
                "item": {
                    "type": event.item_type,
                    "id": item.id,
                    "status": _serialize_item_status(item, event.item_type),
                    "state": event.new_state,
                },
                "history": [
                    TrackingService.serialize_event(h) for h in history
                ],
                "anomalies": anomalies,
            }
        ),
        200,
    )


@tracking_bp.route("/scan", methods=["OPTIONS"])
def record_scan_options():
    return ("", 204)


@tracking_bp.route("/bin-environment/<int:bin_id>", methods=["GET"])
@jwt_required_with_user
def get_bin_environment(bin_id):
    org_id = get_current_organisation_id()
    env_data = TrackingService.get_bin_environment(bin_id, org_id)
    return jsonify(env_data), 200


@tracking_bp.route("/history/<string:item_type>/<int:item_id>", methods=["GET"])
@jwt_required_with_user
def get_item_history(item_type, item_id):
    org_id = get_current_organisation_id()
    history = TrackingService.get_history(org_id, item_type, item_id)

    return (
        jsonify(
            {
                "item_type": item_type,
                "item_id": item_id,
                "history": [
                    TrackingService.serialize_event(h) for h in history
                ],
            }
        ),
        200,
    )


@tracking_bp.route("/allowed-actions", methods=["GET"])
@jwt_required_with_user
def get_allowed_scan_actions():
    """Return scan action types permitted for the current user's role."""
    from app.tracking_rbac import SCAN_ACTION_ROLES

    role = g.user.role
    actions = [
        action
        for action, roles in SCAN_ACTION_ROLES.items()
        if role in roles or role in ("admin", "superadmin")
    ]
    return jsonify({"role": role, "actions": actions}), 200
