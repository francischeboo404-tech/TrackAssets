from datetime import datetime
from flask import Blueprint, jsonify, Response, request, g
from app import limiter
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

from app.cache import cache

CACHE_TTL_SUMMARY = 60   # dashboard summary: 60 s
CACHE_TTL_MOVEMENTS = 120  # movement trends: 2 min


@analytics_bp.route("/dashboard/summary", methods=["GET"])
@jwt_required_with_user
@limiter.limit("60 per minute")
def get_summary():
    """Get high-level dashboard KPIs."""
    org_id = get_current_organisation_id()
    warehouse_id = request.args.get('warehouse_id', type=int)

    role_name = g.user.role.name if g.user and hasattr(g.user.role, 'name') else str(getattr(g.user, 'role', 'user'))
    cache_key = f"analytics:summary:{org_id}:{warehouse_id}:{role_name}"

    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload), 200

    inventory = AnalyticsService.get_inventory_summary(org_id, warehouse_id=warehouse_id)
    valuation = AnalyticsService.get_inventory_valuation(org_id, warehouse_id=warehouse_id)
    assets = AnalyticsService.get_asset_summary(org_id, warehouse_id=warehouse_id)
    geospatial = AnalyticsService.get_geospatial_stats(org_id)
    compliance = AnalyticsService.get_compliance_stats(org_id)
    recent_activity = AnalyticsService.get_recent_activity(org_id, limit=7, warehouse_id=warehouse_id)
    movement_stats = AnalyticsService.get_movement_trends(
        org_id, days=7, warehouse_id=warehouse_id
    )
    insights = AnalyticsService.generate_insights(org_id)

    from app.models.organization import Organization
    org = Organization.query.get(org_id)
    currency = org.preferences.get("currency", "KES") if org and org.preferences else "KES"

    try:
        inv_val = float(valuation or 0)
        asset_val = float(assets.get("total_current_value", 0)) if isinstance(assets, dict) else 0.0
        total_valuation = inv_val + asset_val
    except (TypeError, ValueError):
        total_valuation = 0.0

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

    from flask import g as _g
    filtered_payload = filter_analytics_payload(_g.user.role, payload)

    cache.set(cache_key, filtered_payload, ttl=CACHE_TTL_SUMMARY)
    return jsonify(filtered_payload), 200


@analytics_bp.route("/dashboard/movements", methods=["GET"])
@jwt_required_with_user
@limiter.limit("100 per minute")
def get_movement_trends():
    """Get inventory movement trends for charts."""
    org_id = get_current_organisation_id()
    days = request.args.get("days", 7, type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)

    cache_key = f"analytics:movements:{org_id}:{warehouse_id}:{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached), 200

    trends = AnalyticsService.get_movement_trends(
        org_id, days=days, warehouse_id=warehouse_id
    )
    cache.set(cache_key, trends, ttl=CACHE_TTL_MOVEMENTS)
    return jsonify(trends), 200


@analytics_bp.route("/cache/invalidate", methods=["POST"])
@require_role("admin")
@limiter.limit("10 per minute")
def invalidate_analytics_cache():
    """Force-clear all analytics cache entries for this organisation."""
    org_id = get_current_organisation_id()
    cache.delete_pattern(f"analytics:*:{org_id}:*")
    cache.delete_pattern(f"analytics:summary:{org_id}:*")
    cache.delete_pattern(f"analytics:movements:{org_id}:*")
    return jsonify({"message": "Analytics cache cleared"}), 200


@analytics_bp.route("/dashboard/warehouses", methods=["GET"])
@jwt_required_with_user
@limiter.limit("60 per minute")
def get_warehouses_stats():
    """Get warehouse utilization metrics."""
    org_id = get_current_organisation_id()
    stats = AnalyticsService.get_warehouse_utilization(org_id)
    return jsonify(stats), 200


@analytics_bp.route("/export/movement", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "store_manager")
@limiter.limit("5 per minute")
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
@limiter.limit("5 per minute")
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
@limiter.limit("30 per minute")
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

    # Resume cursor. The standard place for it is the Last-Event-ID header,
    # which the browser sends on its own reconnects; EventSource cannot set
    # headers, so a client driving its own reconnect passes it as a query
    # parameter instead (see useSSE.ts). Anything non-numeric is treated as no
    # cursor at all rather than as an error.
    raw_cursor = request.headers.get("Last-Event-ID") or request.args.get(
        "last_event_id"
    )
    try:
        last_event_id = int(raw_cursor) if raw_cursor else None
    except (TypeError, ValueError):
        last_event_id = None
    if last_event_id is not None and last_event_id < 0:
        last_event_id = None
    
    try:
        gen = event_bus.stream(
            organisation_id=org_id, last_event_id=last_event_id
        )
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
