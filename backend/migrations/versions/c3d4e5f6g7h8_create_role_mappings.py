"""create_role_mappings

Revision ID: c3d4e5f6g7h8
Revises: 02359c89cba4
Create Date: 2026-06-21 18:30:00.000000

Create role_mappings table to persist role labels and permission lists.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = '02359c89cba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create role_mappings table if it does not exist
    op.create_table(
        'role_mappings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organisation_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('role', sa.String(length=100), nullable=False, unique=True),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
    )


def downgrade() -> None:
    try:
        op.drop_table('role_mappings')
    except Exception:
        pass
