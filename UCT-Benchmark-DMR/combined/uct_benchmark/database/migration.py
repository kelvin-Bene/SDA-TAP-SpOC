# -*- coding: utf-8 -*-
"""
Data migration utilities for importing existing data files into the database.

Supports importing:
- Parquet files (observations, state vectors, etc.)
- JSON dataset files (legacy format)
- CSV files

Created for Phase 2 of the UCT Benchmark database implementation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from loguru import logger

from .connection import DatabaseManager


class MigrationReport:
    """Report tracking migration results."""

    def __init__(self):
        self.imported_observations = 0
        self.imported_state_vectors = 0
        self.imported_element_sets = 0
        self.imported_satellites = 0
        self.imported_datasets = 0
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def add_error(self, source: str, message: str) -> None:
        """Record an error."""
        self.errors.append((source, message))

    def add_warning(self, message: str) -> None:
        """Record a warning."""
        self.warnings.append(message)

    @property
    def duration(self) -> Optional[float]:
        """Get migration duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def summary(self) -> str:
        """Generate summary string."""
        lines = [
            "=" * 50,
            "Migration Report",
            "=" * 50,
            f"Satellites imported:    {self.imported_satellites}",
            f"Observations imported:  {self.imported_observations}",
            f"State vectors imported: {self.imported_state_vectors}",
            f"Element sets imported:  {self.imported_element_sets}",
            f"Datasets imported:      {self.imported_datasets}",
            f"Errors:                 {len(self.errors)}",
            f"Warnings:               {len(self.warnings)}",
        ]
        if self.duration:
            lines.append(f"Duration:               {self.duration:.2f}s")

        if self.errors:
            lines.append("-" * 50)
            lines.append("Errors:")
            for source, msg in self.errors[:10]:  # Show first 10
                lines.append(f"  [{source}] {msg}")
            if len(self.errors) > 10:
                lines.append(f"  ... and {len(self.errors) - 10} more")

        if self.warnings:
            lines.append("-" * 50)
            lines.append("Warnings:")
            for msg in self.warnings[:5]:  # Show first 5
                lines.append(f"  {msg}")
            if len(self.warnings) > 5:
                lines.append(f"  ... and {len(self.warnings) - 5} more")

        lines.append("=" * 50)
        return "\n".join(lines)


class DataMigration:
    """
    Data migration utility for importing existing files into the database.

    Usage:
        migration = DataMigration("path/to/database.duckdb")
        report = migration.import_from_parquet("observations.parquet", data_type="observations")
        print(report.summary())
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize migration utility.

        Args:
            db_path: Path to database file. Uses default if None.
        """
        self.db = DatabaseManager(db_path=db_path)
        self.db.initialize()

    def import_from_parquet(
        self,
        file_path: Union[str, Path],
        data_type: str,
        **kwargs,
    ) -> MigrationReport:
        """
        Import data from a Parquet file.

        Args:
            file_path: Path to Parquet file
            data_type: Type of data - "observations", "state_vectors", "element_sets", or "satellites"
            **kwargs: Additional options passed to the import method

        Returns:
            MigrationReport with import statistics
        """
        report = MigrationReport()
        report.start_time = datetime.now()

        try:
            df = pd.read_parquet(file_path)
            logger.info(f"Loaded {len(df)} records from {file_path}")

            if data_type == "observations":
                report = self._import_observations(df, report, **kwargs)
            elif data_type == "state_vectors":
                report = self._import_state_vectors(df, report, **kwargs)
            elif data_type == "element_sets":
                report = self._import_element_sets(df, report, **kwargs)
            elif data_type == "satellites":
                report = self._import_satellites(df, report, **kwargs)
            else:
                report.add_error(str(file_path), f"Unknown data type: {data_type}")

        except Exception as e:
            report.add_error(str(file_path), str(e))
            logger.error(f"Migration failed: {e}")

        report.end_time = datetime.now()
        return report

    def import_from_json(
        self,
        file_path: Union[str, Path],
        dataset_name: Optional[str] = None,
    ) -> MigrationReport:
        """
        Import data from a JSON dataset file (legacy format).

        Args:
            file_path: Path to JSON file
            dataset_name: Name for the dataset. Uses filename if None.

        Returns:
            MigrationReport with import statistics
        """
        report = MigrationReport()
        report.start_time = datetime.now()

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            if dataset_name is None:
                dataset_name = Path(file_path).stem

            # Handle different JSON formats
            if isinstance(data, dict):
                if "observations" in data:
                    # New format with separate sections
                    report = self._import_structured_json(data, dataset_name, report)
                elif "data" in data:
                    # Wrapped format
                    report = self._import_structured_json(data["data"], dataset_name, report)
                else:
                    # Assume it's a list of observations in dict format
                    df = pd.DataFrame([data])
                    report = self._import_observations(df, report)
            elif isinstance(data, list):
                # List of records
                df = pd.DataFrame(data)
                if "obTime" in df.columns or "ob_time" in df.columns:
                    report = self._import_observations(df, report)
                elif "epoch" in df.columns:
                    if "line1" in df.columns:
                        report = self._import_element_sets(df, report)
                    else:
                        report = self._import_state_vectors(df, report)

            logger.info(f"Imported data from {file_path}")

        except Exception as e:
            report.add_error(str(file_path), str(e))
            logger.error(f"JSON import failed: {e}")

        report.end_time = datetime.now()
        return report

    def import_dataset_directory(
        self,
        directory: Union[str, Path],
        dataset_name: Optional[str] = None,
    ) -> MigrationReport:
        """
        Import a complete dataset from a directory structure.

        Expected structure:
            directory/
                observations.parquet or observations.json
                state_vectors.parquet or state_vectors.json
                element_sets.parquet or element_sets.json
                metadata.json (optional)

        Args:
            directory: Path to directory containing dataset files
            dataset_name: Name for the dataset. Uses directory name if None.

        Returns:
            MigrationReport with import statistics
        """
        report = MigrationReport()
        report.start_time = datetime.now()

        directory = Path(directory)
        if dataset_name is None:
            dataset_name = directory.name

        # Look for data files
        file_mappings = {
            "observations": [
                "observations.parquet",
                "obs.parquet",
                "observations.json",
                "obs.json",
            ],
            "state_vectors": [
                "state_vectors.parquet",
                "sv.parquet",
                "states.parquet",
                "state_vectors.json",
            ],
            "element_sets": [
                "element_sets.parquet",
                "elsets.parquet",
                "tles.parquet",
                "element_sets.json",
            ],
        }

        for data_type, filenames in file_mappings.items():
            for filename in filenames:
                file_path = directory / filename
                if file_path.exists():
                    logger.info(f"Found {data_type} file: {file_path}")
                    if filename.endswith(".parquet"):
                        sub_report = self.import_from_parquet(file_path, data_type)
                    else:
                        sub_report = self.import_from_json(file_path, dataset_name)

                    # Merge reports
                    report.imported_observations += sub_report.imported_observations
                    report.imported_state_vectors += sub_report.imported_state_vectors
                    report.imported_element_sets += sub_report.imported_element_sets
                    report.imported_satellites += sub_report.imported_satellites
                    report.errors.extend(sub_report.errors)
                    report.warnings.extend(sub_report.warnings)
                    break
            else:
                report.add_warning(f"No {data_type} file found in {directory}")

        # Create dataset record if data was imported
        if report.imported_observations > 0 or report.imported_state_vectors > 0:
            try:
                metadata_path = directory / "metadata.json"
                params = {}
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        params = json.load(f)

                dataset_id = self.db.datasets.create(
                    name=dataset_name,
                    params=params,
                )
                report.imported_datasets = 1
                logger.info(f"Created dataset '{dataset_name}' with ID {dataset_id}")
            except Exception as e:
                report.add_error("dataset", str(e))

        report.end_time = datetime.now()
        return report

    def _import_observations(
        self,
        df: pd.DataFrame,
        report: MigrationReport,
        **kwargs,
    ) -> MigrationReport:
        """Import observation records."""
        # Column mapping for different naming conventions
        column_map = {
            "satNo": "sat_no",
            "obTime": "ob_time",
            "sensorName": "sensor_name",
            "dataMode": "data_mode",
            "trackId": "track_id",
            "isUct": "is_uct",
            "isSimulated": "is_simulated",
        }

        df_mapped = df.rename(columns=column_map)

        # Ensure satellites exist
        if "sat_no" in df_mapped.columns:
            unique_sats = df_mapped["sat_no"].dropna().unique()
            for sat_no in unique_sats:
                try:
                    self.db.satellites.get_by_sat_no(int(sat_no))
                except Exception:
                    try:
                        self.db.satellites.create(sat_no=int(sat_no))
                        report.imported_satellites += 1
                    except Exception as e:
                        report.add_warning(f"Could not create satellite {sat_no}: {e}")

        # Bulk insert observations
        try:
            count = self.db.observations.bulk_insert(df_mapped)
            report.imported_observations = count
        except Exception as e:
            report.add_error("observations", str(e))

        return report

    def _import_state_vectors(
        self,
        df: pd.DataFrame,
        report: MigrationReport,
        **kwargs,
    ) -> MigrationReport:
        """Import state vector records."""
        column_map = {
            "satNo": "sat_no",
            "xpos": "x_pos",
            "ypos": "y_pos",
            "zpos": "z_pos",
            "xvel": "x_vel",
            "yvel": "y_vel",
            "zvel": "z_vel",
            "dataMode": "data_mode",
            "cov_matrix": "covariance",
        }

        df_mapped = df.rename(columns=column_map)

        # Ensure satellites exist
        if "sat_no" in df_mapped.columns:
            unique_sats = df_mapped["sat_no"].dropna().unique()
            for sat_no in unique_sats:
                try:
                    self.db.satellites.get_by_sat_no(int(sat_no))
                except Exception:
                    try:
                        self.db.satellites.create(sat_no=int(sat_no))
                        report.imported_satellites += 1
                    except Exception as e:
                        report.add_warning(f"Could not create satellite {sat_no}: {e}")

        # Insert state vectors one by one (they have auto-generated IDs)
        for _, row in df_mapped.iterrows():
            try:
                self.db.state_vectors.create(
                    sat_no=int(row["sat_no"]),
                    epoch=row["epoch"],
                    x_pos=row.get("x_pos", 0),
                    y_pos=row.get("y_pos", 0),
                    z_pos=row.get("z_pos", 0),
                    x_vel=row.get("x_vel", 0),
                    y_vel=row.get("y_vel", 0),
                    z_vel=row.get("z_vel", 0),
                    covariance=row.get("covariance"),
                    source=row.get("source", "MIGRATED"),
                    data_mode=row.get("data_mode", "REAL"),
                )
                report.imported_state_vectors += 1
            except Exception as e:
                report.add_error(f"state_vector_{row.get('sat_no', 'unknown')}", str(e))

        return report

    def _import_element_sets(
        self,
        df: pd.DataFrame,
        report: MigrationReport,
        **kwargs,
    ) -> MigrationReport:
        """Import TLE/element set records."""
        column_map = {
            "satNo": "sat_no",
            "argPerigee": "arg_perigee",
            "meanAnomaly": "mean_anomaly",
            "meanMotion": "mean_motion",
            "bStar": "b_star",
            "semiMajorAxis": "semi_major_axis_km",
        }

        df_mapped = df.rename(columns=column_map)

        # Ensure satellites exist
        if "sat_no" in df_mapped.columns:
            unique_sats = df_mapped["sat_no"].dropna().unique()
            for sat_no in unique_sats:
                try:
                    self.db.satellites.get_by_sat_no(int(sat_no))
                except Exception:
                    try:
                        self.db.satellites.create(sat_no=int(sat_no))
                        report.imported_satellites += 1
                    except Exception as e:
                        report.add_warning(f"Could not create satellite {sat_no}: {e}")

        # Insert element sets one by one
        for _, row in df_mapped.iterrows():
            try:
                self.db.element_sets.create(
                    sat_no=int(row["sat_no"]),
                    line1=row.get("line1", ""),
                    line2=row.get("line2", ""),
                    epoch=row.get("epoch"),
                    inclination=row.get("inclination"),
                    raan=row.get("raan"),
                    eccentricity=row.get("eccentricity"),
                    arg_perigee=row.get("arg_perigee"),
                    mean_anomaly=row.get("mean_anomaly"),
                    mean_motion=row.get("mean_motion"),
                    b_star=row.get("b_star"),
                    semi_major_axis_km=row.get("semi_major_axis_km"),
                    source=row.get("source", "MIGRATED"),
                )
                report.imported_element_sets += 1
            except Exception as e:
                report.add_error(f"element_set_{row.get('sat_no', 'unknown')}", str(e))

        return report

    def _import_satellites(
        self,
        df: pd.DataFrame,
        report: MigrationReport,
        **kwargs,
    ) -> MigrationReport:
        """Import satellite catalog records."""
        column_map = {
            "satNo": "sat_no",
            "cosparId": "cospar_id",
            "objectType": "object_type",
            "orbitalRegime": "orbital_regime",
            "launchDate": "launch_date",
            "decayDate": "decay_date",
            "massKg": "mass_kg",
            "crossSectionM2": "cross_section_m2",
            "dragCoeff": "drag_coeff",
            "srpCoeff": "srp_coeff",
        }

        df_mapped = df.rename(columns=column_map)

        for _, row in df_mapped.iterrows():
            try:
                self.db.satellites.create(
                    sat_no=int(row["sat_no"]),
                    name=row.get("name"),
                    cospar_id=row.get("cospar_id"),
                    object_type=row.get("object_type"),
                    orbital_regime=row.get("orbital_regime"),
                    launch_date=row.get("launch_date"),
                    mass_kg=row.get("mass_kg"),
                    cross_section_m2=row.get("cross_section_m2"),
                    drag_coeff=row.get("drag_coeff"),
                    srp_coeff=row.get("srp_coeff"),
                )
                report.imported_satellites += 1
            except Exception as e:
                report.add_error(f"satellite_{row.get('sat_no', 'unknown')}", str(e))

        return report

    def _import_structured_json(
        self,
        data: Dict[str, Any],
        dataset_name: str,
        report: MigrationReport,
    ) -> MigrationReport:
        """Import structured JSON with separate sections."""
        # Import observations
        if "observations" in data:
            obs_df = pd.DataFrame(data["observations"])
            report = self._import_observations(obs_df, report)

        # Import state vectors
        if "state_vectors" in data or "states" in data:
            sv_data = data.get("state_vectors", data.get("states", []))
            sv_df = pd.DataFrame(sv_data)
            report = self._import_state_vectors(sv_df, report)

        # Import element sets
        if "element_sets" in data or "tles" in data or "elsets" in data:
            el_data = data.get("element_sets", data.get("tles", data.get("elsets", [])))
            el_df = pd.DataFrame(el_data)
            report = self._import_element_sets(el_df, report)

        # Create dataset record
        if report.imported_observations > 0:
            try:
                params = data.get("metadata", data.get("params", {}))
                dataset_id = self.db.datasets.create(
                    name=dataset_name,
                    params=params,
                )
                report.imported_datasets = 1
            except Exception as e:
                report.add_error("dataset", str(e))

        return report

    def validate_migration(self) -> Dict[str, Any]:
        """
        Validate database integrity after migration.

        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "issues": [],
            "counts": {},
        }

        # Count records
        try:
            results["counts"]["satellites"] = self.db.execute(
                "SELECT COUNT(*) FROM satellites"
            ).fetchone()[0]
            results["counts"]["observations"] = self.db.execute(
                "SELECT COUNT(*) FROM observations"
            ).fetchone()[0]
            results["counts"]["state_vectors"] = self.db.execute(
                "SELECT COUNT(*) FROM state_vectors"
            ).fetchone()[0]
            results["counts"]["element_sets"] = self.db.execute(
                "SELECT COUNT(*) FROM element_sets"
            ).fetchone()[0]
            results["counts"]["datasets"] = self.db.execute(
                "SELECT COUNT(*) FROM datasets"
            ).fetchone()[0]
        except Exception as e:
            results["valid"] = False
            results["issues"].append(f"Count query failed: {e}")

        # Check referential integrity - observations with missing satellites
        try:
            orphaned_obs = self.db.execute("""
                SELECT COUNT(*) FROM observations o
                LEFT JOIN satellites s ON o.sat_no = s.sat_no
                WHERE s.sat_no IS NULL AND o.sat_no IS NOT NULL
            """).fetchone()[0]
            if orphaned_obs > 0:
                results["valid"] = False
                results["issues"].append(
                    f"{orphaned_obs} observations reference missing satellites"
                )
        except Exception as e:
            results["issues"].append(f"Referential integrity check failed: {e}")

        # Check for duplicate observations
        try:
            dup_obs = self.db.execute("""
                SELECT COUNT(*) - COUNT(DISTINCT id) FROM observations
            """).fetchone()[0]
            if dup_obs > 0:
                results["issues"].append(f"{dup_obs} duplicate observation IDs found")
        except Exception as e:
            results["issues"].append(f"Duplicate check failed: {e}")

        return results


def migrate_existing_data(
    source_dir: Union[str, Path],
    db_path: Optional[str] = None,
    verbose: bool = True,
) -> MigrationReport:
    """
    Convenience function to migrate all data from a directory.

    Args:
        source_dir: Directory containing data files
        db_path: Path to database file
        verbose: Print progress

    Returns:
        MigrationReport with results
    """
    migration = DataMigration(db_path)

    if verbose:
        logger.info(f"Starting migration from {source_dir}")

    report = migration.import_dataset_directory(source_dir)

    if verbose:
        print(report.summary())

    # Validate
    validation = migration.validate_migration()
    if not validation["valid"]:
        logger.warning(f"Validation issues: {validation['issues']}")

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate data files to UCT Benchmark database")
    parser.add_argument("source", help="Source file or directory")
    parser.add_argument("--db", "-d", help="Database path")
    parser.add_argument(
        "--type",
        "-t",
        choices=["observations", "state_vectors", "element_sets", "satellites"],
        help="Data type (for single file import)",
    )
    parser.add_argument("--name", "-n", help="Dataset name")
    args = parser.parse_args()

    source_path = Path(args.source)

    migration = DataMigration(args.db)

    if source_path.is_dir():
        report = migration.import_dataset_directory(source_path, args.name)
    elif source_path.suffix == ".parquet":
        if not args.type:
            print("Error: --type required for Parquet files")
            exit(1)
        report = migration.import_from_parquet(source_path, args.type)
    elif source_path.suffix == ".json":
        report = migration.import_from_json(source_path, args.name)
    else:
        print(f"Error: Unsupported file type: {source_path.suffix}")
        exit(1)

    print(report.summary())
