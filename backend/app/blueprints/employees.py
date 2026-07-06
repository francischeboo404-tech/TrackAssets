from flask import Blueprint, request, jsonify
from app.auth_utils import jwt_required_with_user, require_role, get_current_organisation_id
from app.services.employee_service import EmployeeService
from app.errors import ValidationError, NotFoundError
from app import limiter

employees_bp = Blueprint('employees', __name__)


@employees_bp.route('', methods=['GET'])
@jwt_required_with_user
@limiter.limit('100 per minute')
def list_employees():
    org_id = get_current_organisation_id()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    department_id = request.args.get('department_id', type=int)
    search = request.args.get('q', type=str)
    sort = request.args.get('sort', type=str)

    pagination = EmployeeService.list_employees(org_id, department_id=department_id, page=page, per_page=per_page, search=search, sort=sort)
    result = [
        {
            'id': e.id,
            'name': e.name,
            'code': e.code,
            'email': e.email,
            'phone': e.phone,
            'department_id': e.department_id,
            'department_name': getattr(e.department, 'name', None),
            'date_of_join': e.date_of_join.isoformat() if e.date_of_join else None,
            'is_active': e.is_active,
        }
        for e in pagination.items
    ]

    return jsonify({'employees': result, 'pagination': {'page': pagination.page, 'per_page': pagination.per_page, 'total': pagination.total}}), 200


@employees_bp.route('/<int:emp_id>', methods=['GET'])
@jwt_required_with_user
@limiter.limit('200 per minute')
def get_employee(emp_id):
    org_id = get_current_organisation_id()
    emp = EmployeeService.get_employee(emp_id, org_id)
    return jsonify({
        'id': emp.id,
        'name': emp.name,
        'code': emp.code,
        'email': emp.email,
        'phone': emp.phone,
        'department_id': emp.department_id,
        'department_name': getattr(emp.department, 'name', None),
        'date_of_join': emp.date_of_join.isoformat() if emp.date_of_join else None,
        'is_active': emp.is_active,
    }), 200


@employees_bp.route('', methods=['POST'])
@require_role('admin')
@limiter.limit('20 per minute')
def create_employee():
    org_id = get_current_organisation_id()
    data = request.get_json() or {}
    required = ['name', 'code', 'department_id']
    for r in required:
        if r not in data:
            raise ValidationError(f"Missing required field: {r}")

    emp = EmployeeService.create_employee(org_id, data.get('department_id'), data)
    return jsonify({'message': 'Employee created', 'employee_id': emp.id}), 201


@employees_bp.route('/<int:emp_id>', methods=['PUT'])
@require_role('admin')
@limiter.limit('30 per minute')
def update_employee(emp_id):
    org_id = get_current_organisation_id()
    data = request.get_json() or {}
    emp = EmployeeService.update_employee(emp_id, org_id, data)
    return jsonify({'message': 'Employee updated', 'employee_id': emp.id}), 200


@employees_bp.route('/<int:emp_id>', methods=['DELETE'])
@require_role('admin')
@limiter.limit('10 per minute')
def delete_employee(emp_id):
    org_id = get_current_organisation_id()
    res = EmployeeService.delete_employee(emp_id, org_id)
    return jsonify(res), 200
