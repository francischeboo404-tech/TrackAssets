"""add_requisition_item_location_columns

Revision ID: b5c6d7e8f901
Revises: ef332df3c6b4
Create Date: 2026-06-22 12:00:00.000000

Add warehouse_id and bin_id columns to requisition_items to persist
selected storage locations for requisitions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c6d7e8f901'
down_revision: Union[str, None] = 'ef332df3c6b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add warehouse_id column
    try:
        op.add_column('requisition_items', sa.Column('warehouse_id', sa.Integer(), nullable=True))
    except Exception:
        pass

    # Add bin_id column
    try:
        op.add_column('requisition_items', sa.Column('bin_id', sa.Integer(), nullable=True))
    except Exception:
        pass

    # Create foreign key constraints if they do not exist
    try:
        op.create_foreign_key('fk_requisition_items_warehouse', 'requisition_items', 'warehouses', ['warehouse_id'], ['id'])
    except Exception:
        pass

    try:
        op.create_foreign_key('fk_requisition_items_bin', 'requisition_items', 'warehouse_bins', ['bin_id'], ['id'])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_constraint('fk_requisition_items_bin', 'requisition_items', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_requisition_items_warehouse', 'requisition_items', type_='foreignkey')
    except Exception:
        pass

    try:
        op.drop_column('requisition_items', 'bin_id')
    except Exception:
        pass
    try:
        op.drop_column('requisition_items', 'warehouse_id')
    except Exception:
        pass
