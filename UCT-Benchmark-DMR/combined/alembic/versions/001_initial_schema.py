"""Initial schema baseline.

This migration represents the existing database schema as of v2.0.0.
It does NOT create tables -- they already exist. This establishes
the Alembic version baseline so future migrations work correctly.

Run `alembic stamp head` to mark an existing database as up-to-date.

Revision ID: 001
Revises: None
Create Date: 2026-04-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: tables already exist in production.

    This migration serves as the baseline. The actual schema is defined in:
    uct_benchmark/database/schema_postgres.sql

    Tables: _schema_metadata, satellites, observations, state_vectors,
    element_sets, datasets, dataset_observations, dataset_references,
    submissions, submission_results, jobs, event_types, events,
    event_observations, feedback
    """
    pass


def downgrade() -> None:
    """Cannot downgrade past the initial schema."""
    raise RuntimeError("Cannot downgrade past the initial schema baseline")
