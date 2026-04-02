"""Add UNIQUE constraint on datasets(code, version) pair.

Prevents duplicate dataset entries with the same code and version number.
The code column alone is NOT unique because it is shared across version
families (a v2 regeneration shares the same code as v1).

Revision ID: 006
Revises: 005
Create Date: 2026-04-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean up any existing violations before adding constraint.
    # Keep the newest row (highest id) for each (code, version) pair.
    op.execute(
        "DELETE FROM datasets d1 "
        "USING datasets d2 "
        "WHERE d1.code = d2.code "
        "AND d1.version = d2.version "
        "AND d1.code IS NOT NULL "
        "AND d1.id < d2.id"
    )

    # Add composite unique constraint
    op.execute(
        "ALTER TABLE datasets "
        "ADD CONSTRAINT uq_datasets_code_version "
        "UNIQUE (code, version)"
    )

    # Index on code for version tree lookups
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_datasets_code ON datasets(code)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_datasets_code")
    op.execute(
        "ALTER TABLE datasets "
        "DROP CONSTRAINT IF EXISTS uq_datasets_code_version"
    )
