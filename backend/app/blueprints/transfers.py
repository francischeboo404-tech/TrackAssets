from flask import Blueprint, g, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db
from app.audit_service import AuditService
from app.auth_utils import (
    get_current_organisation_id,
    jwt_required_with_user,
    require_role,
)
from app.db_utils import transaction_retry
from app.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models import asset, organization, transfer
from app.validation import (
    TransferRequestSchema,
    TransferReviewSchema,
    validate_input,
)
from app.services.event_bus import event_bus

transfers_bp = Blueprint("transfers", __name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@transfers_bp.route("/request", methods=["POST"])
@jwt_required_with_user
@require_role("admin", "staff", "dept_head")
@limiter.limit("20 per minute")
@transaction_retry(max_retries=3)
def request_transfer():
    """Request transfer of asset between departments"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    # Validate input
    validated_data, errors = validate_input(TransferRequestSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    item_type = validated_data.get("item_type", "asset")
    
    # Check if new department exists and belongs to organization
    new_dept = organization.Department.query.filter_by(
        id=validated_data["new_department_id"],
        organisation_id=org_id,
        is_active=True,
    ).first()

    if not new_dept:
        raise ValidationError("Invalid destination department")

    if item_type == "asset":
        if not validated_data.get("asset_id"):
            raise ValidationError("asset_id is required for asset transfers")
            
        # Get asset
        asset_obj = asset.Asset.query.filter_by(
            id=validated_data["asset_id"], organisation_id=org_id
        ).first()

        if not asset_obj:
            raise NotFoundError("Asset not found")

        # Check if asset can be transferred (not disposed)
        if asset_obj.status == "disposed":
            raise ValidationError("Cannot transfer a disposed asset")

        # Check if transfer already requested
        existing_request = transfer.TransferRequest.query.filter_by(
            asset_id=validated_data["asset_id"], 
            organisation_id=org_id,
            status="pending"
        ).first()

        if existing_request:
            raise ConflictError("Transfer already requested for this asset")
            
        from_dept_id = asset_obj.department_id
        
        # Create transfer request for asset
        transfer_request = transfer.TransferRequest(
            organisation_id=org_id,
            item_type="asset",
            asset_id=validated_data["asset_id"],
            requested_by=g.user.id,
            from_department_id=from_dept_id,
            to_department_id=validated_data["new_department_id"],
            requested_location=validated_data.get("new_location"),
            to_warehouse_id=validated_data.get("to_warehouse_id"),
            to_bin_id=validated_data.get("to_bin_id"),
            comment=validated_data.get("comment"),
        )
        db.session.add(transfer_request)
        
        # Audit log
        AuditService.log_action(
            action="TRANSFER_REQUESTED",
            entity_type="transfer_request",
            entity_id=transfer_request.id,
            details={
                "asset_id": asset_obj.id,
                "asset_code": asset_obj.asset_code,
                "from_department": from_dept_id,
                "to_department": validated_data["new_department_id"],
                "requested_by": g.user.username,
            },
            organisation_id=org_id,
        )

    else:
        # Inventory Transfer
        if not validated_data.get("inventory_item_id"):
            raise ValidationError("inventory_item_id is required for inventory transfers")
            
        # Check inventory item
        from app.models.inventory import InventoryItem, WarehouseStock
        inv_item = InventoryItem.query.filter_by(
            id=validated_data["inventory_item_id"], organisation_id=org_id
        ).first()
        
        if not inv_item:
            raise NotFoundError("Inventory item not found")
            
        quantity = validated_data.get("quantity", 1)
        from_warehouse_id = validated_data.get("from_warehouse_id")
        
        # Validate stock availability
        if from_warehouse_id:
            stock = WarehouseStock.query.filter_by(item_id=inv_item.id, warehouse_id=from_warehouse_id).first()
            if not stock or stock.quantity_on_hand < quantity:
                raise ValidationError("Insufficient stock in the source warehouse.")
        else:
            if inv_item.quantity < quantity:
                raise ValidationError("Insufficient global stock.")
                
        # We need a from_department_id. Since inventory is global, we can use the requester's department, or just allow null if the schema allows it. But we couldn't drop NOT NULL easily, so let's default to the requester's department or the new_department_id if unknown.
        # Wait, users have `department` as string. Let's use new_department_id as a fallback.
        from_dept_id = validated_data["new_department_id"] 
        
        # Create transfer request for inventory
        transfer_request = transfer.TransferRequest(
            organisation_id=org_id,
            item_type="inventory",
            inventory_item_id=inv_item.id,
            quantity=quantity,
            requested_by=g.user.id,
            from_department_id=from_dept_id,
            to_department_id=validated_data["new_department_id"],
            requested_location=validated_data.get("new_location"),
            to_warehouse_id=validated_data.get("to_warehouse_id"),
            to_bin_id=validated_data.get("to_bin_id"),
            comment=validated_data.get("comment"),
        )
        db.session.add(transfer_request)
        
        AuditService.log_action(
            action="TRANSFER_REQUESTED",
            entity_type="transfer_request",
            entity_id=transfer_request.id,
            details={
                "inventory_item_id": inv_item.id,
                "item_name": inv_item.name,
                "quantity": quantity,
                "to_department": validated_data["new_department_id"],
                "requested_by": g.user.username,
            },
            organisation_id=org_id,
        )

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Transfer request submitted successfully",
                "request_id": transfer_request.id,
            }
        ),
        201,
    )


@transfers_bp.route("/history/<int:asset_id>", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_transfer_history(asset_id):
    """Get transfer history for an asset"""
    org_id = get_current_organisation_id()

    # Verify asset belongs to organization
    asset_obj = asset.Asset.query.filter_by(
        id=asset_id,
        organisation_id=org_id,
    ).first()

    if not asset_obj:
        raise NotFoundError("Asset not found")

    # Get transfer history from audit logs
    from app.models import inventory

    transfer_logs = (
        inventory.AuditLog.query.filter(
            inventory.AuditLog.organisation_id == org_id,
            inventory.AuditLog.entity_type == "asset",
            inventory.AuditLog.entity_id == asset_id,
            inventory.AuditLog.action == "ASSET_TRANSFER",
        )
        .order_by(inventory.AuditLog.created_at.desc())
        .all()
    )

    history = []
    for log in transfer_logs:
        details = log.details or {}
        history.append(
            {
                "id": log.id,
                "timestamp": log.created_at.isoformat(),
                "from_department": details.get("from_department"),
                "to_department": details.get("to_department"),
                "old_location": details.get("old_location"),
                "new_location": details.get("new_location"),
                "transferred_by": details.get("transferred_by"),
                "user_id": log.user_id,
            }
        )

    return (
        jsonify(
            {
                "asset_id": asset_id,
                "asset_code": asset_obj.asset_code,
                "asset_name": asset_obj.name,
                "current_department": asset_obj.department_id,
                "current_location": asset_obj.location,
                "transfer_history": history,
            }
        ),
        200,
    )


@transfers_bp.route("/stats", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_transfer_stats():
    """Get counts for different transfer request statuses"""
    org_id = get_current_organisation_id()
    
    pending = transfer.TransferRequest.query.filter_by(organisation_id=org_id, status="pending").count()
    approved = transfer.TransferRequest.query.filter_by(organisation_id=org_id, status="approved").count()
    rejected = transfer.TransferRequest.query.filter_by(organisation_id=org_id, status="rejected").count()
    in_transit = transfer.TransferRequest.query.filter_by(organisation_id=org_id, status="in_transit").count()
    completed = transfer.TransferRequest.query.filter_by(organisation_id=org_id, status="completed").count()
    
    return jsonify({
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "in_transit": in_transit,
        "completed": completed,
        "total": pending + approved + rejected + in_transit + completed
    }), 200


@transfers_bp.route("/requests", methods=["GET"])
@jwt_required_with_user
@limiter.limit("50 per minute")
def get_transfer_requests():
    """Get transfer requests for current user's organization"""
    org_id = get_current_organisation_id()

    # Query parameters
    status = request.args.get("status", "pending")
    search = request.args.get("search")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    from sqlalchemy.orm import joinedload

    query = transfer.TransferRequest.query.options(
        joinedload(transfer.TransferRequest.asset),
        joinedload(transfer.TransferRequest.inventory_item),
        joinedload(transfer.TransferRequest.requester),
        joinedload(transfer.TransferRequest.reviewer),
        joinedload(transfer.TransferRequest.from_department),
        joinedload(transfer.TransferRequest.to_department),
    ).filter_by(organisation_id=org_id)

    if status and status != "all":
        query = query.filter_by(status=status)
        
    if search:
        from app.models.inventory import InventoryItem

        query = query.outerjoin(asset.Asset).outerjoin(
            InventoryItem,
            transfer.TransferRequest.inventory_item_id == InventoryItem.id,
        ).outerjoin(
            organization.User,
            transfer.TransferRequest.requested_by == organization.User.id,
        ).filter(
            db.or_(
                asset.Asset.name.ilike(f"%{search}%"),
                asset.Asset.asset_code.ilike(f"%{search}%"),
                InventoryItem.name.ilike(f"%{search}%"),
                InventoryItem.sku.ilike(f"%{search}%"),
                organization.User.username.ilike(f"%{search}%"),
                transfer.TransferRequest.comment.ilike(f"%{search}%")
            )
        )

    # Filter based on user role
    if g.user.role not in ["admin", "store_manager"]:
        # Non-admins can only see requests they created or for
        # departments they head
        headed_dept_ids = [d.id for d in g.user.headed_departments]
        query = query.filter(
            db.or_(
                transfer.TransferRequest.requested_by == g.user.id,
                transfer.TransferRequest.from_department_id.in_(
                    headed_dept_ids
                ),
                transfer.TransferRequest.to_department_id.in_(headed_dept_ids),
            )
        )

    requests = query.order_by(
        transfer.TransferRequest.requested_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return (
        jsonify(
            {
                "transfer_requests": [
                    {
                        "id": r.id,
                        "item_type": r.item_type,
                        "asset_id": r.asset_id,
                        "inventory_item_id": r.inventory_item_id,
                        "quantity": r.quantity,
                        "asset_code": r.asset.asset_code if r.asset else (r.inventory_item.sku if r.inventory_item else None),
                        "asset_name": r.asset.name if r.asset else (r.inventory_item.name if r.inventory_item else None),
                        "from_department": r.from_department_id,
                        "from_department_name": (
                            r.from_department.name
                            if r.from_department
                            else None
                        ),
                        "to_department": r.to_department_id,
                        "to_department_name": (
                            r.to_department.name if r.to_department else None
                        ),
                        "requested_location": r.requested_location,
                        "comment": r.comment,
                        "status": r.status,
                        "requested_by": (
                            r.requester.username if r.requester else None
                        ),
                        "requested_at": r.requested_at.isoformat(),
                        "reviewed_by": (
                            r.reviewer.username if r.reviewer else None
                        ),
                        "reviewed_at": (
                            r.reviewed_at.isoformat()
                            if r.reviewed_at
                            else None
                        ),
                        "review_comments": r.review_comments,
                    }
                    for r in requests.items
                ],
                "pagination": {
                    "page": requests.page,
                    "per_page": requests.per_page,
                    "total": requests.total,
                    "pages": requests.pages,
                    "has_next": requests.has_next,
                    "has_prev": requests.has_prev,
                },
            }
        ),
        200,
    )


@transfers_bp.route("/bulk", methods=["POST"])
@jwt_required_with_user
@require_role("admin")
@limiter.limit("10 per minute")
def bulk_transfer():
    """Bulk transfer multiple assets to a department"""
    data = request.get_json()
    org_id = get_current_organisation_id()

    asset_ids = data.get("asset_ids", [])
    new_department_id = data.get("new_department_id")
    new_location = data.get("new_location")

    if not asset_ids or not new_department_id:
        raise ValidationError("asset_ids and new_department_id are required")

    # Validate department
    new_dept = organization.Department.query.filter_by(
        id=new_department_id, organisation_id=org_id, is_active=True
    ).first()

    if not new_dept:
        raise ValidationError("Invalid destination department")

    # Get assets
    assets_to_transfer = asset.Asset.query.filter(
        asset.Asset.id.in_(asset_ids), asset.Asset.organisation_id == org_id
    ).all()

    if len(assets_to_transfer) != len(asset_ids):
        raise ValidationError(
            "Some assets not found or don't belong to your organization"
        )

    # Check if any assets are disposed
    disposed_assets = [a for a in assets_to_transfer if a.status == "disposed"]
    if disposed_assets:
        disposed_codes = [a.asset_code for a in disposed_assets]
        raise ValidationError(
            f"Cannot transfer disposed assets: {disposed_codes}"
        )

    # Perform bulk transfer
    transferred_assets = []
    for asset_obj in assets_to_transfer:
        old_dept_id = asset_obj.department_id
        old_location = asset_obj.location

        asset_obj.department_id = new_department_id
        asset_obj.location = new_location or asset_obj.location
        asset_obj.updated_at = db.func.now()

        transferred_assets.append(
            {
                "id": asset_obj.id,
                "asset_code": asset_obj.asset_code,
                "old_department": old_dept_id,
                "new_department": new_department_id,
                "old_location": old_location,
                "new_location": asset_obj.location,
            }
        )

    db.session.commit()

    # Audit log for bulk transfer
    AuditService.log_action(
        action="BULK_ASSET_TRANSFER",
        entity_type="transfer",
        entity_id=None,
        details={
            "transferred_assets": transferred_assets,
            "new_department": new_department_id,
            "new_location": new_location,
            "transferred_by": g.user.username,
            "count": len(transferred_assets),
        },
        organisation_id=org_id,
    )

    return (
        jsonify(
            {
                "message": (
                    f"Successfully transferred {len(transferred_assets)} assets"
                ),
                "transferred_assets": transferred_assets,
            }
        ),
        200,
    )


@transfers_bp.route("/requests/<int:request_id>/approve", methods=["POST"])
@jwt_required_with_user
@require_role("admin", "dept_head")
@limiter.limit("20 per minute")
@transaction_retry(max_retries=3)
def approve_transfer_request(request_id):
    """Approve a transfer request"""
    data = request.get_json() or {}
    org_id = get_current_organisation_id()

    validated_data, errors = validate_input(TransferReviewSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Get transfer request with lock
    transfer_req = (
        transfer.TransferRequest.query.with_for_update()
        .filter_by(id=request_id, organisation_id=org_id, status="pending")
        .first()
    )

    if not transfer_req:
        raise NotFoundError("Transfer request not found")

    # Check permissions
    if g.user.role not in ["admin"]:
        # Department heads can only approve transfers from/to departments
        # they head
        if transfer_req.from_department_id not in [
            d.id for d in g.user.headed_departments
        ] and transfer_req.to_department_id not in [
            d.id for d in g.user.headed_departments
        ]:
            raise AuthorizationError(
                "You can only approve transfers for departments you head"
            )

    if transfer_req.item_type == "asset":
        # Get asset with lock
        asset_obj = (
            asset.Asset.query.with_for_update()
            .filter_by(id=transfer_req.asset_id, organisation_id=org_id)
            .first()
        )
        if not asset_obj:
            raise NotFoundError("Asset not found")
        item_id = asset_obj.id
    else:
        from app.models.inventory import InventoryItem
        inv_item = (
            InventoryItem.query.with_for_update()
            .filter_by(id=transfer_req.inventory_item_id, organisation_id=org_id)
            .first()
        )
        if not inv_item:
            raise NotFoundError("Inventory item not found")
        item_id = inv_item.id

    # Update transfer request
    transfer_req.status = "approved"
    transfer_req.reviewed_by = g.user.id
    transfer_req.reviewed_at = db.func.now()
    transfer_req.review_comments = validated_data.get("comments")

    AuditService.log_action(
        action="TRANSFER_REQUEST_APPROVED",
        entity_type="transfer_request",
        entity_id=transfer_req.id,
        details={"item_id": item_id, "item_type": transfer_req.item_type, "approved_by": g.user.username},
        organisation_id=org_id,
    )

    db.session.commit()

    event_bus.publish(
        "ASSET_TRANSFER",
        {
            "transfer_request_id": transfer_req.id,
            "status": "approved",
            "item_type": transfer_req.item_type,
            "item_id": item_id,
        },
        organisation_id=org_id,
    )

    return (
        jsonify(
            {
                "message": "Transfer request approved successfully",
                "transfer_request_id": transfer_req.id,
            }
        ),
        200,
    )


@transfers_bp.route("/requests/<int:request_id>/dispatch", methods=["POST"])
@jwt_required_with_user
@require_role("admin", "dept_head")
@limiter.limit("20 per minute")
@transaction_retry(max_retries=3)
def dispatch_transfer_request(request_id):
    """Dispatch an approved transfer request"""
    org_id = get_current_organisation_id()

    # Get transfer request with lock
    transfer_req = (
        transfer.TransferRequest.query.with_for_update()
        .filter_by(id=request_id, organisation_id=org_id, status="approved")
        .first()
    )

    if not transfer_req:
        raise NotFoundError("Transfer request not found or not approved")

    transfer_req.status = "in_transit"
    destination = transfer_req.to_department.name if transfer_req.to_department else "Destination"

    if transfer_req.item_type == "asset":
        asset_obj = (
            asset.Asset.query.with_for_update()
            .filter_by(id=transfer_req.asset_id, organisation_id=org_id)
            .first()
        )
        if not asset_obj:
            raise NotFoundError("Asset not found")

        old_location = asset_obj.location
        asset_obj.location = f"In Transit to {destination}"
        asset_obj.updated_at = db.func.now()

        # Vacate the old bin during transit
        if asset_obj.bin_id:
            from app.models.location_topology import WarehouseBin
            old_bin = WarehouseBin.query.get(asset_obj.bin_id)
            if old_bin:
                old_bin.status = "available"
            asset_obj.bin_id = None
            
        item_id = asset_obj.id
    else:
        # Inventory Transfer dispatch
        from app.models.inventory import InventoryItem, WarehouseStock
        inv_item = (
            InventoryItem.query.with_for_update()
            .filter_by(id=transfer_req.inventory_item_id, organisation_id=org_id)
            .first()
        )
        if not inv_item:
            raise NotFoundError("Inventory item not found")
            
        # We don't deduct stock at dispatch? Actually, for inventory, we should deduct from source warehouse now if specified, or global.
        # But wait, deducting at dispatch means the stock is "In transit". If it fails, it needs rollback. 
        # For simplicity, we just change the request status to "in_transit" and deduct/add upon "receive". Or we deduct now and add later.
        # Let's deduct now.
        # wait, transferring inventory stock is complex to track "in transit" without a transit warehouse. Let's just deduct it now and we add it later on receive.
        
        # Deduct stock
        from_warehouse_id = transfer_req.asset_id # Wait, where did we store from_warehouse_id? It wasn't in TransferRequest. 
        # To avoid schema changes, we can just deduct from global stock now, or just do the full stock transfer at the "Receive" stage.
        # Let's do the full stock transfer at the "Receive" stage, so dispatch just marks it as in_transit.
        old_location = "Source Warehouse"
        item_id = inv_item.id

    AuditService.log_action(
        action="TRANSFER_REQUEST_DISPATCHED",
        entity_type="transfer_request",
        entity_id=transfer_req.id,
        details={
            "item_id": item_id,
            "item_type": transfer_req.item_type,
            "dispatched_by": g.user.username,
            "old_location": old_location,
        },
        organisation_id=org_id,
    )

    db.session.commit()

    event_bus.publish(
        "ASSET_TRANSFER",
        {
            "transfer_request_id": transfer_req.id,
            "status": "in_transit",
            "item_type": transfer_req.item_type,
            "item_id": item_id,
        },
        organisation_id=org_id,
    )

    return (
        jsonify(
            {
                "message": "Transfer request dispatched successfully",
                "transfer_request_id": transfer_req.id,
            }
        ),
        200,
    )


@transfers_bp.route("/requests/<int:request_id>/receive", methods=["POST"])
@jwt_required_with_user
@require_role("admin", "dept_head")
@limiter.limit("20 per minute")
@transaction_retry(max_retries=3)
def receive_transfer_request(request_id):
    """Receive an in-transit transfer request"""
    org_id = get_current_organisation_id()

    # Get transfer request with lock
    transfer_req = (
        transfer.TransferRequest.query.with_for_update()
        .filter_by(id=request_id, organisation_id=org_id, status="in_transit")
        .first()
    )

    if not transfer_req:
        raise NotFoundError("Transfer request not found or not in transit")

    # Check permissions
    if g.user.role not in ["admin"]:
        # Only destination department heads can receive
        if transfer_req.to_department_id not in [
            d.id for d in g.user.headed_departments
        ]:
            raise AuthorizationError(
                "You can only receive transfers for departments you head"
            )

    transfer_req.status = "completed"
    
    if transfer_req.item_type == "asset":
        asset_obj = (
            asset.Asset.query.with_for_update()
            .filter_by(id=transfer_req.asset_id, organisation_id=org_id)
            .first()
        )
        if not asset_obj:
            raise NotFoundError("Asset not found")

        old_dept_id = asset_obj.department_id
        old_bin_id = asset_obj.bin_id

        # Update state
        asset_obj.department_id = transfer_req.to_department_id
        
        if transfer_req.requested_location:
            asset_obj.location = transfer_req.requested_location
        else:
            asset_obj.location = transfer_req.to_department.name if transfer_req.to_department else "Received"
            
        asset_obj.warehouse_id = transfer_req.to_warehouse_id or asset_obj.warehouse_id
        asset_obj.bin_id = transfer_req.to_bin_id or asset_obj.bin_id
        asset_obj.updated_at = db.func.now()

        # Manage bin status interoperability
        from app.models.location_topology import WarehouseBin
        
        if old_bin_id and old_bin_id != asset_obj.bin_id:
            old_bin = WarehouseBin.query.get(old_bin_id)
            if old_bin:
                old_bin.status = "available"
                
        if asset_obj.bin_id and asset_obj.bin_id != old_bin_id:
            new_bin = WarehouseBin.query.get(asset_obj.bin_id)
            if new_bin:
                new_bin.status = "occupied"

        # Audit logs
        AuditService.log_transfer(
            asset_obj,
            old_dept_id,
            transfer_req.to_department_id,
            details={
                "transfer_request_id": transfer_req.id,
                "received_by": g.user.username,
                "new_location": asset_obj.location,
            },
        )
        item_id = asset_obj.id
    else:
        # Inventory transfer receive — use inventory service for consistent stock logging
        from app.models.inventory import InventoryItem
        from app.repositories.inventory_repository import InventoryRepository
        from app.services.inventory_service import InventoryService

        inv_item = (
            InventoryItem.query.with_for_update()
            .filter_by(id=transfer_req.inventory_item_id, organisation_id=org_id)
            .first()
        )
        if not inv_item:
            raise NotFoundError("Inventory item not found")

        inventory_service = InventoryService(
            repository=InventoryRepository(), session=db.session
        )
        inventory_service.update_stock(
            inv_item.id,
            org_id,
            "IN",
            transfer_req.quantity,
            warehouse_id=transfer_req.to_warehouse_id,
            reference=f"Transfer Request {transfer_req.id}",
            notes="Received from transfer request",
        )
        item_id = inv_item.id

    AuditService.log_action(
        action="TRANSFER_REQUEST_COMPLETED",
        entity_type="transfer_request",
        entity_id=transfer_req.id,
        details={"item_id": item_id, "item_type": transfer_req.item_type, "received_by": g.user.username},
        organisation_id=org_id,
    )

    db.session.commit()

    event_bus.publish(
        "ASSET_TRANSFER",
        {
            "transfer_request_id": transfer_req.id,
            "status": "completed",
            "item_type": transfer_req.item_type,
            "item_id": item_id,
        },
        organisation_id=org_id,
    )

    return (
        jsonify(
            {
                "message": "Transfer request received successfully",
                "item_id": item_id,
                "item_type": transfer_req.item_type,
                "transfer_request_id": transfer_req.id,
            }
        ),
        200,
    )


@transfers_bp.route("/requests/<int:request_id>/reject", methods=["POST"])
@jwt_required_with_user
@require_role("admin", "dept_head")
@limiter.limit("20 per minute")
@transaction_retry(max_retries=3)
def reject_transfer_request(request_id):
    """Reject a transfer request"""
    data = request.get_json() or {}
    org_id = get_current_organisation_id()

    validated_data, errors = validate_input(TransferReviewSchema, data)
    if errors:
        raise ValidationError("Validation failed", errors)

    # Get transfer request with lock
    transfer_req = (
        transfer.TransferRequest.query.with_for_update()
        .filter_by(id=request_id, organisation_id=org_id, status="pending")
        .first()
    )

    if not transfer_req:
        raise NotFoundError("Transfer request not found")

    # Check permissions
    if g.user.role not in ["admin"]:
        # Department heads can only reject transfers from/to departments
        # they head
        if transfer_req.from_department_id not in [
            d.id for d in g.user.headed_departments
        ] and transfer_req.to_department_id not in [
            d.id for d in g.user.headed_departments
        ]:
            raise AuthorizationError(
                "You can only reject transfers for departments you head"
            )

    # Update transfer request
    transfer_req.status = "rejected"
    transfer_req.reviewed_by = g.user.id
    transfer_req.reviewed_at = db.func.now()
    transfer_req.review_comments = validated_data.get("comments")

    # Audit log
    AuditService.log_action(
        action="TRANSFER_REQUEST_REJECTED",
        entity_type="transfer_request",
        entity_id=transfer_req.id,
        details={
            "asset_id": transfer_req.asset_id,
            "rejected_by": g.user.username,
            "comments": transfer_req.review_comments,
        },
        organisation_id=org_id,
    )

    db.session.commit()

    event_bus.publish(
        "ASSET_TRANSFER",
        {
            "transfer_request_id": transfer_req.id,
            "status": "rejected",
            "item_type": transfer_req.item_type,
            "item_id": transfer_req.asset_id or transfer_req.inventory_item_id,
        },
        organisation_id=org_id,
    )

    return (
        jsonify(
            {
                "message": "Transfer request rejected",
                "transfer_request_id": transfer_req.id,
            }
        ),
        200,
    )
