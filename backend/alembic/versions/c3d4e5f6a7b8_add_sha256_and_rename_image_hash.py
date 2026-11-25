"""add sha256 and rename image_hash to phash

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("sha256_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("phash_size", sa.Integer(), nullable=True))
        batch_op.alter_column("image_hash", new_column_name="phash")

    with op.batch_alter_table("reports") as batch_op:
        batch_op.create_index(op.f("ix_reports_sha256_hash"), ["sha256_hash"], unique=False)

    # Backfill phash_size for existing rows (legacy pHash was 64-bit / 8x8).
    op.execute("UPDATE reports SET phash_size = 8 WHERE phash_size IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_index(op.f("ix_reports_sha256_hash"))
    with op.batch_alter_table("reports") as batch_op:
        batch_op.alter_column("phash", new_column_name="image_hash")
        batch_op.drop_column("phash_size")
        batch_op.drop_column("sha256_hash")
