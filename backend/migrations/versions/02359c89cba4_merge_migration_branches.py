"""merge_migration_branches

Revision ID: 02359c89cba4
Revises: 7b78fb2f3dda, b2c4e8f1a901
Create Date: 2026-05-24 16:03:46.084860

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02359c89cba4'
down_revision: Union[str, None] = ('7b78fb2f3dda', 'b2c4e8f1a901')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
