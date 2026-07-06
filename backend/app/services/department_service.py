"""
Department Service - Manages department operations within warehouses

This service handles:
- CRUD operations for departments
- Department-warehouse relationships
- Department hierarchy and organization
"""

from app import db
from app.models.organization import Department
from app.models.location_topology import Warehouse
from app.errors import NotFoundError, ConflictError, ValidationError
from app.db_utils import transaction_retry
from app.services.event_bus import event_bus
from flask import current_app


class DepartmentService:
    """Service for managing departments within warehouses"""

    @staticmethod
    @transaction_retry(max_retries=3)
    def create_department(org_id: int, warehouse_id: int, dept_data: dict) -> Department:
        """Create a new department within a warehouse
        
        Args:
            org_id: Organization ID
            warehouse_id: Warehouse ID where department belongs
            dept_data: Dictionary with name, code, description, etc.
            
        Returns:
            Created Department object
            
        Raises:
            NotFoundError: If warehouse not found
            ValidationError: If invalid data provided
            ConflictError: If department code already exists
        """
        # Validate warehouse exists
        warehouse = Warehouse.query.filter_by(
            id=warehouse_id,
            organisation_id=org_id,
            is_active=True
        ).first()
        
        if not warehouse:
            raise NotFoundError(f"Warehouse {warehouse_id} not found in your organization")
        
        # Check for duplicate department code
        existing = Department.query.filter_by(
            organisation_id=org_id,
            code=dept_data.get('code'),
            warehouse_id=warehouse_id
        ).first()
        
        if existing:
            raise ConflictError(
                f"Department with code '{dept_data.get('code')}' already exists "
                f"in {warehouse.name}"
            )
        
        department = Department(
            organisation_id=org_id,
            warehouse_id=warehouse_id,
            name=dept_data.get('name'),
            code=dept_data.get('code'),
            description=dept_data.get('description'),
            head_id=dept_data.get('head_id')
        )
        
        db.session.add(department)
        db.session.commit()
        
        current_app.logger.info(
            f"Department created: {department.code}",
            extra={"org_id": org_id, "warehouse_id": warehouse_id, "dept_id": department.id}
        )
        
        event_bus.publish('DEPARTMENT_CREATED', {
            'department_id': department.id,
            'warehouse_id': warehouse_id,
            'org_id': org_id,
            'name': department.name
        })
        
        return department

    @staticmethod
    def get_department(dept_id: int, org_id: int) -> Department:
        """Get a department by ID
        
        Args:
            dept_id: Department ID
            org_id: Organization ID (for scope)
            
        Returns:
            Department object
            
        Raises:
            NotFoundError: If department not found
        """
        department = Department.query.filter_by(
            id=dept_id,
            organisation_id=org_id
        ).first()
        
        if not department:
            raise NotFoundError(f"Department {dept_id} not found")
        
        return department

    @staticmethod
    def list_departments(org_id: int, warehouse_id: int = None, page: int = 1, per_page: int = 50):
        """List departments in an organization or warehouse
        
        Args:
            org_id: Organization ID
            warehouse_id: Optional warehouse ID to filter by
            page: Page number for pagination
            per_page: Items per page
            
        Returns:
            Paginated list of departments
        """
        query = Department.query.filter_by(
            organisation_id=org_id,
            is_active=True
        )
        
        if warehouse_id:
            query = query.filter_by(warehouse_id=warehouse_id)
        
        return query.paginate(page=page, per_page=per_page)

    @staticmethod
    @transaction_retry(max_retries=3)
    def update_department(dept_id: int, org_id: int, dept_data: dict) -> Department:
        """Update a department
        
        Args:
            dept_id: Department ID
            org_id: Organization ID
            dept_data: Dictionary with fields to update
            
        Returns:
            Updated Department object
            
        Raises:
            NotFoundError: If department not found
            ValidationError: If invalid data provided
        """
        department = DepartmentService.get_department(dept_id, org_id)
        
        # Update allowed fields
        allowed_fields = ['name', 'description', 'head_id', 'allowed_category_ids',
                         'allowed_inventory_item_types', 'allowed_asset_types']
        
        for field in allowed_fields:
            if field in dept_data:
                setattr(department, field, dept_data[field])
        
        db.session.commit()
        
        current_app.logger.info(
            f"Department updated: {department.code}",
            extra={"dept_id": dept_id, "org_id": org_id}
        )
        
        event_bus.publish('DEPARTMENT_UPDATED', {
            'department_id': department.id,
            'org_id': org_id
        })
        
        return department

    @staticmethod
    @transaction_retry(max_retries=3)
    def delete_department(dept_id: int, org_id: int) -> dict:
        """Soft delete a department
        
        Args:
            dept_id: Department ID
            org_id: Organization ID
            
        Returns:
            Status dictionary
            
        Raises:
            NotFoundError: If department not found
            ConflictError: If department has active employees or items
        """
        department = DepartmentService.get_department(dept_id, org_id)
        
        # Check for active employees
        from app.models.organization import Employee
        active_employees = Employee.query.filter_by(
            department_id=dept_id,
            is_active=True
        ).first()
        
        if active_employees:
            raise ConflictError(
                "Cannot delete department with active employees. "
                "Please deactivate or reassign all employees first."
            )
        
        # Check for pending item issues
        from app.models.organization import ItemIssue
        pending_issues = ItemIssue.query.filter_by(
            to_department_id=dept_id,
            is_active=True
        ).first()
        
        if pending_issues:
            raise ConflictError(
                "Cannot delete department with pending item issues. "
                "Please close or resolve all issues first."
            )
        
        department.is_active = False
        db.session.commit()
        
        current_app.logger.info(
            f"Department deactivated: {department.code}",
            extra={"dept_id": dept_id, "org_id": org_id}
        )
        
        event_bus.publish('DEPARTMENT_DELETED', {
            'department_id': department.id,
            'org_id': org_id
        })
        
        return {'status': 'deleted', 'department_id': dept_id}

    @staticmethod
    def get_departments_by_warehouse(warehouse_id: int, org_id: int):
        """Get all departments for a warehouse
        
        Args:
            warehouse_id: Warehouse ID
            org_id: Organization ID
            
        Returns:
            List of departments
        """
        return Department.query.filter_by(
            warehouse_id=warehouse_id,
            organisation_id=org_id,
            is_active=True
        ).all()

    @staticmethod
    def move_department_to_warehouse(dept_id: int, org_id: int, new_warehouse_id: int) -> Department:
        """Move a department to a different warehouse
        
        Args:
            dept_id: Department ID
            org_id: Organization ID
            new_warehouse_id: New warehouse ID
            
        Returns:
            Updated Department object
            
        Raises:
            NotFoundError: If department or warehouse not found
            ConflictError: If department has active items issued
        """
        department = DepartmentService.get_department(dept_id, org_id)
        
        # Validate new warehouse
        warehouse = Warehouse.query.filter_by(
            id=new_warehouse_id,
            organisation_id=org_id,
            is_active=True
        ).first()
        
        if not warehouse:
            raise NotFoundError(f"Warehouse {new_warehouse_id} not found")
        
        # Check for active item issues
        from app.models.organization import ItemIssue
        active_issues = ItemIssue.query.filter_by(
            to_department_id=dept_id,
            is_active=True
        ).first()
        
        if active_issues:
            raise ConflictError(
                "Cannot move department with active item issues. "
                "Please close all issues first."
            )
        
        old_warehouse_id = department.warehouse_id
        department.warehouse_id = new_warehouse_id
        db.session.commit()
        
        current_app.logger.info(
            f"Department moved: {department.code}",
            extra={
                "dept_id": dept_id,
                "from_warehouse": old_warehouse_id,
                "to_warehouse": new_warehouse_id
            }
        )
        
        event_bus.publish('DEPARTMENT_MOVED', {
            'department_id': department.id,
            'from_warehouse_id': old_warehouse_id,
            'to_warehouse_id': new_warehouse_id,
            'org_id': org_id
        })
        
        return department
