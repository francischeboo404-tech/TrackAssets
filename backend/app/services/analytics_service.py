from sqlalchemy import func
from app import db
from app.models import InventoryItem, StockMovement
from datetime import datetime, timedelta


class AnalyticsService:
    """Service for computing enterprise-grade analytics and KPIs."""

    @staticmethod
    def get_inventory_summary(org_id, warehouse_id=None):
        """Get high-level inventory distribution (Health)."""
        # Count items by status/levels
        from app.models import RestockAlert
        from app.models.stock_levels import WarehouseStock

        if warehouse_id:
            total_items = db.session.query(func.sum(WarehouseStock.quantity_on_hand)).filter(
                WarehouseStock.warehouse_id == warehouse_id
            ).scalar() or 0
        else:
            total_items = db.session.query(func.sum(InventoryItem.quantity)).filter(
                InventoryItem.organisation_id == org_id,
                InventoryItem.is_active == True
            ).scalar() or 0

        # Consolidate into a single aggregation query
        alert_query = db.session.query(
            RestockAlert.severity, func.count(RestockAlert.id)
        ).filter_by(organisation_id=org_id, status="PENDING")
        
        if warehouse_id:
            alert_query = alert_query.filter_by(warehouse_id=warehouse_id)
            
        alert_counts = alert_query.group_by(RestockAlert.severity).all()

        counts_map = {severity: count for severity, count in alert_counts}

        low_stock = counts_map.get("LOW", 0)
        critical_stock = counts_map.get("CRITICAL", 0)
        out_of_stock = counts_map.get("OUT_OF_STOCK", 0)

        # Sum quantities of items with pending alerts
        items_alerts_query = db.session.query(func.sum(RestockAlert.current_quantity)).filter_by(organisation_id=org_id, status="PENDING")
        if warehouse_id:
            items_alerts_query = items_alerts_query.filter_by(warehouse_id=warehouse_id)
            
        items_with_alerts = items_alerts_query.scalar() or 0

        return {
            "total_items": total_items,
            "health": {
                "healthy": max(0, total_items - items_with_alerts) if total_items > 0 else 0,
                "low": counts_map.get("LOW", 0),
                "critical": counts_map.get("CRITICAL", 0),
                "out_of_stock": counts_map.get("OUT_OF_STOCK", 0),
            },
        }

    @staticmethod
    def get_warehouse_utilization(org_id):
        """Calculate bin occupancy per warehouse using a single aggregated query."""
        from app.models import (
            Warehouse,
            WarehouseBin,
            WarehouseZone,
            WarehouseRack,
            WarehouseShelf,
        )

        # Aggregate totals and occupied counts per warehouse
        results = (
            db.session.query(
                Warehouse.id,
                Warehouse.name,
                func.count(WarehouseBin.id).label("total_bins"),
                func.sum(
                    db.case((WarehouseBin.status == "occupied", 1), else_=0)
                ).label("occupied_bins"),
            )
            .select_from(Warehouse)
            .outerjoin(
                WarehouseZone, WarehouseZone.warehouse_id == Warehouse.id
            )
            .outerjoin(
                WarehouseRack, WarehouseRack.zone_id == WarehouseZone.id
            )
            .outerjoin(
                WarehouseShelf, WarehouseShelf.rack_id == WarehouseRack.id
            )
            .outerjoin(
                WarehouseBin, WarehouseBin.shelf_id == WarehouseShelf.id
            )
            .filter(Warehouse.organisation_id == org_id)
            .group_by(Warehouse.id, Warehouse.name)
            .all()
        )

        return [
            {
                "warehouse_id": r.id,
                "warehouse_name": r.name,
                "total_bins": r.total_bins,
                "occupied_bins": int(r.occupied_bins or 0),
                "empty_bins": max(0, (r.total_bins or 0) - int(r.occupied_bins or 0)),
                "utilization_percentage": (
                    round((int(r.occupied_bins or 0) / r.total_bins * 100), 1)
                    if r.total_bins > 0
                    else 0
                ),
            }
            for r in results
        ]

    @staticmethod
    def get_movement_trends(org_id, days=7, warehouse_id=None):
        """Get daily movement volume for time-series charts."""
        threshold = datetime.utcnow() - timedelta(days=days)

        query = (
            db.session.query(
                func.date(StockMovement.date).label("day"),
                StockMovement.type,
                func.count(StockMovement.id).label("count"),
            )
            .join(InventoryItem)
            .filter(
                InventoryItem.organisation_id == org_id,
                StockMovement.date >= threshold,
            )
        )

        if warehouse_id:
            from app.models.stock_levels import WarehouseStock

            query = query.join(
                WarehouseStock, WarehouseStock.item_id == InventoryItem.id
            ).filter(WarehouseStock.warehouse_id == warehouse_id)

        movements = query.group_by("day", StockMovement.type).all()

        # Reformat for frontend charts
        results = {}
        # Pre-fill with last N days to ensure chart always has x-axis points
        for i in range(days):
            d = (datetime.utcnow() - timedelta(days=i)).date()
            results[str(d)] = {"IN": 0, "OUT": 0}

        for day, m_type, count in movements:
            d_str = str(day)
            if d_str in results:
                results[d_str][m_type] = count
            else:
                results[d_str] = {"IN": 0, "OUT": 0}
                results[d_str][m_type] = count

        return results

    @staticmethod
    def get_inventory_valuation(org_id, warehouse_id=None):
        """Calculate total monetary value of inventory on hand."""
        from app.models.stock_levels import WarehouseStock
        
        if warehouse_id:
            value = (
                db.session.query(
                    func.sum(WarehouseStock.quantity_on_hand * InventoryItem.unit_price)
                )
                .join(WarehouseStock)
                .filter(
                    InventoryItem.organisation_id == org_id,
                    InventoryItem.is_active == True,
                    WarehouseStock.warehouse_id == warehouse_id
                )
                .scalar()
                or 0
            )
        else:
            value = (
                db.session.query(
                    func.sum(InventoryItem.quantity * InventoryItem.unit_price)
                )
                .filter(
                    InventoryItem.organisation_id == org_id,
                    InventoryItem.is_active == True
                )
                .scalar()
                or 0
            )

        return round(value, 2)

    @staticmethod
    def get_asset_summary(org_id, warehouse_id=None):
        """Get asset valuation, ROI and status breakdown."""
        from app.models.asset import Asset
        
        query = Asset.query.filter(
            Asset.organisation_id == org_id,
            Asset.status.notin_(['requested', 'disposed', 'rejected'])
        )
        
        if warehouse_id:
            query = query.filter(Asset.warehouse_id == warehouse_id)
            
        assets = query.all()
        
        total_assets = len(assets)
        total_purchase_value = 0.0
        total_current_value = 0.0
        
        for a in assets:
            a.update_current_value() # Dynamically recalculate real-time current value
            total_purchase_value += float(a.purchase_value or 0)
            total_current_value += float(a.current_value or 0)
        
        roi = round(((total_current_value - total_purchase_value) / total_purchase_value * 100) if total_purchase_value > 0 else 0, 2)
        
        # Calculate ROI for the last 30 days vs 30-60 days ago
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)

        def get_roi_for_period(start_date, end_date=None):
            query = Asset.query.filter(
                Asset.organisation_id == org_id, 
                Asset.created_at >= start_date,
                Asset.status.notin_(['requested', 'disposed', 'rejected'])
            )
            
            if warehouse_id:
                query = query.filter(Asset.warehouse_id == warehouse_id)
            
            if end_date:
                query = query.filter(Asset.created_at < end_date)
            
            assets_period = query.all()
            p_val = 0.0
            c_val = 0.0
            for a in assets_period:
                a.update_current_value() # Dynamically recalculate real-time current value
                p_val += float(a.purchase_value or 0)
                c_val += float(a.current_value or 0)
                
            return round(((c_val - p_val) / p_val * 100) if p_val > 0 else 0, 2)

        recent_roi = get_roi_for_period(thirty_days_ago)
        prev_roi = get_roi_for_period(sixty_days_ago, thirty_days_ago)
        
        roi_diff = round(recent_roi - prev_roi, 2)
        trend = {
            "value": abs(roi_diff),
            "isUp": roi_diff >= 0
        }
        
        status_counts_query = db.session.query(
            Asset.status, func.count(Asset.id)
        ).filter(Asset.organisation_id == org_id)
        
        if warehouse_id:
            status_counts_query = status_counts_query.filter(Asset.warehouse_id == warehouse_id)
            
        status_counts = status_counts_query.group_by(Asset.status).all()
        
        return {
            "total_assets": total_assets,
            "total_purchase_value": total_purchase_value,
            "total_current_value": total_current_value,
            "roi": roi,
            "trend": trend,
            "status_breakdown": {status: count for status, count in status_counts}
        }

    @staticmethod
    def get_geospatial_stats(org_id):
        """Get distribution of assets across warehouses."""
        from app.models.location_topology import Warehouse
        from app.models.asset import Asset
        
        total_nodes = Warehouse.query.filter_by(organisation_id=org_id, is_active=True).count()
        
        results = db.session.query(
            Warehouse.name,
            func.count(Asset.id)
        ).outerjoin(Asset, Asset.warehouse_id == Warehouse.id).filter(
            Warehouse.organisation_id == org_id
        ).group_by(Warehouse.name).all()
        
        total_assigned = sum(count for _, count in results)
        
        distribution = [
            {
                "name": name,
                "count": count,
                "pct": round((count / total_assigned * 100), 1) if total_assigned > 0 else 0
            }
            for name, count in results
        ]
        
        return {
            "total_nodes": total_nodes,
            "distribution": distribution
        }

    @staticmethod
    def get_compliance_stats(org_id):
        """Calculate compliance score based on variance."""
        from app.models.inventory import StockMovement, InventoryItem
        
        def get_stats_for_period(start_date=None, end_date=None):
            query_total = db.session.query(func.count(StockMovement.id)).join(
                InventoryItem
            ).filter(InventoryItem.organisation_id == org_id)
            
            query_manual = db.session.query(func.count(StockMovement.id)).join(
                InventoryItem
            ).filter(
                InventoryItem.organisation_id == org_id,
                db.or_(
                    StockMovement.reference.ilike("%Manual%"),
                    StockMovement.notes.ilike("%Manual%")
                )
            )

            if start_date:
                query_total = query_total.filter(StockMovement.date >= start_date)
                query_manual = query_manual.filter(StockMovement.date >= start_date)
            if end_date:
                query_total = query_total.filter(StockMovement.date < end_date)
                query_manual = query_manual.filter(StockMovement.date < end_date)

            total_m = query_total.scalar() or 0
            manual_m = query_manual.scalar() or 0
            variance = round((manual_m / total_m * 100) if total_m > 0 else 0.00, 2)
            score = round(100.0 - variance, 2)
            return variance, score

        # Overall compliance
        audit_variance, compliance_score = get_stats_for_period()
        
        # 30-day trend
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)
        
        recent_variance, recent_score = get_stats_for_period(thirty_days_ago)
        prev_variance, prev_score = get_stats_for_period(sixty_days_ago, thirty_days_ago)
        
        score_diff = round(recent_score - prev_score, 2)
        trend = {
            "value": abs(score_diff),
            "isUp": score_diff >= 0
        }
        
        variance_diff = round(audit_variance - recent_variance, 2)
        variance_trend = {
            "value": abs(variance_diff),
            "isUp": variance_diff >= 0
        }
        
        return {
            "audit_variance": audit_variance,
            "compliance_score": compliance_score,
            "trend": trend,
            "variance_trend": variance_trend
        }

    @staticmethod
    def get_recent_activity(org_id, limit=10):
        """Get recent audit log stream."""
        from app.models.inventory import AuditLog
        
        logs = db.session.query(AuditLog).filter_by(organisation_id=org_id).order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "details": log.details,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]

    @staticmethod
    def generate_insights(org_id):
        """Generate actionable business intelligence insights from current database aggregations."""
        insights = []
        
        # Insight 1: Asset ROI
        asset_summary = AnalyticsService.get_asset_summary(org_id)
        trend = asset_summary.get("trend", {"value": 0, "isUp": True})
        if trend["isUp"]:
            insights.append({
                "id": "asset_roi_up",
                "type": "positive",
                "title": "Asset Utilization Up",
                "description": f"Asset ROI has improved by {trend['value']}% over the last 30 days.",
                "value": f"+{trend['value']}%",
                "trend": "Improving"
            })
        else:
            insights.append({
                "id": "asset_roi_down",
                "type": "warning",
                "title": "Value Depreciation",
                "description": f"Asset ROI has decreased by {trend['value']}% recently.",
                "value": f"-{trend['value']}%",
                "trend": "Declining"
            })
            
        # Insight 2: Inventory Health
        inv_summary = AnalyticsService.get_inventory_summary(org_id)
        critical = inv_summary.get("health", {}).get("critical", 0)
        out_of_stock = inv_summary.get("health", {}).get("out_of_stock", 0)
        low = inv_summary.get("health", {}).get("low", 0)
        
        if out_of_stock > 0 or critical > 0:
            insights.append({
                "id": "inv_critical",
                "type": "negative",
                "title": "Stock Depletion Alert",
                "description": f"{out_of_stock} items out of stock, {critical} at critical levels. Action required.",
                "value": f"{out_of_stock + critical} Items",
                "trend": "Critical"
            })
        elif low > 0:
            insights.append({
                "id": "inv_low",
                "type": "warning",
                "title": "Low Stock Warning",
                "description": f"{low} items have fallen below their recommended reorder levels.",
                "value": f"{low} Items",
                "trend": "Warning"
            })
            
        # Insight 3: Valuation Info
        valuation = AnalyticsService.get_inventory_valuation(org_id)
        insights.append({
            "id": "valuation_info",
            "type": "info",
            "title": "Current Inventory Value",
            "description": "Total monetary value of active inventory currently on hand.",
            "value": f"{valuation:,.2f}",
            "trend": "Stable"
        })
        
        return insights
