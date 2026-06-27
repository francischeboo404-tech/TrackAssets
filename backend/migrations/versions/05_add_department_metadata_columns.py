"""Add department metadata fields

Revision ID: 05_add_dept_metadata
Revises: 04_fix_inventory_column_names
Create Date: 2026-06-26 12:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '05_add_dept_metadata'
down_revision: Union[str, None] = '04_fix_inventory_column_names'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'departments',
        sa.Column('allowed_category_ids', sa.JSON(), nullable=True),
    )
    op.add_column(
        'departments',
        sa.Column('allowed_inventory_item_types', sa.JSON(), nullable=True),
    )
    op.add_column(
        'departments',
        sa.Column('allowed_asset_types', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('departments', 'allowed_asset_types')
    op.drop_column('departments', 'allowed_inventory_item_types')
    op.drop_column('departments', 'allowed_category_ids')
