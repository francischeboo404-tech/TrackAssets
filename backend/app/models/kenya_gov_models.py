from datetime import datetime, timezone
from app import db
from app.types import SafeNumeric

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    parent_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class ItemType(db.Model):
    __tablename__ = 'item_types'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class RolePermission(db.Model):
    __tablename__ = 'role_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    module = db.Column(db.String(100), nullable=False)
    can_create = db.Column(db.Boolean, default=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    can_approve = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class PurchaseRequest(db.Model):
    __tablename__ = 'purchase_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    pr_number = db.Column(db.String(100), nullable=False, unique=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_head_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # warehouse_id: auto-resolved from requester's department on creation
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    status = db.Column(db.String(50), default='pending')
    reason = db.Column(db.Text)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class PurchaseRequestItem(db.Model):
    __tablename__ = 'purchase_request_items'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    pr_id = db.Column(db.Integer, db.ForeignKey('purchase_requests.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    item_type = db.Column(db.String(50), nullable=False, default='inventory')
    quantity = db.Column(db.Integer, nullable=False)
    estimated_cost = db.Column(SafeNumeric(12, 2), nullable=False) # Currency is KES
    justification = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    po_number = db.Column(db.String(100), nullable=False, unique=True)
    pr_id = db.Column(db.Integer, db.ForeignKey('purchase_requests.id'), nullable=True)
    ris_id = db.Column(db.Integer, db.ForeignKey('requisition_slips.id'), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    total_amount = db.Column(SafeNumeric(12, 2), nullable=False, default=0.0) # Currency is KES
    status = db.Column(db.String(50), default='pending')
    approved_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    item_type = db.Column(db.String(50), nullable=False, default='inventory')
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(SafeNumeric(12, 2), nullable=False) # Currency is KES
    total_cost = db.Column(SafeNumeric(12, 2), nullable=False) # Currency is KES
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class CanvassQuote(db.Model):
    __tablename__ = 'canvass_quotes'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    supplier_name = db.Column(db.String(255), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    unit_cost = db.Column(SafeNumeric(12, 2), nullable=False) # Currency is KES
    total_cost = db.Column(SafeNumeric(12, 2), nullable=False) # Currency is KES
    quote_date = db.Column(db.DateTime, nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class GoodsReceiptNote(db.Model):
    __tablename__ = 'goods_receipt_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    grn_number = db.Column(db.String(100), nullable=False, unique=True)
    invoice_number = db.Column(db.String(100), nullable=True)
    delivery_note_number = db.Column(db.String(100), nullable=True)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    received_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    received_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(50), default='quarantine')
    total_quantity = db.Column(db.Integer, default=0)
    # warehouse_id: the warehouse where goods are being received into
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class GoodsReceiptItem(db.Model):
    __tablename__ = 'goods_receipt_items'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    grn_id = db.Column(db.Integer, db.ForeignKey('goods_receipt_notes.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    item_type = db.Column(db.String(50), nullable=False, default='inventory')
    quantity_received = db.Column(db.Integer, nullable=False)
    quantity_accepted = db.Column(db.Integer, default=0)
    quantity_rejected = db.Column(db.Integer, default=0)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    bin_location_id = db.Column(db.Integer, db.ForeignKey('warehouse_bins.id'), nullable=True)
    unit_cost = db.Column(SafeNumeric(12, 2), nullable=False) # Currency is KES
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    warehouse = db.relationship(
        'Warehouse',
        backref='grn_items',
        foreign_keys=[warehouse_id]
    )

class InspectionReport(db.Model):
    __tablename__ = 'inspection_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    iar_number = db.Column(db.String(100), nullable=False, unique=True)
    grn_id = db.Column(db.Integer, db.ForeignKey('goods_receipt_notes.id'), nullable=False)
    inspector_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    inspection_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(50), default='pending')
    comments = db.Column(db.Text)
    quality_certificate = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class StockCard(db.Model):
    __tablename__ = 'stock_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    stock_card_number = db.Column(db.String(100), nullable=False)
    quantity_on_hand = db.Column(db.Integer, default=0)
    last_received_date = db.Column(db.DateTime, nullable=True)
    last_issued_date = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class SuppliesLedgerCard(db.Model):
    __tablename__ = 'supplies_ledger_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    ledger_number = db.Column(db.String(100), nullable=False)
    quantity_on_hand = db.Column(db.Integer, default=0)
    total_value = db.Column(SafeNumeric(12, 2), default=0.0) # KES
    last_received_date = db.Column(db.DateTime, nullable=True)
    last_issued_date = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class RequisitionSlip(db.Model):
    __tablename__ = 'requisition_slips'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    ris_number = db.Column(db.String(100), nullable=False, unique=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_head_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(50), default='pending')
    requested_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    approved_date = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class RequisitionItem(db.Model):
    __tablename__ = 'requisition_items'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    ris_id = db.Column(db.Integer, db.ForeignKey('requisition_slips.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    item_type = db.Column(db.String(50), nullable=False, default='inventory')
    quantity_requested = db.Column(db.Integer, nullable=False)
    quantity_issued = db.Column(db.Integer, default=0)
    unit_cost = db.Column(SafeNumeric(12, 2), nullable=False) # KES
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    bin_id = db.Column(db.Integer, db.ForeignKey('warehouse_bins.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Optional relationships for convenience
    warehouse = db.relationship('Warehouse', foreign_keys=[warehouse_id], lazy=True)
    bin = db.relationship('WarehouseBin', foreign_keys=[bin_id], lazy=True)

class VarianceReport(db.Model):
    __tablename__ = 'variance_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    report_number = db.Column(db.String(100), nullable=False, unique=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    system_quantity = db.Column(db.Integer, nullable=False)
    physical_quantity = db.Column(db.Integer, nullable=False)
    variance = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='open')
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class DisposalRequest(db.Model):
    __tablename__ = 'disposal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    disposal_number = db.Column(db.String(100), nullable=False, unique=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    committee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    total_value = db.Column(SafeNumeric(12, 2), default=0.0) # KES
    status = db.Column(db.String(50), default='pending')
    approved_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class DisposalItem(db.Model):
    __tablename__ = 'disposal_items'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    disposal_id = db.Column(db.Integer, db.ForeignKey('disposal_requests.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
