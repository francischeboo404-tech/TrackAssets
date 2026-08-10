from flask import Blueprint, g, jsonify, request
from marshmallow import Schema, fields

from app import limiter
from app.auth_utils import get_current_organisation_id, jwt_required_with_user
from app.errors import ValidationError, NotFoundError, ConflictError
from flask import current_app
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
@limiter.limit("30 per minute")
def get_entity_qr(entity_type, entity_id):
    """Generate or return signed QR payload for an asset or inventory item."""
    org_id = get_current_organisation_id()
    payload = QRService.get_qr_payload(org_id, entity_type, entity_id)
    return jsonify(payload), 200


@tracking_bp.route("/scan/verify", methods=["POST"])
@jwt_required_with_user
@limiter.limit("60 per minute")
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
@limiter.limit("30 per minute")
def record_scan():
    """Process a QR scan: validate, log immutable event, apply state if permitted."""
    data = request.get_json()
    org_id = get_current_organisation_id()

    validated_data, errors = validate_input(ScanRequestSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    if "notes" in validated_data:
        validated_data["notes"] = sanitize_string(validated_data["notes"])

    try:
        item, event, anomalies = TrackingService.record_scan(
            org_id=org_id,
            user_id=g.user.id,
            user_role=g.user.role,
            **validated_data,
        )

        history = TrackingService.get_history(org_id, event.item_type, item.id)

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
    except ValidationError as ve:
        current_app.logger.warning("Validation error during scan: %s", ve)
        return jsonify({"message": str(ve)}), 400
    except ConflictError as ce:
        current_app.logger.info("Duplicate scan suppressed: %s", ce)
        return jsonify({"message": str(ce)}), 409
    except NotFoundError as nfe:
        current_app.logger.info("Scan target not found: %s", nfe)
        return jsonify({"message": str(nfe)}), 404
    except Exception as e:
        # Log full traceback for diagnosis and return generic JSON to client
        current_app.logger.exception("Unhandled error while recording scan")
        return jsonify({"message": "Internal server error while processing scan"}), 500


@tracking_bp.route("/scan", methods=["OPTIONS"])
def record_scan_options():
    return ("", 204)


@tracking_bp.route("/bin-environment/<int:bin_id>", methods=["GET"])
@jwt_required_with_user
@limiter.limit("60 per minute")
def get_bin_environment(bin_id):
    org_id = get_current_organisation_id()
    env_data = TrackingService.get_bin_environment(bin_id, org_id)
    return jsonify(env_data), 200


@tracking_bp.route("/history/<string:item_type>/<int:item_id>", methods=["GET"])
@jwt_required_with_user
@limiter.limit("100 per minute")
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


@tracking_bp.route("/live-positions", methods=["GET"])
@jwt_required_with_user
@limiter.limit("60 per minute")
def get_live_positions():
    """Return the latest GPS-tagged scan event per item for the organisation."""
    from app import db
    from app.models.scan_event import ScanEvent
    from sqlalchemy import func

    org_id = get_current_organisation_id()

    subq = (
        db.session.query(
            ScanEvent.item_type,
            ScanEvent.item_id,
            func.max(ScanEvent.timestamp).label("latest"),
        )
        .filter(
            ScanEvent.organisation_id == org_id,
            ScanEvent.latitude.isnot(None),
            ScanEvent.longitude.isnot(None),
            ScanEvent.validation_status == "verified",
        )
        .group_by(ScanEvent.item_type, ScanEvent.item_id)
        .subquery()
    )

    events = (
        db.session.query(ScanEvent)
        .join(
            subq,
            (ScanEvent.item_type == subq.c.item_type)
            & (ScanEvent.item_id == subq.c.item_id)
            & (ScanEvent.timestamp == subq.c.latest),
        )
        .filter(ScanEvent.organisation_id == org_id)
        .all()
    )

    return jsonify([
        {
            "item_type": e.item_type,
            "item_id": e.item_id,
            "lat": e.latitude,
            "lon": e.longitude,
            "action": e.action_type,
            "timestamp": e.timestamp.isoformat(),
            "warehouse_id": e.warehouse_id,
        }
        for e in events
    ]), 200


@tracking_bp.route("/allowed-actions", methods=["GET"])
@jwt_required_with_user
@limiter.limit("100 per minute")
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


@tracking_bp.route("/misplaced-items", methods=["GET"])
@jwt_required_with_user
@limiter.limit("30 per minute")
def get_misplaced_items():
    """Get a list of misplaced items across the organization."""
    org_id = get_current_organisation_id()
    limit = request.args.get("limit", default=50, type=int)

    try:
        misplaced = AnomalyService.predict_misplaced_items(org_id, limit=limit)
        return (
            jsonify(
                {
                    "misplaced_items": misplaced,
                    "count": len(misplaced),
                    "total": len(misplaced),
                }
            ),
            200,
        )
    except Exception as e:
        current_app.logger.exception("Error fetching misplaced items")
        return jsonify({"message": "Error fetching misplaced items"}), 500
