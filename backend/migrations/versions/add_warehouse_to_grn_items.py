"""Add warehouse_id to goods_receipt_items for warehouse routing

Revision ID: add_warehouse_to_grn_items
Revises: add_asset_support_grn
Create Date: 2026-07-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_warehouse_to_grn_items'
down_revision = 'add_asset_support_grn'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    # --- 1. Add warehouse_id column (only if missing) ---
    existing_columns = [col['name'] for col in inspector.get_columns('goods_receipt_items')]
    if 'warehouse_id' not in existing_columns:
        op.add_column(
            'goods_receipt_items',
            sa.Column('warehouse_id', sa.Integer(), nullable=True)
        )

    # --- 2. Add foreign key constraint (only if missing) ---
    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('goods_receipt_items')]
    if 'fk_grn_items_warehouse_id' not in existing_fks:
        op.create_foreign_key(
            'fk_grn_items_warehouse_id',
            'goods_receipt_items',
            'warehouses',
            ['warehouse_id'],
            ['id']
        )

    # --- 3. Add index (only if missing) ---
    existing_indexes = [ix['name'] for ix in inspector.get_indexes('goods_receipt_items')]
    if 'ix_grn_items_warehouse_id' not in existing_indexes:
        op.create_index(
            'ix_grn_items_warehouse_id',
            'goods_receipt_items',
            ['warehouse_id']
        )


def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_indexes = [ix['name'] for ix in inspector.get_indexes('goods_receipt_items')]
    if 'ix_grn_items_warehouse_id' in existing_indexes:
        op.drop_index('ix_grn_items_warehouse_id', table_name='goods_receipt_items')

    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('goods_receipt_items')]
    if 'fk_grn_items_warehouse_id' in existing_fks:
        op.drop_constraint(
            'fk_grn_items_warehouse_id',
            'goods_receipt_items',
            type_='foreignkey'
        )

    existing_columns = [col['name'] for col in inspector.get_columns('goods_receipt_items')]
    if 'warehouse_id' in existing_columns:
        op.drop_column('goods_receipt_items', 'warehouse_id')
