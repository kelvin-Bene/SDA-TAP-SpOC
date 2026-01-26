"""
Data ingestion pipeline for UCT Benchmark database.

Provides utilities for ingesting data from external APIs (UDL, Space-Track, etc.)
into the database with validation, deduplication, and error handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

import pandas as pd
from loguru import logger

if TYPE_CHECKING:
    from .connection import DatabaseManager


@dataclass
class IngestionReport:
    """Report of data ingestion results."""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_records: int = 0
    inserted_records: int = 0
    duplicate_records: int = 0
    failed_records: int = 0
    successes: Dict[int, int] = field(default_factory=dict)  # sat_no -> count
    failures: Dict[int, str] = field(default_factory=dict)  # sat_no -> error message
    validation_errors: List[str] = field(default_factory=list)

    def add_success(self, sat_no: int, count: int) -> None:
        """Record a successful ingestion for a satellite."""
        self.successes[sat_no] = count
        self.inserted_records += count

    def add_failure(self, sat_no: int, error: str) -> None:
        """Record a failed ingestion for a satellite."""
        self.failures[sat_no] = error
        self.failed_records += 1

    def add_validation_error(self, error: str) -> None:
        """Record a validation error."""
        self.validation_errors.append(error)

    def finalize(self) -> None:
        """Mark the report as complete."""
        self.end_time = datetime.now()
        self.total_records = self.inserted_records + self.duplicate_records + self.failed_records

    @property
    def duration_seconds(self) -> float:
        """Get the duration of the ingestion in seconds."""
        if self.end_time is None:
            return (datetime.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.inserted_records / self.total_records) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to a dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_records": self.total_records,
            "inserted_records": self.inserted_records,
            "duplicate_records": self.duplicate_records,
            "failed_records": self.failed_records,
            "success_rate": self.success_rate,
            "satellites_processed": len(self.successes) + len(self.failures),
            "satellites_succeeded": len(self.successes),
            "satellites_failed": len(self.failures),
            "validation_errors": self.validation_errors,
        }

    def __str__(self) -> str:
        return (
            f"IngestionReport: {self.inserted_records} inserted, "
            f"{self.duplicate_records} duplicates, {self.failed_records} failed "
            f"({self.success_rate:.1f}% success rate)"
        )


class ValidationError(Exception):
    """Raised when data validation fails."""

    pass


class DataIngestionPipeline:
    """
    Pipeline for ingesting data from external APIs into the database.

    Provides:
    - Data fetching from UDL, Space-Track, CelesTrak
    - Validation and normalization
    - Deduplication
    - Batch insertion
    - Progress reporting
    """

    def __init__(self, db: "DatabaseManager"):
        """
        Initialize the ingestion pipeline.

        Args:
            db: DatabaseManager instance
        """
        self.db = db

    def ingest_observations_from_dataframe(
        self,
        df: pd.DataFrame,
        source: str = "UNKNOWN",
        validate: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> IngestionReport:
        """
        Ingest observation data from a DataFrame.

        Args:
            df: DataFrame with observation data
            source: Data source identifier
            validate: Whether to validate data before insertion
            progress_callback: Optional callback for progress updates

        Returns:
            IngestionReport with ingestion statistics
        """
        report = IngestionReport()

        if df.empty:
            report.finalize()
            return report

        # Validate if requested
        if validate:
            try:
                df = self._validate_observations(df)
            except ValidationError as e:
                report.add_validation_error(str(e))
                report.finalize()
                return report

        # Normalize column names
        df = self._normalize_observation_columns(df)

        # Add metadata
        if "data_mode" not in df.columns:
            df["data_mode"] = "REAL"

        # Insert in batches
        batch_size = 10000
        total_batches = (len(df) + batch_size - 1) // batch_size

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]

            try:
                inserted = self.db.observations.bulk_insert(batch)
                report.inserted_records += inserted
                report.duplicate_records += len(batch) - inserted
            except Exception as e:
                logger.error(f"Failed to insert observation batch: {e}")
                report.failed_records += len(batch)

            if progress_callback:
                progress_callback(min(i + batch_size, len(df)), len(df))

        report.finalize()
        return report

    def ingest_state_vectors_from_dataframe(
        self,
        df: pd.DataFrame,
        source: str = "UNKNOWN",
        validate: bool = True,
    ) -> IngestionReport:
        """
        Ingest state vector data from a DataFrame.

        Args:
            df: DataFrame with state vector data
            source: Data source identifier
            validate: Whether to validate data before insertion

        Returns:
            IngestionReport with ingestion statistics
        """
        report = IngestionReport()

        if df.empty:
            report.finalize()
            return report

        # Validate if requested
        if validate:
            try:
                df = self._validate_state_vectors(df)
            except ValidationError as e:
                report.add_validation_error(str(e))
                report.finalize()
                return report

        # Normalize column names
        df = self._normalize_state_vector_columns(df)

        # Add source if not present
        if "source" not in df.columns:
            df["source"] = source

        try:
            inserted = self.db.state_vectors.bulk_insert(df)
            report.inserted_records = inserted
            report.duplicate_records = len(df) - inserted
        except Exception as e:
            logger.error(f"Failed to insert state vectors: {e}")
            report.failed_records = len(df)

        report.finalize()
        return report

    def ingest_element_sets_from_dataframe(
        self,
        df: pd.DataFrame,
        source: str = "UNKNOWN",
        validate: bool = True,
    ) -> IngestionReport:
        """
        Ingest element set (TLE) data from a DataFrame.

        Args:
            df: DataFrame with element set data
            source: Data source identifier
            validate: Whether to validate data before insertion

        Returns:
            IngestionReport with ingestion statistics
        """
        report = IngestionReport()

        if df.empty:
            report.finalize()
            return report

        # Normalize column names
        df = self._normalize_element_set_columns(df)

        # Add source if not present
        if "source" not in df.columns:
            df["source"] = source

        try:
            inserted = self.db.element_sets.bulk_insert(df)
            report.inserted_records = inserted
            report.duplicate_records = len(df) - inserted
        except Exception as e:
            logger.error(f"Failed to insert element sets: {e}")
            report.failed_records = len(df)

        report.finalize()
        return report

    def ingest_satellites_from_dataframe(
        self,
        df: pd.DataFrame,
        source: str = "UNKNOWN",
    ) -> IngestionReport:
        """
        Ingest satellite catalog data from a DataFrame.

        Args:
            df: DataFrame with satellite data
            source: Data source identifier

        Returns:
            IngestionReport with ingestion statistics
        """
        report = IngestionReport()

        if df.empty:
            report.finalize()
            return report

        # Normalize column names
        df = self._normalize_satellite_columns(df)

        try:
            inserted = self.db.satellites.bulk_upsert(df)
            report.inserted_records = inserted
        except Exception as e:
            logger.error(f"Failed to insert satellites: {e}")
            report.failed_records = len(df)

        report.finalize()
        return report

    def ingest_from_udl(
        self,
        token: str,
        sat_ids: List[int],
        time_window: Tuple[datetime, datetime],
        services: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> IngestionReport:
        """
        Ingest data from UDL API.

        This is a convenience method that fetches data from UDL and inserts it
        into the database in a single operation.

        Args:
            token: UDL authentication token
            sat_ids: List of satellite NORAD numbers
            time_window: Tuple of (start_time, end_time)
            services: List of UDL services to query (default: eoobservation, statevector)
            progress_callback: Optional callback for progress updates

        Returns:
            IngestionReport with combined ingestion statistics
        """
        # Import API functions lazily to avoid circular imports
        try:
            from uct_benchmark.api.apiIntegration import (
                asyncUDLBatchQuery,
                datetimeToUDL,
            )
        except ImportError:
            logger.error("Could not import UDL API functions")
            report = IngestionReport()
            report.add_validation_error("UDL API functions not available")
            report.finalize()
            return report

        if services is None:
            services = ["eoobservation", "statevector"]

        report = IngestionReport()
        start_time_str = datetimeToUDL(time_window[0])
        end_time_str = datetimeToUDL(time_window[1])

        for i, sat_id in enumerate(sat_ids):
            try:
                for service in services:
                    params = {
                        "satNo": str(sat_id),
                        "obTime"
                        if service == "eoobservation"
                        else "epoch": f"{start_time_str}..{end_time_str}",
                        "dataMode": "REAL",
                    }

                    # Build params list for batch query
                    params_list = [params]
                    result_df = asyncUDLBatchQuery(token, service, params_list, dt=0.1)

                    if result_df is not None and not result_df.empty:
                        if service == "eoobservation":
                            sub_report = self.ingest_observations_from_dataframe(
                                result_df, source="UDL"
                            )
                        elif service == "statevector":
                            sub_report = self.ingest_state_vectors_from_dataframe(
                                result_df, source="UDL"
                            )
                        else:
                            continue

                        report.inserted_records += sub_report.inserted_records
                        report.duplicate_records += sub_report.duplicate_records

                report.add_success(sat_id, report.inserted_records)

            except Exception as e:
                logger.error(f"Failed to ingest data for satellite {sat_id}: {e}")
                report.add_failure(sat_id, str(e))

            if progress_callback:
                progress_callback(i + 1, len(sat_ids))

        report.finalize()
        return report

    def _validate_observations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate observation data before insertion."""
        # Check required fields
        required = ["id", "ob_time"]
        missing = [col for col in required if col not in df.columns]

        # Check for alternative column names
        alt_names = {
            "id": ["observationId", "observation_id"],
            "ob_time": ["obTime", "observation_time", "time"],
        }

        for req_col in list(missing):
            for alt in alt_names.get(req_col, []):
                if alt in df.columns:
                    df = df.rename(columns={alt: req_col})
                    missing.remove(req_col)
                    break

        if missing:
            raise ValidationError(f"Missing required columns: {missing}")

        # Validate RA/Dec ranges if present
        if "ra" in df.columns:
            invalid_ra = (df["ra"] < 0) | (df["ra"] > 360)
            if invalid_ra.any():
                logger.warning(
                    f"Found {invalid_ra.sum()} observations with RA outside [0, 360] range"
                )

        if "declination" in df.columns:
            invalid_dec = (df["declination"] < -90) | (df["declination"] > 90)
            if invalid_dec.any():
                logger.warning(
                    f"Found {invalid_dec.sum()} observations with declination outside [-90, 90] range"
                )

        return df

    def _validate_state_vectors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate state vector data before insertion."""
        required = ["sat_no", "epoch", "x_pos", "y_pos", "z_pos", "x_vel", "y_vel", "z_vel"]

        # Check for alternative column names
        alt_names = {
            "sat_no": ["satNo", "norad_id", "satellite_id"],
            "x_pos": ["xPos", "x", "pos_x"],
            "y_pos": ["yPos", "y", "pos_y"],
            "z_pos": ["zPos", "z", "pos_z"],
            "x_vel": ["xVel", "vx", "vel_x"],
            "y_vel": ["yVel", "vy", "vel_y"],
            "z_vel": ["zVel", "vz", "vel_z"],
        }

        for req_col in required:
            if req_col not in df.columns:
                for alt in alt_names.get(req_col, []):
                    if alt in df.columns:
                        df = df.rename(columns={alt: req_col})
                        break

        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing required columns: {missing}")

        return df

    def _normalize_observation_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize observation column names to match database schema."""
        column_map = {
            "observationId": "id",
            "obTime": "ob_time",
            "satNo": "sat_no",
            "rightAscension": "ra",
            "declination": "declination",
            "sensorName": "sensor_name",
            "dataMode": "data_mode",
            "trackId": "track_id",
            "range": "range_km",
            "rangeRate": "range_rate_km_s",
        }

        # Only rename columns that exist
        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        if rename_dict:
            df = df.rename(columns=rename_dict)

        return df

    def _normalize_state_vector_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize state vector column names to match database schema."""
        column_map = {
            "satNo": "sat_no",
            "xPos": "x_pos",
            "yPos": "y_pos",
            "zPos": "z_pos",
            "xVel": "x_vel",
            "yVel": "y_vel",
            "zVel": "z_vel",
            "dataMode": "data_mode",
        }

        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        if rename_dict:
            df = df.rename(columns=rename_dict)

        return df

    def _normalize_element_set_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize element set column names to match database schema."""
        column_map = {
            "satNo": "sat_no",
            "noradCatId": "sat_no",
            "tleLine1": "line1",
            "tleLine2": "line2",
            "inclination": "inclination",
            "eccentricity": "eccentricity",
            "argOfPericenter": "arg_perigee",
            "meanAnomaly": "mean_anomaly",
            "meanMotion": "mean_motion",
            "bstar": "b_star",
            "semiMajorAxis": "semi_major_axis_km",
            "period": "period_minutes",
            "raOfAscNode": "raan",
        }

        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        if rename_dict:
            df = df.rename(columns=rename_dict)

        return df

    def _normalize_satellite_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize satellite column names to match database schema."""
        column_map = {
            "satNo": "sat_no",
            "noradCatId": "sat_no",
            "objectName": "name",
            "satName": "name",
            "objectType": "object_type",
            "launchDate": "launch_date",
            "decayDate": "decay_date",
            "orbitalRegime": "orbital_regime",
            "intlDes": "cospar_id",
            "mass": "mass_kg",
            "crossSection": "cross_section_m2",
        }

        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        if rename_dict:
            df = df.rename(columns=rename_dict)

        return df

    def sync_from_existing_parquet(
        self,
        parquet_path: str,
        data_type: str = "observations",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> IngestionReport:
        """
        Sync data from an existing Parquet file into the database.

        This is useful for migrating existing data to the database.

        Args:
            parquet_path: Path to the Parquet file
            data_type: Type of data (observations, state_vectors, element_sets, satellites)
            progress_callback: Optional callback for progress updates

        Returns:
            IngestionReport with ingestion statistics
        """
        from pathlib import Path

        path = Path(parquet_path)
        if not path.exists():
            report = IngestionReport()
            report.add_validation_error(f"File not found: {parquet_path}")
            report.finalize()
            return report

        df = pd.read_parquet(path)
        logger.info(f"Loaded {len(df)} records from {parquet_path}")

        if data_type == "observations":
            return self.ingest_observations_from_dataframe(
                df, source="PARQUET", progress_callback=progress_callback
            )
        elif data_type == "state_vectors":
            return self.ingest_state_vectors_from_dataframe(df, source="PARQUET")
        elif data_type == "element_sets":
            return self.ingest_element_sets_from_dataframe(df, source="PARQUET")
        elif data_type == "satellites":
            return self.ingest_satellites_from_dataframe(df, source="PARQUET")
        else:
            report = IngestionReport()
            report.add_validation_error(f"Unknown data type: {data_type}")
            report.finalize()
            return report
