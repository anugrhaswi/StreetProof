"""add multisignal fields to match_suggestions

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-25 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("match_suggestions") as batch_op:
        batch_op.add_column(sa.Column("sha256_match", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("phash_hamming_distance", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("phash_similarity", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("text_similarity", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("geo_distance_meters", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("category_match", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("candidate_classification", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("match_suggestions") as batch_op:
        batch_op.drop_column("candidate_classification")
        batch_op.drop_column("category_match")
        batch_op.drop_column("geo_distance_meters")
        batch_op.drop_column("text_similarity")
        batch_op.drop_column("phash_similarity")
        batch_op.drop_column("phash_hamming_distance")
        batch_op.drop_column("sha256_match")
