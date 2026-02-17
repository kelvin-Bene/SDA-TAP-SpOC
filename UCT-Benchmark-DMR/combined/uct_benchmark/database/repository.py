"""
Repository pattern implementation for UCT Benchmark database.

Provides data access abstraction for all entity types.
Supports both DuckDB and PostgreSQL backends.
"""

import json
from abc import ABC
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd

if TYPE_CHECKING:
    from .connection import DatabaseManager


class BaseRepository(ABC):
    """
    Abstract base class for all repositories.

    Provides common database operations and query utilities.
    """

    def __init__(self, db: "DatabaseManager"):
        """
        Initialize the repository.

        Args:
            db: DatabaseManager instance for database operations
        """
        self.db = db

    @property
    def backend(self) -> str:
        """Get the database backend name."""
        return self.db.backend

    @property
    def adapter(self):
        """Get the database adapter."""
        return self.db.adapter

    def _convert_query(self, query: str) -> str:
        """Convert query placeholders to backend-specific format."""
        return self.adapter.convert_placeholders(query)

    def execute(self, query: str, params: tuple = ()):
        """Execute a SQL query and return the result."""
        return self.db.execute(query, params)

    def executemany(self, query: str, params_list: list) -> None:
        """Execute a query with multiple parameter sets."""
        self.db.executemany(query, params_list)

    def to_dataframe(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Execute a query and return results as a DataFrame."""
        return self.adapter.fetchdf(self._convert_query(query), params)

    def fetchone(self, query: str, params: tuple = ()) -> Optional[tuple]:
        """Execute a query and return a single row."""
        return self.adapter.fetchone(self._convert_query(query), params)

    def fetchall(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute a query and return all rows."""
        return self.adapter.fetchall(self._convert_query(query), params)

    def _get_conflict_sql(
        self, action: str = "nothing", conflict_columns: Optional[List[str]] = None
    ) -> str:
        """
        Get backend-specific conflict handling SQL.

        Args:
            action: 'nothing' or 'update'
            conflict_columns: Columns for conflict detection

        Returns:
            SQL clause for conflict handling
        """
        if not conflict_columns:
            return ""
        cols = ", ".join(conflict_columns)
        if action == "nothing":
            return f"ON CONFLICT ({cols}) DO NOTHING"
        return f"ON CONFLICT ({cols}) DO UPDATE SET"

    def _get_insert_ignore_sql(self, table: str, columns: List[str], conflict_columns: List[str]) -> str:
        """
        Get backend-specific INSERT IGNORE equivalent.

        Args:
            table: Table name
            columns: Columns to insert
            conflict_columns: Columns for conflict detection

        Returns:
            Full INSERT statement with conflict handling
        """
        placeholders = ", ".join(["?"] * len(columns))
        cols = ", ".join(columns)
        conflict_cols = ", ".join(conflict_columns)
        return f"""
            INSERT INTO {table} ({cols})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_cols}) DO NOTHING
        """


class SatelliteRepository(BaseRepository):
    """Repository for satellite catalog data."""

    def create(
        self,
        sat_no: int,
        name: Optional[str] = None,
        cospar_id: Optional[str] = None,
        object_type: Optional[str] = None,
        orbital_regime: Optional[str] = None,
        launch_date: Optional[datetime] = None,
        **kwargs,
    ) -> int:
        """
        Create a new satellite record.

        Args:
            sat_no: NORAD catalog number
            name: Satellite name
            cospar_id: COSPAR ID
            object_type: PAYLOAD, ROCKET BODY, DEBRIS
            orbital_regime: LEO, MEO, GEO, HEO
            launch_date: Launch date
            **kwargs: Additional fields (mass_kg, cross_section_m2, etc.)

        Returns:
            The satellite number (sat_no)
        """
        fields = ["sat_no", "name", "cospar_id", "object_type", "orbital_regime"]
        values = [sat_no, name, cospar_id, object_type, orbital_regime]

        if launch_date:
            fields.append("launch_date")
            values.append(launch_date)

        for key in ["mass_kg", "cross_section_m2", "drag_coeff", "srp_coeff", "decay_date"]:
            if key in kwargs:
                fields.append(key)
                values.append(kwargs[key])

        placeholders = ", ".join(["?"] * len(values))
        field_names = ", ".join(fields)

        # Use ON CONFLICT DO NOTHING for both backends
        query = f"""
            INSERT INTO satellites ({field_names}) VALUES ({placeholders})
            ON CONFLICT (sat_no) DO NOTHING
        """
        self.execute(query, tuple(values))
        return sat_no

    def get(self, sat_no: int) -> Optional[pd.Series]:
        """
        Get a satellite by NORAD number.

        Args:
            sat_no: NORAD catalog number

        Returns:
            Satellite data as a Series, or None if not found
        """
        df = self.to_dataframe("SELECT * FROM satellites WHERE sat_no = ?", (sat_no,))
        return df.iloc[0] if len(df) > 0 else None

    def get_all(self) -> pd.DataFrame:
        """Get all satellites."""
        return self.to_dataframe("SELECT * FROM satellites ORDER BY sat_no")

    def get_by_regime(self, regime: str) -> pd.DataFrame:
        """
        Get all satellites in a specific orbital regime.

        Args:
            regime: LEO, MEO, GEO, or HEO

        Returns:
            DataFrame of satellites
        """
        return self.to_dataframe(
            "SELECT * FROM satellites WHERE orbital_regime = ? ORDER BY sat_no",
            (regime,),
        )

    def update(self, sat_no: int, **kwargs) -> bool:
        """
        Update satellite fields.

        Args:
            sat_no: NORAD catalog number
            **kwargs: Fields to update

        Returns:
            True if update was successful
        """
        if not kwargs:
            return False

        # Add updated_at timestamp
        kwargs["updated_at"] = datetime.now()

        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [sat_no]

        self.execute(
            f"UPDATE satellites SET {set_clause} WHERE sat_no = ?",
            tuple(values),
        )
        return True

    def delete(self, sat_no: int) -> bool:
        """
        Delete a satellite record.

        Args:
            sat_no: NORAD catalog number

        Returns:
            True if deletion was successful
        """
        self.execute("DELETE FROM satellites WHERE sat_no = ?", (sat_no,))
        return True

    def upsert(self, sat_no: int, **kwargs) -> int:
        """
        Insert or update a satellite record.

        Args:
            sat_no: NORAD catalog number
            **kwargs: Satellite fields

        Returns:
            The satellite number
        """
        existing = self.get(sat_no)
        if existing is not None:
            self.update(sat_no, **kwargs)
        else:
            self.create(sat_no, **kwargs)
        return sat_no

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        Bulk upsert satellites from a DataFrame.

        Args:
            df: DataFrame with satellite data (must have 'sat_no' column)

        Returns:
            Number of records processed
        """
        count = 0
        for _, row in df.iterrows():
            sat_no = int(row["sat_no"])
            data = row.dropna().to_dict()
            data.pop("sat_no", None)
            self.upsert(sat_no, **data)
            count += 1
        return count

    def count(self) -> int:
        """Get the total number of satellites."""
        result = self.fetchone("SELECT COUNT(*) FROM satellites")
        return result[0] if result else 0


class ObservationRepository(BaseRepository):
    """Repository for observation data access."""

    def get_by_id(self, obs_id: str) -> Optional[pd.Series]:
        """
        Get an observation by ID.

        Args:
            obs_id: Observation ID

        Returns:
            Observation data as a Series, or None if not found
        """
        df = self.to_dataframe("SELECT * FROM observations WHERE id = ?", (obs_id,))
        return df.iloc[0] if len(df) > 0 else None

    def get_by_satellite_time_window(
        self,
        sat_no: int,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """
        Query observations for a satellite within a time window.

        Args:
            sat_no: NORAD catalog number
            start_time: Start of time window
            end_time: End of time window

        Returns:
            DataFrame of observations
        """
        query = """
            SELECT * FROM observations
            WHERE sat_no = ?
              AND ob_time BETWEEN ? AND ?
            ORDER BY ob_time
        """
        return self.to_dataframe(query, (sat_no, start_time, end_time))

    def get_by_time_window(
        self,
        start_time: datetime,
        end_time: datetime,
        data_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Query all observations within a time window.

        Args:
            start_time: Start of time window
            end_time: End of time window
            data_mode: Optional filter for REAL or SIMULATED

        Returns:
            DataFrame of observations
        """
        if data_mode:
            query = """
                SELECT * FROM observations
                WHERE ob_time BETWEEN ? AND ?
                  AND data_mode = ?
                ORDER BY ob_time
            """
            return self.to_dataframe(query, (start_time, end_time, data_mode))
        else:
            query = """
                SELECT * FROM observations
                WHERE ob_time BETWEEN ? AND ?
                ORDER BY ob_time
            """
            return self.to_dataframe(query, (start_time, end_time))

    def get_by_regime(
        self,
        regime: str,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """
        Query observations for all satellites in an orbital regime.

        Args:
            regime: LEO, MEO, GEO, or HEO
            start_time: Start of time window
            end_time: End of time window

        Returns:
            DataFrame of observations
        """
        query = """
            SELECT o.* FROM observations o
            JOIN satellites s ON o.sat_no = s.sat_no
            WHERE s.orbital_regime = ?
              AND o.ob_time BETWEEN ? AND ?
            ORDER BY o.ob_time
        """
        return self.to_dataframe(query, (regime, start_time, end_time))

    def get_uct_observations(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Query observations flagged as UCT (decorrelated).

        Args:
            start_time: Optional start of time window
            end_time: Optional end of time window

        Returns:
            DataFrame of UCT observations
        """
        if start_time and end_time:
            query = """
                SELECT * FROM observations
                WHERE is_uct = TRUE
                  AND ob_time BETWEEN ? AND ?
                ORDER BY ob_time
            """
            return self.to_dataframe(query, (start_time, end_time))
        else:
            return self.to_dataframe(
                "SELECT * FROM observations WHERE is_uct = TRUE ORDER BY ob_time"
            )

    def bulk_insert(self, df: pd.DataFrame) -> int:
        """
        Bulk insert observations from a DataFrame.

        Args:
            df: DataFrame with observation data

        Returns:
            Number of records inserted
        """
        if df.empty:
            return 0

        # Valid columns for observations table
        valid_columns = [
            "id",
            "sat_no",
            "ob_time",
            "ra",
            "declination",
            "range_km",
            "range_rate_km_s",
            "azimuth",
            "elevation",
            "sensor_name",
            "data_mode",
            "track_id",
            "is_uct",
            "is_simulated",
            "created_at",
        ]

        # Filter to only columns that exist in DataFrame and are valid
        available_columns = [c for c in valid_columns if c in df.columns]
        insert_df = df[available_columns].copy()

        # Use adapter's bulk insert method
        return self.adapter.bulk_insert_df(
            table="observations",
            df=insert_df,
            columns=available_columns,
            on_conflict="nothing",
            conflict_columns=["id"],
        )

    def count_by_satellite(self, sat_no: int) -> int:
        """
        Count observations for a satellite.

        Args:
            sat_no: NORAD catalog number

        Returns:
            Number of observations
        """
        result = self.fetchone("SELECT COUNT(*) FROM observations WHERE sat_no = ?", (sat_no,))
        return result[0] if result else 0

    def get_track_gaps(self, sat_no: int, limit: int = 10) -> pd.DataFrame:
        """
        Find the largest gaps in observation tracks for a satellite.

        Args:
            sat_no: NORAD catalog number
            limit: Maximum number of gaps to return

        Returns:
            DataFrame with gap information
        """
        query = """
            WITH sorted_obs AS (
                SELECT
                    sat_no,
                    ob_time,
                    LAG(ob_time) OVER (PARTITION BY sat_no ORDER BY ob_time) as prev_time
                FROM observations
                WHERE sat_no = ?
            )
            SELECT
                sat_no,
                ob_time,
                prev_time,
                EXTRACT(EPOCH FROM (ob_time - prev_time)) / 3600 as gap_hours
            FROM sorted_obs
            WHERE prev_time IS NOT NULL
            ORDER BY gap_hours DESC
            LIMIT ?
        """
        return self.to_dataframe(query, (sat_no, limit))

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get observation statistics per satellite.

        Args:
            start_time: Optional start of time window
            end_time: Optional end of time window

        Returns:
            DataFrame with statistics
        """
        if start_time and end_time:
            query = """
                SELECT
                    sat_no,
                    COUNT(*) as obs_count,
                    MIN(ob_time) as first_obs,
                    MAX(ob_time) as last_obs,
                    COUNT(DISTINCT track_id) as track_count
                FROM observations
                WHERE ob_time BETWEEN ? AND ?
                GROUP BY sat_no
                ORDER BY obs_count DESC
            """
            return self.to_dataframe(query, (start_time, end_time))
        else:
            query = """
                SELECT
                    sat_no,
                    COUNT(*) as obs_count,
                    MIN(ob_time) as first_obs,
                    MAX(ob_time) as last_obs,
                    COUNT(DISTINCT track_id) as track_count
                FROM observations
                GROUP BY sat_no
                ORDER BY obs_count DESC
            """
            return self.to_dataframe(query)

    def delete_by_satellite(self, sat_no: int) -> int:
        """
        Delete all observations for a satellite.

        Args:
            sat_no: NORAD catalog number

        Returns:
            Number of records deleted
        """
        count = self.count_by_satellite(sat_no)
        self.execute("DELETE FROM observations WHERE sat_no = ?", (sat_no,))
        return count

    def count(self) -> int:
        """Get total observation count."""
        result = self.fetchone("SELECT COUNT(*) FROM observations")
        return result[0] if result else 0


class StateVectorRepository(BaseRepository):
    """Repository for state vector data access."""

    def create(
        self,
        sat_no: int,
        epoch: datetime,
        x_pos: float,
        y_pos: float,
        z_pos: float,
        x_vel: float,
        y_vel: float,
        z_vel: float,
        covariance: Optional[List[List[float]]] = None,
        source: Optional[str] = None,
        data_mode: Optional[str] = None,
    ) -> int:
        """
        Create a new state vector record.

        Args:
            sat_no: NORAD catalog number
            epoch: State vector epoch
            x_pos, y_pos, z_pos: Position in km (J2000 ECI)
            x_vel, y_vel, z_vel: Velocity in km/s (J2000 ECI)
            covariance: Optional 6x6 covariance matrix
            source: Data source (UDL, SPACE_TRACK, PROPAGATED)
            data_mode: REAL or SIMULATED

        Returns:
            The inserted record ID, or -1 if skipped due to duplicate
        """
        cov_json = json.dumps(covariance) if covariance else None

        # Use ON CONFLICT to handle duplicate (sat_no, epoch, source) gracefully
        # This prevents transaction abort in PostgreSQL when duplicates exist
        result = self.fetchone(
            """
            INSERT INTO state_vectors (sat_no, epoch, x_pos, y_pos, z_pos,
                                        x_vel, y_vel, z_vel, covariance, source, data_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (sat_no, epoch, source) DO NOTHING
            RETURNING id
            """,
            (sat_no, epoch, x_pos, y_pos, z_pos, x_vel, y_vel, z_vel, cov_json, source, data_mode),
        )
        return result[0] if result else -1

    def get(self, sv_id: int) -> Optional[pd.Series]:
        """
        Get a state vector by ID.

        Args:
            sv_id: State vector ID

        Returns:
            State vector data as a Series, or None if not found
        """
        df = self.to_dataframe("SELECT * FROM state_vectors WHERE id = ?", (sv_id,))
        return df.iloc[0] if len(df) > 0 else None

    def get_by_satellite_epoch(
        self,
        sat_no: int,
        epoch: datetime,
        tolerance_seconds: float = 60.0,
    ) -> Optional[pd.Series]:
        """
        Get a state vector for a satellite at a specific epoch.

        Args:
            sat_no: NORAD catalog number
            epoch: Target epoch
            tolerance_seconds: Time tolerance in seconds

        Returns:
            Closest state vector, or None if not found
        """
        query = """
            SELECT * FROM state_vectors
            WHERE sat_no = ?
              AND ABS(EXTRACT(EPOCH FROM (epoch - ?))) < ?
            ORDER BY ABS(EXTRACT(EPOCH FROM (epoch - ?)))
            LIMIT 1
        """
        df = self.to_dataframe(query, (sat_no, epoch, tolerance_seconds, epoch))
        return df.iloc[0] if len(df) > 0 else None

    def get_by_satellite_time_window(
        self,
        sat_no: int,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """
        Get all state vectors for a satellite in a time window.

        Args:
            sat_no: NORAD catalog number
            start_time: Start of time window
            end_time: End of time window

        Returns:
            DataFrame of state vectors
        """
        query = """
            SELECT * FROM state_vectors
            WHERE sat_no = ?
              AND epoch BETWEEN ? AND ?
            ORDER BY epoch
        """
        return self.to_dataframe(query, (sat_no, start_time, end_time))

    def get_latest(self, sat_no: int) -> Optional[pd.Series]:
        """
        Get the most recent state vector for a satellite.

        Args:
            sat_no: NORAD catalog number

        Returns:
            Latest state vector, or None if not found
        """
        df = self.to_dataframe(
            "SELECT * FROM state_vectors WHERE sat_no = ? ORDER BY epoch DESC LIMIT 1",
            (sat_no,),
        )
        return df.iloc[0] if len(df) > 0 else None

    def bulk_insert(self, df: pd.DataFrame) -> int:
        """
        Bulk insert state vectors from a DataFrame.

        Args:
            df: DataFrame with state vector data

        Returns:
            Number of records inserted
        """
        if df.empty:
            return 0

        # Prepare DataFrame
        insert_df = df.copy()

        # Ensure covariance is JSON serialized
        if "covariance" in insert_df.columns:
            insert_df["covariance"] = insert_df["covariance"].apply(
                lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x
            )

        columns = [
            "sat_no", "epoch", "x_pos", "y_pos", "z_pos",
            "x_vel", "y_vel", "z_vel", "covariance", "source", "data_mode"
        ]
        available_columns = [c for c in columns if c in insert_df.columns]

        return self.adapter.bulk_insert_df(
            table="state_vectors",
            df=insert_df,
            columns=available_columns,
            on_conflict="nothing",
            conflict_columns=["sat_no", "epoch", "source"],
        )

    def count(self) -> int:
        """Get total state vector count."""
        result = self.fetchone("SELECT COUNT(*) FROM state_vectors")
        return result[0] if result else 0


class ElementSetRepository(BaseRepository):
    """Repository for TLE/element set data access."""

    def create(
        self,
        sat_no: int,
        line1: str,
        line2: str,
        epoch: datetime,
        inclination: Optional[float] = None,
        raan: Optional[float] = None,
        eccentricity: Optional[float] = None,
        arg_perigee: Optional[float] = None,
        mean_anomaly: Optional[float] = None,
        mean_motion: Optional[float] = None,
        b_star: Optional[float] = None,
        semi_major_axis_km: Optional[float] = None,
        period_minutes: Optional[float] = None,
        source: Optional[str] = None,
    ) -> int:
        """
        Create a new element set record.

        Args:
            sat_no: NORAD catalog number
            line1: TLE line 1
            line2: TLE line 2
            epoch: Element set epoch
            inclination: Inclination in degrees
            raan: Right Ascension of Ascending Node in degrees
            eccentricity: Eccentricity
            arg_perigee: Argument of Perigee in degrees
            mean_anomaly: Mean Anomaly in degrees
            mean_motion: Mean motion in rev/day
            b_star: B* drag term
            semi_major_axis_km: Semi-major axis in km
            period_minutes: Orbital period in minutes
            source: Data source

        Returns:
            The inserted record ID, or -1 if skipped due to duplicate
        """
        # Use ON CONFLICT to handle duplicate (sat_no, epoch) gracefully
        # This prevents transaction abort in PostgreSQL when duplicates exist
        result = self.fetchone(
            """
            INSERT INTO element_sets (sat_no, line1, line2, epoch, inclination, raan,
                                       eccentricity, arg_perigee, mean_anomaly, mean_motion,
                                       b_star, semi_major_axis_km, period_minutes, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (sat_no, epoch) DO NOTHING
            RETURNING id
            """,
            (
                sat_no,
                line1,
                line2,
                epoch,
                inclination,
                raan,
                eccentricity,
                arg_perigee,
                mean_anomaly,
                mean_motion,
                b_star,
                semi_major_axis_km,
                period_minutes,
                source,
            ),
        )
        return result[0] if result else -1

    def get(self, elset_id: int) -> Optional[pd.Series]:
        """
        Get an element set by ID.

        Args:
            elset_id: Element set ID

        Returns:
            Element set data as a Series, or None if not found
        """
        df = self.to_dataframe("SELECT * FROM element_sets WHERE id = ?", (elset_id,))
        return df.iloc[0] if len(df) > 0 else None

    def get_by_satellite_epoch(
        self,
        sat_no: int,
        epoch: datetime,
        tolerance_seconds: float = 3600.0,
    ) -> Optional[pd.Series]:
        """
        Get an element set for a satellite at a specific epoch.

        Args:
            sat_no: NORAD catalog number
            epoch: Target epoch
            tolerance_seconds: Time tolerance in seconds

        Returns:
            Closest element set, or None if not found
        """
        query = """
            SELECT * FROM element_sets
            WHERE sat_no = ?
              AND ABS(EXTRACT(EPOCH FROM (epoch - ?))) < ?
            ORDER BY ABS(EXTRACT(EPOCH FROM (epoch - ?)))
            LIMIT 1
        """
        df = self.to_dataframe(query, (sat_no, epoch, tolerance_seconds, epoch))
        return df.iloc[0] if len(df) > 0 else None

    def get_by_satellite_time_window(
        self,
        sat_no: int,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """
        Get all element sets for a satellite in a time window.

        Args:
            sat_no: NORAD catalog number
            start_time: Start of time window
            end_time: End of time window

        Returns:
            DataFrame of element sets
        """
        query = """
            SELECT * FROM element_sets
            WHERE sat_no = ?
              AND epoch BETWEEN ? AND ?
            ORDER BY epoch
        """
        return self.to_dataframe(query, (sat_no, start_time, end_time))

    def get_latest(self, sat_no: int) -> Optional[pd.Series]:
        """
        Get the most recent element set for a satellite.

        Args:
            sat_no: NORAD catalog number

        Returns:
            Latest element set, or None if not found
        """
        df = self.to_dataframe(
            "SELECT * FROM element_sets WHERE sat_no = ? ORDER BY epoch DESC LIMIT 1",
            (sat_no,),
        )
        return df.iloc[0] if len(df) > 0 else None

    def bulk_insert(self, df: pd.DataFrame) -> int:
        """
        Bulk insert element sets from a DataFrame.

        Args:
            df: DataFrame with element set data

        Returns:
            Number of records inserted
        """
        if df.empty:
            return 0

        columns = [
            "sat_no", "line1", "line2", "epoch", "inclination", "raan",
            "eccentricity", "arg_perigee", "mean_anomaly", "mean_motion",
            "b_star", "semi_major_axis_km", "period_minutes", "source"
        ]
        available_columns = [c for c in columns if c in df.columns]

        return self.adapter.bulk_insert_df(
            table="element_sets",
            df=df,
            columns=available_columns,
            on_conflict="nothing",
            conflict_columns=["sat_no", "epoch"],
        )

    def count(self) -> int:
        """Get total element set count."""
        result = self.fetchone("SELECT COUNT(*) FROM element_sets")
        return result[0] if result else 0


class DatasetRepository(BaseRepository):
    """
    Repository for dataset management.

    Provides CRUD operations for benchmark datasets, version control,
    and comparison tools.
    """

    def create_dataset(
        self,
        name: str,
        code: Optional[str] = None,
        tier: Optional[str] = None,
        orbital_regime: Optional[str] = None,
        time_window_start: Optional[datetime] = None,
        time_window_end: Optional[datetime] = None,
        generation_params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Create a new dataset record.

        Args:
            name: Unique dataset name
            code: Dataset code (e.g., "LEO_A_H_H_H")
            tier: Tier level (T1-T5)
            orbital_regime: LEO, MEO, GEO, HEO
            time_window_start: Start of observation window
            time_window_end: End of observation window
            generation_params: Parameters used to generate the dataset

        Returns:
            The created dataset ID
        """
        params_json = json.dumps(generation_params) if generation_params else None

        result = self.fetchone(
            """
            INSERT INTO datasets (name, code, tier, orbital_regime,
                                   time_window_start, time_window_end, generation_params)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (name, code, tier, orbital_regime, time_window_start, time_window_end, params_json),
        )
        return result[0] if result else -1

    def get_dataset(
        self, dataset_id: Optional[int] = None, name: Optional[str] = None
    ) -> Optional[pd.Series]:
        """
        Load a dataset by ID or name.

        Args:
            dataset_id: Dataset ID
            name: Dataset name

        Returns:
            Dataset data as a Series, or None if not found
        """
        if dataset_id is not None:
            df = self.to_dataframe("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
        elif name is not None:
            df = self.to_dataframe("SELECT * FROM datasets WHERE name = ?", (name,))
        else:
            raise ValueError("Either dataset_id or name must be provided")

        if len(df) > 0:
            row = df.iloc[0]
            # Parse JSON fields
            if pd.notna(row.get("generation_params")):
                try:
                    row = row.copy()
                    row["generation_params"] = json.loads(row["generation_params"])
                except (json.JSONDecodeError, TypeError):
                    pass
            return row
        return None

    def list_datasets(
        self,
        tier: Optional[str] = None,
        orbital_regime: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        List all datasets with optional filtering.

        Args:
            tier: Filter by tier (T1-T5)
            orbital_regime: Filter by regime (LEO, MEO, GEO, HEO)
            status: Filter by status (created, processing, complete, failed)
            limit: Maximum number of results

        Returns:
            DataFrame of datasets
        """
        conditions = []
        params = []

        if tier:
            conditions.append("tier = ?")
            params.append(tier)
        if orbital_regime:
            conditions.append("orbital_regime = ?")
            params.append(orbital_regime)
        if status:
            conditions.append("status = ?")
            params.append(status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        query = f"""
            SELECT id, name, code, tier, orbital_regime, status,
                   observation_count, satellite_count,
                   time_window_start, time_window_end,
                   created_at, updated_at
            FROM datasets
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        return self.to_dataframe(query, tuple(params))

    def update_dataset(
        self,
        dataset_id: int,
        status: Optional[str] = None,
        observation_count: Optional[int] = None,
        satellite_count: Optional[int] = None,
        avg_coverage: Optional[float] = None,
        avg_obs_count: Optional[float] = None,
        max_track_gap: Optional[float] = None,
        json_path: Optional[str] = None,
        parquet_path: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Update dataset fields.

        Args:
            dataset_id: Dataset ID
            status: New status
            observation_count: Number of observations
            satellite_count: Number of satellites
            avg_coverage: Average orbital coverage
            avg_obs_count: Average observation count per satellite
            max_track_gap: Maximum track gap
            json_path: Path to exported JSON file
            parquet_path: Path to exported Parquet file
            **kwargs: Additional fields to update

        Returns:
            True if update was successful
        """
        updates = {}
        if status is not None:
            updates["status"] = status
        if observation_count is not None:
            updates["observation_count"] = observation_count
        if satellite_count is not None:
            updates["satellite_count"] = satellite_count
        if avg_coverage is not None:
            updates["avg_coverage"] = avg_coverage
        if avg_obs_count is not None:
            updates["avg_obs_count"] = avg_obs_count
        if max_track_gap is not None:
            updates["max_track_gap"] = max_track_gap
        if json_path is not None:
            updates["json_path"] = json_path
        if parquet_path is not None:
            updates["parquet_path"] = parquet_path

        updates.update(kwargs)
        updates["updated_at"] = datetime.now()

        if not updates:
            return False

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [dataset_id]

        self.execute(
            f"UPDATE datasets SET {set_clause} WHERE id = ?",
            tuple(values),
        )
        return True

    def delete_dataset(self, dataset_id: int, cascade: bool = True) -> bool:
        """
        Delete a dataset and optionally its related records.

        Args:
            dataset_id: Dataset ID
            cascade: If True, also delete related records in junction tables

        Returns:
            True if deletion was successful
        """
        if cascade:
            # Delete junction table records first
            self.execute("DELETE FROM dataset_observations WHERE dataset_id = ?", (dataset_id,))
            self.execute("DELETE FROM dataset_references WHERE dataset_id = ?", (dataset_id,))

        self.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
        return True

    def create_version(
        self,
        parent_id: int,
        name: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Create a new version of a dataset.

        Args:
            parent_id: ID of the parent dataset
            name: Optional new name (defaults to parent name with version suffix)
            changes: Optional parameter changes

        Returns:
            ID of the new dataset version
        """
        parent = self.get_dataset(dataset_id=parent_id)
        if parent is None:
            raise ValueError(f"Parent dataset {parent_id} not found")

        # Determine version number
        max_version = self.fetchone(
            """
            SELECT COALESCE(MAX(version), 0) + 1
            FROM datasets
            WHERE name LIKE ? OR parent_id = ?
            """,
            (f"{parent['name']}%", parent_id),
        )[0]

        # Create new dataset with parent reference
        new_name = name or f"{parent['name']}_v{max_version}"

        # Merge generation params
        parent_params = parent.get("generation_params", {})
        if isinstance(parent_params, str):
            parent_params = json.loads(parent_params)
        if parent_params is None:
            parent_params = {}
        merged_params = {**parent_params, **(changes or {})}

        result = self.fetchone(
            """
            INSERT INTO datasets (name, code, tier, orbital_regime,
                                   time_window_start, time_window_end,
                                   generation_params, version, parent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                new_name,
                parent.get("code"),
                parent.get("tier"),
                parent.get("orbital_regime"),
                parent.get("time_window_start"),
                parent.get("time_window_end"),
                json.dumps(merged_params),
                max_version,
                parent_id,
            ),
        )
        return result[0] if result else -1

    def get_dataset_versions(self, dataset_id: int) -> pd.DataFrame:
        """
        Get all versions of a dataset.

        Args:
            dataset_id: Dataset ID (can be any version in the chain)

        Returns:
            DataFrame of all dataset versions
        """
        # Find the root dataset
        dataset = self.get_dataset(dataset_id=dataset_id)
        if dataset is None:
            return pd.DataFrame()

        # Walk up to find root
        root_id = dataset_id
        while dataset is not None and pd.notna(dataset.get("parent_id")):
            root_id = int(dataset["parent_id"])
            dataset = self.get_dataset(dataset_id=root_id)

        # Get all descendants
        query = """
            WITH RECURSIVE version_tree AS (
                SELECT id, name, version, parent_id, created_at
                FROM datasets
                WHERE id = ?

                UNION ALL

                SELECT d.id, d.name, d.version, d.parent_id, d.created_at
                FROM datasets d
                INNER JOIN version_tree vt ON d.parent_id = vt.id
            )
            SELECT * FROM version_tree ORDER BY version
        """
        return self.to_dataframe(query, (root_id,))

    def compare_datasets(
        self,
        dataset_id_1: int,
        dataset_id_2: int,
    ) -> Dict[str, Any]:
        """
        Compare two datasets.

        Args:
            dataset_id_1: First dataset ID
            dataset_id_2: Second dataset ID

        Returns:
            Dictionary with comparison results
        """
        ds1 = self.get_dataset(dataset_id=dataset_id_1)
        ds2 = self.get_dataset(dataset_id=dataset_id_2)

        if ds1 is None or ds2 is None:
            raise ValueError("One or both datasets not found")

        # Get observation IDs for each dataset
        obs1 = set(
            self.fetchall(
                "SELECT observation_id FROM dataset_observations WHERE dataset_id = ?",
                (dataset_id_1,),
            )
        )
        obs2 = set(
            self.fetchall(
                "SELECT observation_id FROM dataset_observations WHERE dataset_id = ?",
                (dataset_id_2,),
            )
        )

        common = obs1 & obs2
        only_in_1 = obs1 - obs2
        only_in_2 = obs2 - obs1

        return {
            "dataset_1": {
                "id": dataset_id_1,
                "name": ds1.get("name"),
                "observation_count": len(obs1),
            },
            "dataset_2": {
                "id": dataset_id_2,
                "name": ds2.get("name"),
                "observation_count": len(obs2),
            },
            "common_observations": len(common),
            "only_in_dataset_1": len(only_in_1),
            "only_in_dataset_2": len(only_in_2),
            "jaccard_similarity": len(common) / len(obs1 | obs2) if obs1 | obs2 else 0.0,
            "parameter_diff": self._compare_params(
                ds1.get("generation_params", {}),
                ds2.get("generation_params", {}),
            ),
        }

    def _compare_params(
        self,
        params1: Dict[str, Any] | str,
        params2: Dict[str, Any] | str,
    ) -> Dict[str, Any]:
        """Compare generation parameters between two datasets."""
        if isinstance(params1, str):
            params1 = json.loads(params1) if params1 else {}
        if isinstance(params2, str):
            params2 = json.loads(params2) if params2 else {}
        if params1 is None:
            params1 = {}
        if params2 is None:
            params2 = {}

        all_keys = set(params1.keys()) | set(params2.keys())
        diff = {}

        for key in all_keys:
            val1 = params1.get(key)
            val2 = params2.get(key)
            if val1 != val2:
                diff[key] = {"dataset_1": val1, "dataset_2": val2}

        return diff

    def add_observations_to_dataset(
        self,
        dataset_id: int,
        observation_ids: List[str],
        track_assignments: Optional[Dict[str, int]] = None,
        object_assignments: Optional[Dict[str, int]] = None,
    ) -> int:
        """
        Associate observations with a dataset.

        Args:
            dataset_id: Dataset ID
            observation_ids: List of observation IDs
            track_assignments: Optional dict mapping obs ID to track ID
            object_assignments: Optional dict mapping obs ID to object ID

        Returns:
            Number of observations added
        """
        track_assignments = track_assignments or {}
        object_assignments = object_assignments or {}

        data = [
            (
                dataset_id,
                obs_id,
                track_assignments.get(obs_id),
                object_assignments.get(obs_id),
            )
            for obs_id in observation_ids
        ]

        query = """
            INSERT INTO dataset_observations (dataset_id, observation_id, assigned_track_id, assigned_object_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (dataset_id, observation_id) DO NOTHING
        """
        self.executemany(query, data)
        return len(observation_ids)

    def add_references_to_dataset(
        self,
        dataset_id: int,
        sat_no: int,
        state_vector_id: Optional[int] = None,
        element_set_id: Optional[int] = None,
        grouped_obs_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Add a reference (truth) record to a dataset.

        Args:
            dataset_id: Dataset ID
            sat_no: Satellite NORAD number
            state_vector_id: Optional state vector ID
            element_set_id: Optional element set ID
            grouped_obs_ids: Optional list of observation IDs for this satellite
        """
        obs_json = json.dumps(grouped_obs_ids) if grouped_obs_ids else None

        self.execute(
            """
            INSERT INTO dataset_references (dataset_id, sat_no, state_vector_id, element_set_id, grouped_obs_ids)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (dataset_id, sat_no) DO UPDATE SET
                state_vector_id = EXCLUDED.state_vector_id,
                element_set_id = EXCLUDED.element_set_id,
                grouped_obs_ids = EXCLUDED.grouped_obs_ids
            """,
            (dataset_id, sat_no, state_vector_id, element_set_id, obs_json),
        )

    def get_dataset_observations(self, dataset_id: int) -> pd.DataFrame:
        """
        Get all observations for a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            DataFrame with observation data and track assignments
        """
        query = """
            SELECT
                o.*,
                dso.assigned_track_id,
                dso.assigned_object_id
            FROM dataset_observations dso
            JOIN observations o ON dso.observation_id = o.id
            WHERE dso.dataset_id = ?
            ORDER BY o.ob_time
        """
        return self.to_dataframe(query, (dataset_id,))

    def get_dataset_references(self, dataset_id: int) -> pd.DataFrame:
        """
        Get all reference records for a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            DataFrame with reference data
        """
        query = """
            SELECT
                dr.sat_no,
                s.name as sat_name,
                s.orbital_regime,
                dr.state_vector_id,
                dr.element_set_id,
                dr.grouped_obs_ids
            FROM dataset_references dr
            LEFT JOIN satellites s ON dr.sat_no = s.sat_no
            WHERE dr.dataset_id = ?
            ORDER BY dr.sat_no
        """
        return self.to_dataframe(query, (dataset_id,))

    def count(self) -> int:
        """Get total dataset count."""
        result = self.fetchone("SELECT COUNT(*) FROM datasets")
        return result[0] if result else 0


class EventRepository(BaseRepository):
    """Repository for event labelling data access."""

    def create_event(
        self,
        event_type: str,
        primary_sat_no: int,
        event_time_start: Optional[datetime] = None,
        event_time_end: Optional[datetime] = None,
        secondary_sat_no: Optional[int] = None,
        confidence: float = 1.0,
        detection_method: str = "MANUAL",
        source: Optional[str] = None,
        external_id: Optional[str] = None,
        labelled_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """
        Create a new event record.

        Args:
            event_type: Type of event (launch, maneuver, proximity, breakup, reentry)
            primary_sat_no: Primary satellite NORAD number
            event_time_start: Start of event
            event_time_end: End of event
            secondary_sat_no: Secondary satellite (for proximity events)
            confidence: Confidence score (0.0 to 1.0)
            detection_method: AUTOMATIC, MANUAL, EXTERNAL
            source: Data source
            external_id: External reference ID
            labelled_by: Person/system that created the label
            notes: Additional notes

        Returns:
            The created event ID
        """
        # Get event type ID
        type_result = self.fetchone("SELECT id FROM event_types WHERE name = ?", (event_type,))
        if type_result is None:
            raise ValueError(f"Unknown event type: {event_type}")
        event_type_id = type_result[0]

        result = self.fetchone(
            """
            INSERT INTO events (event_type_id, primary_sat_no, event_time_start,
                                event_time_end, secondary_sat_no, confidence,
                                detection_method, source, external_id, labelled_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                event_type_id,
                primary_sat_no,
                event_time_start,
                event_time_end,
                secondary_sat_no,
                confidence,
                detection_method,
                source,
                external_id,
                labelled_by,
                notes,
            ),
        )
        return result[0] if result else -1

    def get_event(self, event_id: int) -> Optional[pd.Series]:
        """
        Get an event by ID.

        Args:
            event_id: Event ID

        Returns:
            Event data as a Series, or None if not found
        """
        query = """
            SELECT
                e.*,
                et.name as event_type_name
            FROM events e
            JOIN event_types et ON e.event_type_id = et.id
            WHERE e.id = ?
        """
        df = self.to_dataframe(query, (event_id,))
        return df.iloc[0] if len(df) > 0 else None

    def get_events_for_satellite(
        self,
        sat_no: int,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get events for a satellite.

        Args:
            sat_no: NORAD catalog number
            event_type: Optional filter by event type
            start_time: Optional start of time window
            end_time: Optional end of time window

        Returns:
            DataFrame of events
        """
        conditions = ["(e.primary_sat_no = ? OR e.secondary_sat_no = ?)"]
        params = [sat_no, sat_no]

        if event_type:
            conditions.append("et.name = ?")
            params.append(event_type)
        if start_time:
            conditions.append("e.event_time_start >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("e.event_time_end <= ?")
            params.append(end_time)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                e.*,
                et.name as event_type_name
            FROM events e
            JOIN event_types et ON e.event_type_id = et.id
            WHERE {where_clause}
            ORDER BY e.event_time_start
        """
        return self.to_dataframe(query, tuple(params))

    def link_observations_to_event(
        self,
        event_id: int,
        observation_ids: List[str],
    ) -> int:
        """
        Link observations to an event.

        Args:
            event_id: Event ID
            observation_ids: List of observation IDs

        Returns:
            Number of observations linked
        """
        data = [(event_id, obs_id) for obs_id in observation_ids]
        query = """
            INSERT INTO event_observations (event_id, observation_id)
            VALUES (?, ?)
            ON CONFLICT (event_id, observation_id) DO NOTHING
        """
        self.executemany(query, data)
        return len(observation_ids)

    def get_event_observations(self, event_id: int) -> pd.DataFrame:
        """
        Get observations linked to an event.

        Args:
            event_id: Event ID

        Returns:
            DataFrame of observations
        """
        query = """
            SELECT o.*
            FROM event_observations eo
            JOIN observations o ON eo.observation_id = o.id
            WHERE eo.event_id = ?
            ORDER BY o.ob_time
        """
        return self.to_dataframe(query, (event_id,))

    def list_event_types(self) -> pd.DataFrame:
        """Get all available event types."""
        return self.to_dataframe("SELECT * FROM event_types ORDER BY id")

    def delete_event(self, event_id: int) -> bool:
        """
        Delete an event and its observation links.

        Args:
            event_id: Event ID

        Returns:
            True if deletion was successful
        """
        self.execute("DELETE FROM event_observations WHERE event_id = ?", (event_id,))
        self.execute("DELETE FROM events WHERE id = ?", (event_id,))
        return True

    def count(self) -> int:
        """Get total event count."""
        result = self.fetchone("SELECT COUNT(*) FROM events")
        return result[0] if result else 0
