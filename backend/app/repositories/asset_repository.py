from sqlalchemy.orm import joinedload
from app import db
from app.models import asset
from app.models import organization
from app.models import location_topology

class AssetRepository:
    """Repository for asset ORM operations."""

    def list_assets(
        self,
        org_id,
        page=1,
        per_page=50,
        status=None,
        department_id=None,
        search=None,
    ):
        query = asset.Asset.query.options(
            joinedload(asset.Asset.department)
        ).filter_by(organisation_id=org_id)

        if status:
            query = query.filter_by(status=status)
        if department_id:
            query = query.filter_by(department_id=department_id)
        if search:
            query = query.outerjoin(organization.Department).outerjoin(
                location_topology.Warehouse, asset.Asset.warehouse_id == location_topology.Warehouse.id
            ).outerjoin(
                location_topology.WarehouseBin, asset.Asset.bin_id == location_topology.WarehouseBin.id
            ).filter(
                db.or_(
                    asset.Asset.name.ilike(f"%{search}%"),
                    asset.Asset.asset_code.ilike(f"%{search}%"),
                    asset.Asset.serial_number.ilike(f"%{search}%"),
                    asset.Asset.assigned_to.ilike(f"%{search}%"),
                    asset.Asset.location.ilike(f"%{search}%"),
                    asset.Asset.type.ilike(f"%{search}%"),
                    organization.Department.name.ilike(f"%{search}%"),
                    organization.Department.code.ilike(f"%{search}%"),
                    location_topology.Warehouse.name.ilike(f"%{search}%"),
                    location_topology.WarehouseBin.code.ilike(f"%{search}%"),
                )
            )
        query = query.order_by(asset.Asset.created_at.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_asset(self, asset_id, org_id):
        return asset.Asset.query.filter_by(
            id=asset_id, organisation_id=org_id
        ).first()

    def list_all_assets(self, org_id):
        return asset.Asset.query.filter_by(organisation_id=org_id).all()

    def list_assets_by_ids(self, org_id, asset_ids):
        return asset.Asset.query.filter(
            asset.Asset.id.in_(asset_ids),
            asset.Asset.organisation_id == org_id
        ).all()

    def exists_asset_code(self, org_id, code):
        return (
            asset.Asset.query.filter_by(
                asset_code=code, organisation_id=org_id
            ).first()
            is not None
        )

    def count_assets(self, org_id):
        return asset.Asset.query.filter_by(organisation_id=org_id).count()

    def exists_serial(self, org_id, serial):
        if not serial:
            return False
        return (
            asset.Asset.query.filter_by(
                serial_number=serial, organisation_id=org_id
            ).first()
            is not None
        )

    def create_asset(self, org_id, data, session=None):
        sess = session or db.session
        new_asset = asset.Asset(
            organisation_id=org_id,
            asset_code=data["asset_code"],
            name=data["name"],
            type=data["type"],
            serial_number=data.get("serial_number"),
            department_id=data["department_id"],
            assigned_to=data.get("assigned_to"),
            location=data.get("location"),
            warehouse_id=data.get("warehouse_id"),
            bin_id=data.get("bin_id"),
            purchase_date=data["purchase_date"],
            purchase_value=data["purchase_value"],
            useful_life=data["useful_life"],
            current_value=data.get("purchase_value", 0),
            qr_code_data=data.get("qr_code_data"),
        )
        sess.add(new_asset)
        return new_asset

    def update_asset(self, asset_obj, update_fields):
        for field, value in update_fields.items():
            setattr(asset_obj, field, value)
        asset_obj.updated_at = db.func.now()
        return asset_obj

    def delete_asset(self, asset_obj, session=None):
        sess = session or db.session
        sess.delete(asset_obj)
        return asset_obj

    def stats(self, org_id):
        status_counts = (
            db.session.query(asset.Asset.status, db.func.count(asset.Asset.id))
            .filter_by(organisation_id=org_id)
            .group_by(asset.Asset.status)
            .all()
        )

        total_value = (
            db.session.query(db.func.sum(asset.Asset.current_value))
            .filter_by(organisation_id=org_id)
            .scalar()
            or 0
        )

        condition_counts = (
            db.session.query(
                asset.Asset.condition, db.func.count(asset.Asset.id)
            )
            .filter_by(organisation_id=org_id)
            .group_by(asset.Asset.condition)
            .all()
        )

        return {
            "total_assets": sum(count for _, count in status_counts),
            "total_value": total_value,
            "status_breakdown": {
                status: count for status, count in status_counts
            },
            "condition_breakdown": {
                condition: count for condition, count in condition_counts
            },
        }
