from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.models.kenya_gov_models import PurchaseOrder
from app.services.procurement_service import ProcurementService

app = create_app()
with app.app_context():
    try:
        pos = ProcurementService.list_purchase_orders(1)
        for o in pos:
            print(f"PO {o.id}: created_at={o.created_at}, total_amount={o.total_amount}")
            # Try to replicate the serialization
            float(o.total_amount)
            if o.created_at:
                o.created_at.isoformat()
            if o.approved_at:
                o.approved_at.isoformat()
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()
