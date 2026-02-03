#!/usr/bin/env python3
"""Migrate data from a DuckDB database to PostgreSQL (Supabase).

This script reads all tables from a local DuckDB database and inserts the
data into a PostgreSQL database using batch INSERTs with ON CONFLICT DO NOTHING
for idempotent re-runs.

Usage:
    python scripts/migrate_duckdb_to_postgres.py \
        --duckdb-path data/database/uct_benchmark.duckdb \
        --postgres-url postgresql://user:pass@host:5432/db \
        [--batch-size 5000] \
        [--dry-run]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

# Migration order respects FK dependencies
TABLE_ORDER = [
    "data_sources",
    "_schema_metadata",
    "satellites",
    "observations",
    "state_vectors",
    "element_sets",
    "datasets",
    "dataset_observations",
    "dataset_references",
    "event_types",
    "events",
    "event_observations",
    "validation_measurements",
    "submissions",
    "submission_results",
    "jobs",
    "uctp_runs",
    "uctp_models",
    "uctp_api_connections",
    "credentials",
]

# Alias for backward compatibility with tests
MIGRATION_ORDER = TABLE_ORDER

# Tables with JSON columns that need conversion from string to proper JSON
JSON_COLUMNS = {
    "datasets": ["generation_config"],
    "submissions": ["algorithm_config"],
    "submission_results": ["satellite_results", "additional_metrics"],
    "uctp_runs": ["config", "results", "logs"],
    "uctp_models": ["hyperparameters", "metrics", "feature_config"],
    "uctp_api_connections": ["config", "last_error"],
    "jobs": ["metadata", "result"],
    "event_types": ["properties_schema"],
    "events": ["properties"],
}


def get_table_columns(duck_conn, table_name: str) -> list[str]:
    """Get column names for a DuckDB table."""
    result = duck_conn.execute(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_name = '{table_name}' AND table_schema = 'main' "
        f"ORDER BY ordinal_position"
    ).fetchall()
    return [row[0] for row in result]


def get_table_count(duck_conn, table_name: str) -> int:
    """Get row count for a table."""
    return duck_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def convert_json_columns(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Convert JSON string columns to proper JSON for PostgreSQL JSONB."""
    json_cols = JSON_COLUMNS.get(table_name, [])
    for col in json_cols:
        if col in df.columns:
            def safe_json(val):
                if pd.isna(val) or val is None:
                    return None
                if isinstance(val, (dict, list)):
                    return json.dumps(val)
                try:
                    # Validate it's valid JSON
                    json.loads(str(val))
                    return str(val)
                except (json.JSONDecodeError, TypeError):
                    return None
            df[col] = df[col].apply(safe_json)
    return df


def migrate_table(
    duck_conn,
    pg_conn,
    table_name: str,
    batch_size: int,
    dry_run: bool,
) -> int:
    """Migrate a single table from DuckDB to PostgreSQL."""
    count = get_table_count(duck_conn, table_name)
    if count == 0:
        print(f"  {table_name}: 0 rows (skipping)")
        return 0

    columns = get_table_columns(duck_conn, table_name)
    col_list = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = (
        f"INSERT INTO {table_name} ({col_list}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT DO NOTHING"
    )

    total_inserted = 0
    offset = 0

    while offset < count:
        df = duck_conn.execute(
            f"SELECT {col_list} FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
        ).fetchdf()

        if df.empty:
            break

        # Convert JSON columns
        df = convert_json_columns(df, table_name)

        # Replace NaN/NaT with None
        df = df.where(df.notna(), None)

        rows = [tuple(row) for row in df.itertuples(index=False, name=None)]

        if not dry_run:
            import psycopg
            with pg_conn.cursor() as cur:
                cur.executemany(insert_sql, rows)
            pg_conn.commit()

        total_inserted += len(rows)
        offset += batch_size

    print(f"  {table_name}: {total_inserted}/{count} rows {'(dry run)' if dry_run else 'migrated'}")
    return total_inserted


def reset_sequences(pg_conn, tables: list[str]) -> None:
    """Reset PostgreSQL sequences to match max IDs after data import."""
    import psycopg

    # Tables with integer identity/serial columns
    sequence_tables = [
        ("datasets", "id", "datasets_id_seq"),
        ("submissions", "id", "submissions_id_seq"),
        ("submission_results", "id", "submission_results_id_seq"),
        ("events", "id", "events_id_seq"),
        ("event_types", "id", "event_types_id_seq"),
        ("validation_measurements", "id", "validation_measurements_id_seq"),
        ("uctp_runs", "id", "uctp_runs_id_seq"),
        ("uctp_models", "id", "uctp_models_id_seq"),
        ("uctp_api_connections", "id", "uctp_api_connections_id_seq"),
    ]

    with pg_conn.cursor() as cur:
        for table, col, seq in sequence_tables:
            if table in tables:
                try:
                    cur.execute(f"SELECT MAX({col}) FROM {table}")
                    max_val = cur.fetchone()[0]
                    if max_val is not None:
                        cur.execute(f"SELECT setval('{seq}', {max_val})")
                        print(f"  Reset {seq} to {max_val}")
                except Exception as exc:
                    print(f"  Warning: Could not reset {seq}: {exc}")
    pg_conn.commit()


def verify_migration(duck_conn, pg_conn, tables: list[str]) -> bool:
    """Compare row counts between DuckDB and PostgreSQL."""
    print("\nVerification:")
    all_match = True

    for table in tables:
        duck_count = get_table_count(duck_conn, table)
        if duck_count == 0:
            continue

        import psycopg
        with pg_conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            pg_count = cur.fetchone()[0]

        status = "OK" if pg_count >= duck_count else "MISMATCH"
        if status == "MISMATCH":
            all_match = False
        print(f"  {table}: DuckDB={duck_count}, PostgreSQL={pg_count} [{status}]")

    return all_match


def main():
    parser = argparse.ArgumentParser(
        description="Migrate UCT Benchmark data from DuckDB to PostgreSQL"
    )
    parser.add_argument(
        "--duckdb-path",
        type=str,
        required=True,
        help="Path to the DuckDB database file",
    )
    parser.add_argument(
        "--postgres-url",
        type=str,
        required=True,
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Number of rows per batch insert (default: 5000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read data but don't write to PostgreSQL",
    )
    args = parser.parse_args()

    # Validate DuckDB path
    db_path = Path(args.duckdb_path)
    if not db_path.exists():
        print(f"Error: DuckDB file not found: {db_path}")
        sys.exit(1)

    print(f"Source: {db_path}")
    print(f"Target: {args.postgres_url.split('@')[0]}@****")
    print(f"Batch size: {args.batch_size}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Connect to DuckDB (read-only)
    duck_conn = duckdb.connect(str(db_path), read_only=True)

    # Discover which tables actually exist in DuckDB
    existing_tables = [
        row[0]
        for row in duck_conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    ]
    tables_to_migrate = [t for t in TABLE_ORDER if t in existing_tables]

    print(f"Tables to migrate: {len(tables_to_migrate)}/{len(TABLE_ORDER)}")
    print()

    # Connect to PostgreSQL
    if not args.dry_run:
        import psycopg
        pg_conn = psycopg.connect(args.postgres_url, autocommit=False)
    else:
        pg_conn = None

    # Migrate tables
    start_time = time.time()
    total_rows = 0

    print("Migration:")
    for table in tables_to_migrate:
        rows = migrate_table(duck_conn, pg_conn, table, args.batch_size, args.dry_run)
        total_rows += rows

    elapsed = time.time() - start_time
    print(f"\nTotal: {total_rows} rows in {elapsed:.1f}s")

    # Reset sequences
    if not args.dry_run and pg_conn:
        print("\nResetting sequences:")
        reset_sequences(pg_conn, tables_to_migrate)

        # Verify
        verify_migration(duck_conn, pg_conn, tables_to_migrate)

        pg_conn.close()

    duck_conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
