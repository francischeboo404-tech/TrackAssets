"""
Enterprise report aggregations — all metrics computed server-side (SQLAlchemy).
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func

from app import db
from app.models import InventoryItem, StockMovement
from app.models.asset import Asset
from app.models.organization import Organization
from app.services.analytics_service import AnalyticsService

# Simple in-process cache: key -> (expires_at, payload)
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 60

STATUS_LABELS = {
    "requested": "Pending",
    "approved": "Approved",
    "rejected": "Rejected",
    "in_use": "In Use",
    "maintenance": "Maintenance",
    "disposed": "Disposed",
}

PIE_COLORS = {
    "Pending": "#6366f1",
    "Approved": "#3b82f6",
    "Rejected": "#94a3b8",
    "In Use": "#10b981",
    "Maintenance": "#f59e0b",
    "Disposed": "#f43f5e",
}


def _cache_key(org_id: int, report: str, days: int, scope: str) -> str:
    return f"{org_id}:{report}:{days}:{scope}"


def _cache_get(key: str) -> Any | None:
    entry = _CACHE.get(key)
    if not entry:
        return None
    expires, payload = entry
    if time.time() > expires:
        _CACHE.pop(key, None)
        return None
    return payload


def _cache_set(key: str, payload: Any) -> None:
    _CACHE[key] = (time.time() + _CACHE_TTL_SECONDS, payload)


def _org_currency(org_id: int) -> str:
    org = Organization.query.get(org_id)
    if org and org.preferences:
        return org.preferences.get("currency", "KES")
    return "KES"


def _parse_days(days: int | None) -> int:
    if days is None or days < 1:
        return 30
    return min(days, 365)


def _department_asset_filter(query, department_name: str | None):
    """Scope assets to a department name (dept_head)."""
    if not department_name:
        return query
    from app.models.organization import Department

    return query.join(Department, Asset.department_id == Department.id).filter(
        Department.name == department_name
    )


class ReportAnalyticsService:
    """SQL-backed report payloads for JSON analytics APIs."""

    @staticmethod
    def get_assets_report(
        org_id: int,
        days: int = 30,
        department_name: str | None = None,
    ) -> dict:
        days = _parse_days(days)
        scope = department_name or "org"
        key = _cache_key(org_id, "assets", days, scope)
        cached = _cache_get(key)
        if cached:
            return cached

        base = Asset.query.filter(Asset.organisation_id == org_id)
        base = _department_asset_filter(base, department_name)

        total_count = base.count()

        status_rows = (
            db.session.query(Asset.status, func.count(Asset.id))
            .filter(Asset.organisation_id == org_id)
        )
        if department_name:
            from app.models.organization import Department

            status_rows = status_rows.join(
                Department, Asset.department_id == Department.id
            ).filter(Department.name == department_name)
        status_rows = status_rows.group_by(Asset.status).all()

        status_counts = {s: c for s, c in status_rows}
        by_status = []
        for code, label in STATUS_LABELS.items():
            count = status_counts.get(code, 0)
            by_status.append(
                {
                    "code": code,
                    "label": label,
                    "count": count,
                    "percentage": round(
                        (count / total_count * 100) if total_count else 0, 1
                    ),
                    "color": PIE_COLORS.get(label, "#64748b"),
                }
            )

        from app.models.organization import Department

        dept_rows = (
            db.session.query(Department.name, func.count(Asset.id))
            .join(Asset, Asset.department_id == Department.id)
            .filter(Asset.organisation_id == org_id)
            .group_by(Department.name)
            .order_by(func.count(Asset.id).desc())
            .all()
        )
        if department_name:
            dept_rows = [(n, c) for n, c in dept_rows if n == department_name]

        dept_total = sum(c for _, c in dept_rows) or 1
        by_department = [
            {
                "department": name,
                "count": count,
                "percentage": round(count / dept_total * 100, 1),
            }
            for name, count in dept_rows
        ]

        # Utilization: in_use / (all except disposed & rejected)
        active_denominator = sum(
            c
            for s, c in status_counts.items()
            if s not in ("disposed", "rejected")
        )
        in_use_count = status_counts.get("in_use", 0)
        utilization_rate = round(
            (in_use_count / active_denominator * 100) if active_denominator else 0,
            1,
        )

        threshold = datetime.utcnow() - timedelta(days=days)
        from app.models.inventory import AuditLog

        lifecycle_logs = (
            db.session.query(AuditLog)
            .filter(
                AuditLog.organisation_id == org_id,
                AuditLog.entity_type == "asset",
                AuditLog.action == "ASSET_STATUS_CHANGED",
                AuditLog.created_at >= threshold,
            )
            .order_by(AuditLog.created_at.asc())
            .all()
        )

        lifecycle_by_day: dict[str, dict[str, int]] = {}
        for log in lifecycle_logs:
            day = log.created_at.date().isoformat()
            if day not in lifecycle_by_day:
                lifecycle_by_day[day] = {k: 0 for k in STATUS_LABELS}
            new_status = None
            if isinstance(log.details, dict):
                nv = log.details.get("new_values")
                if isinstance(nv, dict):
                    new_status = nv.get("status")
            if new_status and new_status in STATUS_LABELS:
                lifecycle_by_day[day][new_status] += 1

        lifecycle_series = []
        for i in range(days):
            d = (datetime.utcnow() - timedelta(days=days - 1 - i)).date().isoformat()
            counts = lifecycle_by_day.get(d, {k: 0 for k in STATUS_LABELS})
            lifecycle_series.append(
                {
                    "date": d,
                    "total": sum(counts.values()),
                    **{
                        STATUS_LABELS[k]: counts.get(k, 0)
                        for k in STATUS_LABELS
                    },
                }
            )

        location_rows = (
            db.session.query(Asset.location, func.count(Asset.id))
            .filter(
                Asset.organisation_id == org_id,
                Asset.location.isnot(None),
                Asset.location != "",
            )
        )
        if department_name:
            location_rows = _department_asset_filter(location_rows, department_name)
        location_rows = (
            location_rows.group_by(Asset.location)
            .order_by(func.count(Asset.id).desc())
            .limit(15)
            .all()
        )
        by_location = [
            {"location": loc or "Unassigned", "count": cnt}
            for loc, cnt in location_rows
        ]

        payload = {
            "total_count": total_count,
            "by_status": by_status,
            "by_department": by_department,
            "by_location": by_location,
            "utilization_rate": utilization_rate,
            "utilization_detail": {
                "in_use": in_use_count,
                "active_pool": active_denominator,
            },
            "lifecycle_over_time": lifecycle_series,
            "period_days": days,
            "currency": _org_currency(org_id),
        }
        _cache_set(key, payload)
        return payload

    @staticmethod
    def get_inventory_report(org_id: int, days: int = 30) -> dict:
        days = _parse_days(days)
        key = _cache_key(org_id, "inventory", days, "org")
        cached = _cache_get(key)
        if cached:
            return cached

        inv_base = InventoryItem.query.filter_by(
            organisation_id=org_id, is_active=True
        )

        total_skus = inv_base.count()
        total_units = (
            db.session.query(func.sum(InventoryItem.quantity))
            .filter_by(organisation_id=org_id, is_active=True)
            .scalar()
            or 0
        )

        items = inv_base.all()
        low_stock_items = []
        overstock_items = []
        for item in items:
            qty = int(item.quantity or 0)
            reorder = int(item.reorder_level or 0)
            if item.is_low_stock():
                low_stock_items.append(
                    {
                        "id": item.id,
                        "sku": item.sku,
                        "name": item.name,
                        "quantity": qty,
                        "reorder_level": reorder,
                    }
                )
            if reorder > 0 and qty > reorder * 3:
                overstock_items.append(
                    {
                        "id": item.id,
                        "sku": item.sku,
                        "name": item.name,
                        "quantity": qty,
                        "reorder_level": reorder,
                        "overage_ratio": round(qty / reorder, 1),
                    }
                )

        top_stock = (
            db.session.query(
                InventoryItem.id,
                InventoryItem.sku,
                InventoryItem.name,
                InventoryItem.quantity,
                InventoryItem.unit,
            )
            .filter_by(organisation_id=org_id, is_active=True)
            .order_by(InventoryItem.quantity.desc())
            .limit(12)
            .all()
        )
        stock_levels_chart = [
            {
                "sku": row.sku or f"ID-{row.id}",
                "name": row.name[:24],
                "quantity": int(row.quantity or 0),
                "unit": row.unit or "unit",
            }
            for row in top_stock
        ]

        threshold = datetime.utcnow() - timedelta(days=days)
        movement_rows = (
            db.session.query(
                func.date(StockMovement.date).label("day"),
                StockMovement.type,
                func.sum(StockMovement.quantity).label("qty"),
            )
            .join(InventoryItem)
            .filter(
                InventoryItem.organisation_id == org_id,
                StockMovement.date >= threshold,
            )
            .group_by("day", StockMovement.type)
            .all()
        )

        movement_by_day: dict[str, dict[str, int]] = {}
        for day, m_type, qty in movement_rows:
            d = str(day)
            if d not in movement_by_day:
                movement_by_day[d] = {"IN": 0, "OUT": 0}
            movement_by_day[d][m_type] = int(qty or 0)

        movement_series = []
        for i in range(days):
            d = (datetime.utcnow() - timedelta(days=days - 1 - i)).date().isoformat()
            flows = movement_by_day.get(d, {"IN": 0, "OUT": 0})
            movement_series.append(
                {
                    "date": d,
                    "inflow": flows["IN"],
                    "outflow": flows["OUT"],
                    "net": flows["IN"] - flows["OUT"],
                }
            )

        consumed = (
            db.session.query(
                InventoryItem.id,
                InventoryItem.sku,
                InventoryItem.name,
                func.sum(StockMovement.quantity).label("consumed"),
            )
            .join(StockMovement, StockMovement.item_id == InventoryItem.id)
            .filter(
                InventoryItem.organisation_id == org_id,
                StockMovement.type == "OUT",
                StockMovement.date >= threshold,
            )
            .group_by(InventoryItem.id, InventoryItem.sku, InventoryItem.name)
            .order_by(func.sum(StockMovement.quantity).desc())
            .limit(10)
            .all()
        )
        most_consumed = [
            {
                "id": r.id,
                "sku": r.sku,
                "name": r.name,
                "quantity_out": int(r.consumed or 0),
            }
            for r in consumed
        ]

        usage_frequency = [
            {
                "sku": r.sku or f"ID-{r.id}",
                "name": r.name[:20],
                "frequency": int(r.consumed or 0),
            }
            for r in consumed[:8]
        ]

        valuation = AnalyticsService.get_inventory_valuation(org_id)

        payload = {
            "total_skus": total_skus,
            "total_units": int(total_units),
            "total_valuation": valuation,
            "currency": _org_currency(org_id),
            "low_stock_count": len(low_stock_items),
            "overstock_count": len(overstock_items),
            "low_stock_items": low_stock_items[:20],
            "overstock_items": overstock_items[:20],
            "stock_levels_chart": stock_levels_chart,
            "movement_over_time": movement_series,
            "most_consumed": most_consumed,
            "usage_frequency": usage_frequency,
            "period_days": days,
        }
        _cache_set(key, payload)
        return payload

    @staticmethod
    def get_tracking_report(org_id: int, days: int = 30) -> dict:
        days = _parse_days(days)
        key = _cache_key(org_id, "tracking", days, "org")
        cached = _cache_get(key)
        if cached:
            return cached

        threshold = datetime.utcnow() - timedelta(days=days)
        from app.models.scan_event import ScanEvent
        from app.models.inventory import AuditLog
        from app.models.user import User

        total_scans = (
            ScanEvent.query.filter(
                ScanEvent.organisation_id == org_id,
                ScanEvent.timestamp >= threshold,
            ).count()
        )

        scans_by_day_rows = (
            db.session.query(
                func.date(ScanEvent.timestamp).label("day"),
                func.count(ScanEvent.id),
            )
            .filter(
                ScanEvent.organisation_id == org_id,
                ScanEvent.timestamp >= threshold,
            )
            .group_by("day")
            .all()
        )
        scans_map = {str(day): cnt for day, cnt in scans_by_day_rows}
        activity_frequency = []
        for i in range(days):
            d = (datetime.utcnow() - timedelta(days=days - 1 - i)).date().isoformat()
            activity_frequency.append(
                {"date": d, "scans": scans_map.get(d, 0)}
            )

        scans_by_action = (
            db.session.query(ScanEvent.action_type, func.count(ScanEvent.id))
            .filter(
                ScanEvent.organisation_id == org_id,
                ScanEvent.timestamp >= threshold,
            )
            .group_by(ScanEvent.action_type)
            .all()
        )

        scans_by_role = (
            db.session.query(ScanEvent.user_role, func.count(ScanEvent.id))
            .filter(
                ScanEvent.organisation_id == org_id,
                ScanEvent.timestamp >= threshold,
                ScanEvent.user_role.isnot(None),
            )
            .group_by(ScanEvent.user_role)
            .all()
        )

        audit_logs = AuditLog.query.filter(
            AuditLog.organisation_id == org_id,
            AuditLog.created_at >= threshold,
        ).all()
        role_counts: dict[str, int] = {}
        for log in audit_logs:
            role = "unknown"
            if isinstance(log.details, dict):
                role = log.details.get("role") or role
            role_counts[role] = role_counts.get(role, 0) + 1
        actions_per_role = [
            {"role": r, "count": c}
            for r, c in sorted(role_counts.items(), key=lambda x: -x[1])
        ]

        recent_scans = (
            ScanEvent.query.filter_by(organisation_id=org_id)
            .order_by(ScanEvent.timestamp.desc())
            .limit(25)
            .all()
        )
        scan_timeline = []
        for ev in reversed(recent_scans):
            user = User.query.get(ev.user_id) if ev.user_id else None
            scan_timeline.append(
                {
                    "id": ev.id,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                    "action_type": ev.action_type,
                    "item_type": ev.item_type,
                    "item_id": ev.item_id,
                    "user": user.username if user else None,
                    "role": ev.user_role,
                    "validation_status": ev.validation_status,
                }
            )

        recent_audit = AnalyticsService.get_recent_activity(org_id, limit=15)

        payload = {
            "total_scans": total_scans,
            "scans_by_action": [
                {"action": a, "count": c} for a, c in scans_by_action
            ],
            "scans_by_role": [
                {"role": r or "unknown", "count": c} for r, c in scans_by_role
            ],
            "actions_per_role": actions_per_role,
            "activity_frequency": activity_frequency,
            "movement_timeline": scan_timeline,
            "recent_system_events": recent_audit,
            "period_days": days,
        }
        _cache_set(key, payload)
        return payload

    @staticmethod
    def get_dashboard_report(
        org_id: int,
        days: int = 30,
        department_name: str | None = None,
    ) -> dict:
        days = _parse_days(days)
        scope = department_name or "org"
        key = _cache_key(org_id, "dashboard", days, scope)
        cached = _cache_get(key)
        if cached:
            return cached

        assets = ReportAnalyticsService.get_assets_report(
            org_id, days, department_name
        )
        inventory = ReportAnalyticsService.get_inventory_report(org_id, days)
        tracking = ReportAnalyticsService.get_tracking_report(org_id, days)

        asset_summary = AnalyticsService.get_asset_summary(org_id)
        inv_summary = AnalyticsService.get_inventory_summary(org_id)
        compliance = AnalyticsService.get_compliance_stats(org_id)
        movement_stats = AnalyticsService.get_movement_trends(org_id, days=days)
        valuation = AnalyticsService.get_inventory_valuation(org_id)

        try:
            total_valuation = round(
                float(valuation or 0)
                + float(asset_summary.get("total_current_value", 0)),
                2,
            )
        except (TypeError, ValueError):
            total_valuation = 0.0

        critical_alerts = []
        if inventory["low_stock_count"] > 0:
            critical_alerts.append(
                {
                    "severity": "warning",
                    "title": "Low Stock",
                    "message": f"{inventory['low_stock_count']} SKU(s) below reorder level",
                    "count": inventory["low_stock_count"],
                }
            )
        disposed = next(
            (s["count"] for s in assets["by_status"] if s["code"] == "disposed"),
            0,
        )
        if disposed > 0:
            critical_alerts.append(
                {
                    "severity": "info",
                    "title": "Disposed Assets",
                    "message": f"{disposed} asset(s) marked disposed",
                    "count": disposed,
                }
            )
        maintenance = next(
            (s["count"] for s in assets["by_status"] if s["code"] == "maintenance"),
            0,
        )
        if maintenance > 0:
            critical_alerts.append(
                {
                    "severity": "warning",
                    "title": "Maintenance Queue",
                    "message": f"{maintenance} asset(s) in maintenance",
                    "count": maintenance,
                }
            )
        pending = next(
            (s["count"] for s in assets["by_status"] if s["code"] == "requested"),
            0,
        )
        if pending > 0:
            critical_alerts.append(
                {
                    "severity": "info",
                    "title": "Pending Approval",
                    "message": f"{pending} asset request(s) awaiting approval",
                    "count": pending,
                }
            )

        payload = {
            "kpis": {
                "total_assets": assets["total_count"],
                "total_inventory_units": inventory["total_units"],
                "total_skus": inventory["total_skus"],
                "inventory_valuation": valuation,
                "asset_book_value": asset_summary.get("total_current_value", 0),
                "total_valuation": total_valuation,
                "currency": _org_currency(org_id),
                "compliance_score": compliance.get("compliance_score", 0),
                "utilization_rate": assets["utilization_rate"],
                "scan_activity": tracking["total_scans"],
                "low_stock_count": inventory["low_stock_count"],
            },
            "assets": assets,
            "inventory": inventory,
            "tracking": tracking,
            "movement_trends": movement_stats,
            "inventory_health": inv_summary.get("health", {}),
            "asset_roi": asset_summary.get("roi", 0),
            "critical_alerts": critical_alerts,
            "recent_activity": tracking["recent_system_events"],
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        _cache_set(key, payload)
        return payload
