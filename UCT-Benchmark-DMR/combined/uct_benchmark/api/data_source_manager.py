# -*- coding: utf-8 -*-
"""
Data Source Manager for Open Source Integration

Provides a unified interface for enriching satellite data from multiple
open source databases (UCS, GCAT) and managing ILRS validation data.

This module connects the open_sources.py API wrappers to the database
pipeline for automated satellite enrichment and HAMR detection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger

from .open_sources import (
    gcatLookupByNorad,
    gcatQuery,
    ilrsGetSatellites,
    ucsLookupByNorad,
    ucsQuery,
    enrichSatelliteData,
)

if TYPE_CHECKING:
    from uct_benchmark.database.connection import DatabaseManager


# HAMR threshold: objects with AMR > 0.1 m²/kg are considered high area-to-mass ratio
# This is a commonly used threshold in space situational awareness
HAMR_AMR_THRESHOLD = 0.1  # m²/kg

# Default cross-section estimation for satellites without known dimensions
# Based on typical small satellite dimensions (1m x 1m)
DEFAULT_CROSS_SECTION_M2 = 1.0

# Cache duration for enrichment data (avoid re-fetching recently enriched satellites)
ENRICHMENT_CACHE_DURATION = timedelta(hours=24)


@dataclass
class EnrichmentReport:
    """Report of satellite enrichment results."""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_satellites: int = 0
    enriched_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0  # Already recently enriched
    ucs_matches: int = 0
    gcat_matches: int = 0
    hamr_detected: int = 0
    errors: Dict[int, str] = field(default_factory=dict)  # sat_no -> error

    def finalize(self) -> None:
        """Mark the report as complete."""
        self.end_time = datetime.now()

    @property
    def duration_seconds(self) -> float:
        """Get the duration in seconds."""
        if self.end_time is None:
            return (datetime.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_satellites": self.total_satellites,
            "enriched_count": self.enriched_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "ucs_matches": self.ucs_matches,
            "gcat_matches": self.gcat_matches,
            "hamr_detected": self.hamr_detected,
            "success_rate": (self.enriched_count / self.total_satellites * 100)
            if self.total_satellites > 0
            else 0.0,
        }


class DataSourceManager:
    """
    Manager for integrating open source satellite data into the UCT Benchmark pipeline.

    Provides:
    - Satellite enrichment from UCS and GCAT databases
    - Accurate area-to-mass ratio (AMR) calculation using real mass data
    - HAMR (High Area-to-Mass Ratio) object detection
    - ILRS satellite identification for validation datasets

    Example:
        >>> from uct_benchmark.database import DatabaseManager
        >>> from uct_benchmark.api.data_source_manager import DataSourceManager
        >>>
        >>> db = DatabaseManager('data/uct_benchmark.db')
        >>> dsm = DataSourceManager(db)
        >>>
        >>> # Enrich a single satellite
        >>> data = dsm.enrich_satellite(25544)  # ISS
        >>> print(data['purpose'], data['mass_kg'])
        >>>
        >>> # Check if satellite is HAMR
        >>> if dsm.is_hamr_object(12345):
        ...     print("High area-to-mass ratio object detected!")
    """

    def __init__(self, db: "DatabaseManager"):
        """
        Initialize the DataSourceManager.

        Args:
            db: DatabaseManager instance for database access
        """
        self.db = db
        self._ucs_cache: Optional[pd.DataFrame] = None
        self._gcat_cache: Optional[pd.DataFrame] = None
        self._ilrs_satellites: Optional[List[int]] = None

    def enrich_satellite(
        self,
        sat_no: int,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Enrich a single satellite with data from UCS and GCAT.

        Fetches metadata including:
        - Purpose (Communications, Earth Observation, etc.)
        - Operator/Owner
        - Launch site
        - Mass (critical for AMR calculation)
        - Power output

        Args:
            sat_no: NORAD catalog number
            force_refresh: If True, bypass cache and re-fetch

        Returns:
            Dictionary with enrichment data and database update status
        """
        result = {
            "sat_no": sat_no,
            "enriched": False,
            "ucs_match": False,
            "gcat_match": False,
            "data": {},
        }

        # Check if recently enriched (skip if within cache duration)
        if not force_refresh and self._is_recently_enriched(sat_no):
            result["skipped"] = True
            result["reason"] = "Recently enriched"
            return result

        enrichment_data = {}

        # Try UCS database (most detailed metadata)
        try:
            ucs_data = ucsLookupByNorad(sat_no)
            if ucs_data is not None:
                result["ucs_match"] = True
                enrichment_data.update(self._extract_ucs_fields(ucs_data))
                logger.debug(f"UCS data found for sat {sat_no}")
        except Exception as e:
            logger.warning(f"UCS lookup failed for sat {sat_no}: {e}")

        # Try GCAT database (launch/classification info)
        try:
            gcat_data = gcatLookupByNorad(sat_no)
            if gcat_data is not None:
                result["gcat_match"] = True
                # Only add GCAT fields not already from UCS
                gcat_fields = self._extract_gcat_fields(gcat_data)
                for key, value in gcat_fields.items():
                    if key not in enrichment_data or enrichment_data[key] is None:
                        enrichment_data[key] = value
                logger.debug(f"GCAT data found for sat {sat_no}")
        except Exception as e:
            logger.warning(f"GCAT lookup failed for sat {sat_no}: {e}")

        # Calculate AMR if we have mass and cross-section data
        if enrichment_data.get("mass_kg"):
            cross_section = enrichment_data.get("cross_section_m2")
            if cross_section is None:
                # Try to get from existing database record
                existing = self.db.execute(
                    "SELECT cross_section_m2 FROM satellites WHERE sat_no = ?",
                    (sat_no,),
                ).fetchone()
                if existing and existing[0]:
                    cross_section = float(existing[0])

            if cross_section:
                enrichment_data["amr_m2_kg"] = cross_section / enrichment_data["mass_kg"]

        result["data"] = enrichment_data

        # Update database if we have data
        if enrichment_data:
            try:
                self._update_satellite_record(sat_no, enrichment_data)
                result["enriched"] = True
            except Exception as e:
                logger.error(f"Failed to update satellite {sat_no}: {e}")
                result["error"] = str(e)

        return result

    def enrich_satellites_batch(
        self,
        sat_nos: List[int],
        force_refresh: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> EnrichmentReport:
        """
        Enrich multiple satellites in batch.

        More efficient than individual calls as it caches the UCS/GCAT
        catalogs for the duration of the batch operation.

        Args:
            sat_nos: List of NORAD catalog numbers
            force_refresh: If True, bypass cache and re-fetch all
            progress_callback: Optional callback(current, total) for progress

        Returns:
            EnrichmentReport with batch statistics
        """
        report = EnrichmentReport()
        report.total_satellites = len(sat_nos)

        # Pre-load catalogs for efficiency
        self._load_catalogs()

        for i, sat_no in enumerate(sat_nos):
            try:
                result = self.enrich_satellite(sat_no, force_refresh)

                if result.get("skipped"):
                    report.skipped_count += 1
                elif result.get("enriched"):
                    report.enriched_count += 1
                    if result.get("ucs_match"):
                        report.ucs_matches += 1
                    if result.get("gcat_match"):
                        report.gcat_matches += 1
                    # Check HAMR
                    if self.is_hamr_object(sat_no):
                        report.hamr_detected += 1
                else:
                    report.failed_count += 1
                    if "error" in result:
                        report.errors[sat_no] = result["error"]

            except Exception as e:
                report.failed_count += 1
                report.errors[sat_no] = str(e)
                logger.error(f"Enrichment failed for sat {sat_no}: {e}")

            if progress_callback:
                progress_callback(i + 1, len(sat_nos))

        report.finalize()
        return report

    def calculate_accurate_amr(self, sat_no: int) -> Optional[float]:
        """
        Calculate accurate area-to-mass ratio using real mass data.

        This method uses actual mass values from UCS database instead of
        the hardcoded estimates previously used for HAMR detection.

        Args:
            sat_no: NORAD catalog number

        Returns:
            AMR in m²/kg, or None if mass data unavailable
        """
        # First check database for cached AMR
        cached = self.db.execute(
            "SELECT amr_m2_kg, mass_kg, cross_section_m2 FROM satellites WHERE sat_no = ?",
            (sat_no,),
        ).fetchone()

        if cached:
            # If we have a pre-calculated AMR, use it
            if cached[0] is not None:
                return float(cached[0])

            # Otherwise calculate from mass and cross-section
            mass_kg = cached[1]
            cross_section = cached[2]

            if mass_kg and cross_section:
                return float(cross_section) / float(mass_kg)

        # No cached data - try to fetch from UCS
        ucs_data = ucsLookupByNorad(sat_no)
        if ucs_data is not None:
            # Find mass column
            mass_cols = [c for c in ucs_data.index if 'mass' in c.lower() and 'launch' in c.lower()]
            if mass_cols:
                mass_kg = ucs_data[mass_cols[0]]
                if pd.notna(mass_kg) and mass_kg > 0:
                    # Get cross-section from database or estimate
                    cross_section = DEFAULT_CROSS_SECTION_M2
                    if cached and cached[2]:
                        cross_section = float(cached[2])
                    return cross_section / float(mass_kg)

        return None

    def is_hamr_object(self, sat_no: int) -> bool:
        """
        Determine if a satellite is a High Area-to-Mass Ratio (HAMR) object.

        Uses real mass data from UCS database when available, falling back
        to database cached values.

        HAMR objects (AMR > 0.1 m²/kg) include:
        - Debris
        - Rocket bodies (some)
        - Defunct satellites with deployed solar panels
        - Certain lightweight satellites

        Args:
            sat_no: NORAD catalog number

        Returns:
            True if AMR > threshold (0.1 m²/kg), False otherwise
        """
        amr = self.calculate_accurate_amr(sat_no)

        if amr is None:
            # Fall back to object type heuristic if no mass data
            object_type = self.db.execute(
                "SELECT object_type FROM satellites WHERE sat_no = ?",
                (sat_no,),
            ).fetchone()

            if object_type and object_type[0]:
                # Debris and rocket bodies often have high AMR
                obj_type = object_type[0].upper()
                if "DEBRIS" in obj_type or "DEB" in obj_type:
                    return True
                if "ROCKET" in obj_type or "R/B" in obj_type:
                    # Rocket bodies vary widely, assume not HAMR without data
                    return False

            return False

        return amr > HAMR_AMR_THRESHOLD

    def get_ilrs_tracked_satellites(self) -> List[int]:
        """
        Get list of NORAD IDs for satellites tracked by ILRS.

        ILRS (International Laser Ranging Service) provides sub-centimeter
        precision range measurements. These satellites are ideal for
        algorithm validation as they have the most accurate ground truth.

        Returns:
            List of NORAD catalog numbers for ILRS-tracked satellites
        """
        if self._ilrs_satellites is None:
            ilrs_df = ilrsGetSatellites()
            if not ilrs_df.empty and 'norad_id' in ilrs_df.columns:
                self._ilrs_satellites = ilrs_df['norad_id'].tolist()
            else:
                self._ilrs_satellites = []

        return self._ilrs_satellites

    def is_ilrs_satellite(self, sat_no: int) -> bool:
        """
        Check if a satellite is tracked by ILRS.

        Args:
            sat_no: NORAD catalog number

        Returns:
            True if satellite is tracked by ILRS
        """
        return sat_no in self.get_ilrs_tracked_satellites()

    def get_enrichment_status(self, sat_no: int) -> Dict[str, Any]:
        """
        Get the current enrichment status of a satellite.

        Args:
            sat_no: NORAD catalog number

        Returns:
            Dictionary with enrichment timestamps and data availability
        """
        row = self.db.execute(
            """
            SELECT purpose, operator, launch_site, mass_kg, amr_m2_kg,
                   ucs_synced_at, gcat_synced_at
            FROM satellites WHERE sat_no = ?
            """,
            (sat_no,),
        ).fetchone()

        if not row:
            return {"exists": False, "enriched": False}

        return {
            "exists": True,
            "enriched": any([row[0], row[1], row[2]]),  # Has any enrichment data
            "has_purpose": row[0] is not None,
            "has_operator": row[1] is not None,
            "has_launch_site": row[2] is not None,
            "has_mass": row[3] is not None,
            "has_amr": row[4] is not None,
            "ucs_synced_at": row[5],
            "gcat_synced_at": row[6],
        }

    def sync_data_source_stats(self) -> None:
        """
        Update data_sources table with current record counts.

        Call this after batch operations to keep stats current.
        """
        # Update satellite count (approximation of enriched records)
        enriched_count = self.db.execute(
            "SELECT COUNT(*) FROM satellites WHERE ucs_synced_at IS NOT NULL OR gcat_synced_at IS NOT NULL"
        ).fetchone()[0]

        self.db.execute(
            """
            UPDATE data_sources
            SET record_count = ?, last_sync = CURRENT_TIMESTAMP
            WHERE source_name IN ('UCS', 'GCAT')
            """,
            (enriched_count,),
        )

        # Update ILRS count
        ilrs_count = len(self.get_ilrs_tracked_satellites())
        self.db.execute(
            """
            UPDATE data_sources
            SET record_count = ?, last_sync = CURRENT_TIMESTAMP
            WHERE source_name = 'ILRS'
            """,
            (ilrs_count,),
        )

    # =========================================================================
    # Private helper methods
    # =========================================================================

    def _is_recently_enriched(self, sat_no: int) -> bool:
        """Check if satellite was enriched within cache duration."""
        row = self.db.execute(
            "SELECT ucs_synced_at, gcat_synced_at FROM satellites WHERE sat_no = ?",
            (sat_no,),
        ).fetchone()

        if not row:
            return False

        threshold = datetime.now() - ENRICHMENT_CACHE_DURATION

        # Check if either sync timestamp is recent
        for sync_time in row:
            if sync_time is not None:
                if isinstance(sync_time, str):
                    sync_time = datetime.fromisoformat(sync_time)
                if sync_time > threshold:
                    return True

        return False

    def _load_catalogs(self) -> None:
        """Pre-load UCS and GCAT catalogs for batch efficiency."""
        if self._ucs_cache is None:
            self._ucs_cache = ucsQuery()
        if self._gcat_cache is None:
            self._gcat_cache = gcatQuery('satcat')

    def _extract_ucs_fields(self, ucs_data: pd.Series) -> Dict[str, Any]:
        """Extract relevant fields from UCS data."""
        fields = {}

        # Map UCS columns to our schema
        column_mapping = {
            'purpose': ['Purpose', 'Primary Purpose'],
            'operator': ['Operator/Owner', 'Owner'],
            'mass_kg': ['Launch Mass (kg.)', 'Launch Mass', 'Dry Mass (kg.)'],
            'power_watts': ['Power (watts)', 'Power'],
        }

        for field_name, possible_cols in column_mapping.items():
            for col in possible_cols:
                if col in ucs_data.index and pd.notna(ucs_data[col]):
                    value = ucs_data[col]
                    # Clean up numeric fields
                    if field_name in ('mass_kg', 'power_watts'):
                        try:
                            value = float(str(value).replace(',', ''))
                        except (ValueError, TypeError):
                            continue
                    fields[field_name] = value
                    break

        return fields

    def _extract_gcat_fields(self, gcat_data: pd.Series) -> Dict[str, Any]:
        """Extract relevant fields from GCAT data."""
        fields = {}

        # Map GCAT columns to our schema
        column_mapping = {
            'launch_site': ['LaSite', 'LaunchSite', 'Launch Site'],
            'operator': ['Owner', 'OpOwner'],
            'object_type': ['Type', 'ObjType'],
        }

        for field_name, possible_cols in column_mapping.items():
            for col in possible_cols:
                if col in gcat_data.index and pd.notna(gcat_data[col]):
                    fields[field_name] = gcat_data[col]
                    break

        return fields

    def _update_satellite_record(
        self,
        sat_no: int,
        data: Dict[str, Any],
    ) -> None:
        """Update satellite record with enrichment data."""
        # Build dynamic update query
        update_fields = []
        values = []

        field_mapping = {
            'purpose': 'purpose',
            'operator': 'operator',
            'launch_site': 'launch_site',
            'mass_kg': 'mass_kg',
            'power_watts': 'power_watts',
            'amr_m2_kg': 'amr_m2_kg',
        }

        for data_key, db_column in field_mapping.items():
            if data_key in data and data[data_key] is not None:
                update_fields.append(f"{db_column} = ?")
                values.append(data[data_key])

        if not update_fields:
            return

        # Add sync timestamps
        update_fields.append("ucs_synced_at = CURRENT_TIMESTAMP")
        update_fields.append("gcat_synced_at = CURRENT_TIMESTAMP")
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        # Add sat_no for WHERE clause
        values.append(sat_no)

        sql = f"UPDATE satellites SET {', '.join(update_fields)} WHERE sat_no = ?"
        self.db.execute(sql, tuple(values))


# Module-level convenience functions

def get_data_source_manager(db: "DatabaseManager") -> DataSourceManager:
    """
    Factory function to create a DataSourceManager.

    Args:
        db: DatabaseManager instance

    Returns:
        Configured DataSourceManager
    """
    return DataSourceManager(db)


__all__ = [
    'DataSourceManager',
    'EnrichmentReport',
    'get_data_source_manager',
    'HAMR_AMR_THRESHOLD',
]
