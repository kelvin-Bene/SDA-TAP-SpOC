# -*- coding: utf-8 -*-
"""
ILRS Validation Metrics Module

Provides validation functions for comparing algorithm outputs against
ILRS (International Laser Ranging Service) ground truth data.

ILRS provides millimeter-level precision range measurements to ~100 satellites,
making it the gold standard for orbit determination validation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

if TYPE_CHECKING:
    from uct_benchmark.database.connection import DatabaseManager


@dataclass
class ValidationResult:
    """Results from ILRS validation comparison."""

    satellite_id: int
    algorithm_name: str
    dataset_id: int

    # Position metrics
    position_rms_m: float = 0.0
    position_mean_error_m: float = 0.0
    position_max_error_m: float = 0.0

    # Along-track, cross-track, radial decomposition
    along_track_rms_m: float = 0.0
    cross_track_rms_m: float = 0.0
    radial_rms_m: float = 0.0

    # Sample statistics
    num_comparisons: int = 0
    time_span_hours: float = 0.0

    # Status
    validated: bool = False
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "satellite_id": self.satellite_id,
            "algorithm_name": self.algorithm_name,
            "dataset_id": self.dataset_id,
            "position_rms_m": self.position_rms_m,
            "position_mean_error_m": self.position_mean_error_m,
            "position_max_error_m": self.position_max_error_m,
            "along_track_rms_m": self.along_track_rms_m,
            "cross_track_rms_m": self.cross_track_rms_m,
            "radial_rms_m": self.radial_rms_m,
            "num_comparisons": self.num_comparisons,
            "time_span_hours": self.time_span_hours,
            "validated": self.validated,
            "warnings": self.warnings,
        }


def validate_against_ilrs(
    algorithm_states: pd.DataFrame,
    ilrs_satellites: List[int],
    db: "DatabaseManager",
    max_time_diff_seconds: float = 60.0,
) -> Dict[int, ValidationResult]:
    """
    Validate algorithm state predictions against ILRS ground truth.

    Compares predicted satellite positions from algorithm output against
    the highest-precision ground truth available (ILRS laser ranging).

    Args:
        algorithm_states: DataFrame with algorithm predicted states
            Required columns: sat_no, epoch, x_pos, y_pos, z_pos
            Optional columns: x_vel, y_vel, z_vel
        ilrs_satellites: List of ILRS-tracked NORAD IDs to validate
        db: DatabaseManager for accessing validation_measurements table
        max_time_diff_seconds: Maximum time difference for matching (default 60s)

    Returns:
        Dictionary mapping sat_no to ValidationResult

    Example:
        >>> results = validate_against_ilrs(predicted_states, [8820, 22195], db)
        >>> for sat_no, result in results.items():
        ...     print(f"Sat {sat_no}: RMS = {result.position_rms_m:.2f} m")
    """
    results = {}

    if algorithm_states.empty:
        logger.warning("Empty algorithm states DataFrame provided")
        return results

    # Normalize column names
    algorithm_states = _normalize_columns(algorithm_states)

    for sat_no in ilrs_satellites:
        result = ValidationResult(
            satellite_id=sat_no,
            algorithm_name="unknown",
            dataset_id=0,
        )

        # Filter algorithm states for this satellite
        sat_states = algorithm_states[algorithm_states['sat_no'] == sat_no]

        if sat_states.empty:
            result.warnings.append(f"No algorithm states for satellite {sat_no}")
            results[sat_no] = result
            continue

        # Get ILRS measurements for this satellite
        ilrs_data = _fetch_ilrs_measurements(sat_no, db)

        if ilrs_data.empty:
            result.warnings.append(f"No ILRS measurements available for satellite {sat_no}")
            results[sat_no] = result
            continue

        # Match states to ILRS measurements by time
        matched_pairs = _match_by_time(
            sat_states, ilrs_data, max_time_diff_seconds
        )

        if not matched_pairs:
            result.warnings.append("No time-matched pairs found")
            results[sat_no] = result
            continue

        # Compute validation metrics
        errors = _compute_position_errors(matched_pairs)

        if errors:
            result.position_rms_m = float(np.sqrt(np.mean(np.array(errors) ** 2)))
            result.position_mean_error_m = float(np.mean(errors))
            result.position_max_error_m = float(np.max(errors))
            result.num_comparisons = len(errors)
            result.validated = True

            # Calculate time span
            epochs = [p['epoch'] for p in matched_pairs]
            if len(epochs) >= 2:
                time_span = max(epochs) - min(epochs)
                result.time_span_hours = time_span.total_seconds() / 3600.0

        results[sat_no] = result

    return results


def get_validation_summary(
    algorithm_name: str,
    dataset_id: int,
    results: Dict[int, ValidationResult],
) -> str:
    """
    Generate a human-readable validation summary.

    Args:
        algorithm_name: Name of the algorithm being validated
        dataset_id: Dataset ID used for validation
        results: Dictionary of ValidationResults from validate_against_ilrs

    Returns:
        Formatted summary string
    """
    lines = [
        f"ILRS Validation Summary",
        f"=" * 50,
        f"Algorithm: {algorithm_name}",
        f"Dataset ID: {dataset_id}",
        f"Satellites validated: {sum(1 for r in results.values() if r.validated)}",
        f"",
    ]

    # Overall statistics
    validated_results = [r for r in results.values() if r.validated]
    if validated_results:
        all_rms = [r.position_rms_m for r in validated_results]
        lines.append(f"Overall Position RMS: {np.mean(all_rms):.2f} m (mean)")
        lines.append(f"                      {np.max(all_rms):.2f} m (worst)")
        lines.append(f"                      {np.min(all_rms):.2f} m (best)")
        lines.append("")

    # Per-satellite details
    lines.append("Per-Satellite Results:")
    lines.append("-" * 50)

    for sat_no, result in sorted(results.items()):
        if result.validated:
            lines.append(
                f"  {sat_no}: RMS={result.position_rms_m:.2f}m, "
                f"n={result.num_comparisons}, "
                f"span={result.time_span_hours:.1f}h"
            )
        else:
            warning = result.warnings[0] if result.warnings else "Unknown issue"
            lines.append(f"  {sat_no}: NOT VALIDATED - {warning}")

    return "\n".join(lines)


def get_ilrs_coverage_for_dataset(
    dataset_id: int,
    db: "DatabaseManager",
) -> Dict[str, Any]:
    """
    Analyze ILRS coverage for satellites in a dataset.

    Useful for determining if a dataset is suitable for ILRS validation.

    Args:
        dataset_id: Dataset ID to analyze
        db: DatabaseManager instance

    Returns:
        Dictionary with coverage statistics
    """
    from uct_benchmark.api.data_source_manager import DataSourceManager

    dsm = DataSourceManager(db)
    ilrs_sats = set(dsm.get_ilrs_tracked_satellites())

    # Get satellites in dataset
    dataset_sats = db.execute(
        """
        SELECT DISTINCT o.sat_no
        FROM observations o
        JOIN dataset_observations dso ON o.id = dso.observation_id
        WHERE dso.dataset_id = ?
        """,
        (dataset_id,),
    ).fetchall()

    dataset_sat_nos = {row[0] for row in dataset_sats}

    # Find overlap
    ilrs_in_dataset = dataset_sat_nos & ilrs_sats

    return {
        "dataset_id": dataset_id,
        "total_satellites": len(dataset_sat_nos),
        "ilrs_tracked_count": len(ilrs_in_dataset),
        "ilrs_satellite_ids": sorted(list(ilrs_in_dataset)),
        "ilrs_coverage_pct": (
            len(ilrs_in_dataset) / len(dataset_sat_nos) * 100
            if dataset_sat_nos else 0.0
        ),
        "validation_eligible": len(ilrs_in_dataset) > 0,
    }


# =============================================================================
# Private Helper Functions
# =============================================================================

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column names to expected schema."""
    column_map = {
        'satNo': 'sat_no',
        'satellite_id': 'sat_no',
        'norad_id': 'sat_no',
        'xPos': 'x_pos',
        'yPos': 'y_pos',
        'zPos': 'z_pos',
        'xVel': 'x_vel',
        'yVel': 'y_vel',
        'zVel': 'z_vel',
    }

    rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
    if rename_dict:
        df = df.rename(columns=rename_dict)

    return df


def _fetch_ilrs_measurements(
    sat_no: int,
    db: "DatabaseManager",
) -> pd.DataFrame:
    """Fetch ILRS measurements for a satellite from the database."""
    try:
        result = db.execute(
            """
            SELECT epoch, range_m, station_code, normal_point_rms_m
            FROM validation_measurements
            WHERE sat_no = ?
            ORDER BY epoch
            """,
            (sat_no,),
        ).fetchdf()
        return result
    except Exception as e:
        logger.warning(f"Failed to fetch ILRS data for sat {sat_no}: {e}")
        return pd.DataFrame()


def _match_by_time(
    algorithm_states: pd.DataFrame,
    ilrs_data: pd.DataFrame,
    max_diff_seconds: float,
) -> List[Dict[str, Any]]:
    """Match algorithm states to ILRS measurements by time proximity."""
    matched = []

    for _, ilrs_row in ilrs_data.iterrows():
        ilrs_epoch = ilrs_row['epoch']
        if isinstance(ilrs_epoch, str):
            ilrs_epoch = datetime.fromisoformat(ilrs_epoch)

        # Find closest algorithm state
        best_match = None
        best_diff = float('inf')

        for _, alg_row in algorithm_states.iterrows():
            alg_epoch = alg_row['epoch']
            if isinstance(alg_epoch, str):
                alg_epoch = datetime.fromisoformat(alg_epoch)

            diff = abs((alg_epoch - ilrs_epoch).total_seconds())
            if diff < best_diff and diff <= max_diff_seconds:
                best_diff = diff
                best_match = alg_row

        if best_match is not None:
            matched.append({
                'epoch': ilrs_epoch,
                'ilrs_range_m': ilrs_row['range_m'],
                'station_code': ilrs_row['station_code'],
                'algorithm_state': best_match,
                'time_diff_s': best_diff,
            })

    return matched


def _compute_position_errors(matched_pairs: List[Dict[str, Any]]) -> List[float]:
    """
    Compute position errors between algorithm states and ILRS measurements.

    Note: ILRS provides range measurements, not full position vectors.
    For full validation, we would need to convert range + station location
    to position and compare. This simplified version uses range difference
    as a proxy for position error.
    """
    errors = []

    for pair in matched_pairs:
        ilrs_range = pair.get('ilrs_range_m')
        alg_state = pair.get('algorithm_state')

        if ilrs_range is None or alg_state is None:
            continue

        # Compute algorithm range (distance from Earth center)
        # This is a simplification - proper validation would use station position
        try:
            x = float(alg_state.get('x_pos', 0)) * 1000  # km to m
            y = float(alg_state.get('y_pos', 0)) * 1000
            z = float(alg_state.get('z_pos', 0)) * 1000
            alg_range = np.sqrt(x**2 + y**2 + z**2)

            # Range difference as error proxy
            error = abs(alg_range - float(ilrs_range))
            errors.append(error)
        except (ValueError, TypeError) as e:
            logger.debug(f"Error computing range: {e}")
            continue

    return errors


__all__ = [
    'ValidationResult',
    'validate_against_ilrs',
    'get_validation_summary',
    'get_ilrs_coverage_for_dataset',
]
