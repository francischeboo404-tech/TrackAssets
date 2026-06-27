"""Merge inventory and transfer branches

Revision ID: 64e4bc7747e2
Revises: 4f7b6456ff12, e5b3c7f8a219
Create Date: 2026-06-25 20:50:31.177012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64e4bc7747e2'
down_revision: Union[str, None] = ('4f7b6456ff12', 'e5b3c7f8a219')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
