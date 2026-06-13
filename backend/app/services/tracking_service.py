import hashlib
from datetime import datetime, timedelta

from flask import current_app

from app import db
from app.audit_service import AuditService
from app.db_utils import transaction_retry
from app.errors import ConflictError, NotFoundError, ValidationError
from app.models.asset import Asset
from app.models.inventory import InventoryItem
from app.models.location_topology import Warehouse, WarehouseBin
from app.models.scan_event import ScanEvent
from app.services.event_bus import event_bus
from app.tracking_rbac import assert_can_scan, is_state_mutating_action
from app.utils.qr_payload import _extract_signed_token, parse_verified_payload
from app.utils.security import verify_signed_qr


class TrackingService:
    """Service for managing item tracking via signed QR scans."""

    @staticmethod
    def _capture_state(item, item_type: str) -> dict:
        if item_type == "asset":
            return {
                "status": getattr(item, "status", None),
                "location": getattr(item, "location", None),
                "warehouse_id": getattr(item, "warehouse_id", None),
                "bin_id": getattr(item, "bin_id", None),
            }
        if item_type == "inventory":
            return {
                "quantity": getattr(item, "quantity", None),
                "is_active": getattr(item, "is_active", True),
            }
        return {"status": getattr(item, "status", None)}

    @staticmethod
    def _scan_fingerprint(
        org_id,
        item_type,
        item_id,
        user_id,
        action_type,
        warehouse_id,
        bin_id,
    ) -> str:
        raw = (
            f"{org_id}:{item_type}:{item_id}:{user_id}:"
            f"{action_type}:{warehouse_id}:{bin_id}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    @staticmethod
    def _check_duplicate(fingerprint: str, org_id: int):
        window = current_app.config.get("SCAN_DEDUP_SECONDS", 30)
        since = datetime.utcnow() - timedelta(seconds=window)
        existing = (
            ScanEvent.query.filter_by(
                organisation_id=org_id,
                scan_fingerprint=fingerprint,
                validation_status="verified",
            )
            .filter(ScanEvent.timestamp >= since)
            .first()
        )
        if existing:
            raise ConflictError(
                "Duplicate scan detected; wait before scanning again"
            )

    @staticmethod
    def _resolve_item(org_id, qr_data, sess):
        """Resolve entity from signed QR payload (secure path first)."""
        token = _extract_signed_token(qr_data)

        # v1 structured signed payload
        try:
            entity_type, payload_org, entity_id, _exp = parse_verified_payload(
                token
            )
            if payload_org != org_id:
                raise ValidationError(
                    "QR code belongs to another organization"
                )
            if entity_type == "asset":
                item = (
                    Asset.query.with_for_update()
                    .filter_by(id=entity_id, organisation_id=org_id)
                    .first()
                )
                if item:
                    return item, "asset"
            elif entity_type == "inventory":
                item = (
                    InventoryItem.query.with_for_update()
                    .filter_by(id=entity_id, organisation_id=org_id)
                    .first()
                )
                if item:
                    return item, "inventory"
            raise NotFoundError("Entity in QR code not found")
        except ValueError:
            pass

        # Legacy signed asset:org_id:asset_code
        verified = verify_signed_qr(token)
        if verified:
            if verified.startswith("asset:") and ":" in verified:
                parts = verified.split(":")
                if len(parts) >= 3 and int(parts[1]) == org_id:
                    asset_code = parts[2]
                    item = (
                        Asset.query.with_for_update()
                        .filter_by(
                            organisation_id=org_id, asset_code=asset_code
                        )
                        .first()
                    )
                    if item:
                        return item, "asset"

        # Stored scan URL / token match (still requires prior signature at creation)
        asset_obj = (
            Asset.query.with_for_update()
            .filter(
                Asset.organisation_id == org_id,
                db.or_(
                    Asset.qr_code_data == qr_data,
                    Asset.qr_code_data.contains(token),
                ),
            )
            .first()
        )
        if asset_obj:
            return asset_obj, "asset"

        inventory_item = (
            InventoryItem.query.with_for_update()
            .filter(
                InventoryItem.organisation_id == org_id,
                db.or_(
                    InventoryItem.qr_code_data == qr_data,
                    InventoryItem.qr_code_data.contains(token),
                    InventoryItem.sku == token,
                ),
            )
            .first()
        )
        if inventory_item:
            return inventory_item, "inventory"

        from app.models.item_instance import ItemInstance

        instance = (
            ItemInstance.query.with_for_update()
            .join(InventoryItem)
            .filter(
                InventoryItem.organisation_id == org_id,
                db.or_(
                    ItemInstance.qr_code_data == qr_data,
                    ItemInstance.qr_code_data.contains(token),
                ),
            )
            .first()
        )
        if instance:
            return instance, "inventory_instance"

        raise NotFoundError("No item found matching this QR code")

    @staticmethod
    def _target_asset_status(asset: Asset, action_type: str):
        action = (action_type or "").upper()
        current = asset.status
        if action == "CHECK_OUT" and current == "approved":
            return "in_use"
        if action == "CHECK_IN" and current == "maintenance":
            return "in_use"
        if action == "TRANSFER" and current == "maintenance":
            return "in_use"
        return None

    @staticmethod
    @transaction_retry(max_retries=3)
    def record_scan(
        org_id,
        user_id,
        user_role,
        qr_data,
        action_type,
        warehouse_id=None,
        bin_id=None,
        device_id=None,
        notes=None,
        lat=None,
        lon=None,
        session=None,
    ):
        """Record a verified scan event and apply location/state updates."""
        sess = session or db.session
        action_type = (action_type or "AUDIT").upper()

        assert_can_scan(user_role, action_type)

        item, item_type = TrackingService._resolve_item(org_id, qr_data, sess)

        fingerprint = TrackingService._scan_fingerprint(
            org_id,
            item_type,
            item.id,
            user_id,
            action_type,
            warehouse_id,
            bin_id,
        )
        if is_state_mutating_action(action_type):
            TrackingService._check_duplicate(fingerprint, org_id)

        if bin_id:
            from app.models.location_topology import (
                WarehouseShelf,
                WarehouseRack,
                WarehouseZone,
            )

            bin_obj = (
                WarehouseBin.query.join(WarehouseShelf)
                .join(WarehouseRack)
                .join(WarehouseZone)
                .join(Warehouse)
                .filter(
                    WarehouseBin.id == bin_id,
                    Warehouse.organisation_id == org_id,
                )
                .first()
            )
            if not bin_obj:
                raise ValidationError("Invalid storage bin or access denied")
            if warehouse_id:
                if bin_obj.shelf.rack.zone.warehouse_id != warehouse_id:
                    raise ValidationError(
                        "Storage bin does not belong to the selected warehouse"
                    )
            else:
                raise ValidationError(
                    "Warehouse ID is required when specifying a bin"
                )

        previous_state = TrackingService._capture_state(item, item_type)

        if is_state_mutating_action(action_type):
            TrackingService._apply_scan_effects(
                item,
                item_type,
                action_type,
                warehouse_id,
                bin_id,
                notes,
            )

        new_state = TrackingService._capture_state(item, item_type)

        event = ScanEvent(
            organisation_id=org_id,
            user_id=user_id,
            user_role=user_role,
            item_type=item_type,
            item_id=item.id,
            warehouse_id=warehouse_id,
            bin_id=bin_id,
            device_id=device_id,
            action_type=action_type,
            notes=notes,
            latitude=lat,
            longitude=lon,
            previous_state=previous_state,
            new_state=new_state,
            validation_status="verified",
            scan_fingerprint=fingerprint,
            timestamp=datetime.utcnow(),
        )
        sess.add(event)

        AuditService.log_action(
            action=f"QR_SCAN_{action_type}",
            entity_type=item_type,
            entity_id=item.id,
            details={
                "warehouse_id": warehouse_id,
                "bin_id": bin_id,
                "previous_state": previous_state,
                "new_state": new_state,
                "scan_event_id": None,
            },
            user_id=user_id,
            organisation_id=org_id,
            session=sess,
        )

        event_bus.publish(
            "SCAN_EVENT",
            {
                "scan_event_id": event.id,
                "item_id": item.id,
                "type": item_type,
                "warehouse_id": warehouse_id,
                "action": action_type,
                "previous_state": previous_state,
                "new_state": new_state,
                "lat": lat,
                "lon": lon,
                "timestamp": event.timestamp.isoformat(),
            },
            organisation_id=org_id,
        )

        sess.commit()
        return item, event

    @staticmethod
    def verify_scan(org_id, user_id, user_role, qr_data):
        """Read-only QR verification (viewer-safe)."""
        assert_can_scan(user_role, "VERIFY")
        item, item_type = TrackingService._resolve_item(org_id, qr_data, db.session)
        state = TrackingService._capture_state(item, item_type)
        return {
            "entity_type": item_type,
            "entity_id": item.id,
            "state": state,
            "validation_status": "verified",
        }

    @staticmethod
    def _apply_scan_effects(
        item,
        item_type,
        action_type,
        warehouse_id,
        bin_id,
        notes,
    ):
        old_bin_id = getattr(item, "bin_id", None) if item_type != "inventory" else None

        if action_type == "CHECK_OUT":
            if hasattr(item, "warehouse_id"):
                item.warehouse_id = None
            if hasattr(item, "bin_id"):
                item.bin_id = None
            if item_type == "asset":
                item.location = "Checked Out"
        else:
            if warehouse_id is not None and hasattr(item, "warehouse_id"):
                item.warehouse_id = warehouse_id
            if bin_id is not None and hasattr(item, "bin_id"):
                item.bin_id = bin_id

        if item_type == "asset":
            if warehouse_id:
                wh = Warehouse.query.get(warehouse_id)
                if wh:
                    item.location = f"WH: {wh.name}"
                    if bin_id:
                        item.location += f" / Bin: {bin_id}"

            target = TrackingService._target_asset_status(item, action_type)
            if target and item.can_transition_to(target):
                item.status = target

        elif item_type == "inventory_instance":
            if action_type == "CHECK_OUT":
                item.status = "shipped"
            elif action_type in ("CHECK_IN", "TRANSFER"):
                item.status = "in_stock"

        elif item_type == "inventory":
            if action_type == "CHECK_OUT":
                try:
                    item.remove_stock(
                        1, warehouse_id, f"Scan OUT - {notes or ''}"
                    )
                except ValueError:
                    item.remove_stock(
                        1, None, f"Scan OUT (Global) - {notes or ''}"
                    )
            elif action_type == "CHECK_IN":
                item.add_stock(1, warehouse_id, f"Scan IN - {notes or ''}")

        if item_type != "inventory":
            if old_bin_id and old_bin_id != getattr(item, "bin_id", None):
                old_bin = WarehouseBin.query.get(old_bin_id)
                if old_bin:
                    old_bin.status = "available"
            if getattr(item, "bin_id", None) and getattr(item, "bin_id", None) != old_bin_id:
                new_bin = WarehouseBin.query.get(item.bin_id)
                if new_bin:
                    new_bin.status = "occupied"

    @staticmethod
    def get_history(org_id, item_type, item_id):
        """Get immutable movement history for an item."""
        return (
            ScanEvent.query.filter_by(
                organisation_id=org_id,
                item_type=item_type,
                item_id=item_id,
                validation_status="verified",
            )
            .order_by(ScanEvent.timestamp.desc())
            .all()
        )

    @staticmethod
    def serialize_event(event: ScanEvent) -> dict:
        return {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "action": event.action_type,
            "user_id": event.user_id,
            "user_role": event.user_role,
            "warehouse_id": event.warehouse_id,
            "bin_id": event.bin_id,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "previous_state": event.previous_state,
            "new_state": event.new_state,
            "validation_status": event.validation_status,
            "notes": event.notes,
        }

    @staticmethod
    def get_bin_environment(bin_id, org_id):
        """Get the surrounding environment of a bin."""
        bin_obj = WarehouseBin.query.get(bin_id)
        if not bin_obj:
            raise NotFoundError("Bin not found")

        nearby_assets = Asset.query.filter_by(
            organisation_id=org_id,
            bin_id=bin_id,
        ).all()

        return {
            "bin_code": bin_obj.code,
            "coordinates": {
                "x": bin_obj.x_pos,
                "y": bin_obj.y_pos,
                "z": bin_obj.z_pos,
            },
            "environment_image": bin_obj.environment_image_url,
            "nearby_items_count": len(nearby_assets),
            "status": bin_obj.status,
        }
