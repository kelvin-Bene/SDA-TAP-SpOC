"""Add user_id column to submissions table.

Revision ID: 002
Revises: 001
Create Date: 2026-04-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('submissions', sa.Column('user_id', sa.String(255), nullable=True))
    op.create_index('idx_submissions_user', 'submissions', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_submissions_user', table_name='submissions')
    op.drop_column('submissions', 'user_id')
