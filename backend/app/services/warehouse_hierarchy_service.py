"""
Warehouse Hierarchy Service

Manages the hierarchical warehouse structure with a main warehouse as parent
and child storage facilities. Enforces business rules for warehouse relationships
and stock transfers.
"""

from app import db
from app.models.location_topology import Warehouse
from app.errors import NotFoundError, ConflictError, ValidationError
from sqlalchemy import and_


class WarehouseHierarchyService:
    """Service for managing warehouse hierarchy and relationships"""

    @staticmethod
    def get_main_warehouse(org_id: int) -> Warehouse:
        """Get the main warehouse for an organization"""
        main_warehouse = db.session.query(Warehouse).filter(
            and_(
                Warehouse.organisation_id == org_id,
                Warehouse.is_main_warehouse == True,
                Warehouse.is_active == True
            )
        ).first()
        
        if not main_warehouse:
            raise NotFoundError(
                "No main warehouse configured for this organization. "
                "Please configure a main warehouse in system settings."
            )
        return main_warehouse

    @staticmethod
    def get_child_warehouses(parent_warehouse_id: int) -> list:
        """Get all direct child warehouses of a given parent"""
        return db.session.query(Warehouse).filter(
            and_(
                Warehouse.parent_warehouse_id == parent_warehouse_id,
                Warehouse.is_active == True
            )
        ).all()

    @staticmethod
    def get_all_descendants(warehouse_id: int) -> list:
        """Get all warehouses in the hierarchy below this warehouse (recursively)"""
        warehouse = db.session.query(Warehouse).filter_by(id=warehouse_id).first()
        if not warehouse:
            raise NotFoundError("Warehouse not found")
        
        descendants = []
        
        def collect_descendants(wh):
            for child in wh.child_warehouses:
                if child.is_active:
                    descendants.append(child)
                    collect_descendants(child)
        
        collect_descendants(warehouse)
        return descendants

    @staticmethod
    def get_warehouse_hierarchy(org_id: int) -> dict:
        """Get the complete warehouse hierarchy for an organization"""
        main = WarehouseHierarchyService.get_main_warehouse(org_id)
        
        def build_hierarchy(warehouse):
            children = []
            for child in warehouse.child_warehouses:
                if child.is_active:
                    children.append(build_hierarchy(child))
            
            return {
                "id": warehouse.id,
                "name": warehouse.name,
                "code": warehouse.code,
                "address": warehouse.address,
                "is_main": warehouse.is_main_warehouse,
                "hierarchy_level": warehouse.hierarchy_level,
                "children": children
            }
        
        return build_hierarchy(main)

    @staticmethod
    def set_main_warehouse(warehouse_id: int, org_id: int) -> Warehouse:
        """
        Set a warehouse as the main warehouse for an organization.
        
        Business Rules:
        - Only one main warehouse per organization
        - Main warehouse cannot have a parent
        - All other warehouses become storage facilities
        """
        # Verify warehouse exists and belongs to org
        warehouse = db.session.query(Warehouse).filter(
            and_(
                Warehouse.id == warehouse_id,
                Warehouse.organisation_id == org_id
            )
        ).first()
        
        if not warehouse:
            raise NotFoundError("Warehouse not found")
        
        # If this warehouse has a parent, it cannot be the main warehouse
        if warehouse.parent_warehouse_id:
            raise ConflictError(
                "Cannot set a child warehouse as main. "
                "Only root warehouses can be main warehouses."
            )
        
        # If a different warehouse is already main, demote it
        current_main = db.session.query(Warehouse).filter(
            and_(
                Warehouse.organisation_id == org_id,
                Warehouse.is_main_warehouse == True,
                Warehouse.id != warehouse_id
            )
        ).first()
        
        if current_main:
            current_main.is_main_warehouse = False
            current_main.warehouse_type = "storage_facility"
            current_main.hierarchy_level = 1
        
        # Set the new main warehouse
        warehouse.is_main_warehouse = True
        warehouse.warehouse_type = "main"
        warehouse.hierarchy_level = 0
        warehouse.parent_warehouse_id = None
        
        db.session.commit()
        return warehouse

    @staticmethod
    def add_child_warehouse(
        child_warehouse_id: int, 
        parent_warehouse_id: int,
        org_id: int
    ) -> Warehouse:
        """
        Add a warehouse as a child of another warehouse.
        
        Business Rules:
        - Parent must exist and be active
        - Child must exist and be active
        - Both must belong to same organization
        - Cannot create circular relationships
        - Child cannot be an ancestor of parent
        """
        parent = db.session.query(Warehouse).filter(
            and_(
                Warehouse.id == parent_warehouse_id,
                Warehouse.organisation_id == org_id,
                Warehouse.is_active == True
            )
        ).first()
        
        if not parent:
            raise NotFoundError("Parent warehouse not found")
        
        child = db.session.query(Warehouse).filter(
            and_(
                Warehouse.id == child_warehouse_id,
                Warehouse.organisation_id == org_id,
                Warehouse.is_active == True
            )
        ).first()
        
        if not child:
            raise NotFoundError("Child warehouse not found")
        
        if child.id == parent.id:
            raise ValidationError("A warehouse cannot be its own parent")
        
        # Check if child is already an ancestor of parent (would create circular ref)
        if child.is_child_of(parent.id) or parent.is_child_of(child.id):
            raise ConflictError(
                "Cannot create circular warehouse hierarchy. "
                "The destination warehouse is already in the hierarchy chain."
            )
        
        # Check if child already has a different parent
        if child.parent_warehouse_id and child.parent_warehouse_id != parent_warehouse_id:
            raise ConflictError(
                f"Warehouse already has a parent (ID: {child.parent_warehouse_id}). "
                "Use move_warehouse to change parent relationships."
            )
        
        # Update the child's parent and hierarchy level
        child.parent_warehouse_id = parent_warehouse_id
        child.warehouse_type = "storage_facility"
        child.is_main_warehouse = False
        child.hierarchy_level = parent.hierarchy_level + 1
        
        db.session.commit()
        return child

    @staticmethod
    def move_warehouse(
        warehouse_id: int,
        new_parent_warehouse_id: int,
        org_id: int
    ) -> Warehouse:
        """
        Move a warehouse to a different parent in the hierarchy.
        
        This updates both the warehouse and all its descendants recursively.
        """
        warehouse = db.session.query(Warehouse).filter(
            and_(
                Warehouse.id == warehouse_id,
                Warehouse.organisation_id == org_id,
                Warehouse.is_active == True
            )
        ).first()
        
        if not warehouse:
            raise NotFoundError("Warehouse not found")
        
        if warehouse.is_main_warehouse:
            raise ConflictError("Cannot move the main warehouse")
        
        new_parent = db.session.query(Warehouse).filter(
            and_(
                Warehouse.id == new_parent_warehouse_id,
                Warehouse.organisation_id == org_id,
                Warehouse.is_active == True
            )
        ).first()
        
        if not new_parent:
            raise NotFoundError("New parent warehouse not found")
        
        if warehouse.id == new_parent.id:
            raise ValidationError("A warehouse cannot be its own parent")
        
        # Check for circular relationships
        if warehouse.is_child_of(new_parent.id) or new_parent.is_child_of(warehouse.id):
            raise ConflictError(
                "Cannot move warehouse: would create circular hierarchy"
            )
        
        # Update warehouse and all descendants
        def update_hierarchy(wh, new_level):
            wh.parent_warehouse_id = wh.parent_warehouse_id
            wh.hierarchy_level = new_level
            for child in wh.child_warehouses:
                if child.is_active:
                    update_hierarchy(child, new_level + 1)
        
        warehouse.parent_warehouse_id = new_parent_warehouse_id
        warehouse.hierarchy_level = new_parent.hierarchy_level + 1
        
        # Update descendants
        for child in warehouse.child_warehouses:
            if child.is_active:
                update_hierarchy(child, warehouse.hierarchy_level + 1)
        
        db.session.commit()
        return warehouse

    @staticmethod
    def validate_transfer_path(
        from_warehouse_id: int,
        to_warehouse_id: int,
        org_id: int
    ) -> bool:
        """
        Validate that a transfer between warehouses is allowed.
        
        Business Rules for SAP-like transfers:
        - Main warehouse can transfer to any child directly
        - Child can transfer to parent (main warehouse)
        - Child cannot transfer directly to another child (must go through parent)
        - Both warehouses must be in the same organization
        
        Returns True if transfer is allowed, raises exception if not.
        """
        from_wh = db.session.query(Warehouse).filter(
            and_(
                Warehouse.id == from_warehouse_id,
                Warehouse.organisation_id == org_id,
                Warehouse.is_active == True
            )
        ).first()
        
        to_wh = db.session.query(Warehouse).filter(
            and_(
                Warehouse.id == to_warehouse_id,
                Warehouse.organisation_id == org_id,
                Warehouse.is_active == True
            )
        ).first()
        
        if not from_wh:
            raise NotFoundError("Source warehouse not found")
        if not to_wh:
            raise NotFoundError("Destination warehouse not found")
        
        if from_warehouse_id == to_warehouse_id:
            raise ValidationError("Cannot transfer to the same warehouse")
        
        # Main warehouse can transfer to any child
        if from_wh.is_main_warehouse:
            if to_wh.is_main_warehouse:
                raise ConflictError("Cannot transfer between main warehouses")
            # Verify destination is in the hierarchy
            return True
        
        # Child can transfer to its parent (main warehouse)
        if from_wh.is_child_of(to_warehouse_id):
            return True
        
        # Child can transfer to main warehouse directly
        if to_wh.is_main_warehouse:
            return True
        
        # All other transfer patterns are not allowed (child-to-child must go through main)
        raise ConflictError(
            "Direct transfer between child warehouses is not allowed. "
            "Items must be transferred through the main warehouse."
        )

    @staticmethod
    def get_warehouse_with_hierarchy(warehouse_id: int, org_id: int) -> dict:
        """Get a warehouse with its full hierarchy context"""
        warehouse = db.session.query(Warehouse).filter(
            and_(
                Warehouse.id == warehouse_id,
                Warehouse.organisation_id == org_id
            )
        ).first()
        
        if not warehouse:
            raise NotFoundError("Warehouse not found")
        
        return {
            "id": warehouse.id,
            "name": warehouse.name,
            "code": warehouse.code,
            "address": warehouse.address,
            "is_main": warehouse.is_main_warehouse,
            "warehouse_type": warehouse.warehouse_type,
            "hierarchy_level": warehouse.hierarchy_level,
            "parent_warehouse_id": warehouse.parent_warehouse_id,
            "parent_warehouse": {
                "id": warehouse.parent_warehouse.id,
                "name": warehouse.parent_warehouse.name,
                "code": warehouse.parent_warehouse.code
            } if warehouse.parent_warehouse else None,
            "child_warehouses": [
                {
                    "id": child.id,
                    "name": child.name,
                    "code": child.code,
                    "hierarchy_level": child.hierarchy_level
                }
                for child in warehouse.child_warehouses
                if child.is_active
            ]
        }
