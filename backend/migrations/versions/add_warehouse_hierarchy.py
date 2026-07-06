"""Add warehouse hierarchy support (parent_warehouse_id, is_main_warehouse, etc.)

Revision ID: add_warehouse_hierarchy
Revises: 
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_warehouse_hierarchy'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add hierarchy columns to warehouses table
    op.add_column('warehouses', sa.Column('parent_warehouse_id', sa.Integer(), nullable=True))
    op.add_column('warehouses', sa.Column('is_main_warehouse', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('warehouses', sa.Column('warehouse_type', sa.String(50), nullable=False, server_default='storage_facility'))
    op.add_column('warehouses', sa.Column('hierarchy_level', sa.Integer(), nullable=False, server_default='0'))
    
    # Create foreign key for parent_warehouse_id (self-referential)
    op.create_foreign_key(
        'fk_warehouses_parent_warehouse_id',
        'warehouses', 'warehouses',
        ['parent_warehouse_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes for performance
    op.create_index('ix_warehouses_parent_id', 'warehouses', ['parent_warehouse_id'])
    op.create_index('ix_warehouses_is_main', 'warehouses', ['is_main_warehouse'])
    op.create_index('ix_warehouses_warehouse_type', 'warehouses', ['warehouse_type'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_warehouses_warehouse_type', table_name='warehouses')
    op.drop_index('ix_warehouses_is_main', table_name='warehouses')
    op.drop_index('ix_warehouses_parent_id', table_name='warehouses')
    
    # Drop foreign key
    op.drop_constraint('fk_warehouses_parent_warehouse_id', 'warehouses', type_='foreignkey')
    
    # Drop columns
    op.drop_column('warehouses', 'hierarchy_level')
    op.drop_column('warehouses', 'warehouse_type')
    op.drop_column('warehouses', 'is_main_warehouse')
    op.drop_column('warehouses', 'parent_warehouse_id')
