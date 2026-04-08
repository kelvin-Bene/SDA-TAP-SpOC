# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 2025

@author: Louis Caves
"""

import uct_benchmark.settings as config


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
    seed: int | None = None,
    use_physical_noise: bool = True,
    seeing_bias: str = "median",
    sample_seeing_per_obs: bool = False,
):
    """
    Simulate RA/Dec observations from TLE using Orekit-generated ephemeris.

    Two noise paths are supported:

    * **Physical** (default, ``use_physical_noise=True``) — applies the team's
      research-grade noise model: velocity aberration shift, atmospheric
      refraction shift via Bennett's formula, and per-observation noise sampled
      from a Fried's-law airmass-scaled atmospheric seeing profile calibrated
      against the Smear Explanation document (518,092 real observations).
      Sensor characteristics come from the GEODSS profile by default. This is
      the path Louis Caves asked for in the Jan 22 and Aug 28 2025 meetings
      ("more accurate noise characteristics ... we just haven't had a chance
      to incorporate that into the simulation workflow").

    * **Legacy** (``use_physical_noise=False``) — applies a flat isotropic
      Gaussian to RA/Dec independently with sigma=``angularNoise`` and to
      ECI xyz with sigma=``positionNoise``. Preserved for backward compat with
      callers that need deterministic noise-free output (``angularNoise=0``)
      and for the existing test fixtures.

    Parameters:
    input1: state vector (6x1 np.array) OR TLE line 1 (string)
    input2: Epoch of state vector (datetime) OR TLE line 2 (string)
    timespan (float OR datetime list): Duration in seconds from to simulate
        obs for OR list of epochs to simulate observations at.
    sensorsDataFrame (pd.DataFrame): DataFrame containing sensor information
        with columns ['idSensor', 'senlat', 'senlon', 'senalt', 'count'].
        senlat/senlon are in degrees, senalt is in km.
    positionNoise (float): Standard deviation of the position noise in the
        same units as the propagator output. Used only by the legacy path.
    angularNoise (float): Standard deviation of the angular noise in degrees
        (default is 1/3600 or 1 arcsecond). Used only by the legacy path.
    step (float): Sampling interval in seconds (default is 10s).
    satelliteParameters (list): List of satellite parameters
        [satNo, mass, cross-sectional area] (default is [99999, 0, 0]).
        Only used for state vector input.
    seed (int|None): RNG seed.
    use_physical_noise (bool): Switch to the physical noise pipeline. Default
        True so new datasets get realistic noise out of the box.
    seeing_bias (str): When ``sample_seeing_per_obs=False``, anchor the entire
        run at this Smear percentile. One of 'best', 'good_day', 'median'
        (default), 'bad_day', 'really_bad', 'worst'.
    sample_seeing_per_obs (bool): When True, draw a fresh seeing sigma from
        the Smear distribution for every observation. Default False (one
        sigma per run, deterministic for tests).

    Returns:
    pandas dataframe in UDL EOobs schema, with one row per simulated
    observation. The ``sensorStDev`` column carries the per-row noise sigma
    in degrees (varies across rows when ``use_physical_noise=True``).
    """
    from datetime import timezone

    import numpy as np

    # B7: Use per-call RNG for thread safety (np.random.seed is global state)
    rng = np.random.default_rng(seed)

    # Import propagator functions
    from uct_benchmark.simulation.propagator import TLEpropagator, ephemerisPropagator

    # Lazy imports for physical-noise dependencies — keeps the legacy path
    # cheap when use_physical_noise=False.
    if use_physical_noise:
        from uct_benchmark.simulation.atmospheric import (
            compute_observer_velocity,
            compute_velocity_aberration,
            refraction_correction_for_ra_dec,
        )
        from uct_benchmark.simulation.noiseModels import (
            AtmosphericConditions,
            apply_physical_noise,
            get_sensor_profile,
            sample_smear_seeing_arcsec,
        )

        # Default sensor profile for ground-based optical (GEODSS-class).
        # This is the canonical sensor type Louis's project targets per the
        # Jan 22 transcript ("optical only for the time being").
        default_sensor_profile = get_sensor_profile("GEODSS")

        # Anchor seeing sigma for the run unless caller asks for per-obs sampling.
        run_seeing_sigma = (
            None
            if sample_seeing_per_obs
            else sample_smear_seeing_arcsec(rng=None, bias=seeing_bias)
        )

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
        state = propagatedStates[i]
        x, y, z = float(state[0]), float(state[1]), float(state[2])

        # Detect units: TLEpropagator returns km/km·s^-1, ephemerisPropagator
        # returns m/m·s^-1 unless the caller passed km (in which case km is
        # preserved). Use the same threshold radec2azel uses (line 251).
        pos_norm = np.linalg.norm([x, y, z])
        if pos_norm < 1e-10:
            continue
        in_km = pos_norm < 100000  # < 100,000 means km, else meters

        if in_km:
            sat_pos_km = np.array([x, y, z])
            sat_vel_km_s = (
                np.array([float(state[3]), float(state[4]), float(state[5])])
                if len(state) >= 6
                else None
            )
            range_for_az_el = pos_norm  # km, radec2azel will auto-convert
        else:
            sat_pos_km = np.array([x, y, z]) / 1000.0
            sat_vel_km_s = (
                np.array([float(state[3]), float(state[4]), float(state[5])]) / 1000.0
                if len(state) >= 6
                else None
            )
            range_for_az_el = pos_norm  # meters, radec2azel passes through

        # Apply legacy ECI position noise BEFORE computing geometric RA/Dec.
        # Physical-noise path keeps positionNoise=0 by default; noise lives
        # in the angular domain via apply_physical_noise instead.
        if not use_physical_noise and positionNoise:
            sat_pos_km = sat_pos_km + rng.normal(0, positionNoise, size=3) / (
                1.0 if in_km else 1000.0
            )

        r_km = float(np.linalg.norm(sat_pos_km))
        if r_km < 1e-10:
            continue

        # True geometric RA/Dec from xyz (degrees)
        ra_true = float(np.degrees(np.arctan2(sat_pos_km[1], sat_pos_km[0]) % (2 * np.pi)))
        dec_true = float(
            np.degrees(np.arcsin(np.clip(sat_pos_km[2] / r_km, -1.0, 1.0)))
        )

        # Sensor selection — pick a fresh sensor every groupSize observations
        # so each sensor "owns" a small burst of consecutive obs.
        if i % groupSize == 0:
            randomSensor = sensorsDataFrame.sample(
                weights="count", random_state=seed
            ).iloc[0]
            sensorPosition = randomSensor[["senlat", "senlon", "senalt"]].tolist()
            sensorID = randomSensor["idSensor"]
        sen_lat, sen_lon, sen_alt_km = (
            float(sensorPosition[0]),
            float(sensorPosition[1]),
            float(sensorPosition[2]),
        )

        # First-pass az/el using the GEOMETRIC RA/Dec — used to gate on
        # elevation before we spend cycles on aberration/refraction/noise.
        az, el = radec2azel(
            ra_true, dec_true, range_for_az_el, sensorPosition, datetimeList[i]
        )

        # If too low, try other sensors until we find one that can see it
        # (legacy retry loop, kept verbatim).
        triedSensors = set()
        while el < 6:
            triedSensors.add(sensorID)
            availableSensors = sensorsDataFrame[
                ~sensorsDataFrame["idSensor"].isin(triedSensors)
            ]
            if availableSensors.empty:
                break
            randomSensor = availableSensors.sample(
                weights="count", random_state=seed
            ).iloc[0]
            sensorPosition = randomSensor[["senlat", "senlon", "senalt"]].tolist()
            sensorID = randomSensor["idSensor"]
            sen_lat, sen_lon, sen_alt_km = (
                float(sensorPosition[0]),
                float(sensorPosition[1]),
                float(sensorPosition[2]),
            )
            az, el = radec2azel(
                ra_true, dec_true, range_for_az_el, sensorPosition, datetimeList[i]
            )

        if el < 6:
            continue  # No sensor can see it; skip this epoch.

        if use_physical_noise:
            # 1. Velocity aberration shift (apparent position differs from
            #    geometric due to finite c + observer/satellite motion).
            try:
                obs_vel = compute_observer_velocity(
                    sen_lat, sen_lon, sen_alt_km, datetimeList[i]
                )
                ra_apparent, dec_apparent = compute_velocity_aberration(
                    ra_true,
                    dec_true,
                    obs_vel,
                    target_velocity=sat_vel_km_s,
                )
            except Exception:
                # If aberration math fails (e.g. missing satellite velocity),
                # fall through with the geometric position.
                ra_apparent, dec_apparent = ra_true, dec_true

            # 2. Atmospheric refraction shift via Bennett's formula. Returns
            #    the input unchanged below 6° elevation.
            try:
                ra_apparent, dec_apparent = refraction_correction_for_ra_dec(
                    ra_apparent,
                    dec_apparent,
                    sen_lat,
                    sen_lon,
                    sen_alt_km,
                    datetimeList[i],
                )
            except Exception:
                pass  # Refraction is best-effort; geometric position is the fallback.

            # 3. Sample physical noise from the team's noise model.
            seeing_sigma_arcsec = (
                sample_smear_seeing_arcsec(rng=rng, bias=seeing_bias)
                if sample_seeing_per_obs
                else run_seeing_sigma
            )
            atmosphere = AtmosphericConditions(seeing_arcsec=seeing_sigma_arcsec)
            ra_obs, dec_obs, noise_model = apply_physical_noise(
                ra_apparent,
                dec_apparent,
                el,
                sensor=default_sensor_profile,
                atmosphere=atmosphere,
                rng=rng,
            )
            # The reported per-row sigma is the RA noise component in degrees.
            row_sigma_deg = float(noise_model.angular_noise_ra_arcsec) / 3600.0

            # Recompute az/el from the noised RA/Dec for the output schema.
            az, el = radec2azel(
                ra_obs, dec_obs, range_for_az_el, sensorPosition, datetimeList[i]
            )
            if el < 6:
                continue  # Noise pushed us below the horizon; rare but possible.
        else:
            # Legacy path — flat isotropic Gaussian on RA and Dec independently.
            ra_obs = ra_true + rng.normal(0, angularNoise)
            dec_obs = dec_true + rng.normal(0, angularNoise)
            row_sigma_deg = float(angularNoise)
            az, el = radec2azel(
                ra_obs, dec_obs, range_for_az_el, sensorPosition, datetimeList[i]
            )

        results.append(
            (
                tstring,
                ra_obs,
                dec_obs,
                sensorID,
                sen_lat,
                sen_lon,
                sen_alt_km,
                az,
                el,
                range_for_az_el,
                row_sigma_deg,
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
    from datetime import datetime

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
    results (list): List of tuples produced by simulateObs. Each tuple is
        either the legacy 10-element shape
        ``(ts, ra, dec, sensorID, senLat, senLon, senAlt, Az, El, rangeVal)``
        or the post-physical-noise 11-element shape that adds a trailing
        per-row sigma in degrees:
        ``(..., rangeVal, row_sigma_deg)``.
    satNo (int): Satellite number.
    noiseCharacteristics (float): Fallback noise sigma in degrees applied to
        rows that don't carry their own per-row sigma (i.e. legacy 10-tuples).

    Returns:
    pd.DataFrame: DataFrame in the UDL EOObs schema. The ``sensorStDev``
    column carries the per-row sigma for 11-tuple rows and falls back to the
    scalar ``noiseCharacteristics`` for legacy 10-tuple rows.
    """
    import uuid
    from datetime import datetime, timezone

    import numpy as np
    import pandas as pd

    rows = []
    for r in results:
        # Accept either the 10-element legacy tuple or the 11-element
        # tuple that includes a per-row sigma at index 10.
        if len(r) >= 11:
            ts, ra, dec, sensorID, senLat, senLon, senAlt, Az, El, rangeVal, row_sigma = r
        else:
            ts, ra, dec, sensorID, senLat, senLon, senAlt, Az, El, rangeVal = r
            row_sigma = noiseCharacteristics

        rows.append(
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
                "sensorStDev": float(row_sigma),
                "rawFileURI": "",
                "source": "LOU",
                "dataMode": "SIMULATED",
                "createdAt": datetime.now(timezone.utc).isoformat() + "Z",
                "createdBy": "LOU",
                "origNetwork": "N/A",
                "type": "OPTICAL",
            }
        )

    return pd.DataFrame(rows)


def epochsToSim(
    satNo,
    satObs,
    orbElems,
    target_obs_count=None,
    max_sim_ratio=None,
    epoch_strategy="bin_uniform",
    preserve_longest_gap=False,
):
    """
    Determine epochs at which to simulate observations for a satellite.

    Uses time-bin based approach: divides observation window into bins
    based on orbital period, identifies bins with insufficient observations,
    and returns epochs at the center of each gap bin.

    Supports two epoch placement strategies:
        - "bin_uniform": Default. Sorts empty bins by observation count
          (ascending) so the emptiest bins are filled first uniformly.
        - "coverage_optimal": Prioritises filling the largest gaps in
          orbital coverage. For each empty bin the orbital phase (mean
          anomaly) at its centre is estimated, and bins are weighted by
          angular separation from the nearest non-empty bin so that the
          biggest orbital-coverage holes are filled first (matching the
          reference intent of "maximum impact" epoch placement).

    The optional *preserve_longest_gap* flag identifies the single
    longest observation-time gap and excludes bins that fall inside it.
    This mirrors the reference implementation's behaviour of protecting
    the longest gap because it represents a real physical constraint
    (satellite not visible from any sensor).

    Args:
        satNo: NORAD ID of satellite
        satObs: DataFrame of existing observations (must have 'obTime' column)
        orbElems: Dict with orbital elements including 'Period' (seconds)
        target_obs_count: Target total observation count (default: current + 50%)
        max_sim_ratio: Maximum ratio of simulated to total (default: from config)
        epoch_strategy: Epoch placement strategy. One of "bin_uniform"
            (default, current behaviour) or "coverage_optimal" (orbital-
            coverage-gap-aware prioritisation).
        preserve_longest_gap: If True, the longest observation time gap
            is identified and bins falling inside it are excluded from
            filling.  Default False (no gap protection).

    Returns:
        epochs: List of datetime objects for simulation
        bins_info: Dict with bin statistics for logging
    """
    from datetime import timedelta

    import numpy as np
    import pandas as pd

    # Validate epoch_strategy parameter
    valid_strategies = ("bin_uniform", "coverage_optimal")
    if epoch_strategy not in valid_strategies:
        raise ValueError(
            f"epoch_strategy must be one of {valid_strategies}, got '{epoch_strategy}'"
        )

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
        return [], {"status": "insufficient_existing_obs", "existing": len(satObs)}

    # Convert obTime to datetime if needed
    satObs = satObs.copy()
    if satObs["obTime"].dtype == "object":
        # Try multiple datetime formats
        try:
            satObs["obTime"] = pd.to_datetime(satObs["obTime"], format="%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try:
                satObs["obTime"] = pd.to_datetime(satObs["obTime"], format="%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                satObs["obTime"] = pd.to_datetime(satObs["obTime"])

    satObs = satObs.sort_values(by="obTime").reset_index(drop=True)

    # Get orbital period
    if "Period" in orbElems:
        period_sec = orbElems["Period"]
    else:
        # Estimate from semi-major axis using Kepler's law
        # T = 2*pi*sqrt(a^3/mu) where mu = 398600.4418 km^3/s^2
        a_km = orbElems.get("Semi-Major Axis", 7000)  # Default to ~630km altitude
        mu = 398600.4418  # km^3/s^2
        period_sec = 2 * np.pi * np.sqrt((a_km**3) / mu)

    # Get observation time window
    start_time = satObs["obTime"].min()
    end_time = satObs["obTime"].max()
    window_duration = (end_time - start_time).total_seconds()

    # Calculate number of orbital periods in window
    num_periods = window_duration / period_sec
    if num_periods < 0.5:
        # Window too short for meaningful simulation
        return [], {"status": "window_too_short", "periods": num_periods}

    # Calculate bin size (in seconds)
    bin_size_sec = period_sec / bins_per_period
    total_bins = int(np.ceil(window_duration / bin_size_sec))

    # Create time bins
    bin_edges = [start_time + timedelta(seconds=i * bin_size_sec) for i in range(total_bins + 1)]

    # Count observations in each bin
    bin_counts = np.zeros(total_bins, dtype=int)
    for obs_time in satObs["obTime"]:
        bin_idx = int((obs_time - start_time).total_seconds() / bin_size_sec)
        if 0 <= bin_idx < total_bins:
            bin_counts[bin_idx] += 1

    # Find bins with insufficient observations
    empty_bins = np.where(bin_counts < min_obs_per_bin)[0]

    if len(empty_bins) == 0:
        return [], {"status": "all_bins_covered", "total_bins": total_bins}

    # ------------------------------------------------------------------
    # Gap preservation: identify the longest observation time gap and
    # mark bins inside it as "protected" so they will not be filled.
    # ------------------------------------------------------------------
    preserved_gap_hours = 0.0
    protected_bin_set = set()

    if preserve_longest_gap:
        obs_times_sorted = satObs["obTime"].sort_values().reset_index(drop=True)
        if len(obs_times_sorted) >= 2:
            gaps = [
                (obs_times_sorted.iloc[i + 1] - obs_times_sorted.iloc[i]).total_seconds()
                for i in range(len(obs_times_sorted) - 1)
            ]
            longest_gap_idx = int(np.argmax(gaps))
            gap_start_time = obs_times_sorted.iloc[longest_gap_idx]
            gap_end_time = obs_times_sorted.iloc[longest_gap_idx + 1]
            preserved_gap_hours = gaps[longest_gap_idx] / 3600.0

            # Determine which bins fall entirely within this gap
            for b in range(total_bins):
                b_start_sec = b * bin_size_sec
                b_end_sec = (b + 1) * bin_size_sec
                b_start_dt = start_time + timedelta(seconds=b_start_sec)
                b_end_dt = start_time + timedelta(seconds=b_end_sec)
                if b_start_dt >= gap_start_time and b_end_dt <= gap_end_time:
                    protected_bin_set.add(b)

        # Remove protected bins from the candidate set
        empty_bins = np.array([b for b in empty_bins if b not in protected_bin_set])
        if len(empty_bins) == 0:
            return [], {
                "status": "all_gaps_protected",
                "total_bins": total_bins,
                "preserved_gap_hours": preserved_gap_hours,
                "epoch_strategy": epoch_strategy,
            }

    # Calculate target observation count
    current_count = len(satObs)
    if target_obs_count is None:
        target_obs_count = int(current_count * (1 + config.simulation_target_increase))

    # Calculate maximum simulated observations allowed
    max_simulated = int(current_count * max_sim_ratio / (1 - max_sim_ratio))
    obs_to_add = min(target_obs_count - current_count, max_simulated)

    if obs_to_add <= 0:
        return [], {
            "status": "already_at_target",
            "current": current_count,
            "target": target_obs_count,
        }

    # Number of tracks to simulate (each track has track_size observations)
    tracks_to_add = int(np.ceil(obs_to_add / track_size))

    # ------------------------------------------------------------------
    # Prioritise bins according to selected strategy
    # ------------------------------------------------------------------
    coverage_gap_filled = None  # only populated for coverage_optimal

    if epoch_strategy == "bin_uniform":
        # Default: sort empty bins by observation count (ascending)
        bin_priorities = [(bin_idx, bin_counts[bin_idx]) for bin_idx in empty_bins]
        bin_priorities.sort(key=lambda x: x[1])

    elif epoch_strategy == "coverage_optimal":
        # Coverage-aware prioritisation: weight each empty bin by the
        # angular separation (in orbital phase / mean anomaly) from the
        # nearest non-empty bin.  Larger gaps in coverage get higher
        # priority so that observations are placed for "maximum impact."

        # Compute orbital phase (mean anomaly in radians) at bin centre.
        # phase = 2*pi * ((t_centre mod T) / T)
        non_empty_bins = np.where(bin_counts >= min_obs_per_bin)[0]

        # Pre-compute phase for every bin centre
        def _bin_centre_phase(b_idx):
            """Return orbital phase in [0, 2*pi) for the centre of bin b_idx."""
            t_centre_sec = (b_idx + 0.5) * bin_size_sec
            return (t_centre_sec % period_sec) / period_sec * 2 * np.pi

        non_empty_phases = np.array([_bin_centre_phase(b) for b in non_empty_bins])

        bin_weights = []
        for b_idx in empty_bins:
            phase = _bin_centre_phase(b_idx)

            if len(non_empty_phases) == 0:
                # No non-empty bins at all -- every bin equally important
                angular_sep = 2 * np.pi
            else:
                # Angular distance on a circle: min over all non-empty phases
                diffs = np.abs(non_empty_phases - phase)
                # Wrap to [0, pi] for circular distance
                diffs = np.minimum(diffs, 2 * np.pi - diffs)
                angular_sep = float(np.min(diffs))

            bin_weights.append((b_idx, bin_counts[b_idx], angular_sep))

        # Sort by angular separation descending (largest gap first),
        # break ties by observation count ascending (emptier first)
        bin_weights.sort(key=lambda x: (-x[2], x[1]))
        bin_priorities = [(bw[0], bw[1]) for bw in bin_weights]

        # Record the largest angular coverage gap that will be filled
        if bin_weights:
            coverage_gap_filled = float(np.degrees(bin_weights[0][2]))

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
        "status": "success",
        "satNo": satNo,
        "period_sec": period_sec,
        "total_bins": total_bins,
        "empty_bins": int(len(empty_bins)),
        "tracks_added": bins_used,
        "epochs_count": len(epochs),
        "existing_obs": current_count,
        "target_obs": target_obs_count,
        "epoch_strategy": epoch_strategy,
        "coverage_gap_filled": coverage_gap_filled,
        "preserved_gap_hours": preserved_gap_hours if preserve_longest_gap else None,
    }

    return epochs, bins_info


# Test Cases
if __name__ == "__main__":
    from datetime import datetime, timedelta

    import numpy as np
    import pandas as pd

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
