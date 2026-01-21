# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 2025

@author: Louis Caves

Enhanced with physics-based simulation models for atmospheric refraction,
velocity aberration, sensor-specific noise, and photometric simulation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import uct_benchmark.config as config
from uct_benchmark.config import (
    SimulationConfig,
    SENSOR_NOISE_MODELS,
    simulation_config,
)

# Import physics modules
try:
    from uct_benchmark.simulation.atmospheric import (
        apply_atmospheric_refraction,
        compute_velocity_aberration,
        compute_observer_velocity,
        apply_atmospheric_effects,
    )
    from uct_benchmark.simulation.noise_models import (
        get_sensor_noise_model,
        apply_realistic_noise,
        simulate_magnitude,
        get_sun_position_approx,
        is_satellite_illuminated,
    )
    PHYSICS_MODULES_AVAILABLE = True
except ImportError:
    PHYSICS_MODULES_AVAILABLE = False


# =============================================================================
# ENHANCED SIMULATION FUNCTIONS
# =============================================================================

def simulateObsEnhanced(
    input1,
    input2,
    timespan,
    sensorsDataFrame,
    sim_config: SimulationConfig = None,
    positionNoise: float = None,
    angularNoise: float = None,
    step: float = 10.0,
    satelliteParameters: List = None,
    rng: np.random.Generator = None,
) -> pd.DataFrame:
    """
    Enhanced observation simulation with physics-based models.

    Includes:
    - Atmospheric refraction correction
    - Velocity aberration
    - Sensor-specific noise models
    - Photometric (magnitude) simulation

    Parameters:
        input1: State vector (6x1 np.array) OR TLE line 1 (string)
        input2: Epoch of state vector (datetime) OR TLE line 2 (string)
        timespan: Duration in seconds OR list of epochs
        sensorsDataFrame: DataFrame with sensor info
        sim_config: SimulationConfig for physics settings
        positionNoise: Override position noise (km)
        angularNoise: Override angular noise (arcsec)
        step: Sampling interval in seconds
        satelliteParameters: [satNo, mass, cross_section] for SV input
        rng: Random number generator

    Returns:
        DataFrame in UDL EOobs schema with enhanced fields
    """
    # Use default config if not provided
    if sim_config is None:
        sim_config = simulation_config

    # Override noise if specified
    if positionNoise is None:
        positionNoise = config.positionNoise
    if angularNoise is None:
        # Use sensor-specific noise if available
        sensor_model = SENSOR_NOISE_MODELS.get(sim_config.sensor_model, {})
        angularNoise = sensor_model.get('angular_noise_arcsec', config.angularNoise)

    if satelliteParameters is None:
        satelliteParameters = [99999, 0, 0]

    if rng is None:
        rng = np.random.default_rng(sim_config.seed)

    # Call base simulation
    base_df = simulateObs(
        input1,
        input2,
        timespan,
        sensorsDataFrame,
        positionNoise=positionNoise,
        angularNoise=angularNoise,
        step=step,
        satelliteParameters=satelliteParameters,
    )

    if base_df.empty or not PHYSICS_MODULES_AVAILABLE:
        return base_df

    # Apply enhanced physics if available
    enhanced_df = base_df.copy()

    # Apply atmospheric refraction
    if sim_config.apply_atmospheric_refraction:
        enhanced_df = _apply_refraction_to_df(enhanced_df)

    # Apply velocity aberration (simplified for now)
    if sim_config.apply_velocity_aberration:
        enhanced_df = _apply_aberration_to_df(enhanced_df, input1, input2)

    # Apply sensor-specific noise
    if sim_config.apply_sensor_noise:
        enhanced_df = _apply_sensor_noise_to_df(
            enhanced_df, sim_config.sensor_model, rng
        )

    # Simulate magnitude
    if sim_config.simulate_magnitude:
        enhanced_df = _simulate_magnitude_for_df(
            enhanced_df, input1, input2, sim_config.default_albedo
        )

    return enhanced_df


def _apply_refraction_to_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply atmospheric refraction correction to all observations."""
    if 'elevation' not in df.columns:
        return df

    df = df.copy()
    refracted_el = []

    for _, row in df.iterrows():
        el = row.get('elevation', 90.0)
        if pd.notna(el) and el > 0:
            corrected = apply_atmospheric_refraction(el)
            refracted_el.append(corrected if corrected is not None else el)
        else:
            refracted_el.append(el)

    df['elevation'] = refracted_el
    df['refractionApplied'] = True
    return df


def _apply_aberration_to_df(
    df: pd.DataFrame,
    input1,
    input2
) -> pd.DataFrame:
    """Apply velocity aberration correction to all observations."""
    if 'ra' not in df.columns or 'declination' not in df.columns:
        return df

    df = df.copy()

    # For each observation, apply aberration
    corrected_ra = []
    corrected_dec = []

    for _, row in df.iterrows():
        ra = row.get('ra', 0)
        dec = row.get('declination', 0)

        # Get observer position for velocity calculation
        obs_lat = row.get('senlat', 0)
        obs_lon = row.get('senlon', 0)
        obs_alt = row.get('senalt', 0)

        try:
            obs_velocity = compute_observer_velocity(
                obs_lat, obs_lon, obs_alt, None
            )
            ra_corr, dec_corr = compute_velocity_aberration(
                ra, dec, obs_velocity, None
            )
            corrected_ra.append(ra_corr)
            corrected_dec.append(dec_corr)
        except Exception:
            corrected_ra.append(ra)
            corrected_dec.append(dec)

    df['ra'] = corrected_ra
    df['declination'] = corrected_dec
    df['aberrationApplied'] = True
    return df


def _apply_sensor_noise_to_df(
    df: pd.DataFrame,
    sensor_model: str,
    rng: np.random.Generator
) -> pd.DataFrame:
    """Apply sensor-specific noise to all observations."""
    if 'ra' not in df.columns:
        return df

    df = df.copy()
    noisy_ra = []
    noisy_dec = []
    timing_offsets = []

    for _, row in df.iterrows():
        ra = row.get('ra', 0)
        dec = row.get('declination', 0)

        ra_n, dec_n, t_off = apply_realistic_noise(
            ra, dec, None, sensor_model, None, rng
        )
        noisy_ra.append(ra_n)
        noisy_dec.append(dec_n)
        timing_offsets.append(t_off)

    df['ra'] = noisy_ra
    df['declination'] = noisy_dec
    df['sensorNoiseApplied'] = True
    return df


def _simulate_magnitude_for_df(
    df: pd.DataFrame,
    input1,
    input2,
    albedo: float
) -> pd.DataFrame:
    """Simulate visual magnitude for all observations."""
    df = df.copy()

    # Get satellite cross-section (default 10 m^2)
    cross_section = 10.0

    # For simplicity, compute approximate magnitude
    # Full implementation would propagate satellite state
    magnitudes = []

    for _, row in df.iterrows():
        range_km = row.get('range', 1000)

        # Simplified magnitude calculation
        # Assuming illuminated, phase angle ~90 degrees
        # mag ~ -26.7 + 5*log10(range_km*1000) - 2.5*log10(albedo * cross_section)
        if range_km > 0:
            mag = -26.7 + 5 * np.log10(range_km * 1000) - 2.5 * np.log10(albedo * cross_section)
            # Apply atmospheric extinction
            el = row.get('elevation', 45)
            if el > 0:
                airmass = 1.0 / np.sin(np.radians(max(1.0, el)))
                mag += 0.2 * airmass
            magnitudes.append(mag)
        else:
            magnitudes.append(np.nan)

    df['mag'] = magnitudes
    return df


# Define Functions for simulating observations from TLE or state vector
def simulateObs(
    input1,
    input2,
    timespan,
    sensorsDataFrame,
    positionNoise=config.positionNoise,
    angularNoise=config.angularNoise,
    step=10.0,
    satelliteParameters=[99999, 0, 0],
):
    """
    Simulate RA/Dec observations from TLE using Orekit-generated ephemeris.

    Parameters:
    input1: state vector (6x1 np.array) OR TLE line 1 (string)
    input2: Epoch of state vector (datetime) OR TLE line 2 (string)
    timespan (float OR datetime list): Duration in seconds from to simulate obs for OR list of epochs to simulate observations at.
    sensorsDataFrame (pd.DataFrame): DataFrame containing sensor information with columns ['idSensor', 'senlat', 'senlon', 'senalt', 'sensorLikelihood'].
    positionNoise (float): Standard deviation of the position noise in meters (default is 0).
    angularNoise (float): Standard deviation of the angular noise in degrees (default is 1/3600 or 1 arcsecond).
    step (float): Sampling interval in seconds (default is 10s).
    satelliteParameters (list): List of satellite parameters [satNo, mass, cross-sectional area] (default is [99999, 0, 0]), only used for state vector input.

    Returns:
    pandas dataframe in UDL EOobs schema:
    """
    from datetime import timezone

    import numpy as np

    # Use ephemeris propagator functions that already exists
    if isinstance(input1, str):  # TLE input
        # Convert timespan (in seconds) to a list of datetime objects centered on epoch if necessary
        if isinstance(timespan, list):
            datetimeList = timespan
        else:
            # Must extract epoch from TLE and convert to datetime
            epoch = extractTLEepoch(input1)  # Extract epoch from TLE line 1
            datetimeList = epochTimespan2DatetimeList(epoch, timespan, step)
        # Generate list of propagated state vectors using ephmerisPropagator
        _, _, propagatedStates = TLEpropagator(
            input1, input2, datetimeList
        )  # state vectors are 3rd output of TLEpropagator
        satNo = int(input1[2:7])  # Extract satellite number from TLE line 1

    else:  # State vector input
        # Convert timespan (in seconds) to a list of datetime objects centered on epochif necessary
        if isinstance(timespan, list):
            datetimeList = timespan
        else:
            datetimeList = epochTimespan2DatetimeList(input2, timespan, step)
        # Generate list of propagated state vectors using ephmerisPropagator
        satNo = satelliteParameters[0]  # Extract satellite number from parameters
        satelliteParameters = satelliteParameters[1:] + [0, 0]
        propagatedStates = ephemerisPropagator(
            input1, input2, datetimeList, satelliteParameters=satelliteParameters
        )

    # Sample from both ephemerides
    results = []
    nSteps = len(propagatedStates)

    # Number of observations to simulate for each sensor
    groupSize = 3

    for i in range(nSteps):
        tstring = datetimeList[i].astimezone(timezone.utc).isoformat()
        x, y, z = propagatedStates[i][0:3]  # Extract position from propagated state vector
        x = float(x) + np.random.normal(0, positionNoise)
        y = float(y) + np.random.normal(0, positionNoise)
        z = float(z) + np.random.normal(0, positionNoise)
        r = np.linalg.norm([x, y, z])
        ra = (float(np.arctan2(y, x) % (2 * np.pi)) * 180.0 / np.pi) + np.random.normal(
            0, angularNoise
        )
        dec = (float(np.arcsin(z / r)) * 180.0 / np.pi) + np.random.normal(0, angularNoise)
        rangeVal = np.linalg.norm([x, y, z])  # Range in meters
        # Pick a random sensor to simulate observations for (but keep constant for debugging purposes)
        # Sample sensor every group_size observations
        if i % groupSize == 0:
            randomSensor = sensorsDataFrame.sample(weights="count", random_state=None).iloc[0]
            sensorPosition = randomSensor[["senlat", "senlon", "senalt"]].tolist()
            sensorID = randomSensor["idSensor"]
        az, el = radec2azel(
            ra, dec, rangeVal, sensorPosition, datetimeList[i]
        )  # Convert RA/Dec to azimuth/elevation
        triedSensors = set()
        while el < 6:  # If elevation is less than 6 degrees, try another sensor
            triedSensors.add(sensorID)
            availableSensors = sensorsDataFrame[
                ~sensorsDataFrame["idSensor"].isin(triedSensors)
            ]
            if availableSensors.empty:
                break
            randomSensor = availableSensors.sample(weights="count", random_state=None).iloc[0]
            sensorPosition = randomSensor[["senlat", "senlon", "senalt"]].tolist()
            sensorID = randomSensor["idSensor"]
            az, el = radec2azel(
                ra, dec, rangeVal, sensorPosition, datetimeList[i]
            )  # Convert RA/Dec to azimuth/elevation
        if el >= 6:  # Only save observation if there is a valid elevation angle
            results.append(
                (
                    tstring,
                    ra,
                    dec,
                    sensorID,
                    sensorPosition[0],
                    sensorPosition[1],
                    sensorPosition[2],
                    az,
                    el,
                    rangeVal,
                )
            )

    df = toObsSchema(results, satNo=satNo, noiseCharacteristics=angularNoise)

    return df


def extractTLEepoch(tle_line1):
    """
    Extract the epoch from a TLE line 1 string and convert it to a datetime object.
    Args:
        tle_line1 (str): The first line of a TLE string.
    Returns:
        epoch (datetime): The epoch as a datetime object.
    """
    from datetime import datetime, timedelta

    # Extract epoch year and day of year
    epoch_year = int(tle_line1[18:20])
    epoch_day = float(tle_line1[20:32])

    # Convert year to full year (assumes 2000–2099 range)
    full_year = 2000 + epoch_year if epoch_year < 57 else 1900 + epoch_year

    # Build datetime from year and day-of-year
    epoch_datetime = datetime(full_year, 1, 1) + timedelta(days=epoch_day - 1)
    return epoch_datetime


def datetime2AbsDate(datetime_obj, utc):
    """
    Convert a Python datetime object to an Orekit AbsoluteDate object.

    Args:
        datetime_obj (datetime): The datetime object to convert.

    Returns:
        AbsoluteDate: The corresponding Orekit AbsoluteDate object.
    """
    from org.orekit.time import AbsoluteDate

    # utc = TimeScalesFactory.getUTC()
    return AbsoluteDate(
        datetime_obj.year,
        datetime_obj.month,
        datetime_obj.day,
        datetime_obj.hour,
        datetime_obj.minute,
        datetime_obj.second
        + datetime_obj.microsecond / 1e6,  # convert microseconds to fractional seconds
        utc,
    )


def epochTimespan2DatetimeList(epoch, timespan, step=10):
    """
    Generate a list of datetime objects centered on the given epoch.

    Parameters:
    - epoch: datetime object representing the center time.
    - timespan: total span in seconds (symmetric around the epoch).
    - step: interval between datetime entries in seconds (default 10).

    Returns:
    - List of datetime objects.
    """
    from datetime import timedelta

    half_span = int(timespan // 2)
    return [epoch + timedelta(seconds=i) for i in range(-half_span, half_span + 1, int(step))]


def radec2azel(ra_deg, dec_deg, rangeVal, sensorPosition, obs_time):
    """
    Convert Right Ascension and Declination to Azimuth and Elevation.

    Parameters
    ----------
    ra (float):  Right Ascension in degrees (J2000).
    dec (float): Declination in degrees (J2000).
    range (float): Range to the object in kilometers
    sensorPosition (list): sensorLat (deg), sensorLon(deg), sensorAlt (km)
    obs_time (datetime): Observation time in UTC.

    Returns
    -------
    azimuth (float): Azimuth angle in degrees (0° = North, 90° = East).
    elevation (float): Elevation angle in degrees above the horizon.

    Notes
    -----
    This conversion accounts for the Earth's rotation and observer position at the given time.
    Assumes geodetic coordinates for the observer and equatorial coordinates for the RA/Dec input.
    """
    import numpy as np
    from org.hipparchus.geometry.euclidean.threed import Vector3D
    from org.orekit.bodies import GeodeticPoint, OneAxisEllipsoid
    from org.orekit.frames import FramesFactory, TopocentricFrame
    from org.orekit.time import AbsoluteDate, TimeScalesFactory
    from org.orekit.utils import Constants, IERSConventions

    # Unpack sensor position
    obs_lat = sensorPosition[0]  # Latitude in degrees
    obs_lon = sensorPosition[1]  # Longitude in degrees
    obs_alt_km = sensorPosition[2]  # Altitude in kilometers

    # RA/Dec to unit vector
    ra_rad = float(np.radians(ra_deg))
    dec_rad = float(np.radians(dec_deg))
    x = np.cos(dec_rad) * np.cos(ra_rad)
    y = np.cos(dec_rad) * np.sin(ra_rad)
    z = np.sin(dec_rad)
    radec_vec = Vector3D(float(x), float(y), float(z))

    # Convert range if necessary
    if rangeVal < 500000:  # If range is less than 500,000 km, assume it's in kilometers
        rangeVal = float(rangeVal * 1000)

    raDecRange = radec_vec.scalarMultiply(float(rangeVal))  # Scale unit vector by range

    # Time
    utc = TimeScalesFactory.getUTC()
    if isinstance(obs_time, datetime):
        obs_date = AbsoluteDate(
            obs_time.year,
            obs_time.month,
            obs_time.day,
            obs_time.hour,
            obs_time.minute,
            obs_time.second + obs_time.microsecond / 1e6,
            utc,
        )
    else:
        obs_date = obs_time  # already an AbsoluteDate

    # Observer frame
    earth = OneAxisEllipsoid(
        Constants.WGS84_EARTH_EQUATORIAL_RADIUS,
        Constants.WGS84_EARTH_FLATTENING,
        FramesFactory.getITRF(IERSConventions.IERS_2010, True),
    )
    geo = GeodeticPoint(
        float(np.radians(obs_lat)), float(np.radians(obs_lon)), float(obs_alt_km * 1000)
    )
    topo = TopocentricFrame(earth, geo, "observer")

    # Convert to az/el
    az = np.degrees(topo.getAzimuth(raDecRange, FramesFactory.getEME2000(), obs_date))
    el = np.degrees(topo.getElevation(raDecRange, FramesFactory.getEME2000(), obs_date))

    return az, el


def toObsSchema(results, satNo, noiseCharacteristics):
    """
    Convert results to observation schema.

    Parameters:
    results (np array): List of tuples (AbsoluteDate, RA [deg], Dec [deg]).
    satNo (int): Satellite number.
    noiseCharacteristics (float): Standard deviation of the noise [deg].
    AzEl (list): List of tuples (sensorID, sensorLat, sensorLon, sensorAlt, azimuth [deg], elevation [deg]) if available.

    Returns:
    pd.DataFrame: DataFrame with columns ['satNo', 'time', 'ra', 'dec'].
    """
    from datetime import datetime, timezone
    import uuid

    import numpy as np
    import pandas as pd

    # convert to pandas DataFrame with necessary columns
    # satNo = int(TLEline1[2:7])
    df = pd.DataFrame(
        [
            {
                "id": str(uuid.uuid4()),
                "classificationMarking": "U//LOU-SIM",
                "obTime": ts + "Z",
                "idOnOrbit": str(satNo),
                "idSensor": sensorID + "_SIM",
                "satNo": satNo,
                "taskId": "0",
                "origObjectId": "Sim",
                "origSensorId": int(sensorID[3:]),
                "uct": False,
                "azimuth": float(Az),
                "elevation": float(El),
                "range": float(rangeVal),
                "ra": float(ra),
                "declination": float(dec),
                "losUnc": np.nan,
                "senlat": float(senLat),
                "senlon": float(senLon),
                "senalt": float(senAlt),
                "senx": np.nan,
                "seny": np.nan,
                "senz": np.nan,
                "senvelx": np.nan,
                "senvely": np.nan,
                "senvelz": np.nan,
                "expDuration": np.nan,
                "zeroptd": np.nan,
                "netObjSig": np.nan,
                "netObjSigUnc": np.nan,
                "mag": np.nan,
                "magUnc": np.nan,
                "geolat": np.nan,
                "geolon": np.nan,
                "geoalt": np.nan,
                "georange": np.nan,
                "solarPhaseAngle": np.nan,
                "solarEqPhaseAngle": np.nan,
                "solarDecAngle": np.nan,
                "shutterDelay": 0,
                "sensorStDev": noiseCharacteristics,
                "rawFileURI": "",
                "source": "LOU",
                "dataMode": "SIMULATED",
                "createdAt": datetime.now(timezone.utc).isoformat() + "Z",
                "createdBy": "LOU",
                "origNetwork": "N/A",
                "type": "OPTICAL",
            }
            for ts, ra, dec, sensorID, senLat, senLon, senAlt, Az, El, rangeVal in results
        ]
    )

    return df


def epochsToSim(satNo, satObs, orbElems, target_obs_count=None, max_sim_ratio=None):
    """
    Determine epochs at which to simulate observations for a satellite.

    Uses time-bin based approach: divides observation window into bins
    based on orbital period, identifies bins with insufficient observations,
    and returns epochs at the center of each gap bin.

    Args:
        satNo: NORAD ID of satellite
        satObs: DataFrame of existing observations (must have 'obTime' column)
        orbElems: Dict with orbital elements including 'Period' (seconds)
        target_obs_count: Target total observation count (default: current + 50%)
        max_sim_ratio: Maximum ratio of simulated to total (default: from config)

    Returns:
        epochs: List of datetime objects for simulation
        bins_info: Dict with bin statistics for logging
    """
    from datetime import timedelta

    import numpy as np
    import pandas as pd

    # Use config defaults if not specified
    if max_sim_ratio is None:
        max_sim_ratio = config.simulation_max_ratio

    bins_per_period = config.simulation_bins_per_period
    min_obs_per_bin = config.simulation_min_obs_per_bin
    track_size = config.simulation_track_size
    track_spacing = config.simulation_track_spacing
    min_existing = config.simulation_min_existing_obs

    # Validate inputs
    if len(satObs) < min_existing:
        return [], {'status': 'insufficient_existing_obs', 'existing': len(satObs)}

    # Convert obTime to datetime if needed
    satObs = satObs.copy()
    if satObs['obTime'].dtype == 'object':
        # Try multiple datetime formats
        try:
            satObs['obTime'] = pd.to_datetime(satObs['obTime'], format="%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try:
                satObs['obTime'] = pd.to_datetime(satObs['obTime'], format="%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                satObs['obTime'] = pd.to_datetime(satObs['obTime'])

    satObs = satObs.sort_values(by='obTime').reset_index(drop=True)

    # Get orbital period
    if 'Period' in orbElems:
        period_sec = orbElems['Period']
    else:
        # Estimate from semi-major axis using Kepler's law
        # T = 2*pi*sqrt(a^3/mu) where mu = 398600.4418 km^3/s^2
        a_km = orbElems.get('Semi-Major Axis', 7000)  # Default to ~630km altitude
        mu = 398600.4418  # km^3/s^2
        period_sec = 2 * np.pi * np.sqrt((a_km ** 3) / mu)

    # Get observation time window
    start_time = satObs['obTime'].min()
    end_time = satObs['obTime'].max()
    window_duration = (end_time - start_time).total_seconds()

    # Calculate number of orbital periods in window
    num_periods = window_duration / period_sec
    if num_periods < 0.5:
        # Window too short for meaningful simulation
        return [], {'status': 'window_too_short', 'periods': num_periods}

    # Calculate bin size (in seconds)
    bin_size_sec = period_sec / bins_per_period
    total_bins = int(np.ceil(window_duration / bin_size_sec))

    # Create time bins
    bin_edges = [start_time + timedelta(seconds=i * bin_size_sec) for i in range(total_bins + 1)]

    # Count observations in each bin
    bin_counts = np.zeros(total_bins, dtype=int)
    for obs_time in satObs['obTime']:
        bin_idx = int((obs_time - start_time).total_seconds() / bin_size_sec)
        if 0 <= bin_idx < total_bins:
            bin_counts[bin_idx] += 1

    # Find bins with insufficient observations
    empty_bins = np.where(bin_counts < min_obs_per_bin)[0]

    if len(empty_bins) == 0:
        return [], {'status': 'all_bins_covered', 'total_bins': total_bins}

    # Calculate target observation count
    current_count = len(satObs)
    if target_obs_count is None:
        target_obs_count = int(current_count * (1 + config.simulation_target_increase))

    # Calculate maximum simulated observations allowed
    max_simulated = int(current_count * max_sim_ratio / (1 - max_sim_ratio))
    obs_to_add = min(target_obs_count - current_count, max_simulated)

    if obs_to_add <= 0:
        return [], {'status': 'already_at_target', 'current': current_count, 'target': target_obs_count}

    # Number of tracks to simulate (each track has track_size observations)
    tracks_to_add = int(np.ceil(obs_to_add / track_size))

    # Prioritize bins by how empty they are (least observations first)
    # Sort empty bins by their observation count (ascending)
    bin_priorities = [(bin_idx, bin_counts[bin_idx]) for bin_idx in empty_bins]
    bin_priorities.sort(key=lambda x: x[1])

    # Generate epochs for simulation
    epochs = []
    bins_used = 0

    for bin_idx, _ in bin_priorities:
        if bins_used >= tracks_to_add:
            break

        # Calculate center of bin
        bin_start = start_time + timedelta(seconds=bin_idx * bin_size_sec)
        bin_center = bin_start + timedelta(seconds=bin_size_sec / 2)

        # Add track of observations centered on bin center
        track_start = bin_center - timedelta(seconds=(track_size - 1) * track_spacing / 2)

        for i in range(track_size):
            epoch = track_start + timedelta(seconds=i * track_spacing)
            # Ensure epoch is within observation window
            if start_time <= epoch <= end_time:
                epochs.append(epoch.to_pydatetime())

        bins_used += 1

    # Build info dict for logging
    bins_info = {
        'status': 'success',
        'satNo': satNo,
        'period_sec': period_sec,
        'total_bins': total_bins,
        'empty_bins': len(empty_bins),
        'tracks_added': bins_used,
        'epochs_count': len(epochs),
        'existing_obs': current_count,
        'target_obs': target_obs_count
    }

    return epochs, bins_info


# Test Cases
if __name__ == "__main__":
    from datetime import datetime, timedelta

    import numpy as np
    import pandas as pd
    from propagator import TLEpropagator, ephemerisPropagator

    # Read in sensor data
    sensorCountsDf = pd.read_csv("data\\sensorCounts.csv")

    # Define test case
    testcase = "SV2"
    if testcase == "TLE":
        input1 = "1 25544U 98067A   21275.54791667  .00001264  00000-0  33463-4 0  9993"
        input2 = "2 25544  51.6455  15.0426 0002957  36.8858 323.2219 15.48920000300102"
        satelliteParameters = [99999, 0, 0]  # Dummy parameters for TLE (not used)
        timespan = 3600  # 1 hour in seconds

    elif testcase == "SV":
        input1 = np.array([-600000, -3700000, 50000000, 5659, -4211, -3616])
        input2 = datetime(2021, 10, 2, 13, 8, 57, 360000)
        satelliteParameters = [
            99999,
            1000,
            10,
        ]  # Example parameters: [satNo, mass, cross-sectional area]
        timespan = 3600

    elif testcase == "SV2":
        input1 = np.array([-600000, -3700000, 50000000, 5659, -4211, -3616])
        input2 = datetime(2021, 10, 2, 13, 8, 57, 360000)
        timespan = [
            datetime(2021, 10, 2, 13, 8, 57, 360000) + timedelta(seconds=i)
            for i in range(0, 3600, 10)
        ]
        satelliteParameters = [
            99999,
            1000,
            10,
        ]  # Example parameters: [satNo, mass, cross-sectional area]

    results = simulateObs(
        input1,
        input2,
        3600,
        sensorCountsDf,
        positionNoise=0,
        angularNoise=1 / 3600,
        step=10.0,
        satelliteParameters=satelliteParameters,
    )

    results.to_csv("data\\simulated_observations.csv", index=False)
