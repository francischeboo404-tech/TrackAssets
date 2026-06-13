from app import db
from app.models import inventory
from app.audit_service import AuditService
from app.repositories.inventory_repository import InventoryRepository
from app.errors import NotFoundError, ConflictError, ValidationError
from app.db_utils import transaction_retry
from app.services.event_bus import event_bus
from app.services.qr_service import QRService
from flask import current_app


class InventoryService:
    """Service layer for inventory business logic.

    This service manages transaction boundaries and uses the repository for
    data access. It does not alter response shapes — controllers remain
    responsible for formatting responses.
    """

    def __init__(self, repository: InventoryRepository = None, session=None):
        self.repo = repository or InventoryRepository()
        self.session = session or db.session

    def list_items(
        self, org_id, page=1, per_page=50, search=None, low_stock_only=False
    ):
        return self.repo.list_items(
            org_id,
            page=page,
            per_page=per_page,
            search=search,
            low_stock_only=low_stock_only,
        )

    def get_item(self, item_id, org_id):
        item = self.repo.get_item(item_id, org_id)
        if not item:
            raise NotFoundError("Inventory item not found")
        movements = self.repo.get_recent_movements(item_id, org_id)
        return item, movements

    @transaction_retry(max_retries=3)
    def create_item(self, org_id, validated_data):
        current_app.logger.debug(
            "create_item called",
            extra={"org_id": org_id, "data_keys": list(validated_data.keys())},
        )

        # business validations (uniqueness)
        if self.repo.exists_sku(org_id, validated_data.get("sku")):
            current_app.logger.warning(
                "create_item: sku conflict",
                extra={"sku": validated_data.get("sku")},
            )
            raise ConflictError("SKU already exists")

        item = self.repo.create_item(
            org_id, validated_data, session=self.session
        )
        QRService.ensure_inventory_qr(item)
        # Audit log (added to same session)
        AuditService.log_inventory_change(
            item,
            "INVENTORY_ITEM_CREATED",
            reference="Initial creation",
            session=self.session,
        )
        try:
            self.session.commit()
        except Exception as e:
            current_app.logger.error(
                "create_item: commit failed", extra={"error": str(e)}
            )
            self.session.rollback()
            raise

        event_bus.publish("INVENTORY_CREATED", {"item_id": item.id, "sku": item.sku}, organisation_id=org_id)
        current_app.logger.info(
            "create_item: success",
            extra={"item_id": item.id, "sku": item.sku},
        )

        return item

    @transaction_retry(max_retries=3)
    def update_item(self, item_id, org_id, data):
        # Reload with lock
        item = (
            inventory.InventoryItem.query.with_for_update()
            .filter_by(id=item_id, organisation_id=org_id, is_active=True)
            .first()
        )
        if not item:
            raise NotFoundError("Inventory item not found")

        # Check SKU uniqueness if changing
        if "sku" in data and data["sku"] != item.sku:
            if self.repo.exists_sku(org_id, data["sku"]):
                raise ConflictError("SKU already exists")

        old_values = {
            k: getattr(item, k)
            for k in [
                "name",
                "sku",
                "description",
                "reorder_level",
                "unit_price",
                "unit",
            ]
        }

        if "quantity" in data:
            raise ValidationError(
                "Quantity cannot be edited directly; use stock movements"
            )

        if data.get("reorder_level") is not None and data["reorder_level"] < 0:
            raise ValidationError("Reorder level cannot be negative")
        if data.get("unit_price") is not None and data["unit_price"] < 0:
            raise ValidationError("Unit price cannot be negative")

        try:
            updatable_fields = {
                k: data[k]
                for k in [
                    "name",
                    "description",
                    "reorder_level",
                    "unit_price",
                    "unit",
                ]
                if k in data
            }
            self.repo.update_item(item, updatable_fields)
            if "sku" in data:
                item.sku = data["sku"]

            AuditService.log_action(
                action="INVENTORY_ITEM_UPDATED",
                entity_type="inventory_item",
                entity_id=item.id,
                details={
                    "old_values": old_values,
                    "new_values": {
                        k: getattr(item, k) for k in old_values.keys()
                    },
                },
                organisation_id=org_id,
                session=self.session,
            )
            self.session.commit()
            
            # Re-evaluate stock health in case thresholds or quantities were modified manually
            from app.services.restock_service import RestockService
            RestockService.evaluate_stock_health(item.id)
            
            event_bus.publish("INVENTORY_UPDATED", {"item_id": item.id}, organisation_id=org_id)
            
            return item
        except Exception:
            self.session.rollback()
            raise

    @transaction_retry(max_retries=3)
    def update_stock(
        self,
        item_id,
        org_id,
        movement_type,
        quantity,
        warehouse_id=None,
        reference=None,
        notes=None,
    ):
        # Reload with lock (Fixes ARC-006)
        item = (
            inventory.InventoryItem.query.with_for_update()
            .filter_by(id=item_id, organisation_id=org_id)
            .first()
        )
        if not item:
            raise NotFoundError("Inventory item not found")

        try:
            if movement_type == "IN":
                item.add_stock(quantity, warehouse_id=warehouse_id, reference=reference, notes=notes)
                action = "STOCK_INCREASED"
                qty_change = quantity
            elif movement_type == "OUT":
                item.remove_stock(quantity, warehouse_id=warehouse_id, reference=reference, notes=notes)
                action = "STOCK_DECREASED"
                qty_change = -quantity
            else:
                raise ValidationError("Invalid movement type")

            AuditService.log_inventory_change(
                item,
                action,
                quantity_change=qty_change,
                reference=reference or "Manual adjustment",
                session=self.session,
            )

            # Note: RestockService.evaluate_stock_health is now triggered automatically
            # inside item.add_stock / remove_stock to prevent logic bypass.

            self.session.commit()
            
            event_bus.publish("STOCK_UPDATE", {"item_id": item.id, "movement_type": movement_type, "quantity": qty_change}, organisation_id=org_id)
            
            return item
        except ValueError as e:
            raise ConflictError(str(e))

    @transaction_retry(max_retries=3)
    def delete_item(self, item_id, org_id):
        item = self.repo.get_item(item_id, org_id)
        if not item:
            raise NotFoundError("Inventory item not found")

        if item.quantity > 0:
            raise ConflictError("Cannot delete item with remaining stock")

        self.repo.soft_delete_item(item)
        AuditService.log_inventory_change(
            item,
            "INVENTORY_ITEM_DELETED",
            reference="Soft delete",
            session=self.session,
        )
        self.session.commit()
        
        event_bus.publish("INVENTORY_DELETED", {"item_id": item_id}, organisation_id=org_id)
        
        return item

    def low_stock_items(self, org_id):
        return self.repo.low_stock_items(org_id)

    def stats(self, org_id):
        return self.repo.stats(org_id)
