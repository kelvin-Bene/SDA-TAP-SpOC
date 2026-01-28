"""Tests for the DuckDB-to-PostgreSQL migration utilities.

These tests exercise the pure helper functions from the migration script
without requiring live DuckDB or PostgreSQL connections.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Ensure the scripts directory is importable
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "scripts")
)
from migrate_duckdb_to_postgres import (
    JSON_COLUMNS,
    MIGRATION_ORDER,
    SEQUENCE_TABLES,
    build_insert_sql,
    build_sequence_reset_sql,
    convert_json_columns,
    get_table_columns_duckdb,
    migrate_table,
    reset_sequences,
    verify_row_counts,
)


# ============================================================
# JSON Column Conversion
# ============================================================


class TestConvertJsonColumns:
    """Tests for convert_json_columns()."""

    def test_converts_json_string_to_dict(self):
        """A JSON string in a known column should be parsed into a dict."""
        columns = ["id", "config", "name"]
        row = (1, '{"key": "value"}', "test")
        result = convert_json_columns(row, columns)
        assert result == (1, {"key": "value"}, "test")

    def test_converts_json_string_to_list(self):
        """A JSON array string should be parsed into a list."""
        columns = ["id", "training_dataset_ids"]
        row = (1, "[1, 2, 3]")
        result = convert_json_columns(row, columns)
        assert result == (1, [1, 2, 3])

    def test_leaves_none_unchanged(self):
        """None values should remain None even for JSON columns."""
        columns = ["id", "config"]
        row = (1, None)
        result = convert_json_columns(row, columns)
        assert result == (1, None)

    def test_leaves_non_json_columns_unchanged(self):
        """Non-JSON columns should pass through unchanged."""
        columns = ["id", "name", "status"]
        row = (1, "test-name", "active")
        result = convert_json_columns(row, columns)
        assert result == (1, "test-name", "active")

    def test_handles_invalid_json_gracefully(self):
        """Invalid JSON strings should be left as-is."""
        columns = ["id", "config"]
        row = (1, "not valid json {{{")
        result = convert_json_columns(row, columns)
        assert result == (1, "not valid json {{{")

    def test_all_json_columns_recognized(self):
        """Verify the set of known JSON columns matches specification."""
        expected = {
            "covariance",
            "grouped_obs_ids",
            "raw_results",
            "result",
            "metadata",
            "generation_params",
            "downsampling_config",
            "simulation_config",
            "config",
            "training_dataset_ids",
            "training_config",
        }
        assert JSON_COLUMNS == expected

    def test_already_parsed_value_left_unchanged(self):
        """If the value is already a dict (not a string), leave it alone."""
        columns = ["id", "config"]
        row = (1, {"already": "parsed"})
        result = convert_json_columns(row, columns)
        assert result == (1, {"already": "parsed"})

    def test_nested_json(self):
        """Deeply nested JSON should be correctly parsed."""
        columns = ["id", "generation_params"]
        nested = {"a": {"b": {"c": [1, 2, 3]}}}
        row = (1, json.dumps(nested))
        result = convert_json_columns(row, columns)
        assert result == (1, nested)


# ============================================================
# Migration Order
# ============================================================


class TestMigrationOrder:
    """Tests for the MIGRATION_ORDER constant."""

    def test_migration_order_length(self):
        """There should be exactly 20 tables in the migration order."""
        assert len(MIGRATION_ORDER) == 20

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
# SQL Generation
# ============================================================


class TestBuildInsertSQL:
    """Tests for build_insert_sql()."""

    def test_basic_insert(self):
        sql = build_insert_sql("test_table", ["id", "name", "value"])
        assert "INSERT INTO test_table" in sql
        assert "(id, name, value)" in sql
        assert "(%s, %s, %s)" in sql
        assert "ON CONFLICT DO NOTHING" in sql

    def test_single_column(self):
        sql = build_insert_sql("t", ["id"])
        assert "(id)" in sql
        assert "(%s)" in sql


class TestBuildSequenceResetSQL:
    """Tests for build_sequence_reset_sql()."""

    def test_generates_setval_call(self):
        sql = build_sequence_reset_sql("state_vectors", "state_vectors_id_seq")
        assert "setval" in sql
        assert "state_vectors_id_seq" in sql
        assert "MAX(id)" in sql
        assert "state_vectors" in sql

    def test_all_sequence_tables_present(self):
        """Every table in SEQUENCE_TABLES should be in MIGRATION_ORDER."""
        for table in SEQUENCE_TABLES:
            assert table in MIGRATION_ORDER, (
                f"Sequence table '{table}' not in MIGRATION_ORDER"
            )


# ============================================================
# Batch Processing Logic
# ============================================================


class TestMigrateTable:
    """Tests for migrate_table() using mocked connections."""

    def test_skips_empty_table(self, capsys):
        """An empty source table should be skipped."""
        duck = MagicMock()
        duck.execute.side_effect = [
            # DESCRIBE
            MagicMock(fetchall=MagicMock(return_value=[("id",), ("name",)])),
            # COUNT(*)
            MagicMock(fetchone=MagicMock(return_value=(0,))),
        ]
        pg = MagicMock()

        count = migrate_table(duck, pg, "empty_table")
        assert count == 0
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower() or "SKIP" in captured.out

    def test_skips_missing_table(self, capsys):
        """A table not in DuckDB should be skipped gracefully."""
        duck = MagicMock()
        duck.execute.side_effect = Exception("Table not found")
        pg = MagicMock()

        count = migrate_table(duck, pg, "missing_table")
        assert count == 0
        captured = capsys.readouterr()
        assert "SKIP" in captured.out

    def test_processes_single_batch(self, capsys):
        """A small table should be processed in a single batch."""
        rows = [(1, "a"), (2, "b"), (3, "c")]
        duck = MagicMock()
        duck.execute.side_effect = [
            # DESCRIBE
            MagicMock(fetchall=MagicMock(return_value=[("id",), ("name",)])),
            # COUNT(*)
            MagicMock(fetchone=MagicMock(return_value=(3,))),
            # SELECT * LIMIT/OFFSET batch 1
            MagicMock(fetchall=MagicMock(return_value=rows)),
            # SELECT * LIMIT/OFFSET batch 2 (empty)
            MagicMock(fetchall=MagicMock(return_value=[])),
        ]

        pg_cursor = MagicMock()
        pg = MagicMock()
        pg.cursor.return_value = pg_cursor

        count = migrate_table(duck, pg, "test_table", batch_size=10)
        assert count == 3
        pg_cursor.executemany.assert_called_once()

    def test_dry_run_does_not_write(self, capsys):
        """Dry run should read from DuckDB but not write to PostgreSQL."""
        rows = [(1, "x")]
        duck = MagicMock()
        duck.execute.side_effect = [
            # DESCRIBE
            MagicMock(fetchall=MagicMock(return_value=[("id",), ("name",)])),
            # COUNT(*)
            MagicMock(fetchone=MagicMock(return_value=(1,))),
            # SELECT * batch 1
            MagicMock(fetchall=MagicMock(return_value=rows)),
            # SELECT * batch 2 (empty)
            MagicMock(fetchall=MagicMock(return_value=[])),
        ]

        pg = MagicMock()

        count = migrate_table(duck, pg, "test_table", dry_run=True)
        assert count == 1
        # PostgreSQL cursor should never be created
        pg.cursor.assert_not_called()

    def test_multiple_batches(self, capsys):
        """A large table should be processed in multiple batches."""
        batch1 = [(i, f"r{i}") for i in range(5)]
        batch2 = [(i, f"r{i}") for i in range(5, 8)]

        duck = MagicMock()
        duck.execute.side_effect = [
            # DESCRIBE
            MagicMock(fetchall=MagicMock(return_value=[("id",), ("name",)])),
            # COUNT(*)
            MagicMock(fetchone=MagicMock(return_value=(8,))),
            # Batch 1
            MagicMock(fetchall=MagicMock(return_value=batch1)),
            # Batch 2
            MagicMock(fetchall=MagicMock(return_value=batch2)),
            # Batch 3 (empty)
            MagicMock(fetchall=MagicMock(return_value=[])),
        ]

        pg_cursor = MagicMock()
        pg = MagicMock()
        pg.cursor.return_value = pg_cursor

        count = migrate_table(duck, pg, "big_table", batch_size=5)
        assert count == 8
        assert pg_cursor.executemany.call_count == 2


# ============================================================
# Sequence Reset
# ============================================================


class TestResetSequences:
    """Tests for reset_sequences()."""

    def test_resets_all_sequences(self):
        """All known sequences should be reset."""
        pg_cursor = MagicMock()
        pg = MagicMock()
        pg.cursor.return_value = pg_cursor

        reset_sequences(pg)

        assert pg_cursor.execute.call_count == len(SEQUENCE_TABLES)
        for table, seq in SEQUENCE_TABLES.items():
            found = False
            for c in pg_cursor.execute.call_args_list:
                sql = c.args[0] if c.args else ""
                if seq in sql and table in sql:
                    found = True
                    break
            assert found, f"Sequence {seq} not reset"

    def test_dry_run_does_not_execute(self, capsys):
        """Dry run should print SQL but not execute."""
        pg_cursor = MagicMock()
        pg = MagicMock()
        pg.cursor.return_value = pg_cursor

        reset_sequences(pg, dry_run=True)

        pg_cursor.execute.assert_not_called()
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out


# ============================================================
# Verify Row Counts
# ============================================================


class TestVerifyRowCounts:
    """Tests for verify_row_counts()."""

    def test_matching_counts_returns_true(self, capsys):
        """When all counts match, verify should return True."""
        duck = MagicMock()
        duck.execute.return_value = MagicMock(
            fetchone=MagicMock(return_value=(10,))
        )

        pg_cursor = MagicMock()
        pg_cursor.fetchone.return_value = (10,)
        pg = MagicMock()
        pg.cursor.return_value = pg_cursor

        assert verify_row_counts(duck, pg) is True

    def test_mismatched_counts_returns_false(self, capsys):
        """When PostgreSQL has fewer rows, verify should return False."""
        duck = MagicMock()
        duck.execute.return_value = MagicMock(
            fetchone=MagicMock(return_value=(10,))
        )

        pg_cursor = MagicMock()
        pg_cursor.fetchone.return_value = (5,)
        pg = MagicMock()
        pg.cursor.return_value = pg_cursor

        assert verify_row_counts(duck, pg) is False
        captured = capsys.readouterr()
        assert "MISMATCH" in captured.out


# ============================================================
# get_table_columns_duckdb
# ============================================================


class TestGetTableColumnsDuckdb:
    """Tests for get_table_columns_duckdb()."""

    def test_returns_column_names(self):
        duck = MagicMock()
        duck.execute.return_value = MagicMock(
            fetchall=MagicMock(
                return_value=[
                    ("id", "INTEGER", "YES", None, None, None),
                    ("name", "VARCHAR", "YES", None, None, None),
                    ("config", "JSON", "YES", None, None, None),
                ]
            )
        )
        cols = get_table_columns_duckdb(duck, "test_table")
        assert cols == ["id", "name", "config"]
