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
from datetime import datetime, timezone

class ProcurementService:
    @staticmethod
    def create_purchase_request(org_id, requester_id, reason, items_data):
        # Auto-generate PR number: PR-YYYY-XXXXX
        year = datetime.now(timezone.utc).year
        count = PurchaseRequest.query.filter(PurchaseRequest.pr_number.like(f"PR-{year}-%")).count() + 1
        pr_number = f"PR-{year}-{count:05d}"
        
        pr = PurchaseRequest(
            organization_id=org_id,
            pr_number=pr_number,
            requester_id=requester_id,
            reason=reason
        )
        db.session.add(pr)
        db.session.flush() # get ID
        
        for item_data in items_data:
            pr_item = PurchaseRequestItem(
                organization_id=org_id,
                pr_id=pr.id,
                item_id=item_data['item_id'],
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
    def list_purchase_requests(org_id):
        """Return purchase requests for an organization, most recent first."""
        return PurchaseRequest.query.filter_by(organization_id=org_id).order_by(PurchaseRequest.created_at.desc()).all()


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
            pr_item = PurchaseRequestItem(
                organization_id=org_id,
                pr_id=pr.id,
                item_id=item_data['item_id'],
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
                pr_item = PurchaseRequestItem.query.filter_by(pr_id=pr_id, item_id=item['item_id']).first()
                if not pr_item:
                    raise ValidationError(f"Item {item['item_id']} is not in the Purchase Request")
                if int(item['quantity']) > int(pr_item.quantity):
                    raise ValidationError(
                        f"PO quantity for item {item['item_id']} exceeds requested PR quantity ({pr_item.quantity})"
                    )
        elif ris_id:
            from app.models.kenya_gov_models import RequisitionItem
            for item in items_data:
                ris_item = RequisitionItem.query.filter_by(ris_id=ris_id, item_id=item['item_id']).first()
                if not ris_item:
                    raise ValidationError(f"Item {item['item_id']} is not in the Requisition")
                if int(item['quantity']) > int(ris_item.quantity_requested):
                    raise ValidationError(
                        f"PO quantity for item {item['item_id']} exceeds requested Requisition quantity ({ris_item.quantity_requested})"
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
            po_item = PurchaseOrderItem(
                organization_id=org_id,
                po_id=po.id,
                item_id=item_data['item_id'],
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
    def add_canvass_quote(org_id, po_id, supplier_name, item_name, unit_cost, quote_date):
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise ValueError("PO not found")
            
        quote = CanvassQuote(
            organization_id=org_id,
            po_id=po_id,
            supplier_name=supplier_name,
            item_name=item_name,
            unit_cost=unit_cost,
            total_cost=unit_cost, # simplified
            quote_date=quote_date
        )
        db.session.add(quote)
        db.session.commit()
        return quote

    @staticmethod
    def list_purchase_orders(org_id):
        """Return purchase orders for an organization, most recent first."""
        return PurchaseOrder.query.filter_by(organization_id=org_id).order_by(PurchaseOrder.created_at.desc()).all()

    @staticmethod
    def approve_purchase_order(po_id, user_id=None):
        po = db.session.get(PurchaseOrder, po_id)
        if not po:
            raise NotFoundError("PO not found")
        
        # 3-supplier canvass requirement for orders >= KES 1,000
        if po.total_amount >= 1000:
            quotes_count = CanvassQuote.query.filter_by(po_id=po_id).count()
            if quotes_count < 3:
                raise ValidationError("PO over KES 1,000 requires at least 3 canvass quotes before approval")
                
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
            details={"po_number": po.po_number, "quotes_count": quotes_count if 'quotes_count' in locals() else 0},
            user_id=user_id,
            organisation_id=po.organization_id,
            module="procurement",
            session=db.session,
        )
        return po

    @staticmethod
    def reject_purchase_order(po_id):
        po = db.session.get(PurchaseOrder, po_id)
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
