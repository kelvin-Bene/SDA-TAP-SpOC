"""Convert TIMESTAMP columns to TIMESTAMPTZ for proper timezone handling.

Revision ID: 004
Revises: 003
Create Date: 2026-04-01
"""
from typing import Sequence, Union

from alembic import op

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table_name, [columns]) pairs for TIMESTAMP -> TIMESTAMPTZ conversion
TABLES_COLUMNS = [
    ("satellites", ["created_at", "updated_at"]),
    ("observations", ["ob_time", "created_at"]),
    ("state_vectors", ["epoch", "created_at"]),
    ("element_sets", ["epoch", "created_at"]),
    ("datasets", ["time_window_start", "time_window_end", "created_at", "updated_at"]),
    ("submissions", ["created_at", "completed_at"]),
    ("submission_results", ["created_at"]),
    ("events", ["event_time_start", "event_time_end", "labelled_at"]),
    ("feedback", ["created_at", "updated_at"]),
    ("profiles", ["created_at", "updated_at"]),
    ("breakup_events", ["event_date", "cached_at"]),
    ("non_reference_observations", ["obs_time", "created_at"]),
    ("_schema_metadata", ["updated_at"]),
]


def upgrade() -> None:
    for table, columns in TABLES_COLUMNS:
        for col in columns:
            op.execute(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN {col} TYPE TIMESTAMPTZ "
                f"USING {col} AT TIME ZONE 'UTC'"
            )


def downgrade() -> None:
    for table, columns in TABLES_COLUMNS:
        for col in columns:
            op.execute(
                f"ALTER TABLE {table} "
                f"ALTER COLUMN {col} TYPE TIMESTAMP"
            )
