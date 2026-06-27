from flask import Blueprint, request, jsonify, g
from app import db
from app.auth_utils import jwt_required_with_user, get_current_organisation_id, get_current_user_id, require_role
from app.errors import AuthorizationError
from app.services.requisition_service import RequisitionService
from app.models.kenya_gov_models import RequisitionSlip, RequisitionItem
from app.models.inventory import InventoryItem

requisition_bp = Blueprint('requisition_bp', __name__)

@requisition_bp.route('/requisitions', methods=['POST'])
@jwt_required_with_user
def create_requisition():
    data = request.json
    org_id = get_current_organisation_id()
    user_id = get_current_user_id()
    # Validate bin selection permissions: only users with inventory stock permissions may set bin_id
    items_payload = data.get('items', [])
    if any((itm.get('bin_id') is not None) for itm in items_payload):
        if not g.user.has_permission('inventory:stock'):
            raise AuthorizationError("Permission 'inventory:stock' required to select bins")
    ris = RequisitionService.create_requisition(
        org_id=org_id,
        requester_id=user_id,
        items_data=data.get('items', []),
    )
    return (
        jsonify({'message': 'Requisition created', 'ris_id': ris.id, 'ris_number': ris.ris_number}),
        201,
    )

@requisition_bp.route('/issue-slips/<int:id>/approve', methods=['PUT'])
@require_role('procurement_officer')
def approve_ris(id):
    user_id = get_current_user_id()
    ris = RequisitionService.approve_requisition(id, department_head_id=user_id)
    return jsonify({'message': 'RIS approved', 'ris_id': ris.id})

@requisition_bp.route('/issue-slips/<int:id>/issue', methods=['PUT'])
@require_role('logistics_officer')
def issue_ris(id):
    user_id = get_current_user_id()
    ris = RequisitionService.issue_requisition(id)
    return jsonify({'message': 'Items issued successfully', 'ris_id': ris.id})


@requisition_bp.route('/issue-slips/<int:id>/cancel', methods=['POST'])
@jwt_required_with_user
def cancel_ris(id):
    """Cancel a requisition if allowed."""
    user_id = get_current_user_id()
    data = request.json or {}
    reason = data.get('reason')
    ris = RequisitionService.cancel_requisition(id, cancelled_by_id=user_id, reason=reason)
    return jsonify({'message': 'RIS cancelled', 'ris_id': ris.id})


@requisition_bp.route('/issue-slips/<int:id>/return', methods=['POST'])
@require_role('admin', 'store_manager', 'logistics_officer')
def return_ris(id):
    """Process return-to-store for an issued requisition."""
    user_id = get_current_user_id()
    data = request.json or {}
    items = data.get('items')
    ris = RequisitionService.return_to_store(id, returned_by_id=user_id, items=items)
    return jsonify({'message': 'RIS returned', 'ris_id': ris.id})


@requisition_bp.route('/issue-slips/<int:id>', methods=['GET'])
@jwt_required_with_user
def get_ris(id):
    """Retrieve RIS details including requested and issued quantities."""
    org_id = get_current_organisation_id()
    ris = db.session.get(RequisitionSlip, id)
    if not ris or ris.organization_id != org_id:
        return jsonify({'message': 'RIS not found', 'status_code': 404}), 404

    req_items = RequisitionItem.query.filter_by(ris_id=id).all()
    items = []
    for ri in req_items:
        inv = db.session.get(InventoryItem, ri.item_id)
        items.append({
            'id': ri.id,
            'item_id': ri.item_id,
            'sku': getattr(inv, 'sku', None),
            'name': getattr(inv, 'name', None),
            'quantity_requested': int(ri.quantity_requested or 0),
            'quantity_issued': int(ri.quantity_issued or 0),
            'unit_cost': float(ri.unit_cost) if ri.unit_cost is not None else None,
        })

    return jsonify({'ris_id': ris.id, 'ris_number': ris.ris_number, 'status': ris.status, 'items': items})


@requisition_bp.route('/issue-slips', methods=['GET'])
@jwt_required_with_user
def list_ris():
    """List recent or searched RIS for the current organisation."""
    org_id = get_current_organisation_id()
    q = request.args.get('q')
    try:
        limit = int(request.args.get('limit', 10))
    except Exception:
        limit = 10
    try:
        offset = int(request.args.get('offset', 0))
    except Exception:
        offset = 0

    query = RequisitionSlip.query.filter_by(organization_id=org_id)
    if q:
        q = q.strip()
        if q.isdigit():
            query = query.filter(RequisitionSlip.id == int(q))
        else:
            query = query.filter(RequisitionSlip.ris_number.ilike(f"%{q}%"))

    results = (
        query.order_by(RequisitionSlip.created_at.desc()).offset(offset).limit(limit).all()
    )
    items = []
    for r in results:
        req_items = RequisitionItem.query.filter_by(ris_id=r.id).all()
        r_items = []
        for ri in req_items:
            r_items.append({
                'item_id': ri.item_id,
                'quantity_requested': int(ri.quantity_requested or 0),
                'quantity_issued': int(ri.quantity_issued or 0),
                'unit_cost': float(ri.unit_cost) if ri.unit_cost is not None else 0.0,
            })
            
        items.append({
            'id': r.id,
            'ris_number': r.ris_number,
            'status': r.status,
            'requested_date': r.requested_date.isoformat() if getattr(r, 'requested_date', None) else None,
            'department_name': 'Dept', # Add dummy or fetched department name for UI
            'items': r_items
        })

    return jsonify({
        'items': items,
        'next_offset': offset + len(items),
        'has_more': len(items) == limit,
    })
