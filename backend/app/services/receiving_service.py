from app import db
from sqlalchemy import func
from app.audit_service import AuditService
from app.errors import NotFoundError, ValidationError
from app.models.kenya_gov_models import GoodsReceiptNote, GoodsReceiptItem, InspectionReport, PurchaseOrder, PurchaseOrderItem
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.models.asset import Asset
from app.services.inventory_service import InventoryService
from datetime import datetime, timezone

class ReceivingService:
    @staticmethod
    def create_grn(org_id, po_id, received_by_id, items_data, invoice_number=None, delivery_note_number=None):
        # Validate input
        if not po_id:
            raise ValidationError("po_id is required")
        if not items_data or len(items_data) == 0:
            raise ValidationError("At least one item must be provided")
        if not received_by_id:
            raise ValidationError("received_by_id is required")
            
        # Validate PO exists and belongs to organisation
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("PO not found")
        if po.organization_id != org_id:
            raise ValidationError("PO belongs to another organisation")

        # PO must be approved before receiving
        if po.status != 'approved':
            raise ValidationError(f"Purchase Order must be APPROVED before receiving goods (current status: {po.status})")

        # Map PO items for quick lookup
        po_items = PurchaseOrderItem.query.filter_by(po_id=po_id).all()
        po_map = {p.item_id: p for p in po_items}
        
        if not po_map:
            raise ValidationError(f"PO {po_id} has no items")

        # Compute already received quantities per item for this PO
        received_sums = dict(
            db.session.query(GoodsReceiptItem.item_id, func.coalesce(func.sum(GoodsReceiptItem.quantity_received), 0))
            .join(GoodsReceiptNote, GoodsReceiptNote.id == GoodsReceiptItem.grn_id)
            .filter(GoodsReceiptNote.po_id == po_id)
            .group_by(GoodsReceiptItem.item_id)
            .all()
        )

        # Validate incoming items against PO
        for idx, itm in enumerate(items_data):
            item_type = (itm.get('item_type') or 'inventory').strip().lower()
            if item_type not in {'inventory', 'asset'}:
                raise ValidationError(f"Item {idx}: item_type must be either 'inventory' or 'asset'")

            qty = itm.get('quantity_received')
            unit_cost = itm.get('unit_cost')
            warehouse_id = itm.get('warehouse_id')
            
            if qty is None:
                raise ValidationError(f"Item {idx}: quantity_received is required")
            if unit_cost is None:
                raise ValidationError(f"Item {idx}: unit_cost is required")

            try:
                qty = int(qty)
                unit_cost = float(unit_cost)
            except (ValueError, TypeError) as e:
                raise ValidationError(f"Item {idx}: Invalid data type - {str(e)}")

            # Backward compatibility: if the caller omits warehouse_id, resolve a default
            # warehouse for the organization instead of breaking existing flows.
            if warehouse_id in (None, "", []):
                from app.models.location_topology import Warehouse
                default_warehouse = (
                    db.session.query(Warehouse)
                    .filter(Warehouse.organisation_id == org_id, Warehouse.is_active.is_(True))
                    .order_by(Warehouse.is_main_warehouse.desc(), Warehouse.name.asc())
                    .first()
                )
                if not default_warehouse:
                    default_warehouse = Warehouse(
                        organisation_id=org_id,
                        name="Main Warehouse",
                        code=f"WH-{org_id}",
                        is_main_warehouse=True,
                        warehouse_type="main",
                        hierarchy_level=0,
                        is_active=True,
                    )
                    db.session.add(default_warehouse)
                    db.session.flush()
                warehouse_id = default_warehouse.id
            else:
                try:
                    warehouse_id = int(warehouse_id)
                except (ValueError, TypeError) as e:
                    raise ValidationError(f"Item {idx}: Invalid warehouse_id - {str(e)}")

            if qty <= 0:
                raise ValidationError(f"Item {idx}: Received quantity must be greater than zero")
            
            # Validate warehouse exists and belongs to organization
            from app.models.location_topology import Warehouse
            warehouse = db.session.get(Warehouse, warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Item {idx}: Warehouse {warehouse_id} not found")
            if warehouse.organisation_id != org_id:
                raise ValidationError(f"Item {idx}: Warehouse {warehouse_id} does not belong to this organization")

            if item_type == 'inventory':
                item_id = itm.get('item_id')
                if not item_id:
                    raise ValidationError(f"Item {idx}: item_id is required for inventory items")
                try:
                    item_id = int(item_id)
                except (ValueError, TypeError) as e:
                    raise ValidationError(f"Item {idx}: Invalid inventory item_id - {str(e)}")

                if item_id not in po_map:
                    raise ValidationError(f"Item {item_id} is not part of Purchase Order {po_id}")
                po_item = po_map[item_id]
                already = int(received_sums.get(item_id, 0))
                remaining = int(po_item.quantity) - already
                if qty > remaining:
                    raise ValidationError(f"Item {idx}: Received quantity ({qty}) exceeds remaining PO quantity ({remaining})")

                po_cost = float(po_item.unit_cost)
                if abs(unit_cost - po_cost) > 0.01:
                    raise ValidationError(f"Item {idx}: Unit cost ({unit_cost}) does not match PO unit cost ({po_cost})")
            else:
                asset_id = itm.get('asset_id')
                if not asset_id:
                    raise ValidationError(f"Item {idx}: asset_id is required for asset items")
                try:
                    asset_id = int(asset_id)
                except (ValueError, TypeError) as e:
                    raise ValidationError(f"Item {idx}: Invalid asset_id - {str(e)}")

                asset_obj = db.session.get(Asset, asset_id)
                if not asset_obj or asset_obj.organisation_id != org_id:
                    raise ValidationError(f"Item {idx}: Asset {asset_id} not found")

                if qty != 1:
                    raise ValidationError(f"Item {idx}: Asset receipts must be quantity 1")

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
            item_type = (item_data.get('item_type') or 'inventory').strip().lower()
            warehouse_id = item_data.get('warehouse_id')
            if warehouse_id in (None, "", []):
                from app.models.location_topology import Warehouse
                default_warehouse = (
                    db.session.query(Warehouse)
                    .filter(Warehouse.organisation_id == org_id, Warehouse.is_active.is_(True))
                    .order_by(Warehouse.is_main_warehouse.desc(), Warehouse.name.asc())
                    .first()
                )
                warehouse_id = default_warehouse.id if default_warehouse else None
            else:
                warehouse_id = int(warehouse_id)

            grn_item = GoodsReceiptItem(
                organization_id=org_id,
                grn_id=grn.id,
                item_id=item_data.get('item_id') if item_type == 'inventory' else None,
                asset_id=item_data.get('asset_id') if item_type == 'asset' else None,
                item_type=item_type,
                warehouse_id=warehouse_id,
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
        
        For inventory items: Creates stock movements for accepted quantities
        For asset items: Marks quantity_accepted (quantity=1 per asset)
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
        
        try:
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

                # Only create stock movements for inventory items
                if grn_item.item_type == 'inventory' and accepted > 0:
                    # Validate inventory item exists
                    inv_item = db.session.get(InventoryItem, grn_item.item_id)
                    if not inv_item:
                        raise NotFoundError(f"Inventory item {grn_item.item_id} not found")
                    if inv_item.organisation_id != org_id:
                        raise ValidationError(f"Item {grn_item.item_id} does not belong to this organization")
                    
                    # Use warehouse_id from GRN item (already validated at creation time)
                    warehouse_id = grn_item.warehouse_id
                    
                    movements.append({
                        "item_id": grn_item.item_id,
                        "type": "IN",
                        "quantity": int(accepted),
                        "warehouse_id": warehouse_id,
                        "reference": grn.grn_number,
                        "notes": "Approved per-item",
                        "unit_cost": float(grn_item.unit_cost) if grn_item.unit_cost else None,
                    })
                elif grn_item.item_type == 'asset' and accepted > 0:
                    # Validate asset exists and belongs to organization
                    asset_obj = db.session.get(Asset, grn_item.asset_id)
                    if not asset_obj:
                        raise NotFoundError(f"Asset {grn_item.asset_id} not found")
                    if asset_obj.organisation_id != org_id:
                        raise ValidationError(f"Asset {grn_item.asset_id} does not belong to this organization")

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

            # Apply movements (if any) using InventoryService
            if movements:
                InventoryService(session=db.session).update_stock_batch(
                    org_id,
                    movements,
                    user_id=inspector_id,
                    module="receiving"
                )
            else:
                db.session.flush()

            AuditService.log_action(
                action="IAR_PROCESSED",
                entity_type="inspection_report",
                entity_id=iar.id,
                details={
                    "grn_id": grn_id,
                    "total_received": total_received,
                    "total_accepted": total_accepted
                },
                user_id=inspector_id,
                organisation_id=org_id,
                module="receiving",
                session=db.session,
            )
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise

        return iar

    @staticmethod
    def approve_grn(grn_id):
        """
        Approve a GRN and move items into inventory or update asset status.
        Ensures transactional consistency for both asset and inventory updates.
        
        Process:
        1. Validate GRN and inspection report
        2. Update inventory items via stock batch (atomic)
        3. Update asset items with status changes (atomic)
        4. Reconcile PO status
        5. Commit all changes in a single transaction
        6. Invalidate caches for both modules
        """
        grn = db.session.get(GoodsReceiptNote, grn_id)
        if not grn:
            raise NotFoundError("GRN not found")
            
        iar = InspectionReport.query.filter_by(grn_id=grn_id).order_by(InspectionReport.id.desc()).first()
        if not iar or iar.status != 'passed':
            raise ValidationError("Cannot approve GRN without a passed inspection report")
        
        grn_items = GoodsReceiptItem.query.filter_by(grn_id=grn_id).all()
        if not grn_items:
            raise ValidationError("GRN has no items to approve")
            
        # Separate inventory and asset movements
        inventory_movements = []
        asset_updates = []  # List of (asset_id, asset_obj) tuples
        
        try:
            for g_item in grn_items:
                # Accept everything that was received
                g_item.quantity_accepted = g_item.quantity_received
                
                if g_item.item_type == 'asset':
                    # Validate asset exists and belongs to organization
                    asset_obj = db.session.get(Asset, g_item.asset_id)
                    if not asset_obj:
                        raise NotFoundError(f"Asset {g_item.asset_id} not found")
                    if asset_obj.organisation_id != grn.organization_id:
                        raise ValidationError(f"Asset {g_item.asset_id} does not belong to this organization")
                    
                    # Stage asset update
                    asset_updates.append((g_item.asset_id, asset_obj))
                    
                elif g_item.item_type == 'inventory':
                    # Validate item exists and belongs to organization
                    inv_item = db.session.get(InventoryItem, g_item.item_id)
                    if not inv_item:
                        raise NotFoundError(f"Inventory item {g_item.item_id} not found")
                    if inv_item.organisation_id != grn.organization_id:
                        raise ValidationError(f"Item {g_item.item_id} does not belong to this organization")
                    
                    # Validate warehouse_id exists and belongs to organization
                    if not g_item.warehouse_id:
                        raise ValidationError(f"Inventory item {g_item.item_id} has no warehouse assigned")
                    
                    from app.models.location_topology import Warehouse
                    warehouse = db.session.get(Warehouse, g_item.warehouse_id)
                    if not warehouse:
                        raise NotFoundError(f"Warehouse {g_item.warehouse_id} not found")
                    if warehouse.organisation_id != grn.organization_id:
                        raise ValidationError(f"Warehouse {g_item.warehouse_id} does not belong to this organization")
                    
                    # Stage inventory movement with warehouse_id from GRN item
                    inventory_movements.append({
                        "item_id": g_item.item_id,
                        "type": "IN",
                        "quantity": int(g_item.quantity_received),
                        "warehouse_id": g_item.warehouse_id,
                        "reference": grn.grn_number,
                        "notes": "Approved from quarantine",
                        "unit_cost": float(g_item.unit_cost) if g_item.unit_cost else None,
                    })
                else:
                    raise ValidationError(f"Unknown item_type: {g_item.item_type}")
            
            # Apply inventory movements atomically via InventoryService
            if inventory_movements:
                try:
                    InventoryService(session=db.session).update_stock_batch(
                        grn.organization_id,
                        inventory_movements,
                        user_id=grn.received_by_id,
                        module="receiving"
                    )
                except Exception as e:
                    db.session.rollback()
                    raise ValidationError(f"Failed to update inventory stock: {str(e)}")
            
            # Apply asset status updates with audit logging
            for asset_id, asset_obj in asset_updates:
                asset_obj.status = 'available'
                asset_obj.updated_at = datetime.now(timezone.utc)
                db.session.flush()
                
                AuditService.log_action(
                    action="ASSET_RECEIVED",
                    entity_type="asset",
                    entity_id=asset_obj.id,
                    details={
                        "grn_id": grn_id,
                        "grn_number": grn.grn_number,
                        "asset_code": asset_obj.asset_code,
                        "new_status": "available"
                    },
                    user_id=grn.received_by_id,
                    organisation_id=grn.organization_id,
                    module="receiving",
                    session=db.session,
                )
            
            # Update GRN status
            grn.status = 'approved'
            db.session.flush()
            
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
                po.status = ('received' if all_received else 'partially_received')
                db.session.flush()
            
            # Audit: GRN approved
            AuditService.log_action(
                action="GRN_APPROVED",
                entity_type="goods_receipt_note",
                entity_id=grn.id,
                details={
                    "grn_number": grn.grn_number,
                    "po_id": grn.po_id,
                    "inventory_items": len(inventory_movements),
                    "asset_items": len(asset_updates)
                },
                user_id=grn.received_by_id,
                organisation_id=grn.organization_id,
                module="receiving",
                session=db.session,
            )
            
            # Commit all changes atomically
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise
        
        # Invalidate caches AFTER successful commit
        try:
            from app.services.report_analytics_service import ReportAnalyticsService
            from app.services.asset_service import AssetService
            
            ReportAnalyticsService.invalidate_cache(grn.organization_id)
            
            # Invalidate asset cache if any assets were updated
            if asset_updates:
                for asset_id, _ in asset_updates:
                    # Clear asset-specific caches if implemented
                    pass
        except Exception as e:
            # Log but don't fail if cache invalidation fails
            import logging
            logging.warning(f"Cache invalidation warning for GRN {grn_id}: {str(e)}")

        return grn

    @staticmethod
    def reject_grn(grn_id):
        """
        Reject a GRN and mark it as rejected.
        All items return to supplier without updating inventory or assets.
        """
        grn = db.session.get(GoodsReceiptNote, grn_id)
        if not grn:
            raise NotFoundError("GRN not found")
        
        if grn.status in ('approved', 'received'):
            raise ValidationError(f"Cannot reject GRN with status '{grn.status}'. GRN must be in 'quarantine' or 'partially_approved' status.")
        
        grn.status = 'rejected'
        db.session.flush()
        
        AuditService.log_action(
            action="GRN_REJECTED",
            entity_type="goods_receipt_note",
            entity_id=grn.id,
            details={"grn_number": grn.grn_number, "po_id": grn.po_id},
            user_id=None,
            organisation_id=grn.organization_id,
            module="receiving",
            session=db.session,
        )
        
        db.session.commit()
        
        # Invalidate cache
        try:
            from app.services.report_analytics_service import ReportAnalyticsService
            ReportAnalyticsService.invalidate_cache(grn.organization_id)
        except Exception as e:
            import logging
            logging.warning(f"Cache invalidation warning for rejected GRN {grn_id}: {str(e)}")
        
        return grn
