# -*- coding: utf-8 -*-
"""
Object Type Filtering Module

This module implements filtering for specific object types as described by Lewis:
1. High Area-to-Mass Ratio (HAMR) objects
2. Close Proximity objects (apparent or physical)
3. Calibration satellites

These filters allow users to select specific types of objects for their
benchmark datasets, enabling testing of UCT processors against challenging cases.

Author: UCT Benchmark Team
Date: 2026
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from uct_benchmark.settings import (
    CALIBRATION_SATELLITES,
    HAMR_THRESHOLD,
    PROXIMITY_ANGULAR_THRESHOLD_DEG,
    PROXIMITY_DISTANCE_THRESHOLD_KM,
    PROXIMITY_VELOCITY_THRESHOLD_M_S,
    OBJECT_TYPE_CODES,
    LEGACY_OBJECT_TYPE_MAP,
    OBJECT_COUNT_MAP,
)


@dataclass
class ObjectFilterConfig:
    """Configuration for object type filtering."""

    # HAMR filtering
    enable_hamr: bool = False
    hamr_threshold: float = HAMR_THRESHOLD  # m^2/kg

    # Proximity filtering
    enable_proximity: bool = False
    proximity_angular_threshold_deg: float = PROXIMITY_ANGULAR_THRESHOLD_DEG
    proximity_distance_threshold_km: float = PROXIMITY_DISTANCE_THRESHOLD_KM

    # Calibration filtering
    enable_calibration: bool = False
    calibration_satellites: List[int] = None

    # Object type selection
    object_types: List[str] = None  # ["HAMR", "PROX", "CALIB", "NORM", "ALL"]

    # Percentage of each type to include
    hamr_percentage: float = 0.1  # 10% HAMR objects
    proximity_percentage: float = 0.1  # 10% proximity objects
    calibration_percentage: float = 0.1  # 10% calibration objects

    def __post_init__(self):
        if self.calibration_satellites is None:
            self.calibration_satellites = CALIBRATION_SATELLITES
        if self.object_types is None:
            self.object_types = ["NORM"]


# =============================================================================
# HAMR FILTERING
# =============================================================================


def get_area_to_mass_ratio(
    sat_no: int,
    physical_data: Dict[int, Dict] = None,
) -> Optional[float]:
    """
    Get the area-to-mass ratio for a satellite.

    Args:
        sat_no: NORAD catalog number
        physical_data: Dict mapping satNo to physical properties
                      Expected keys: 'mass' (kg), 'cross_section' (m^2)

    Returns:
        Area-to-mass ratio in m^2/kg, or None if not available
    """
    if physical_data is None or sat_no not in physical_data:
        return None

    props = physical_data[sat_no]
    mass = props.get("mass") or props.get("Mass")
    area = props.get("cross_section") or props.get("CrossSection") or props.get("area")

    if mass is None or area is None or mass <= 0:
        return None

    try:
        ratio = area / mass
    except (TypeError, ZeroDivisionError):
        return None

    # Guard against NaN/Inf propagating from non-numeric or degenerate values
    if not np.isfinite(ratio):
        return None

    return ratio


def filter_hamr_objects(
    satellite_ids: List[int],
    physical_data: Dict[int, Dict],
    threshold: float = HAMR_THRESHOLD,
) -> Tuple[List[int], List[int]]:
    """
    Filter satellites to identify High Area-to-Mass Ratio (HAMR) objects.

    HAMR objects are challenging for UCT processors because:
    - High drag uncertainty
    - Significant solar radiation pressure effects
    - More unpredictable orbits

    Args:
        satellite_ids: List of NORAD catalog numbers to filter
        physical_data: Dict mapping satNo to physical properties from ESA DiscoSweb
        threshold: A/M ratio threshold (m^2/kg) - objects above this are HAMR

    Returns:
        Tuple of (hamr_objects, normal_objects)
    """
    hamr_objects = []
    normal_objects = []

    for sat_no in satellite_ids:
        am_ratio = get_area_to_mass_ratio(sat_no, physical_data)

        if am_ratio is not None and am_ratio >= threshold:
            hamr_objects.append(sat_no)
            logger.debug(f"Satellite {sat_no} classified as HAMR (A/M = {am_ratio:.3f} m^2/kg)")
        else:
            normal_objects.append(sat_no)

    logger.info(
        f"HAMR filtering: {len(hamr_objects)} HAMR objects, "
        f"{len(normal_objects)} normal objects (threshold: {threshold} m^2/kg)"
    )

    return hamr_objects, normal_objects


def estimate_am_ratio_from_tle(
    sat_no: int,
    sat_params: Dict[int, Dict],
    tle_data: pd.DataFrame = None,
) -> Optional[float]:
    """
    Estimate area-to-mass ratio from TLE decay rate (B* term).

    This is a rough estimate when physical data is not available.
    B* = (Cd * A * rho0) / (2 * m) where Cd~2.2, rho0 is reference density

    Args:
        sat_no: NORAD catalog number
        sat_params: Dict with orbital parameters
        tle_data: DataFrame with TLE data including bstar column

    Returns:
        Estimated A/M ratio or None
    """
    # This is a simplified estimation
    # B* is in units of 1/earth_radii, needs conversion

    if tle_data is None or tle_data.empty:
        return None

    sat_tle = tle_data[tle_data["satNo"] == sat_no]
    if sat_tle.empty:
        return None

    bstar = sat_tle.iloc[0].get("bstar")
    if bstar is None or bstar == 0:
        return None

    # Very rough conversion: A/M ~ B* * constant
    # This is still an approximation; B* encodes drag and ballistic
    # coefficient but assumes a simplified exponential atmosphere model.
    rho0 = 2.461e-5  # Reference atmospheric density at 120km (kg/m^3)
    Cd = 2.2  # Typical drag coefficient
    R_EARTH_M = 6378137.0  # Earth radius in meters

    # B* from TLEs is in units of 1/Earth_radii; convert to SI (1/m)
    # B* = Cd * A * rho0 / (2 * m * R_E)  =>  A/M = 2 * B*_SI / (Cd * rho0)
    bstar_si = bstar / R_EARTH_M
    am_estimate = abs(2 * bstar_si / (Cd * rho0))

    return am_estimate


# =============================================================================
# PROXIMITY FILTERING
# =============================================================================


def compute_angular_separation(
    ra1: float, dec1: float,
    ra2: float, dec2: float,
) -> float:
    """
    Compute angular separation between two sky positions.

    Uses the haversine formula for spherical geometry.

    Args:
        ra1, dec1: Right ascension and declination of first point (degrees)
        ra2, dec2: Right ascension and declination of second point (degrees)

    Returns:
        Angular separation in degrees
    """
    # Convert to radians
    ra1_rad = np.radians(ra1)
    dec1_rad = np.radians(dec1)
    ra2_rad = np.radians(ra2)
    dec2_rad = np.radians(dec2)

    # Haversine formula
    delta_ra = ra2_rad - ra1_rad
    delta_dec = dec2_rad - dec1_rad

    a = np.sin(delta_dec / 2) ** 2 + np.cos(dec1_rad) * np.cos(dec2_rad) * np.sin(delta_ra / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return np.degrees(c)


def find_proximity_pairs(
    obs_df: pd.DataFrame,
    threshold_deg: float = PROXIMITY_ANGULAR_THRESHOLD_DEG,
    time_window_minutes: float = 10.0,
) -> List[Tuple[int, int, float, datetime]]:
    """
    Find pairs of satellites with close apparent positions.

    This identifies objects that appear close together in the sky,
    which makes them challenging for UCT processors to distinguish.

    Args:
        obs_df: DataFrame with 'satNo', 'obTime', 'ra', 'declination' columns
        threshold_deg: Maximum angular separation to consider "close"
        time_window_minutes: Time window to consider observations as concurrent

    Returns:
        List of tuples: (sat1, sat2, separation_deg, observation_time)
    """
    if obs_df.empty:
        return []

    proximity_pairs = []

    # Ensure obTime is datetime
    obs_df = obs_df.copy()
    if obs_df["obTime"].dtype == "object":
        obs_df["obTime"] = pd.to_datetime(obs_df["obTime"])

    # Get unique satellites
    satellites = obs_df["satNo"].unique()

    if len(satellites) < 2:
        return []

    # Group observations by time bins
    time_bin = pd.Timedelta(minutes=time_window_minutes)
    obs_df["time_bin"] = obs_df["obTime"].dt.floor(time_bin)

    # For each time bin, check pairwise distances
    for time_bin_val, bin_obs in obs_df.groupby("time_bin"):
        sats_in_bin = bin_obs["satNo"].unique()

        if len(sats_in_bin) < 2:
            continue

        # Get representative position for each satellite (average within bin)
        sat_positions = {}
        for sat_no in sats_in_bin:
            sat_obs = bin_obs[bin_obs["satNo"] == sat_no]
            sat_positions[sat_no] = {
                "ra": sat_obs["ra"].mean(),
                "dec": sat_obs["declination"].mean(),
            }

        # Check all pairs
        sats_list = list(sats_in_bin)
        for i, sat1 in enumerate(sats_list):
            for sat2 in sats_list[i + 1:]:
                pos1 = sat_positions[sat1]
                pos2 = sat_positions[sat2]

                separation = compute_angular_separation(
                    pos1["ra"], pos1["dec"],
                    pos2["ra"], pos2["dec"]
                )

                if separation <= threshold_deg:
                    proximity_pairs.append((
                        int(sat1), int(sat2), separation,
                        time_bin_val.to_pydatetime()
                    ))

    logger.info(
        f"Proximity search: found {len(proximity_pairs)} close pairs "
        f"(threshold: {threshold_deg} deg)"
    )

    return proximity_pairs


def filter_proximity_objects(
    satellite_ids: List[int],
    obs_df: pd.DataFrame,
    threshold_deg: float = PROXIMITY_ANGULAR_THRESHOLD_DEG,
) -> Tuple[Set[int], List[Tuple[int, int, float, datetime]]]:
    """
    Filter to identify satellites involved in close proximity events.

    Args:
        satellite_ids: List of NORAD catalog numbers to consider
        obs_df: DataFrame of observations
        threshold_deg: Angular separation threshold

    Returns:
        Tuple of (proximity_satellites, proximity_pairs)
        proximity_satellites: Set of satellite IDs involved in proximity events
        proximity_pairs: List of (sat1, sat2, separation, time) tuples
    """
    # Filter observations to only include target satellites
    filtered_obs = obs_df[obs_df["satNo"].isin(satellite_ids)]

    if filtered_obs.empty:
        return set(), []

    # Find proximity pairs
    pairs = find_proximity_pairs(filtered_obs, threshold_deg)

    # Extract unique satellites involved in proximity events
    proximity_sats = set()
    for sat1, sat2, _, _ in pairs:
        proximity_sats.add(sat1)
        proximity_sats.add(sat2)

    return proximity_sats, pairs


# =============================================================================
# CALIBRATION SATELLITE FILTERING
# =============================================================================


def filter_calibration_satellites(
    satellite_ids: List[int],
    calibration_list: List[int] = None,
) -> Tuple[List[int], List[int]]:
    """
    Filter satellites to identify calibration objects.

    Calibration satellites are well-known objects with:
    - Good observation coverage
    - Well-determined orbits
    - Known dynamics models

    They should be easy for UCT processors to identify and can be used
    for verification of algorithm performance.

    Args:
        satellite_ids: List of NORAD catalog numbers to filter
        calibration_list: List of known calibration satellite IDs
                         (defaults to CALIBRATION_SATELLITES from settings)

    Returns:
        Tuple of (calibration_objects, other_objects)
    """
    if calibration_list is None:
        calibration_list = CALIBRATION_SATELLITES

    calibration_set = set(calibration_list)
    calibration_objects = [sat for sat in satellite_ids if sat in calibration_set]
    other_objects = [sat for sat in satellite_ids if sat not in calibration_set]

    logger.info(
        f"Calibration filtering: {len(calibration_objects)} calibration satellites, "
        f"{len(other_objects)} other satellites"
    )

    return calibration_objects, other_objects


# =============================================================================
# COMBINED OBJECT TYPE FILTERING
# =============================================================================


def filter_by_object_type(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    physical_data: Dict[int, Dict] = None,
    config: ObjectFilterConfig = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Apply combined object type filtering based on configuration.

    This is the main entry point for object type filtering that:
    1. Identifies HAMR objects (if enabled)
    2. Identifies proximity objects (if enabled)
    3. Identifies calibration satellites (if enabled)
    4. Selects objects based on configured percentages

    Args:
        obs_df: DataFrame of observations
        sat_params: Dict mapping satNo to orbital parameters
        physical_data: Dict mapping satNo to physical properties (mass, area)
        config: ObjectFilterConfig instance

    Returns:
        Tuple of (filtered_obs_df, metadata)
    """
    if config is None:
        config = ObjectFilterConfig()

    if obs_df.empty:
        return obs_df, {"status": "empty_input", "object_types": []}

    all_satellites = obs_df["satNo"].unique().tolist()
    selected_satellites = set()
    object_classifications = {}

    metadata = {
        "total_satellites": len(all_satellites),
        "hamr_satellites": [],
        "proximity_satellites": [],
        "calibration_satellites": [],
        "normal_satellites": [],
        "selected_satellites": [],
        "filters_applied": [],
    }

    # Initialize physical_data if not provided
    if physical_data is None:
        physical_data = {}

    # Step 1: HAMR filtering
    if config.enable_hamr or "HAMR" in (config.object_types or []):
        hamr_sats, normal_sats = filter_hamr_objects(
            all_satellites, physical_data, config.hamr_threshold
        )
        metadata["hamr_satellites"] = hamr_sats
        metadata["filters_applied"].append("HAMR")

        # Select percentage of HAMR objects
        n_hamr = max(1, int(len(hamr_sats) * config.hamr_percentage))
        if hamr_sats:
            selected_hamr = hamr_sats[:n_hamr]
            selected_satellites.update(selected_hamr)
            for sat in selected_hamr:
                object_classifications[sat] = "HAMR"

    # Step 2: Proximity filtering
    if config.enable_proximity or "PROX" in (config.object_types or []):
        proximity_sats, proximity_pairs = filter_proximity_objects(
            all_satellites, obs_df, config.proximity_angular_threshold_deg
        )
        metadata["proximity_satellites"] = list(proximity_sats)
        metadata["proximity_pairs"] = [
            {"sat1": p[0], "sat2": p[1], "separation_deg": p[2], "time": str(p[3])}
            for p in proximity_pairs
        ]
        metadata["filters_applied"].append("PROXIMITY")

        # Select percentage of proximity objects
        proximity_list = list(proximity_sats)
        n_prox = max(1, int(len(proximity_list) * config.proximity_percentage))
        if proximity_list:
            selected_prox = proximity_list[:n_prox]
            selected_satellites.update(selected_prox)
            for sat in selected_prox:
                if sat not in object_classifications:
                    object_classifications[sat] = "PROX"

    # Step 3: Calibration filtering
    if config.enable_calibration or "CALIB" in (config.object_types or []):
        calib_sats, other_sats = filter_calibration_satellites(
            all_satellites, config.calibration_satellites
        )
        metadata["calibration_satellites"] = calib_sats
        metadata["filters_applied"].append("CALIBRATION")

        # Select percentage of calibration objects
        n_calib = max(1, int(len(calib_sats) * config.calibration_percentage))
        if calib_sats:
            selected_calib = calib_sats[:n_calib]
            selected_satellites.update(selected_calib)
            for sat in selected_calib:
                if sat not in object_classifications:
                    object_classifications[sat] = "CALIB"

    # Step 4: Add normal satellites if needed or if "NORM" or "ALL" specified
    if "NORM" in (config.object_types or []) or "ALL" in (config.object_types or []):
        # Add satellites not already classified
        normal_sats = [
            sat for sat in all_satellites
            if sat not in object_classifications
        ]
        metadata["normal_satellites"] = normal_sats

        if "ALL" in (config.object_types or []):
            # Include all satellites
            selected_satellites.update(all_satellites)
            for sat in all_satellites:
                if sat not in object_classifications:
                    object_classifications[sat] = "NORM"
        else:
            # Add normal satellites to reach target count
            remaining_spots = max(0, len(all_satellites) - len(selected_satellites))
            if remaining_spots > 0 and normal_sats:
                selected_normal = normal_sats[:remaining_spots]
                selected_satellites.update(selected_normal)
                for sat in selected_normal:
                    if sat not in object_classifications:
                        object_classifications[sat] = "NORM"

    # If no filters applied, include all satellites
    if not selected_satellites:
        selected_satellites = set(all_satellites)
        for sat in all_satellites:
            object_classifications[sat] = "NORM"

    # Filter observations to selected satellites
    filtered_obs = obs_df[obs_df["satNo"].isin(selected_satellites)].copy()

    # Add object type classification to observations
    filtered_obs["object_type"] = filtered_obs["satNo"].map(
        lambda x: object_classifications.get(x, "NORM")
    )

    metadata["selected_satellites"] = list(selected_satellites)
    metadata["object_classifications"] = object_classifications
    metadata["final_satellite_count"] = len(selected_satellites)
    metadata["final_observation_count"] = len(filtered_obs)
    metadata["status"] = "success"

    logger.info(
        f"Object type filtering complete: {len(selected_satellites)} satellites selected, "
        f"{len(filtered_obs)} observations"
    )

    return filtered_obs, metadata


# =============================================================================
# HELPER FUNCTIONS FOR API INTEGRATION
# =============================================================================


def fetch_esa_physical_data(
    satellite_ids: List[int],
    api_token: Optional[str] = None,
    use_cache: bool = True,
    cache_hours: int = 168,  # 1 week cache
) -> Dict[int, Dict]:
    """
    Fetch physical satellite data from ESA DiscoSweb API.

    Per Louis's specification, used for HAMR (High Area-to-Mass Ratio) filtering.
    HAMR objects have A/M > 0.1 m²/kg.

    Args:
        satellite_ids: List of NORAD catalog IDs
        api_token: ESA DiscoSweb API token (uses env var if not provided)
        use_cache: Whether to use cached results
        cache_hours: Cache expiration time in hours

    Returns:
        Dict mapping NORAD ID to physical properties:
        {
            norad_id: {
                'mass': float (kg),
                'cross_section': float (m²),
                'area_to_mass_ratio': float (m²/kg),
                'object_class': str,
                'is_hamr': bool,
            }
        }
    """
    import os
    import json
    from pathlib import Path
    from datetime import timedelta
    import requests

    # Get API token from environment if not provided
    if api_token is None:
        api_token = os.environ.get("ESA_DISCOS_API_TOKEN", "")

    if not api_token:
        logger.warning(
            "ESA DiscoSweb API token not configured. "
            "Set ESA_DISCOS_API_TOKEN environment variable. "
            "HAMR filtering will not work without physical data."
        )
        return {}

    # Check cache first
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_file = cache_dir / "esa_physical_data.json"

    if use_cache and cache_file.exists():
        try:
            cache_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - cache_mtime < timedelta(hours=cache_hours):
                with open(cache_file, "r") as f:
                    cached_data = json.load(f)
                    # Filter to requested satellite IDs
                    results = {}
                    for sat_id in satellite_ids:
                        str_id = str(sat_id)
                        if str_id in cached_data:
                            results[sat_id] = cached_data[str_id]
                    if results:
                        logger.info(f"Loaded {len(results)} satellite records from ESA cache")
                        return results
        except Exception as e:
            logger.debug(f"Could not load ESA cache: {e}")

    # ESA DiscoSweb API endpoint
    ESA_DISCOS_API_URL = "https://discosweb.esoc.esa.int/api"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/vnd.api+json",
    }

    results = {}

    # Query in batches to avoid rate limits
    batch_size = 50
    for i in range(0, len(satellite_ids), batch_size):
        batch = satellite_ids[i:i + batch_size]

        for norad_id in batch:
            try:
                # Query DiscoSweb for object by NORAD ID
                url = f"{ESA_DISCOS_API_URL}/objects"
                params = {
                    "filter": f"eq(satno,{norad_id})",
                    "fields[object]": "satno,objectClass,mass,xSectAvg,name",
                }

                response = requests.get(
                    url, headers=headers, params=params, timeout=30
                )

                if response.status_code == 401:
                    logger.error("ESA DiscoSweb authentication failed - check API token")
                    return results

                if response.status_code == 429:
                    logger.warning("ESA DiscoSweb rate limit hit - using partial results")
                    break

                if response.status_code != 200:
                    logger.debug(f"ESA query for {norad_id} returned status {response.status_code}")
                    continue

                data = response.json()

                if data.get("data") and len(data["data"]) > 0:
                    obj = data["data"][0]
                    attrs = obj.get("attributes", {})

                    mass = attrs.get("mass")
                    cross_section = attrs.get("xSectAvg")

                    # Calculate area-to-mass ratio
                    if mass and cross_section and mass > 0:
                        a_m_ratio = cross_section / mass
                    else:
                        a_m_ratio = None

                    results[norad_id] = {
                        "mass": mass,
                        "cross_section": cross_section,
                        "area_to_mass_ratio": a_m_ratio,
                        "object_class": attrs.get("objectClass"),
                        "name": attrs.get("name"),
                        "is_hamr": a_m_ratio is not None and a_m_ratio > HAMR_THRESHOLD,
                    }

            except requests.exceptions.Timeout:
                logger.warning(f"ESA query timeout for {norad_id}")
                continue
            except requests.exceptions.RequestException as e:
                logger.debug(f"ESA query error for {norad_id}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Error processing ESA data for {norad_id}: {e}")
                continue

    # Save results to cache
    if use_cache and results:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Load existing cache and merge
            existing_cache = {}
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        existing_cache = json.load(f)
                except Exception:
                    pass

            # Merge new results
            for sat_id, data in results.items():
                existing_cache[str(sat_id)] = data

            with open(cache_file, "w") as f:
                json.dump(existing_cache, f, indent=2, default=str)

            logger.debug(f"Saved {len(results)} ESA records to cache")
        except Exception as e:
            logger.warning(f"Could not save ESA cache: {e}")

    logger.info(f"Fetched physical data for {len(results)}/{len(satellite_ids)} satellites from ESA DiscoSweb")
    return results


def filter_hamr_by_esa_data(
    satellite_ids: List[int],
    include_hamr: bool = True,
    api_token: Optional[str] = None,
) -> Tuple[List[int], Dict[str, Any]]:
    """
    Filter satellites based on HAMR classification from ESA DiscoSweb.

    Per Louis's specification, HAMR objects have area-to-mass ratio > 0.1 m²/kg.

    Args:
        satellite_ids: Input NORAD IDs
        include_hamr: If True, return only HAMR objects; if False, exclude HAMR
        api_token: ESA DiscoSweb API token

    Returns:
        Tuple of (filtered_ids, metadata)
    """
    physical_data = fetch_esa_physical_data(satellite_ids, api_token)

    filtered = []
    hamr_found = 0
    non_hamr_found = 0
    unknown = 0

    for norad_id in satellite_ids:
        data = physical_data.get(norad_id, {})
        is_hamr = data.get("is_hamr", False)
        has_data = "area_to_mass_ratio" in data

        if not has_data:
            unknown += 1
            # Include unknowns in non-HAMR by default
            if not include_hamr:
                filtered.append(norad_id)
        elif is_hamr:
            hamr_found += 1
            if include_hamr:
                filtered.append(norad_id)
        else:
            non_hamr_found += 1
            if not include_hamr:
                filtered.append(norad_id)

    metadata = {
        "total_input": len(satellite_ids),
        "hamr_count": hamr_found,
        "non_hamr_count": non_hamr_found,
        "unknown_count": unknown,
        "filtered_count": len(filtered),
        "include_hamr": include_hamr,
        "hamr_threshold": HAMR_THRESHOLD,
    }

    return filtered, metadata


def get_object_type_statistics(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    physical_data: Dict[int, Dict] = None,
) -> Dict[str, Any]:
    """
    Get statistics about object types in the observation data.

    Args:
        obs_df: DataFrame of observations
        sat_params: Dict mapping satNo to orbital parameters
        physical_data: Dict mapping satNo to physical properties

    Returns:
        Dict with statistics about each object type
    """
    if obs_df.empty:
        return {"status": "empty_input"}

    all_satellites = obs_df["satNo"].unique().tolist()

    # Count by type
    hamr_sats, _ = filter_hamr_objects(
        all_satellites, physical_data or {}, HAMR_THRESHOLD
    )
    calib_sats, _ = filter_calibration_satellites(all_satellites)
    prox_sats, _ = filter_proximity_objects(all_satellites, obs_df)

    stats = {
        "total_satellites": len(all_satellites),
        "hamr_count": len(hamr_sats),
        "hamr_percentage": len(hamr_sats) / len(all_satellites) * 100 if all_satellites else 0,
        "calibration_count": len(calib_sats),
        "calibration_percentage": len(calib_sats) / len(all_satellites) * 100 if all_satellites else 0,
        "proximity_count": len(prox_sats),
        "proximity_percentage": len(prox_sats) / len(all_satellites) * 100 if all_satellites else 0,
        "normal_count": len(all_satellites) - len(set(hamr_sats) | set(calib_sats) | prox_sats),
    }

    return stats


# =============================================================================
# LEGACY 16-CHARACTER CODE FILTERING (Louis's Documentation)
# =============================================================================


def compute_physical_distance(
    pos1_km: Tuple[float, float, float],
    pos2_km: Tuple[float, float, float],
) -> float:
    """
    Compute physical distance between two 3D positions.

    Args:
        pos1_km: (x, y, z) position in km (ECI or ECEF frame)
        pos2_km: (x, y, z) position in km (ECI or ECEF frame)

    Returns:
        Distance in km
    """
    x1, y1, z1 = pos1_km
    x2, y2, z2 = pos2_km
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)


def compute_velocity_difference(
    vel1_km_s: Tuple[float, float, float],
    vel2_km_s: Tuple[float, float, float],
) -> float:
    """
    Compute relative velocity difference between two objects.

    Args:
        vel1_km_s: (vx, vy, vz) velocity in km/s
        vel2_km_s: (vx, vy, vz) velocity in km/s

    Returns:
        Relative velocity magnitude in m/s
    """
    vx1, vy1, vz1 = vel1_km_s
    vx2, vy2, vz2 = vel2_km_s
    # Convert km/s to m/s and compute magnitude of difference
    return np.sqrt((vx2 - vx1) ** 2 + (vy2 - vy1) ** 2 + (vz2 - vz1) ** 2) * 1000.0


def filter_physical_proximity(
    satellite_ids: List[int],
    state_data: Dict[int, Dict],
    threshold_km: float = PROXIMITY_DISTANCE_THRESHOLD_KM,
    velocity_threshold_m_s: float = PROXIMITY_VELOCITY_THRESHOLD_M_S,
    time_window_hours: float = 24.0,
    require_velocity: bool = False,
) -> Tuple[Set[int], List[Dict[str, Any]]]:
    """
    Filter satellites by physical proximity (close approach).

    This identifies objects that are physically close to each other in 3D space,
    as opposed to just appearing close in angular coordinates.

    For Close Objects (C) in legacy code per Louis's specification:
    "distance < X km, velocity < X m/s"

    Args:
        satellite_ids: List of NORAD catalog numbers to consider
        state_data: Dict mapping satNo to state data with:
                   - 'position': (x, y, z) in km
                   - 'velocity': (vx, vy, vz) in km/s (optional)
                   - 'epoch': datetime (optional, for time correlation)
        threshold_km: Physical distance threshold in km (default 100 km)
        velocity_threshold_m_s: Relative velocity threshold in m/s (default 100 m/s)
        time_window_hours: Time window to consider states as concurrent
        require_velocity: If True, only consider pairs with velocity data

    Returns:
        Tuple of (proximity_satellites, proximity_events)
        proximity_satellites: Set of satellite IDs involved in close approaches
        proximity_events: List of close approach event dictionaries
    """
    if not state_data or len(satellite_ids) < 2:
        return set(), []

    proximity_satellites = set()
    proximity_events = []

    # Get satellites with valid state data
    valid_sats = [
        sat_id for sat_id in satellite_ids
        if sat_id in state_data and "position" in state_data[sat_id]
    ]

    if len(valid_sats) < 2:
        logger.warning("Insufficient valid state data for physical proximity filtering")
        return set(), []

    # Check all pairs
    for i, sat1 in enumerate(valid_sats):
        state1 = state_data[sat1]
        pos1 = state1["position"]
        vel1 = state1.get("velocity")

        for sat2 in valid_sats[i + 1:]:
            state2 = state_data[sat2]
            pos2 = state2["position"]
            vel2 = state2.get("velocity")

            # Check time proximity if epochs available
            epoch1 = state1.get("epoch")
            epoch2 = state2.get("epoch")
            if epoch1 and epoch2:
                if isinstance(epoch1, str):
                    epoch1 = pd.to_datetime(epoch1)
                if isinstance(epoch2, str):
                    epoch2 = pd.to_datetime(epoch2)
                time_diff_hours = abs((epoch2 - epoch1).total_seconds()) / 3600
                if time_diff_hours > time_window_hours:
                    continue

            # Compute physical distance
            distance = compute_physical_distance(pos1, pos2)

            # Check distance threshold
            if distance > threshold_km:
                continue

            # Compute relative velocity if available
            relative_velocity_m_s = None
            velocity_check_passed = True

            if vel1 is not None and vel2 is not None:
                relative_velocity_m_s = compute_velocity_difference(vel1, vel2)
                # Per Louis's spec: both distance AND velocity must be below thresholds
                velocity_check_passed = relative_velocity_m_s <= velocity_threshold_m_s
            elif require_velocity:
                # Skip pairs without velocity data if required
                continue

            # Both distance and velocity (if available) must pass
            if velocity_check_passed:
                proximity_satellites.add(sat1)
                proximity_satellites.add(sat2)

                event = {
                    "sat1": sat1,
                    "sat2": sat2,
                    "distance_km": distance,
                    "relative_velocity_m_s": relative_velocity_m_s,
                    "epoch1": str(epoch1) if epoch1 else None,
                    "epoch2": str(epoch2) if epoch2 else None,
                }
                proximity_events.append(event)

                vel_info = f", velocity {relative_velocity_m_s:.1f} m/s" if relative_velocity_m_s else ""
                logger.debug(
                    f"Physical proximity detected: {sat1} - {sat2} at {distance:.2f} km{vel_info}"
                )

    logger.info(
        f"Physical proximity filtering: found {len(proximity_satellites)} satellites "
        f"in {len(proximity_events)} close approach events "
        f"(distance threshold: {threshold_km} km, velocity threshold: {velocity_threshold_m_s} m/s)"
    )

    return proximity_satellites, proximity_events


def filter_by_object_type_code(
    obs_df: pd.DataFrame,
    object_type_code: str,
    sat_params: Dict[int, Dict] = None,
    physical_data: Dict[int, Dict] = None,
    state_data: Dict[int, Dict] = None,
    target_count: int = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Filter observations based on legacy 16-character object type code.

    Maps the single-character object type codes (H/C/A/U/N) to appropriate
    filtering logic as specified in Louis's documentation.

    Object Type Codes:
        H (HAMR): High Area-to-Mass Ratio objects (A/M > 1.0 m²/kg)
        C (Close): Physical proximity objects (distance < 100 km)
        A (Apparent): Angular proximity objects (separation < 0.5°)
        U (Unspecified): No filtering, include all objects
        N (Calibration): Only include calibration satellites from predefined list

    Args:
        obs_df: DataFrame of observations with 'satNo' column
        object_type_code: Single character code: H, C, A, U, or N
        sat_params: Dict mapping satNo to orbital parameters
        physical_data: Dict mapping satNo to physical properties (mass, area)
        state_data: Dict mapping satNo to state vectors (for C filtering)
        target_count: Optional target number of objects to select

    Returns:
        Tuple of (filtered_obs_df, metadata)

    Raises:
        ValueError: If object_type_code is not valid
    """
    valid_codes = list(LEGACY_OBJECT_TYPE_MAP.keys())
    if object_type_code not in valid_codes:
        raise ValueError(
            f"Invalid object type code '{object_type_code}'. "
            f"Valid codes are: {valid_codes}"
        )

    if obs_df.empty:
        return obs_df, {"status": "empty_input", "object_type_code": object_type_code}

    all_satellites = obs_df["satNo"].unique().tolist()
    selected_satellites = []
    metadata = {
        "object_type_code": object_type_code,
        "object_type_name": LEGACY_OBJECT_TYPE_MAP.get(object_type_code, "Unknown"),
        "total_satellites": len(all_satellites),
        "filters_applied": [],
    }

    # Initialize data structures if not provided
    if sat_params is None:
        sat_params = {}
    if physical_data is None:
        physical_data = {}
    if state_data is None:
        state_data = {}

    # Apply appropriate filter based on object type code
    if object_type_code == "H":
        # HAMR: High Area-to-Mass Ratio objects
        hamr_sats, normal_sats = filter_hamr_objects(
            all_satellites, physical_data, HAMR_THRESHOLD
        )
        selected_satellites = hamr_sats
        metadata["filters_applied"].append("HAMR")
        metadata["hamr_count"] = len(hamr_sats)
        metadata["hamr_threshold_m2_kg"] = HAMR_THRESHOLD

        # If no HAMR objects found with physical data, try TLE-based estimation
        if not hamr_sats:
            logger.warning(
                "No HAMR objects found with physical data. "
                "Consider providing physical_data for accurate HAMR filtering."
            )

    elif object_type_code == "C":
        # Close: Physical proximity objects
        # Per Louis's spec: "distance < X km, velocity < X m/s"
        prox_sats, prox_events = filter_physical_proximity(
            all_satellites,
            state_data,
            threshold_km=PROXIMITY_DISTANCE_THRESHOLD_KM,
            velocity_threshold_m_s=PROXIMITY_VELOCITY_THRESHOLD_M_S,
            require_velocity=False,  # Allow matching without velocity if not available
        )
        selected_satellites = list(prox_sats)
        metadata["filters_applied"].append("PHYSICAL_PROXIMITY")
        metadata["proximity_count"] = len(prox_sats)
        metadata["proximity_events"] = prox_events
        metadata["proximity_threshold_km"] = PROXIMITY_DISTANCE_THRESHOLD_KM
        metadata["velocity_threshold_m_s"] = PROXIMITY_VELOCITY_THRESHOLD_M_S

        if not prox_sats:
            logger.warning(
                "No physical proximity objects found. "
                "Consider providing state_data (with 'position' and 'velocity' keys) "
                "for accurate Close filtering per Louis's spec."
            )

    elif object_type_code == "A":
        # Apparent: Angular proximity objects
        angular_prox_sats, angular_pairs = filter_proximity_objects(
            all_satellites, obs_df, PROXIMITY_ANGULAR_THRESHOLD_DEG
        )
        selected_satellites = list(angular_prox_sats)
        metadata["filters_applied"].append("ANGULAR_PROXIMITY")
        metadata["angular_proximity_count"] = len(angular_prox_sats)
        metadata["angular_pairs"] = [
            {"sat1": p[0], "sat2": p[1], "separation_deg": p[2], "time": str(p[3])}
            for p in angular_pairs
        ]
        metadata["angular_threshold_deg"] = PROXIMITY_ANGULAR_THRESHOLD_DEG

    elif object_type_code == "U":
        # Unspecified: Include all objects, no filtering
        selected_satellites = all_satellites
        metadata["filters_applied"].append("NONE")

    elif object_type_code == "N":
        # Calibration: Only calibration satellites
        calib_sats, other_sats = filter_calibration_satellites(all_satellites)
        selected_satellites = calib_sats
        metadata["filters_applied"].append("CALIBRATION")
        metadata["calibration_count"] = len(calib_sats)
        metadata["calibration_list_used"] = len(CALIBRATION_SATELLITES)

    # Apply target count limit if specified
    if target_count is not None and len(selected_satellites) > target_count:
        # Randomly sample to target count for reproducibility
        np.random.seed(42)  # Use fixed seed for reproducibility
        selected_satellites = list(
            np.random.choice(selected_satellites, size=target_count, replace=False)
        )
        metadata["target_count_applied"] = target_count

    # Filter observations to selected satellites
    if selected_satellites:
        filtered_obs = obs_df[obs_df["satNo"].isin(selected_satellites)].copy()
    else:
        # Return empty DataFrame if no satellites selected
        filtered_obs = obs_df.iloc[:0].copy()
        logger.warning(
            f"No satellites selected for object type code '{object_type_code}'"
        )

    metadata["selected_satellites"] = selected_satellites
    metadata["selected_count"] = len(selected_satellites)
    metadata["observation_count"] = len(filtered_obs)
    metadata["status"] = "success" if selected_satellites else "no_matches"

    logger.info(
        f"Object type filtering (code={object_type_code}): "
        f"{len(selected_satellites)} satellites, {len(filtered_obs)} observations"
    )

    return filtered_obs, metadata


def get_legacy_object_type_description(code: str) -> str:
    """
    Get human-readable description for a legacy object type code.

    Args:
        code: Single character object type code (H/C/A/U/N)

    Returns:
        Human-readable description
    """
    descriptions = {
        "H": f"HAMR (High Area-to-Mass Ratio) - Objects with A/M > {HAMR_THRESHOLD} m²/kg",
        "C": (
            f"Close proximity - Objects physically close "
            f"(distance < {PROXIMITY_DISTANCE_THRESHOLD_KM} km, "
            f"velocity < {PROXIMITY_VELOCITY_THRESHOLD_M_S} m/s)"
        ),
        "A": f"Apparent proximity - Objects appearing close in sky (< {PROXIMITY_ANGULAR_THRESHOLD_DEG}°)",
        "U": "Unspecified - All objects included without filtering",
        "N": "Calibration - Well-known satellites with good orbit determination",
    }
    return descriptions.get(code, f"Unknown object type code: {code}")
