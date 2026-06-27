from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.services.inventory_service import InventoryService

app = create_app('development')
ctx = app.app_context()
ctx.push()

service = InventoryService()
try:
    service.update_stock(2, 1, 'IN', 1, warehouse_id=1, reference='TEST-1', notes='')
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
