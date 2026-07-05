from app import db
from app.models.kenya_gov_models import VarianceReport
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from datetime import datetime, timezone
from app.services.stock_service import StockService
from app.db_utils import transaction_retry

class LedgerService:
    @staticmethod
    @staticmethod
    @transaction_retry(max_retries=3)
    def create_variance_report(org_id, item_id, location_id, physical_quantity, reason):
        item = db.session.get(InventoryItem, item_id)
        if not item:
            raise ValueError("Item not found")
            
        system_quantity = StockService(session=db.session).get_current_quantity(item.id)
        variance = physical_quantity - system_quantity
        
        year = datetime.now(timezone.utc).year
        count = db.session.query(VarianceReport).filter(VarianceReport.report_number.like(f"VAR-{year}-%")).count() + 1
        report_number = f"VAR-{year}-{count:05d}"
        
        var_rep = VarianceReport(
            organization_id=org_id,
            report_number=report_number,
            item_id=item_id,
            location_id=location_id,
            system_quantity=system_quantity,
            physical_quantity=physical_quantity,
            variance=variance,
            reason=reason
        )
        db.session.add(var_rep)
        db.session.commit()
        return var_rep

    @staticmethod
    @staticmethod
    @transaction_retry(max_retries=3)
    def resolve_variance(var_id, resolved_by_id):
        var_rep = db.session.get(VarianceReport, var_id)
        if not var_rep or var_rep.status != 'open':
            raise ValueError("Variance Report not found or already resolved")
            
        # Update system stock to match physical stock
        item = db.session.query(InventoryItem).with_for_update().filter_by(id=var_rep.item_id).first()
        if item:
            current_quantity = StockService(session=db.session).get_current_quantity(item.id)
            variance = var_rep.physical_quantity - current_quantity
            stock_service = StockService(session=db.session)
            if variance != 0:
                movements = []
                if variance > 0:
                    movements.append(
                        {
                            "item_id": item.id,
                            "type": "IN",
                            "quantity": variance,
                            "warehouse_id": var_rep.location_id,
                            "reference": var_rep.report_number,
                            "notes": f"Variance Resolution: {var_rep.reason}",
                        }
                    )
                else:
                    movements.append(
                        {
                            "item_id": item.id,
                            "type": "OUT",
                            "quantity": abs(variance),
                            "warehouse_id": var_rep.location_id,
                            "reference": var_rep.report_number,
                            "notes": f"Variance Resolution: {var_rep.reason}",
                        }
                    )

                try:
                    stock_service.apply_batch(var_rep.organization_id, movements, commit=False)
                except Exception as err:
                    # Preserve previous behaviour: log and surface error
                    raise
            
        var_rep.status = 'resolved'
        var_rep.resolved_by = resolved_by_id
        var_rep.resolved_at = datetime.now(timezone.utc)
        db.session.commit()
        return var_rep
