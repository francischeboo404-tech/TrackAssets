"""Add asset assignment fields and overhaul status values

Revision ID: c3f1d9e2a705
Revises: b2c4e8f1a901
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa


revision = "c3f1d9e2a705"
down_revision = "02359c89cba4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("assigned_to_user_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("assigned_department_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("assignment_date", sa.Date(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("return_date", sa.Date(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_assets_assigned_to_user_id",
            "users",
            ["assigned_to_user_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_assets_assigned_department_id",
            "departments",
            ["assigned_department_id"],
            ["id"],
        )

    # Migrate existing status values to new model
    # SQLite: plain UPDATE (no ALTER TYPE needed)
    # PostgreSQL: status column is VARCHAR(50), so UPDATE works directly
    op.execute(
        "UPDATE assets SET status = 'available' WHERE status IN ('requested', 'approved', 'rejected')"
    )
    op.execute(
        "UPDATE assets SET status = 'assigned' WHERE status = 'in_use'"
    )
    op.execute(
        "UPDATE assets SET status = 'under_maintenance' WHERE status = 'maintenance'"
    )


def downgrade():
    # Reverse status migration
    op.execute(
        "UPDATE assets SET status = 'requested' WHERE status = 'available'"
    )
    op.execute(
        "UPDATE assets SET status = 'in_use' WHERE status = 'assigned'"
    )
    op.execute(
        "UPDATE assets SET status = 'maintenance' WHERE status = 'under_maintenance'"
    )

    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_constraint("fk_assets_assigned_to_user_id", type_="foreignkey")
        batch_op.drop_constraint("fk_assets_assigned_department_id", type_="foreignkey")
        batch_op.drop_column("return_date")
        batch_op.drop_column("assignment_date")
        batch_op.drop_column("assigned_department_id")
        batch_op.drop_column("assigned_to_user_id")
