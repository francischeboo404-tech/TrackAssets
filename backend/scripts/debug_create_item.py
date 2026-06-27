import sys
import traceback
from pathlib import Path

# Ensure repo root on path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from app import create_app, db
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService

app = create_app('development')
with app.app_context():
    svc = InventoryService(repository=InventoryRepository(), session=db.session)
    try:
        item = svc.create_item(1, {'name':'dbg-item','unit_price':1.0,'quantity':1})
        print('created item id', item.id)
    except Exception as e:
        print('exception during create_item')
        traceback.print_exc()
