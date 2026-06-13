"""Organization settings business logic."""

import os
from datetime import datetime, timedelta

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.errors import NotFoundError, ValidationError
from app.models.asset import Asset
from app.models.inventory import InventoryItem, StockMovement
from app.utils.formatted_export import (
    build_csv_multi_section,
    format_currency,
    format_status_label,
)

ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "svg"}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2MB

ALLOWED_PREFERENCE_KEYS = {
    "currency",
    "require_2fa",
    "strict_password",
    "session_timeout",
    "daily_digest",
    "critical_alerts",
    "timezone",
    "date_format",
}


class SettingsService:
    @staticmethod
    def get_organization(org_id: int):
        from app.models.organization import Organization

        org = Organization.query.get(org_id)
        if not org:
            raise NotFoundError("Organization not found")
        return org

    @staticmethod
    def serialize_organization(org) -> dict:
        return {
            "id": org.id,
            "name": org.name,
            "code": org.code,
            "description": org.description,
            "logo_url": org.logo_url,
            "preferences": org.preferences or {},
            "is_active": org.is_active,
        }

    @staticmethod
    def update_organization(org, data: dict, user_id: int, org_id: int):
        old_name = org.name
        changes = {}

        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                raise ValidationError("Organization name cannot be empty")
            if len(name) > 255:
                raise ValidationError("Organization name is too long")
            org.name = name
            changes["name"] = name

        if "preferences" in data:
            if not isinstance(data["preferences"], dict):
                raise ValidationError("Preferences must be an object")
            prefs = dict(org.preferences or {})
            for key, value in data["preferences"].items():
                if key not in ALLOWED_PREFERENCE_KEYS:
                    continue
                prefs[key] = SettingsService._normalize_preference(key, value)
            org.preferences = prefs
            changes["preferences"] = prefs

        db.session.commit()
        return org, {"old_name": old_name, "changes": changes}

    @staticmethod
    def _normalize_preference(key: str, value):
        if key == "currency" and isinstance(value, str):
            return value.upper()[:10]
        if key == "session_timeout":
            try:
                timeout = int(value)
            except (TypeError, ValueError):
                raise ValidationError("Session timeout must be a number")
            if timeout not in (30, 60, 240, 480):
                raise ValidationError("Invalid session timeout value")
            return timeout
        if key in ("require_2fa", "strict_password", "daily_digest", "critical_alerts"):
            return bool(value)
        return value

    @staticmethod
    def save_logo(org, file_storage, user_id: int, org_id: int) -> str:
        if not file_storage or not file_storage.filename:
            raise ValidationError("No file selected")

        filename = secure_filename(file_storage.filename)
        if not SettingsService._allowed_logo(filename):
            raise ValidationError("File type not allowed. Use PNG, JPG, or SVG.")

        file_storage.stream.seek(0, os.SEEK_END)
        size = file_storage.stream.tell()
        file_storage.stream.seek(0)
        if size > MAX_LOGO_BYTES:
            raise ValidationError("Logo file must be 2MB or smaller")

        unique_filename = f"{org.code}_{os.urandom(4).hex()}_{filename}"
        upload_folder = os.path.join(
            current_app.root_path, "static", "uploads", "logos"
        )
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, unique_filename)
        file_storage.save(filepath)

        org.logo_url = f"/static/uploads/logos/{unique_filename}"
        db.session.commit()
        return org.logo_url

    @staticmethod
    def _allowed_logo(filename: str) -> bool:
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS
        )

    @staticmethod
    def export_csv(org_id: int) -> str:
        org = SettingsService.get_organization(org_id)
        currency = (org.preferences or {}).get("currency", "KES")

        assets = Asset.query.filter_by(organisation_id=org_id).order_by(
            Asset.asset_code.asc()
        ).all()
        asset_rows = []
        asset_value_total = 0.0
        for asset in assets:
            asset.update_current_value()
            val = float(asset.current_value or 0)
            asset_value_total += val
            asset_rows.append(
                [
                    asset.asset_code,
                    asset.name,
                    asset.type,
                    asset.department.name if asset.department else "",
                    format_status_label(asset.status),
                    format_status_label(asset.condition),
                    asset.location or "",
                    format_currency(val, currency),
                    asset.purchase_date.isoformat() if asset.purchase_date else "",
                ]
            )

        inventory = (
            InventoryItem.query.filter_by(organisation_id=org_id, is_active=True)
            .order_by(InventoryItem.sku.asc())
            .all()
        )
        inv_rows = []
        inv_value_total = 0.0
        for item in inventory:
            line_val = float(item.quantity or 0) * float(item.unit_price or 0)
            inv_value_total += line_val
            inv_rows.append(
                [
                    item.sku or "",
                    item.name,
                    item.quantity,
                    item.unit or "unit",
                    format_currency(item.unit_price, currency),
                    format_currency(line_val, currency),
                    item.reorder_level,
                    "Low Stock" if item.is_low_stock() else "OK",
                ]
            )

        return build_csv_multi_section(
            "Institutional Data Export — Assets & Inventory",
            org.name,
            [
                {
                    "title": "Fixed Assets Register",
                    "headers": [
                        "Asset Code",
                        "Asset Name",
                        "Type",
                        "Department",
                        "Status",
                        "Condition",
                        "Location",
                        "Current Value",
                        "Purchase Date",
                    ],
                    "rows": asset_rows,
                },
                {
                    "title": "Inventory Stock Register",
                    "headers": [
                        "SKU",
                        "Item Name",
                        "Quantity",
                        "Unit",
                        "Unit Price",
                        "Line Value",
                        "Reorder Level",
                        "Health",
                    ],
                    "rows": inv_rows,
                },
            ],
            subtitle=f"Currency: {currency} | Assets: {len(asset_rows)} | SKUs: {len(inv_rows)}",
        )

    @staticmethod
    def purge_old_movements(org_id: int) -> int:
        cutoff = datetime.utcnow() - timedelta(days=3 * 365)
        items = InventoryItem.query.filter_by(organisation_id=org_id).all()
        item_ids = [i.id for i in items]
        deleted = 0
        if item_ids:
            deleted = StockMovement.query.filter(
                StockMovement.item_id.in_(item_ids),
                StockMovement.date < cutoff,
            ).delete(synchronize_session=False)
            db.session.commit()
        return deleted
