from datetime import date, datetime
from flask import Blueprint, request, jsonify
from app import limiter
from app.auth_utils import jwt_required_with_user, get_current_organisation_id, get_current_user_id, require_role
from app.services.receiving_service import ReceivingService

receiving_bp = Blueprint('receiving_bp', __name__)


def _serialize_datetime_value(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def _create_grn():
    from flask import g
    from app.errors import AuthorizationError, ValidationError, NotFoundError, APIError
    
    if not g.user or g.user.role not in ("procurement_officer", "store_manager", "admin"):
        return jsonify({
            "message": "Unauthorized"
        }), 403

    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "message": "Request body is required",
            "error": "ValidationError",
            "status_code": 400
        }), 400
        
    org_id = get_current_organisation_id()
    user_id = get_current_user_id()

    try:
        grn = ReceivingService.create_grn(
            org_id=org_id,
            po_id=data.get('po_id'),
            received_by_id=user_id,
            items_data=data.get('items', []),
            invoice_number=data.get('invoice_number'),
            delivery_note_number=data.get('delivery_note_number')
        )
        return (
            jsonify({'message': 'GRN created', 'grn_id': grn.id, 'grn_number': grn.grn_number}),
            201,
        )
    except (ValidationError, NotFoundError) as e:
        # Re-raise to let the error handler deal with it
        raise
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to create GRN: {str(e)}",
            "error": "InternalError",
            "status_code": 500
        }), 500

def _list_grns():
    org_id = get_current_organisation_id()
    grns = ReceivingService.list_goods_receipts(org_id)
    return jsonify({
        'goods_receipts': [
            {
                'id': g.id,
                'grn_number': g.grn_number,
                'invoice_number': g.invoice_number,
                'delivery_note_number': g.delivery_note_number,
                'po_id': g.po_id,
                'received_by_id': g.received_by_id,
                'total_quantity': g.total_quantity,
                'status': g.status,
                'created_at': _serialize_datetime_value(getattr(g, 'created_at', None)),
                'received_date': _serialize_datetime_value(getattr(g, 'received_date', None)),
            } for g in grns
        ]
    }), 200

@receiving_bp.route('/goods-receipts', methods=['GET', 'POST'])
@jwt_required_with_user
@limiter.limit("50 per minute")
def handle_grns():
    if request.method == 'POST':
        return _create_grn()
    return _list_grns()
@receiving_bp.route('/goods-receipts/<int:id>', methods=['GET'])
@jwt_required_with_user
@limiter.limit("100 per minute")
def get_grn(id):
    from app import db
    from app.models.kenya_gov_models import GoodsReceiptNote, GoodsReceiptItem, InspectionReport
    from app.models.inventory import InventoryItem
    from app.models.asset import Asset
    from app.models.location_topology import Warehouse

    org_id = get_current_organisation_id()
    grn = db.session.get(GoodsReceiptNote, id)
    if not grn or grn.organization_id != org_id:
        return jsonify({'message': 'GRN not found', 'status_code': 404}), 404

    grn_items = GoodsReceiptItem.query.filter_by(grn_id=id).all()
    items = []
    for g_item in grn_items:
        inv = db.session.get(InventoryItem, g_item.item_id) if g_item.item_type == 'inventory' else None
        asset = db.session.get(Asset, g_item.asset_id) if g_item.item_type == 'asset' else None
        warehouse = db.session.get(Warehouse, g_item.warehouse_id) if g_item.warehouse_id else None
        
        items.append({
            'id': g_item.id,
            'item_type': g_item.item_type,
            'item_id': g_item.item_id,
            'asset_id': g_item.asset_id,
            'sku': getattr(inv, 'sku', None),
            'name': getattr(inv, 'name', None) or getattr(asset, 'name', None),
            'asset_code': getattr(asset, 'asset_code', None),
            'warehouse_id': g_item.warehouse_id,
            'warehouse_name': warehouse.name if warehouse else None,
            'warehouse_code': warehouse.code if warehouse else None,
            'quantity_received': g_item.quantity_received,
            'quantity_accepted': g_item.quantity_accepted,
            'quantity_rejected': g_item.quantity_rejected,
            'unit_cost': float(g_item.unit_cost) if g_item.unit_cost else 0.0,
            'expiry_date': _serialize_datetime_value(getattr(g_item, 'expiry_date', None)),
        })

    iar = InspectionReport.query.filter_by(grn_id=id).order_by(InspectionReport.id.desc()).first()
    iar_status = iar.status if iar else None
    iar_number = iar.iar_number if iar else None

    return jsonify({
        'id': grn.id,
        'grn_number': grn.grn_number,
        'invoice_number': grn.invoice_number,
        'delivery_note_number': grn.delivery_note_number,
        'po_id': grn.po_id,
        'received_by_id': grn.received_by_id,
        'total_quantity': grn.total_quantity,
        'status': grn.status,
        'received_date': _serialize_datetime_value(getattr(grn, 'received_date', None)),
        'items': items,
        'inspection_report': {
            'status': iar_status,
            'iar_number': iar_number
        } if iar else None
    }), 200


@receiving_bp.route('/inspection-reports', methods=['POST'])
@require_role('procurement_officer', 'store_manager')
@limiter.limit("20 per minute")
def create_iar():
    data = request.json
    org_id = get_current_organisation_id()
    user_id = get_current_user_id()

    iar = ReceivingService.create_inspection_report(
        org_id=org_id,
        grn_id=data.get('grn_id'),
        inspector_id=user_id,
        status=data.get('status'),
        comments=data.get('remarks'),
    )
    return (
        jsonify({'message': 'Inspection Report created', 'iar_id': iar.id, 'iar_number': iar.iar_number}),
        201,
    )


@receiving_bp.route('/inspection-reports/items', methods=['POST'])
@require_role('procurement_officer', 'store_manager')
@limiter.limit("20 per minute")
def process_iar_items():
    data = request.json
    org_id = get_current_organisation_id()
    user_id = get_current_user_id()

    iar = ReceivingService.process_inspection_items(
        org_id=org_id,
        grn_id=data.get('grn_id'),
        inspector_id=user_id,
        items_data=data.get('items', []),
        comments=data.get('comments'),
    )
    return (
        jsonify({'message': 'Inspection processed', 'iar_id': iar.id, 'iar_number': iar.iar_number}),
        201,
    )


@receiving_bp.route('/goods-receipts/<int:id>/approve', methods=['PUT'])
@require_role('procurement_officer', 'store_manager')
@limiter.limit("20 per minute")
def approve_grn(id):
    grn = ReceivingService.approve_grn(id)
    return jsonify({'message': 'GRN approved and items moved to stock', 'grn_id': grn.id})


@receiving_bp.route('/goods-receipts/<int:id>/reject', methods=['PUT'])
@require_role('procurement_officer', 'store_manager')
@limiter.limit("20 per minute")
def reject_grn(id):
    grn = ReceivingService.reject_grn(id)
    return jsonify({'message': 'GRN rejected', 'grn_id': grn.id})


@receiving_bp.route('/warehouses', methods=['GET'])
@jwt_required_with_user
@limiter.limit("100 per minute")
def list_warehouses():
    """List all active warehouses for the organization for warehouse selection during GRN creation"""
    from app.models.location_topology import Warehouse
    
    org_id = get_current_organisation_id()
    
    warehouses = Warehouse.query.filter_by(
        organisation_id=org_id,
        is_active=True
    ).order_by(Warehouse.name.asc()).all()
    
    warehouse_list = [
        {
            'id': w.id,
            'name': w.name,
            'code': w.code,
            'type': w.warehouse_type,
            'is_main': w.is_main_warehouse,
            'address': w.address,
            'hierarchy_level': w.hierarchy_level,
        }
        for w in warehouses
    ]
    
    return jsonify({
        'success': True,
        'warehouses': warehouse_list,
        'total': len(warehouse_list)
    })
