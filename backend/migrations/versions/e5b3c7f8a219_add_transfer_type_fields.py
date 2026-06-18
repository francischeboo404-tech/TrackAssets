"""Add transfer_type, from_user_id, to_user_id, from_warehouse_id to transfer_requests

Revision ID: e5b3c7f8a219
Revises: 0a72fcd3d5df
Create Date: 2026-06-18

"""
from alembic import op
import sqlalchemy as sa


revision = "e5b3c7f8a219"
down_revision = "0a72fcd3d5df"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("transfer_requests", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "transfer_type",
                sa.String(50),
                nullable=False,
                server_default="department_to_department",
            )
        )
        batch_op.add_column(
            sa.Column("from_user_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("to_user_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("from_warehouse_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_transfer_from_user", "users", ["from_user_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_transfer_to_user", "users", ["to_user_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_transfer_from_warehouse", "warehouses", ["from_warehouse_id"], ["id"]
        )
        batch_op.create_index(
            "ix_transfer_requests_transfer_type", ["transfer_type"]
        )

    # Backfill existing rows — all pre-existing transfers are department-to-department
    op.execute(
        "UPDATE transfer_requests SET transfer_type = 'department_to_department' "
        "WHERE transfer_type IS NULL OR transfer_type = ''"
    )


def downgrade():
    with op.batch_alter_table("transfer_requests", schema=None) as batch_op:
        batch_op.drop_index("ix_transfer_requests_transfer_type")
        batch_op.drop_constraint("fk_transfer_from_warehouse", type_="foreignkey")
        batch_op.drop_constraint("fk_transfer_to_user", type_="foreignkey")
        batch_op.drop_constraint("fk_transfer_from_user", type_="foreignkey")
        batch_op.drop_column("from_warehouse_id")
        batch_op.drop_column("to_user_id")
        batch_op.drop_column("from_user_id")
        batch_op.drop_column("transfer_type")
