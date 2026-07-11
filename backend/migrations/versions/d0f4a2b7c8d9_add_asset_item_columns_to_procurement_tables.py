"""Add asset-aware columns to procurement and requisition tables

Revision ID: d0f4a2b7c8d9
Revises: add_asset_support_grn
Create Date: 2026-07-07 23:55:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "d0f4a2b7c8d9"
down_revision = "add_asset_support_grn"
branch_labels = None
depends_on = None

def _column_exists(inspector, table_name, column_name):
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    # -------------------------------------------------------
    # purchase_request_items
    # -------------------------------------------------------
    if inspector.has_table("purchase_request_items"):
        with op.batch_alter_table("purchase_request_items") as batch_op:

            if not _column_exists(inspector, "purchase_request_items", "asset_id"):
                batch_op.add_column(
                    sa.Column("asset_id", sa.Integer(), nullable=True)
                )

            if not _column_exists(inspector, "purchase_request_items", "item_type"):
                batch_op.add_column(
                    sa.Column(
                        "item_type",
                        sa.String(50),
                        nullable=False,
                        server_default="inventory",
                    )
                )

    # -------------------------------------------------------
    # purchase_order_items
    # -------------------------------------------------------
    if inspector.has_table("purchase_order_items"):
        with op.batch_alter_table("purchase_order_items") as batch_op:

            if not _column_exists(inspector, "purchase_order_items", "asset_id"):
                batch_op.add_column(
                    sa.Column("asset_id", sa.Integer(), nullable=True)
                )

            if not _column_exists(inspector, "purchase_order_items", "item_type"):
                batch_op.add_column(
                    sa.Column(
                        "item_type",
                        sa.String(50),
                        nullable=False,
                        server_default="inventory",
                    )
                )

    # -------------------------------------------------------
    # requisition_items
    # -------------------------------------------------------
    if inspector.has_table("requisition_items"):
        with op.batch_alter_table("requisition_items") as batch_op:

            if not _column_exists(inspector, "requisition_items", "asset_id"):
                batch_op.add_column(
                    sa.Column("asset_id", sa.Integer(), nullable=True)
                )

            if not _column_exists(inspector, "requisition_items", "item_type"):
                batch_op.add_column(
                    sa.Column(
                        "item_type",
                        sa.String(50),
                        nullable=False,
                        server_default="inventory",
                    )
                )

            if not _column_exists(inspector, "requisition_items", "warehouse_id"):
                batch_op.add_column(
                    sa.Column("warehouse_id", sa.Integer(), nullable=True)
                )

            if not _column_exists(inspector, "requisition_items", "bin_id"):
                batch_op.add_column(
                    sa.Column("bin_id", sa.Integer(), nullable=True)
                )

    # -------------------------------------------------------
    # goods_receipt_items
    # -------------------------------------------------------
    if inspector.has_table("goods_receipt_items"):
        with op.batch_alter_table("goods_receipt_items") as batch_op:

            if not _column_exists(inspector, "goods_receipt_items", "item_type"):
                batch_op.add_column(
                    sa.Column(
                        "item_type",
                        sa.String(50),
                        nullable=False,
                        server_default="inventory",
                    )
                )

            if not _column_exists(inspector, "goods_receipt_items", "warehouse_id"):
                batch_op.add_column(
                    sa.Column("warehouse_id", sa.Integer(), nullable=True)
                )

def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    grn_columns = [c["name"] for c in inspector.get_columns("goods_receipt_items")]
    req_columns = [c["name"] for c in inspector.get_columns("requisition_items")]

    if "warehouse_id" in grn_columns:
        op.drop_column("goods_receipt_items", "warehouse_id")

    if "bin_id" in req_columns:
        op.drop_column("requisition_items", "bin_id")

    if "warehouse_id" in req_columns:
        op.drop_column("requisition_items", "warehouse_id")

    if "item_type" in grn_columns:
        op.drop_column("goods_receipt_items", "item_type")

    for table in [
        "purchase_request_items",
        "purchase_order_items",
        "requisition_items",
    ]:
        cols = [c["name"] for c in inspector.get_columns(table)]

        if "item_type" in cols:
            op.drop_column(table, "item_type")

        if "asset_id" in cols:
            op.drop_column(table, "asset_id")
