from datetime import datetime

from app.models.asset import Asset
from app.models.organization import Organization
from app.utils.formatted_export import format_currency, format_status_label
from app.utils.reporting_engines import ProfessionalExcelReport, ProfessionalPDFReport


class ReportingService:
    """Institutional PDF and Excel reports."""

    @staticmethod
    def _org_context(org_id):
        org = Organization.query.get(org_id)
        currency = "KES"
        if org and org.preferences:
            currency = org.preferences.get("currency", currency)
        return org, currency

    @staticmethod
    def get_asset_register(org_id, format="pdf", date_from=None, date_to=None):
        org, currency = ReportingService._org_context(org_id)
        query = Asset.query.filter_by(organisation_id=org_id)

        if date_from:
            query = query.filter(Asset.created_at >= date_from)
        if date_to:
            query = query.filter(Asset.created_at <= date_to)

        assets = query.order_by(Asset.asset_code.asc()).all()

        headers = [
            "Asset Code",
            "Asset Name",
            "Type",
            "Department",
            "Location",
            "Status",
            "Condition",
            "Current Value",
        ]
        data = []
        total_value = 0.0
        for asset in assets:
            asset.update_current_value()
            val = float(asset.current_value or 0)
            total_value += val
            data.append(
                [
                    asset.asset_code,
                    asset.name,
                    asset.type,
                    asset.department.name if asset.department else "N/A",
                    asset.location or "N/A",
                    format_status_label(asset.status),
                    format_status_label(asset.condition),
                    format_currency(val, currency),
                ]
            )

        subtitle = f"Records: {len(data)} | Total value: {format_currency(total_value, currency)}"
        if date_from or date_to:
            subtitle += f" | Filtered date range applied"

        if format == "excel":
            return ProfessionalExcelReport.generate(
                "Master Asset Register",
                headers,
                data,
                org_name=org.name,
                subtitle=subtitle,
                sheet_title="Asset Register",
            )

        report = ProfessionalPDFReport(
            "Master Asset Register",
            org.name,
            landscape_mode=True,
            subtitle=subtitle,
        )
        report.create_table([headers] + data)
        return report.generate()

    @staticmethod
    def get_inventory_register(org_id, format="excel", date_from=None, date_to=None):
        from app.models.inventory import InventoryItem

        org, currency = ReportingService._org_context(org_id)
        query = InventoryItem.query.filter_by(organisation_id=org_id, is_active=True)
        if date_from:
            query = query.filter(InventoryItem.created_at >= date_from)
        if date_to:
            query = query.filter(InventoryItem.created_at <= date_to)

        items = query.order_by(InventoryItem.sku.asc()).all()

        headers = [
            "SKU",
            "Item Name",
            "Quantity",
            "Unit",
            "Unit Price",
            "Line Value",
            "Reorder Level",
            "Status",
        ]
        data = []
        total = 0.0
        for item in items:
            line = float(item.quantity or 0) * float(item.unit_price or 0)
            total += line
            data.append(
                [
                    item.sku or "",
                    item.name,
                    item.quantity,
                    item.unit or "unit",
                    format_currency(item.unit_price, currency),
                    format_currency(line, currency),
                    item.reorder_level,
                    "Low Stock" if item.is_low_stock() else "In Stock",
                ]
            )

        subtitle = f"SKUs: {len(data)} | Total value: {format_currency(total, currency)}"

        if format == "pdf":
            report = ProfessionalPDFReport(
                "Inventory Stock Register",
                org.name,
                landscape_mode=True,
                subtitle=subtitle,
            )
            report.create_table([headers] + data)
            return report.generate()

        return ProfessionalExcelReport.generate(
            "Inventory Stock Register",
            headers,
            data,
            org_name=org.name,
            subtitle=subtitle,
            sheet_title="Inventory",
        )

    @staticmethod
    def get_condition_report(org_id, condition="repair", date_from=None, date_to=None):
        org, currency = ReportingService._org_context(org_id)
        query = Asset.query.filter_by(organisation_id=org_id, condition=condition)

        if date_from:
            query = query.filter(Asset.created_at >= date_from)
        if date_to:
            query = query.filter(Asset.created_at <= date_to)

        assets = query.order_by(Asset.asset_code.asc()).all()

        title = (
            "Maintenance & Repair Schedule"
            if condition == "repair"
            else "Disposal & Condemned Assets"
        )
        headers = [
            "Asset Code",
            "Asset Name",
            "Department",
            "Location",
            "Condition",
            "Status",
            "Current Value",
        ]
        data = []
        for asset in assets:
            asset.update_current_value()
            data.append(
                [
                    asset.asset_code,
                    asset.name,
                    asset.department.name if asset.department else "",
                    asset.location or "N/A",
                    format_status_label(asset.condition),
                    format_status_label(asset.status),
                    format_currency(asset.current_value, currency),
                ]
            )

        report = ProfessionalPDFReport(
            title,
            org.name,
            subtitle=f"Assets listed: {len(data)}",
        )
        report.create_table([headers] + data)
        return report.generate()

    @staticmethod
    def get_audit_trail(org_id, date_from=None, date_to=None):
        from app.models.inventory import AuditLog
        from app.models.user import User

        org, _currency = ReportingService._org_context(org_id)
        query = AuditLog.query.filter_by(organisation_id=org_id)

        if date_from:
            query = query.filter(AuditLog.created_at >= date_from)
        if date_to:
            query = query.filter(AuditLog.created_at <= date_to)

        logs = query.order_by(AuditLog.created_at.desc()).limit(1000).all()

        headers = [
            "Timestamp (UTC)",
            "Action",
            "Entity Type",
            "Entity ID",
            "User",
            "Role",
            "IP Address",
            "Summary",
        ]
        data = []
        for log in logs:
            user = User.query.get(log.user_id) if log.user_id else None
            username = user.username if user else f"ID {log.user_id}"
            role = ""
            if isinstance(log.details, dict):
                role = log.details.get("role", user.role if user else "")
            summary = ""
            if isinstance(log.details, dict):
                summary = str(log.details.get("new_state") or log.details)[:80]
            else:
                summary = str(log.details)[:80] if log.details else ""

            data.append(
                [
                    log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    log.action,
                    log.entity_type,
                    log.entity_id,
                    username,
                    role,
                    log.ip_address or "",
                    summary,
                ]
            )

        report = ProfessionalPDFReport(
            "Security & Compliance Audit Trail",
            org.name,
            landscape_mode=True,
            subtitle=f"Entries: {len(data)} (max 1,000 most recent)",
        )
        report.create_table([headers] + data)
        return report.generate()

    @staticmethod
    def get_department_summary(org_id, date_from=None, date_to=None):
        from app.models.organization import Department

        org, currency = ReportingService._org_context(org_id)
        depts = Department.query.filter_by(organisation_id=org_id).order_by(
            Department.name.asc()
        ).all()

        headers = [
            "Department",
            "Asset Count",
            "Total Value",
            "Condition: Good",
            "Condition: Fair",
            "Condition: Repair",
            "Condition: Condemned",
        ]
        data = []
        for dept in depts:
            query = Asset.query.filter_by(department_id=dept.id)
            if date_from:
                query = query.filter(Asset.created_at >= date_from)
            if date_to:
                query = query.filter(Asset.created_at <= date_to)
            assets = query.all()
            for asset in assets:
                asset.update_current_value()

            total_val = sum(float(a.current_value or 0) for a in assets)
            data.append(
                [
                    dept.name,
                    len(assets),
                    format_currency(total_val, currency),
                    len([a for a in assets if a.condition == "good"]),
                    len([a for a in assets if a.condition == "fair"]),
                    len([a for a in assets if a.condition == "repair"]),
                    len([a for a in assets if a.condition == "condemned"]),
                ]
            )

        return ProfessionalExcelReport.generate(
            "Departmental Asset Summary",
            headers,
            data,
            org_name=org.name,
            subtitle="Aggregated valuation by department",
            sheet_title="By Department",
        )

    @staticmethod
    def export_combined_workbook(org_id, date_from=None, date_to=None):
        """Excel workbook with Asset + Inventory sheets."""
        from app.models.inventory import InventoryItem

        org_obj, currency = ReportingService._org_context(org_id)
        # Assets sheet data
        aq = Asset.query.filter_by(organisation_id=org_id)
        if date_from:
            aq = aq.filter(Asset.created_at >= date_from)
        if date_to:
            aq = aq.filter(Asset.created_at <= date_to)
        assets = aq.order_by(Asset.asset_code.asc()).all()
        asset_headers = [
            "Asset Code",
            "Asset Name",
            "Type",
            "Department",
            "Location",
            "Status",
            "Condition",
            "Current Value",
        ]
        asset_rows = []
        for a in assets:
            a.update_current_value()
            asset_rows.append(
                [
                    a.asset_code,
                    a.name,
                    a.type,
                    a.department.name if a.department else "",
                    a.location or "N/A",
                    format_status_label(a.status),
                    format_status_label(a.condition),
                    format_currency(a.current_value, currency),
                ]
            )

        iq = InventoryItem.query.filter_by(organisation_id=org_id, is_active=True)
        if date_from:
            iq = iq.filter(InventoryItem.created_at >= date_from)
        if date_to:
            iq = iq.filter(InventoryItem.created_at <= date_to)
        items = iq.order_by(InventoryItem.sku.asc()).all()
        inv_headers = [
            "SKU",
            "Item Name",
            "Quantity",
            "Unit",
            "Unit Price",
            "Line Value",
            "Reorder Level",
            "Status",
        ]
        inv_rows = []
        for item in items:
            line = float(item.quantity or 0) * float(item.unit_price or 0)
            inv_rows.append(
                [
                    item.sku or "",
                    item.name,
                    item.quantity,
                    item.unit or "unit",
                    format_currency(item.unit_price, currency),
                    format_currency(line, currency),
                    item.reorder_level,
                    "Low Stock" if item.is_low_stock() else "In Stock",
                ]
            )

        return ProfessionalExcelReport.generate_multi_sheet(
            org_obj.name,
            "Institutional Export Workbook",
            [
                {
                    "title": "Master Asset Register",
                    "headers": asset_headers,
                    "rows": asset_rows,
                    "sheet_title": "Assets",
                },
                {
                    "title": "Inventory Stock Register",
                    "headers": inv_headers,
                    "rows": inv_rows,
                    "sheet_title": "Inventory",
                },
            ],
        )
