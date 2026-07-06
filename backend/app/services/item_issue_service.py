"""
Item Issue Service - Issues items from warehouse to a department/employee
"""
from app import db
from flask import current_app
from app.errors import NotFoundError, ValidationError, ConflictError
from app.models.organization import ItemIssue, Department, Employee
from app.models.inventory import InventoryItem
from app.db_utils import transaction_retry
from app.services.stock_service import StockService
from app.services.event_bus import event_bus
from app.audit_service import AuditService
from datetime import datetime


class ItemIssueService:
    @staticmethod
    @transaction_retry(max_retries=3)
    def issue_item(org_id: int, item_id: int, from_warehouse_id: int, to_department_id: int, employee_id: int, quantity: int, issued_by: int, reference: str=None, notes: str=None):
        # Validate item
        item = InventoryItem.query.filter_by(id=item_id, organisation_id=org_id, is_active=True).first()
        if not item:
            raise NotFoundError("Inventory item not found")

        # Validate warehouse
        from app.models.location_topology import Warehouse
        warehouse = Warehouse.query.filter_by(id=from_warehouse_id, organisation_id=org_id, is_active=True).first()
        if not warehouse:
            raise NotFoundError("Source warehouse not found")

        # Validate department
        department = Department.query.filter_by(id=to_department_id, organisation_id=org_id, is_active=True).first()
        if not department:
            raise NotFoundError("Destination department not found")

        # Ensure department belongs to the warehouse
        if department.warehouse_id and department.warehouse_id != from_warehouse_id:
            raise ValidationError("Department does not belong to the specified warehouse")

        # Validate employee
        employee = Employee.query.filter_by(id=employee_id, organisation_id=org_id, department_id=to_department_id, is_active=True).first()
        if not employee:
            raise NotFoundError("Employee not found in the specified department")

        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero")

        # Use StockService to decrease stock from warehouse
        stock_service = StockService(session=db.session)
        try:
            stock_service.decrease_stock(item_id, org_id, quantity, warehouse_id=from_warehouse_id, reference=reference, notes=notes, user_id=issued_by, commit=False)
        except Exception as e:
            db.session.rollback()
            raise

        # Create issue record
        issue = ItemIssue(
            organisation_id=org_id,
            item_id=item_id,
            from_warehouse_id=from_warehouse_id,
            to_department_id=to_department_id,
            employee_id=employee_id,
            quantity=quantity,
            reference=reference,
            notes=notes,
            issued_by=issued_by,
            issued_date=datetime.utcnow()
        )
        db.session.add(issue)

        # Audit action
        AuditService.log_action(
            action="ITEM_ISSUED",
            entity_type="inventory_item",
            entity_id=item_id,
            details={
                'quantity': quantity,
                'from_warehouse_id': from_warehouse_id,
                'to_department_id': to_department_id,
                'employee_id': employee_id,
                'reference': reference,
                'notes': notes
            },
            user_id=issued_by,
            organisation_id=org_id,
            session=db.session
        )

        # Commit (StockService decrease was called with commit=False)
        db.session.commit()
        event_bus.publish('ITEM_ISSUED', {'issue_id': issue.id, 'org_id': org_id})
        return issue
