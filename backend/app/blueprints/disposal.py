from flask import Blueprint, request, jsonify
from app.auth_utils import jwt_required_with_user, get_current_organisation_id, get_current_user_id, require_role, require_permission
from app.services.disposal_service import DisposalService

disposal_bp = Blueprint('disposal_bp', __name__)

@disposal_bp.route('/disposal-requests', methods=['POST'])
@require_permission('disposal:create')
def create_disposal():
    data = request.json
    org_id = get_current_organisation_id()
    user_id = get_current_user_id()
    
    try:
        disp = DisposalService.create_disposal_request(
            org_id=org_id,
            requester_id=user_id,
            items_data=data.get('items', [])
        )
        return jsonify({'message': 'Disposal request created', 'disp_id': disp.id, 'disp_number': disp.disposal_number}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@disposal_bp.route('/disposal-requests/<int:id>/approve', methods=['PUT'])
@require_role('admin', 'superadmin')
def approve_disposal(id):
    data = request.json or {}
    user_id = get_current_user_id()
    is_finance_board = data.get('is_finance_board', False)
    
    try:
        disp = DisposalService.approve_disposal(
            disp_id=id,
            approver_id=user_id,
            is_finance_board=is_finance_board
        )
        return jsonify({'message': 'Disposal approved', 'disp_id': disp.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@disposal_bp.route('/disposal-requests/<int:id>/execute', methods=['PUT'])
@require_role('admin', 'superadmin')
def execute_disposal(id):
    try:
        user_id = get_current_user_id()
        disp = DisposalService.execute_disposal(id, executed_by_id=user_id)
        return jsonify({'message': 'Disposal executed', 'disp_id': disp.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
