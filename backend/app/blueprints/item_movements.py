from flask import Blueprint, request, jsonify, g
from app.auth_utils import jwt_required_with_user, require_role, require_permission, get_current_organisation_id, get_current_user_id
from app import limiter, db
from app.services.item_issue_service import ItemIssueService
from app.services.item_return_service import ItemReturnService
from app.errors import ValidationError

movements_bp = Blueprint('movements', __name__)

# Backwards-compatible export name expected by app factory
item_movements_bp = movements_bp


@movements_bp.route('/issue', methods=['POST'])
@require_permission('movements:issue')
@limiter.limit('30 per minute')
def issue_item():
    org_id = get_current_organisation_id()
    data = request.get_json() or {}

    item_type = (data.get('item_type') or 'inventory').lower()
    if item_type == 'asset':
        required = ['asset_id', 'from_warehouse_id', 'to_department_id', 'employee_id', 'quantity']
    else:
        required = ['item_id', 'from_warehouse_id', 'to_department_id', 'employee_id', 'quantity']

    for r in required:
        if r not in data:
            raise ValidationError(f"Missing required field: {r}")

    issue = ItemIssueService.issue_item(
        org_id=org_id,
        item_id=int(data['item_id']) if data.get('item_id') is not None else None,
        asset_id=int(data['asset_id']) if data.get('asset_id') is not None else None,
        from_warehouse_id=int(data['from_warehouse_id']),
        to_department_id=int(data['to_department_id']),
        employee_id=int(data['employee_id']),
        quantity=int(data['quantity']),
        issued_by=get_current_user_id(),
        reference=data.get('reference'),
        notes=data.get('notes'),
        item_type=item_type
    )

    return jsonify({'message': 'Item issued', 'issue_id': issue.id, 'item_type': issue.item_type}), 201


@movements_bp.route('/return', methods=['POST'])
@require_permission('movements:return')
@limiter.limit('30 per minute')
def return_item():
    org_id = get_current_organisation_id()
    data = request.get_json() or {}

    item_type = (data.get('item_type') or 'inventory').lower()
    if item_type == 'asset':
        required = ['asset_id', 'from_department_id', 'to_warehouse_id', 'employee_id', 'quantity']
    else:
        required = ['item_id', 'from_department_id', 'to_warehouse_id', 'employee_id', 'quantity']

    for r in required:
        if r not in data:
            raise ValidationError(f"Missing required field: {r}")

    ret = ItemReturnService.return_item(
        org_id=org_id,
        item_id=int(data['item_id']) if data.get('item_id') is not None else None,
        asset_id=int(data['asset_id']) if data.get('asset_id') is not None else None,
        from_department_id=int(data['from_department_id']),
        to_warehouse_id=int(data['to_warehouse_id']),
        employee_id=int(data['employee_id']),
        quantity=int(data['quantity']),
        returned_by=get_current_user_id(),
        condition=data.get('condition', 'good'),
        remarks=data.get('remarks'),
        reference=data.get('reference'),
        item_type=item_type
    )

    return jsonify({'message': 'Item returned', 'return_id': ret.id, 'item_type': ret.item_type}), 201


@movements_bp.route('/issues', methods=['GET'])
@require_role('admin', 'store_manager', 'staff', 'dept_head')
@limiter.limit('100 per minute')
def list_issues():
    org_id = get_current_organisation_id()
    # Simple listing for now
    from app.models.organization import ItemIssue
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = ItemIssue.query.filter_by(organisation_id=org_id)

    # Restrict view for non-admin/store_manager to relevant records
    if g.user.role not in ('admin', 'store_manager'):
        headed_dept_ids = [d.id for d in getattr(g.user, 'headed_departments', [])]
        query = query.filter(
            db.or_(
                ItemIssue.issued_by == g.user.id,
                ItemIssue.to_department_id.in_(headed_dept_ids),
            )
        )

    pagination = query.order_by(ItemIssue.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    result = [
        {
            'id': i.id,
            'item_id': i.item_id,
            'from_warehouse_id': i.from_warehouse_id,
            'to_department_id': i.to_department_id,
            'employee_id': i.employee_id,
            'quantity': i.quantity,
            'issued_date': i.issued_date.isoformat() if i.issued_date else None,
            'issued_by': i.issued_by,
            'reference': i.reference,
        }
        for i in pagination.items
    ]
    return jsonify({'issues': result, 'pagination': {'page': pagination.page, 'per_page': pagination.per_page, 'total': pagination.total}}), 200


@movements_bp.route('/returns', methods=['GET'])
@require_role('admin', 'store_manager', 'staff', 'dept_head')
@limiter.limit('100 per minute')
def list_returns():
    org_id = get_current_organisation_id()
    from app.models.organization import ItemReturn
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = ItemReturn.query.filter_by(organisation_id=org_id)

    if g.user.role not in ('admin', 'store_manager'):
        headed_dept_ids = [d.id for d in getattr(g.user, 'headed_departments', [])]
        query = query.filter(
            db.or_(
                ItemReturn.returned_by == g.user.id,
                ItemReturn.from_department_id.in_(headed_dept_ids),
            )
        )

    pagination = query.order_by(ItemReturn.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    result = [
        {
            'id': r.id,
            'item_type': r.item_type,
            'item_id': r.item_id,
            'asset_id': r.asset_id,
            'item_name': getattr(r.item, 'name', None) if r.item_type == 'inventory' and getattr(r, 'item', None) else getattr(r.asset, 'name', None) if r.item_type == 'asset' and getattr(r, 'asset', None) else None,
            'from_department_id': r.from_department_id,
            'from_department_name': r.from_department.name if getattr(r, 'from_department', None) else None,
            'to_warehouse_id': r.to_warehouse_id,
            'to_warehouse_name': r.to_warehouse.name if getattr(r, 'to_warehouse', None) else None,
            'employee_id': r.employee_id,
            'employee_name': r.employee.name if getattr(r, 'employee', None) else None,
            'quantity': r.quantity,
            'condition': r.condition,
            'remarks': r.remarks,
            'return_date': r.return_date.isoformat() if r.return_date else None,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'returned_by': r.returned_by,
            'returned_by_name': r.returned_by_user.username if getattr(r, 'returned_by_user', None) else None,
            'reference': r.reference,
        }
        for r in pagination.items
    ]
    return jsonify({'returns': result, 'pagination': {'page': pagination.page, 'per_page': pagination.per_page, 'total': pagination.total}}), 200


@movements_bp.route('/history', methods=['GET'])
@require_role('admin', 'store_manager', 'staff', 'dept_head')
@limiter.limit('100 per minute')
def movement_history():
    org_id = get_current_organisation_id()
    from app.models.organization import ItemIssue, ItemReturn

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    department_id = request.args.get('department_id', type=int)

    issue_query = ItemIssue.query.filter_by(organisation_id=org_id)
    return_query = ItemReturn.query.filter_by(organisation_id=org_id)

    if g.user.role not in ('admin', 'store_manager'):
        headed_dept_ids = [d.id for d in getattr(g.user, 'headed_departments', [])]
        issue_query = issue_query.filter(
            db.or_(
                ItemIssue.issued_by == g.user.id,
                ItemIssue.to_department_id.in_(headed_dept_ids),
            )
        )
        return_query = return_query.filter(
            db.or_(
                ItemReturn.returned_by == g.user.id,
                ItemReturn.from_department_id.in_(headed_dept_ids),
            )
        )

    if department_id:
        issue_query = issue_query.filter(ItemIssue.to_department_id == department_id)
        return_query = return_query.filter(ItemReturn.from_department_id == department_id)

    issues = issue_query.order_by(ItemIssue.created_at.desc()).all()
    returns = return_query.order_by(ItemReturn.created_at.desc()).all()

    issue_rows = []
    for record in issues:
        issue_rows.append({
            'id': record.id,
            'movement_type': 'issue',
            'item_type': record.item_type,
            'item_id': record.item_id,
            'asset_id': record.asset_id,
            'item_name': getattr(record.item, 'name', None) if record.item_type == 'inventory' and getattr(record, 'item', None) else getattr(record.asset, 'name', None) if record.item_type == 'asset' and getattr(record, 'asset', None) else None,
            'from_warehouse_id': record.from_warehouse_id,
            'from_warehouse_name': record.from_warehouse.name if getattr(record, 'from_warehouse', None) else None,
            'to_department_id': record.to_department_id,
            'to_department_name': record.to_department.name if getattr(record, 'to_department', None) else None,
            'employee_id': record.employee_id,
            'employee_name': record.employee.name if getattr(record, 'employee', None) else None,
            'quantity': record.quantity,
            'reference': record.reference,
            'notes': record.notes,
            'performed_by': record.issued_by_user.username if getattr(record, 'issued_by_user', None) else None,
            'issued_date': record.issued_date.isoformat() if record.issued_date else None,
            'created_at': record.created_at.isoformat() if record.created_at else None,
        })

    return_rows = []
    for record in returns:
        return_rows.append({
            'id': record.id,
            'movement_type': 'return',
            'item_type': record.item_type,
            'item_id': record.item_id,
            'asset_id': record.asset_id,
            'item_name': getattr(record.item, 'name', None) if record.item_type == 'inventory' and getattr(record, 'item', None) else getattr(record.asset, 'name', None) if record.item_type == 'asset' and getattr(record, 'asset', None) else None,
            'from_department_id': record.from_department_id,
            'from_department_name': record.from_department.name if getattr(record, 'from_department', None) else None,
            'to_warehouse_id': record.to_warehouse_id,
            'to_warehouse_name': record.to_warehouse.name if getattr(record, 'to_warehouse', None) else None,
            'employee_id': record.employee_id,
            'employee_name': record.employee.name if getattr(record, 'employee', None) else None,
            'quantity': record.quantity,
            'reference': record.reference,
            'notes': record.remarks,
            'performed_by': record.returned_by_user.username if getattr(record, 'returned_by_user', None) else None,
            'return_date': record.return_date.isoformat() if record.return_date else None,
            'created_at': record.created_at.isoformat() if record.created_at else None,
            'condition': record.condition,
        })

    history = sorted(issue_rows + return_rows, key=lambda row: row.get('created_at') or row.get('issued_date') or row.get('return_date') or '', reverse=True)
    return jsonify({
        'issues': issue_rows,
        'returns': return_rows,
        'history': history,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_issues': len(issue_rows),
            'total_returns': len(return_rows),
            'total': len(history),
        },
    }), 200
