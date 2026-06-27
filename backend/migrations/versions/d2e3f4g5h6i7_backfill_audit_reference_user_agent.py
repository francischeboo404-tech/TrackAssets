"""backfill_audit_reference_user_agent

Revision ID: d2e3f4g5h6i7
Revises: c1a2b3d4e5f6
Create Date: 2026-06-20 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4g5h6i7'
down_revision: Union[str, None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    # For Postgres use json extraction with ->>
    if dialect == 'postgresql':
        op.execute(
            """
            UPDATE audit_logs
            SET reference = details->>'reference',
                user_agent = details->>'user_agent'
            WHERE details IS NOT NULL
            """
        )
    # For SQLite (and other JSON1-enabled engines), use json_extract
    elif dialect in ('sqlite', 'pysqlite'):
        op.execute(
            """
            UPDATE audit_logs
            SET reference = json_extract(details, '$.reference'),
                user_agent = json_extract(details, '$.user_agent')
            WHERE details IS NOT NULL
            """
        )
    else:
        # Best-effort: try a generic JSON_EXTRACT if available
        try:
            op.execute(
                """
                UPDATE audit_logs
                SET reference = json_extract(details, '$.reference'),
                    user_agent = json_extract(details, '$.user_agent')
                WHERE details IS NOT NULL
                """
            )
        except Exception:
            # If the dialect doesn't support JSON functions, leave rows as-is
            pass


def downgrade() -> None:
    # No-op: do not remove backfilled values on downgrade
    pass
