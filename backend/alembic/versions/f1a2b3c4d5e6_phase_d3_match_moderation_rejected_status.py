"""phase d3 match moderation rejected status

Revision ID: f1a2b3c4d5e6
Revises: e0f03779a16e
Create Date: 2026-11-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e0f03779a16e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TYPE suggestionstatusenum ADD VALUE IF NOT EXISTS 'rejected'")
    else:
        # SQLite stores enums as VARCHAR; SQLAlchemy Enum(check constraint) is updated in models.
        # Existing rows remain valid. No table rebuild needed.
        pass


def downgrade() -> None:
    # Removing enum values is non-trivial across dialects; keep downgrade as no-op for safety.
    pass
