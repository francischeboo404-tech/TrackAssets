"""Add warehouse_id columns to all multi-warehouse tables

Revision ID: 07_add_warehouse_id_multiwarehouse
Revises: add_warehouse_to_grn_items, d0f4a2b7c8d9
Create Date: 2026-07-08 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


revision: str = '07_add_warehouse_id_multiwarehouse'
down_revision = ('add_warehouse_to_grn_items', 'd0f4a2b7c8d9')
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    return column in [c['name'] for c in insp.get_columns(table)]


def _add_column_safe(table: str, column_def) -> None:
    if not _column_exists(table, column_def.name):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(column_def)


def upgrade() -> None:
    _add_column_safe('audit_logs', sa.Column('warehouse_id', sa.Integer(), nullable=True))
    _add_column_safe('departments', sa.Column('warehouse_id', sa.Integer(), nullable=True))
    _add_column_safe('purchase_requests', sa.Column('warehouse_id', sa.Integer(), nullable=True))
    _add_column_safe('goods_receipt_notes', sa.Column('warehouse_id', sa.Integer(), nullable=True))

    bind = op.get_bind()
    insp = Inspector.from_engine(bind)

    def _create_index_safe(name, table, columns):
        existing = [ix['name'] for ix in insp.get_indexes(table)]
        if name not in existing:
            try:
                op.create_index(name, table, columns)
            except Exception:
                pass

    _create_index_safe('ix_audit_logs_warehouse_id', 'audit_logs', ['warehouse_id'])
    _create_index_safe('ix_departments_warehouse_id', 'departments', ['warehouse_id'])
    _create_index_safe('ix_purchase_requests_warehouse_id', 'purchase_requests', ['warehouse_id'])


def downgrade() -> None:
    for table, col, idx in [
        ('audit_logs', 'warehouse_id', 'ix_audit_logs_warehouse_id'),
        ('departments', 'warehouse_id', 'ix_departments_warehouse_id'),
        ('purchase_requests', 'warehouse_id', 'ix_purchase_requests_warehouse_id'),
    ]:
        try:
            op.drop_index(idx, table_name=table)
        except Exception:
            pass
        try:
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_column(col)
        except Exception:
            pass
