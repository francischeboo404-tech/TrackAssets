"""add_audit_module

Revision ID: a9b8c7d6e5f4
Revises: c1a2b3d4e5f6
Create Date: 2026-06-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('audit_logs', sa.Column('module', sa.String(length=100), nullable=True))
    op.create_index('ix_audit_logs_module', 'audit_logs', ['module'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_audit_logs_module', table_name='audit_logs')
    op.drop_column('audit_logs', 'module')
