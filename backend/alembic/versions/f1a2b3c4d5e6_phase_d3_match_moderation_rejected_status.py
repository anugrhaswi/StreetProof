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
        # Correct type name and label case. SQLAlchemy persists enum member names.
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'suggestion_status_enum') THEN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_enum e
                        JOIN pg_type t ON t.oid = e.enumtypid
                        WHERE t.typname = 'suggestion_status_enum' AND e.enumlabel = 'REJECTED'
                    ) THEN
                        ALTER TYPE suggestion_status_enum ADD VALUE 'REJECTED';
                    END IF;
                END IF;
            END
            $$;
            """
        )
    else:
        # SQLite stores enums as VARCHAR; SQLAlchemy Enum(check constraint) is updated in models.
        # Existing rows remain valid. No table rebuild needed.
        pass


def downgrade() -> None:
    # Removing enum values is non-trivial across dialects; keep downgrade as no-op for safety.
    pass
