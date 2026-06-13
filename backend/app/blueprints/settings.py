from datetime import datetime

from flask import Blueprint, Response, jsonify, request, g

from app.auth_utils import (
    get_current_organisation_id,
    jwt_required_with_user,
    require_role,
)
from app.audit_service import AuditService
from app.services.settings_service import SettingsService
from app.services.event_bus import event_bus

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/organization", methods=["GET"])
@jwt_required_with_user
@require_role("admin")
def get_organization_settings():
    """Fetch organization configuration (admin only)."""
    org_id = get_current_organisation_id()
    org = SettingsService.get_organization(org_id)
    return jsonify(
        {
            "success": True,
            "organization": SettingsService.serialize_organization(org),
        }
    ), 200


@settings_bp.route("/organization", methods=["PUT"])
@jwt_required_with_user
@require_role("admin")
def update_organization_settings():
    """Update organization name and whitelisted preferences."""
    org_id = get_current_organisation_id()
    org = SettingsService.get_organization(org_id)
    data = request.get_json() or {}

    org, audit_details = SettingsService.update_organization(
        org, data, g.user.id, org_id
    )

    AuditService.log_action(
        action="UPDATE_SETTINGS",
        entity_type="organization",
        entity_id=org.id,
        details=audit_details,
        user_id=g.user.id,
        organisation_id=org_id,
    )

    event_bus.publish(
        "ORGANIZATION_UPDATE",
        {"name": org.name, "preferences": org.preferences},
        organisation_id=org_id,
    )

    return jsonify(
        {
            "success": True,
            "message": "Organization settings updated successfully",
            "organization": SettingsService.serialize_organization(org),
        }
    ), 200


@settings_bp.route("/organization", methods=["OPTIONS"])
def organization_options():
    return ("", 204)


@settings_bp.route("/organization/logo", methods=["POST"])
@jwt_required_with_user
@require_role("admin")
def upload_organization_logo():
    """Upload organization logo (max 2MB)."""
    org_id = get_current_organisation_id()
    org = SettingsService.get_organization(org_id)

    if "logo" not in request.files:
        return jsonify({"success": False, "message": "No file part in the request"}), 400

    logo_url = SettingsService.save_logo(org, request.files["logo"], g.user.id, org_id)

    AuditService.log_action(
        action="UPLOAD_LOGO",
        entity_type="organization",
        entity_id=org.id,
        details={"logo_url": logo_url},
        user_id=g.user.id,
        organisation_id=org_id,
    )

    event_bus.publish("ORGANIZATION_UPDATE", {"logo_url": logo_url}, organisation_id=org_id)

    return jsonify(
        {
            "success": True,
            "message": "Logo uploaded successfully",
            "logo_url": logo_url,
        }
    ), 200


@settings_bp.route("/organization/logo", methods=["OPTIONS"])
def upload_organization_logo_options():
    return ("", 204)


@settings_bp.route("/organization/export", methods=["POST"])
@jwt_required_with_user
@require_role("admin")
def export_system_data():
    """Export assets and inventory as CSV."""
    org_id = get_current_organisation_id()
    csv_data = SettingsService.export_csv(org_id)

    AuditService.log_action(
        action="DATA_EXPORT",
        entity_type="organization",
        entity_id=org_id,
        details={"format": "csv"},
        user_id=g.user.id,
        organisation_id=org_id,
    )

    filename = f"institutional_export_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@settings_bp.route("/organization/export", methods=["OPTIONS"])
def export_system_data_options():
    return ("", 204)


@settings_bp.route("/organization/purge", methods=["DELETE"])
@jwt_required_with_user
@require_role("admin")
def purge_historical_data():
    """Delete stock movement logs older than 3 years."""
    org_id = get_current_organisation_id()
    deleted_count = SettingsService.purge_old_movements(org_id)
    cutoff = datetime.utcnow()

    AuditService.log_action(
        action="DATA_PURGE",
        entity_type="organization",
        entity_id=org_id,
        details={
            "records_deleted": deleted_count,
            "cutoff_years": 3,
        },
        user_id=g.user.id,
        organisation_id=org_id,
    )

    return jsonify(
        {
            "success": True,
            "message": f"Successfully purged {deleted_count} historical records.",
            "records_deleted": deleted_count,
        }
    ), 200


@settings_bp.route("/organization/purge", methods=["OPTIONS"])
def purge_historical_data_options():
    return ("", 204)

