#!/usr/bin/env python3
"""
Migrate UCT Benchmark data from DuckDB to Supabase (PostgreSQL).

This script migrates data from a local DuckDB database to a PostgreSQL
database (Supabase). It handles all tables in the correct order to
respect foreign key relationships.

Usage:
    # Dry run (shows what would be migrated)
    python scripts/migrate_to_supabase.py --source ./data/db.duckdb --target $DATABASE_URL --dry-run

    # Full migration
    python scripts/migrate_to_supabase.py --source ./data/db.duckdb --target $DATABASE_URL

    # Validate migration
    python scripts/migrate_to_supabase.py --validate --target $DATABASE_URL --source ./data/db.duckdb

Requirements:
    - psycopg[binary,pool]>=3.1.0
"""

import argparse
import hashlib
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from tqdm import tqdm

from uct_benchmark.database.connection import DatabaseManager

# Migration order (respects foreign key relationships)
MIGRATION_ORDER = [
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
    "submissions",
    "submission_results",
    "jobs",
    "_schema_metadata",
]

# Batch size for bulk inserts
BATCH_SIZE = 10000


def get_source_db(source_path: str) -> DatabaseManager:
    """Create a DatabaseManager for the source DuckDB database."""
    return DatabaseManager(db_path=Path(source_path), read_only=True)


def get_target_db(target_url: str) -> DatabaseManager:
    """Create a DatabaseManager for the target PostgreSQL database."""
    return DatabaseManager(
        backend="postgres",
        database_url=target_url,
        pool_min=2,
        pool_max=10,
    )


def get_table_counts(db: DatabaseManager) -> dict:
    """Get row counts for all tables."""
    counts = {}
    for table in MIGRATION_ORDER:
        try:
            result = db.adapter.fetchone(f"SELECT COUNT(*) FROM {table}")
            counts[table] = result[0] if result else 0
        except Exception:
            counts[table] = 0
    return counts


def compute_checksum(db: DatabaseManager, table: str) -> str:
    """Compute a checksum for a table's data."""
    # Get a sample of data for checksum
    try:
        df = db.adapter.fetchdf(f"SELECT * FROM {table} ORDER BY 1 LIMIT 1000")
        if df.empty:
            return "empty"
        # Create a hash of the concatenated string representation
        data_str = df.to_csv(index=False)
        return hashlib.md5(data_str.encode()).hexdigest()[:16]
    except Exception as e:
        return f"error: {str(e)[:50]}"


def migrate_table(
    source: DatabaseManager,
    target: DatabaseManager,
    table: str,
    batch_size: int = BATCH_SIZE,
    dry_run: bool = False,
) -> int:
    """
    Migrate a single table from source to target.

    Args:
        source: Source DuckDB database
        target: Target PostgreSQL database
        table: Table name to migrate
        batch_size: Number of rows per batch
        dry_run: If True, only show what would be done

    Returns:
        Number of rows migrated
    """
    # Get total count
    result = source.adapter.fetchone(f"SELECT COUNT(*) FROM {table}")
    total_rows = result[0] if result else 0

    if total_rows == 0:
        return 0

    if dry_run:
        print(f"  Would migrate {total_rows:,} rows from {table}")
        return total_rows

    # Get column info
    df_sample = source.adapter.fetchdf(f"SELECT * FROM {table} LIMIT 1")
    columns = list(df_sample.columns)

    # Migrate in batches
    migrated = 0
    offset = 0

    with tqdm(total=total_rows, desc=f"  {table}", unit="rows") as pbar:
        while offset < total_rows:
            # Fetch batch from source
            batch_df = source.adapter.fetchdf(
                f"SELECT * FROM {table} ORDER BY 1 LIMIT {batch_size} OFFSET {offset}"
            )

            if batch_df.empty:
                break

            # Insert into target
            try:
                rows_inserted = target.adapter.bulk_insert_df(
                    table=table,
                    df=batch_df,
                    columns=columns,
                    on_conflict="nothing",  # Skip duplicates
                    conflict_columns=[columns[0]],  # Assume first column is primary key
                )
                migrated += rows_inserted
            except Exception as e:
                print(f"    Error inserting batch: {e}")
                # Try row-by-row for better error handling
                for _, row in batch_df.iterrows():
                    try:
                        target.adapter.bulk_insert_df(
                            table=table,
                            df=pd.DataFrame([row]),
                            columns=columns,
                            on_conflict="nothing",
                            conflict_columns=[columns[0]],
                        )
                        migrated += 1
                    except Exception:
                        pass  # Skip problematic rows

            offset += batch_size
            pbar.update(len(batch_df))

    return migrated


def reset_sequences(target: DatabaseManager) -> None:
    """Reset PostgreSQL sequences to match migrated data."""
    sequences = [
        ("state_vectors_id_seq", "state_vectors", "id"),
        ("element_sets_id_seq", "element_sets", "id"),
        ("datasets_id_seq", "datasets", "id"),
        ("events_id_seq", "events", "id"),
        ("submissions_id_seq", "submissions", "id"),
        ("submission_results_id_seq", "submission_results", "id"),
    ]

    for seq_name, table_name, column_name in sequences:
        try:
            result = target.adapter.fetchone(f"SELECT MAX({column_name}) FROM {table_name}")
            max_id = result[0] if result and result[0] else 0
            target.adapter.execute(f"SELECT setval('{seq_name}', {max_id + 1}, false)")
        except Exception as e:
            print(f"  Warning: Could not reset sequence {seq_name}: {e}")


def run_migration(
    source_path: str,
    target_url: str,
    dry_run: bool = False,
    tables: list = None,
) -> dict:
    """
    Run the full migration.

    Args:
        source_path: Path to source DuckDB file
        target_url: PostgreSQL connection URL
        dry_run: If True, only show what would be done
        tables: Optional list of tables to migrate (defaults to all)

    Returns:
        Dictionary with migration results
    """
    print("=" * 60)
    print("UCT Benchmark Migration: DuckDB -> PostgreSQL")
    print("=" * 60)

    if dry_run:
        print("DRY RUN MODE - No data will be modified")
    print()

    # Connect to databases
    print("Connecting to source database...")
    source = get_source_db(source_path)

    print("Connecting to target database...")
    target = get_target_db(target_url)

    # Initialize target schema if needed
    print("Initializing target schema...")
    target.initialize()

    # Get source counts
    print("\nSource database statistics:")
    source_counts = get_table_counts(source)
    for table, count in source_counts.items():
        if count > 0:
            print(f"  {table}: {count:,} rows")

    # Migrate tables
    tables_to_migrate = tables or MIGRATION_ORDER
    results = {}

    print("\nMigrating tables...")
    for table in tables_to_migrate:
        if table not in MIGRATION_ORDER:
            print(f"  Skipping unknown table: {table}")
            continue

        if source_counts.get(table, 0) == 0:
            print(f"  Skipping empty table: {table}")
            results[table] = {"source": 0, "migrated": 0}
            continue

        try:
            migrated = migrate_table(source, target, table, dry_run=dry_run)
            results[table] = {
                "source": source_counts[table],
                "migrated": migrated,
            }
        except Exception as e:
            print(f"  Error migrating {table}: {e}")
            results[table] = {"source": source_counts[table], "migrated": 0, "error": str(e)}

    # Reset sequences (only for real migration)
    if not dry_run:
        print("\nResetting sequences...")
        reset_sequences(target)

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    total_source = sum(r["source"] for r in results.values())
    total_migrated = sum(r.get("migrated", 0) for r in results.values())
    print(f"Total rows in source: {total_source:,}")
    print(f"Total rows migrated: {total_migrated:,}")

    if not dry_run:
        errors = [t for t, r in results.items() if "error" in r]
        if errors:
            print(f"\nTables with errors: {', '.join(errors)}")

    # Clean up
    source.close()
    target.close()

    return results


def validate_migration(source_path: str, target_url: str) -> dict:
    """
    Validate a completed migration by comparing row counts and checksums.

    Args:
        source_path: Path to source DuckDB file
        target_url: PostgreSQL connection URL

    Returns:
        Dictionary with validation results
    """
    print("=" * 60)
    print("Migration Validation")
    print("=" * 60)
    print()

    source = get_source_db(source_path)
    target = get_target_db(target_url)

    results = {}
    all_valid = True

    print("Comparing table counts and checksums...")
    for table in MIGRATION_ORDER:
        source_count = get_table_counts(source).get(table, 0)
        target_count = get_table_counts(target).get(table, 0)

        source_checksum = compute_checksum(source, table) if source_count > 0 else "empty"
        target_checksum = compute_checksum(target, table) if target_count > 0 else "empty"

        count_match = source_count == target_count
        checksum_match = source_checksum == target_checksum

        status = "OK" if count_match and checksum_match else "MISMATCH"
        if not count_match or not checksum_match:
            all_valid = False

        results[table] = {
            "source_count": source_count,
            "target_count": target_count,
            "count_match": count_match,
            "source_checksum": source_checksum,
            "target_checksum": target_checksum,
            "checksum_match": checksum_match,
            "status": status,
        }

        print(f"  {table}: {status}")
        if not count_match:
            print(f"    Count: source={source_count}, target={target_count}")
        if not checksum_match:
            print(f"    Checksum: source={source_checksum}, target={target_checksum}")

    print()
    print("=" * 60)
    print(f"Validation Result: {'PASSED' if all_valid else 'FAILED'}")
    print("=" * 60)

    source.close()
    target.close()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Migrate UCT Benchmark data from DuckDB to PostgreSQL/Supabase"
    )
    parser.add_argument(
        "--source",
        required=False,
        help="Path to source DuckDB file",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="PostgreSQL connection URL (or set DATABASE_URL env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate migration by comparing source and target",
    )
    parser.add_argument(
        "--tables",
        nargs="*",
        help="Specific tables to migrate (default: all)",
    )

    args = parser.parse_args()

    if args.validate:
        if not args.source:
            parser.error("--source is required for validation")
        validate_migration(args.source, args.target)
    else:
        if not args.source:
            parser.error("--source is required for migration")
        run_migration(
            args.source,
            args.target,
            dry_run=args.dry_run,
            tables=args.tables,
        )


if __name__ == "__main__":
    main()
