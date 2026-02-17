# -*- coding: utf-8 -*-
"""
Created on Wed Jul 23 2025

@author: Louis Caves
"""

import os
from pathlib import Path

# Set working directory to the parent of this script's directory (i.e., 'src/')
os.chdir(Path(__file__).resolve().parent.parent)
print("Current working directory:", os.getcwd())

import sys

sys.path.insert(0, str((Path(__file__).resolve().parent.parent)))

# Function to incorporate scoring logic

import uct_benchmark.settings as config
from uct_benchmark.simulation.orbitCoverage import orbitCoverage
from uct_benchmark.simulation.propagator import orbit2OE


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
    """stdCovg = 0.01
    lowCovg = 0.001
    stdCovgSats = results_df[results_df.orbitCoverage > stdCovg].satNo.tolist()
    numstdCovg = len(stdCovgSats)
    lowCovgSats = results_df[
        (results_df.orbitCoverage > lowCovg) & (results_df.orbitCoverage < stdCovg)
    ].satNo.tolist()
    numLowCovg = len(lowCovgSats)"""

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
    # targetObjects = partNumber.ObjType  # Unused variable
    # targetObjPerc = int(partNumber.ObjDist)  # Unused variable
    # orbitRegime = partNumber.Regime  # Unused variable
    # eventClass = partNumber.Event  # Unused variable
    # sensorType = partNumber.SensorType  # Unused variable
    targetOrbitCoverage = partNumber.PercentOrb
    targetTrackGap = partNumber.TrackGapPer
    targetObsCount = partNumber.ObsCount
    objectCount = partNumber.ObjCount
    # fitSpan = int(partNumber.TimeWindow)  # Unused variable

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
    T1 = T2covg = T2Gap = T2Obs = T3covg = T3Gap = T3Obs = T4 = False
    # Initialize data manipulation Counts
    dwnGap = simGap = dwnCovg = simCovg = dwnObsLow = dwnObsStd = simObs = None

    # Flag T4: not enough objects available
    enoughObj = numObj > targetNumObj
    if not enoughObj:
        T4 = True

    # === Orbital Coverage Analysis ===
    lowRatio = numLowCovg / targetNumObj
    stdRatio = numStdCovg / targetNumObj

    if targetOrbitCoverage == "A":  # "All" low coverage
        covgGood = (lowRatio > highPercentage) and (stdRatio > (1 - lowRatio))
        if not covgGood:
            T2covg = (lowRatio > highPercentage) and enoughObj
            if T2covg:
                dwnCovg = targetNumObj * highPercentage - numLowCovg

    elif targetOrbitCoverage == "S":  # Split coverage
        covgGood = (lowRatio > stdPercentage) and (stdRatio > stdPercentage)
        if not covgGood:
            T2covg = (lowRatio < stdPercentage) and enoughObj
            if T2covg:
                dwnCovg = targetNumObj * stdPercentage - numLowCovg
            T3covg = (stdRatio < stdPercentage) and enoughObj
            if T3covg:
                simCovg = targetNumObj * stdPercentage - numStdCovg

    elif targetOrbitCoverage == "N":  # "None" low coverage
        covgGood = (lowRatio < (1 - stdRatio)) and (stdRatio > (1 - lowPercentage))
        if not covgGood:
            T3covg = (stdRatio < (1 - lowPercentage)) and enoughObj
            if T3covg:
                simCovg = targetNumObj * highPercentage - numStdCovg
    else:
        print("Target Coverage Character is not valid")

    # === Track Gap Analysis ===
    longRatio = numLongGap / targetNumObj
    stdRatio = numStdGap / targetNumObj

    if targetTrackGap == "A":
        gapGood = (longRatio > highPercentage) and (stdRatio < (1 - longRatio))
        if not gapGood:
            T2Gap = (longRatio < highPercentage) and enoughObj
            if T2Gap:
                dwnGap = targetNumObj * highPercentage - numLongGap

    elif targetTrackGap == "S":
        gapGood = (longRatio > stdPercentage) and (stdRatio > stdPercentage)
        if not gapGood:
            T2Gap = (longRatio < stdPercentage) and enoughObj
            if T2Gap:
                dwnGap = targetNumObj * stdPercentage - numLongGap
            T3Gap = (stdRatio < stdPercentage) and enoughObj
            if T3Gap:
                simGap = targetNumObj * stdPercentage - numStdGap

    elif targetTrackGap == "N":
        gapGood = (stdRatio > (1 - lowPercentage)) and (longRatio > (1 - stdRatio))
        if not gapGood:
            T3Gap = (stdRatio < (1 - lowPercentage)) and enoughObj
            if T3Gap:
                simGap = targetNumObj * highPercentage - numStdGap
    else:
        print("Target track gap Character is not valid")

    # === Observation Count Analysis === #
    lowRatio = numLowObs / targetNumObj
    stdRatio = numStdObs / targetNumObj
    highRatio = (numStdObs + numhighObs) / targetNumObj

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
        print("Target Obs count Character is not valid")

    # === Determine Which Flag to Return ===
    flags = {"T1": T1, "T2": T2covg or T2Gap or T2Obs, "T3": T3covg or T3Gap or T3Obs, "T4": T4}

    true_flag = next((k for k, v in flags.items() if v), "T1")

    thresholds = ["T5", "T4", "T3", "T2", "T1"]
    true_flag = thresholds.index(true_flag)
    if true_flag == 3:
        true_flag = 4

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

    # print(satData['satNo'])

    # print(datasetcode.PercentOrb)
    flag, orbElems, metadata = basicScoring(datasetcode, allObs, satData)
    print(metadata)
    print(orbElems)
