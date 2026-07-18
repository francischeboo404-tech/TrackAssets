from datetime import datetime

from flask import Blueprint, g, jsonify, request, send_file

from app import limiter
from app.auth_utils import (
    get_current_organisation_id,
    jwt_required_with_user,
    require_role,
)
from app.rbac import assert_can_access_report, filter_report_payload
from app.services.report_analytics_service import ReportAnalyticsService
from app.services.reporting_service import ReportingService
from app.cache import cache

reports_bp = Blueprint("reports", __name__)
CACHE_TTL_REPORTS = 120


def _report_json(data, message="Report generated successfully"):
    return jsonify({"success": True, "data": data, "message": message}), 200


def _department_scope():
    """Department name filter for procurement_officer / dept_head users."""
    role = getattr(g.user, "role", None)
    if role in ("dept_head", "procurement_officer") and getattr(g.user, "department", None):
        return g.user.department
    return None


@reports_bp.route("/assets", methods=["GET"])
@jwt_required_with_user
@limiter.limit("60 per minute")
def report_assets():
    """JSON asset analytics for charts (server-aggregated)."""
    assert_can_access_report(g.user.role, "assets")
    org_id = get_current_organisation_id()
    days = request.args.get("days", 30, type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)
    # allow admins to request a specific department by id
    dept_id = request.args.get("department_id", type=int)
    department_name = _department_scope()
    if dept_id and g.user.role == 'admin':
        from app.models.organization import Department
        dept = Department.query.filter_by(id=dept_id, organisation_id=org_id, is_active=True).first()
        if dept:
            department_name = dept.name

    role_name = g.user.role.name if g.user and hasattr(g.user.role, 'name') else str(getattr(g.user, 'role', 'user'))
    cache_key = f"reports:assets:{org_id}:{warehouse_id}:{dept_id}:{days}:{role_name}"

    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return _report_json(cached_data)

    data = ReportAnalyticsService.get_assets_report(
        org_id, days=days, department_name=department_name, warehouse_id=warehouse_id
    )
    data = filter_report_payload(g.user.role, "assets", data)
    cache.set(cache_key, data, ttl=CACHE_TTL_REPORTS)
    return _report_json(data)


@reports_bp.route("/inventory", methods=["GET"])
@jwt_required_with_user
@limiter.limit("60 per minute")
def report_inventory():
    """JSON inventory analytics for charts."""
    assert_can_access_report(g.user.role, "inventory")
    org_id = get_current_organisation_id()
    days = request.args.get("days", 30, type=int)
    dept_id = request.args.get("department_id", type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)
    department_name = _department_scope()
    
    if department_name and not dept_id:
        from app.models.organization import Department
        dept = Department.query.filter_by(name=department_name, organisation_id=org_id, is_active=True).first()
        if dept:
            dept_id = dept.id

    role_name = g.user.role.name if g.user and hasattr(g.user.role, 'name') else str(getattr(g.user, 'role', 'user'))
    cache_key = f"reports:inventory:{org_id}:{warehouse_id}:{dept_id}:{days}:{role_name}"

    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return _report_json(cached_data)

    data = ReportAnalyticsService.get_inventory_report(
        org_id, days=days, department_id=dept_id, warehouse_id=warehouse_id
    )
    data = filter_report_payload(g.user.role, "inventory", data)
    cache.set(cache_key, data, ttl=CACHE_TTL_REPORTS)
    return _report_json(data)


@reports_bp.route("/tracking", methods=["GET"])
@jwt_required_with_user
@limiter.limit("60 per minute")
def report_tracking():
    """JSON tracking / scan / activity analytics."""
    assert_can_access_report(g.user.role, "tracking")
    org_id = get_current_organisation_id()
    days = request.args.get("days", 30, type=int)
    dept_id = request.args.get("department_id", type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)
    department_name = _department_scope()
    
    if department_name and not dept_id:
        from app.models.organization import Department
        dept = Department.query.filter_by(name=department_name, organisation_id=org_id, is_active=True).first()
        if dept:
            dept_id = dept.id

    role_name = g.user.role.name if g.user and hasattr(g.user.role, 'name') else str(getattr(g.user, 'role', 'user'))
    cache_key = f"reports:tracking:{org_id}:{warehouse_id}:{dept_id}:{days}:{role_name}"

    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return _report_json(cached_data)

    data = ReportAnalyticsService.get_tracking_report(
        org_id, days=days, department_id=dept_id, warehouse_id=warehouse_id
    )
    data = filter_report_payload(g.user.role, "tracking", data)
    cache.set(cache_key, data, ttl=CACHE_TTL_REPORTS)
    return _report_json(data)


@reports_bp.route("/dashboard", methods=["GET"])
@jwt_required_with_user
@limiter.limit("60 per minute")
def report_dashboard():
    """Unified procurement intelligence dashboard payload."""
    assert_can_access_report(g.user.role, "dashboard")
    org_id = get_current_organisation_id()
    days = request.args.get("days", 30, type=int)
    dept_id = request.args.get("department_id", type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)
    department_name = _department_scope()
    if dept_id and g.user.role == 'admin':
        from app.models.organization import Department
        dept = Department.query.filter_by(id=dept_id, organisation_id=org_id, is_active=True).first()
        if dept:
            department_name = dept.name

    role_name = g.user.role.name if g.user and hasattr(g.user.role, 'name') else str(getattr(g.user, 'role', 'user'))
    cache_key = f"reports:dashboard:{org_id}:{warehouse_id}:{dept_id}:{days}:{role_name}"

    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return _report_json(cached_data)

    data = ReportAnalyticsService.get_dashboard_report(
        org_id, days=days, department_name=department_name, warehouse_id=warehouse_id
    )
    data = filter_report_payload(g.user.role, "dashboard", data)
    cache.set(cache_key, data, ttl=CACHE_TTL_REPORTS)
    return _report_json(data)


def parse_dates():
    date_from_str = request.args.get("date_from")
    date_to_str = request.args.get("date_to")
    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.fromisoformat(date_from_str.replace("Z", "+00:00"))
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.fromisoformat(date_to_str.replace("Z", "+00:00"))
        except ValueError:
            pass
    return date_from, date_to


def _dated_filename(base: str, ext: str) -> str:
    return f"{base}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.{ext}"


@reports_bp.route("/asset-register", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "auditor")
@limiter.limit("5 per minute")
def export_asset_register():
    org_id = get_current_organisation_id()
    fmt = request.args.get("format", "pdf")
    date_from, date_to = parse_dates()

    file_buffer = ReportingService.get_asset_register(
        org_id, format=fmt, date_from=date_from, date_to=date_to
    )

    if fmt == "excel":
        mimetype = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        ext = "xlsx"
    else:
        mimetype = "application/pdf"
        ext = "pdf"

    return send_file(
        file_buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=_dated_filename("asset_register", ext),
    )


@reports_bp.route("/inventory-register", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "auditor", "store_manager")
@limiter.limit("5 per minute")
def export_inventory_register():
    org_id = get_current_organisation_id()
    fmt = request.args.get("format", "excel")
    date_from, date_to = parse_dates()

    file_buffer = ReportingService.get_inventory_register(
        org_id, format=fmt, date_from=date_from, date_to=date_to
    )

    if fmt == "pdf":
        return send_file(
            file_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=_dated_filename("inventory_register", "pdf"),
        )

    return send_file(
        file_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=_dated_filename("inventory_register", "xlsx"),
    )


@reports_bp.route("/full-export", methods=["GET"])
@jwt_required_with_user
@require_role("admin")
@limiter.limit("3 per minute")
def export_full_workbook():
    """Combined Excel workbook: Assets + Inventory sheets."""
    org_id = get_current_organisation_id()
    date_from, date_to = parse_dates()
    file_buffer = ReportingService.export_combined_workbook(
        org_id, date_from=date_from, date_to=date_to
    )
    return send_file(
        file_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=_dated_filename("institutional_export", "xlsx"),
    )


@reports_bp.route("/maintenance", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "store_manager")
@limiter.limit("5 per minute")
def export_maintenance_report():
    org_id = get_current_organisation_id()
    date_from, date_to = parse_dates()
    file_buffer = ReportingService.get_condition_report(
        org_id, condition="repair", date_from=date_from, date_to=date_to
    )
    return send_file(
        file_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=_dated_filename("maintenance_report", "pdf"),
    )


@reports_bp.route("/disposal", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "store_manager")
@limiter.limit("5 per minute")
def export_disposal_report():
    org_id = get_current_organisation_id()
    date_from, date_to = parse_dates()
    file_buffer = ReportingService.get_condition_report(
        org_id, condition="condemned", date_from=date_from, date_to=date_to
    )
    return send_file(
        file_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=_dated_filename("disposal_report", "pdf"),
    )


@reports_bp.route("/audit-trail", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "auditor")
@limiter.limit("5 per minute")
def export_audit_report():
    org_id = get_current_organisation_id()
    date_from, date_to = parse_dates()
    file_buffer = ReportingService.get_audit_trail(
        org_id, date_from=date_from, date_to=date_to
    )
    return send_file(
        file_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=_dated_filename("audit_trail", "pdf"),
    )


@reports_bp.route("/department-summary", methods=["GET"])
@jwt_required_with_user
@require_role("admin")
@limiter.limit("5 per minute")
def export_dept_summary():
    org_id = get_current_organisation_id()
    date_from, date_to = parse_dates()
    file_buffer = ReportingService.get_department_summary(
        org_id, date_from=date_from, date_to=date_to
    )
    return send_file(
        file_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=_dated_filename("department_summary", "xlsx"),
    )
