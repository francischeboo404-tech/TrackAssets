from app import db
from app.audit_service import AuditService
from app.repositories.asset_repository import AssetRepository
from app.models import organization
from app.services.qr_service import QRService
from app.errors import NotFoundError, ConflictError, ValidationError, AuthorizationError
from app.rbac import assert_can_transition_status, assert_not_read_only
from app.db_utils import transaction_retry
from datetime import datetime
from app.services.event_bus import event_bus
from flask import current_app

class AssetService:
    """Service layer for asset business logic."""

    def __init__(self, repository: AssetRepository = None, session=None):
        self.repo = repository or AssetRepository()
        self.session = session or db.session

    def list_assets(
        self,
        org_id,
        page=1,
        per_page=50,
        status=None,
        department_id=None,
        search=None,
    ):
        return self.repo.list_assets(
            org_id,
            page=page,
            per_page=per_page,
            status=status,
            department_id=department_id,
            search=search,
        )

    def get_asset(self, asset_id, org_id):
        asset_obj = self.repo.get_asset(asset_id, org_id)
        if not asset_obj:
            raise NotFoundError("Asset not found")
        return asset_obj

    @transaction_retry(max_retries=3)
    def create_asset(self, org_id, validated_data):
        current_app.logger.debug(
            "create_asset called",
            extra={"org_id": org_id, "data_keys": list(validated_data.keys())},
        )
        # validate department exists
        dept = organization.Department.query.filter_by(
            id=validated_data["department_id"], organisation_id=org_id
        ).first()
        if not dept:
            current_app.logger.warning(
                "create_asset: invalid department",
                extra={"department_id": validated_data.get("department_id")},
            )
            raise ValidationError("Invalid department")

        # Purchase date cannot be in the future (allow 1 day buffer for timezone differences)
        from datetime import timedelta
        if validated_data["purchase_date"] > (datetime.utcnow().date() + timedelta(days=1)):
            raise ValidationError("Purchase date cannot be in the future")

        # Get organization for code prefix
        org = organization.Organization.query.get(org_id)
        if not org:
            raise ValidationError("Organization not found")

        # 1. Auto-generate Asset Code if missing (e.g., ORG-001)
        if not validated_data.get("asset_code"):
            asset_count = self.repo.count_assets(org_id)
            new_code = f"{org.code}-{str(asset_count + 1).zfill(3)}"
            
            # Ensure uniqueness (loop in case of race/deletion)
            while self.repo.exists_asset_code(org_id, new_code):
                asset_count += 1
                new_code = f"{org.code}-{str(asset_count + 1).zfill(3)}"
            
            validated_data["asset_code"] = new_code
        else:
            if self.repo.exists_asset_code(org_id, validated_data["asset_code"]):
                raise ConflictError("Asset code already exists")

        if validated_data.get("serial_number") and self.repo.exists_serial(
            org_id, validated_data.get("serial_number")
        ):
            current_app.logger.warning(
                "create_asset: serial conflict",
                extra={"serial": validated_data.get("serial_number")},
            )
            raise ConflictError("Serial number already exists")

        new_asset = self.repo.create_asset(
            org_id, validated_data, session=self.session
        )

        QRService.ensure_asset_qr(new_asset)

        # Sync with Inventory (Safely within current transaction without calling nested service commits)
        try:
            from app.models.inventory import InventoryItem, StockMovementType, StockMovement
            
            derived_sku = f"ASSET-{new_asset.type.upper()}-{new_asset.name.upper().replace(' ', '-')}"
            
            existing_item = InventoryItem.query.filter_by(
                organisation_id=org_id, 
                name=new_asset.name
            ).first()
            
            if not existing_item:
                existing_item = InventoryItem(
                    organisation_id=org_id,
                    name=new_asset.name,
                    sku=derived_sku[:100],
                    description=f"Aggregate inventory for {new_asset.type} assets: {new_asset.name}",
                    unit_price=float(new_asset.purchase_value),
                    unit="unit",
                    reorder_level=0,
                    quantity=0,
                )
                self.session.add(existing_item)
                self.session.flush() # Flush to get ID
                
            # Increment stock manually to avoid inner commits
            existing_item.quantity += 1
            if new_asset.warehouse_id:
                from app.models.stock_levels import WarehouseStock
                wh_stock = WarehouseStock.query.filter_by(
                    item_id=existing_item.id, warehouse_id=new_asset.warehouse_id
                ).first()
                if not wh_stock:
                    wh_stock = WarehouseStock(item_id=existing_item.id, warehouse_id=new_asset.warehouse_id, quantity_on_hand=1)
                    self.session.add(wh_stock)
                else:
                    wh_stock.quantity_on_hand += 1

            movement = StockMovement(
                item_id=existing_item.id,
                type=StockMovementType.IN.value,
                quantity=1,
                reference=f"Asset Registration: {new_asset.asset_code}",
                notes=f"Auto-increment from asset registration of {new_asset.name}",
                date=db.func.now(),
            )
            self.session.add(movement)
            
        except Exception as inv_err:
            current_app.logger.error(
                "create_asset: inventory sync failed", 
                extra={"error": str(inv_err), "asset_code": new_asset.asset_code}
            )
            # We don't fail asset creation if inventory sync fails, but we log it
            # In a robust ERP, this might be a mandatory transaction

        # Update bin status if assigned
        if new_asset.bin_id:
            from app.models.location_topology import WarehouseBin
            new_bin = WarehouseBin.query.get(new_asset.bin_id)
            if new_bin:
                new_bin.status = "occupied"

        # set initial current value via model method
        new_asset.update_current_value()
        AuditService.log_asset_change(
            new_asset,
            "ASSET_CREATED",
            new_values={
                "asset_code": new_asset.asset_code,
                "name": new_asset.name,
                "department_id": new_asset.department_id,
            },
            session=self.session,
        )
        try:
            self.session.commit()
        except Exception as e:
            current_app.logger.error(
                "create_asset: commit failed", extra={"error": str(e)}
            )
            self.session.rollback()
            raise
        
        event_bus.publish("ASSET_CREATED", {"asset_id": new_asset.id, "asset_code": new_asset.asset_code}, organisation_id=org_id)
        current_app.logger.info(
            "create_asset: success",
            extra={"asset_id": new_asset.id, "asset_code": new_asset.asset_code},
        )
        return new_asset

    @transaction_retry(max_retries=3)
    def update_asset(self, asset_id, org_id, data, user_role=None):
        if user_role:
            assert_not_read_only(user_role, "edit assets")

        # Reload with lock
        from app.models.asset import Asset

        asset_obj = (
            Asset.query.with_for_update()
            .filter_by(id=asset_id, organisation_id=org_id)
            .first()
        )
        if not asset_obj:
            raise NotFoundError("Asset not found")

        old_values = {
            "name": asset_obj.name,
            "department_id": asset_obj.department_id,
            "assigned_to": asset_obj.assigned_to,
            "location": asset_obj.location,
            "condition": asset_obj.condition,
            "bin_id": asset_obj.bin_id,
        }

        if "department_id" in data:
            dept = organization.Department.query.filter_by(
                id=data["department_id"], organisation_id=org_id
            ).first()
            if not dept:
                raise ValidationError("Invalid department")

        updatable_fields = {
            k: data[k]
            for k in [
                "name",
                "assigned_to",
                "location",
                "condition",
                "warehouse_id",
                "bin_id",
                "type",
                "serial_number",
                "purchase_date",
                "purchase_value",
                "useful_life",
            ]
            if k in data
        }
        self.repo.update_asset(asset_obj, updatable_fields)
        if "department_id" in data:
            asset_obj.department_id = data["department_id"]

        # Manage bin status interoperability
        if "bin_id" in data and data["bin_id"] != old_values["bin_id"]:
            from app.models.location_topology import WarehouseBin
            if old_values["bin_id"]:
                old_bin = WarehouseBin.query.get(old_values["bin_id"])
                if old_bin:
                    old_bin.status = "available"
            if data["bin_id"]:
                new_bin = WarehouseBin.query.get(data["bin_id"])
                if new_bin:
                    new_bin.status = "occupied"

        asset_obj.updated_at = db.func.now()
        AuditService.log_asset_change(
            asset_obj,
            "ASSET_UPDATED",
            old_values=old_values,
            new_values={k: getattr(asset_obj, k) for k in old_values.keys()},
            session=self.session,
        )
        self.session.commit()
        
        event_bus.publish("ASSET_UPDATED", {"asset_id": asset_obj.id}, organisation_id=org_id)
        
        return asset_obj

    @transaction_retry(max_retries=3)
    def update_asset_status(
        self, asset_id, org_id, new_status, current_user_role, comments=None
    ):
        # Reload with lock
        from app.models.asset import Asset

        asset_obj = (
            Asset.query.with_for_update()
            .filter_by(id=asset_id, organisation_id=org_id)
            .first()
        )
        if not asset_obj:
            raise NotFoundError("Asset not found")

        old_status = asset_obj.status
        if not asset_obj.can_transition_to(new_status):
            raise ValidationError(
                f"Invalid status transition from {old_status} to {new_status}"
            )

        if current_user_role:
            assert_can_transition_status(
                current_user_role, old_status, new_status
            )
        elif new_status == "disposed":
            raise AuthorizationError("Only admins can dispose assets")
        asset_obj.status = new_status
        asset_obj.updated_at = db.func.now()
        AuditService.log_asset_change(
            asset_obj,
            "ASSET_STATUS_CHANGED",
            old_values={"status": old_status},
            new_values={"status": new_status, "comments": comments},
            session=self.session,
        )
        self.session.commit()
        
        event_bus.publish("ASSET_STATUS_CHANGED", {"asset_id": asset_obj.id, "status": new_status}, organisation_id=org_id)
        
        return asset_obj

    def delete_asset(self, asset_id, org_id):
        asset_obj = self.repo.get_asset(asset_id, org_id)
        if not asset_obj:
            raise NotFoundError("Asset not found")

        if asset_obj.status in ["in_use", "maintenance"]:
            raise ConflictError(
                "Cannot delete asset that is in use or under maintenance"
            )

        # store audit data before delete
        asset_data = {
            "asset_code": asset_obj.asset_code,
            "name": asset_obj.name,
            "status": asset_obj.status,
        }
        
        # Free up bin space
        old_bin_id = asset_obj.bin_id
        
        self.repo.delete_asset(asset_obj, session=self.session)
        
        if old_bin_id:
            from app.models.location_topology import WarehouseBin
            old_bin = WarehouseBin.query.get(old_bin_id)
            if old_bin:
                old_bin.status = "available"

        # Sync with Inventory (Decrement) Safely
        try:
            from app.models.inventory import InventoryItem, StockMovementType, StockMovement
            
            existing_item = InventoryItem.query.filter_by(
                organisation_id=org_id, 
                name=asset_obj.name
            ).first()
            
            if existing_item and existing_item.quantity > 0:
                existing_item.quantity -= 1
                
                if asset_obj.warehouse_id:
                    from app.models.stock_levels import WarehouseStock
                    wh_stock = WarehouseStock.query.filter_by(
                        item_id=existing_item.id, warehouse_id=asset_obj.warehouse_id
                    ).first()
                    if wh_stock and wh_stock.quantity_on_hand > 0:
                        wh_stock.quantity_on_hand -= 1

                movement = StockMovement(
                    item_id=existing_item.id,
                    type=StockMovementType.OUT.value,
                    quantity=1,
                    reference=f"Asset Deletion: {asset_obj.asset_code}",
                    notes=f"Auto-decrement from asset deletion of {asset_obj.name}",
                    date=db.func.now(),
                )
                self.session.add(movement)
        except Exception as inv_err:
            current_app.logger.error(
                "delete_asset: inventory sync failed", 
                extra={"error": str(inv_err), "asset_code": asset_obj.asset_code}
            )

        AuditService.log_action(
            action="ASSET_DELETED",
            entity_type="asset",
            entity_id=asset_obj.id,
            details=asset_data,
            organisation_id=asset_obj.organisation_id,
            session=self.session,
        )
        self.session.commit()
        
        event_bus.publish("ASSET_DELETED", {"asset_id": asset_id}, organisation_id=org_id)
        
        return True

    def stats(self, org_id):
        """Get asset statistics from repository"""
        return self.repo.stats(org_id)

    def get_bulk_qr_data(self, org_id, asset_ids=None):
        """Get data for bulk QR generation"""
        assets = self.repo.list_assets_by_ids(org_id, asset_ids) if asset_ids else self.repo.list_all_assets(org_id)
        return [
            {
                "id": a.id,
                "asset_code": a.asset_code,
                "name": a.name,
                "qr_code_data": a.qr_code_data
            }
            for a in assets
        ]
