"""QR code generation and resolution for trackable entities."""

from app import db
from app.errors import NotFoundError
from app.models.asset import Asset
from app.models.inventory import InventoryItem
from app.utils.qr_payload import (
    build_scan_url,
    build_signed_token,
    legacy_asset_code_payload,
)
from app.utils.security import generate_signed_qr


class QRService:
    @staticmethod
    def ensure_asset_qr(asset: Asset, refresh: bool = False) -> str:
        """Return signed scan URL stored on asset.qr_code_data."""
        if asset.qr_code_data and not refresh:
            if "?data=" in asset.qr_code_data:
                return asset.qr_code_data

        signed = build_signed_token("asset", asset.organisation_id, asset.id)
        url = build_scan_url(signed)
        asset.qr_code_data = url
        db.session.add(asset)
        return url

    @staticmethod
    def ensure_inventory_qr(item: InventoryItem, refresh: bool = False) -> str:
        if item.qr_code_data and not refresh:
            if "?data=" in item.qr_code_data:
                return item.qr_code_data

        signed = build_signed_token("inventory", item.organisation_id, item.id)
        url = build_scan_url(signed)
        item.qr_code_data = url
        db.session.add(item)
        return url

    @staticmethod
    def get_qr_payload(org_id: int, entity_type: str, entity_id: int) -> dict:
        if entity_type == "asset":
            asset = Asset.query.filter_by(
                id=entity_id, organisation_id=org_id
            ).first()
            if not asset:
                raise NotFoundError("Asset not found")
            url = QRService.ensure_asset_qr(asset)
            signed = url.split("data=", 1)[-1]
            legacy = generate_signed_qr(
                legacy_asset_code_payload(org_id, asset.asset_code)
            )
            db.session.commit()
            return {
                "entity_type": "asset",
                "entity_id": asset.id,
                "entity_code": asset.asset_code,
                "signed_token": signed,
                "scan_url": url,
                "legacy_token": legacy,
            }

        if entity_type == "inventory":
            item = InventoryItem.query.filter_by(
                id=entity_id, organisation_id=org_id
            ).first()
            if not item:
                raise NotFoundError("Inventory item not found")
            url = QRService.ensure_inventory_qr(item)
            signed = url.split("data=", 1)[-1]
            db.session.commit()
            return {
                "entity_type": "inventory",
                "entity_id": item.id,
                "entity_code": item.sku,
                "signed_token": signed,
                "scan_url": url,
            }

        raise NotFoundError("Unsupported entity type")
