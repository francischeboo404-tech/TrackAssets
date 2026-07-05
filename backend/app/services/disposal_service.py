from app import db
from app.models.kenya_gov_models import DisposalRequest, DisposalItem
from app.models.inventory import InventoryItem
from app.services.inventory_service import InventoryService
from app.services.stock_service import StockService
from app.db_utils import transaction_retry
from datetime import datetime, timezone


class DisposalService:
    @staticmethod
    @transaction_retry(max_retries=3)
    def create_disposal_request(org_id, requester_id, items_data):
        year = datetime.now(timezone.utc).year
        count = db.session.query(DisposalRequest).filter(DisposalRequest.disposal_number.like(f"DISP-{year}-%")).count() + 1
        disp_number = f"DISP-{year}-{count:05d}"

        # Calculate total value using session-safe lookups
        total_val = 0.0
        for item_data in items_data:
            item = db.session.get(InventoryItem, int(item_data['item_id']))
            if item:
                total_val += float(item.unit_price or 0) * int(item_data['quantity'])

        disp = DisposalRequest(
            organization_id=org_id,
            disposal_number=disp_number,
            requester_id=requester_id,
            total_value=total_val,
        )
        db.session.add(disp)
        db.session.flush()

        for item_data in items_data:
            disp_item = DisposalItem(
                organization_id=org_id,
                disposal_id=disp.id,
                item_id=int(item_data['item_id']),
                quantity=int(item_data['quantity']),
                reason=item_data.get('reason', 'damaged'),
            )
            db.session.add(disp_item)

        db.session.commit()
        return disp

    @staticmethod
    @transaction_retry(max_retries=3)
    def approve_disposal(disp_id, approver_id, is_finance_board=False):
        disp = (
            db.session.query(DisposalRequest).with_for_update().filter_by(id=disp_id).first()
        )
        if not disp:
            raise ValueError("Disposal Request not found")

        # Kenyan Gov Rule: <= KES 50,000 -> Dept Head, > 50,000 -> Finance Board
        if float(disp.total_value or 0) > 50000 and not is_finance_board:
            raise ValueError("Disposal value > KES 50,000 requires Finance Board approval")

        disp.status = 'approved'
        disp.committee_id = approver_id
        disp.approved_at = datetime.now(timezone.utc)
        db.session.commit()
        return disp

    @staticmethod
    @transaction_retry(max_retries=3)
    def execute_disposal(disp_id, executed_by_id=None):
        disp = (
            db.session.query(DisposalRequest).with_for_update().filter_by(id=disp_id).first()
        )
        if not disp or disp.status != 'approved':
            raise ValueError("Disposal Request not found or not approved")

        disp_items = db.session.query(DisposalItem).filter_by(disposal_id=disp_id).all()
        if not disp_items:
            raise ValueError("No items found for disposal request")

        # Lock inventory rows for involved items to validate availability
        item_ids = [int(x.item_id) for x in disp_items]
        items = (
            db.session.query(InventoryItem).with_for_update()
            .filter(InventoryItem.id.in_(item_ids))
            .all()
        )
        item_map = {i.id: i for i in items}

        movements = []
        for d_item in disp_items:
            item = item_map.get(int(d_item.item_id))
            if not item:
                raise ValueError(f"Item {d_item.item_id} not found")

            current_qty = StockService(session=db.session).get_current_quantity(item.id)
            if int(current_qty or 0) < int(d_item.quantity or 0):
                raise ValueError(f"Insufficient stock to dispose for {item.name}")

            movements.append(
                {
                    "item_id": item.id,
                    "type": "OUT",
                    "quantity": int(d_item.quantity),
                    "warehouse_id": None,
                    "reference": disp.disposal_number,
                    "notes": f"Disposal executed: {d_item.reason}",
                }
            )

        # Apply all disposals as a single atomic batch using the shared session
        InventoryService(session=db.session).update_stock_batch(disp.organization_id, movements, user_id=executed_by_id)

        disp.status = 'executed'
        if executed_by_id:
            disp.updated_by = executed_by_id
        db.session.commit()
        return disp
