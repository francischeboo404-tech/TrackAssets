from app import db
from app.audit_service import AuditService
from app.errors import NotFoundError, ValidationError, ConflictError
from app.models.kenya_gov_models import (
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseOrder,
    PurchaseOrderItem,
    CanvassQuote,
)
from app.models.inventory import InventoryItem
from app.models.asset import Asset
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from flask import current_app

class ProcurementService:
    @staticmethod
    def _normalize_item_type(item_data):
        item_type = (item_data.get('item_type') or 'inventory').strip().lower()
        if item_type not in {'inventory', 'asset'}:
            raise ValidationError("Item type must be either 'inventory' or 'asset'")
        return item_type

    @staticmethod
    def _resolve_item_reference(org_id, item_data, *, allow_missing=False):
        item_type = ProcurementService._normalize_item_type(item_data)
        if item_type == 'inventory':
            item_id = item_data.get('item_id')
            if item_id in (None, '', []):
                if allow_missing:
                    return None, None, item_type
                raise ValidationError("item_id is required for inventory items")
            item_id = int(item_id)
            inventory_item = db.session.get(InventoryItem, item_id)
            if not inventory_item or inventory_item.organisation_id != org_id:
                raise ValidationError(f"Inventory item {item_id} not found")
            return item_id, None, item_type

        asset_id = item_data.get('asset_id')
        if asset_id in (None, '', []):
            if allow_missing:
                return None, None, item_type
            raise ValidationError("asset_id is required for asset items")
        asset_id = int(asset_id)
        asset = db.session.get(Asset, asset_id)
        if not asset or asset.organisation_id != org_id:
            raise ValidationError(f"Asset {asset_id} not found")
        return None, asset_id, item_type

    @staticmethod
    def create_purchase_request(org_id, requester_id, reason, items_data):
        # Auto-generate PR number: PR-YYYY-XXXXX
        year = datetime.now(timezone.utc).year
        count = PurchaseRequest.query.filter(PurchaseRequest.pr_number.like(f"PR-{year}-%")).count() + 1
        pr_number = f"PR-{year}-{count:05d}"

        # Auto-resolve warehouse from requester's department
        warehouse_id = None
        try:
            from app.models.user import User
            from app.models.organization import Department
            requester = db.session.get(User, requester_id)
            if requester and getattr(requester, 'department_id', None):
                dept = db.session.get(Department, requester.department_id)
                if dept:
                    warehouse_id = getattr(dept, 'warehouse_id', None)
        except Exception:
            pass
        
        pr = PurchaseRequest(
            organization_id=org_id,
            pr_number=pr_number,
            requester_id=requester_id,
            warehouse_id=warehouse_id,
            reason=reason
        )
        db.session.add(pr)
        db.session.flush() # get ID
        
        for item_data in items_data:
            item_id, asset_id, item_type = ProcurementService._resolve_item_reference(org_id, item_data)
            pr_item = PurchaseRequestItem(
                organization_id=org_id,
                pr_id=pr.id,
                item_id=item_id,
                asset_id=asset_id,
                item_type=item_type,
                quantity=item_data['quantity'],
                estimated_cost=item_data.get('estimated_cost', 0.0),
                justification=item_data.get('justification', '')
            )
            db.session.add(pr_item)
            
        db.session.commit()

        # Audit: PR created
        try:
            AuditService.log_action(
                action="PR_CREATED",
                entity_type="purchase_request",
                entity_id=pr.id,
                details={"pr_number": pr.pr_number, "items_count": len(items_data)},
                user_id=requester_id,
                organisation_id=org_id,
                module="procurement",
                session=db.session,
            )
        except Exception:
            # Fail-safe: do not interrupt creation on audit failure
            pass
        return pr

    @staticmethod
    def list_purchase_requests(org_id, warehouse_id=None):
        """Return purchase requests for an organization, most recent first."""
        q = PurchaseRequest.query.filter_by(organization_id=org_id)
        if warehouse_id:
            q = q.filter(PurchaseRequest.warehouse_id == warehouse_id)
        return q.order_by(PurchaseRequest.created_at.desc()).all()


    @staticmethod
    def approve_purchase_request(pr_id, department_head_id):
        pr = db.session.get(PurchaseRequest, pr_id)
        if not pr:
            raise NotFoundError("PR not found")
        pr.status = 'approved'
        pr.department_head_id = department_head_id
        pr.approved_at = datetime.now(timezone.utc)
        db.session.commit()

        # Audit: PR approved
        AuditService.log_action(
            action="PR_APPROVED",
            entity_type="purchase_request",
            entity_id=pr.id,
            details={"pr_number": pr.pr_number},
            user_id=department_head_id,
            organisation_id=pr.organization_id,
            module="procurement",
            session=db.session,
        )
        return pr

    @staticmethod
    def reject_purchase_request(pr_id, department_head_id):
        pr = db.session.get(PurchaseRequest, pr_id)
        if not pr:
            raise NotFoundError("PR not found")
        pr.status = 'rejected'
        pr.department_head_id = department_head_id
        db.session.commit()

        # Audit: PR rejected
        AuditService.log_action(
            action="PR_REJECTED",
            entity_type="purchase_request",
            entity_id=pr.id,
            details={"pr_number": pr.pr_number},
            user_id=department_head_id,
            organisation_id=pr.organization_id,
            session=db.session,
        )
        return pr

    @staticmethod
    def update_purchase_request(org_id, pr_id, requester_id, reason, items_data):
        pr = db.session.get(PurchaseRequest, pr_id)
        if not pr:
            raise NotFoundError("PR not found")
        if pr.organization_id != org_id:
            raise ValidationError("PR belongs to another organisation")
        if pr.status not in ('pending', 'rejected'):
            raise ValidationError("Only pending or rejected PRs can be updated")

        pr.reason = reason
        pr.status = 'pending' # Reset status to pending if it was rejected

        # Remove existing items and recreate
        PurchaseRequestItem.query.filter_by(pr_id=pr.id).delete()
        
        for item_data in items_data:
            item_id, asset_id, item_type = ProcurementService._resolve_item_reference(org_id, item_data)
            pr_item = PurchaseRequestItem(
                organization_id=org_id,
                pr_id=pr.id,
                item_id=item_id,
                asset_id=asset_id,
                item_type=item_type,
                quantity=item_data['quantity'],
                estimated_cost=item_data.get('estimated_cost', 0.0),
                justification=item_data.get('justification', '')
            )
            db.session.add(pr_item)
            
        db.session.commit()

        AuditService.log_action(
            action="PR_UPDATED",
            entity_type="purchase_request",
            entity_id=pr.id,
            details={"pr_number": pr.pr_number, "items_count": len(items_data)},
            user_id=requester_id,
            organisation_id=org_id,
            session=db.session,
        )
        return pr

    @staticmethod
    def create_purchase_order(org_id, pr_id=None, supplier_id=None, items_data=None, ris_id=None):
        if not pr_id and not ris_id:
            raise ValidationError("Either PR or Requisition must be provided to create a PO")

        # Validate PR exists and is approved if pr_id provided
        if pr_id:
            pr = db.session.get(PurchaseRequest, pr_id)
            if not pr:
                raise NotFoundError("PR not found")
            if pr.organization_id != org_id:
                raise ValidationError("PR belongs to another organisation")
            if not getattr(pr, 'is_active', True):
                raise ValidationError("Purchase Request is not active")
            if pr.status in ('cancelled', 'archived'):
                raise ValidationError("Purchase Request is not valid for creating Purchase Order")
            if pr.status != 'approved':
                raise ValidationError("Purchase Request must be APPROVED before creating a Purchase Order")
                
        # Validate RIS exists and is approved if ris_id provided
        if ris_id:
            from app.models.kenya_gov_models import RequisitionSlip
            ris = db.session.get(RequisitionSlip, ris_id)
            if not ris:
                raise NotFoundError("Requisition not found")
            if ris.organization_id != org_id:
                raise ValidationError("Requisition belongs to another organisation")
            if not getattr(ris, 'is_active', True):
                raise ValidationError("Requisition is not active")
            if ris.status != 'approved':
                raise ValidationError("Requisition must be APPROVED before creating a Purchase Order")

        # Prevent multiple active POs for a PR or RIS
        if pr_id:
            existing_po = (
                PurchaseOrder.query.filter_by(pr_id=pr_id, is_active=True)
                .filter(PurchaseOrder.status != 'cancelled')
                .first()
            )
            if existing_po:
                raise ConflictError("An active Purchase Order already exists for this Purchase Request")
        if ris_id:
            existing_po = (
                PurchaseOrder.query.filter_by(ris_id=ris_id, is_active=True)
                .filter(PurchaseOrder.status != 'cancelled')
                .first()
            )
            if existing_po:
                raise ConflictError("An active Purchase Order already exists for this Requisition")

        # Validate supplier exists and belongs to organisation
        try:
            from app.models.supplier import Supplier

            supplier = db.session.get(Supplier, supplier_id)
        except Exception:
            supplier = None
        if not supplier or not getattr(supplier, 'is_active', True):
            raise NotFoundError("Supplier not found or inactive")
        supplier_org = getattr(supplier, 'organisation_id', getattr(supplier, 'organization_id', None))
        if supplier_org is not None and supplier_org != org_id:
            raise ValidationError("Supplier does not belong to the organisation")

        # Validate PO items are present in PR/RIS and quantities do not exceed requested quantities
        if pr_id:
            for item in items_data:
                item_type = ProcurementService._normalize_item_type(item)
                if item_type == 'inventory':
                    item_id = int(item['item_id'])
                    pr_item = PurchaseRequestItem.query.filter_by(pr_id=pr_id, item_type='inventory', item_id=item_id).first()
                    if not pr_item:
                        pr_item = PurchaseRequestItem.query.filter_by(pr_id=pr_id, item_id=item_id).first()
                    if not pr_item:
                        raise ValidationError(f"Item {item_id} is not in the Purchase Request")
                    if int(item['quantity']) > int(pr_item.quantity):
                        raise ValidationError(
                            f"PO quantity for item {item_id} exceeds requested PR quantity ({pr_item.quantity})"
                        )
                else:
                    asset_id = int(item['asset_id'])
                    pr_item = PurchaseRequestItem.query.filter_by(pr_id=pr_id, item_type='asset', asset_id=asset_id).first()
                    if not pr_item:
                        pr_item = PurchaseRequestItem.query.filter_by(pr_id=pr_id, asset_id=asset_id).first()
                    if not pr_item:
                        raise ValidationError(f"Asset {asset_id} is not in the Purchase Request")
                    if int(item['quantity']) > int(pr_item.quantity):
                        raise ValidationError(
                            f"PO quantity for asset {asset_id} exceeds requested PR quantity ({pr_item.quantity})"
                        )
        elif ris_id:
            from app.models.kenya_gov_models import RequisitionItem
            for item in items_data:
                item_type = ProcurementService._normalize_item_type(item)
                if item_type == 'inventory':
                    item_id = int(item['item_id'])
                    ris_item = RequisitionItem.query.filter_by(ris_id=ris_id, item_type='inventory', item_id=item_id).first()
                    if not ris_item:
                        ris_item = RequisitionItem.query.filter_by(ris_id=ris_id, item_id=item_id).first()
                    if not ris_item:
                        raise ValidationError(f"Item {item_id} is not in the Requisition")
                    if int(item['quantity']) > int(ris_item.quantity_requested):
                        raise ValidationError(
                            f"PO quantity for item {item_id} exceeds requested Requisition quantity ({ris_item.quantity_requested})"
                        )
                else:
                    asset_id = int(item['asset_id'])
                    ris_item = RequisitionItem.query.filter_by(ris_id=ris_id, item_type='asset', asset_id=asset_id).first()
                    if not ris_item:
                        ris_item = RequisitionItem.query.filter_by(ris_id=ris_id, asset_id=asset_id).first()
                    if not ris_item:
                        raise ValidationError(f"Asset {asset_id} is not in the Requisition")
                    if int(item['quantity']) > int(ris_item.quantity_requested):
                        raise ValidationError(
                            f"PO quantity for asset {asset_id} exceeds requested Requisition quantity ({ris_item.quantity_requested})"
                        )

        # Create PO
        year = datetime.now(timezone.utc).year
        count = PurchaseOrder.query.filter(PurchaseOrder.po_number.like(f"PO-{year}-%")).count() + 1
        po_number = f"PO-{year}-{count:05d}"

        total_amount = sum([float(i.get('total_cost', i['quantity'] * i['unit_cost'])) for i in items_data])

        po = PurchaseOrder(
            organization_id=org_id,
            po_number=po_number,
            pr_id=pr_id,
            ris_id=ris_id,
            supplier_id=supplier_id,
            total_amount=total_amount,
        )
        db.session.add(po)
        db.session.flush()

        for item_data in items_data:
            item_type = ProcurementService._normalize_item_type(item_data)
            if item_type == 'inventory':
                item_id = int(item_data['item_id'])
                asset_id = None
            else:
                item_id = None
                asset_id = int(item_data['asset_id'])
            po_item = PurchaseOrderItem(
                organization_id=org_id,
                po_id=po.id,
                item_id=item_id,
                asset_id=asset_id,
                item_type=item_type,
                quantity=item_data['quantity'],
                unit_cost=item_data['unit_cost'],
                total_cost=item_data.get('total_cost', item_data['quantity'] * item_data['unit_cost']),
            )
            db.session.add(po_item)

        db.session.commit()

        # Audit: PO created
        AuditService.log_action(
            action="PO_CREATED",
            entity_type="purchase_order",
            entity_id=po.id,
            details={"po_number": po.po_number, "pr_id": pr_id, "supplier_id": supplier_id},
            user_id=None,
            organisation_id=org_id,
            module="procurement",
            session=db.session,
        )

        return po

    @staticmethod
    def add_canvass_quote(org_id, po_id, supplier_id=None, item_id=None, supplier_name=None, item_name=None, unit_cost=None, quote_date=None):
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("Purchase Order not found")

        if unit_cost is None:
            # Keep backward compatibility with older tests and callers that pass values in the
            # supplier/item position due to the earlier signature order.
            if supplier_name is not None and isinstance(supplier_name, (int, float)) and item_name is None:
                unit_cost = supplier_name
                supplier_name = None
            elif item_name is not None and isinstance(item_name, (int, float)) and supplier_name is None:
                unit_cost = item_name
                item_name = None
            elif supplier_id is not None and isinstance(supplier_id, (int, float)) and item_id is None:
                unit_cost = supplier_id
                supplier_id = None
            elif item_id is not None and isinstance(item_id, (int, float)) and supplier_id is None:
                unit_cost = item_id
                item_id = None
            elif supplier_name is not None and isinstance(supplier_name, (int, float)) and item_name is not None:
                unit_cost = supplier_name
                quote_date = item_name
                supplier_name = supplier_id
                item_name = item_id
                supplier_id = None
                item_id = None
            else:
                raise ValidationError("Unit cost is required for canvass quotes")
        try:
            unit_cost = float(unit_cost)
        except (TypeError, ValueError):
            raise ValidationError("Unit cost must be a valid number")

        if supplier_id is None and not supplier_name:
            raise ValidationError("Supplier selection or name is required for canvass quotes")
        if item_id is None and not item_name:
            raise ValidationError("Item selection or name is required for canvass quotes")

        # Resolve names if IDs provided
        resolved_supplier_name = supplier_name
        resolved_item_name = item_name

        if supplier_id is not None:
            from app.models.supplier import Supplier
            supplier = db.session.get(Supplier, supplier_id)
            if not supplier:
                raise NotFoundError("Supplier not found")
            resolved_supplier_name = getattr(supplier, 'name', resolved_supplier_name)

        if item_id is not None:
            inv = db.session.get(InventoryItem, item_id)
            if not inv:
                raise NotFoundError("Inventory item not found")
            resolved_item_name = getattr(inv, 'name', resolved_item_name)

        quote_date = quote_date or datetime.now(timezone.utc)

        quote = CanvassQuote(
            organization_id=org_id,
            po_id=po_id,
            supplier_name=resolved_supplier_name or 'Unknown',
            item_name=resolved_item_name or 'Unknown',
            unit_cost=unit_cost,
            total_cost=unit_cost, # simplified
            quote_date=quote_date
        )
        db.session.add(quote)
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise ConflictError(
                "A canvass quote with the same details already exists or cannot be created"
            ) from exc
        return quote

    @staticmethod
    def list_purchase_orders(org_id, statuses=None, include_inactive=False):
        """Return purchase orders for an organization, most recent first.

        When the caller needs a receivable PO list for GRN creation, they can request
        a filtered subset such as approved or partially_received orders without needing
        to re-implement status filtering in each UI layer.
        """
        query = PurchaseOrder.query.filter_by(organization_id=org_id)

        if not include_inactive:
            query = query.filter(PurchaseOrder.is_active.is_(True))

        if statuses:
            normalized_statuses = [str(status).strip().lower() for status in statuses if str(status).strip()]
            if normalized_statuses:
                query = query.filter(PurchaseOrder.status.in_(normalized_statuses))

        return query.order_by(PurchaseOrder.created_at.desc()).all()

    @staticmethod
    def approve_purchase_order(po_id, user_id=None):
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("PO not found")

        # Previously there was a canvass requirement; requirement removed by default.
        # Budget check simulation
        # if not budget_available(po.total_amount): raise ValueError("Insufficient budget")

        po.status = 'approved'
        po.approved_at = datetime.now(timezone.utc)
        db.session.commit()

        # Audit: PO approved
        AuditService.log_action(
            action="PO_APPROVED",
            entity_type="purchase_order",
            entity_id=po.id,
            details={"po_number": po.po_number},
            user_id=user_id,
            organisation_id=po.organization_id,
            module="procurement",
            session=db.session,
        )
        return po

    @staticmethod
    def close_canvass_quote(po_id, quote_id, user_id=None):
        quote = db.session.get(CanvassQuote, quote_id)
        if not quote or quote.po_id != po_id:
            raise NotFoundError("Canvass quote not found for this PO")
        if not quote.is_active:
            raise ValidationError("Canvass quote already closed")
        quote.is_active = False
        db.session.commit()

        AuditService.log_action(
            action="CANVASS_QUOTE_CLOSED",
            entity_type="canvass_quote",
            entity_id=quote.id,
            details={"po_id": po_id},
            user_id=user_id,
            organisation_id=quote.organization_id,
            module="procurement",
            session=db.session,
        )
        return quote
        if not po:
            raise NotFoundError("PO not found")
        if po.status != 'pending':
            raise ValidationError("Only pending POs can be rejected")
            
        po.status = 'rejected'
        db.session.commit()

        AuditService.log_action(
            action="PO_REJECTED",
            entity_type="purchase_order",
            entity_id=po.id,
            details={"po_number": po.po_number},
            user_id=None,
            organisation_id=po.organization_id,
            session=db.session,
        )
        return po

    @staticmethod
    def cancel_purchase_order(po_id):
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("PO not found")
        if po.status in ('received', 'partially_received', 'completed'):
            raise ValidationError("Cannot cancel a PO that is already being received")
            
        po.status = 'cancelled'
        po.is_active = False
        db.session.commit()

        AuditService.log_action(
            action="PO_CANCELLED",
            entity_type="purchase_order",
            entity_id=po.id,
            details={"po_number": po.po_number},
            user_id=None,
            organisation_id=po.organization_id,
            session=db.session,
        )
        return po
