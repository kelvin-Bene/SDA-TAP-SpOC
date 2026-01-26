"""
Command-line interface for UCT Benchmark database management.

Usage:
    uv run python -m uct_benchmark.database.cli <command> [options]

Commands:
    init        Initialize the database schema
    status      Show database status and statistics
    backup      Create a database backup
    restore     Restore from a backup
    export      Export a dataset to JSON/Parquet
    import      Import data from JSON/Parquet
    list        List datasets
    verify      Verify database schema integrity
    vacuum      Optimize the database
"""

import argparse
import sys
from pathlib import Path

from loguru import logger


def init_command(args):
    """Initialize the database schema."""
    from .connection import DatabaseManager

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    if args.force:
        logger.warning("Force flag set - this will DROP all existing tables!")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() != "yes":
            logger.info("Aborted.")
            return 1

    logger.info(f"Initializing database at {db.db_path}...")
    db.initialize(force=args.force)
    logger.info("Database initialized successfully.")

    # Show status
    stats = db.get_statistics()
    logger.info(f"Tables created: {len(stats)}")

    return 0


def status_command(args):
    """Show database status and statistics."""
    from .connection import DatabaseManager
    from .schema import get_schema_version, verify_schema

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    print(f"\nDatabase: {db.db_path}")
    print("-" * 50)

    # Check if initialized
    if not db.is_initialized():
        print("Status: NOT INITIALIZED")
        print("\nRun 'python -m uct_benchmark.database.cli init' to initialize.")
        return 1

    # Get schema version
    version = get_schema_version(db)
    print(f"Schema Version: {version or 'Unknown'}")

    # Get table statistics
    stats = db.get_statistics()
    print("\nTable Statistics:")
    print("-" * 50)

    for table, count in sorted(stats.items()):
        if table.startswith("_"):
            continue
        print(f"  {table:25s}: {count:>10,} rows")

    # Database file size
    if "_file_size_mb" in stats:
        print(f"\nDatabase Size: {stats['_file_size_mb']:.2f} MB")

    # Verify schema
    verification = verify_schema(db)
    if verification["valid"]:
        print("\nSchema: Valid")
    else:
        print(f"\nSchema: INVALID - Missing tables: {verification['missing_tables']}")

    return 0


def backup_command(args):
    """Create a database backup."""
    from .connection import DatabaseManager

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    if not db.is_initialized():
        logger.error("Database not initialized.")
        return 1

    backup_path = args.output if args.output else None
    if backup_path:
        backup_path = Path(backup_path)

    logger.info("Creating backup...")
    result_path = db.backup(backup_path)
    logger.info(f"Backup created: {result_path}")

    return 0


def restore_command(args):
    """Restore from a backup."""
    from .connection import DatabaseManager

    if not args.backup_file:
        logger.error("Backup file path required.")
        return 1

    backup_path = Path(args.backup_file)
    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_path}")
        return 1

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    logger.warning(f"This will overwrite the database at {db.db_path}")
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() != "yes":
        logger.info("Aborted.")
        return 1

    logger.info(f"Restoring from {backup_path}...")
    db.restore(backup_path)
    logger.info("Restore complete.")

    return 0


def export_command(args):
    """Export a dataset to JSON or Parquet."""
    from .connection import DatabaseManager
    from .export import export_dataset_to_json, export_observations_to_parquet

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    if not db.is_initialized():
        logger.error("Database not initialized.")
        return 1

    output_path = Path(args.output) if args.output else None

    if args.dataset_id:
        # Export a specific dataset
        logger.info(f"Exporting dataset {args.dataset_id}...")
        result_path = export_dataset_to_json(
            db, args.dataset_id, output_path, include_truth=not args.no_truth
        )
        logger.info(f"Dataset exported to: {result_path}")

    elif args.observations:
        # Export all observations
        if not output_path:
            logger.error("Output path required for observation export.")
            return 1

        logger.info("Exporting observations to Parquet...")
        result_path = export_observations_to_parquet(
            db, output_path, compression=args.compression or "zstd"
        )
        logger.info(f"Observations exported to: {result_path}")

    else:
        logger.error("Specify --dataset-id or --observations")
        return 1

    return 0


def import_command(args):
    """Import data from JSON or Parquet."""
    from .connection import DatabaseManager
    from .export import import_dataset_from_json
    from .ingestion import DataIngestionPipeline

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    if not db.is_initialized():
        logger.info("Database not initialized. Initializing...")
        db.initialize()

    input_path = Path(args.input_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    if input_path.suffix == ".json":
        logger.info(f"Importing dataset from JSON: {input_path}")
        dataset_id = import_dataset_from_json(db, input_path, dataset_name=args.name)
        logger.info(f"Dataset imported with ID: {dataset_id}")

    elif input_path.suffix == ".parquet":
        logger.info(f"Importing from Parquet: {input_path}")
        pipeline = DataIngestionPipeline(db)
        report = pipeline.sync_from_existing_parquet(
            str(input_path), data_type=args.data_type or "observations"
        )
        logger.info(f"Import complete: {report}")

    else:
        logger.error(f"Unsupported file format: {input_path.suffix}")
        return 1

    return 0


def list_command(args):
    """List datasets in the database."""
    from .connection import DatabaseManager

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    if not db.is_initialized():
        logger.error("Database not initialized.")
        return 1

    datasets = db.datasets.list_datasets(
        tier=args.tier,
        orbital_regime=args.regime,
        status=args.status,
        limit=args.limit or 50,
    )

    if datasets.empty:
        print("No datasets found.")
        return 0

    print(f"\nDatasets ({len(datasets)} found):")
    print("-" * 80)
    print(
        f"{'ID':>5} {'Name':25s} {'Code':15s} {'Tier':5s} {'Regime':7s} {'Obs':>8} {'Status':12s}"
    )
    print("-" * 80)

    for _, row in datasets.iterrows():
        print(
            f"{row['id']:>5} {str(row['name'])[:25]:25s} {str(row['code'] or '')[:15]:15s} "
            f"{str(row['tier'] or ''):5s} {str(row['orbital_regime'] or ''):7s} "
            f"{row['observation_count'] or 0:>8} {str(row['status'])[:12]:12s}"
        )

    return 0


def verify_command(args):
    """Verify database schema integrity."""
    from .connection import DatabaseManager
    from .schema import verify_schema

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    print(f"\nVerifying database at {db.db_path}...")
    print("-" * 50)

    results = verify_schema(db)

    if results["valid"]:
        print("Schema: VALID")
    else:
        print("Schema: INVALID")
        print(f"Missing tables: {results['missing_tables']}")

    print(f"Schema version: {results['schema_version'] or 'Unknown'}")

    print("\nTable row counts:")
    for table, info in sorted(results["tables"].items()):
        print(f"  {table}: {info['row_count']} rows")

    return 0 if results["valid"] else 1


def vacuum_command(args):
    """Optimize the database by reclaiming unused space."""
    from .connection import DatabaseManager

    db_path = args.db_path if args.db_path else None
    db = DatabaseManager(db_path=db_path)

    if not db.is_initialized():
        logger.error("Database not initialized.")
        return 1

    # Get size before
    stats_before = db.get_statistics()
    size_before = stats_before.get("_file_size_mb", 0)

    logger.info("Running VACUUM...")
    db.vacuum()

    # Get size after
    stats_after = db.get_statistics()
    size_after = stats_after.get("_file_size_mb", 0)

    saved = size_before - size_after
    logger.info(
        f"VACUUM complete. Size: {size_before:.2f} MB -> {size_after:.2f} MB (saved {saved:.2f} MB)"
    )

    return 0


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="UCT Benchmark Database Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--db-path",
        help="Path to the database file (default: auto-detected)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize the database schema")
    init_parser.add_argument("--force", action="store_true", help="Drop and recreate all tables")

    # status command
    subparsers.add_parser("status", help="Show database status and statistics")

    # backup command
    backup_parser = subparsers.add_parser("backup", help="Create a database backup")
    backup_parser.add_argument("-o", "--output", help="Output path for backup file")

    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument("backup_file", help="Path to backup file")

    # export command
    export_parser = subparsers.add_parser("export", help="Export data to JSON/Parquet")
    export_parser.add_argument("--dataset-id", type=int, help="ID of dataset to export")
    export_parser.add_argument(
        "--observations", action="store_true", help="Export all observations"
    )
    export_parser.add_argument("-o", "--output", help="Output file path")
    export_parser.add_argument(
        "--no-truth", action="store_true", help="Exclude truth data from export"
    )
    export_parser.add_argument(
        "--compression", default="zstd", help="Compression for Parquet (zstd, snappy, gzip)"
    )

    # import command
    import_parser = subparsers.add_parser("import", help="Import data from JSON/Parquet")
    import_parser.add_argument("input_file", help="Path to input file")
    import_parser.add_argument("--name", help="Override dataset name")
    import_parser.add_argument(
        "--data-type",
        choices=["observations", "state_vectors", "element_sets", "satellites"],
        default="observations",
        help="Type of data for Parquet import",
    )

    # list command
    list_parser = subparsers.add_parser("list", help="List datasets")
    list_parser.add_argument(
        "--tier", choices=["T1", "T2", "T3", "T4", "T5"], help="Filter by tier"
    )
    list_parser.add_argument(
        "--regime", choices=["LEO", "MEO", "GEO", "HEO"], help="Filter by orbital regime"
    )
    list_parser.add_argument(
        "--status",
        choices=["created", "processing", "complete", "failed"],
        help="Filter by status",
    )
    list_parser.add_argument("--limit", type=int, default=50, help="Maximum number of results")

    # verify command
    subparsers.add_parser("verify", help="Verify database schema integrity")

    # vacuum command
    subparsers.add_parser("vacuum", help="Optimize the database")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    # Route to appropriate command
    commands = {
        "init": init_command,
        "status": status_command,
        "backup": backup_command,
        "restore": restore_command,
        "export": export_command,
        "import": import_command,
        "list": list_command,
        "verify": verify_command,
        "vacuum": vacuum_command,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
