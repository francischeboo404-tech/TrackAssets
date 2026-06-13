"""Enhance scan_events for secure tracking audit trail

Revision ID: b2c4e8f1a901
Revises: a8bf43f2b3f3
Create Date: 2026-05-24

"""
from alembic import op
import sqlalchemy as sa


revision = "b2c4e8f1a901"
down_revision = "a8bf43f2b3f3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("inventory_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("qr_code_data", sa.String(length=500), nullable=True)
        )

    with op.batch_alter_table("scan_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_role", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("previous_state", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("new_state", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "validation_status",
                sa.String(length=20),
                nullable=False,
                server_default="verified",
            )
        )
        batch_op.add_column(
            sa.Column("scan_fingerprint", sa.String(length=64), nullable=True)
        )
        batch_op.create_index(
            "ix_scan_events_user_id", ["user_id"], unique=False
        )
        batch_op.create_index(
            "ix_scan_events_scan_fingerprint",
            ["scan_fingerprint"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("inventory_items", schema=None) as batch_op:
        batch_op.drop_column("qr_code_data")

    with op.batch_alter_table("scan_events", schema=None) as batch_op:
        batch_op.drop_index("ix_scan_events_scan_fingerprint")
        batch_op.drop_index("ix_scan_events_user_id")
        batch_op.drop_column("scan_fingerprint")
        batch_op.drop_column("validation_status")
        batch_op.drop_column("new_state")
        batch_op.drop_column("previous_state")
        batch_op.drop_column("user_role")
