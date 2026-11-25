"""phase_d2_automatic_merge

Revision ID: e0f03779a16e
Revises: d4e5f6a7b8c9
Create Date: 2026-11-25 13:39:41.449215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0f03779a16e'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'merge_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_incident_id', sa.String(length=36), nullable=True),
        sa.Column('target_incident_id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=36), nullable=False),
        sa.Column('matched_report_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=32), nullable=False),
        sa.Column('actor', sa.String(length=150), nullable=False),
        sa.Column('transferred_report_ids', sa.JSON(), nullable=False),
        sa.Column('target_incident_report_ids_before', sa.JSON(), nullable=False),
        sa.Column('source_incident_status_before', sa.String(length=16), nullable=False),
        sa.Column('target_incident_status_before', sa.String(length=16), nullable=False),
        sa.Column('sha256_match', sa.Boolean(), nullable=True),
        sa.Column('phash_hamming_distance', sa.Integer(), nullable=True),
        sa.Column('phash_similarity', sa.Float(), nullable=True),
        sa.Column('text_similarity', sa.Float(), nullable=True),
        sa.Column('geo_distance_meters', sa.Float(), nullable=True),
        sa.Column('category_match', sa.Boolean(), nullable=True),
        sa.Column('candidate_classification', sa.String(length=32), nullable=False),
        sa.Column('heuristic_score', sa.Float(), nullable=True),
        sa.Column('policy_snapshot', sa.JSON(), nullable=False),
        sa.Column('reversed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reversal_merge_event_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['matched_report_id'], ['reports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reversal_merge_event_id'], ['merge_events.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_incident_id'], ['incidents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_incident_id'], ['incidents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_merge_events_report_id'), 'merge_events', ['report_id'], unique=False)
    op.create_index(op.f('ix_merge_events_reversal_merge_event_id'), 'merge_events', ['reversal_merge_event_id'], unique=False)
    op.create_index(op.f('ix_merge_events_source_incident_id'), 'merge_events', ['source_incident_id'], unique=False)
    op.create_index(op.f('ix_merge_events_target_incident_id'), 'merge_events', ['target_incident_id'], unique=False)

    op.create_table(
        'merge_executions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('match_suggestion_id', sa.String(length=36), nullable=False),
        sa.Column('merge_event_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RETRYING', 'SUCCEEDED', 'FAILED', name='merge_execution_status_enum'), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['match_suggestion_id'], ['match_suggestions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merge_event_id'], ['merge_events.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_merge_execution_idempotency_key'),
        sa.UniqueConstraint('match_suggestion_id', name='uq_merge_execution_suggestion'),
    )
    op.create_index(op.f('ix_merge_executions_match_suggestion_id'), 'merge_executions', ['match_suggestion_id'], unique=False)
    op.create_index(op.f('ix_merge_executions_merge_event_id'), 'merge_executions', ['merge_event_id'], unique=False)
    op.create_index(op.f('ix_merge_executions_status'), 'merge_executions', ['status'], unique=False)

    # Incidents: add merge traceability
    with op.batch_alter_table('incidents') as batch_op:
        batch_op.add_column(sa.Column('merged_into_incident_id', sa.String(length=36), nullable=True))
        batch_op.create_index(op.f('ix_incidents_merged_into_incident_id'), ['merged_into_incident_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_incidents_merged_into_incident_id_incidents',
            'incidents',
            ['merged_into_incident_id'],
            ['id'],
            ondelete='SET NULL',
        )

    # Admin audit logs: preserve existing rows, add actor model and merge_event link
    with op.batch_alter_table('admin_audit_logs') as batch_op:
        batch_op.add_column(sa.Column('actor_type', sa.Enum('ADMIN', 'SYSTEM', name='actor_type_enum'), nullable=True))
        batch_op.add_column(sa.Column('system_actor', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('merge_event_id', sa.String(length=36), nullable=True))
        batch_op.alter_column('admin_username', existing_type=sa.VARCHAR(length=150), nullable=True)

    op.execute("UPDATE admin_audit_logs SET actor_type='ADMIN' WHERE actor_type IS NULL AND admin_username IS NOT NULL")
    op.execute("UPDATE admin_audit_logs SET actor_type='SYSTEM', system_actor='legacy' WHERE actor_type IS NULL")

    with op.batch_alter_table('admin_audit_logs') as batch_op:
        batch_op.alter_column('actor_type', existing_type=sa.Enum('ADMIN', 'SYSTEM', name='actor_type_enum'), nullable=False)
        batch_op.create_index(op.f('ix_admin_audit_logs_merge_event_id'), ['merge_event_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_admin_audit_logs_merge_event_id_merge_events',
            'merge_events',
            ['merge_event_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_check_constraint(
            'ck_admin_audit_logs_actor_consistency',
            "(actor_type = 'ADMIN' AND admin_username IS NOT NULL AND system_actor IS NULL) OR "
            "(actor_type = 'SYSTEM' AND admin_username IS NULL AND system_actor IS NOT NULL)",
        )

    # Match suggestions: extend status enum to include AUTO_MERGED/SUPERSEDED
    with op.batch_alter_table('match_suggestions') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.VARCHAR(length=9),
            type_=sa.Enum('PENDING', 'REVIEWED', 'DISMISSED', 'AUTO_MERGED', 'SUPERSEDED', name='suggestion_status_enum'),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('match_suggestions') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('PENDING', 'REVIEWED', 'DISMISSED', 'AUTO_MERGED', 'SUPERSEDED', name='suggestion_status_enum'),
            type_=sa.VARCHAR(length=9),
            existing_nullable=False,
        )

    with op.batch_alter_table('admin_audit_logs') as batch_op:
        batch_op.drop_constraint('ck_admin_audit_logs_actor_consistency', type_='check')
        batch_op.drop_constraint('fk_admin_audit_logs_merge_event_id_merge_events', type_='foreignkey')
        batch_op.drop_index(op.f('ix_admin_audit_logs_merge_event_id'))
        batch_op.alter_column('admin_username', existing_type=sa.VARCHAR(length=150), nullable=False)
        batch_op.drop_column('merge_event_id')
        batch_op.drop_column('system_actor')
        batch_op.drop_column('actor_type')

    with op.batch_alter_table('incidents') as batch_op:
        batch_op.drop_constraint('fk_incidents_merged_into_incident_id_incidents', type_='foreignkey')
        batch_op.drop_index(op.f('ix_incidents_merged_into_incident_id'))
        batch_op.drop_column('merged_into_incident_id')

    op.drop_index(op.f('ix_merge_executions_status'), table_name='merge_executions')
    op.drop_index(op.f('ix_merge_executions_merge_event_id'), table_name='merge_executions')
    op.drop_index(op.f('ix_merge_executions_match_suggestion_id'), table_name='merge_executions')
    op.drop_table('merge_executions')

    op.drop_index(op.f('ix_merge_events_target_incident_id'), table_name='merge_events')
    op.drop_index(op.f('ix_merge_events_source_incident_id'), table_name='merge_events')
    op.drop_index(op.f('ix_merge_events_reversal_merge_event_id'), table_name='merge_events')
    op.drop_index(op.f('ix_merge_events_report_id'), table_name='merge_events')
    op.drop_table('merge_events')
