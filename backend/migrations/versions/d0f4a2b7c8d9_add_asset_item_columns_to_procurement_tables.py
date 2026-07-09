"""Add asset-aware columns to procurement and requisition tables

Revision ID: d0f4a2b7c8d9
Revises: add_asset_support_grn
Create Date: 2026-07-07 23:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd0f4a2b7c8d9'
down_revision = 'add_asset_support_grn'
branch_labels = None
depends_on = None


def upgrade():
    for table_name in ['purchase_request_items', 'purchase_order_items', 'requisition_items']:
        op.add_column(table_name, sa.Column('asset_id', sa.Integer(), nullable=True))
        op.add_column(table_name, sa.Column('item_type', sa.String(length=50), nullable=False, server_default='inventory'))

    op.add_column('goods_receipt_items', sa.Column('item_type', sa.String(length=50), nullable=False, server_default='inventory'))

    op.add_column('requisition_items', sa.Column('warehouse_id', sa.Integer(), nullable=True))
    op.add_column('requisition_items', sa.Column('bin_id', sa.Integer(), nullable=True))

    op.add_column('goods_receipt_items', sa.Column('warehouse_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('goods_receipt_items', 'warehouse_id')
    op.drop_column('requisition_items', 'bin_id')
    op.drop_column('requisition_items', 'warehouse_id')
    op.drop_column('goods_receipt_items', 'item_type')

    for table_name in ['purchase_request_items', 'purchase_order_items', 'requisition_items']:
        op.drop_column(table_name, 'item_type')
        op.drop_column(table_name, 'asset_id')
