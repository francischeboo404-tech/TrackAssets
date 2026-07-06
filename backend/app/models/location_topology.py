from datetime import datetime
from app import db


class Warehouse(db.Model):
    """Main warehouse facility with hierarchical support for multi-location inventory"""

    __tablename__ = "warehouses"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(500))
    
    # Warehouse Hierarchy Support
    parent_warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=True
    )
    is_main_warehouse = db.Column(db.Boolean, default=False)
    warehouse_type = db.Column(
        db.String(50), 
        default="storage_facility",
        nullable=False
    )  # 'main' | 'storage_facility'
    hierarchy_level = db.Column(db.Integer, default=0)  # 0=main, 1=direct child, etc.
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index("ix_warehouses_org_id", "organisation_id"),
        db.Index("ix_warehouses_parent_id", "parent_warehouse_id"),
        db.Index("ix_warehouses_is_main", "is_main_warehouse"),
    )

    zones = db.relationship(
        "WarehouseZone",
        backref="warehouse",
        lazy=True,
        cascade="all, delete-orphan",
    )
    
    # Self-referential relationship for parent-child warehouse hierarchy
    parent_warehouse = db.relationship(
        "Warehouse",
        remote_side=[id],
        backref="child_warehouses",
        foreign_keys=[parent_warehouse_id]
    )

    def get_hierarchy_path(self):
        """Get the full hierarchy path for this warehouse"""
        path = [self.id]
        current = self
        while current.parent_warehouse_id:
            path.insert(0, current.parent_warehouse_id)
            current = self.__class__.query.filter_by(
                id=current.parent_warehouse_id
            ).first()
        return path

    def is_child_of(self, warehouse_id):
        """Check if this warehouse is a child of the given warehouse"""
        current = self
        while current.parent_warehouse_id:
            if current.parent_warehouse_id == warehouse_id:
                return True
            current = self.__class__.query.filter_by(
                id=current.parent_warehouse_id
            ).first()
        return False


class WarehouseZone(db.Model):
    """Specific zone within a warehouse (e.g., Receiving, Shipping, Cold Storage)"""

    __tablename__ = "warehouse_zones"

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=False
    )
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    zone_type = db.Column(db.String(50))  # e.g., STORAGE, TRANSIT, STAGING

    racks = db.relationship(
        "WarehouseRack",
        backref="zone",
        lazy=True,
        cascade="all, delete-orphan",
    )


class WarehouseRack(db.Model):
    """Storage rack within a zone"""

    __tablename__ = "warehouse_racks"

    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(
        db.Integer, db.ForeignKey("warehouse_zones.id"), nullable=False
    )
    code = db.Column(db.String(50), nullable=False)

    shelves = db.relationship(
        "WarehouseShelf",
        backref="rack",
        lazy=True,
        cascade="all, delete-orphan",
    )


class WarehouseShelf(db.Model):
    """Specific shelf within a rack"""

    __tablename__ = "warehouse_shelves"

    id = db.Column(db.Integer, primary_key=True)
    rack_id = db.Column(
        db.Integer, db.ForeignKey("warehouse_racks.id"), nullable=False
    )
    code = db.Column(db.String(50), nullable=False)

    bins = db.relationship(
        "WarehouseBin",
        backref="shelf",
        lazy=True,
        cascade="all, delete-orphan",
    )


class WarehouseBin(db.Model):
    """Smallest unit of storage (Bin/Slot) with spatial awareness"""

    __tablename__ = "warehouse_bins"

    id = db.Column(db.Integer, primary_key=True)
    shelf_id = db.Column(
        db.Integer, db.ForeignKey("warehouse_shelves.id"), nullable=False
    )
    code = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="available")

    # Spatial Coordinates (Grid system)
    x_pos = db.Column(db.Float)
    y_pos = db.Column(db.Float)
    z_pos = db.Column(db.Float)  # Height/Level

    __table_args__ = (
        db.Index("ix_warehouse_bins_shelf_status", "shelf_id", "status"),
        db.Index("ix_warehouse_bins_status", "status"),
    )

    # Environment Visibility
    environment_image_url = db.Column(db.String(500))
    description = db.Column(db.String(255))
