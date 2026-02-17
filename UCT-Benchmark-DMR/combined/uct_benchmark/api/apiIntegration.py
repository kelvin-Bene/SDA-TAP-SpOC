# -*- coding: utf-8 -*-
"""
Created on Fri Jun  6 08:51:11 2025

@author: Gabriel Lundin

Combined API Integration module merging:
- Kelvin's core pipeline functions with database integration
- Blake's enhancements (caching, metrics, smart queries, new service wrappers)
"""

import asyncio
import base64
import datetime
import hashlib
import json
import os
import re
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np

# initialize orekit and JVM
# - This must be done only once per program execution -
# - If orekit is already initialized, these lines will have no effect -
# - Using orekit_jpype as it is better maintained -
# - Expecting OREKIT_DATA_PATH environment variable to be set -
import orekit_jpype as orekit
import pandas as pd
import requests
from loguru import logger

vm_started = orekit.initVM()
from orekit_jpype.pyhelpers import setup_orekit_curdir

orekit_data_path = os.getenv("OREKIT_DATA_PATH", "./orekit-data-main")
# setup_orekit_curdir(orekit_data_path)
setup_orekit_curdir(from_pip_library=True)

from org.orekit.propagation.analytical.tle import TLE, TLEPropagator

from uct_benchmark.data.dataManipulation import binTracks
from uct_benchmark.settings import (
    INTERIM_DATA_DIR,
    api_config,
    semiMajorAxis_GEO,
    semiMajorAxis_LEO,
)

# Optional database integration (opt-in)
# Import database module if available, but don't fail if not present
_DATABASE_AVAILABLE = False
try:
    from uct_benchmark.database import DatabaseManager

    _DATABASE_AVAILABLE = True
except ImportError:
    DatabaseManager = None


# Because HTTPS is annoying
def _suppress_warnings():
    """Suppress HTTPS verification warnings."""
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")


# Backward-compatible alias (deprecated)
_supressWarn = _suppress_warnings


def _check_api_response(response: "requests.Response", service_name: str) -> None:
    """
    Check API response and raise appropriate errors.

    Args:
        response: The requests Response object
        service_name: Name of the API service for error messages

    Raises:
        requests.exceptions.HTTPError: If response indicates an error
    """
    if response.status_code == 200:
        return

    error_messages = {
        401: "Authentication failed",
        403: "Access forbidden",
        404: "Resource not found",
        429: "Rate limit exceeded",
        500: "Server error",
        502: "Bad gateway",
        503: "Service unavailable",
    }

    msg = error_messages.get(response.status_code, f"HTTP {response.status_code}")
    raise requests.exceptions.HTTPError(f"{service_name}: {msg}")


# =============================================================================
# API CALL LOGGING AND METRICS
# =============================================================================

# Global API call metrics
_api_call_metrics: Dict[str, Any] = {
    "total_calls": 0,
    "total_records": 0,
    "total_errors": 0,
    "call_history": [],
}

# API logger (separate from main logger for filtering)
api_logger = logger.bind(name="udl.api")


def _log_api_call(
    service: str,
    params: Dict,
    response_size: int,
    elapsed_time: float,
    success: bool = True,
    error_msg: Optional[str] = None,
) -> None:
    """Log each UDL API call with metrics."""
    call_record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "service": service,
        "params": {k: str(v)[:100] for k, v in params.items()},  # Truncate long values
        "response_records": response_size,
        "elapsed_ms": elapsed_time * 1000,
        "success": success,
        "error": error_msg,
    }

    _api_call_metrics["total_calls"] += 1
    _api_call_metrics["total_records"] += response_size
    if not success:
        _api_call_metrics["total_errors"] += 1

    # Keep last 100 calls for debugging
    _api_call_metrics["call_history"].append(call_record)
    if len(_api_call_metrics["call_history"]) > 100:
        _api_call_metrics["call_history"].pop(0)

    if success:
        api_logger.debug(
            f"API call: {service} returned {response_size} records in {elapsed_time * 1000:.1f}ms"
        )
    else:
        api_logger.warning(f"API call failed: {service} - {error_msg}")


def get_api_metrics() -> Dict[str, Any]:
    """Return current API call metrics."""
    return _api_call_metrics.copy()


def reset_api_metrics() -> None:
    """Reset API call metrics."""
    global _api_call_metrics
    _api_call_metrics = {
        "total_calls": 0,
        "total_records": 0,
        "total_errors": 0,
        "call_history": [],
    }


# =============================================================================
# RESPONSE CACHING
# =============================================================================


class QueryCache:
    """Thread-safe cache for UDL query responses."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 900):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

    def _make_key(self, service: str, params: Dict) -> str:
        """Generate cache key from service and params."""
        params_str = json.dumps(params, sort_keys=True, default=str)
        return hashlib.md5(f"{service}:{params_str}".encode()).hexdigest()

    def get(self, service: str, params: Dict) -> Optional[Any]:
        """Get cached response if available and not expired."""
        key = self._make_key(service, params)
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl_seconds:
                logger.debug(f"Cache hit for {service}")
                return data
            else:
                del self._cache[key]
        return None

    def set(self, service: str, params: Dict, data: Any) -> None:
        """Cache response data."""
        if len(self._cache) >= self._max_size:
            # Remove oldest entries
            oldest_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])[
                : self._max_size // 4
            ]
            for k in oldest_keys:
                del self._cache[k]

        key = self._make_key(service, params)
        self._cache[key] = (data, time.time())

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()


# Global cache instance
_query_cache = QueryCache(
    max_size=api_config.cache_max_size, ttl_seconds=api_config.cache_ttl_seconds
)


# =============================================================================
# ORBITAL REGIME DETECTION
# =============================================================================


def determine_orbital_regime(semi_major_axis_km: float, eccentricity: float = 0.0) -> str:
    """
    Determine the orbital regime based on semi-major axis and eccentricity.

    Args:
        semi_major_axis_km: Semi-major axis in kilometers
        eccentricity: Orbital eccentricity (default 0)

    Returns:
        str: One of 'LEO', 'MEO', 'GEO', 'HEO'
    """
    if eccentricity >= 0.7:
        return "HEO"
    elif semi_major_axis_km < semiMajorAxis_LEO:
        return "LEO"
    elif semi_major_axis_km >= semiMajorAxis_GEO:
        return "GEO"
    else:
        return "MEO"


def get_batch_size_for_regime(regime: str) -> datetime.timedelta:
    """Get the recommended batch query size for a given orbital regime."""
    return api_config.batch_sizes.get(regime, datetime.timedelta(hours=6))


# =============================================================================
# COUNT-FIRST QUERY STRATEGY
# =============================================================================


def UDLQueryCount(token: str, service: str, params: Dict) -> int:
    """
    Perform a count query to check how many records would be returned.

    Args:
        token: UDL authentication token
        service: UDL service name
        params: Query parameters

    Returns:
        int: Count of matching records
    """
    return UDLQuery(token, service, params, count=True)


def smart_query(token: str, service: str, params: Dict, threshold: int = None) -> pd.DataFrame:
    """
    Perform an intelligent query that checks count first and splits if needed.

    Args:
        token: UDL authentication token
        service: UDL service name
        params: Query parameters
        threshold: Max records per query (default from config)

    Returns:
        pd.DataFrame: Query results
    """
    if threshold is None:
        threshold = api_config.count_first_threshold

    # Check cache first
    if api_config.enable_cache:
        cached = _query_cache.get(service, params)
        if cached is not None:
            return cached

    # Get count first
    try:
        count = UDLQueryCount(token, service, params)
    except Exception as e:
        logger.warning(f"Count query failed, proceeding with direct query: {e}")
        count = 0

    if count > threshold:
        logger.info(f"Large result set ({count} records), splitting query...")
        result = _chunked_time_query(token, service, params, count)
    else:
        result = UDLQuery(token, service, params)

    # Cache result
    if api_config.enable_cache and not result.empty:
        _query_cache.set(service, params, result)

    return result


def _chunked_time_query(
    token: str, service: str, params: Dict, expected_count: int
) -> pd.DataFrame:
    """
    Split a large query into smaller time-based chunks.

    Args:
        token: UDL authentication token
        service: UDL service name
        params: Query parameters (must contain time field like 'obTime' or 'epoch')
        expected_count: Expected total record count

    Returns:
        pd.DataFrame: Combined results from all chunks
    """
    # Find time field in params
    time_fields = ["obTime", "epoch", "createdAt", "time"]
    time_field = None
    time_range = None

    for field in time_fields:
        if field in params:
            time_range = params[field]
            time_field = field
            break

    if time_field is None or ".." not in str(time_range):
        # Can't chunk, try with pagination
        logger.warning("Cannot chunk query - no time range found. Using pagination.")
        return _paginated_query(token, service, params)

    # Parse time range
    start_str, end_str = str(time_range).split("..")
    start_time = UDLToDatetime(start_str)
    end_time = UDLToDatetime(end_str)

    # Calculate chunk size based on expected count
    num_chunks = max(2, expected_count // api_config.max_results_per_query + 1)
    total_seconds = (end_time - start_time).total_seconds()
    chunk_seconds = total_seconds / num_chunks

    # Build chunk params list
    params_list = []
    current_start = start_time
    for i in range(num_chunks):
        current_end = current_start + datetime.timedelta(seconds=chunk_seconds)
        if i == num_chunks - 1:
            current_end = end_time

        chunk_params = params.copy()
        chunk_params[time_field] = f"{datetimeToUDL(current_start)}..{datetimeToUDL(current_end)}"
        params_list.append(chunk_params)
        current_start = current_end

    # Execute batch query
    return asyncUDLBatchQuery(token, service, params_list)


def _paginated_query(token: str, service: str, params: Dict, page_size: int = None) -> pd.DataFrame:
    """
    Perform paginated query for large result sets.

    Args:
        token: UDL authentication token
        service: UDL service name
        params: Query parameters
        page_size: Results per page (default from config)

    Returns:
        pd.DataFrame: All results combined
    """
    if page_size is None:
        page_size = api_config.max_results_per_query

    all_results = []
    offset = 0

    while True:
        page_params = params.copy()
        page_params["maxResults"] = page_size
        page_params["firstResult"] = offset

        result = UDLQuery(token, service, page_params)

        if result.empty:
            break

        all_results.append(result)
        offset += len(result)

        if len(result) < page_size:
            break

    if all_results:
        return pd.concat(all_results, ignore_index=True)
    return pd.DataFrame()


# =============================================================================
# NEW UDL SERVICE WRAPPERS
# =============================================================================


def queryRadarObservations(
    token: str, sat_ids: List[int], time_range: str, additional_params: Optional[Dict] = None
) -> pd.DataFrame:
    """
    Query radar observations from UDL.

    Args:
        token: UDL authentication token
        sat_ids: List of satellite NORAD IDs
        time_range: UDL time range string (e.g., '>now-7 days' or 'start..end')
        additional_params: Optional additional query parameters

    Returns:
        pd.DataFrame: Radar observation records
    """
    params = {
        "satNo": ",".join(map(str, sat_ids)),
        "obTime": time_range,
        "uct": "false",
        "dataMode": "REAL",
    }
    if additional_params:
        params.update(additional_params)

    return smart_query(token, "radarobservation", params)


def queryRFObservations(
    token: str, sat_ids: List[int], time_range: str, additional_params: Optional[Dict] = None
) -> pd.DataFrame:
    """
    Query RF observations from UDL.

    Args:
        token: UDL authentication token
        sat_ids: List of satellite NORAD IDs
        time_range: UDL time range string
        additional_params: Optional additional query parameters

    Returns:
        pd.DataFrame: RF observation records
    """
    params = {
        "satNo": ",".join(map(str, sat_ids)),
        "obTime": time_range,
        "uct": "false",
        "dataMode": "REAL",
    }
    if additional_params:
        params.update(additional_params)

    return smart_query(token, "rfobservation", params)


def queryConjunctions(
    token: str,
    sat_ids: Optional[List[int]] = None,
    time_range: Optional[str] = None,
    min_probability: Optional[float] = None,
    additional_params: Optional[Dict] = None,
) -> pd.DataFrame:
    """
    Query conjunction data messages (CDMs) from UDL.

    Args:
        token: UDL authentication token
        sat_ids: Optional list of satellite NORAD IDs
        time_range: Optional UDL time range string
        min_probability: Optional minimum collision probability filter
        additional_params: Optional additional query parameters

    Returns:
        pd.DataFrame: Conjunction data records
    """
    params = {}
    if sat_ids:
        params["satNo1"] = ",".join(map(str, sat_ids))
    if time_range:
        params["tca"] = time_range
    if min_probability is not None:
        params["collisionProbability"] = f">{min_probability}"

    if additional_params:
        params.update(additional_params)

    return smart_query(token, "conjunction", params)


def queryManeuvers(
    token: str, sat_ids: List[int], time_range: str, additional_params: Optional[Dict] = None
) -> pd.DataFrame:
    """
    Query detected/planned maneuver data from UDL.

    Args:
        token: UDL authentication token
        sat_ids: List of satellite NORAD IDs
        time_range: UDL time range string
        additional_params: Optional additional query parameters

    Returns:
        pd.DataFrame: Maneuver records
    """
    params = {
        "satNo": ",".join(map(str, sat_ids)),
        "maneuverTime": time_range,
    }
    if additional_params:
        params.update(additional_params)

    return smart_query(token, "maneuver", params)


def querySensorCalibration(
    token: str,
    sensor_ids: Optional[List[str]] = None,
    time_range: Optional[str] = None,
    additional_params: Optional[Dict] = None,
) -> pd.DataFrame:
    """
    Query sensor calibration data from UDL.

    Args:
        token: UDL authentication token
        sensor_ids: Optional list of sensor IDs
        time_range: Optional UDL time range string
        additional_params: Optional additional query parameters

    Returns:
        pd.DataFrame: Sensor calibration records
    """
    params = {}
    if sensor_ids:
        params["idSensor"] = ",".join(sensor_ids)
    if time_range:
        params["calibrationTime"] = time_range

    if additional_params:
        params.update(additional_params)

    return smart_query(token, "sensorcalibration", params)


# =============================================================================
# PARALLEL SERVICE QUERIES
# =============================================================================


async def _async_pull_comprehensive_data(
    token: str, sat_ids: List[int], time_range: str, services: List[str] = None
) -> Dict[str, pd.DataFrame]:
    """
    Pull data from multiple UDL services concurrently.

    Args:
        token: UDL authentication token
        sat_ids: List of satellite NORAD IDs
        time_range: UDL time range string
        services: List of services to query (default: eo, radar, statevector, elset)

    Returns:
        Dict mapping service names to DataFrames
    """
    if services is None:
        services = ["eoobservation", "radarobservation", "statevector", "elset"]

    sat_list = ",".join(map(str, sat_ids))

    # Build params for each service
    service_params = {
        "eoobservation": {
            "satNo": sat_list,
            "obTime": time_range,
            "uct": "false",
            "dataMode": "REAL",
        },
        "radarobservation": {
            "satNo": sat_list,
            "obTime": time_range,
            "uct": "false",
            "dataMode": "REAL",
        },
        "rfobservation": {
            "satNo": sat_list,
            "obTime": time_range,
            "uct": "false",
            "dataMode": "REAL",
        },
        "statevector": {
            "satNo": sat_list,
            "epoch": time_range,
            "uct": "false",
            "dataMode": "REAL",
            "sort": "epoch,DESC",
        },
        "elset": {
            "satNo": sat_list,
            "epoch": time_range,
            "uct": "false",
            "dataMode": "REAL",
            "sort": "epoch,DESC",
        },
    }

    async def query_service(service: str) -> Tuple[str, pd.DataFrame]:
        params = service_params.get(service, {"satNo": sat_list})
        try:
            result = await _asyncUDLQuery(token, service, params)
            return service, result
        except Exception as e:
            logger.warning(f"Failed to query {service}: {e}")
            return service, pd.DataFrame()

    # Run all queries concurrently
    tasks = [query_service(svc) for svc in services if svc in service_params]
    results = await asyncio.gather(*tasks)

    return dict(results)


def pullComprehensiveData(
    token: str, sat_ids: List[int], time_range: str, services: List[str] = None
) -> Dict[str, pd.DataFrame]:
    """
    Pull data from multiple UDL services concurrently.

    Args:
        token: UDL authentication token
        sat_ids: List of satellite NORAD IDs
        time_range: UDL time range string
        services: List of services to query

    Returns:
        Dict mapping service names to DataFrames
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_async_pull_comprehensive_data(token, sat_ids, time_range, services))
    else:
        import nest_asyncio

        nest_asyncio.apply()
        return asyncio.get_event_loop().run_until_complete(
            _async_pull_comprehensive_data(token, sat_ids, time_range, services)
        )


def pullMultiPhenomenologyData(
    token: str, sat_ids: List[int], time_range: str
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Pull EO, Radar, and RF observations for multi-phenomenology datasets.

    Args:
        token: UDL authentication token
        sat_ids: List of satellite NORAD IDs
        time_range: UDL time range string

    Returns:
        Tuple of (eo_obs, radar_obs, rf_obs) DataFrames
    """
    results = pullComprehensiveData(
        token, sat_ids, time_range, services=["eoobservation", "radarobservation", "rfobservation"]
    )
    return (
        results.get("eoobservation", pd.DataFrame()),
        results.get("radarobservation", pd.DataFrame()),
        results.get("rfobservation", pd.DataFrame()),
    )


# =============================================================================
# ADAPTIVE BATCH SIZING
# =============================================================================


def generateAdaptiveBatchParams(
    sat_ids: List[int],
    sat_params: Dict[int, Dict],
    timeframe: int,
    timeunit: str,
    end_time: datetime.datetime = None,
) -> List[Tuple[List[int], str]]:
    """
    Generate batch query parameters with regime-adaptive time windows.

    Groups satellites by orbital regime and creates appropriate batch sizes.

    Args:
        sat_ids: List of satellite NORAD IDs
        sat_params: Dict mapping satNo to orbital parameters (needs 'Semi-Major Axis')
        timeframe: Total timeframe
        timeunit: Timeframe unit (days, hours, etc.)
        end_time: End time for queries (default: now)

    Returns:
        List of (sat_ids_batch, time_range_str) tuples
    """
    if end_time is None:
        end_time = datetime.datetime.utcnow()

    total_duration = pd.Timedelta(**{timeunit: timeframe})
    start_time = end_time - total_duration

    # Group satellites by regime
    regime_sats: Dict[str, List[int]] = {"LEO": [], "MEO": [], "GEO": [], "HEO": []}

    for sat_id in sat_ids:
        params = sat_params.get(sat_id, {})
        sma = params.get("Semi-Major Axis", 7000)  # Default to LEO
        ecc = params.get("Eccentricity", 0.0)
        regime = determine_orbital_regime(sma, ecc)
        regime_sats[regime].append(sat_id)

    batch_params = []

    for regime, sats in regime_sats.items():
        if not sats:
            continue

        batch_duration = get_batch_size_for_regime(regime)
        current_start = start_time

        while current_start < end_time:
            current_end = min(current_start + batch_duration, end_time)
            time_range = f"{datetimeToUDL(current_start)}..{datetimeToUDL(current_end)}"
            batch_params.append((sats, time_range))
            current_start = current_end

    return batch_params


def addManeuverFlags(obs_df: pd.DataFrame, token: str, hours_threshold: int = 24) -> pd.DataFrame:
    """
    Add maneuver proximity flags to observations.

    Queries the maneuver service and flags observations within N hours of a detected maneuver.

    Args:
        obs_df: DataFrame of observations with 'satNo' and 'obTime' columns
        token: UDL authentication token
        hours_threshold: Hours before/after maneuver to flag

    Returns:
        DataFrame with 'nearManeuver' boolean column added
    """
    if obs_df.empty:
        obs_df["nearManeuver"] = False
        return obs_df

    # Get unique satellites and time range
    sat_ids = obs_df["satNo"].unique().tolist()

    # Ensure obTime is datetime
    if obs_df["obTime"].dtype == "object":
        obs_df = obs_df.copy()
        obs_df["obTime"] = pd.to_datetime(obs_df["obTime"])

    start_time = obs_df["obTime"].min() - pd.Timedelta(hours=hours_threshold)
    end_time = obs_df["obTime"].max() + pd.Timedelta(hours=hours_threshold)
    time_range = f"{datetimeToUDL(start_time)}..{datetimeToUDL(end_time)}"

    # Query maneuvers
    try:
        maneuvers = queryManeuvers(token, sat_ids, time_range)
    except Exception as e:
        logger.warning(f"Failed to query maneuvers: {e}")
        obs_df["nearManeuver"] = False
        return obs_df

    if maneuvers.empty:
        obs_df["nearManeuver"] = False
        return obs_df

    # Parse maneuver times
    if "maneuverTime" in maneuvers.columns:
        maneuvers["maneuverTime"] = pd.to_datetime(maneuvers["maneuverTime"])

        # Create threshold timedelta
        threshold = pd.Timedelta(hours=hours_threshold)

        # Check each observation against maneuvers
        def is_near_maneuver(row):
            sat_maneuvers = maneuvers[maneuvers["satNo"] == row["satNo"]]
            if sat_maneuvers.empty:
                return False
            time_diffs = abs(sat_maneuvers["maneuverTime"] - row["obTime"])
            return (time_diffs <= threshold).any()

        obs_df["nearManeuver"] = obs_df.apply(is_near_maneuver, axis=1)
    else:
        obs_df["nearManeuver"] = False

    return obs_df


# =============================================================================
# CORE API FUNCTIONS
# =============================================================================


def UDLTokenGen(username, password):
    """
    Generates a UDL token with your login information if you don't already have one.
    WARNING: This function is not encrypted. If your login is sensitive, PLEASE MANUALLY GENERATE YOUR TOKEN.

    Args:
        username (string): Your UDL username.
        password (string): Your UDL password.

    Returns:
        string: Your UDL Base64 token for login.

    Raises:
        TypeError: If either input is not a string.
    """

    if not all(isinstance(var, str) for var in [username, password]):
        raise TypeError(
            f"Username and password must be strings, got types {type(username).__name__} and {type(password).__name__} instead."
        )
    return base64.b64encode((username + ":" + password).encode("utf-8")).decode("ascii")


def spacetrackTokenGen(username, password):
    """
    Generates a Space-Track token with your login information.
    This is specific to this API integration and cannot be generated on Space-Track's website.

    Args:
        username (string): Your Space-Track username.
        password (string): Your Space-Track password.

    Returns:
        dict: Your Space-Track token for login.

    Raises:
        TypeError: If either input is not a string.
    """

    if not all(isinstance(var, str) for var in [username, password]):
        raise TypeError(
            f"Username and password must be strings, got types {type(username).__name__} and {type(password).__name__} instead."
        )
    return {"identity": username, "password": password}


def UDLQuery(token, service, params, count=False, history=False):
    """
    Performs a UDL search using the given parameters.

    Args:
        token (string): Your UDL Base64 login token. If you don't have one, use UDLTokenGen or the Utilities page of the UDL Help site.
        service (string): The service requested from UDL.
        params (dict): A dictionary of search parameters in the form {'parameter': 'value'}. The following symbols are accepted before value (for equal, leave prefix blank):
            '~value': not equal
            '*value*': like
            '>value': greater than or equal to
            '<value': less than or equal to
            'value1..value2': between
            'value1,value2': in
        Specific parameters valid for all queries are:
            sort: 'value,ASC/DESC'
            maxResults: 'amount'
            fistResult: 'amount' (offsets search)
            columns: 'value1,value2' (constrains result columns)
        For time-based values, the following format is required: 'YYYY-MM-DDTHH:MM:SS.sZ'. Note that the quantity of 's' depends on your service and parameter.
        count (bool): If True, returns a count query instead of a data one. Defaults to False.
        history (bool): If True, uses the History Rest API instead of the standard Rest API. Defaults to False.

    Returns:
        Pandas DataFrame: The results of your query (count = False)
        int: The count for your query (count = True)

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If query fails.
    """

    # Error handling
    _supressWarn()

    if not (
        isinstance(token, str)
        and isinstance(service, str)
        and isinstance(params, dict)
        and isinstance(count, bool)
        and isinstance(history, bool)
    ):
        raise TypeError(
            f"Expected (string, string, dict, bool, bool), got ({type(token).__name__}, {type(service).__name__}, {type(params).__name__}, {type(count).__name__}, {type(history).__name__}) instead."
        )

    # Set up params for call
    basicAuth = "Basic " + token

    url = "https://unifieddatalibrary.com/udl/" + service.lower()
    if history:
        url = url + "/history"
    if count:
        url = url + "/count"

    # Call with timing
    start_time = time.perf_counter()
    logger.info(f"Performing UDL query on service '{service}' with parameters={params}...")

    try:
        resp = requests.get(url, headers={"Authorization": basicAuth}, params=params, verify=False)
        elapsed = time.perf_counter() - start_time

        # If call worked, return data
        if resp.status_code != 200:
            error_msg = None
            if resp.status_code == 400:
                error_msg = "Query failed due to bad parameters."
            elif resp.status_code == 401:
                error_msg = "Query failed due to invalid login."
            elif resp.status_code == 500:
                error_msg = "Query failed due to internal error; if UDL isn't down, likely a time-out for excessive data request."
            else:
                error_msg = "Query failed for unknown reason."

            _log_api_call(service, params, 0, elapsed, success=False, error_msg=error_msg)
            raise requests.exceptions.HTTPError(resp, error_msg)

        result = resp.json()
        response_size = result if count else len(result)
        _log_api_call(
            service,
            params,
            response_size if isinstance(response_size, int) else len(result),
            elapsed,
        )

        if not count:
            return pd.DataFrame(result)
        else:
            return result

    except requests.exceptions.RequestException as e:
        elapsed = time.perf_counter() - start_time
        _log_api_call(service, params, 0, elapsed, success=False, error_msg=str(e))
        raise


def TLEToSV(line1, line2):
    """
    Uses Orekit to obtain a state vector for a given TLE.

    Args:
        line1 (string): TLE line 1.
        line2 (string): TLE line 2.

    Returns:
        Numpy Array: (6,) Numpy array containing the corresponding state vector in km and km/s.

    Raises:
        TypeError: If inputs are not strings.
    """

    # Error handling
    if not all(isinstance(var, str) for var in [line1, line2]):
        raise TypeError(
            f"TLE lines must be strings, got types {type(line1).__name__} and {type(line2).__name__} instead."
        )

    # Set up Orekit TLE
    tle = TLE(line1, line2)
    propagator = TLEPropagator.selectExtrapolator(tle)
    date = tle.getDate()

    # Obtain and parse state vector
    pv_coords = propagator.getPVCoordinates(date)
    position = np.array(pv_coords.getPosition().toArray()) / 1000.0  # m to km
    velocity = np.array(pv_coords.getVelocity().toArray()) / 1000.0  # m/s to km/s
    return np.hstack((position, velocity))


def parseTLE(line1, line2):
    """
    Parses a TLE given in standard UDL form.

    Args:
        line1, line2 (string): lines 1 and 2 of a TLE

    Returns:
        dict: A dict containing the TLE information in the following format:
            'NORAD_ID': int
            'classification': string
            'COSPAR_ID': string
            'epoch': datetime
            'BC': float
            'n_ddot': float
            'B_star': float
            'ephemeris_type': int
            'elset_num': int
            'inclination': float
            'RAAN': float
            'eccentricity': float
            'perigee': float
            'mean_anomaly': float
            'mean_motion': float
            'rev_num': int
            'line1': string
            'line2': string

    Raises:
        TypeError: If inputs are not strings.
    """

    # Error handling
    if not all(isinstance(var, str) for var in [line1, line2]):
        raise TypeError(
            f"TLE lines must be strings, got types {type(line1).__name__} and {type(line2).__name__} instead."
        )

    TLE = line1 + " " + line2
    lines = TLE.split()

    # Fix potential lack of end values (thanks Orekit)
    if len(lines) > 17:
        lines = lines[:16] + ["".join(lines[16:]).replace(" ", "0")]

    # TLE parsing
    elset = {
        "NORAD_ID": int(lines[1][0:-1]),
        "classification": lines[1][-1],
        "COSPAR_ID": lines[2],
        "BC": float(re.sub(r"^([+-]?)(\d{5})([+-]\d)$", r"\g<1>0.\g<2>e\g<3>", lines[4])),
        "n_ddot": float(re.sub(r"^([+-]?)(\d{5})([+-]\d)$", r"\g<1>0.\g<2>e\g<3>", lines[5]))
        if lines[5] != "00000-0"
        else 0.0,
        "B_star": float(re.sub(r"^([+-]?)(\d{5})([+-]\d)$", r"\g<1>0.\g<2>e\g<3>", lines[6]))
        if lines[6] != "00000-0"
        else 0.0,
        "ephemeris_type": int(lines[7]),
        "elset_num": int(lines[8][0:-1]),
        "inclination": float(lines[11]),
        "RAAN": float(lines[12]),
        "eccentricity": float(lines[13]) / (10**7),
        "perigee": float(lines[14]),
        "mean_anomaly": float(lines[15]),
        "mean_motion": float(lines[16][0:11]),
        "rev_num": int(lines[16][11:-1]),
        "line1": line1,
        "line2": line2,
    }

    # Format epoch year correctly
    year = int(lines[3][0:2])
    if year > 56:
        year += 1900
    else:
        year += 2000

    elset["epoch"] = datetime.datetime(year, 1, 1) + datetime.timedelta(
        days=float(lines[3][2:]) - 1
    )

    return elset


def spacetrackQuery(token, params, request="satcat", controller="basicspacedata"):
    """
    Performs a Space-Track search using the given parameters.

    Args:
        token (dict): Your Space-Track login token. If you don't have one, use spacetrackTokenGen.
        params (dict): A dictionary of search parameters in the form {'parameter': 'value'}. The following symbols are accepted before value (for equal, leave prefix blank):
            '<>value': not equal
            '~~value': like
            '^value': like (after value only)
            '>value': greater than or equal to
            '<value': less than or equal to
            'value1--value2': between
            'value1,value2': or
        Specific parameters valid for all queries are:
            orderby: 'VALUE asc/desc' (VALUE must be all caps)
            metadata: 'true'
            emptyresult: 'show'
        For time-based values, the following format is required: 'YYYY-MM-DD'.
        request (string): The request class desired from Space-Track. Defaults to "satcat".
        controller (string): The controller requested from Space-Track. Defaults to "basicspacedata"

    Returns:
        Pandas DataFrame: The results of your query.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If login or query fails.
    """

    # Error handling
    _supressWarn()

    if not (
        isinstance(token, dict)
        and isinstance(controller, str)
        and isinstance(params, dict)
        and isinstance(request, str)
    ):
        raise TypeError(
            f"Expected (dict, dict, string, string), got ({type(token).__name__}, {type(params).__name__}, {type(request).__name__}, {type(controller).__name__}) instead."
        )

    # Set up query params
    uriBase = "https://www.space-track.org"
    requestLogin = "/ajaxauth/login"
    requestCmdAction = "/" + controller + "/query"
    requestFind = "/class/" + request
    requestFind.join(f"/{k.upper()}/{v}" for k, v in params.items())

    # Spacetrack requires lowercase
    if any(k.lower() == "format" for k in params):
        params = {k: v for k, v in params.items() if k.lower() != "format"}

    # Perform query
    with requests.Session() as session:
        resp = session.post(uriBase + requestLogin, data=token)
        if resp.status_code != 200:
            raise requests.exceptions.HTTPError(resp, "Login failed; double-check login info.")

        resp = session.get(uriBase + requestCmdAction + requestFind)
        if resp.status_code != 200:
            if resp.status_code == 500:
                raise requests.exceptions.HTTPError(
                    resp, "Query failed due to throttle limit (500); please slow down!"
                )
            if resp.status_code == 401:
                raise requests.exceptions.HTTPError(
                    resp, "Query failed due to bad credentials (401)."
                )
            else:
                raise requests.exceptions.HTTPError(
                    resp,
                    "Query failed for unknown reason ("
                    + str(resp.status_code)
                    + "); double-check search parameters.",
                )

        session.close()
    return pd.DataFrame(resp.json())


def discoswebQuery(token, params, data="objects", version=2):
    """
    Performs an ESA Discosweb search using the given parameters.

    Args:
        token (string): Your ESA Discosweb access token. If you don't have one, generate one at https://discosweb.esoc.esa.int/tokens.
        params (dict): A string of search parameters in the form "searchTerm1&searchTerm2". Please read https://discosweb.esoc.esa.int/apidocs/v2 for formatting.
        data (string): The requested data type from Discosweb. Defaults to "objects".
        version (int): The requested Discosweb API version. Defaults to version 2.

    Returns:
        Pandas DataFrame: The results of your query.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If login or query fails.
    """

    # Error handling
    if not (
        isinstance(token, str)
        and isinstance(data, str)
        and isinstance(params, str)
        and isinstance(version, int)
    ):
        raise TypeError(
            f"Expected (string, string, string, int), got ({type(token).__name__}, {type(params).__name__}, {type(data).__name__}, {type(version).__name__}) instead."
        )

    # Set up query
    URL = "https://discosweb.esoc.esa.int"

    auth = {"Authorization": f"Bearer {token}", "DiscosWeb-Api-Version": str(version)}

    # Perform query
    resp = requests.get(
        f"{URL}/api/{data}",
        headers=auth,
        params={"filter": params},
    )

    if resp.status_code != 200:
        if resp.status_code == 429:
            raise requests.exceptions.HTTPError(
                resp, "Query failed due to API rate limit (429). Slow down!"
            )
        else:
            raise requests.exceptions.HTTPError(
                resp,
                "Query failed for unknown reason ("
                + str(resp.status_code)
                + "); double-check login info and query parameters.",
            )
    return pd.DataFrame(resp.json()["data"])


def celestrakSatcat():
    """
    Grabs the entire CelesTrak satcat. Probably very slow.

    Returns:
        Pandas DataFrame: The sat cat.
    """

    URL = "https://celestrak.org/pub/satcat.csv"

    return pd.read_csv(URL)


def celestrakQuery(params, table="gp"):
    """
    Performs a CelesTrak search using the given parameters.

    Args:
        params (dict): A dictionary of search parameters in the form {'parameter': 'value'}. Inequalities are not accepted for this type of query.
        table (string): The requested CelesTrak database, either gp variants or satcat. Defaults to "gp".

    Returns:
        Pandas DataFrame: The results of your query.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If query fails.
    """

    # Error handling
    if not (isinstance(params, dict) and isinstance(table, str)):
        raise TypeError(
            f"Expected (dict, string), got ({type(params).__name__}, {type(table).__name__}) instead."
        )

    # Set up query
    if table.lower() == "satcat":
        URL = "https://celestrak.org/satcat/records.php"
    else:
        URL = "https://celestrak.org/NORAD/elements/" + table.lower() + ".php"

    params = {k.upper(): v for k, v in params.items() if k.upper() != "FORMAT"}

    params["FORMAT"] = "JSON"

    # Perform query
    resp = requests.get(
        URL,
        params=params,
    )

    if resp.status_code != 200:
        raise requests.exceptions.HTTPError(
            resp,
            "Query failed for unknown reason ("
            + str(resp.status_code)
            + "); double-check query parameters.",
        )
    return pd.DataFrame(resp.json())


def datetimeToUDL(time, micro=6):
    """
    Converts a datetime object to UDL formatting.

    Args:
        time (datetime.datetime): Time you wish to convert.
        micro (int): Amount of fraction-second precision needed. Max and defaults to 6.

    Returns:
        String: UDL-formatted timestamp.

    Raises:
        TypeError: If input types are incorrect.
    """

    if not isinstance(micro, int):
        raise TypeError(f"Expected micro to  be an int, got {type(micro).__name__}) instead.")

    micro = max(micro, 6)

    return time.strftime("%Y-%m-%dT%H:%M:%S.") + str(time.microsecond)[0:micro] + "Z"


def UDLToDatetime(time):
    """
    Converts a UDL formatted timestamp to a datetime object.

    Args:
        time (string): Timestamp you wish to convert.

    Returns:
        datetime.datetime: Datetime object.

    Raises:
        TypeError: If input types are incorrect.
    """

    return datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")


async def _asyncUDLQuery(token, service, params, count=False, history=False, max_retries=3):
    """
    Async version of UDLQuery using aiohttp with retry logic and timeout.
    """

    # Error handling
    if not (
        isinstance(token, str)
        and isinstance(service, str)
        and isinstance(params, dict)
        and isinstance(count, bool)
        and isinstance(history, bool)
    ):
        raise TypeError(
            f"Expected (string, string, dict, bool, bool), got "
            f"({type(token).__name__}, {type(service).__name__}, "
            f"{type(params).__name__}, {type(count).__name__}, {type(history).__name__})"
        )

    # Form query params
    base_url = "https://unifieddatalibrary.com/udl/"
    url = base_url + service.lower()
    if history:
        url += "/history"
    if count:
        url += "/count"

    headers = {"Authorization": "Basic " + token}

    # Configure timeout (120 seconds for large queries)
    timeout = aiohttp.ClientTimeout(total=120)

    last_error = None
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, params=params, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data if count else pd.DataFrame(data)
                    elif response.status == 500 and attempt < max_retries - 1:
                        # Retry on 500 errors (server overload/timeout)
                        await asyncio.sleep(2**attempt)  # Exponential backoff
                        continue
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Query failed. Common status codes: 400 - bad params, 401 - invalid login, 500 - internal error (UDL down or time-out).",
                        )
        except asyncio.TimeoutError:
            last_error = asyncio.TimeoutError(
                f"Query timed out after 120 seconds (attempt {attempt + 1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            raise last_error
        except aiohttp.ClientError as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            raise


async def _batchUDLQuery(
    token, service, params_list, dt=1.0, count=False, history=False, max_concurrent=5
):
    """
    Internal wrapper for _asyncUDLQuery() that performs the asyncio calls.
    Uses semaphore to limit concurrent requests and prevent server overload.
    """
    results = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_query(params):
        async with semaphore:
            await asyncio.sleep(dt)  # Rate limit between queries
            return await _asyncUDLQuery(token, service, params, count, history)

    tasks = [limited_query(p) for p in params_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions and log them
    valid_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Query {i} failed: {result}")
        else:
            valid_results.append(result)

    if not valid_results:
        raise RuntimeError("All batch queries failed")

    return sum(valid_results) if count else pd.concat(valid_results, ignore_index=True)


def asyncUDLBatchQuery(token, service, params_list, dt=0.1, count=False, history=False):
    """
    Performs an async batch of UDL searchs using the given parameters.

    Args:
        token (string): Your UDL Base64 login token. If you don't have one, use UDLTokenGen or the Utilities page of the UDL Help site.
        service (string): The service requested from UDL.
        params_list (list): A list of params sent into UDLQuery. Read that documentation for more information.
        dt (float): Rate limit for UDL calls in seconds. Defaults to 1 second.
        count (bool): If True, returns a count query instead of a data one. Defaults to False.
        history (bool): If True, uses the History Rest API instead of the standard Rest API. Defaults to False.

    Returns:
        Pandas DataFrame: The results of your queries concated (count = False)
        int: The sum of all query counts (count = True)

    Raises:
        TypeError: If input types are incorrect.
        ClientResponseError: If a query fails.
    """
    # Try-Except to handle certain Python clients which already run an async loop
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_batchUDLQuery(token, service, params_list, dt, count, history))
    else:
        import nest_asyncio

        nest_asyncio.apply()
        return asyncio.get_event_loop().run_until_complete(
            _batchUDLQuery(token, service, params_list, dt, count, history)
        )


# ============================================================
# SEARCH STRATEGY FUNCTIONS
# ============================================================

# Regime ranges from reference batchPull.py — removed because 'range' is not a valid
# field on the eoobservation endpoint. The reference code iterated over multiple sensor
# types (eoobservation, radarobservation, rfobservation); 'range' may have been valid
# for radar but silently returned zero results for EO observations.
# REGIME_RANGES = {
#     "LEO": "<2000",
#     "MEO": "2000..35786",
#     "GEO": ">35786",
#     "HEO": ">35786",
# }


def _fetch_observations_fast(
    token, sat_ids, sweep_time, max_datapoints, dt, progress_callback=None, DatasetStage=None
):
    """
    FAST strategy: Single query per satellite, full time range.

    Fastest approach but may hit API limits for large time ranges.
    """
    params_list = [
        {
            "satNo": str(ID),
            "obTime": sweep_time,
            "uct": "false",
            "dataMode": "REAL",
            "maxResults": max_datapoints,
        }
        for ID in sat_ids
    ]
    if max_datapoints <= 0:
        params_list = [{k: v for k, v in d.items() if k != "maxResults"} for d in params_list]
    return asyncUDLBatchQuery(token, "eoobservation", params_list, dt)


def _fetch_observations_windowed(
    token,
    sat_ids,
    start_time,
    end_time,
    window_size_minutes,
    dt,
    progress_callback=None,
    DatasetStage=None,
):
    """
    WINDOWED strategy: Fixed time windows with per-satellite queries.

    Splits the time range into windows and queries all satellites in parallel
    per window using asyncUDLBatchQuery. Provides fine-grained time coverage
    at the cost of more API calls.

    Args:
        token: UDL auth token
        sat_ids: List of satellite NORAD IDs to query
        start_time: Start datetime
        end_time: End datetime
        window_size_minutes: Size of each query window in minutes
        dt: Rate limit delay between queries
        progress_callback: Optional progress reporting callback
        DatasetStage: Optional stage enum for progress reporting
    """
    if not sat_ids:
        return pd.DataFrame()

    window_delta = datetime.timedelta(minutes=window_size_minutes)
    total_duration = end_time - start_time
    total_windows = max(1, int(total_duration / window_delta) + 1)

    logger.info(
        f"Windowed strategy: {len(sat_ids)} satellites, "
        f"{total_windows} windows of {window_size_minutes}min"
    )

    data_list = []
    current_time = start_time
    window_count = 0

    while current_time < end_time:
        window_end = min(current_time + window_delta, end_time)
        ob_time = f"{datetimeToUDL(current_time)}..{datetimeToUDL(window_end)}"

        params_list = [
            {
                "satNo": str(sat_id),
                "obTime": ob_time,
                "uct": "false",
                "dataMode": "REAL",
            }
            for sat_id in sat_ids
        ]

        try:
            window_data = asyncUDLBatchQuery(token, "eoobservation", params_list, dt)
            if not window_data.empty:
                data_list.append(window_data)
        except Exception as e:
            logger.warning(f"Window query failed: {e}")

        window_count += 1
        if progress_callback and DatasetStage:
            progress_callback(DatasetStage.COLLECTING_OBSERVATIONS, window_count / total_windows)

        current_time = window_end

    return pd.concat(data_list, ignore_index=True) if data_list else pd.DataFrame()


def _fetch_observations_hybrid(
    token,
    sat_ids,
    sweep_time,
    start_time,
    end_time,
    max_datapoints,
    dt,
    progress_callback=None,
    DatasetStage=None,
):
    """
    HYBRID strategy: Count-first check with dynamic chunking via smart_query().

    Best balance of speed and completeness. Recommended default.
    """
    all_results = []
    total_sats = len(sat_ids)

    for idx, sat_id in enumerate(sat_ids):
        params = {"satNo": str(sat_id), "obTime": sweep_time, "uct": "false", "dataMode": "REAL"}
        if max_datapoints > 0:
            params["maxResults"] = max_datapoints

        try:
            sat_data = smart_query(token, "eoobservation", params)
            if not sat_data.empty:
                all_results.append(sat_data)
        except Exception as e:
            logger.warning(f"Hybrid query failed for {sat_id}: {e}")

        if progress_callback and DatasetStage:
            progress_callback(DatasetStage.COLLECTING_OBSERVATIONS, (idx + 1) / total_sats)
        time.sleep(dt)

    return pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()


def generateDataset(
    UDL_token,
    ESA_token,
    satIDs,
    timeframe,
    timeunit,
    dt=0.1,
    max_datapoints=0,
    end_time="now",
    use_database=False,
    db_path=None,
    dataset_name=None,
    downsample_config=None,
    simulation_config=None,
    tier="T2",
    dataset_id=None,
    progress_callback=None,
    search_strategy="hybrid",
    window_size_minutes=10,
    regime="LEO",
):
    """
    Generates a benchmark  dataset given satellites and various parameters.

    Args:
        UDL_token (string): Your UDL Base64 login token. If you don't have one, use UDLTokenGen or the Utilities page of the UDL Help site.
        ESA_token (string): Your ESA Discosweb access token. If you don't have one, generate one at https://discosweb.esoc.esa.int/tokens.
        satIDs (numpy Array): List of satellites you wish to pull obs from.
        timeframe (int): Timespan of sweep.
        timeunit (string): Unit of timeframe.
        dt (float): Rate limit for UDL calls in sec. Please check EULA or contact Bluestack before making this very small. Defaults to 0.1.
        max_datapoints (int): If > 0, limit of obs data return per satellite, returning newest obs. Defaults to 0 (disabled), max 10000.
        end_time (datetime.datetime): Sets the end time of the data timespan. Defaults to 'now' which sets end to current time.
        use_database (bool): If True, persist data to DuckDB database. Defaults to False. Requires database module to be installed.
        db_path (string): Path to database file. If None, uses default path. Only used if use_database=True.
        dataset_name (string): Name for the dataset in database. Auto-generated if None. Only used if use_database=True.
        downsample_config (dict or DownsampleConfig): Configuration for downsampling. If dict with 'enabled': True,
            downsampling will be applied. Pass None or {'enabled': False} to skip.
        simulation_config (dict or SimulationConfig): Configuration for gap-filling simulation. If dict with 'enabled': True,
            simulation will be applied. Pass None or {'enabled': False} to skip.
        tier (string): Dataset quality tier (T1, T2, T3, T4). Affects downsampling intensity. Defaults to "T2".

    Returns:
        Pandas DataFrame: A dataset of "uct" observations.
        Pandas DataFrame: The truth observations, matched using "id" field.
        Pandas DataFrame: The truth state vectors of requested satellites.
        Pandas DataFrame: The truth TLEs of requested satellites.
        Array (int): All satellites that were actually obtained.
        Dict: Various runtime data.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError/ClientResponseError: If a query fails.
        ImportError: If use_database=True but database module is not available.
    """
    # Import DatasetStage enum for progress reporting
    try:
        from backend_api.jobs.progress import DatasetStage
    except ImportError:
        DatasetStage = None

    # Start timing the entire operation
    start_time = time.perf_counter()

    # Helper function to safely call progress callback
    def report_progress(stage, stage_progress=0.0):
        """Report progress if callback is provided."""
        if progress_callback is not None and stage is not None:
            try:
                progress_callback(stage, stage_progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    # Calculate actual times for all strategies
    if end_time != "now":
        actual_end_time = end_time
        actual_start_time = end_time - pd.Timedelta(**{timeunit: timeframe})
        sweep_time = datetimeToUDL(actual_start_time) + ".." + datetimeToUDL(actual_end_time)
    else:
        actual_end_time = datetime.datetime.utcnow()
        actual_start_time = actual_end_time - pd.Timedelta(**{timeunit: timeframe})
        sweep_time = ">now-" + str(timeframe) + " " + timeunit

    # Report progress: collecting observations
    if DatasetStage is not None:
        report_progress(DatasetStage.COLLECTING_OBSERVATIONS, 0.0)

    # Fetch observations using selected strategy
    logger.info(f"Using search strategy: {search_strategy}")

    if search_strategy == "fast":
        obs_truth_data = _fetch_observations_fast(
            UDL_token, satIDs, sweep_time, max_datapoints, dt, report_progress, DatasetStage
        )
    elif search_strategy == "windowed":
        obs_truth_data = _fetch_observations_windowed(
            UDL_token,
            satIDs,
            actual_start_time,
            actual_end_time,
            window_size_minutes,
            dt,
            report_progress,
            DatasetStage,
        )
    else:  # hybrid (default)
        obs_truth_data = _fetch_observations_hybrid(
            UDL_token,
            satIDs,
            sweep_time,
            actual_start_time,
            actual_end_time,
            max_datapoints,
            dt,
            report_progress,
            DatasetStage,
        )

    # Check for empty observation data
    if obs_truth_data.empty or "obTime" not in obs_truth_data.columns:
        raise ValueError(
            f"No observation data returned for satellites {satIDs}. "
            "The selected satellites may not have recent observation data. "
            "Try increasing the timeframe or selecting different satellites."
        )

    # Convert observation times to datetime objects
    obs_truth_data["obTime"] = [UDLToDatetime(t) for t in obs_truth_data["obTime"]]

    # Cull satIDs list to only include those for which data was actually returned
    requested_sats = len(satIDs)
    satIDs = obs_truth_data["satNo"].unique()
    obs_sats = len(satIDs)

    # Compute elapsed time for the observation query step
    obs_elapsed_time = time.perf_counter() - start_time

    # Report progress: observation collection complete, starting state vectors
    if DatasetStage is not None:
        report_progress(DatasetStage.COLLECTING_OBSERVATIONS, 1.0)
        report_progress(DatasetStage.COLLECTING_STATE_VECTORS, 0.0)

    # Grabs state vector data
    # Required to do batch call (no access to statevector/current)
    params_list = [
        {
            "satNo": str(ID),
            "epoch": sweep_time,
            "uct": "false",
            "dataMode": "REAL",
            "sort": "epoch,DESC",
        }
        for ID in satIDs
    ]

    state_truth_data = asyncUDLBatchQuery(UDL_token, "statevector", params_list, dt)

    # Remove duplicate state vectors and prioritize ones with covariance
    if state_truth_data["satNo"].nunique() < len(state_truth_data):
        df = state_truth_data.copy()
        # Create helper column to track presence of covariance
        cov_sources = ["eqCov", "cov"]
        df["has_cov"] = np.any(
            [
                df[col].notna() if col in df.columns else pd.Series(False, index=df.index)
                for col in cov_sources
            ],
            axis=0,
        )

        # Keep only rows with covariance
        df_with_cov = df[df["has_cov"]]

        # If no covariance for a satellite, it will disappear here
        if not df_with_cov.empty:
            # Sort by epoch descending so most recent first
            df_with_cov_sorted = df_with_cov.sort_values(by="epoch", ascending=False)

            # Select the most recent row WITH covariance for each satellite
            state_truth_data = (
                df_with_cov_sorted.groupby("satNo", group_keys=False).head(1).reset_index(drop=True)
            )
        else:
            # If absolutely no covariance anywhere, result is empty
            state_truth_data = df_with_cov.copy()

        # Drop the helper column if it still exists
        state_truth_data = state_truth_data.reset_index(drop=True)
        state_truth_data.drop(columns="has_cov", inplace=True, errors="ignore")

    # Convert epoch times to datetime
    state_truth_data["epoch"] = [UDLToDatetime(t) for t in state_truth_data["epoch"]]

    # Format drag coeff and solar rad coeff correctly
    cols_to_fill = ["dragCoeff", "solarRadPressCoeff"]
    for col in cols_to_fill:
        if col not in state_truth_data.columns:
            state_truth_data[col] = 0
        else:
            state_truth_data[col] = state_truth_data[col].fillna(0)

    # If a satellite has no orbit data, drop it from list and obs
    satIDs = state_truth_data["satNo"].unique()
    orbit_sats = len(satIDs)
    obs_truth_data = obs_truth_data[obs_truth_data["satNo"].isin(satIDs)]

    # Obtain mass and cross-sectional area from Discosweb
    if ESA_token:
        params = "in(satno,(" + ",".join(map(str, satIDs)) + "))"
        resp = discoswebQuery(ESA_token, params)

        # Only interested in mass and area
        keys = ["satno", "mass", "xSectAvg"]
        supp_data = pd.DataFrame([{k: d.get(k) for k in keys} for d in resp["attributes"]])
        # Rename columns for consistency with state_truth_data
        supp_data = supp_data.rename(columns={"satno": "satNo", "xSectAvg": "crossSection"})
        # Fill any missing values with 0
        supp_data = supp_data.fillna(0)
        # Merge into main dataset, ensuring no info is lost
        state_truth_data = pd.merge(state_truth_data, supp_data, on="satNo", how="left")
        state_truth_data = state_truth_data.fillna({"mass": 0, "crossSection": 0})
    else:
        logger.warning("No ESA token provided - skipping Discosweb query. Mass and crossSection will default to 0.")
        state_truth_data["mass"] = 0
        state_truth_data["crossSection"] = 0

    # Compute elapsed time for state vector query step
    sv_elapsed_time = time.perf_counter() - obs_elapsed_time - start_time

    # Report progress: state vector collection complete, starting TLE query
    if DatasetStage is not None:
        report_progress(DatasetStage.COLLECTING_STATE_VECTORS, 1.0)
        report_progress(DatasetStage.COLLECTING_TLES, 0.0)

    # Grab TLE data. Assumes that you can get it if a state vector exists
    # Use "current" call if allowed, else grab individuals
    if end_time == "now":
        elset_truth_data = UDLQuery(
            UDL_token,
            "elset/current",
            {
                "satNo": ",".join(map(str, satIDs)),
            },
        )
    else:
        params_list = [
            {
                "satNo": str(ID),
                "epoch": sweep_time,
                "uct": "false",
                "dataMode": "REAL",
                "sort": "epoch,DESC",
                "maxResults": 1,
            }
            for ID in satIDs
        ]
        elset_truth_data = asyncUDLBatchQuery(UDL_token, "elset", params_list, dt)

    # If a satellite has no TLE data, drop it from list, state vectors, and obs
    satIDs = elset_truth_data["satNo"].unique()
    elset_sats = len(satIDs)
    obs_truth_data = obs_truth_data[obs_truth_data["satNo"].isin(satIDs)]
    state_truth_data = state_truth_data[state_truth_data["satNo"].isin(satIDs)]

    # Parse TLEs into usable orbital elements
    elset_truth_data["elset"] = elset_truth_data.apply(
        lambda row: parseTLE(row["line1"], row["line2"]), axis=1
    )

    # Compute elapsed time for TLE query step
    elset_elapsed_time = time.perf_counter() - sv_elapsed_time - obs_elapsed_time - start_time

    # Report progress: TLE collection complete
    if DatasetStage is not None:
        report_progress(DatasetStage.COLLECTING_TLES, 1.0)

    # =========================================================================
    # OPTIONAL: Apply downsampling to reduce observation quality
    # =========================================================================
    downsampling_metadata = None
    if downsample_config is not None:
        # Check if enabled (handle both dict and dataclass)
        ds_enabled = False
        if isinstance(downsample_config, dict):
            ds_enabled = downsample_config.get("enabled", False)
        else:
            ds_enabled = getattr(downsample_config, "enabled", True)

        if ds_enabled:
            from uct_benchmark.data.dataManipulation import apply_downsampling
            from uct_benchmark.settings import DownsampleConfig as DSConfig
            from uct_benchmark.simulation.propagator import orbit2OE

            # Report progress: starting downsampling
            if DatasetStage is not None:
                report_progress(DatasetStage.APPLYING_DOWNSAMPLING, 0.0)

            logger.info(f"Applying {tier} downsampling to {len(obs_truth_data)} observations...")
            ds_start = time.perf_counter()

            # Build sat_params from TLE data
            sat_params = {}
            for _, row in elset_truth_data.iterrows():
                try:
                    sat_id = int(row["satNo"])
                    orb_elems = row.get("elset", {})
                    if not orb_elems:
                        orb_elems = orbit2OE(row["line1"], row["line2"])

                    sat_obs = obs_truth_data[obs_truth_data["satNo"] == sat_id]
                    period = orb_elems.get("period_sec", orb_elems.get("Period", 5400))

                    # Calculate max track gap
                    if len(sat_obs) > 1:
                        sorted_times = sat_obs["obTime"].sort_values()
                        gaps = sorted_times.diff().dropna()
                        max_gap_sec = gaps.max().total_seconds() if not gaps.empty else 0
                        max_track_gap = max_gap_sec / period if period > 0 else 0
                    else:
                        max_track_gap = 0

                    sat_params[sat_id] = {
                        "Semi-Major Axis": orb_elems.get(
                            "semi_major_axis", orb_elems.get("Semi-Major Axis", 7000)
                        ),
                        "Eccentricity": orb_elems.get(
                            "eccentricity", orb_elems.get("Eccentricity", 0.001)
                        ),
                        "Inclination": orb_elems.get(
                            "inclination", orb_elems.get("Inclination", 45)
                        ),
                        "RAAN": orb_elems.get("RAAN", orb_elems.get("raan", 0)),
                        "Argument of Perigee": orb_elems.get(
                            "perigee", orb_elems.get("Argument of Perigee", 0)
                        ),
                        "Mean Anomaly": orb_elems.get(
                            "mean_anomaly", orb_elems.get("Mean Anomaly", 0)
                        ),
                        "Period": period,
                        "Number of Obs": len(sat_obs),
                        "Orbital Coverage": 0.5,
                        "Max Track Gap": max_track_gap,
                    }
                except Exception as e:
                    logger.warning(f"Failed to build params for sat {row.get('satNo')}: {e}")
                    continue

            # Convert dict config to dataclass if needed
            if isinstance(downsample_config, dict):
                ds_cfg = DSConfig(
                    target_coverage=downsample_config.get("target_coverage", 0.05),
                    target_gap=downsample_config.get("target_gap", 2.0),
                    max_obs_per_sat=downsample_config.get("max_obs_per_sat", 50),
                    min_obs_per_sat=downsample_config.get("min_obs_per_sat", 5),
                    preserve_track_boundaries=downsample_config.get("preserve_tracks", True),
                    seed=downsample_config.get("seed"),
                )
            else:
                ds_cfg = downsample_config

            # Apply downsampling
            obs_truth_data, downsampling_metadata = apply_downsampling(
                obs_truth_data, sat_params, elset_data=elset_truth_data, config=ds_cfg, tier=tier
            )

            ds_elapsed = time.perf_counter() - ds_start
            downsampling_metadata["elapsed_time"] = ds_elapsed
            logger.info(
                f"Downsampling complete: {downsampling_metadata.get('original_count', 0)} -> "
                f"{downsampling_metadata.get('final_count', 0)} observations "
                f"({downsampling_metadata.get('retention_ratio', 0):.1%} retained) in {ds_elapsed:.2f}s"
            )

            # Report progress: downsampling complete
            if DatasetStage is not None:
                report_progress(DatasetStage.APPLYING_DOWNSAMPLING, 1.0)

            # Update satIDs to only include satellites that still have observations
            satIDs = obs_truth_data["satNo"].unique()

    # =========================================================================
    # OPTIONAL: Apply simulation to fill observation gaps
    # =========================================================================
    simulation_metadata = None
    if simulation_config is not None:
        # Check if enabled (handle both dict and dataclass)
        sim_enabled = False
        if isinstance(simulation_config, dict):
            sim_enabled = simulation_config.get("enabled", False)
        else:
            sim_enabled = getattr(simulation_config, "enabled", True)

        if sim_enabled:
            from uct_benchmark.data.dataManipulation import apply_simulation_to_gaps
            from uct_benchmark.settings import SimulationConfig as SimConfig

            # Report progress: starting simulation
            if DatasetStage is not None:
                report_progress(DatasetStage.RUNNING_SIMULATION, 0.0)

            logger.info(f"Applying gap-filling simulation to {len(obs_truth_data)} observations...")
            sim_start = time.perf_counter()

            # Build sensor dataframe (use defaults if not available)
            sensor_df = pd.DataFrame(
                {
                    "idSensor": ["SEN001", "SEN002", "SEN003"],
                    "name": ["DIEGO_GARCIA", "ASCENSION", "MAUI"],
                    "senlat": [-7.3, -7.9, 20.7],
                    "senlon": [72.4, -14.4, -156.3],
                    "senalt": [0.01, 0.04, 3.1],
                    "count": [10, 10, 10],
                }
            )

            # Convert dict config to dataclass if needed
            if isinstance(simulation_config, dict):
                sim_cfg = SimConfig(
                    apply_sensor_noise=simulation_config.get("apply_noise", True),
                    sensor_model=simulation_config.get("sensor_model", "GEODSS"),
                    max_synthetic_ratio=simulation_config.get("max_synthetic_ratio", 0.5),
                    seed=simulation_config.get("seed"),
                )
            else:
                sim_cfg = simulation_config

            # Apply simulation
            obs_truth_data, simulation_metadata = apply_simulation_to_gaps(
                obs_truth_data, elset_truth_data, sensor_df, config=sim_cfg
            )

            sim_elapsed = time.perf_counter() - sim_start
            simulation_metadata["elapsed_time"] = sim_elapsed
            logger.info(
                f"Simulation complete: {simulation_metadata.get('original_count', 0)} original + "
                f"{simulation_metadata.get('simulated_count', 0)} simulated = "
                f"{simulation_metadata.get('total_count', 0)} total in {sim_elapsed:.2f}s"
            )

            # Report progress: simulation complete
            if DatasetStage is not None:
                report_progress(DatasetStage.RUNNING_SIMULATION, 1.0)

            # Update satIDs
            satIDs = obs_truth_data["satNo"].unique()

    # Generate final dataset from observation data
    dataset = obs_truth_data.copy()
    dataset["uct"] = True  # Mark these as UCT/"unknown" points

    # Remove metadata columns that might identify data (silently ignore if any are missing)
    dataset = dataset.drop(
        columns=[
            "satNo",
            "idOnOrbit",
            "origObjectId",
            "rawFileURI",
            "createdAt",
            "trackId",
            "has_cov",
        ],
        errors="ignore",
    )

    # Create artificial track bins
    binned, _ = binTracks(obs_truth_data, state_truth_data)
    id_to_track = {}

    for track_idx, (_, _, df) in enumerate(binned):
        # Get all ids from this dataframe
        ids_in_track = df["id"].values
        # Map each id to the current track index
        id_to_track.update({id_: track_idx for id_ in ids_in_track})

    dataset["trackId"] = dataset["id"].map(id_to_track)
    dataset["origObjectId"] = dataset["id"].map(id_to_track)

    # Shuffle the dataset for good measure
    dataset = dataset.sample(frac=1).reset_index(drop=True)

    # Compute total elapsed time
    total_elapsed_time = time.perf_counter() - start_time

    # Collect and return all performance outputs
    performance_data = {
        "Observation Collection Time": obs_elapsed_time,
        "State Vector Collection Time": sv_elapsed_time,
        "TLE Collection Time": elset_elapsed_time,
        "Total Runtime": total_elapsed_time,
        "Desired Satellite Count": requested_sats,
        "Satellites with Observations": obs_sats,
        "Observed Satellites with SV Information": orbit_sats,
        "Observed Satellites with SV and TLE Information": elset_sats,
        "Tier": tier,
    }

    # Add downsampling metadata if applied
    if downsampling_metadata is not None:
        performance_data["Downsampling Applied"] = True
        performance_data["Downsampling Metadata"] = downsampling_metadata
    else:
        performance_data["Downsampling Applied"] = False

    # Add simulation metadata if applied
    if simulation_metadata is not None:
        performance_data["Simulation Applied"] = True
        performance_data["Simulation Metadata"] = simulation_metadata
        performance_data["Simulated Observation Count"] = simulation_metadata.get(
            "simulated_count", 0
        )
    else:
        performance_data["Simulation Applied"] = False
        performance_data["Simulated Observation Count"] = 0

    # Optional: Persist to database if requested
    if use_database:
        if not _DATABASE_AVAILABLE:
            raise ImportError(
                "Database module not available. Install uct_benchmark with database support "
                "or ensure the database module is in your Python path."
            )

        logger.info("Persisting dataset to database...")
        db_start_time = time.perf_counter()

        try:
            # Initialize database manager
            db = DatabaseManager(db_path=db_path)
            db.initialize()  # Ensure schema exists

            # Generate dataset name if not provided
            if dataset_name is None:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                dataset_name = f"dataset_{timestamp}"

            # Persist satellites
            for sat_no in satIDs:
                try:
                    db.satellites.get_by_sat_no(int(sat_no))
                except Exception:
                    db.satellites.create(sat_no=int(sat_no))

            # Persist observations
            if not obs_truth_data.empty:
                # Prepare observation data for bulk insert
                obs_for_db = obs_truth_data.copy()
                obs_for_db = obs_for_db.rename(
                    columns={
                        "satNo": "sat_no",
                        "obTime": "ob_time",
                        "declination": "declination",
                        "ra": "ra",
                        "sensorName": "sensor_name",
                        "idSensor": "sensor_name",  # Simulated data uses idSensor
                        "dataMode": "data_mode",
                        "trackId": "track_id",
                    }
                )
                db.observations.bulk_insert(obs_for_db)
                logger.debug(f"Inserted {len(obs_for_db)} observations")

            # Persist state vectors
            if not state_truth_data.empty:
                for _, row in state_truth_data.iterrows():
                    try:
                        db.state_vectors.create(
                            sat_no=int(row["satNo"]),
                            epoch=row["epoch"],
                            x_pos=row.get("xpos", row.get("x", 0)),
                            y_pos=row.get("ypos", row.get("y", 0)),
                            z_pos=row.get("zpos", row.get("z", 0)),
                            x_vel=row.get("xvel", row.get("vx", 0)),
                            y_vel=row.get("yvel", row.get("vy", 0)),
                            z_vel=row.get("zvel", row.get("vz", 0)),
                            covariance=row.get("cov_matrix"),
                            source="UDL",
                            data_mode=row.get("dataMode", "REAL"),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to insert state vector for sat {row['satNo']}: {e}")
                logger.debug(f"Inserted {len(state_truth_data)} state vectors")

            # Persist TLEs/element sets
            if not elset_truth_data.empty:
                for _, row in elset_truth_data.iterrows():
                    try:
                        elset = row.get("elset", {})
                        db.element_sets.create(
                            sat_no=int(row["satNo"]),
                            line1=row["line1"],
                            line2=row["line2"],
                            epoch=elset.get("epoch", row.get("epoch")),
                            inclination=elset.get("inclination"),
                            raan=elset.get("RAAN"),
                            eccentricity=elset.get("eccentricity"),
                            arg_perigee=elset.get("perigee"),
                            mean_anomaly=elset.get("mean_anomaly"),
                            mean_motion=elset.get("mean_motion"),
                            b_star=elset.get("B_star"),
                            source="UDL",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to insert TLE for sat {row['satNo']}: {e}")
                logger.debug(f"Inserted {len(elset_truth_data)} element sets")

            # Create dataset record if not already provided by backend API
            # NOTE: When called from backend, dataset_id should already exist
            logger.info(
                f"dataset_id parameter value: {dataset_id} (type: {type(dataset_id).__name__})"
            )
            if dataset_id is None:
                dataset_id = db.datasets.create_dataset(
                    name=dataset_name,
                    generation_params={
                        "timeframe": timeframe,
                        "timeunit": timeunit,
                        "satIDs": [int(s) for s in satIDs],
                        "end_time": str(end_time),
                        "max_datapoints": max_datapoints,
                    },
                )

            # Link observations to dataset
            if not obs_truth_data.empty:
                obs_ids = obs_truth_data["id"].tolist()
                # Build track assignments, converting NaN to None for DuckDB compatibility
                track_assignments = {}
                INT32_MAX = 2147483647  # Max value for INT32
                for _, row in obs_truth_data.iterrows():
                    track_id = row.get("trackId")
                    # Convert NaN/NaT to None (DuckDB can't handle NaN in INT columns)
                    if pd.isna(track_id):
                        track_id = None
                    elif track_id is not None:
                        # Convert to int if it's a string or float
                        try:
                            track_id = int(track_id)
                            # Check if value fits in INT32 (database schema limitation)
                            if track_id > INT32_MAX or track_id < -INT32_MAX:
                                track_id = None  # Too large for INT32, store as NULL
                        except (ValueError, TypeError):
                            track_id = None
                    track_assignments[row["id"]] = track_id
                db.datasets.add_observations_to_dataset(dataset_id, obs_ids, track_assignments)

            db_elapsed_time = time.perf_counter() - db_start_time
            performance_data["Database Persistence Time"] = db_elapsed_time
            performance_data["Database Dataset ID"] = dataset_id
            performance_data["Database Dataset Name"] = dataset_name
            logger.info(
                f"Dataset '{dataset_name}' (ID: {dataset_id}) persisted to database in {db_elapsed_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"Failed to persist to database: {e}")
            performance_data["Database Error"] = str(e)

    return dataset, obs_truth_data, state_truth_data, elset_truth_data, satIDs, performance_data


def pullStates(UDL_token, satIDs, timeframe, timeunit, dt=0.1, end_time="now"):
    """
    Generates a dataframe of state vectors from UDL data given desired window and satellites.

    Args:
        UDL_token (string): Your UDL Base64 login token. If you don't have one, use UDLTokenGen or the Utilities page of the UDL Help site.
        satIDs (numpy Array): List of satellites you wish to obtain vectors for.
        timeframe (int): Timespan of sweep.
        timeunit (string): Unit of timeframe.
        dt (float): Rate limit for UDL calls in sec. Please check EULA or contact Bluestack before making this very small. Defaults to 0.1.
        end_time (datetime.datetime): Sets the end time of the data timespan. Defaults to 'now' which sets end to current time.

    Returns:
        Pandas DataFrame: State vectors of requested satellites, with covariance.
        Pandas DataFrame: TLEs of requested satellites.
        Array (int): All satellites that were actually obtained.
        Float: Runtime.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError/ClientResponseError: If a query fails.
    """

    # Start timing the entire operation
    start_time = time.perf_counter()

    # Determine the time window for observation data based on the user-specified end_time
    if end_time != "now":
        # Construct a UDL time range string from (end_time - timeframe) to end_time
        sweep_time = (
            datetimeToUDL(end_time - pd.Timedelta(**{timeunit: timeframe}))
            + ".."
            + datetimeToUDL(end_time)
        )
    else:
        # Use relative time if 'now' is specified
        sweep_time = ">now-" + str(timeframe) + " " + timeunit

    # Grabs state vector data
    # Required to do batch call (no access to statevector/current)
    params_list = [
        {
            "satNo": str(ID),
            "epoch": sweep_time,
            "uct": "false",
            "dataMode": "REAL",
            "sort": "epoch,DESC",
        }
        for ID in satIDs
    ]

    sv_data = asyncUDLBatchQuery(UDL_token, "statevector", params_list, dt)

    # Remove duplicate state vectors and prioritize ones with covariance
    if sv_data["satNo"].nunique() < len(sv_data):
        df = sv_data.copy()
        # Create helper column to track presence of covariance
        cov_sources = ["eqCov", "cov"]
        df["has_cov"] = np.any(
            [
                df[col].notna() if col in df.columns else pd.Series(False, index=df.index)
                for col in cov_sources
            ],
            axis=0,
        )

        # Keep only rows with covariance
        df_with_cov = df[df["has_cov"]]

        # If no covariance for a satellite, it will disappear here
        if not df_with_cov.empty:
            # Sort by epoch descending so most recent first
            df_with_cov_sorted = df_with_cov.sort_values(by="epoch", ascending=False)

            # Select the most recent row WITH covariance for each satellite
            sv_data = (
                df_with_cov_sorted.groupby("satNo", group_keys=False).head(1).reset_index(drop=True)
            )
        else:
            # If absolutely no covariance anywhere, result is empty
            sv_data = df_with_cov.copy()

        # Drop the helper column if it still exists
        sv_data = sv_data.reset_index(drop=True)
        sv_data.drop(columns="has_cov", inplace=True, errors="ignore")

    # Convert epoch times to datetime
    sv_data["epoch"] = [UDLToDatetime(t) for t in sv_data["epoch"]]

    # Format drag coeff and solar rad coeff correctly
    cols_to_fill = ["dragCoeff", "solarRadPressCoeff"]
    for col in cols_to_fill:
        if col not in sv_data.columns:
            sv_data[col] = 0
        else:
            sv_data[col] = sv_data[col].fillna(0)

    # Grab TLE data. Assumes that you can get it if a state vector exists
    # Use "current" call if allowed, else grab individuals
    if end_time == "now":
        elset_data = UDLQuery(
            UDL_token,
            "elset/current",
            {
                "satNo": ",".join(map(str, satIDs)),
            },
        )
    else:
        params_list = [
            {
                "satNo": str(ID),
                "epoch": sweep_time,
                "uct": "false",
                "dataMode": "REAL",
                "sort": "epoch,DESC",
                "maxResults": 1,
            }
            for ID in satIDs
        ]
        elset_data = asyncUDLBatchQuery(UDL_token, "elset", params_list, dt)

    # If a satellite has no TLE data, drop it from list, state vectors, and obs
    satIDs = elset_data["satNo"].unique()
    sv_data = sv_data[sv_data["satNo"].isin(satIDs)]

    # Parse TLEs into usable orbital elements
    elset_data["elset"] = elset_data.apply(lambda row: parseTLE(row["line1"], row["line2"]), axis=1)

    return sv_data, elset_data, sv_data["satNo"].unique(), time.perf_counter() - start_time


def saveDataset(ref_obs, ref_track, ref_sv, ref_elset, output_path):
    """
    Saves obtained data to a json file in the format:
        output_json: {
            'dataset_obs': Dataframe
            'dataset_elset': Dataframe
            'reference': Dataframe containing:
                groupedObs
                groupedObsIds
                groupedElsets
                groupedElsetIds
            }

    Args:
        ref_obs (Pandas DataFrame): Dataframe of "truth" observations.
        ref_track (Pandas DataFrame): Dataframe of "truth" track TLEs.
        ref_sv (Pandas DataFrame): Dataframe of satellite state vector data.
        ref_elset (Pandas DataFrame): Dataframe of satellite TLE data.
        output_path (string): Relative save path for the file.

    Returns:
        The json data saved.
    """

    # Avoid modifying in place
    ref_obs = ref_obs.copy()
    ref_track = ref_track.copy()

    # convert obTime columns to timestamps if not already
    ref_obs["obTime"] = pd.to_datetime(ref_obs["obTime"])

    # --------------------------------------------------------------------
    # Generate decorrelated obs dataset
    # --------------------------------------------------------------------
    obs_data = ref_obs.copy()
    obs_data["uct"] = True  # Mark these as UCT/"unknown" points

    # Remove metadata columns that might identify data (silently ignore if any are missing)
    obs_data = obs_data.drop(
        columns=[
            "satNo",
            "idOnOrbit",
            "origObjectId",
            "rawFileURI",
            "createdAt",
            "trackId",
            "has_cov",
        ],
        errors="ignore",
    )

    # Create artificial track bins
    binned, _ = binTracks(ref_obs, ref_sv)
    id_to_track = {}

    for track_idx, (_, _, df) in enumerate(binned):
        # Get all ids from this dataframe
        ids_in_track = df["id"].values
        # Map each id to the current track index
        id_to_track.update({id_: track_idx for id_ in ids_in_track})

    obs_data["trackId"] = obs_data["id"].map(id_to_track)
    obs_data["origObjectId"] = obs_data["id"].map(id_to_track)

    # Shuffle the dataset for good measure
    obs_data = obs_data.sample(frac=1).reset_index(drop=True)

    # Serialize decorrelated obs dataset
    obs_data["obTime"] = obs_data["obTime"].astype(str)
    obs_data_json = obs_data.to_dict(orient="records")

    # --------------------------------------------------------------------
    # Generate decorrelated track dataset
    # --------------------------------------------------------------------
    track_data = ref_track.copy()
    track_data["uct"] = True  # Mark these as UCT/"unknown" points

    # Remove metadata columns that might identify data (silently ignore if any are missing)
    track_data = obs_data.drop(
        columns=[
            "satNo",
            "idOnOrbit",
            "origObjectId",
            "rawFileURI",
            "createdAt",
            "trackId",
            "has_cov",
            "epochNormalized",
        ],
        errors="ignore",
    )

    # Shuffle the dataset for good measure
    track_data = track_data.sample(frac=1).reset_index(drop=True)

    # Serialize decorrelated track dataset
    track_data_json = track_data.to_dict(orient="records")

    # --------------------------------------------------------------------
    # Serialize ref obs
    # --------------------------------------------------------------------
    ref_obs["obTime"] = ref_obs["obTime"].astype(str)

    # --------------------------------------------------------------------
    # Set up and serialize orbital data
    # --------------------------------------------------------------------
    cols_sv = [
        "satNo",
        "xpos",
        "ypos",
        "zpos",
        "xvel",
        "yvel",
        "zvel",
        "epoch",
        "cov",
        "mass",
        "crossSection",
        "dragCoeff",
        "solarRadPressCoeff",
    ]
    cols_elset = ["satNo", "line1", "line2"]

    orbit_data = pd.merge(ref_sv[cols_sv], ref_elset[cols_elset], on="satNo")

    obs_ids = ref_obs.groupby("satNo")["id"].agg(list).to_dict()
    elset_ids = ref_track.groupby("satNo")["id"].agg(list).to_dict()
    orbit_data["groupedObsIds"] = orbit_data["satNo"].map(obs_ids)
    orbit_data["groupedElsetIds"] = orbit_data["satNo"].map(elset_ids)

    orbit_data["cov"] = [json.dumps(arr) for arr in orbit_data["cov"].values]

    # orbit_data = safe_serialize_cov_column(orbit_data)

    orbit_data["epoch"] = orbit_data["epoch"].astype(str)

    orbit_data_json = orbit_data.to_dict(orient="records")

    # --------------------------------------------------------------------
    # Create and save output
    # --------------------------------------------------------------------
    output_json = {
        "dataset_obs": obs_data_json,
        "dataset_elset": track_data_json,
        "reference": orbit_data_json,
    }

    obs_data.to_parquet(INTERIM_DATA_DIR / "output_dataset_obs.parquet", index=False)
    track_data.to_parquet(INTERIM_DATA_DIR / "output_dataset_elset.parquet", index=False)
    orbit_data.to_parquet(INTERIM_DATA_DIR / "output_dataset_reference.parquet", index=False)

    output_dataset_path = INTERIM_DATA_DIR / "output_dataset.json"
    with open(str(output_dataset_path), "w") as f:
        json.dump(
            output_json,
            f,
            indent=2,
            default=lambda o: o.isoformat() if isinstance(o, pd.Timestamp) else str(o),
        )

    return output_json


def loadDataset(input_path):
    """
    Loads dataset JSON into its original DataFrame components.

    Args:
        input_path (string): Path to JSON file.

    Returns:
        ref_obs (Pandas DataFrame): Dataframe of "truth" observations.
        obs_data (Pandas DataFrame): Dataframe of decorrelated observations.
        ref_track (Pandas DataFrame): Dataframe of "truth" track TLEs.
        track_data (Pandas DataFrame): Dataframe of decorrelated track TLEs.
        ref_sv (Pandas DataFrame): Dataframe of satellite state vector data.
        ref_elset (Pandas DataFrame): Dataframe of satellite TLE data.
    """
    with open(input_path, "r") as f:
        data = json.load(f)

    # Reconstruct obs_data
    obs_data = pd.DataFrame(data["dataset_obs"])
    obs_data["obTime"] = pd.to_datetime(obs_data["obTime"])

    # Reconstruct track_data
    track_data = pd.DataFrame(data["dataset_elset"])

    # Reconstruct ref_obs from 'reference' field
    reference = pd.DataFrame(data["reference"])

    # Reconstruct ref_obs and ref_tracks by correlating groupedObsIds and groupedElsetIds
    obs_id_to_satno = {}
    elset_id_to_satno = {}
    for entry in data["reference"]:
        sat_no = entry["satNo"]
        for obs_id in entry["groupedObsIds"]:
            obs_id_to_satno[obs_id] = sat_no
        for elset_id in entry["groupedElsetIds"]:
            elset_id_to_satno[elset_id] = sat_no

    ref_obs = obs_data[obs_data["id"].isin(obs_id_to_satno)].copy()
    ref_obs["satNo"] = ref_obs["id"].map(obs_id_to_satno)

    ref_track = track_data[track_data["id"].isin(elset_id_to_satno)].copy()
    ref_track["satNo"] = ref_track["id"].map(elset_id_to_satno)

    # Reconstruct ref_sv
    ref_sv = reference[
        [
            "satNo",
            "xpos",
            "ypos",
            "zpos",
            "xvel",
            "yvel",
            "zvel",
            "epoch",
            "cov_matrix",
            "mass",
            "crossSection",
            "dragCoeff",
            "solarRadPressCoeff",
        ]
    ].copy()
    ref_sv["epoch"] = pd.to_datetime(ref_sv["epoch"])
    ref_sv["cov_matrix"] = ref_sv["cov_matrix"].apply(lambda x: np.array(json.loads(x)))

    # Reconstruct ref_elset
    ref_elset = reference[["satNo", "line1", "line2"]].copy()

    return ref_obs, obs_data, ref_track, track_data, ref_sv, ref_elset
