from app import db
from sqlalchemy import func
from app.audit_service import AuditService
from app.errors import NotFoundError, ValidationError
from app.models.kenya_gov_models import GoodsReceiptNote, GoodsReceiptItem, InspectionReport, PurchaseOrder, PurchaseOrderItem
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.services.inventory_service import InventoryService
from datetime import datetime, timezone

class ReceivingService:
    @staticmethod
    def create_grn(org_id, po_id, received_by_id, items_data, invoice_number=None, delivery_note_number=None):
        # Validate PO exists and belongs to organisation
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("PO not found")
        if po.organization_id != org_id:
            raise ValidationError("PO belongs to another organisation")

        # PO must be approved before receiving
        if po.status != 'approved':
            raise ValidationError("Purchase Order must be APPROVED before receiving goods")

        # Map PO items for quick lookup
        po_items = PurchaseOrderItem.query.filter_by(po_id=po_id).all()
        po_map = {p.item_id: p for p in po_items}

        # Compute already received quantities per item for this PO
        received_sums = dict(
            db.session.query(GoodsReceiptItem.item_id, func.coalesce(func.sum(GoodsReceiptItem.quantity_received), 0))
            .join(GoodsReceiptNote, GoodsReceiptNote.id == GoodsReceiptItem.grn_id)
            .filter(GoodsReceiptNote.po_id == po_id)
            .group_by(GoodsReceiptItem.item_id)
            .all()
        )

        # Validate incoming items against PO
        for itm in items_data:
            item_id = itm.get('item_id')
            qty = int(itm.get('quantity_received', 0))
            if item_id not in po_map:
                raise ValidationError(f"Item {item_id} is not part of Purchase Order {po_id}")
            po_item = po_map[item_id]

            already = int(received_sums.get(item_id, 0))
            remaining = int(po_item.quantity) - already
            if qty <= 0:
                raise ValidationError("Received quantity must be greater than zero")
            if qty > remaining:
                raise ValidationError(f"Received quantity for item {item_id} exceeds remaining PO quantity ({remaining})")

            # Unit cost must match PO item unit cost
            if 'unit_cost' in itm and float(itm.get('unit_cost')) != float(po_item.unit_cost):
                raise ValidationError(f"Unit cost for item {item_id} does not match PO")

        year = datetime.now(timezone.utc).year
        count = GoodsReceiptNote.query.filter(GoodsReceiptNote.grn_number.like(f"GRN-{year}-%")).count() + 1
        grn_number = f"GRN-{year}-{count:05d}"

        total_qty = sum([int(i['quantity_received']) for i in items_data])

        grn = GoodsReceiptNote(
            organization_id=org_id,
            grn_number=grn_number,
            invoice_number=invoice_number,
            delivery_note_number=delivery_note_number,
            po_id=po_id,
            received_by_id=received_by_id,
            total_quantity=total_qty,
            status='quarantine'  # All received items go to quarantine
        )
        db.session.add(grn)
        db.session.flush()

        for item_data in items_data:
            grn_item = GoodsReceiptItem(
                organization_id=org_id,
                grn_id=grn.id,
                item_id=item_data['item_id'],
                quantity_received=int(item_data['quantity_received']),
                unit_cost=item_data['unit_cost'],
                expiry_date=item_data.get('expiry_date')
            )
            db.session.add(grn_item)

        db.session.commit()

        # Audit: GRN created
        AuditService.log_action(
            action="GRN_CREATED",
            entity_type="goods_receipt_note",
            entity_id=grn.id,
            details={"grn_number": grn.grn_number, "po_id": po_id, "total_quantity": total_qty},
            user_id=received_by_id,
            organisation_id=org_id,
            module="receiving",
            session=db.session,
        )

        return grn

    @staticmethod
    def list_goods_receipts(org_id):
        return GoodsReceiptNote.query.filter_by(organization_id=org_id).order_by(GoodsReceiptNote.created_at.desc()).all()

    @staticmethod
    def create_inspection_report(org_id, grn_id, inspector_id, status, comments):
        grn = db.session.get(GoodsReceiptNote, grn_id)
        if not grn:
            raise ValueError("GRN not found")
            
        year = datetime.now(timezone.utc).year
        count = InspectionReport.query.filter(InspectionReport.iar_number.like(f"IAR-{year}-%")).count() + 1
        iar_number = f"IAR-{year}-{count:05d}"
        
        iar = InspectionReport(
            organization_id=org_id,
            iar_number=iar_number,
            grn_id=grn_id,
            inspector_id=inspector_id,
            status=status,
            comments=comments
        )
        db.session.add(iar)
        db.session.commit()
        # Audit: Inspection report created
        AuditService.log_action(
            action="IAR_CREATED",
            entity_type="inspection_report",
            entity_id=iar.id,
            details={"grn_id": grn_id, "status": status},
            user_id=inspector_id,
            organisation_id=org_id,
            module="receiving",
            session=db.session,
        )
        return iar

    @staticmethod
    def process_inspection_items(org_id, grn_id, inspector_id, items_data, comments=None):
        """Process per-GRN-item inspection results and move accepted items to stock.

        items_data: list of dicts with keys: grn_item_id, quantity_accepted, quantity_rejected
        """
        grn = db.session.get(GoodsReceiptNote, grn_id)
        if not grn:
            raise NotFoundError("GRN not found")
        if grn.organization_id != org_id:
            raise ValidationError("GRN belongs to another organisation")

        # Create inspection report header
        year = datetime.now(timezone.utc).year
        count = InspectionReport.query.filter(InspectionReport.iar_number.like(f"IAR-{year}-%")).count() + 1
        iar_number = f"IAR-{year}-{count:05d}"

        iar = InspectionReport(
            organization_id=org_id,
            iar_number=iar_number,
            grn_id=grn_id,
            inspector_id=inspector_id,
            status='pending',
            comments=comments,
        )
        db.session.add(iar)
        db.session.flush()

        # Apply per-item acceptance/rejection
        movements = []
        total_received = 0
        total_accepted = 0
        for itm in items_data:
            grn_item_id = itm.get('grn_item_id')
            accepted = int(itm.get('quantity_accepted', 0))
            rejected = int(itm.get('quantity_rejected', 0))

            grn_item = GoodsReceiptItem.query.filter_by(id=grn_item_id, grn_id=grn_id).first()
            if not grn_item:
                raise ValidationError(f"GRN item {grn_item_id} not found for GRN {grn_id}")

            if accepted + rejected > int(grn_item.quantity_received):
                raise ValidationError(f"Sum of accepted and rejected exceeds received for GRN item {grn_item_id}")

            grn_item.quantity_accepted = accepted
            grn_item.quantity_rejected = rejected

            total_received += int(grn_item.quantity_received)
            total_accepted += accepted

            if accepted > 0:
                # Determine warehouse for stock movement
                warehouse_id = None
                if grn_item.bin_location_id:
                    # Get warehouse from bin
                    from app.models.location_topology import WarehouseBin, WarehouseShelf, WarehouseRack, WarehouseZone
                    bin_obj = db.session.get(WarehouseBin, grn_item.bin_location_id)
                    if bin_obj:
                        # Navigate up the hierarchy to find warehouse
                        shelf = db.session.get(WarehouseShelf, bin_obj.shelf_id) if bin_obj.shelf_id else None
                        if shelf:
                            rack = db.session.get(WarehouseRack, shelf.rack_id) if shelf.rack_id else None
                            if rack:
                                zone = db.session.get(WarehouseZone, rack.zone_id) if rack.zone_id else None
                                if zone:
                                    warehouse_id = zone.warehouse_id
                else:
                    # No bin specified; find warehouse with existing stock for this item
                    from app.models.stock_levels import WarehouseStock
                    ws = db.session.query(WarehouseStock).filter_by(item_id=grn_item.item_id).first()
                    if ws:
                        warehouse_id = ws.warehouse_id
                
                movements.append(
                    {
                        "item_id": grn_item.item_id,
                        "type": "IN",
                        "quantity": int(accepted),
                        "warehouse_id": warehouse_id,
                        "reference": grn.grn_number,
                        "notes": "Approved per-item",
                        "unit_cost": float(grn_item.unit_cost) if grn_item.unit_cost else None,
                    }
                )

        # Determine overall statuses
        if total_accepted == 0 and total_received > 0:
            grn.status = 'rejected'
            iar.status = 'failed'
        elif total_accepted < total_received:
            grn.status = 'partially_approved'
            iar.status = 'partial'
        else:
            grn.status = 'approved'
            iar.status = 'passed'

        # Persist item-level inspection results and iar status together with PO reconciliation
        # Reconcile PO status based on accepted quantities
        po = db.session.get(PurchaseOrder, grn.po_id)
        if po:
            po_items = PurchaseOrderItem.query.filter_by(po_id=po.id).all()
            all_received = True
            for p_item in po_items:
                accepted_sum = (
                    db.session.query(func.coalesce(func.sum(GoodsReceiptItem.quantity_accepted), 0))
                    .join(GoodsReceiptNote, GoodsReceiptNote.id == GoodsReceiptItem.grn_id)
                    .filter(GoodsReceiptNote.po_id == po.id, GoodsReceiptItem.item_id == p_item.item_id)
                    .scalar()
                )
                if int(accepted_sum or 0) < int(p_item.quantity):
                    all_received = False
                    break
            po.status = 'received' if all_received else 'partially_received'

        # Apply movements (if any) using InventoryService which will commit the session
        if movements:
            InventoryService(session=db.session).update_stock_batch(grn.organization_id, movements, user_id=inspector_id, module="receiving")
        else:
            db.session.commit()

        AuditService.log_action(
            action="IAR_PROCESSED",
            entity_type="inspection_report",
            entity_id=iar.id,
            details={"grn_id": grn_id, "total_received": total_received, "total_accepted": total_accepted},
            user_id=inspector_id,
            organisation_id=org_id,
            module="receiving",
            session=db.session,
        )

        return iar

    @staticmethod
    def approve_grn(grn_id):
        # Move from quarantine to warehouse if inspection passed
        grn = db.session.get(GoodsReceiptNote, grn_id)
        if not grn:
            raise NotFoundError("GRN not found")
            
        iar = InspectionReport.query.filter_by(grn_id=grn_id).order_by(InspectionReport.id.desc()).first()
        if not iar or iar.status != 'passed':
            raise ValidationError("Cannot approve GRN without a passed inspection report")
            
        grn.status = 'approved'
        # Update accepted quantities and prepare movements
        grn_items = GoodsReceiptItem.query.filter_by(grn_id=grn_id).all()
        movements = []
        for g_item in grn_items:
            # Accept everything that was received (inspection-level item acceptance not modelled yet)
            g_item.quantity_accepted = g_item.quantity_received
            movements.append(
                {
                    "item_id": g_item.item_id,
                    "type": "IN",
                    "quantity": int(g_item.quantity_accepted),
                    "warehouse_id": None,
                    "reference": grn.grn_number,
                    "notes": "Approved from quarantine",
                    "unit_cost": float(g_item.unit_cost) if g_item.unit_cost else None,
                }
            )

        # Apply all GRN items as a single atomic batch
        InventoryService(session=db.session).update_stock_batch(grn.organization_id, movements, user_id=grn.received_by_id, module="receiving")

        # Reconcile PO status: check if all PO items fully received
        po = db.session.get(PurchaseOrder, grn.po_id)
        if po:
            po_items = PurchaseOrderItem.query.filter_by(po_id=po.id).all()
            all_received = True
            for p_item in po_items:
                accepted_sum = (
                    db.session.query(func.coalesce(func.sum(GoodsReceiptItem.quantity_accepted), 0))
                    .join(GoodsReceiptNote, GoodsReceiptNote.id == GoodsReceiptItem.grn_id)
                    .filter(GoodsReceiptNote.po_id == po.id, GoodsReceiptItem.item_id == p_item.item_id)
                    .scalar()
                )
                if int(accepted_sum or 0) < int(p_item.quantity):
                    all_received = False
                    break
            po.status = ('received' if all_received else 'partially_received')

        # Audit: GRN approved
        AuditService.log_action(
            action="GRN_APPROVED",
            entity_type="goods_receipt_note",
            entity_id=grn.id,
            details={"grn_number": grn.grn_number, "po_id": grn.po_id},
            user_id=None,
            organisation_id=grn.organization_id,
            module="receiving",
            session=db.session,
        )
        db.session.commit()
        from app.services.report_analytics_service import ReportAnalyticsService
        ReportAnalyticsService.invalidate_cache(grn.organization_id)

        return grn

    @staticmethod
    def reject_grn(grn_id):
        grn = db.session.get(GoodsReceiptNote, grn_id)
        if not grn:
            raise ValueError("GRN not found")
            
        grn.status = 'rejected'
        db.session.commit()
        AuditService.log_action(
            action="GRN_REJECTED",
            entity_type="goods_receipt_note",
            entity_id=grn.id,
            details={"grn_number": grn.grn_number},
            user_id=None,
            organisation_id=grn.organization_id,
            module="receiving",
            session=db.session,
        )
        return grn
