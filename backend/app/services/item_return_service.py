"""
Item Return Service - Handles returns from employees back to warehouse
"""
from app import db
from datetime import datetime
from app.errors import NotFoundError, ValidationError
from app.models.organization import ItemReturn, Department, Employee
from app.models.inventory import InventoryItem
from app.models.asset import Asset
from app.db_utils import transaction_retry
from app.services.stock_service import StockService
from app.services.event_bus import event_bus
from app.audit_service import AuditService


class ItemReturnService:
    @staticmethod
    @transaction_retry(max_retries=3)
    def return_item(org_id: int, item_id: int = None, asset_id: int = None, from_department_id: int = None, to_warehouse_id: int = None, employee_id: int = None, quantity: int = 1, returned_by: int = None, condition: str = 'good', remarks: str = None, reference: str = None, item_type: str = 'inventory'):
        if item_type not in {'inventory', 'asset'}:
            raise ValidationError("Unsupported movement type")

        if not from_department_id or not to_warehouse_id or not employee_id or not returned_by:
            raise ValidationError("Missing movement routing details")

        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero")

        try:
            department = Department.query.filter_by(id=from_department_id, organisation_id=org_id, is_active=True).first()
            if not department:
                raise NotFoundError("Source department not found")

            from app.models.location_topology import Warehouse
            warehouse = Warehouse.query.filter_by(id=to_warehouse_id, organisation_id=org_id, is_active=True).first()
            if not warehouse:
                raise NotFoundError("Destination warehouse not found")

            employee = Employee.query.filter_by(id=employee_id, organisation_id=org_id, department_id=from_department_id, is_active=True).first()
            if not employee:
                raise NotFoundError("Employee not found in the specified department")
        except ValidationError:
            raise
        except NotFoundError:
            raise
        except Exception as exc:
            raise ValidationError("Unable to validate the return request at the moment.") from exc

        ret = ItemReturn(
            organisation_id=org_id,
            item_id=item_id,
            asset_id=asset_id,
            item_type=item_type,
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

        try:
            if item_type == 'inventory':
                if not item_id:
                    raise ValidationError("Inventory item id is required")
                item = InventoryItem.query.filter_by(id=item_id, organisation_id=org_id, is_active=True).first()
                if not item:
                    raise NotFoundError("Inventory item not found")
                stock_service = StockService(session=db.session)
                try:
                    stock_service.increase_stock(item_id, org_id, quantity, warehouse_id=to_warehouse_id, reference=reference, notes=remarks, user_id=returned_by, commit=False)
                except Exception as exc:
                    db.session.rollback()
                    raise ValidationError("Unable to update inventory stock for the return request.") from exc
                entity_type = 'inventory_item'
                entity_id = item_id
            else:
                if not asset_id:
                    raise ValidationError("Asset id is required")
                asset = Asset.query.filter_by(id=asset_id, organisation_id=org_id).first()
                if not asset:
                    raise NotFoundError("Asset not found")
                if asset.status != 'assigned' or asset.assigned_department_id != from_department_id:
                    raise ValidationError("Asset is not currently assigned to the selected department")
                asset.status = 'available'
                asset.assigned_to = None
                asset.assigned_to_user_id = None
                asset.assigned_department_id = None
                asset.assignment_date = None
                asset.return_date = None
                asset.actual_return_date = datetime.utcnow().date()
                asset.updated_at = datetime.utcnow()
                entity_type = 'asset'
                entity_id = asset_id

            db.session.add(ret)

            AuditService.log_action(
                action="ITEM_RETURNED",
                entity_type=entity_type,
                entity_id=entity_id,
                details={
                    'item_type': item_type,
                    'item_id': item_id,
                    'asset_id': asset_id,
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
            event_bus.publish('ITEM_RETURNED', {'return_id': ret.id, 'org_id': org_id, 'item_type': item_type})
            return ret
        except ValidationError:
            db.session.rollback()
            raise
        except NotFoundError:
            db.session.rollback()
            raise
        except Exception as exc:
            db.session.rollback()
            raise ValidationError("Unable to complete the return operation. Please try again later.") from exc
