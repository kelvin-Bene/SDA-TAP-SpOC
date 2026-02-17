"""Tests for the DuckDB-to-PostgreSQL migration utilities.

These tests exercise the helper functions from the migration script
without requiring live DuckDB or PostgreSQL connections.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the scripts directory is importable
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "scripts")
)
from migrate_duckdb_to_postgres import (
    JSON_COLUMNS,
    MIGRATION_ORDER,
    TABLE_ORDER,
    convert_json_columns,
    get_table_columns,
    get_table_count,
    migrate_table,
    reset_sequences,
    verify_migration,
)


# ============================================================
# Migration Order
# ============================================================


class TestMigrationOrder:
    """Tests for the TABLE_ORDER/MIGRATION_ORDER constant."""

    def test_migration_order_length(self):
        """There should be exactly 20 tables in the migration order."""
        assert len(MIGRATION_ORDER) == 20

    def test_migration_order_alias(self):
        """MIGRATION_ORDER should be an alias for TABLE_ORDER."""
        assert MIGRATION_ORDER is TABLE_ORDER

    def test_migration_order_starts_with_data_sources(self):
        """data_sources should be the first table migrated."""
        assert MIGRATION_ORDER[0] == "data_sources"

    def test_migration_order_ends_with_credentials(self):
        """credentials should be the last table migrated."""
        assert MIGRATION_ORDER[-1] == "credentials"

    def test_data_sources_before_observations(self):
        """data_sources must come before observations (FK dependency)."""
        ds_idx = MIGRATION_ORDER.index("data_sources")
        obs_idx = MIGRATION_ORDER.index("observations")
        assert ds_idx < obs_idx

    def test_satellites_before_state_vectors(self):
        """satellites must come before state_vectors (FK dependency)."""
        sat_idx = MIGRATION_ORDER.index("satellites")
        sv_idx = MIGRATION_ORDER.index("state_vectors")
        assert sat_idx < sv_idx

    def test_datasets_before_dataset_observations(self):
        """datasets must come before dataset_observations (FK dependency)."""
        ds_idx = MIGRATION_ORDER.index("datasets")
        dso_idx = MIGRATION_ORDER.index("dataset_observations")
        assert ds_idx < dso_idx

    def test_submissions_before_submission_results(self):
        """submissions must come before submission_results (FK dependency)."""
        sub_idx = MIGRATION_ORDER.index("submissions")
        sr_idx = MIGRATION_ORDER.index("submission_results")
        assert sub_idx < sr_idx

    def test_event_types_before_events(self):
        """event_types must come before events (FK dependency)."""
        et_idx = MIGRATION_ORDER.index("event_types")
        ev_idx = MIGRATION_ORDER.index("events")
        assert et_idx < ev_idx

    def test_events_before_event_observations(self):
        """events must come before event_observations (FK dependency)."""
        ev_idx = MIGRATION_ORDER.index("events")
        eo_idx = MIGRATION_ORDER.index("event_observations")
        assert ev_idx < eo_idx

    def test_no_duplicates(self):
        """Migration order should not contain duplicate table names."""
        assert len(MIGRATION_ORDER) == len(set(MIGRATION_ORDER))


# ============================================================
# JSON Column Configuration
# ============================================================


class TestJsonColumns:
    """Tests for JSON_COLUMNS configuration."""

    def test_json_columns_is_dict(self):
        """JSON_COLUMNS should be a dict mapping table names to column lists."""
        assert isinstance(JSON_COLUMNS, dict)

    def test_known_json_tables(self):
        """Expected tables should have JSON column definitions."""
        expected_tables = {
            "datasets",
            "submissions",
            "submission_results",
            "uctp_runs",
            "uctp_models",
            "uctp_api_connections",
            "jobs",
            "event_types",
            "events",
        }
        assert set(JSON_COLUMNS.keys()) == expected_tables

    def test_datasets_json_columns(self):
        """datasets table should have generation_config as JSON."""
        assert "generation_config" in JSON_COLUMNS["datasets"]


# ============================================================
# Helper Functions
# ============================================================


class TestGetTableColumns:
    """Tests for get_table_columns()."""

    def test_returns_column_names(self):
        """Should return list of column names from DuckDB."""
        duck = MagicMock()
        duck.execute.return_value = MagicMock(
            fetchall=MagicMock(
                return_value=[
                    ("id",),
                    ("name",),
                    ("config",),
                ]
            )
        )
        cols = get_table_columns(duck, "test_table")
        assert cols == ["id", "name", "config"]


class TestGetTableCount:
    """Tests for get_table_count()."""

    def test_returns_count(self):
        """Should return row count from DuckDB table."""
        duck = MagicMock()
        duck.execute.return_value = MagicMock(
            fetchone=MagicMock(return_value=(42,))
        )
        count = get_table_count(duck, "test_table")
        assert count == 42


# ============================================================
# Migrate Table (Mocked)
# ============================================================


class TestMigrateTable:
    """Tests for migrate_table() using mocked connections."""

    def test_skips_empty_table(self, capsys):
        """An empty source table should be skipped."""
        duck = MagicMock()
        # First call: get_table_count returns 0
        duck.execute.return_value = MagicMock(
            fetchone=MagicMock(return_value=(0,))
        )
        pg = MagicMock()

        count = migrate_table(duck, pg, "empty_table", batch_size=1000, dry_run=False)
        assert count == 0
        captured = capsys.readouterr()
        assert "0 rows" in captured.out.lower() or "skipping" in captured.out.lower()


# ============================================================
# Verify Migration
# ============================================================


class TestVerifyMigration:
    """Tests for verify_migration()."""

    def test_matching_counts_returns_true(self, capsys):
        """When all counts match, verify should return True."""
        duck = MagicMock()
        duck.execute.return_value = MagicMock(
            fetchone=MagicMock(return_value=(10,))
        )

        pg_cursor = MagicMock()
        pg_cursor.fetchone.return_value = (10,)
        pg = MagicMock()
        pg.cursor.return_value.__enter__ = MagicMock(return_value=pg_cursor)
        pg.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Only test a single table to avoid complex mocking
        result = verify_migration(duck, pg, ["data_sources"])
        assert result is True

    def test_mismatched_counts_returns_false(self, capsys):
        """When PostgreSQL has fewer rows, verify should return False."""
        duck = MagicMock()
        duck.execute.return_value = MagicMock(
            fetchone=MagicMock(return_value=(10,))
        )

        pg_cursor = MagicMock()
        pg_cursor.fetchone.return_value = (5,)
        pg = MagicMock()
        pg.cursor.return_value.__enter__ = MagicMock(return_value=pg_cursor)
        pg.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = verify_migration(duck, pg, ["data_sources"])
        assert result is False
        captured = capsys.readouterr()
        assert "MISMATCH" in captured.out
