"""fix suggestion status enum labels for postgresql

Revision ID: g1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-11-25 00:00:00.000000

Idempotent corrective migration for PostgreSQL databases that may have applied
earlier broken suggestion_status_enum migrations. SQLite is a no-op because
SQLAlchemy enums are stored as VARCHAR there.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "g1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REQUIRED_LABELS = ["PENDING", "REVIEWED", "DISMISSED", "REJECTED", "AUTO_MERGED", "SUPERSEDED"]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Idempotent: add any missing labels. Do not remove or rename labels.
    # Labels are hardcoded constants; literals are required by ALTER TYPE ADD VALUE.
    for label in REQUIRED_LABELS:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'suggestion_status_enum') THEN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_enum e
                        JOIN pg_type t ON t.oid = e.enumtypid
                        WHERE t.typname = 'suggestion_status_enum' AND e.enumlabel = '{label}'
                    ) THEN
                        EXECUTE 'ALTER TYPE suggestion_status_enum ADD VALUE ''{label}''';
                    END IF;
                END IF;
            END
            $$;
            """
        )


def downgrade() -> None:
    # Removing enum labels in PostgreSQL is non-trivial and unsafe for existing data.
    pass
