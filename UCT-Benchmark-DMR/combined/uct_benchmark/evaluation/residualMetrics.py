# -*- coding: utf-8 -*-
"""
Created on Thu Jun 19 13:40:12 2025

@author: Miles Puchner
"""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd


def retrieveResiduals(args):
    # Separate args
    row, ref_obs, propFunc, flag, flag2 = args

    # If TLE input, extract TLE from dataframe row
    if flag2:
        line1 = row["line1"]
        line2 = row["line2"]

    # If SV input, extract epoch and state from the dataframe row
    else:
        line2 = row["epoch"]
        line1 = np.array(
            [row["xpos"], row["ypos"], row["zpos"], row["xvel"], row["yvel"], row["zvel"]]
        )

    # Initialize filtered ref observations data frame
    ref_obs_filtered = pd.DataFrame()

    # Mode 1: compare ref observations with associated orbits
    if flag:
        # Determine sat params
        m = row["mass"]
        A = row["crossSection"]
        CD = row["dragCoeff"]
        CS = row["solarRadPressCoeff"]

        # Determine satNo for current state
        satNo = row["satNo"]

        # Filter reference obs based on satNo
        ref_obs_filtered = ref_obs[ref_obs["satNo"].isin([satNo])]

    # Mode 2: compare ref observations with entire UCTP output
    else:
        # Default sat params for consistency (no perturbation)
        m, A, CD, CS = 1000.0, 10.0, 0, 0

        # Pull observation ids for the given state from UCTP output
        uctp_ids = row["sourcedData"]

        # Filter ref observations based on uctp ids
        ref_obs_filtered = ref_obs[ref_obs["id"].isin(uctp_ids)]

    # Sort the observations by chronological order (for efficient propagation)
    ref_obs_filtered = ref_obs_filtered.sort_values(by="obTime").reset_index(drop=True)

    # Define the satellite prameters list for use in propagator
    satParams = [m, A, CD, CS]

    # Pull epoch, ra, and dec from filtered ref observation dataframe
    ids = ref_obs_filtered["id"]
    epochs = pd.to_datetime(ref_obs_filtered["obTime"]).reset_index(drop=True).to_list()
    alphas = ref_obs_filtered["ra"].to_numpy()
    deltas = ref_obs_filtered["declination"].to_numpy()

    # Convert to nx2 numpy array in the form ra, dec
    obs = np.vstack([alphas, deltas]).T

    # Initialize residuals array
    res = np.empty((0, 1))

    # Initialize RMSE
    rmse = 0

    # Find list of propagated states at each obs time
    X_propagated = propFunc(line1, line2, epochs, satParams)

    # Loop through each observation associated with the current iterations state
    for j, row2 in enumerate(obs):
        # Sort current observation
        alpha_obs, delta_obs = row2

        # Covert ra and dec to radians
        alpha_obs = np.deg2rad(alpha_obs)
        delta_obs = np.deg2rad(delta_obs)

        # Pull the propagated state at the current iteration's observation
        X_prop_temp = X_propagated[j]

        # Convert propagated state to RA and Dec
        x, y, z = X_prop_temp[0:3]
        r = np.sqrt(x**2 + y**2 + z**2)
        alpha_obs_est = np.arctan2(y, x) % (2 * np.pi)
        delta_obs_est = np.arcsin(z / r)

        # Determine great circle residual (unit circle)
        res_temp = abs(
            np.arccos(
                np.sin(delta_obs) * np.sin(delta_obs_est)
                + np.cos(delta_obs) * np.cos(delta_obs_est) * np.cos(alpha_obs - alpha_obs_est)
            )
        )

        # Compute the RMSE running sum
        rmse += res_temp**2

        # Stack data onto array
        new_row = np.array([res_temp])
        res = np.vstack([res, new_row])

    # Finalize rmse (rads) for current state
    if obs.shape[0] > 0:
        rmse = np.sqrt(rmse / obs.shape[0])

    # Detemine mean and std of residuals for current state
    mu = np.mean(res)
    sigma = np.std(res)

    # Force rmse to float type
    if isinstance(rmse, np.ndarray):
        rmse = rmse[0]

    # Create dictionary of residuals and stats for current state and append to other iterations
    return {
        "id": ids.tolist(),
        "Epoch": epochs,
        "Residuals": res.squeeze().tolist(),
        "RMSE": rmse,
        "Mean": mu,
        "std": sigma,
    }


def residualMetrics(ref_obs, mode_df, propFunc, flag, flag2=False):
    """
    The following function determines the residual metrics between propagated
    observations and a list of reference orbits. The residuals are determined
    based on the projection of the great circle distance on the unit circle.

    Inputs:
    ref_obs - Dataframe of reference observations
    mode_df - Either the associated_orbits or uctp_output dataframe
    propFunc - propagator
    flag - Boolean to represent the mode_df used
        --> True  :  use associated_orbits dataframe
        --> False :  use the uctp_output dataframe
    flag2 - Boolean to represent the type of orbital estimate input. Defaults to False.
        --> True  :  use TLE as input
        --> False :  use SV as input

    Outputs:
    residual_results - results dataframe containing the ids, epochs, residuals,
                    rmse, mean, and std for each state tested
    """

    # Define input args for row specifc calc
    args_list = [(row, ref_obs, propFunc, flag, flag2) for _, row in mode_df.iterrows()]

    # Use parallel processing to find residuals relative to each state concurrently
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        residual_results = list(executor.map(retrieveResiduals, args_list))

    # Output the total residuals data frame
    return pd.DataFrame(residual_results)


def retrieveResidualsTLE(args):
    # Separate args
    row, ref_obs, propFunc, flag, flag2 = args

    # If TLE input, extract TLE from dataframe row
    if flag2:
        line1 = row["line1"]
        line2 = row["line2"]

    # If SV input, extract epoch and state from the dataframe row
    else:
        line2 = row["epoch"]
        line1 = np.array(
            [row["xpos"], row["ypos"], row["zpos"], row["xvel"], row["yvel"], row["zvel"]]
        )

    # Initialize filtered ref observations data frame
    ref_obs_filtered = pd.DataFrame()

    # Mode 1: compare ref observations with associated orbits
    if flag:
        # Determine sat params
        m = row["mass"]
        A = row["crossSection"]
        CD = row["dragCoeff"]
        CS = row["solarRadPressCoeff"]

        # Determine satNo for current state
        satNo = row["satNo"]

        # Filter reference obs based on satNo
        ref_obs_filtered = ref_obs[ref_obs["satNo"].isin([satNo])]

    # Mode 2: compare ref observations with entire UCTP output
    else:
        # Default sat params for consistency (no perturbation)
        m, A, CD, CS = 1000.0, 10.0, 0, 0

        # Pull observation ids for the given state from UCTP output
        uctp_ids = row["sourcedData"]

        # Filter ref observations based on uctp ids
        ref_obs_filtered = ref_obs[ref_obs["idElset"].isin(uctp_ids)]

    # Sort the observations by chronological order (for efficient propagation)
    ref_obs_filtered = ref_obs_filtered.sort_values(by="epoch").reset_index(drop=True)

    # Pull epoch, TLEline1, and TLEline2 from filtered ref observation dataframe
    ids = ref_obs_filtered["idElset"]
    epochs = pd.to_datetime(ref_obs_filtered["epoch"]).reset_index(drop=True).to_list()
    TLEline1 = ref_obs_filtered["line1"]
    TLEline2 = ref_obs_filtered["line2"]

    # Convert to nx2 numpy array in the form line1, line2
    obs = np.vstack([TLEline1, TLEline2]).T

    # Initialize residuals array
    res = np.empty((0, 1))

    # Initialize RMSE
    rmse = 0

    # Define the satellite prameters list for use in propagator
    sat_params = [m, A, CD, CS]

    # Find list of propagated states at each obs time
    propLine1, propLine2, X_propagated = propFunc(line1, line2, epochs, sat_params)

    # Loop through each observation associated with the current iterations state
    for j, row2 in enumerate(obs):
        # Sort current observation
        obLine1, obLine2 = row2

        # Pull the propagated state at the current iteration's observation
        propLine1Temp = propLine1[j]
        propLine2Temp = propLine2[j]

        # Compare TLEs by orbital elements
        resultsDict = compareTLEs(obLine1, obLine2, propLine1Temp, propLine2Temp)

        # Stack data onto array
        newRow = np.array(
            [
                resultsDict["semiMajorAxisKmDif"],
                resultsDict["eccentricityDif"],
                resultsDict["inclinationDegDif"],
                resultsDict["raanDegDif"],
                resultsDict["argPerigeeDegDif"],
                resultsDict["meanAnomalyDegDif"],
            ]
        )
        res = np.vstack([res, newRow])

    # Find average, stdev, and rmse for each orbital elements
    rmse = np.array([np.sum(res[:, j] ** 2) for j in range(res.shape[1])])
    mu = np.array([np.mean(res[:, j]) for j in range(res.shape[1])])
    sigma = np.array([np.std(res[:, j]) for j in range(res.shape[1])])

    # List of orbital elements
    orbital_elements = [
        "semiMajorAxis_km",
        "eccentricity",
        "inclination_deg",
        "raan_deg",
        "argPerigee_deg",
        "meanAnomaly_deg",
    ]

    # Create dictionary of residuals and stats for current state and append to other iterations
    return {
        "id": ids.tolist(),
        "Epoch": epochs,
        "Orbital Elements": orbital_elements,
        "Residuals": res.T.tolist(),
        "RMSE": rmse,
        "Mean": mu,
        "std": sigma,
    }


def parse_tle(line1, line2):
    from datetime import datetime, timedelta
    from math import pi

    # Epoch
    year = int(line1[18:20])
    doy = float(line1[20:32])
    if year < 57:
        year += 2000
    else:
        year += 1900
    epoch = datetime(year, 1, 1) + timedelta(days=doy - 1)

    # Line 2 orbital elements
    i = float(line2[8:16])  # Inclination [deg]
    raan = float(line2[17:25])  # RAAN [deg]
    e = float("." + line2[26:33])  # Eccentricity
    argp = float(line2[34:42])  # Argument of perigee [deg]
    M = float(line2[43:51])  # Mean anomaly [deg]
    n = float(line2[52:63])  # Mean motion [revs per day]

    # Optional: Semi-major axis (in km) using Kepler's third law
    mu = 398600.4418  # Earth's gravitational parameter, km^3/s^2
    T = 86400 / n  # orbital period in seconds
    a = (mu * (T / (2 * pi)) ** 2) ** (1 / 3)  # semi-major axis in km

    return {
        "epoch": epoch,
        "inclinationDeg": i,
        "raanDeg": raan,
        "eccentricity": e,
        "argPerigeeDeg": argp,
        "meanAnomalyDeg": M,
        "meanMotionRevPerDay": n,
        "semiMajorAxisKm": a,
    }


def compareTLEs(TLE1Line1, TLE1Line2, TLE2Line1, TLE2Line2):
    elements1 = parse_tle(TLE1Line1, TLE1Line2)
    elements2 = parse_tle(TLE2Line1, TLE2Line2)

    aDif = elements1["semiMajorAxisKm"] - elements2["semiMajorAxisKm"]
    iDif = elements1["inclinationDeg"] - elements2["inclinationDeg"]
    raanDif = elements1["raanDeg"] - elements2["raanDeg"]
    eDif = elements1["eccentricity"] - elements2["eccentricity"]
    argpDif = elements1["argPerigeeDeg"] - elements2["argPerigeeDeg"]
    MDif = elements1["meanAnomalyDeg"] - elements2["meanAnomalyDeg"]

    return {
        "semiMajorAxisKmDif": aDif,
        "inclinationDegDif": iDif,
        "raanDegDif": raanDif,
        "eccentricityDif": eDif,
        "argPerigeeDegDif": argpDif,
        "meanAnomalyDegDif": MDif,
    }


def residualMetricsTLE(ref_obs, mode_df, propFunc, flag, flag2=False):
    """
    The following function determines the residual metrics between propagated
    candidate TLE and a list of trackTLEs. The residuals are determined
    for each orbital element (a,e,i,raan,perArg,meanAnomoly).

    Inputs:
    ref_obs - Dataframe of reference observation track TLEs
    mode_df - Either the associated_orbits or uctp_output dataframe
    propFunc - propagator
    flag - Boolean to represent the mode_df used
        --> True  :  use associated_orbits dataframe
        --> False :  use the uctp_output dataframe
    flag2 - Boolean to represent the type of orbital estimate input
        --> True  :  use TLE as input
        --> False :  use SV as input

    Outputs:
    residual_results - results dataframe containing the ids, epochs, residuals,
                    rmse, mean, and std for each state tested
    """

    # Define input args for row specifc calc
    args_list = [(row, ref_obs, propFunc, flag, flag2) for _, row in mode_df.iterrows()]

    # Use parallel processing to find residuals relative to each state concurrently
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        residual_results = list(executor.map(retrieveResidualsTLE, args_list))

    # Output the total residuals data frame
    return pd.DataFrame(residual_results)
