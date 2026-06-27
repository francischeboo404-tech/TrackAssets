"""Merge multiple heads

Revision ID: 32e4405bb5c6
Revises: b5c6d7e8f901, ca26802f4692
Create Date: 2026-06-22 16:57:21.140867

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32e4405bb5c6'
down_revision: Union[str, None] = ('b5c6d7e8f901', 'ca26802f4692')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
