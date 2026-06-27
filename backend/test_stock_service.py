import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from app import create_app, db
from app.services.stock_service import StockService

app = create_app('development')
with app.app_context():
    from app.models.user import User
    from app.models.inventory import InventoryItem
    
    # Get a test user and item
    user = User.query.first()
    item = InventoryItem.query.first()
    
    if not item:
        print("No inventory items found!")
    else:
        print(f"Testing increase_stock for item {item.id} (org {item.organisation_id})")
        stock_service = StockService(session=db.session)
        try:
            stock_service.increase_stock(
                item_id=item.id,
                org_id=item.organisation_id,
                quantity=1,
                user_id=user.id if user else None,
                commit=True
            )
            print("Successfully increased stock.")
        except Exception as e:
            import traceback
            traceback.print_exc()
