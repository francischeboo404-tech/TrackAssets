from decimal import Decimal
from datetime import date, datetime
from uuid import UUID

from flask import g, request

from app import db
from app.models import inventory


class AuditService:
    """Comprehensive audit logging service.

    Important: Audit entries are added to the provided session but are not
    committed by this service by default. This preserves transaction atomicity
    and prevents nested commits. Callers may pass `commit=True` to commit
    explicitly, but prefer committing at the service layer of the business
    operation.
    """

    @staticmethod
    def _sanitize_for_json(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, (list, tuple, set)):
            return [AuditService._sanitize_for_json(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): AuditService._sanitize_for_json(item)
                for key, item in value.items()
            }
        return str(value)

    @staticmethod
    def log_action(
        action,
        entity_type,
        entity_id,
        details=None,
        user_id=None,
        organisation_id=None,
        module=None,
        session=None,
        commit=False,
    ):
        """Log an action to the audit trail.

        Parameters:
        - session: optional SQLAlchemy session to use (defaults to db.session)
        - commit: if True, call session.commit() after adding (use sparingly)
        """
        try:
            sess = session or db.session

            # Get user and organization from request context when not provided
            if user_id is None and hasattr(g, "user"):
                user_id = getattr(g.user, "id", None)
            if organisation_id is None and hasattr(g, "user"):
                organisation_id = getattr(g.user, "organisation_id", None)

            if organisation_id is None:
                # Cannot write audit log without organization context
                # Non-fatal: skip logging
                return

            # Get IP address when in request context
            try:
                ip_address = request.remote_addr
            except RuntimeError:
                ip_address = None
            # Get User-Agent when in request context
            try:
                user_agent = request.headers.get("User-Agent")
            except Exception:
                user_agent = None

            user_role = None
            if hasattr(g, "user") and g.user is not None:
                user_role = getattr(g.user, "role", None)

            enriched_details = (
                {
                    key: AuditService._sanitize_for_json(value)
                    for key, value in details.items()
                }
                if isinstance(details, dict)
                else {}
            )
            if details is not None and not isinstance(details, dict):
                enriched_details = {
                    "payload": AuditService._sanitize_for_json(details)
                }
            if user_role:
                enriched_details["role"] = user_role
            if user_agent:
                enriched_details["user_agent"] = user_agent
            if "previous_state" not in enriched_details and enriched_details.get(
                "old_values"
            ):
                enriched_details["previous_state"] = enriched_details["old_values"]
            if "new_state" not in enriched_details and enriched_details.get(
                "new_values"
            ):
                enriched_details["new_state"] = enriched_details["new_values"]

            audit_log = inventory.AuditLog(
                organisation_id=organisation_id,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                reference=details.get("reference") if isinstance(details, dict) else None,
                module=module,
                details=enriched_details or None,
                ip_address=ip_address,
            )

            sess.add(audit_log)
            if commit:
                sess.commit()

        except Exception as e:
            # Fail-safe: never raise from audit logging. In production this
            # should be logged to a separate monitoring system.
            print(f"Audit logging failed: {e}")

    @staticmethod
    def log_asset_change(
        asset, action, old_values=None, new_values=None, module=None, session=None
    ):
        """Log asset-specific changes"""
        from app.models.asset import AssetAuditLog
        
        sess = session or db.session
        
        log_entry = AssetAuditLog(
            asset_id=asset.id,
            action=action,
            old_values=old_values,
            new_values=new_values,
        )
        sess.add(log_entry)
        
        # Also log to generic AuditLog for organization-level audit trail
        details = {}
        if old_values:
            details["old_values"] = old_values
        if new_values:
            details["new_values"] = new_values

        AuditService.log_action(
            action=action,
            entity_type="asset",
            entity_id=asset.id,
            details=details or None,
            organisation_id=getattr(asset, "organisation_id", None),
            module=module,
            session=session,
        )

    @staticmethod
    def log_inventory_change(
        item, action, quantity_change=None, reference=None, module=None, session=None
    ):
        """Log inventory-specific changes"""
        details = {}
        if quantity_change is not None:
            details["quantity_change"] = quantity_change
        if reference:
            details["reference"] = reference

        AuditService.log_action(
            action=action,
            entity_type="inventory_item",
            entity_id=getattr(item, "id", None),
            details=details or None,
            organisation_id=getattr(item, "organisation_id", None),
            module=module,
            session=session,
        )

    @staticmethod
    def log_user_action(action, details=None, session=None):
        """Log user-related actions"""
        user_id = None
        organisation_id = None
        if hasattr(g, "user"):
            user_id = getattr(g.user, "id", None)
            organisation_id = getattr(g.user, "organisation_id", None)

        AuditService.log_action(
            action=action,
            entity_type="user",
            entity_id=user_id,
            details=details,
            organisation_id=organisation_id,
            session=session,
        )

    @staticmethod
    def log_authentication_event(
        action, user_id=None, details=None, session=None
    ):
        """Log authentication events"""
        AuditService.log_action(
            action=f"AUTH_{action}",
            entity_type="authentication",
            entity_id=user_id,
            details=details,
            session=session,
        )

    @staticmethod
    def log_department_change(department, action, details=None, session=None):
        """Log department-related changes"""
        AuditService.log_action(
            action=action,
            entity_type="department",
            entity_id=getattr(department, "id", None),
            details=details,
            organisation_id=getattr(department, "organisation_id", None),
            session=session,
        )

    @staticmethod
    def log_transfer(asset, from_dept, to_dept, details=None, session=None):
        """Log asset transfers"""
        transfer_details = {
            "from_department": from_dept,
            "to_department": to_dept,
            "asset_code": getattr(asset, "asset_code", None),
        }
        if details:
            transfer_details.update(details)

        AuditService.log_action(
            action="ASSET_TRANSFER",
            entity_type="asset",
            entity_id=getattr(asset, "id", None),
            details=transfer_details,
            organisation_id=getattr(asset, "organisation_id", None),
            session=session,
        )
