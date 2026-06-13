from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import StockMovement, InventoryItem


class ForecastingService:
    """Intelligent forecasting for inventory depletion and demand."""

    @staticmethod
    def calculate_daily_velocity(item_id, days=30):
        """Calculate average daily consumption velocity for an item."""
        threshold = datetime.utcnow() - timedelta(days=days)

        # Sum all OUT movements in the period
        total_out = (
            db.session.query(func.sum(StockMovement.quantity))
            .filter(
                StockMovement.item_id == item_id,
                StockMovement.type == "OUT",
                StockMovement.date >= threshold,
            )
            .scalar()
            or 0
        )

        return total_out / days

    @staticmethod
    def predict_days_remaining(item_id):
        """Predict how many days until stock exhaustion based on velocity."""
        item = InventoryItem.query.get(item_id)
        if not item or item.quantity <= 0:
            return 0

        velocity = ForecastingService.calculate_daily_velocity(item_id)
        if velocity <= 0:
            return 999  # Infinite stock at current velocity

        return item.quantity / velocity

    @staticmethod
    def get_replenishment_recommendation(item_id, warehouse_id=None):
        """Suggest reorder quantity based on velocity, lead time, and safety stock."""
        # Simple EOQ-inspired logic or target-max logic
        # For now, let's use TargetMax - CurrentStock
        from app.models import WarehouseStock

        level = (
            WarehouseStock.query.filter_by(
                item_id=item_id, warehouse_id=warehouse_id
            ).first()
            if warehouse_id
            else None
        )

        if not level:
            return 0

        ForecastingService.calculate_daily_velocity(item_id)
        # lead_time_demand = velocity * lead_time

        recommended = level.max_stock_level - level.quantity_available
        return max(0, recommended)
