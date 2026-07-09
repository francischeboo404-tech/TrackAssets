"""Add warehouse_id to goods_receipt_items for warehouse routing

Revision ID: add_warehouse_to_grn_items
Revises: add_asset_support_grn
Create Date: 2026-07-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_warehouse_to_grn_items'
down_revision = 'add_asset_support_grn'
branch_labels = None
depends_on = None


def upgrade():
    # Add warehouse_id column to goods_receipt_items
    op.add_column(
        'goods_receipt_items',
        sa.Column('warehouse_id', sa.Integer(), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_grn_items_warehouse_id',
        'goods_receipt_items',
        'warehouses',
        ['warehouse_id'],
        ['id']
    )
    
    # Add index for faster warehouse queries
    op.create_index(
        'ix_grn_items_warehouse_id',
        'goods_receipt_items',
        ['warehouse_id']
    )


def downgrade():
    # Drop index
    op.drop_index('ix_grn_items_warehouse_id', table_name='goods_receipt_items')
    
    # Drop foreign key
    op.drop_constraint(
        'fk_grn_items_warehouse_id',
        'goods_receipt_items',
        type_='foreignkey'
    )
    
    # Drop column
    op.drop_column('goods_receipt_items', 'warehouse_id')
