from datetime import datetime, timedelta

from app.models import InventoryItem, StockMovement
from app.models.organization import Organization
from app.utils.formatted_export import build_csv_document, format_status_label


class ExportService:
    """Analytics CSV exports with institutional formatting."""

    @staticmethod
    def _org_name(org_id: int) -> str:
        org = Organization.query.get(org_id)
        return org.name if org else f"Organization #{org_id}"

    @staticmethod
    def export_movement_history(org_id, days=30):
        from sqlalchemy.orm import joinedload

        threshold = datetime.utcnow() - timedelta(days=days)
        org_name = ExportService._org_name(org_id)

        movements = (
            StockMovement.query.options(joinedload(StockMovement.item))
            .join(InventoryItem)
            .filter(
                InventoryItem.organisation_id == org_id,
                StockMovement.date >= threshold,
            )
            .order_by(StockMovement.date.desc())
            .all()
        )

        headers = [
            "Date & Time",
            "Item Name",
            "SKU",
            "Movement Type",
            "Quantity",
            "Reference",
            "Notes",
        ]
        rows = [
            [
                m.date.isoformat() if m.date else "",
                m.item.name if m.item else "",
                m.item.sku if m.item else "",
                m.type,
                m.quantity,
                m.reference or "",
                (m.notes or "")[:200],
            ]
            for m in movements
        ]

        csv_text = build_csv_document(
            "Inventory Movement History",
            org_name,
            headers,
            rows,
            subtitle=f"Period: last {days} days",
            extra_meta=[f"Total movements: {len(rows)}"],
        )

        def generate():
            yield csv_text

        return generate()

    @staticmethod
    def export_inventory_valuation(org_id):
        org_name = ExportService._org_name(org_id)
        org = Organization.query.get(org_id)
        currency = "KES"
        if org and org.preferences:
            currency = org.preferences.get("currency", currency)

        items = (
            InventoryItem.query.filter_by(organisation_id=org_id, is_active=True)
            .order_by(InventoryItem.name.asc())
            .all()
        )

        headers = [
            "Item Name",
            "SKU",
            "Quantity",
            "Unit",
            "Unit Price",
            "Total Value",
            "Reorder Level",
            "Stock Health",
        ]
        rows = []
        grand_total = 0.0
        for item in items:
            total = float(item.quantity or 0) * float(item.unit_price or 0)
            grand_total += total
            health = "Low Stock" if item.is_low_stock() else "OK"
            rows.append(
                [
                    item.name,
                    item.sku or "",
                    item.quantity,
                    item.unit or "unit",
                    f"{currency} {float(item.unit_price or 0):,.2f}",
                    f"{currency} {total:,.2f}",
                    item.reorder_level,
                    health,
                ]
            )

        csv_text = build_csv_document(
            "Inventory Valuation Report",
            org_name,
            headers,
            rows,
            subtitle=f"Valuation currency: {currency}",
            extra_meta=[f"Portfolio total: {currency} {grand_total:,.2f}"],
        )

        def generate():
            yield csv_text

        return generate()
