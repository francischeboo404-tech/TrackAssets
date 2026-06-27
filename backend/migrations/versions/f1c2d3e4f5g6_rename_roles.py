"""Rename internal roles to Kenyan Government roles

Revision ID: f1c2d3e4f5g6
Revises: 02359c89cba4
Create Date: 2026-06-16 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1c2d3e4f5g6'
down_revision: Union[str, None] = '02359c89cba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename staff -> logistics_officer
    op.execute("UPDATE users SET role = 'logistics_officer' WHERE role = 'staff'")
    
    # Rename dept_head -> procurement_officer
    op.execute("UPDATE users SET role = 'procurement_officer' WHERE role = 'dept_head'")
    
    # Rename viewer -> employee
    op.execute("UPDATE users SET role = 'employee' WHERE role = 'viewer'")


def downgrade() -> None:
    # Rename employee -> viewer
    op.execute("UPDATE users SET role = 'viewer' WHERE role = 'employee'")
    
    # Rename procurement_officer -> dept_head
    op.execute("UPDATE users SET role = 'dept_head' WHERE role = 'procurement_officer'")
    
    # Rename logistics_officer -> staff
    op.execute("UPDATE users SET role = 'staff' WHERE role = 'logistics_officer'")
