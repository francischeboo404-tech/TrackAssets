"""
Employee Service - Manages employee CRUD and lookups
"""
from app import db
from app.models.organization import Department, Employee
from app.errors import NotFoundError, ConflictError, ValidationError
from app.db_utils import transaction_retry
from flask import current_app
from app.services.event_bus import event_bus


class EmployeeService:
    @staticmethod
    @transaction_retry(max_retries=3)
    def create_employee(org_id: int, department_id: int, data: dict) -> Employee:
        # Validate department exists (caller ensures scope)
        # Minimal validation: unique code per org
        existing = Employee.query.filter_by(organisation_id=org_id, code=data.get('code')).first()
        if existing:
            raise ConflictError(f"Employee code '{data.get('code')}' already exists")

        emp = Employee(
            organisation_id=org_id,
            department_id=department_id,
            name=data.get('name'),
            code=data.get('code'),
            email=data.get('email'),
            phone=data.get('phone'),
            date_of_join=data.get('date_of_join'),
            employee_type=data.get('employee_type', 'regular'),
            manager_id=data.get('manager_id')
        )
        db.session.add(emp)
        db.session.commit()

        current_app.logger.info(f"Employee created: {emp.code}", extra={'emp_id': emp.id, 'org_id': org_id})
        event_bus.publish('EMPLOYEE_CREATED', {'employee_id': emp.id, 'org_id': org_id})
        return emp

    @staticmethod
    def get_employee(emp_id: int, org_id: int) -> Employee:
        emp = Employee.query.filter_by(id=emp_id, organisation_id=org_id).first()
        if not emp:
            raise NotFoundError("Employee not found")
        return emp

    @staticmethod
    def list_employees(org_id: int, department_id: int=None, page: int=1, per_page: int=50, search: str=None, sort: str=None):
        q = Employee.query.filter_by(organisation_id=org_id, is_active=True)
        if department_id:
            q = q.filter_by(department_id=department_id)
        if search:
            term = f"%{search}%"
            from sqlalchemy import or_
            q = q.filter(or_(Employee.name.ilike(term), Employee.code.ilike(term), Employee.email.ilike(term)))
        # Sorting: allow simple field names and optional leading '-' for desc
        if sort:
            direction = 'asc'
            field = sort
            if sort.startswith('-'):
                direction = 'desc'
                field = sort[1:]
            # whitelist sortable fields
            allowed = {'name', 'code', 'date_of_join'}
            if field in allowed:
                col = getattr(Employee, field)
                if direction == 'desc':
                    col = col.desc()
                q = q.order_by(col)

        return q.paginate(page=page, per_page=per_page)

    @staticmethod
    @transaction_retry(max_retries=3)
    def update_employee(emp_id: int, org_id: int, data: dict) -> Employee:
        emp = EmployeeService.get_employee(emp_id, org_id)
        if 'department_id' in data:
            department = Department.query.filter_by(id=data['department_id'], organisation_id=org_id, is_active=True).first()
            if not department:
                raise ValidationError('Department not found or inactive')
            emp.department_id = data['department_id']

        for k in ['name','email','phone','employee_type','manager_id','is_active']:
            if k in data:
                setattr(emp, k, data[k])
        db.session.commit()
        event_bus.publish('EMPLOYEE_UPDATED', {'employee_id': emp.id, 'org_id': org_id})
        return emp

    @staticmethod
    @transaction_retry(max_retries=3)
    def delete_employee(emp_id: int, org_id: int) -> dict:
        emp = EmployeeService.get_employee(emp_id, org_id)
        emp.is_active = False
        db.session.commit()
        event_bus.publish('EMPLOYEE_DELETED', {'employee_id': emp.id, 'org_id': org_id})
        return {'status': 'deleted', 'employee_id': emp.id}
