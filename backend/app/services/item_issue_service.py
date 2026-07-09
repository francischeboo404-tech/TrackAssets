"""
Item Issue Service - Issues items from warehouse to a department/employee
"""
from app import db
from flask import current_app
from app.errors import NotFoundError, ValidationError, ConflictError
from app.models.organization import ItemIssue, Department, Employee
from app.models.inventory import InventoryItem
from app.models.asset import Asset
from app.db_utils import transaction_retry
from app.services.stock_service import StockService
from app.services.event_bus import event_bus
from app.audit_service import AuditService
from datetime import datetime


class ItemIssueService:
    @staticmethod
    @transaction_retry(max_retries=3)
    def issue_item(org_id: int, item_id: int = None, asset_id: int = None, from_warehouse_id: int = None, to_department_id: int = None, employee_id: int = None, quantity: int = 1, issued_by: int = None, reference: str = None, notes: str = None, item_type: str = 'inventory'):
        if item_type not in {'inventory', 'asset'}:
            raise ValidationError("Unsupported movement type")

        if not from_warehouse_id or not to_department_id or not employee_id or not issued_by:
            raise ValidationError("Missing movement routing details")

        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero")

        from app.models.location_topology import Warehouse
        warehouse = Warehouse.query.filter_by(id=from_warehouse_id, organisation_id=org_id, is_active=True).first()
        if not warehouse:
            raise NotFoundError("Source warehouse not found")

        department = Department.query.filter_by(id=to_department_id, organisation_id=org_id, is_active=True).first()
        if not department:
            raise NotFoundError("Destination department not found")

        if department.warehouse_id and department.warehouse_id != from_warehouse_id:
            raise ValidationError("Department does not belong to the specified warehouse")

        employee = Employee.query.filter_by(id=employee_id, organisation_id=org_id, department_id=to_department_id, is_active=True).first()
        if not employee:
            raise NotFoundError("Employee not found in the specified department")

        issue = ItemIssue(
            organisation_id=org_id,
            item_id=item_id,
            asset_id=asset_id,
            item_type=item_type,
            from_warehouse_id=from_warehouse_id,
            to_department_id=to_department_id,
            employee_id=employee_id,
            quantity=quantity,
            reference=reference,
            notes=notes,
            issued_by=issued_by,
            issued_date=datetime.utcnow()
        )

        try:
            if item_type == 'inventory':
                if not item_id:
                    raise ValidationError("Inventory item id is required")
                item = InventoryItem.query.filter_by(id=item_id, organisation_id=org_id, is_active=True).first()
                if not item:
                    raise NotFoundError("Inventory item not found")
                stock_service = StockService(session=db.session)
                try:
                    stock_service.decrease_stock(item_id, org_id, quantity, warehouse_id=from_warehouse_id, reference=reference, notes=notes, user_id=issued_by, commit=False)
                except Exception as exc:
                    db.session.rollback()
                    raise ValidationError("Unable to update inventory stock for the issue request.") from exc
                entity_type = 'inventory_item'
                entity_id = item_id
            else:
                if not asset_id:
                    raise ValidationError("Asset id is required")
                asset = Asset.query.filter_by(id=asset_id, organisation_id=org_id).first()
                if not asset:
                    raise NotFoundError("Asset not found")
                if asset.status != 'available':
                    raise ValidationError("Asset is not available for issue")
                asset.status = 'assigned'
                asset.assigned_to = employee.name
                asset.assigned_to_user_id = None
                asset.assigned_department_id = department.id
                asset.assignment_date = datetime.utcnow().date()
                asset.return_date = None
                asset.updated_at = datetime.utcnow()
                entity_type = 'asset'
                entity_id = asset_id

            db.session.add(issue)

            AuditService.log_action(
                action="ITEM_ISSUED",
                entity_type=entity_type,
                entity_id=entity_id,
                details={
                    'item_type': item_type,
                    'item_id': item_id,
                    'asset_id': asset_id,
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

            db.session.commit()
            event_bus.publish('ITEM_ISSUED', {'issue_id': issue.id, 'org_id': org_id, 'item_type': item_type})
            return issue
        except ValidationError:
            db.session.rollback()
            raise
        except NotFoundError:
            db.session.rollback()
            raise
        except Exception as exc:
            db.session.rollback()
            raise ValidationError("Unable to complete the movement request. Please try again later.") from exc
