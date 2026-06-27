"""add_audit_user_agent_reference

Revision ID: c1a2b3d4e5f6
Revises: 02359c89cba4
Create Date: 2026-06-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = '02359c89cba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns for quick filtering/export
    op.add_column('audit_logs', sa.Column('user_agent', sa.String(length=255), nullable=True))
    op.add_column('audit_logs', sa.Column('reference', sa.String(length=255), nullable=True))

    # Add B-tree indexes for common filters
    op.create_index('ix_audit_logs_user_agent', 'audit_logs', ['user_agent'], unique=False)
    op.create_index('ix_audit_logs_reference', 'audit_logs', ['reference'], unique=False)

    # Add GIN index for JSON search on Postgres (cast to jsonb if needed)
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute('CREATE INDEX ix_audit_logs_details_gin ON audit_logs USING gin ((details::jsonb))')


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # drop the GIN index if it exists
        op.execute('DROP INDEX IF EXISTS ix_audit_logs_details_gin')

    op.drop_index('ix_audit_logs_reference', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_agent', table_name='audit_logs')
    op.drop_column('audit_logs', 'reference')
    op.drop_column('audit_logs', 'user_agent')
