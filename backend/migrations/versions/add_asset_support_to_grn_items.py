"""Add asset_id and item_type columns to goods_receipt_items

Revision ID: add_asset_support_grn
Revises: 06_add_warehouse_id_inventory, add_employee_item_tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "add_asset_support_grn"
down_revision = (
    "06_add_warehouse_id_inventory",
    "add_employee_item_tracking",
)
branch_labels = None
depends_on = None


def column_exists(inspector, table, column):
    return column in {c["name"] for c in inspector.get_columns(table)}


def fk_exists(inspector, table, constrained_column):
    for fk in inspector.get_foreign_keys(table):
        if constrained_column in fk.get("constrained_columns", []):
            return True
    return False


def upgrade():

    conn = op.get_bind()
    inspector = inspect(conn)

    if not inspector.has_table("goods_receipt_items"):
        return

    columns = {c["name"] for c in inspector.get_columns("goods_receipt_items")}

    with op.batch_alter_table("goods_receipt_items") as batch:

        if "asset_id" not in columns:
            batch.add_column(
                sa.Column(
                    "asset_id",
                    sa.Integer(),
                    nullable=True,
                )
            )

        if "item_type" not in columns:
            batch.add_column(
                sa.Column(
                    "item_type",
                    sa.String(50),
                    nullable=True,
                    server_default="inventory",
                )
            )

    inspector = inspect(conn)

    if not fk_exists(inspector, "goods_receipt_items", "asset_id"):
        op.create_foreign_key(
            "fk_goods_receipt_items_asset_id",
            "goods_receipt_items",
            "assets",
            ["asset_id"],
            ["id"],
        )

    if column_exists(inspector, "goods_receipt_items", "item_type"):
        op.execute("""
            UPDATE goods_receipt_items
            SET item_type='inventory'
            WHERE item_type IS NULL
        """)

        op.alter_column(
            "goods_receipt_items",
            "item_type",
            existing_type=sa.String(50),
            nullable=False,
            server_default="inventory",
        )

    item_columns = {
        c["name"]: c
        for c in inspector.get_columns("goods_receipt_items")
    }

    if "item_id" in item_columns:

        nullable = item_columns["item_id"]["nullable"]

        if nullable is False:
            op.alter_column(
                "goods_receipt_items",
                "item_id",
                existing_type=sa.Integer(),
                nullable=True,
            )


def downgrade():

    conn = op.get_bind()
    inspector = inspect(conn)

    if not inspector.has_table("goods_receipt_items"):
        return

    columns = {c["name"] for c in inspector.get_columns("goods_receipt_items")}

    fks = inspector.get_foreign_keys("goods_receipt_items")

    for fk in fks:
        if "asset_id" in fk.get("constrained_columns", []):
            op.drop_constraint(
                fk["name"],
                "goods_receipt_items",
                type_="foreignkey",
            )

    with op.batch_alter_table("goods_receipt_items") as batch:

        if "item_type" in columns:
            batch.drop_column("item_type")

        if "asset_id" in columns:
            batch.drop_column("asset_id")
