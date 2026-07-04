from datetime import datetime
from flask import Blueprint, jsonify, Response, request, g
from app.auth_utils import (
    jwt_required_with_user,
    get_current_organisation_id,
    require_role,
)
from app.rbac import filter_analytics_payload, is_read_only_role
from app.services.analytics_service import AnalyticsService
from app.services.export_service import ExportService
from app.services.event_bus import event_bus
from flask_jwt_extended import decode_token
from app.tenant_utils import get_user_by_id, is_token_revoked

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/dashboard/summary", methods=["GET"])
@jwt_required_with_user
def get_summary():
    """Get high-level dashboard KPIs."""
    org_id = get_current_organisation_id()
    warehouse_id = request.args.get('warehouse_id', type=int)

    inventory = AnalyticsService.get_inventory_summary(org_id, warehouse_id=warehouse_id)
    valuation = AnalyticsService.get_inventory_valuation(org_id, warehouse_id=warehouse_id)
    assets = AnalyticsService.get_asset_summary(org_id, warehouse_id=warehouse_id)
    geospatial = AnalyticsService.get_geospatial_stats(org_id)
    compliance = AnalyticsService.get_compliance_stats(org_id)
    recent_activity = AnalyticsService.get_recent_activity(org_id, limit=7)
    movement_stats = AnalyticsService.get_movement_trends(
        org_id, days=7, warehouse_id=warehouse_id
    )
    insights = AnalyticsService.generate_insights(org_id)

    from flask import g
    from app.models.organization import Organization
    org = Organization.query.get(org_id)
    currency = org.preferences.get("currency", "KES") if org and org.preferences else "KES"

    # Robust calculation of total valuation (Inventory + Assets)
    try:
        inv_val = float(valuation or 0)
        asset_val = float(assets.get("total_current_value", 0)) if isinstance(assets, dict) else 0.0
        total_valuation = inv_val + asset_val
    except (TypeError, ValueError):
        total_valuation = 0.0

    from flask import g

    payload = {
        "inventory": inventory,
        "total_valuation": total_valuation,
        "currency": currency,
        "assets": assets,
        "geospatial": geospatial,
        "compliance": compliance,
        "recent_activity": recent_activity,
        "movement_stats": movement_stats,
        "insights": insights,
    }
    return jsonify(filter_analytics_payload(g.user.role, payload)), 200


@analytics_bp.route("/dashboard/movements", methods=["GET"])
@jwt_required_with_user
def get_movement_trends():
    """Get inventory movement trends for charts."""
    org_id = get_current_organisation_id()
    days = request.args.get("days", 7, type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)
    trends = AnalyticsService.get_movement_trends(
        org_id, days=days, warehouse_id=warehouse_id
    )
    return jsonify(trends), 200


@analytics_bp.route("/dashboard/warehouses", methods=["GET"])
@jwt_required_with_user
def get_warehouses_stats():
    """Get warehouse utilization metrics."""
    org_id = get_current_organisation_id()
    stats = AnalyticsService.get_warehouse_utilization(org_id)
    return jsonify(stats), 200


@analytics_bp.route("/export/movement", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "store_manager")
def export_movement():
    """Export movement history as CSV."""
    org_id = get_current_organisation_id()
    generator = ExportService.export_movement_history(org_id)
    return Response(
        generator,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=movement_history_"
                f"{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
            )
        },
    )


@analytics_bp.route("/export/valuation", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "store_manager")
def export_valuation():
    """Export inventory valuation as CSV."""
    org_id = get_current_organisation_id()
    generator = ExportService.export_inventory_valuation(org_id)
    return Response(
        generator,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=inventory_valuation_"
                f"{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
            )
        },
    )


@analytics_bp.route("/stream", methods=["GET"])
def stream_events():
    """Real-time event stream (SSE).

    This endpoint accepts authentication via any of:
    - cookies / Authorization header (standard JWT flow)
    - `access_token` query parameter (useful for EventSource clients)
    The view performs lightweight validation and attaches `g.user`.
    """
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

    # 1) Try standard cookie/header JWT (optional)
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        # ignore, we'll fall back to query param
        pass

    user_obj = None
    try:
        identity = get_jwt_identity()
        if identity:
            user_obj = get_user_by_id(identity)
    except Exception:
        user_obj = None

    # 2) If not authenticated via header/cookie, accept ?access_token=...
    if not user_obj:
        token = request.args.get("access_token")
        if token:
            try:
                decoded = decode_token(token)
            except Exception:
                return jsonify({"success": False, "message": "Invalid token"}), 401

            # Check blocklist
            jti = decoded.get("jti")
            if jti and is_token_revoked(jti):
                return jsonify({"success": False, "message": "Token revoked"}), 401

            identity = decoded.get("sub") or decoded.get("identity")
            user_obj = get_user_by_id(identity)

    if not user_obj:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    # Attach user to request context for downstream RBAC
    g.user = user_obj

    org_id = get_current_organisation_id()
    try:
        gen = event_bus.stream(organisation_id=org_id)
        return Response(
            gen,
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        # If the stream cannot be established, return a Service Unavailable
        from flask import current_app
        current_app.logger.error(f"Failed to start SSE stream: {e}")
        return jsonify({"success": False, "message": "Event stream unavailable"}), 503
