"""Enhance inventory master data with procurement, traceability, and batch tracking fields

Revision ID: 03_enhance_inventory_master_data
Revises: 32e4405bb5c6
Create Date: 2026-06-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03_enhance_inventory_master_data'
down_revision: Union[str, None] = '64e4bc7747e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to inventory_items
    # Note: category_id, created_by, updated_by already exist from ef332df3c6b4
    with op.batch_alter_table('inventory_items', schema=None) as batch_op:
        # New Item Identification fields
        batch_op.add_column(sa.Column('item_type', sa.String(length=50), nullable=True, server_default='consumable'))
        batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=True, server_default='active'))
        
        # New Procurement Data
        batch_op.add_column(sa.Column('preferred_supplier_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('supplier_item_reference', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('purchase_cost', sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column('last_purchase_cost', sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column('tax_category', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('lead_time_days', sa.Integer(), nullable=True, server_default='7'))
        
        # New Inventory Control Data (global defaults)
        batch_op.add_column(sa.Column('min_stock_level', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('max_stock_level', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('safety_stock', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('opening_stock', sa.Integer(), nullable=True, server_default='0'))
        
        # New Traceability Data
        batch_op.add_column(sa.Column('batch_tracking', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('serial_tracking', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('expiry_tracking', sa.Boolean(), nullable=True, server_default='false'))
        
        # Foreign keys
        batch_op.create_foreign_key('fk_inventory_preferred_supplier', 'suppliers', ['preferred_supplier_id'], ['id'])
        
        # Indexes for performance
        batch_op.create_index('ix_inventory_item_type', ['organisation_id', 'item_type'])
        batch_op.create_index('ix_inventory_status', ['organisation_id', 'status'])
        batch_op.create_index('ix_inventory_preferred_supplier', ['preferred_supplier_id'])
    
    # Create inventory_batches table
    op.create_table('inventory_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organisation_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('batch_number', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warehouse_id', sa.Integer(), nullable=True),
        sa.Column('received_date', sa.DateTime(), nullable=False),
        sa.Column('manufacture_date', sa.DateTime(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint('quantity >= 0', name='ck_batch_quantity_nonneg'),
        sa.ForeignKeyConstraint(['organisation_id'], ['organizations.id'], name='fk_batch_org'),
        sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], name='fk_batch_item'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name='fk_batch_warehouse'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], name='fk_batch_supplier'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_batch_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_batch_updated_by'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'item_id', 'batch_number', name='uq_batch_org_item_number')
    )
    
    # Indexes for inventory_batches
    op.create_index('ix_batch_org_id', 'inventory_batches', ['organisation_id'])
    op.create_index('ix_batch_item_id', 'inventory_batches', ['item_id'])
    op.create_index('ix_batch_warehouse_id', 'inventory_batches', ['warehouse_id'])
    op.create_index('ix_batch_supplier_id', 'inventory_batches', ['supplier_id'])
    op.create_index('ix_batch_status', 'inventory_batches', ['status'])
    op.create_index('ix_batch_expiry_date', 'inventory_batches', ['expiry_date'])
    op.create_index('ix_batch_org_status_expiry', 'inventory_batches', ['organisation_id', 'status', 'expiry_date'])


def downgrade() -> None:
    # Drop indexes and batch table
    try:
        op.drop_index('ix_batch_org_status_expiry', table_name='inventory_batches')
        op.drop_index('ix_batch_expiry_date', table_name='inventory_batches')
        op.drop_index('ix_batch_status', table_name='inventory_batches')
        op.drop_index('ix_batch_supplier_id', table_name='inventory_batches')
        op.drop_index('ix_batch_warehouse_id', table_name='inventory_batches')
        op.drop_index('ix_batch_item_id', table_name='inventory_batches')
        op.drop_index('ix_batch_org_id', table_name='inventory_batches')
        op.drop_table('inventory_batches')
    except Exception:
        pass  # Table may not exist if upgrade failed
    
    # Drop columns and indexes from inventory_items
    # Try both old (_enabled suffix) and new (no suffix) column names
    with op.batch_alter_table('inventory_items', schema=None) as batch_op:
        try:
            batch_op.drop_index('ix_inventory_preferred_supplier')
        except Exception:
            pass
        try:
            batch_op.drop_index('ix_inventory_status')
        except Exception:
            pass
        try:
            batch_op.drop_index('ix_inventory_item_type')
        except Exception:
            pass
        try:
            batch_op.drop_constraint('fk_inventory_preferred_supplier', type_='foreignkey')
        except Exception:
            pass
        
        # Try to drop columns with both naming conventions
        columns_to_drop = [
            'expiry_tracking_enabled', 'expiry_tracking',
            'serial_tracking_enabled', 'serial_tracking',
            'batch_tracking_enabled', 'batch_tracking',
            'opening_stock', 'maximum_stock_level', 'minimum_stock_level',
            'max_stock_level', 'min_stock_level', 'safety_stock',
            'lead_time_days', 'tax_category', 'last_purchase_cost',
            'purchase_cost', 'supplier_item_reference', 'preferred_supplier_id',
            'status', 'item_type'
        ]
        for col in columns_to_drop:
            try:
                batch_op.drop_column(col)
            except Exception:
                pass  # Column may not exist
