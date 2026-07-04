"""Add warehouse_id to inventory_items table

Revision ID: 06_add_warehouse_id_inventory
Revises: 05_add_dept_metadata
Create Date: 2026-07-01 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06_add_warehouse_id_inventory'
down_revision: Union[str, None] = '05_add_dept_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add warehouse_id column to inventory_items (nullable FK to warehouses)
    with op.batch_alter_table('inventory_items', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('warehouse_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_inventory_items_warehouse_id',
            'warehouses',
            ['warehouse_id'],
            ['id']
        )
        batch_op.create_index('ix_inventory_items_warehouse_id', ['warehouse_id'])


def downgrade() -> None:
    with op.batch_alter_table('inventory_items', schema=None) as batch_op:
        try:
            batch_op.drop_index('ix_inventory_items_warehouse_id')
        except Exception:
            pass
        try:
            batch_op.drop_constraint('fk_inventory_items_warehouse_id', type_='foreignkey')
        except Exception:
            pass
        try:
            batch_op.drop_column('warehouse_id')
        except Exception:
            pass
