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

    required = ['item_id', 'from_warehouse_id', 'to_department_id', 'employee_id', 'quantity']
    for r in required:
        if r not in data:
            raise ValidationError(f"Missing required field: {r}")

    issue = ItemIssueService.issue_item(
        org_id=org_id,
        item_id=int(data['item_id']),
        from_warehouse_id=int(data['from_warehouse_id']),
        to_department_id=int(data['to_department_id']),
        employee_id=int(data['employee_id']),
        quantity=int(data['quantity']),
        issued_by=get_current_user_id(),
        reference=data.get('reference'),
        notes=data.get('notes')
    )

    return jsonify({'message': 'Item issued', 'issue_id': issue.id}), 201


@movements_bp.route('/return', methods=['POST'])
@require_permission('movements:return')
@limiter.limit('30 per minute')
def return_item():
    org_id = get_current_organisation_id()
    data = request.get_json() or {}

    required = ['item_id', 'from_department_id', 'to_warehouse_id', 'employee_id', 'quantity']
    for r in required:
        if r not in data:
            raise ValidationError(f"Missing required field: {r}")

    ret = ItemReturnService.return_item(
        org_id=org_id,
        item_id=int(data['item_id']),
        from_department_id=int(data['from_department_id']),
        to_warehouse_id=int(data['to_warehouse_id']),
        employee_id=int(data['employee_id']),
        quantity=int(data['quantity']),
        returned_by=get_current_user_id(),
        condition=data.get('condition', 'good'),
        remarks=data.get('remarks'),
        reference=data.get('reference')
    )

    return jsonify({'message': 'Item returned', 'return_id': ret.id}), 201


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

    # Restrict view for non-admin/store_manager to relevant records
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
            'item_id': r.item_id,
            'from_department_id': r.from_department_id,
            'to_warehouse_id': r.to_warehouse_id,
            'employee_id': r.employee_id,
            'quantity': r.quantity,
            'condition': r.condition,
            'remarks': r.remarks,
            'return_date': r.return_date.isoformat() if r.return_date else None,
            'returned_by': r.returned_by,
            'reference': r.reference,
        }
        for r in pagination.items
    ]
    return jsonify({'returns': result, 'pagination': {'page': pagination.page, 'per_page': pagination.per_page, 'total': pagination.total}}), 200
