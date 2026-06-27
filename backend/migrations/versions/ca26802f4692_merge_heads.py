"""merge heads

Revision ID: ca26802f4692
Revises: d2e3f4g5h6i7, ef332df3c6b4, c3d4e5f6g7h8, a9b8c7d6e5f4
Create Date: 2026-06-21 23:41:05.302225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca26802f4692'
down_revision: Union[str, None] = ('d2e3f4g5h6i7', 'ef332df3c6b4', 'c3d4e5f6g7h8', 'a9b8c7d6e5f4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
