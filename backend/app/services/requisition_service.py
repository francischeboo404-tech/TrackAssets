from app import db
from app.models.kenya_gov_models import RequisitionSlip, RequisitionItem
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.models.location_topology import WarehouseBin, WarehouseShelf, WarehouseRack, WarehouseZone
from app.models.stock_levels import WarehouseStock
from app.models.item_instance import ItemInstance
from app.errors import ValidationError
from app.services.inventory_service import InventoryService
from app.services.stock_service import StockService
from app.db_utils import transaction_retry
from datetime import datetime, timezone

class RequisitionService:
    @staticmethod
    @transaction_retry(max_retries=3)
    def create_requisition(org_id, requester_id, items_data):
        year = datetime.now(timezone.utc).year
        count = db.session.query(RequisitionSlip).filter(RequisitionSlip.ris_number.like(f"RIS-{year}-%")).count() + 1
        ris_number = f"RIS-{year}-{count:05d}"
        
        ris = RequisitionSlip(
            organization_id=org_id,
            ris_number=ris_number,
            requester_id=requester_id,
        )
        db.session.add(ris)
        db.session.flush()
        
        for item_data in items_data:
            item = db.session.get(InventoryItem, int(item_data['item_id']))
            req_item = RequisitionItem(
                organization_id=org_id,
                ris_id=ris.id,
                item_id=item_data['item_id'],
                quantity_requested=item_data['quantity'],
                quantity_issued=item_data.get('quantity_issued', 0),
                unit_cost=item_data.get('unit_cost') if item_data.get('unit_cost') is not None else (item.unit_price if item else 0),
                warehouse_id=item_data.get('warehouse_id'),
                bin_id=item_data.get('bin_id'),
            )
            db.session.add(req_item)
            
        db.session.commit()
        return ris

    @staticmethod
    @transaction_retry(max_retries=3)
    def approve_requisition(ris_id, department_head_id):
        ris = (
            db.session.query(RequisitionSlip).with_for_update()
            .filter_by(id=ris_id)
            .first()
        )
        if not ris:
            raise ValueError("Requisition not found")
        ris.status = 'approved'
        ris.department_head_id = department_head_id
        ris.approved_date = datetime.now(timezone.utc)
        db.session.commit()
        return ris

    @staticmethod
    @transaction_retry(max_retries=3)
    def cancel_requisition(ris_id, cancelled_by_id, reason=None):
        """Cancel a requisition if it has not yet been issued.

        Raises ValueError if the requisition does not exist or has already
        been partially/fully issued.
        """
        ris = (
            db.session.query(RequisitionSlip).with_for_update()
            .filter_by(id=ris_id)
            .first()
        )
        if not ris:
            raise ValueError("Requisition not found")

        if ris.status in ('issued', 'partially_issued'):
            raise ValueError("Cannot cancel requisition that has been issued")

        ris.status = 'cancelled'
        ris.updated_by = cancelled_by_id
        db.session.commit()
        return ris

    @staticmethod
    @transaction_retry(max_retries=3)
    def return_to_store(ris_id, returned_by_id, items=None):
        """Return issued quantities from a requisition back to stock.

        `items` (optional) should be a list of dicts with `item_id` and
        `quantity`. If omitted, all issued quantities are returned.
        """
        ris = (
            db.session.query(RequisitionSlip).with_for_update()
            .filter_by(id=ris_id)
            .first()
        )
        if not ris:
            raise ValueError("Requisition not found")

        if ris.status not in ("issued", "partially_issued"):
            raise ValueError("Only issued requisitions can be returned")

        req_items = db.session.query(RequisitionItem).filter_by(ris_id=ris_id).all()
        if not req_items:
            raise ValueError("No items found for requisition")

        # Map requested return quantities by item_id
        requested = {}
        if items:
            for it in items:
                try:
                    iid = int(it.get("item_id"))
                    qty = int(it.get("quantity") or 0)
                except Exception:
                    continue
                if qty > 0:
                    requested[iid] = requested.get(iid, 0) + qty

        movements = []
        total_returned = 0

        for r_item in req_items:
            issued = int(r_item.quantity_issued or 0)
            if issued <= 0:
                continue

            if requested:
                to_return = min(requested.get(r_item.item_id, 0), issued)
            else:
                to_return = issued

            if to_return <= 0:
                continue

            # Decrement the issued quantity on the requisition item
            r_item.quantity_issued = issued - to_return

            movements.append(
                {
                    "item_id": r_item.item_id,
                    "type": "IN",
                    "quantity": to_return,
                    "warehouse_id": r_item.warehouse_id,
                    "reference": f"{ris.ris_number}-RETURN",
                    "notes": "Returned via Requisition",
                }
            )
            total_returned += to_return

        if total_returned == 0:
            raise ValueError("Nothing to return")

        # Apply IN movements atomically
        InventoryService(session=db.session).update_stock_batch(ris.organization_id, movements)

        # Update RIS status based on remaining issued quantities
        still_issued = any((int(x.quantity_issued or 0) > 0) for x in req_items)
        if still_issued:
            ris.status = "partially_returned"
        else:
            ris.status = "returned"

        ris.updated_by = returned_by_id
        db.session.commit()
        return ris

    @staticmethod
    @transaction_retry(max_retries=3)
    def issue_requisition(ris_id):
        ris = (
            db.session.query(RequisitionSlip).with_for_update()
            .filter_by(id=ris_id)
            .first()
        )
        if not ris or ris.status != 'approved':
            raise ValueError("Requisition not found or not approved")

        req_items = db.session.query(RequisitionItem).filter_by(ris_id=ris_id).all()
        movements = []
        total_requested = 0
        total_issued = 0

        for r_item in req_items:
            item = db.session.get(InventoryItem, r_item.item_id)
            if not item:
                raise ValueError(f"Item {r_item.item_id} not found")

            requested = int(r_item.quantity_requested or 0)
            total_requested += requested

            warehouse_id = getattr(r_item, 'warehouse_id', None)
            bin_id = getattr(r_item, 'bin_id', None)

            # If a bin was specified, validate it belongs to the organisation
            if bin_id:
                bin_obj = (
                    db.session.query(WarehouseBin)
                    .join(WarehouseShelf)
                    .join(WarehouseRack)
                    .join(WarehouseZone)
                    .join('warehouse')
                    .filter(WarehouseBin.id == bin_id, WarehouseZone.warehouse_id == warehouse_id)
                    .first()
                )
                if not bin_obj:
                    # more strict: ensure bin exists and belongs to org via zone->warehouse
                    # fallback: validate by organisation id through warehouse relation
                    bin_obj = (
                        db.session.query(WarehouseBin)
                        .join(WarehouseShelf)
                        .join(WarehouseRack)
                        .join(WarehouseZone)
                        .join('warehouse')
                        .filter(WarehouseBin.id == bin_id)
                        .first()
                    )
                    if not bin_obj:
                        raise ValidationError("Invalid storage bin or access denied")

            # Determine if item has serialized instances
            has_instances = db.session.query(ItemInstance).filter_by(item_id=item.id).first() is not None

            if has_instances:
                # Allocate physical instances from requested bin/warehouse when possible
                instances_q = db.session.query(ItemInstance).with_for_update().filter_by(item_id=item.id, status='in_stock')
                if bin_id:
                    instances_q = instances_q.filter_by(bin_id=bin_id, warehouse_id=warehouse_id)
                elif warehouse_id:
                    instances_q = instances_q.filter_by(warehouse_id=warehouse_id)

                instances = instances_q.limit(requested).all()
                target_issue = int(r_item.quantity_issued) if int(r_item.quantity_issued or 0) > 0 else requested
                to_issue = min(len(instances), target_issue)

                # Mark selected instances as shipped (finalized issuance)
                for inst in instances[:to_issue]:
                    inst.status = 'shipped'
                    inst.warehouse_id = None
                    inst.bin_id = None
                    db.session.add(inst)

                # Record issued quantity
                r_item.quantity_issued = to_issue
                if not r_item.unit_cost:
                    r_item.unit_cost = item.unit_price

                if to_issue > 0:
                    movements.append(
                        {
                            "item_id": item.id,
                            "type": "OUT",
                            "quantity": to_issue,
                            "warehouse_id": warehouse_id,
                            "reference": ris.ris_number,
                            "notes": "Issued via Requisition",
                        }
                    )
                    total_issued += to_issue
            else:
                # Non-serialized: prefer warehouse-level availability if provided
                available = StockService(session=db.session).get_current_quantity(item.id)
                if warehouse_id:
                    wh = db.session.query(WarehouseStock).filter_by(item_id=item.id, warehouse_id=warehouse_id).first()
                    if wh:
                        available = int(wh.quantity_on_hand or 0)

                target_issue = int(r_item.quantity_issued) if int(r_item.quantity_issued or 0) > 0 else requested
                to_issue = min(available, target_issue)

                # Record issued quantity (may be zero)
                r_item.quantity_issued = to_issue
                if not r_item.unit_cost:
                    r_item.unit_cost = item.unit_price

                if to_issue > 0:
                    movements.append(
                        {
                            "item_id": item.id,
                            "type": "OUT",
                            "quantity": to_issue,
                            "warehouse_id": warehouse_id,
                            "reference": ris.ris_number,
                            "notes": "Issued via Requisition",
                        }
                    )
                    total_issued += to_issue

        if total_issued == 0:
            # Nothing to issue
            raise ValueError("Insufficient stock; nothing to issue")

        # Apply batch stock out for the requisition (atomic)
        InventoryService(session=db.session).update_stock_batch(ris.organization_id, movements)

        # Update requisition status according to issuance coverage
        if total_issued < total_requested:
            ris.status = 'partially_issued'
        else:
            ris.status = 'issued'

        db.session.commit()
        return ris
