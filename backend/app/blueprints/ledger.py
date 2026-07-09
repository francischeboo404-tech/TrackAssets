from flask import Blueprint, request, jsonify
from app import limiter
from app.auth_utils import jwt_required_with_user, get_current_organisation_id, get_current_user_id, require_permission
from app.services.ledger_service import LedgerService

ledger_bp = Blueprint('ledger_bp', __name__)


@ledger_bp.route('/variance-reports', methods=['POST'])
@require_permission('variance:create')
@limiter.limit("20 per minute")
def create_variance_report():
    data = request.json
    org_id = get_current_organisation_id()
    
    try:
        var_rep = LedgerService.create_variance_report(
            org_id=org_id,
            item_id=data.get('item_id'),
            location_id=data.get('location_id'),
            physical_quantity=data.get('physical_quantity'),
            reason=data.get('reason')
        )
        return jsonify({'message': 'Variance report created', 'report_id': var_rep.id, 'report_number': var_rep.report_number}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@ledger_bp.route('/variance-reports/<int:id>/resolve', methods=['PUT'])
@require_permission('variance:resolve')
@limiter.limit("10 per minute")
def resolve_variance(id):
    user_id = get_current_user_id()
    try:
        var_rep = LedgerService.resolve_variance(id, resolved_by_id=user_id)
        return jsonify({'message': 'Variance resolved', 'report_id': var_rep.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
