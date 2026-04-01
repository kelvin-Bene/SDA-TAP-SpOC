# -*- coding: utf-8 -*-
"""
Created on Wed Jul 23 2025

@author: Louis Caves
"""

from pathlib import Path
from typing import Dict, Tuple, Optional

from loguru import logger

import uct_benchmark.settings as config
from uct_benchmark.simulation.orbitCoverage import orbitCoverage
from uct_benchmark.simulation.propagator import orbit2OE


def _evaluate_criterion(
    low_count: int,
    std_count: int,
    target_type: str,
    target_num_obj: int,
    thresholds: Tuple[float, float, float],
    enough_obj: bool,
    high_count: Optional[int] = None,
) -> Dict:
    """
    Evaluate a single criterion (coverage, gap, or obs count) for scoring.

    This is a generic evaluator that handles the repeated pattern of:
    - Checking if current ratios meet targets
    - Determining if T2 (downsampling) or T3 (simulation) is needed
    - Computing manipulation counts

    Args:
        low_count: Number of satellites/objects in "low" category
        std_count: Number of satellites/objects in "standard" category
        target_type: Target type character ('A' = All low, 'S' = Split, 'N' = None low)
        target_num_obj: Target number of objects
        thresholds: (high_percentage, std_percentage, low_percentage)
        enough_obj: Whether there are enough objects available
        high_count: Optional count for "high" category (for obs count analysis)

    Returns:
        Dict with keys:
            - is_good: bool - Whether criterion is already satisfied
            - T2: bool - Whether T2 (downsampling) is needed
            - T3: bool - Whether T3 (simulation) is needed
            - dwn_count: Optional manipulation count for downsampling
            - sim_count: Optional manipulation count for simulation
    """
    high_pct, std_pct, low_pct = thresholds

    low_ratio = low_count / target_num_obj if target_num_obj > 0 else 0
    std_ratio = std_count / target_num_obj if target_num_obj > 0 else 0

    result = {
        "is_good": False,
        "T2": False,
        "T3": False,
        "dwn_count": None,
        "sim_count": None,
    }

    if target_type == "A":  # "All" in the low/desirable category
        result["is_good"] = (low_ratio > high_pct) and (std_ratio > (1 - low_ratio))
        if not result["is_good"]:
            result["T2"] = (low_ratio > high_pct) and enough_obj
            if result["T2"]:
                result["dwn_count"] = target_num_obj * high_pct - low_count

    elif target_type == "S":  # Split between low and standard
        result["is_good"] = (low_ratio > std_pct) and (std_ratio > std_pct)
        if not result["is_good"]:
            result["T2"] = (low_ratio < std_pct) and enough_obj
            if result["T2"]:
                result["dwn_count"] = target_num_obj * std_pct - low_count
            result["T3"] = (std_ratio < std_pct) and enough_obj
            if result["T3"]:
                result["sim_count"] = target_num_obj * std_pct - std_count

    elif target_type == "N":  # "None" in the low category (all standard)
        result["is_good"] = (low_ratio < (1 - std_ratio)) and (std_ratio > (1 - low_pct))
        if not result["is_good"]:
            result["T3"] = (std_ratio < (1 - low_pct)) and enough_obj
            if result["T3"]:
                result["sim_count"] = target_num_obj * high_pct - std_count

    return result


def basicScoring(datasetCode, allObs, satData):
    """
    Score satellite observations based on orbital coverage, observation count, and observation timing.

    Parameters:
    - allObs (pd.DataFrame): Observation records with satellite numbers and timestamps.
    - satData (pd.DataFrame): Satellite metadata including TLE lines and HAMR classification.
    - datasetCode (str): Encoded string defining target dataset characteristics.

    Returns:
    - true_flag (str): The tier flag (T1, T2, T3, T4) indicating needed actions for dataset generation.
    - orbElems (dict): Dictionary of orbital elements and derived metrics keyed by satellite number.
    """

    import numpy as np
    import pandas as pd

    uniqueSats = allObs["satNo"].unique()
    results = []

    # Find total time in days included in incoming dataframe
    timeSpan = (
        pd.to_datetime(allObs["obTime"]).max() - pd.to_datetime(allObs["obTime"]).min()
    ).total_seconds() / 86400

    for sat in uniqueSats:
        if np.isnan(sat):
            continue

        # Filter observations for the current satellite
        satObs = allObs[allObs["satNo"] == sat].copy()
        numObs = len(satObs)
        numObsPer3day = 3 * (numObs / timeSpan) if timeSpan > 0 else 0

        # Skip if satellite is not in TLE database
        if sat not in satData["satNo"].values:
            continue

        # Extract TLE lines and compute orbital elements
        line1, line2 = satData.loc[satData["satNo"] == sat, ["line1", "line2"]].values[0]
        orbElems = orbit2OE(line1, line2)

        # Calculate orbital coverage
        coverage, polygon_df = orbitCoverage(satObs, orbElems)
        coverage = float(coverage)
        period = orbElems["Period"]
        if coverage < config.tooLowtoInclude:
            continue

        # Compute max track gap in observation times (normalized by period)
        satObs["obTime"] = pd.to_datetime(satObs["obTime"], format="%Y-%m-%dT%H:%M:%S.%fZ")
        satObs = satObs.sort_values(by="obTime")
        timeDeltas = satObs["obTime"].diff()
        maxGap = timeDeltas.max()

        if not np.isnan(period):
            maxGap = float(maxGap.total_seconds() / period)
        else:
            maxGap = np.nan

        # Classify orbit regime based on semi-major axis
        try:
            a = orbElems["Semi-Major Axis"]
        except Exception:
            a = np.nan

        if a < 7871:
            regime = "LEO"
        elif a > 40000:
            regime = "GEO"
        elif np.isnan(a):
            regime = "N/A"
        else:
            regime = "MEO"

        # Save results
        results.append(
            {
                "satNo": int(sat),
                "numObs": numObsPer3day,
                "orbitCoverage": coverage,
                "maxGap": maxGap,
                "regime": regime,
                "orbitalElements": orbElems,
                "orbitPolygon": polygon_df,
            }
        )

    results_df = pd.DataFrame(results)

    # Build orbital elements dictionary for export
    orbElems = {}
    for sat in results:
        oe = sat["orbitalElements"]
        satNo = sat["satNo"]
        orbElems[satNo] = {
            "Semi-Major Axis": oe["Semi-Major Axis"],
            "Eccentricity": oe["Eccentricity"],
            "Inclination": oe["Inclination"],
            "RAAN": oe["RAAN"],
            "Argument of Perigee": oe["Argument of Perigee"],
            "Mean Anomaly": oe["Mean Anomaly"],
            "Epoch": oe["Epoch"],
            "Period": oe["Period"],
            "Number of Obs": sat["numObs"],
            "Orbital Coverage": sat["orbitCoverage"],
            "Orbital Polygon": sat["orbitPolygon"],
            "Max Track Gap": sat["maxGap"],
        }

    # === Scoring Summary Metrics ===

    # Identify HAMR targets (kept for future use)
    # HAMRs = satData[satData.HAMR == "TRUE"].satNo.tolist()
    # numHAMRS = results_df[results_df['satNo'].isin(HAMRs)]
    numObj = len(uniqueSats)

    # Orbital coverage thresholds
    tooLow = config.tooLowtoInclude
    thresholds = {
        "LEO": config.lowCoverage_LEO,
        "MEO": config.lowCoverage_MEO,
        "GEO": config.lowCoverage_GEO,
    }
    # Initialize empty lists to append to for each regime
    stdCovgSats = []
    lowCovgSats = []
    # Loop through regimes to find satallites at each coverage per regime
    for regime, thresh in thresholds.items():
        mask = results_df["regime"] == regime
        stdCovgSats += results_df[mask & (results_df["orbitCoverage"] >= thresh)].satNo.tolist()
        lowCovgSats += results_df[
            mask & (results_df["orbitCoverage"] < thresh) & (results_df["orbitCoverage"] >= tooLow)
        ].satNo.tolist()
    # Count total number of standard and low coverage
    numStdCovg = len(stdCovgSats)
    numLowCovg = len(lowCovgSats)
    # Track gap categories
    longGap = config.longTrackGap  # threshold: 2 periods
    longGapSats = results_df[results_df.maxGap > longGap].satNo.tolist()
    numLongGap = len(longGapSats)
    stdGapSats = results_df[results_df.maxGap < longGap].satNo.tolist()
    numStdGap = len(stdGapSats)

    # Observation count bins
    lowObsCount = config.lowObsCount
    highObsCount = config.highObsCount
    lowObsSats = results_df[results_df.numObs <= lowObsCount].satNo.tolist()
    numLowObs = len(lowObsSats)
    stdObsSats = results_df[
        (results_df.numObs > lowObsCount) & (results_df.numObs < highObsCount)
    ].satNo.tolist()
    numStdObs = len(stdObsSats)
    highObsSats = results_df[results_df.numObs >= highObsCount].satNo.tolist()
    numhighObs = len(highObsSats)

    # === Decode dataset part number ===
    partNumber = datasetCode
    targetOrbitCoverage = partNumber.PercentOrb
    targetTrackGap = partNumber.TrackGapPer
    targetObsCount = partNumber.ObsCount
    objectCount = partNumber.ObjCount

    # read cutoff percentages from config file
    highPercentage = config.highPercentage[1]
    stdPercentage = config.standardPercentage[1]
    lowPercentage = config.lowPercentage[1]

    # Desired object count
    if objectCount == "S":
        targetNumObj = config.standardObjectCount
    elif objectCount == "H":
        targetNumObj = config.highObjectCount
    elif objectCount == "L":
        targetNumObj = config.lowObjectCount

    # Guard against division by zero
    if targetNumObj <= 0:
        targetNumObj = 1

    # Initialize scoring flags
    T4 = False
    T5 = False  # T5 = impossible criteria (per Louis's spec)
    # Initialize data manipulation Counts
    dwnGap = simGap = dwnCovg = simCovg = dwnObsLow = dwnObsStd = simObs = None

    # Flag T5: criteria impossible to meet (no objects/observations at all)
    if numObj == 0:
        T5 = True

    # Flag T4: not enough objects available
    enoughObj = numObj > targetNumObj
    if not enoughObj:
        T4 = True

    # Threshold tuple for evaluator
    thresholds = (highPercentage, stdPercentage, lowPercentage)

    # === Orbital Coverage Analysis (using generic evaluator) ===
    covg_eval = _evaluate_criterion(
        numLowCovg, numStdCovg, targetOrbitCoverage, targetNumObj, thresholds, enoughObj
    )
    covgGood = covg_eval["is_good"]
    T2covg = covg_eval["T2"]
    T3covg = covg_eval["T3"]
    dwnCovg = covg_eval["dwn_count"]
    simCovg = covg_eval["sim_count"]

    # === Track Gap Analysis (using generic evaluator) ===
    gap_eval = _evaluate_criterion(
        numLongGap, numStdGap, targetTrackGap, targetNumObj, thresholds, enoughObj
    )
    gapGood = gap_eval["is_good"]
    T2Gap = gap_eval["T2"]
    T3Gap = gap_eval["T3"]
    dwnGap = gap_eval["dwn_count"]
    simGap = gap_eval["sim_count"]

    # === Observation Count Analysis === #
    lowRatio = numLowObs / targetNumObj
    stdRatio = numStdObs / targetNumObj
    highRatio = (numStdObs + numhighObs) / targetNumObj

    # Default initialization to prevent unbound references when
    # targetObsCount falls through to the else branch.
    countGood = False
    T2Obs = False
    T3Obs = False

    if targetObsCount == "A":
        countGood = (lowRatio > highPercentage) and (stdRatio > (1 - lowRatio))
        if not countGood:
            T2Obs = (lowRatio < highPercentage) and enoughObj
            if T2Obs:
                dwnObsLow = targetNumObj * highPercentage - numLowObs
                dwnObsStd = 0

    elif targetObsCount == "S":
        countGood = (lowRatio > stdPercentage) and (stdRatio > stdPercentage)
        if not countGood:
            T2Obs = (
                (lowRatio < stdPercentage)
                or ((stdRatio < stdPercentage) and highRatio > stdPercentage)
            ) and enoughObj
            if T2Obs:
                dwnObsLow = max([targetNumObj * stdPercentage - numLowObs, 0])
                dwnObsStd = max([targetNumObj * stdPercentage - numStdObs, 0])
            T3Obs = (highRatio < stdPercentage) and enoughObj
            if T3Obs:
                simObs = targetNumObj * stdPercentage - numStdObs

    elif targetObsCount == "N":
        countGood = (stdRatio > (1 - lowPercentage)) and (lowRatio > (1 - stdRatio))
        if not countGood:
            T2Obs = (highRatio > (1 - lowPercentage)) and enoughObj
            if T2Obs:
                dwnObsLow = 0
                dwnObsStd = targetNumObj * (1 - lowPercentage) - numStdObs
            T3Obs = (highRatio < (1 - lowPercentage)) and enoughObj
            if T3Obs:
                simObs = targetNumObj * (1 - lowPercentage) - numStdObs
    else:
        logger.debug("Target Obs count Character is not valid")

    # === Determine Which Flag to Return ===
    # T1: all criteria met (no manipulation needed)
    # T2: downsample only (too much data for existing objects)
    # T3: downsample + simulate observations for existing objects (obs quality insufficient)
    # T4: downsample + simulate observations + simulate new objects (not enough objects)
    # Higher tier = more manipulation required; highest tier wins
    if numLowObs == 0 and numStdObs == 0 and numhighObs == 0:
        logger.warning("All observation count bins are empty; scoring may be unreliable")
    T1 = covgGood and gapGood and countGood
    has_T2 = T2covg or T2Gap or T2Obs
    has_T3 = T3covg or T3Gap or T3Obs

    # T5 = impossible (no data); T4 > T3 > T2 > T1 priority
    if T5:
        true_flag = 0  # T5 index in ["T5","T4","T3","T2","T1"]
    elif T4:
        true_flag = 1  # T4
    elif has_T3:
        true_flag = 2  # T3
    elif has_T2:
        true_flag = 3  # T2
    elif T1:
        true_flag = 4  # T1
    else:
        true_flag = 4  # Default to T1 (no manipulation)

    # Build a dictionary of what needs manipulation
    flagCoverage = "T1" if covgGood else ("T2" if T2covg else "T3")
    flagObsCount = "T1" if countGood else ("T2" if T2Obs else "T3")
    flagTrackGap = "T1" if gapGood else ("T2" if T2Gap else "T3")

    manipulationRequired = {
        "Obs Count": {
            "Tier": flagObsCount,
            "Number of Downsamples from High obs to std obs": (dwnObsStd),
            "Number of downsamples from std to low": (dwnObsLow),
            "Number of obs simf from low to std": (simObs),
            "List of satellites with Low Obs count": lowObsSats,
            "List of satellites with Standard Obs Count": stdObsSats,
            "List of satellites with high obs count": highObsSats,
        },
        "Orbit Coverage": {
            "Tier": flagCoverage,
            "Number of downsamples required": (dwnCovg),
            "Number of simulations required": (simCovg),
            "List of satellites with low coverage": lowCovgSats,
            "List of satellites with standard coverage": stdCovgSats,
        },
        "Track Gap": {
            "Tier": flagTrackGap,
            "Number of downsamples required": (dwnGap),
            "Number of sims required": (simGap),
            "List of satellites with long track gap": longGapSats,
            "List of satellites with standard track gap": stdGapSats,
        },
    }
    return true_flag, orbElems, manipulationRequired


if __name__ == "__main__":
    import orekit_jpype as orekit
    import pandas as pd
    from orekit_jpype.pyhelpers import setup_orekit_curdir

    orekit.initVM()
    setup_orekit_curdir(from_pip_library=True)

    from uct_benchmark.data.windowTools import DatasetCode

    partNumber = "H50GEONEOPSSSS03"
    datasetcode = DatasetCode(partNumber)
    satData = pd.read_csv("./data/satelliteData_Full.csv")
    allObs = pd.read_csv("./data/sampleWindow.csv")

    flag, orbElems, metadata = basicScoring(datasetcode, allObs, satData)
    print(metadata)
    print(orbElems)
