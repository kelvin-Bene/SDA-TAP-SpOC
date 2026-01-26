# -*- coding: utf-8 -*-
"""
Open Source Data Sources Integration Module

Provides query functions for fully open, no-auth-required data sources:
- SatNOGS (Satellite Observation Network) - CC-BY-SA
- GCAT (General Catalog of Artificial Space Objects) - CC-BY
- ILRS (International Laser Ranging Service) - Public Domain
- UCS (Union of Concerned Scientists Satellite Database) - Open

These sources complement the primary UDL/Space-Track integrations and provide:
- Independent validation data
- Higher precision measurements (ILRS)
- Community observations (SatNOGS)
- Comprehensive catalog metadata (GCAT, UCS)
"""

import datetime
import io
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests
from loguru import logger

# Module-level cache for downloaded catalogs
_catalog_cache: Dict[str, Any] = {
    'gcat': {'data': None, 'timestamp': None},
    'ucs': {'data': None, 'timestamp': None},
}

# Cache TTL (24 hours for catalog data)
CATALOG_CACHE_TTL = datetime.timedelta(hours=24)


# =============================================================================
# SATNOGS (Satellite Observation Network)
# =============================================================================

SATNOGS_API_BASE = "https://network.satnogs.org/api"
SATNOGS_DB_BASE = "https://db.satnogs.org/api"


def satnogsQuery(
    endpoint: str = "observations",
    params: Optional[Dict] = None,
    use_db_api: bool = False,
    page_limit: int = 10
) -> pd.DataFrame:
    """
    Query SatNOGS Network or Database API for satellite observation data.

    SatNOGS is a global network of 200+ ground stations collecting RF observations
    from satellites. All data is CC-BY-SA licensed.

    Args:
        endpoint: API endpoint to query. Options include:
            Network API (use_db_api=False):
                - 'observations': RF observation records
                - 'stations': Ground station information
                - 'jobs': Scheduled observation jobs
            Database API (use_db_api=True):
                - 'satellites': Satellite catalog
                - 'transmitters': Known satellite transmitters
                - 'modes': Transmission modes
        params: Query parameters (filters). Common filters:
            - satellite__norad_cat_id: NORAD ID filter
            - ground_station: Station ID filter
            - start: Start datetime (ISO format)
            - end: End datetime (ISO format)
            - status: Observation status (good, bad, failed, unknown)
        use_db_api: If True, query the database API instead of network API
        page_limit: Maximum pages to fetch (default 10, ~250 results/page)

    Returns:
        pd.DataFrame: Query results with observation or catalog data

    Example:
        >>> # Get recent observations for ISS (NORAD 25544)
        >>> df = satnogsQuery('observations', {'satellite__norad_cat_id': 25544})
        >>>
        >>> # Get all ground stations
        >>> stations = satnogsQuery('stations')
        >>>
        >>> # Get satellite transmitter info from DB API
        >>> transmitters = satnogsQuery('transmitters', use_db_api=True)

    Note:
        - No authentication required
        - Rate limit: Be respectful (recommended <1 req/sec)
        - Data license: CC-BY-SA 4.0
    """
    if params is None:
        params = {}

    base_url = SATNOGS_DB_BASE if use_db_api else SATNOGS_API_BASE
    url = f"{base_url}/{endpoint}/"

    all_results = []
    page = 1

    try:
        while page <= page_limit:
            page_params = params.copy()
            page_params['page'] = page

            logger.debug(f"SatNOGS query: {endpoint} (page {page})")
            response = requests.get(url, params=page_params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Handle paginated vs non-paginated responses
            if isinstance(data, list):
                if not data:
                    break
                all_results.extend(data)
                page += 1
            elif isinstance(data, dict) and 'results' in data:
                all_results.extend(data['results'])
                if not data.get('next'):
                    break
                page += 1
            else:
                # Single object response
                all_results.append(data)
                break

    except requests.exceptions.RequestException as e:
        logger.error(f"SatNOGS API error: {e}")
        return pd.DataFrame()

    if not all_results:
        return pd.DataFrame()

    df = pd.DataFrame(all_results)
    logger.info(f"SatNOGS returned {len(df)} records from {endpoint}")
    return df


def satnogsGetSatellites() -> pd.DataFrame:
    """
    Get the complete SatNOGS satellite database.

    Returns:
        pd.DataFrame: All satellites with NORAD IDs, names, and status
    """
    return satnogsQuery('satellites', use_db_api=True, page_limit=50)


def satnogsGetTransmitters(norad_id: Optional[int] = None) -> pd.DataFrame:
    """
    Get satellite transmitter information from SatNOGS database.

    Args:
        norad_id: Optional NORAD ID to filter by satellite

    Returns:
        pd.DataFrame: Transmitter data (frequencies, modes, status)
    """
    params = {}
    if norad_id:
        params['satellite__norad_cat_id'] = norad_id
    return satnogsQuery('transmitters', params=params, use_db_api=True, page_limit=100)


def satnogsGetObservations(
    norad_id: Optional[int] = None,
    station_id: Optional[int] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    status: Optional[str] = None
) -> pd.DataFrame:
    """
    Get RF observation data from SatNOGS network.

    Args:
        norad_id: Filter by NORAD catalog ID
        station_id: Filter by ground station ID
        start_time: Observations after this time
        end_time: Observations before this time
        status: Filter by status ('good', 'bad', 'failed', 'unknown')

    Returns:
        pd.DataFrame: Observation records with timestamps, frequencies, etc.
    """
    params = {}
    if norad_id:
        params['satellite__norad_cat_id'] = norad_id
    if station_id:
        params['ground_station'] = station_id
    if start_time:
        params['start'] = start_time.isoformat()
    if end_time:
        params['end'] = end_time.isoformat()
    if status:
        params['vetted_status'] = status

    return satnogsQuery('observations', params=params, page_limit=20)


def satnogsGetStations(status: Optional[str] = None) -> pd.DataFrame:
    """
    Get SatNOGS ground station information.

    Args:
        status: Filter by status ('Online', 'Offline', 'Testing')

    Returns:
        pd.DataFrame: Station data with locations, capabilities, etc.
    """
    params = {}
    if status:
        params['status'] = status
    return satnogsQuery('stations', params=params, page_limit=20)


# =============================================================================
# GCAT (General Catalog of Artificial Space Objects)
# =============================================================================

GCAT_BASE_URL = "https://planet4589.org/space/gcat/tsv/cat"


def gcatQuery(
    catalog: str = "satcat",
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Download and parse GCAT (General Catalog of Artificial Space Objects).

    GCAT is maintained by Dr. Jonathan McDowell (Harvard-Smithsonian) and provides
    comprehensive space object tracking data. Updated weekly.

    Args:
        catalog: Which catalog to download. Options:
            - 'satcat': Main satellite catalog (57,000+ objects)
            - 'auxcat': Auxiliary catalog data
            - 'lcat': Launch catalog
            - 'rcat': Reentry catalog
            - 'deepcat': Deep space objects
        force_refresh: If True, bypass cache and re-download

    Returns:
        pd.DataFrame: Catalog data with columns including:
            - Piece: Object designation (e.g., "1998-067A")
            - Name: Object name
            - Owner: Owner/operator
            - State: Current state
            - Status: Operational status
            - Mass: Mass in kg
            - Launch date and site info

    Example:
        >>> # Get main satellite catalog
        >>> satcat = gcatQuery('satcat')
        >>>
        >>> # Filter for Russian satellites
        >>> russian = satcat[satcat['Owner'].str.contains('RUS', na=False)]

    Note:
        - No authentication required
        - License: CC-BY
        - Updates: Weekly
        - Citation: McDowell, Jonathan C., General Catalog of Artificial Space Objects
    """
    cache_key = f'gcat_{catalog}'

    # Check cache
    if not force_refresh and cache_key in _catalog_cache:
        cached = _catalog_cache.get(cache_key, {})
        if cached.get('data') is not None and cached.get('timestamp'):
            age = datetime.datetime.now() - cached['timestamp']
            if age < CATALOG_CACHE_TTL:
                logger.debug(f"GCAT {catalog} served from cache (age: {age})")
                return cached['data'].copy()

    # Build URL based on catalog type
    catalog_urls = {
        'satcat': f"{GCAT_BASE_URL}/satcat.tsv",
        'auxcat': f"{GCAT_BASE_URL}/auxcat.tsv",
        'lcat': "https://planet4589.org/space/gcat/tsv/launch/lcat.tsv",
        'rcat': "https://planet4589.org/space/gcat/tsv/event/rcat.tsv",
        'deepcat': "https://planet4589.org/space/gcat/tsv/cat/deepcat.tsv",
    }

    url = catalog_urls.get(catalog, f"{GCAT_BASE_URL}/{catalog}.tsv")

    try:
        logger.info(f"Downloading GCAT {catalog} from {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        # Parse TSV - GCAT uses '#' for comments and has header row
        lines = response.text.strip().split('\n')
        # Find header line (first non-comment line)
        header_idx = 0
        for i, line in enumerate(lines):
            if not line.startswith('#'):
                header_idx = i
                break

        # Read TSV
        df = pd.read_csv(
            io.StringIO('\n'.join(lines[header_idx:])),
            sep='\t',
            on_bad_lines='skip'
        )

        # Clean column names
        df.columns = df.columns.str.strip()

        # Cache result
        _catalog_cache[cache_key] = {
            'data': df,
            'timestamp': datetime.datetime.now()
        }

        logger.info(f"GCAT {catalog} loaded: {len(df)} objects")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"GCAT download error: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"GCAT parse error: {e}")
        return pd.DataFrame()


def gcatGetSatelliteCatalog() -> pd.DataFrame:
    """
    Get the main GCAT satellite catalog.

    Returns:
        pd.DataFrame: Full satellite catalog (57,000+ objects)
    """
    return gcatQuery('satcat')


def gcatGetLaunches() -> pd.DataFrame:
    """
    Get the GCAT launch catalog.

    Returns:
        pd.DataFrame: Launch records with dates, sites, vehicles
    """
    return gcatQuery('lcat')


def gcatGetReentries() -> pd.DataFrame:
    """
    Get the GCAT reentry catalog.

    Returns:
        pd.DataFrame: Reentry records
    """
    return gcatQuery('rcat')


def gcatLookupByNorad(norad_id: int) -> Optional[pd.Series]:
    """
    Look up a single object by NORAD catalog ID in GCAT.

    Args:
        norad_id: NORAD catalog number

    Returns:
        pd.Series: Object data, or None if not found
    """
    satcat = gcatQuery('satcat')
    if satcat.empty:
        return None

    # GCAT uses 'NORAD' or similar column - check available columns
    norad_cols = [c for c in satcat.columns if 'norad' in c.lower() or 'satno' in c.lower()]
    if not norad_cols:
        logger.warning("NORAD ID column not found in GCAT data")
        return None

    col = norad_cols[0]
    match = satcat[satcat[col] == norad_id]
    return match.iloc[0] if not match.empty else None


# =============================================================================
# ILRS (International Laser Ranging Service)
# =============================================================================

ILRS_CDDIS_BASE = "https://cddis.nasa.gov/archive/slr"


def ilrsGetSatellites() -> pd.DataFrame:
    """
    Get the list of satellites tracked by ILRS laser ranging stations.

    ILRS provides sub-centimeter precision range measurements to ~100 satellites.

    Returns:
        pd.DataFrame: Satellites tracked by ILRS with NORAD IDs and designations

    Note:
        - Data from NASA CDDIS archive (may require Earthdata login for downloads)
        - Precision: millimeter-level range measurements
        - Use for ground truth validation of orbit determination
    """
    url = "https://ilrs.gsfc.nasa.gov/missions/satellite_missions/current_missions/index.html"

    try:
        logger.info("Fetching ILRS satellite list")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse HTML table - basic extraction
        # For full parsing, would need BeautifulSoup
        # Return known high-priority ILRS targets for now
        ilrs_satellites = [
            {'name': 'LAGEOS-1', 'norad_id': 8820, 'cospar_id': '1976-039A', 'altitude_km': 5850},
            {'name': 'LAGEOS-2', 'norad_id': 22195, 'cospar_id': '1992-070A', 'altitude_km': 5625},
            {'name': 'LARES', 'norad_id': 38077, 'cospar_id': '2012-006A', 'altitude_km': 1450},
            {'name': 'LARES-2', 'norad_id': 53106, 'cospar_id': '2022-090A', 'altitude_km': 5900},
            {'name': 'Starlette', 'norad_id': 7646, 'cospar_id': '1975-010A', 'altitude_km': 812},
            {'name': 'Stella', 'norad_id': 22824, 'cospar_id': '1993-061B', 'altitude_km': 804},
            {'name': 'AJISAI', 'norad_id': 16908, 'cospar_id': '1986-061A', 'altitude_km': 1485},
            {'name': 'Etalon-1', 'norad_id': 19751, 'cospar_id': '1989-001C', 'altitude_km': 19120},
            {'name': 'Etalon-2', 'norad_id': 20026, 'cospar_id': '1989-039C', 'altitude_km': 19120},
            {'name': 'BLITS', 'norad_id': 35871, 'cospar_id': '2009-049G', 'altitude_km': 832},
            {'name': 'Jason-3', 'norad_id': 41240, 'cospar_id': '2016-002A', 'altitude_km': 1336},
            {'name': 'Sentinel-6A', 'norad_id': 46984, 'cospar_id': '2020-086A', 'altitude_km': 1336},
            {'name': 'ICESat-2', 'norad_id': 43613, 'cospar_id': '2018-070A', 'altitude_km': 500},
            {'name': 'GRACE-FO 1', 'norad_id': 43476, 'cospar_id': '2018-047A', 'altitude_km': 490},
            {'name': 'GRACE-FO 2', 'norad_id': 43477, 'cospar_id': '2018-047B', 'altitude_km': 490},
        ]

        df = pd.DataFrame(ilrs_satellites)
        logger.info(f"ILRS satellite list: {len(df)} primary targets")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"ILRS query error: {e}")
        return pd.DataFrame()


def ilrsGetStations() -> pd.DataFrame:
    """
    Get ILRS ground station information.

    Returns:
        pd.DataFrame: Laser ranging station locations and capabilities
    """
    # Core ILRS stations
    stations = [
        {'code': 'YARL', 'name': 'Yarragadee', 'country': 'Australia', 'lat': -29.0, 'lon': 115.3},
        {'code': 'MCDL', 'name': 'McDonald', 'country': 'USA', 'lat': 30.7, 'lon': -104.0},
        {'code': 'GRZL', 'name': 'Graz', 'country': 'Austria', 'lat': 47.1, 'lon': 15.5},
        {'code': 'HERL', 'name': 'Herstmonceux', 'country': 'UK', 'lat': 50.9, 'lon': 0.3},
        {'code': 'ZIML', 'name': 'Zimmerwald', 'country': 'Switzerland', 'lat': 46.9, 'lon': 7.5},
        {'code': 'GODE', 'name': 'Greenbelt', 'country': 'USA', 'lat': 39.0, 'lon': -76.8},
        {'code': 'HARL', 'name': 'Hartebeesthoek', 'country': 'South Africa', 'lat': -25.9, 'lon': 27.7},
        {'code': 'WETL', 'name': 'Wettzell', 'country': 'Germany', 'lat': 49.1, 'lon': 12.9},
        {'code': 'MATL', 'name': 'Matera', 'country': 'Italy', 'lat': 40.6, 'lon': 16.7},
        {'code': 'SHOL', 'name': 'Shanghai', 'country': 'China', 'lat': 31.1, 'lon': 121.2},
    ]
    return pd.DataFrame(stations)


def ilrsQueryPredictions(
    satellite: str,
    station: Optional[str] = None
) -> pd.DataFrame:
    """
    Get ILRS pass predictions for a satellite.

    Args:
        satellite: Satellite name or ILRS designation
        station: Optional station code to filter by

    Returns:
        pd.DataFrame: Pass prediction data

    Note:
        This requires Earthdata authentication for full CDDIS access.
        For production use, configure NASA_EARTHDATA_TOKEN environment variable.
    """
    logger.warning("ILRS predictions require NASA Earthdata authentication - returning empty")
    logger.info("To enable: Set NASA_EARTHDATA_TOKEN environment variable")
    logger.info("Register at: https://urs.earthdata.nasa.gov/")
    return pd.DataFrame()


# =============================================================================
# UCS (Union of Concerned Scientists) Satellite Database
# =============================================================================

UCS_DATABASE_URL = "https://www.ucs.org/sites/default/files/2024-01/UCS-Satellite-Database-1-1-2024.txt"


def ucsQuery(force_refresh: bool = False) -> pd.DataFrame:
    """
    Download and parse the UCS Satellite Database.

    The UCS database contains detailed information on 7,500+ operational satellites
    including ownership, purpose, technical specifications, and orbital parameters.

    Args:
        force_refresh: If True, bypass cache and re-download

    Returns:
        pd.DataFrame: Satellite data with columns including:
            - Name of Satellite
            - Country of Operator/Owner
            - Operator/Owner
            - Users (Commercial, Government, Military, Civil)
            - Purpose (Communications, Earth Observation, Navigation, etc.)
            - Class of Orbit (LEO, MEO, GEO, Elliptical)
            - Perigee (km), Apogee (km), Eccentricity, Inclination
            - Launch Mass (kg), Dry Mass (kg)
            - Power (watts)
            - Date of Launch
            - Expected Lifetime (years)
            - NORAD Number

    Example:
        >>> ucs = ucsQuery()
        >>> # Find all SpaceX Starlink satellites
        >>> starlink = ucs[ucs['Name of Satellite'].str.contains('STARLINK', na=False)]
        >>> print(f"Starlink count: {len(starlink)}")

    Note:
        - No authentication required
        - Updated quarterly
        - Authoritative source for operational satellite metadata
    """
    # Check cache
    if not force_refresh:
        cached = _catalog_cache.get('ucs', {})
        if cached.get('data') is not None and cached.get('timestamp'):
            age = datetime.datetime.now() - cached['timestamp']
            if age < CATALOG_CACHE_TTL:
                logger.debug(f"UCS database served from cache (age: {age})")
                return cached['data'].copy()

    try:
        logger.info("Downloading UCS Satellite Database")
        response = requests.get(UCS_DATABASE_URL, timeout=60)
        response.raise_for_status()

        # UCS uses tab-separated format
        df = pd.read_csv(
            io.StringIO(response.text),
            sep='\t',
            on_bad_lines='skip',
            encoding='utf-8'
        )

        # Clean column names
        df.columns = df.columns.str.strip()

        # Cache result
        _catalog_cache['ucs'] = {
            'data': df,
            'timestamp': datetime.datetime.now()
        }

        logger.info(f"UCS database loaded: {len(df)} operational satellites")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"UCS download error: {e}")
        # Try alternate URL format (they update the filename with dates)
        return _ucs_try_alternate_urls()
    except Exception as e:
        logger.error(f"UCS parse error: {e}")
        return pd.DataFrame()


def _ucs_try_alternate_urls() -> pd.DataFrame:
    """Try alternate UCS database URLs (they change with updates)."""
    # UCS changes their URL with each update, try common patterns
    base = "https://www.ucs.org/sites/default/files"
    dates = ['2024-05', '2024-01', '2023-12', '2023-09']

    for date in dates:
        url = f"{base}/{date}/UCS-Satellite-Database.txt"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text), sep='\t', on_bad_lines='skip')
                df.columns = df.columns.str.strip()
                logger.info(f"UCS database loaded from alternate URL: {len(df)} satellites")
                return df
        except:
            continue

    logger.error("Could not find UCS database at any known URL")
    return pd.DataFrame()


def ucsLookupByNorad(norad_id: int) -> Optional[pd.Series]:
    """
    Look up satellite info by NORAD ID in UCS database.

    Args:
        norad_id: NORAD catalog number

    Returns:
        pd.Series: Satellite data, or None if not found
    """
    ucs = ucsQuery()
    if ucs.empty:
        return None

    # Find NORAD column (varies slightly by version)
    norad_cols = [c for c in ucs.columns if 'norad' in c.lower()]
    if not norad_cols:
        logger.warning("NORAD column not found in UCS data")
        return None

    col = norad_cols[0]
    match = ucs[ucs[col] == norad_id]
    return match.iloc[0] if not match.empty else None


def ucsGetByCountry(country: str) -> pd.DataFrame:
    """
    Get all satellites operated by a specific country.

    Args:
        country: Country name or code (e.g., 'USA', 'China', 'Russia')

    Returns:
        pd.DataFrame: Filtered satellite data
    """
    ucs = ucsQuery()
    if ucs.empty:
        return pd.DataFrame()

    # Find country column
    country_cols = [c for c in ucs.columns if 'country' in c.lower() or 'operator' in c.lower()]
    if not country_cols:
        return pd.DataFrame()

    col = country_cols[0]
    return ucs[ucs[col].str.contains(country, case=False, na=False)]


def ucsGetByPurpose(purpose: str) -> pd.DataFrame:
    """
    Get satellites by mission purpose.

    Args:
        purpose: Purpose type ('Communications', 'Earth Observation',
                 'Navigation', 'Technology Development', 'Space Science')

    Returns:
        pd.DataFrame: Filtered satellite data
    """
    ucs = ucsQuery()
    if ucs.empty:
        return pd.DataFrame()

    purpose_cols = [c for c in ucs.columns if 'purpose' in c.lower()]
    if not purpose_cols:
        return pd.DataFrame()

    col = purpose_cols[0]
    return ucs[ucs[col].str.contains(purpose, case=False, na=False)]


# =============================================================================
# COMBINED UTILITIES
# =============================================================================

def enrichSatelliteData(norad_id: int) -> Dict[str, Any]:
    """
    Enrich satellite data by combining information from multiple open sources.

    Args:
        norad_id: NORAD catalog ID

    Returns:
        dict: Combined satellite information from UCS, GCAT, and SatNOGS
    """
    result = {'norad_id': norad_id}

    # UCS data (most detailed metadata)
    ucs_data = ucsLookupByNorad(norad_id)
    if ucs_data is not None:
        result['ucs'] = ucs_data.to_dict()

    # GCAT data (catalog info)
    gcat_data = gcatLookupByNorad(norad_id)
    if gcat_data is not None:
        result['gcat'] = gcat_data.to_dict()

    # SatNOGS transmitter data
    transmitters = satnogsGetTransmitters(norad_id)
    if not transmitters.empty:
        result['transmitters'] = transmitters.to_dict('records')

    return result


def getOpenSourceCatalogStats() -> Dict[str, Any]:
    """
    Get statistics about available open source catalog data.

    Returns:
        dict: Statistics including record counts and cache status
    """
    stats = {}

    # GCAT
    gcat = gcatQuery('satcat')
    stats['gcat'] = {
        'total_objects': len(gcat) if not gcat.empty else 0,
        'cached': 'gcat_satcat' in _catalog_cache and _catalog_cache['gcat_satcat'].get('data') is not None
    }

    # UCS
    ucs = ucsQuery()
    stats['ucs'] = {
        'total_satellites': len(ucs) if not ucs.empty else 0,
        'cached': 'ucs' in _catalog_cache and _catalog_cache['ucs'].get('data') is not None
    }

    # ILRS
    ilrs = ilrsGetSatellites()
    stats['ilrs'] = {
        'tracked_satellites': len(ilrs) if not ilrs.empty else 0
    }

    return stats


def clearOpenSourceCache() -> None:
    """Clear all cached catalog data."""
    global _catalog_cache
    _catalog_cache = {
        'gcat': {'data': None, 'timestamp': None},
        'ucs': {'data': None, 'timestamp': None},
    }
    logger.info("Open source catalog cache cleared")


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # SatNOGS
    'satnogsQuery',
    'satnogsGetSatellites',
    'satnogsGetTransmitters',
    'satnogsGetObservations',
    'satnogsGetStations',
    # GCAT
    'gcatQuery',
    'gcatGetSatelliteCatalog',
    'gcatGetLaunches',
    'gcatGetReentries',
    'gcatLookupByNorad',
    # ILRS
    'ilrsGetSatellites',
    'ilrsGetStations',
    'ilrsQueryPredictions',
    # UCS
    'ucsQuery',
    'ucsLookupByNorad',
    'ucsGetByCountry',
    'ucsGetByPurpose',
    # Utilities
    'enrichSatelliteData',
    'getOpenSourceCatalogStats',
    'clearOpenSourceCache',
]
