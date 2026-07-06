"""
Item Return Service - Handles returns from employees back to warehouse
"""
from app import db
from datetime import datetime
from app.errors import NotFoundError, ValidationError
from app.models.organization import ItemReturn, Department, Employee
from app.models.inventory import InventoryItem
from app.db_utils import transaction_retry
from app.services.stock_service import StockService
from app.services.event_bus import event_bus
from app.audit_service import AuditService


class ItemReturnService:
    @staticmethod
    @transaction_retry(max_retries=3)
    def return_item(org_id: int, item_id: int, from_department_id: int, to_warehouse_id: int, employee_id: int, quantity: int, returned_by: int, condition: str='good', remarks: str=None, reference: str=None):
        # Validate item
        item = InventoryItem.query.filter_by(id=item_id, organisation_id=org_id, is_active=True).first()
        if not item:
            raise NotFoundError("Inventory item not found")

        # Validate department
        department = Department.query.filter_by(id=from_department_id, organisation_id=org_id, is_active=True).first()
        if not department:
            raise NotFoundError("Source department not found")

        # Validate warehouse exists
        from app.models.location_topology import Warehouse
        warehouse = Warehouse.query.filter_by(id=to_warehouse_id, organisation_id=org_id, is_active=True).first()
        if not warehouse:
            raise NotFoundError("Destination warehouse not found")

        # Validate employee
        employee = Employee.query.filter_by(id=employee_id, organisation_id=org_id, department_id=from_department_id, is_active=True).first()
        if not employee:
            raise NotFoundError("Employee not found in the specified department")

        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero")

        # Use StockService to increase stock into warehouse
        stock_service = StockService(session=db.session)
        try:
            stock_service.increase_stock(item_id, org_id, quantity, warehouse_id=to_warehouse_id, reference=reference, notes=remarks, user_id=returned_by, commit=False)
        except Exception as e:
            db.session.rollback()
            raise

        # Create return record
        ret = ItemReturn(
            organisation_id=org_id,
            item_id=item_id,
            from_department_id=from_department_id,
            to_warehouse_id=to_warehouse_id,
            employee_id=employee_id,
            quantity=quantity,
            condition=condition,
            remarks=remarks,
            reference=reference,
            returned_by=returned_by,
            return_date=datetime.utcnow()
        )
        db.session.add(ret)

        # Audit
        AuditService.log_action(
            action="ITEM_RETURNED",
            entity_type="inventory_item",
            entity_id=item_id,
            details={
                'quantity': quantity,
                'from_department_id': from_department_id,
                'to_warehouse_id': to_warehouse_id,
                'employee_id': employee_id,
                'condition': condition,
                'remarks': remarks,
                'reference': reference
            },
            user_id=returned_by,
            organisation_id=org_id,
            session=db.session
        )

        db.session.commit()
        event_bus.publish('ITEM_RETURNED', {'return_id': ret.id, 'org_id': org_id})
        return ret
