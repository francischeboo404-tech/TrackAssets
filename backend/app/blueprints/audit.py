from datetime import datetime, timedelta

from flask import Blueprint, Response, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db
from app.auth_utils import (
    get_current_organisation_id,
    jwt_required_with_user,
    require_role,
)
from app.models import inventory

audit_bp = Blueprint("audit", __name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@audit_bp.route("/logs", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "auditor")
@limiter.limit("50 per minute")
def get_audit_logs():
    """Get audit logs for the organization"""
    org_id = get_current_organisation_id()

    # Query parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    entity_type = request.args.get("entity_type")
    action = request.args.get("action")
    q = request.args.get("q")
    user_id = request.args.get("user_id", type=int)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    from app.models.user import User

    query = inventory.AuditLog.query.filter_by(organisation_id=org_id)
    query = query.outerjoin(User, inventory.AuditLog.user_id == User.id)

    if entity_type:
        query = query.filter(inventory.AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(inventory.AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        query = query.filter(inventory.AuditLog.user_id == user_id)
        
    if q:
        query = query.filter(
            db.or_(
                inventory.AuditLog.action.ilike(f"%{q}%"),
                User.username.ilike(f"%{q}%"),
                db.cast(inventory.AuditLog.entity_id, db.String).ilike(f"%{q}%")
            )
        )

    # Date filtering
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.filter(inventory.AuditLog.created_at >= from_date)
        except ValueError:
            pass  # Invalid date format, ignore

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.filter(inventory.AuditLog.created_at <= to_date)
        except ValueError:
            pass  # Invalid date format, ignore

    # Order by most recent first
    query = query.order_by(inventory.AuditLog.created_at.desc())

    logs = query.paginate(page=page, per_page=per_page, error_out=False)

    return (
        jsonify(
            {
                "audit_logs": [
                    {
                        "id": log.id,
                        "action": log.action,
                        "entity_type": log.entity_type,
                        "entity_id": log.entity_id,
                        "user_id": log.user_id,
                        "details": log.details,
                        "ip_address": log.ip_address,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in logs.items
                ],
                "pagination": {
                    "page": logs.page,
                    "per_page": logs.per_page,
                    "total": logs.total,
                    "pages": logs.pages,
                    "has_next": logs.has_next,
                    "has_prev": logs.has_prev,
                },
            }
        ),
        200,
    )


@audit_bp.route("/logs/<int:log_id>", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "auditor")
@limiter.limit("100 per minute")
def get_audit_log(log_id):
    """Get specific audit log entry"""
    org_id = get_current_organisation_id()

    log = inventory.AuditLog.query.filter_by(
        id=log_id, organisation_id=org_id
    ).first()

    if not log:
        from app.errors import NotFoundError

        raise NotFoundError("Audit log not found")

    return (
        jsonify(
            {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "user_id": log.user_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
        ),
        200,
    )


@audit_bp.route("/summary", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "auditor")
@limiter.limit("30 per minute")
def get_audit_summary():
    """Get audit summary statistics"""
    org_id = get_current_organisation_id()

    # Date range (default last 30 days)
    days = request.args.get("days", 30, type=int)
    since_date = datetime.utcnow() - timedelta(days=days)

    # Action counts
    action_counts = (
        db.session.query(
            inventory.AuditLog.action, db.func.count(inventory.AuditLog.id)
        )
        .filter(
            inventory.AuditLog.organisation_id == org_id,
            inventory.AuditLog.created_at >= since_date,
        )
        .group_by(inventory.AuditLog.action)
        .all()
    )

    # Entity type counts
    entity_counts = (
        db.session.query(
            inventory.AuditLog.entity_type,
            db.func.count(inventory.AuditLog.id),
        )
        .filter(
            inventory.AuditLog.organisation_id == org_id,
            inventory.AuditLog.created_at >= since_date,
        )
        .group_by(inventory.AuditLog.entity_type)
        .all()
    )

    # User activity
    user_activity = (
        db.session.query(
            inventory.AuditLog.user_id, db.func.count(inventory.AuditLog.id)
        )
        .filter(
            inventory.AuditLog.organisation_id == org_id,
            inventory.AuditLog.created_at >= since_date,
        )
        .group_by(inventory.AuditLog.user_id)
        .all()
    )

    # Daily activity (last 7 days)
    daily_activity = []
    for i in range(7):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        count = inventory.AuditLog.query.filter(
            inventory.AuditLog.organisation_id == org_id,
            inventory.AuditLog.created_at >= day_start,
            inventory.AuditLog.created_at <= day_end,
        ).count()

        daily_activity.append(
            {"date": day_start.date().isoformat(), "count": count}
        )

    return (
        jsonify(
            {
                "period_days": days,
                "action_breakdown": {
                    action: count for action, count in action_counts
                },
                "entity_breakdown": {
                    entity: count for entity, count in entity_counts
                },
                "user_activity": {
                    str(user_id): count for user_id, count in user_activity
                },
                "daily_activity": daily_activity,
                "total_logs": sum(count for _, count in action_counts),
            }
        ),
        200,
    )


@audit_bp.route("/export", methods=["GET"])
@jwt_required_with_user
@require_role("admin", "auditor")
@limiter.limit("5 per minute")
def export_audit_logs():
    """Export audit logs as a professionally formatted CSV download."""
    from app.models.organization import Organization
    from app.models.user import User
    from app.utils.formatted_export import build_csv_document

    org_id = get_current_organisation_id()
    org = Organization.query.get(org_id)
    org_name = org.name if org else f"Organization #{org_id}"

    since_date = datetime.utcnow() - timedelta(days=90)

    logs = (
        inventory.AuditLog.query.filter(
            inventory.AuditLog.organisation_id == org_id,
            inventory.AuditLog.created_at >= since_date,
        )
        .order_by(inventory.AuditLog.created_at.desc())
        .limit(10000)
        .all()
    )

    headers = [
        "Log ID",
        "Timestamp (UTC)",
        "Action",
        "Entity Type",
        "Entity ID",
        "Username",
        "User Role",
        "IP Address",
        "Details Summary",
    ]
    rows = []
    for log in logs:
        user = User.query.get(log.user_id) if log.user_id else None
        role = ""
        summary = ""
        if isinstance(log.details, dict):
            role = log.details.get("role", user.role if user else "")
            summary = str(
                log.details.get("new_state")
                or log.details.get("old_values")
                or log.details
            )[:500]
        elif log.details:
            summary = str(log.details)[:500]

        rows.append(
            [
                log.id,
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                log.action,
                log.entity_type,
                log.entity_id,
                user.username if user else f"User #{log.user_id}",
                role,
                log.ip_address or "",
                summary.replace("\n", " ").replace("\r", " "),
            ]
        )

    csv_content = build_csv_document(
        "Security Audit Log Export",
        org_name,
        headers,
        rows,
        subtitle="Rolling 90-day compliance window",
        extra_meta=[f"Total entries: {len(rows)}"],
    )

    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
