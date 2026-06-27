from flask import Blueprint, request, jsonify
from app.auth_utils import jwt_required_with_user, get_current_organisation_id, get_current_user_id, require_role
from app.services.procurement_service import ProcurementService

procurement_bp = Blueprint('procurement_bp', __name__)


@procurement_bp.route('/purchase-requests', methods=['POST'])
@jwt_required_with_user
def create_pr():
    data = request.json
    org_id = get_current_organisation_id()
    user_id = get_current_user_id()

    pr = ProcurementService.create_purchase_request(
        org_id=org_id,
        requester_id=user_id,
        reason=data.get('reason'),
        items_data=data.get('items', []),
    )
    return jsonify({'message': 'PR created', 'pr_id': pr.id, 'pr_number': pr.pr_number}), 201

@procurement_bp.route('/purchase-requests/<int:id>', methods=['GET', 'PUT'])
@jwt_required_with_user
def handle_pr(id):
    if request.method == 'GET':
        from app import db
        from app.models.kenya_gov_models import PurchaseRequest, PurchaseRequestItem
        from app.models.inventory import InventoryItem

        org_id = get_current_organisation_id()
        pr = db.session.get(PurchaseRequest, id)
        if not pr or pr.organization_id != org_id:
            return jsonify({'message': 'PR not found', 'status_code': 404}), 404

        pr_items = PurchaseRequestItem.query.filter_by(pr_id=id).all()
        items = []
        for pri in pr_items:
            inv = db.session.get(InventoryItem, pri.item_id)
            items.append({
                'id': pri.id,
                'item_id': pri.item_id,
                'sku': getattr(inv, 'sku', None),
                'name': getattr(inv, 'name', None),
                'quantity': pri.quantity,
                'estimated_cost': float(pri.estimated_cost) if pri.estimated_cost is not None else 0.0,
                'justification': pri.justification,
            })

        return jsonify({
            'id': pr.id,
            'pr_number': pr.pr_number,
            'reason': pr.reason,
            'status': pr.status,
            'created_at': pr.created_at.isoformat(),
            'approved_at': pr.approved_at.isoformat() if pr.approved_at else None,
            'items': items
        }), 200

    elif request.method == 'PUT':
        data = request.json
        org_id = get_current_organisation_id()
        user_id = get_current_user_id()

        pr = ProcurementService.update_purchase_request(
            org_id=org_id,
            pr_id=id,
            requester_id=user_id,
            reason=data.get('reason'),
            items_data=data.get('items', []),
        )
        return jsonify({'message': 'PR updated', 'pr_id': pr.id, 'pr_number': pr.pr_number}), 200


@procurement_bp.route('/purchase-requests', methods=['GET'])
@jwt_required_with_user
def list_purchase_requests():
    from app.models.kenya_gov_models import PurchaseRequestItem
    org_id = get_current_organisation_id()
    prs = ProcurementService.list_purchase_requests(org_id)
    pr_list = []
    for p in prs:
        pr_items_data = []
        for pri in PurchaseRequestItem.query.filter_by(pr_id=p.id).all():
            pr_items_data.append({
                'item_id': pri.item_id,
                'quantity': pri.quantity,
                'estimated_cost': float(pri.estimated_cost) if pri.estimated_cost else 0.0
            })
        pr_list.append({
            'id': p.id,
            'pr_number': p.pr_number,
            'reason': p.reason,
            'status': p.status,
            'created_at': p.created_at.isoformat(),
            'approved_at': p.approved_at.isoformat() if p.approved_at else None,
            'items': pr_items_data
        })

    return (
        jsonify(
            {
                'purchase_requests': pr_list
            }
        ),
        200,
    )



@procurement_bp.route('/purchase-requests/<int:id>/approve', methods=['PUT'])
@require_role('procurement_officer')
def approve_pr(id):
    user_id = get_current_user_id()
    pr = ProcurementService.approve_purchase_request(id, department_head_id=user_id)
    return jsonify({'message': 'PR approved', 'pr_id': pr.id})


@procurement_bp.route('/purchase-requests/<int:id>/reject', methods=['PUT'])
@require_role('procurement_officer')
def reject_pr(id):
    user_id = get_current_user_id()
    pr = ProcurementService.reject_purchase_request(id, department_head_id=user_id)
    return jsonify({'message': 'PR rejected', 'pr_id': pr.id})


@procurement_bp.route('/purchase-orders', methods=['POST'])
@require_role('procurement_officer')
def create_po():
    data = request.json
    org_id = get_current_organisation_id()

    po = ProcurementService.create_purchase_order(
        org_id=org_id,
        pr_id=data.get('pr_id'),
        ris_id=data.get('ris_id'),
        supplier_id=data.get('supplier_id'),
        items_data=data.get('items', []),
    )
    return (
        jsonify({'message': 'PO created', 'po_id': po.id, 'po_number': po.po_number}),
        201,
    )


@procurement_bp.route('/purchase-orders/<int:id>/canvass', methods=['POST'])
@require_role('procurement_officer')
def add_canvass(id):
    data = request.json
    org_id = get_current_organisation_id()

    from datetime import datetime, timezone

    quote = ProcurementService.add_canvass_quote(
        org_id=org_id,
        po_id=id,
        supplier_name=data.get('supplier_name'),
        item_name=data.get('item_name'),
        unit_cost=data.get('unit_cost'),
        quote_date=datetime.now(timezone.utc),
    )
    return jsonify({'message': 'Canvass quote added', 'quote_id': quote.id}), 201


@procurement_bp.route('/purchase-orders/<int:id>/approve', methods=['PUT'])
@require_role('admin', 'procurement_officer')
def approve_po(id):
    user_id = get_current_user_id()
    po = ProcurementService.approve_purchase_order(id, user_id=user_id)
    return jsonify({'message': 'PO approved', 'po_id': po.id})


@procurement_bp.route('/purchase-orders', methods=['GET'])
@jwt_required_with_user
def list_purchase_orders():
    org_id = get_current_organisation_id()
    pos = ProcurementService.list_purchase_orders(org_id)
    return (
        jsonify(
            {
                'purchase_orders': [
                    {
                        'id': o.id,
                        'po_number': o.po_number,
                        'pr_id': o.pr_id,
                        'supplier_id': o.supplier_id,
                        'total_amount': float(o.total_amount),
                        'status': o.status,
                        'created_at': o.created_at.isoformat() if getattr(o, 'created_at', None) else None,
                        'approved_at': o.approved_at.isoformat() if getattr(o, 'approved_at', None) else None,
                    }
                    for o in pos
                ]
            }
        ),
        200,
    )


@procurement_bp.route('/purchase-orders/<int:id>', methods=['GET'])
@jwt_required_with_user
def get_purchase_order(id):
    from app import db
    from app.models.kenya_gov_models import PurchaseOrder, PurchaseOrderItem, CanvassQuote
    from app.models.inventory import InventoryItem
    from app.models.supplier import Supplier

    org_id = get_current_organisation_id()
    po = db.session.get(PurchaseOrder, id)
    if not po or po.organization_id != org_id:
        return jsonify({'message': 'PO not found', 'status_code': 404}), 404

    supplier = db.session.get(Supplier, po.supplier_id)
    supplier_name = getattr(supplier, 'name', 'Unknown') if supplier else 'Unknown'

    po_items = PurchaseOrderItem.query.filter_by(po_id=id).all()
    items = []
    for poi in po_items:
        inv = db.session.get(InventoryItem, poi.item_id)
        items.append({
            'id': poi.id,
            'item_id': poi.item_id,
            'sku': getattr(inv, 'sku', None),
            'name': getattr(inv, 'name', None),
            'quantity': poi.quantity,
            'unit_cost': float(poi.unit_cost) if poi.unit_cost else 0.0,
            'total_cost': float(poi.total_cost) if poi.total_cost else 0.0,
        })

    quotes = CanvassQuote.query.filter_by(po_id=id).all()
    canvass_quotes = []
    for q in quotes:
        canvass_quotes.append({
            'id': q.id,
            'supplier_name': q.supplier_name,
            'item_name': q.item_name,
            'unit_cost': float(q.unit_cost),
            'quote_date': q.quote_date.isoformat() if q.quote_date else None,
        })

    return jsonify({
        'id': po.id,
        'po_number': po.po_number,
        'pr_id': po.pr_id,
        'supplier_id': po.supplier_id,
        'supplier_name': supplier_name,
        'total_amount': float(po.total_amount),
        'status': po.status,
        'created_at': po.created_at.isoformat() if po.created_at else None,
        'approved_at': po.approved_at.isoformat() if po.approved_at else None,
        'items': items,
        'canvass_quotes': canvass_quotes
    }), 200


@procurement_bp.route('/purchase-orders/<int:id>/reject', methods=['PUT'])
@require_role('admin', 'procurement_officer')
def reject_po(id):
    po = ProcurementService.reject_purchase_order(id)
    return jsonify({'message': 'PO rejected', 'po_id': po.id})

@procurement_bp.route('/purchase-orders/<int:id>/cancel', methods=['PUT'])
@require_role('admin', 'procurement_officer')
def cancel_po(id):
    po = ProcurementService.cancel_purchase_order(id)
    return jsonify({'message': 'PO cancelled', 'po_id': po.id})
