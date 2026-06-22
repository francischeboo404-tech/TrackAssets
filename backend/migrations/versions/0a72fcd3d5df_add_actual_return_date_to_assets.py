"""Add actual_return_date to assets

Revision ID: 0a72fcd3d5df
Revises: c3f1d9e2a705
Create Date: 2026-06-18

"""
from alembic import op
import sqlalchemy as sa


revision = "0a72fcd3d5df"
down_revision = "c3f1d9e2a705"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("actual_return_date", sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_column("actual_return_date")
