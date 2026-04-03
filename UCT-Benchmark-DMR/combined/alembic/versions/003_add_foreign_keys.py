"""Add foreign key constraints with CASCADE delete.

Revision ID: 003
Revises: 002
Create Date: 2026-04-01
"""
from typing import Sequence, Union

from alembic import op

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Foreign keys to create: (constraint_name, source_table, referent_table, local_cols, remote_cols)
FK_DEFINITIONS = [
    ('fk_ds_obs_dataset', 'dataset_observations', 'datasets', ['dataset_id'], ['id']),
    ('fk_ds_ref_dataset', 'dataset_references', 'datasets', ['dataset_id'], ['id']),
    ('fk_submissions_dataset', 'submissions', 'datasets', ['dataset_id'], ['id']),
    ('fk_results_submission', 'submission_results', 'submissions', ['submission_id'], ['id']),
    ('fk_nonref_dataset', 'non_reference_observations', 'datasets', ['dataset_id'], ['id']),
]


def upgrade() -> None:
    for name, source, referent, local_cols, remote_cols in FK_DEFINITIONS:
        op.create_foreign_key(
            name, source, referent,
            local_cols, remote_cols,
            ondelete='CASCADE',
        )


def downgrade() -> None:
    for name, source, _, _, _ in reversed(FK_DEFINITIONS):
        op.drop_constraint(name, source, type_='foreignkey')
