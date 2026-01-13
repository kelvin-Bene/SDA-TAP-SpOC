# -*- coding: utf-8 -*-
"""
Created on Fri Jun 27 11:45:50 2025

@author: Gabriel Lundin
"""

import heapq

import numpy as np
import pandas as pd

from uct_benchmark.simulation.orbitCoverage import orbitCoverage


def binTracks(ref_obs, ref_sv, cutoff=90):
    """
    Bins a set of observations into pseudo "tracks" for TLE generation.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of observations to bin.
        ref_sv (Pandas DataFrame): Associated list of reference orbital state vectors.
        cutoff (int): Time gap to constitute a "track", in minutes. Defaults to 90.

    Returns:
        List: List of binned Dataframes in (satNo, period in sec, df) tuple pairs.
        Array: Track metrics - [total, kept, discarded, invalid]
    """
    mu = 3.986004418e5  # Standard gravitational parameter (km^3/s^2)
    metrics = [0, 0, 0, 0]  # [total, kept, discarded, invalid]

    # --------------------------------------------------------------------
    # Compute orbital periods for each satellite
    # --------------------------------------------------------------------
    # Use only the first state vector per satellite
    first_sv = ref_sv.drop_duplicates("satNo", keep="first")

    # Extract position and velocity vectors
    r_vecs = first_sv[["xpos", "ypos", "zpos"]].to_numpy()
    v_vecs = first_sv[["xvel", "yvel", "zvel"]].to_numpy()

    # Compute magnitudes of r and v vectors
    r_norms = np.linalg.norm(r_vecs, axis=1)
    v_norms = np.linalg.norm(v_vecs, axis=1)

    # Semi-major axis from vis-viva equation
    a = 1 / ((2 / r_norms) - (v_norms**2 / mu))

    # Orbital periods in seconds (NaN if hyperbolic/unbound)
    T = np.where(a > 0, 2 * np.pi * np.sqrt(a**3 / mu), np.nan)

    # Map satNo → period
    periods = dict(zip(first_sv["satNo"], T))

    # --------------------------------------------------------------------
    # Create efficient group keys for binning observations
    # --------------------------------------------------------------------
    # Instead of modifying the original DataFrame in-place, track temporary columns
    added_cols = ["grp_type", "grp_key", "grp_code"]
    ref_obs_wip = ref_obs  # Work directly to avoid full memory copy

    # Determine if observations have a sensor ID or just location
    sensor_mask = ref_obs_wip["idSensor"].notna()

    # Mark grouping type: 'id' for sensor-based, 'loc' for location-based
    ref_obs_wip["grp_type"] = np.where(sensor_mask, "id", "loc")

    # Build fast, hashable group key as a string
    ref_obs_wip["grp_key"] = np.where(
        sensor_mask,
        ref_obs_wip["idSensor"].astype(str) + "_" + ref_obs_wip["satNo"].astype(str),
        ref_obs_wip["senlat"].astype(str)
        + "_"
        + ref_obs_wip["senlon"].astype(str)
        + "_"
        + ref_obs_wip["senalt"].astype(str)
        + "_"
        + ref_obs_wip["satNo"].astype(str),
    )

    # Convert to categorical and use integer group codes for performance
    ref_obs_wip["grp_key"] = ref_obs_wip["grp_key"].astype("category")
    ref_obs_wip["grp_code"] = ref_obs_wip["grp_key"].cat.codes

    # --------------------------------------------------------------------
    # Group by generated group code
    # --------------------------------------------------------------------
    bins = []
    grouped = ref_obs_wip.groupby("grp_code", sort=False)

    for _, group in grouped:
        if len(group) < 3:
            metrics[3] += 1  # Too short to be a track
            continue
        sat = group["satNo"].iloc[0]
        bins.append((sat, group))

    # --------------------------------------------------------------------
    # Split each bin into tracks based on time gaps
    # --------------------------------------------------------------------
    tracks = []

    # Define the time gap threshold
    threshold = pd.Timedelta(minutes=90)

    for sat, obs in bins:
        # Get orbital period in seconds for this satellite
        P = periods.get(sat)
        if not P or not np.isfinite(P):
            metrics[3] += 1  # No valid period
            continue

        # Sort observations by time (stable sort)
        obs_sorted = obs.sort_values("obTime", kind="mergesort")

        # Compute time differences and identify large gaps
        time_diffs = obs_sorted["obTime"].diff().gt(threshold)

        # Use cumulative sum of large gaps to assign track IDs
        track_ids = time_diffs.cumsum()

        # Group into tracks and filter
        for _, track in obs_sorted.groupby(track_ids, sort=False):
            metrics[0] += 1  # total tracks
            if len(track) >= 3:
                metrics[1] += 1  # kept
                tracks.append((sat, P, track.reset_index(drop=True)))
            else:
                metrics[2] += 1  # discarded (too short)

    # --------------------------------------------------------------------
    # Drop temporary columns to avoid modifying input
    # --------------------------------------------------------------------
    ref_obs.drop(
        columns=[col for col in added_cols if col in ref_obs.columns],
        inplace=True,
        errors="ignore",
    )

    return tracks, metrics


def _downsampleAbsolute(ref_obs, sat_params, objp, obs_max, rand, rng, chosen_sats=None, bins=10):
    """
    Downsamples data to a maximum obs count.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of reference observations.
        sat_params (Dict): Associated super-dict of orbital elements in the following form:
            sat_params = {
                satNo: {
                    "Semi-Major Axis": a,
                    "Eccentricity": e,
                    "Inclination": i,
                    "RAAN": RAAN,
                    "Argument of Perigee": arg_perigee,
                    "Mean Anomaly": M,
                    "Period": P,
                    "Number of Obs": #Obs,
                    "Orbital Coverage": %Coverage,
                    "Max Track Gap": T/P
                },
                satNo: {...},
                satNo: {...},
                ...
            }
            All values are in km, degrees, and seconds as appropriate.
        objp (Tuple of floats): Tuple of (min%, max%, target%) in decimal.
        obs_max (int): Max observation count for the chosen objects.
        rand, rng (float): Random seed for reproducibility.
        bins (int): Number of bins for time downsampling. Defaults to 10.
        chosen_sats (List): List of satellites to consider for downsampling. Defaults to None.

    Outputs:
        ref_obs, dataset: Downsampled DataFrames.
    """

    orbital_periods = {
        sat: elems["Period"] for sat, elems in sat_params.items() if np.isfinite(elems["Period"])
    }

    # Remove sats with 2 or fewer obs (don't count)
    counts = ref_obs["satNo"].value_counts()
    culled_obs = ref_obs[ref_obs["satNo"].isin(counts[counts > 2].index)].copy()
    skipped_obs = ref_obs[ref_obs["satNo"].isin(counts[counts <= 2].index)]

    # Select target satellites
    all_satIDs = culled_obs["satNo"].dropna().unique()

    if chosen_sats is not None:
        satIDs = np.array([sat for sat in all_satIDs if sat in set(chosen_sats)])
    else:
        satIDs = all_satIDs

    # Add temp time binnings
    culled_obs["time_bin"] = pd.qcut(culled_obs["obTime"], q=bins, duplicates="drop")

    # Sort obs for performance
    grouped_obs = {sat: df for sat, df in culled_obs.groupby("satNo", observed=True)}

    # Determine observation counts for all sats
    sat_obs_counts = {
        sat: elems["Number of Obs"]
        for sat, elems in sat_params.items()
        if np.isfinite(elems["Number of Obs"])
    }

    # Satellites already below or equal to obs_max stay as is
    already_low_sats = [sat for sat, count in sat_obs_counts.items() if count <= obs_max]

    # End early if min reached
    initial_fraction = len(already_low_sats) / len(satIDs)

    if initial_fraction >= objp[0]:
        return ref_obs

    # Candidates for downsampling (still above threshold)
    remaining_sats = [sat for sat, count in sat_obs_counts.items() if count > obs_max]

    # Compute how many we still need to downsample
    total_target = int(np.ceil(objp[2] * len(satIDs)))
    remaining_needed = max(0, total_target - len(already_low_sats))

    # Sort the remaining sats by *fewest obs first*
    remaining_sats_sorted = sorted(remaining_sats, key=lambda s: sat_obs_counts[s])

    # Pick the lowest-count ones
    sampled_sats = remaining_sats_sorted[:remaining_needed]

    # Union with already-low sats (which won't actually be downsampled)
    sampled_satID_set = set(sampled_sats + already_low_sats)

    # Perform bin-based sampling
    def safe_sample(group, k, period_sec, relax=False):
        if k >= len(group):
            return group
        if relax:
            return group.sample(n=k, random_state=rand)
        time_sorted = group.sort_values("obTime")
        thresh = pd.Timedelta(seconds=0.1 * period_sec)
        diffs = time_sorted["obTime"].diff().abs().fillna(pd.Timedelta(seconds=0))
        dense = 1 / diffs.clip(lower=thresh).dt.total_seconds()
        prob = dense / dense.sum()
        return time_sorted.sample(n=k, weights=prob, random_state=rand)

    # Downsample
    keep_obs = []
    removed_ids = []
    for sat, sat_df in grouped_obs.items():
        if sat in sampled_satID_set and len(sat_df) > obs_max:
            # Group by (satNo, time_bin)
            binned = sat_df.groupby("time_bin", group_keys=False, observed=True)

            # Determine how many obs to keep per bin (initial even split)
            n_bins = binned.ngroups
            base_per_bin = obs_max // n_bins
            remainder = obs_max % n_bins

            period_sec = orbital_periods.get(sat, 5400)

            # Sort by time ONCE
            time_sorted = sat_df.sort_values("obTime")

            # Assign time bins in one vectorized call
            time_bins = pd.qcut(time_sorted["obTime"], q=bins, duplicates="drop")

            # Compute target per bin
            bin_counts = time_bins.value_counts(sort=False)
            n_bins = len(bin_counts)
            base_per_bin = obs_max // n_bins
            remainder = obs_max % n_bins

            # Compute desired sample count per bin (evenly + remainder spread)
            target_per_bin = pd.Series(base_per_bin, index=bin_counts.index) + pd.Series(
                [1] * remainder + [0] * (n_bins - remainder), index=bin_counts.index
            )

            # Compute observation density (vectorized)
            diffs = time_sorted["obTime"].diff().dt.total_seconds().fillna(period_sec)
            thresh = 0.1 * period_sec
            dense = 1.0 / diffs.clip(lower=thresh)

            # Normalize weights globally
            weights = dense / dense.sum()

            # Combine into one DataFrame
            time_sorted = time_sorted.assign(time_bin=time_bins, weight=weights)

            # Now sample per bin vectorized:
            sampled = time_sorted.groupby("time_bin", group_keys=False, observed=True).apply(
                lambda g: g.sample(
                    n=min(int(target_per_bin[g.name]), len(g)),
                    weights=g["weight"],
                    random_state=rand,
                )
            )

            keep_obs.append(sampled)

            removed_idx = sat_df.index.difference(sampled.index)
            removed_ids.extend(sat_df.loc[removed_idx, "id"].tolist())
        else:
            keep_obs.append(sat_df)

    ref_obs = pd.concat(keep_obs + [skipped_obs]).reset_index(drop=True)

    # Remove sample column
    ref_obs = ref_obs.drop("time_bin", axis=1)

    return ref_obs


def _triangle_area(p1, p2, p3) -> float:
    return 0.5 * abs(
        p1["x"] * (p2["y"] - p3["y"])
        + p2["x"] * (p3["y"] - p1["y"])
        + p3["x"] * (p1["y"] - p2["y"])
    )


def _full_polygon_area(points) -> float:
    return 0.5 * abs(
        sum(
            points[i]["x"] * points[(i + 1) % len(points)]["y"]
            - points[(i + 1) % len(points)]["x"] * points[i]["y"]
            for i in range(len(points))
        )
    )


def _lowerOrbitCoverage(ref_obs, sat_params, objp, coveragep, rng, chosen_sats=None):
    """
    Reduces orbital coverage to a set percentage.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of reference observations.
        sat_params (Dict): Associated super-dict of orbital elements in the following form:
            sat_params = {
                satNo: {
                    "Semi-Major Axis": a,
                    "Eccentricity": e,
                    "Inclination": i,
                    "RAAN": RAAN,
                    "Argument of Perigee": arg_perigee,
                    "Mean Anomaly": M,
                    "Period": P,
                    "Number of Obs": #Obs,
                    "Orbital Coverage": %Coverage,
                    "Max Track Gap": T/P
                },
                satNo: {...},
                satNo: {...},
                ...
            }
            All values are in km, degrees, and seconds as appropriate.
        objp (Tuple of floats) Tuple of (min%, max%, target%) in decimal.
        coveragep (Tuple of floats): (Max, Min) orbital coverage for the chosen objects.
        rng (float): Random seed for reproducability.
        chosen_sats (List): List of satellites to consider for coverage downsampling. Defaults to None, which allows sat-agnostic downsampling.

    Outputs:
        ref_obs, dataset: Downsampled DataFrames.
        err: Returns 1 if function failed, else 0.
    """

    err = 0

    # --------------------------------------------------------------------
    # Compute current orbit coverage and check current coverages
    # --------------------------------------------------------------------

    # Pre-group ref_obs by satNo
    # Remove sats with 2 or fewer obs (don't count)
    sorted_obs = ref_obs.groupby("satNo", observed=True).filter(lambda g: len(g) > 2)
    grouped_obs = {sat: df for sat, df in sorted_obs.groupby("satNo", observed=True)}
    satIDs = list(grouped_obs.keys())
    if chosen_sats is not None:
        chosen_sats = set(chosen_sats)
        satIDs = [sat for sat in satIDs if sat in chosen_sats]

    # Compute initial coverage and store points
    coverages = {}
    points = {}

    for sat, sat_df in grouped_obs.items():
        if len(sat_df) >= 3:
            # This does NOT use the params list as all sorted points are also needed
            coverages[sat], points[sat] = orbitCoverage(sat_df, sat_params.get(sat))
            points[sat]["time"] = points[sat]["id"].map(sat_df.set_index("id")["obTime"])
        else:
            # Cannot define coverage, 2 points is considered low coverage anyway
            coverages[sat] = 0
            points[sat] = None

    # Check how many satellites currently meet the threshold
    coverage_series = pd.Series(coverages)
    low_coverage_sats = coverage_series[coverage_series <= coveragep[0]].index
    high_coverage_sats = coverage_series[coverage_series > coveragep[0]].index

    total_sat_count = len(satIDs)

    # Return without change if already meets requirements
    min_required = int(np.ceil(objp[0] * total_sat_count))
    target_required = int(np.ceil(objp[2] * total_sat_count))

    if len(low_coverage_sats) >= min_required:
        return ref_obs, err

    # Compute how many more sats we need to prune
    sats_to_prune = target_required - len(low_coverage_sats)
    if sats_to_prune <= 0:
        return ref_obs, err

    # --------------------------------------------------------------------
    # Downsample to obtain required coverage
    # --------------------------------------------------------------------

    # Track successfully pruned satellites
    successfully_pruned = set()
    dropped_ids = []

    # Sort high-coverage sats by how close they are to the threshold (ascending)
    remaining_candidates = (
        coverage_series[high_coverage_sats]
        .sort_values()  # lowest coverage first
        .index.tolist()
    )

    while len(successfully_pruned) < sats_to_prune:
        if not remaining_candidates:
            print("Warning: Could not meet desired coverage reduction.")
            err = 1
            break

        # Select the lowest coverage satellite that hasn’t been tried yet
        sat = remaining_candidates.pop(0)

        sat_df = grouped_obs[sat]
        if points[sat] is None or len(points[sat]) < 3:
            continue  # skip unusable satellites

        max_area = np.pi * sat_params[sat]["Semi-Major Axis"] ** 2
        min_coverage_area = coveragep[1] * max_area
        target_coverage_area = coveragep[0] * max_area
        n = len(points[sat])
        point_list = points[sat].to_dict("records")

        # Build doubly linked list
        nodes = [
            {"point": pt, "index": i, "prev": (i - 1) % n, "next": (i + 1) % n}
            for i, pt in enumerate(point_list)
        ]
        removed = [False] * n
        heap = []

        sat_period = sat_params[sat]["Period"]
        gap_thresh = pd.Timedelta(seconds=0.1 * sat_period)
        relax = False

        # Heap push to sort observations
        def _push(i):
            if removed[i] or removed[nodes[i]["prev"]] or removed[nodes[i]["next"]]:
                return
            a = nodes[nodes[i]["prev"]]["point"]
            b = nodes[i]["point"]
            c = nodes[nodes[i]["next"]]["point"]
            t_prev = pd.to_datetime(a["time"])
            t_curr = pd.to_datetime(b["time"])
            t_next = pd.to_datetime(c["time"])
            if not relax and ((t_next - t_curr > gap_thresh) or (t_curr - t_prev > gap_thresh)):
                return
            area = _triangle_area(a, b, c)
            heapq.heappush(heap, (-area, i))

        for i in range(n):
            _push(i)

        # Remove point with highest coverage impact
        remaining = n
        total_removed = 0
        area = _full_polygon_area(point_list)
        current_dropped = []

        while area > target_coverage_area and remaining > 3:
            while heap:
                neg_area, i = heapq.heappop(heap)
                if removed[i]:
                    continue
                projected_area = area - abs(neg_area)  # neg_area is negative
                if projected_area < min_coverage_area:
                    continue  # Skip this point, it would drop too far

                area -= abs(neg_area)
                removed[i] = True
                current_dropped.append(nodes[i]["point"]["id"])
                total_removed += 1
                remaining -= 1

                pi = nodes[i]["prev"]
                ni = nodes[i]["next"]
                nodes[pi]["next"] = ni
                nodes[ni]["prev"] = pi

                _push(pi)
                _push(ni)

                break
            else:
                if not relax:
                    relax = True
                    heap.clear()
                    for j in range(n):
                        _push(j)
                    continue
                break  # no valid points left and already relaxed

        if area <= target_coverage_area and area >= min_coverage_area and remaining >= 3:
            dropped_ids.extend(current_dropped)
            successfully_pruned.add(sat)

    # Use set for fast membership testing
    dropped_id_set = set(dropped_ids)

    # Mask to keep only non-dropped observations
    mask_ref = ~ref_obs["id"].map(dropped_id_set.__contains__)
    ref_obs = ref_obs.loc[mask_ref].reset_index(drop=True)

    return ref_obs, err


def _increaseTrackDistance(ref_obs, sat_params, objp, trackp, rng, chosen_sats=None):
    """
    Inceases gaps between tracks to obtain a minimum gap.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of reference observations.
        sat_params (Dict): Associated super-dict of orbital elements in the following form:
            sat_params = {
                satNo: {
                    "Semi-Major Axis": a,
                    "Eccentricity": e,
                    "Inclination": i,
                    "RAAN": RAAN,
                    "Argument of Perigee": arg_perigee,
                    "Mean Anomaly": M,
                    "Period": P,
                    "Number of Obs": #Obs,
                    "Orbital Coverage": %Coverage,
                    "Max Track Gap": T/P
                },
                satNo: {...},
                satNo: {...},
                ...
            }
            All values are in km, degrees, and seconds as appropriate.
        objp (Tuple of floats): Tuple of (min%, max%, target%) in decimal.
        trackp (float): Desired gap size (in percentage of period).
        rng (float): Random seed for reproducability.
        chosen_sats (List): List of satellites to consider for track downsampling. Defaults to None, which allows sat-agnostic downsampling.

    Outputs:
        ref_obs, dataset: Downsampled DataFrames.
        err: Returns 1 if function failed, else 0.
    """

    err = 0

    # --------------------------------------------------------------------
    # Compute the maximum time gap between observations per satellite
    # --------------------------------------------------------------------

    gap_df = pd.DataFrame.from_dict(sat_params, orient="index")

    gap_df = gap_df[gap_df["Number of Obs"] > 2]

    # Convert "Max Track Gap" from fraction-of-period to an absolute timedelta if needed
    gap_df["max_gap"] = pd.to_timedelta(gap_df["Max Track Gap"] * gap_df["Period"], unit="s")

    # Period is already in seconds, make it a Timedelta for consistency
    gap_df["period_td"] = pd.to_timedelta(gap_df["Period"], unit="s")

    # Keep only the relevant columns
    gap_df = gap_df[["period_td", "max_gap"]].dropna()
    gap_df.columns = ["period", "max_gap"]  # rename to match old interface

    # Compute the target gap as a fraction of orbital period
    gap_df["target_gap"] = pd.to_timedelta(gap_df["period"] * trackp, unit="s")

    # Determine whether each satellite already has a sufficient gap
    gap_df["sufficient_gap"] = gap_df["max_gap"] >= gap_df["target_gap"]

    # --------------------------------------------------------------------
    # Select satellites that need pruning to meet desired percentage (objp)
    # --------------------------------------------------------------------
    if chosen_sats is not None:
        chosen_sats = set(chosen_sats)
        gap_df = gap_df.loc[gap_df.index.intersection(chosen_sats)]

    # Satellites with/without sufficient observation gaps
    sufficient_sats = set(gap_df[gap_df["sufficient_gap"]].index)
    insufficient_sats = set(gap_df[~gap_df["sufficient_gap"]].index)

    # Calculate how many satellites should have widened gaps
    total_sats = len(sufficient_sats) + len(insufficient_sats)
    min_required = int(np.ceil(objp[0] * total_sats))
    target_required = int(np.ceil(objp[2] * total_sats))

    # Return early if meets min threshold
    if len(sufficient_sats) >= min_required:
        return ref_obs, err

    # Determine how many additional satellites need gap widening
    num_to_prune = target_required - len(sufficient_sats)
    if num_to_prune <= 0:
        return ref_obs, err
    num_to_prune = min(num_to_prune, len(insufficient_sats))  # Don't exceed available sats

    # --------------------------------------------------------------------
    # Prune observations for selected satellites to widen gaps
    # --------------------------------------------------------------------

    dropped_ids = []  # To collect the IDs of removed observations

    # Process satellites dynamically until the desired number is met
    grouped_obs = {sat: df for sat, df in ref_obs.groupby("satNo", observed=True)}
    remaining_candidates = (
        gap_df.loc[insufficient_sats]
        .assign(delta=lambda df: (df["target_gap"] - df["max_gap"]).dt.total_seconds())
        .sort_values("delta")
        .index.tolist()
    )
    successfully_pruned = set()

    while len(successfully_pruned) < num_to_prune:
        if not remaining_candidates:
            print("Warning: Could not achieve desired number of satellites with widened gaps.")
            err = 1

        # Pick the satellite with highest existing gap to try pruning
        sat = remaining_candidates.pop(0)
        sat_df = grouped_obs[sat]

        # Get the target gap
        target_gap = gap_df.loc[sat, "target_gap"]
        if pd.isna(target_gap) or len(sat_df) < 2:
            continue

        total_span = sat_df["obTime"].max() - sat_df["obTime"].min()
        if total_span < target_gap:
            continue

        sorted_df = sat_df.sort_values("obTime").reset_index()
        times_np = sorted_df["obTime"].values.astype("datetime64[ns]")
        target_gap_np = target_gap.to_numpy()

        # Initialize sliding window algorithm
        min_count = float("inf")
        best_start_idx = None
        best_end_idx = None

        # Find minimal count window of exact length target_gap
        for i in range(len(times_np)):
            start_time = times_np[i]

            # If even the newest observation is within target_gap, we can stop
            if (times_np[-1] - start_time) < target_gap_np:
                break

            # Find the last index within [start_time, start_time + target_gap_np]
            end_time = start_time + target_gap_np
            j = np.searchsorted(times_np, end_time, side="right")  # include obs equal to end_time

            count = j - i  # how many obs fall inside this window

            if count < min_count:
                min_count = count
                best_start_idx = i
                best_end_idx = j

        to_remove = sorted_df.iloc[best_start_idx:best_end_idx]

        # Ensure at least 2 remain after removal
        if len(sorted_df) - len(to_remove) < 3:
            continue  # Cannot perform window increase

        # Record success
        total_span = sorted_df["obTime"].max() - sorted_df["obTime"].min()

        dropped_ids.extend(to_remove["id"].tolist())
        successfully_pruned.add(sat)

    # --------------------------------------------------------------------
    # Remove pruned observations from ref_obs and dataset
    # --------------------------------------------------------------------

    # Use set for fast membership testing
    dropped_id_set = set(dropped_ids)

    # Mask to keep only non-dropped observations
    mask_ref = ~ref_obs["id"].map(dropped_id_set.__contains__)
    ref_obs = ref_obs.loc[mask_ref].reset_index(drop=True)

    return ref_obs, err


def downsampleData(
    ref_obs, sat_params, orbit_coverage, track_length, obs_count, bins=10, rand=None
):
    """
    Does best downsampling of a observation dataset given specified parameters.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of reference observations.
        sat_params (Dict): Associated super-dict of orbital elements in the following form:
            sat_params = {
                satNo: {
                    "Semi-Major Axis": a,
                    "Eccentricity": e,
                    "Inclination": i,
                    "RAAN": RAAN,
                    "Argument of Perigee": arg_perigee,
                    "Mean Anomaly": M,
                    "Period": P,
                    "Number of Obs": #Obs,
                    "Orbital Coverage": %Coverage,
                    "Max Track Gap": T/P
                },
                satNo: {...},
                satNo: {...},
                ...
            }
            All values are in km, degrees, and seconds as appropriate.
        orbit_coverage (Dict): Dictionary of coverage downsample requests in the following form:
            - 'sats': List of sat IDs (leave as None if all requested)
            - 'p_bounds': Tuple of (min%, max%, target%) in decimal
            - 'p_coverage': Requested (max, min) coverage in decimal
        track_length (Dict): Dictionary of track downsample requests in the following form:
            - 'sats': List of sat IDs (leave as None if all requested)
            - 'p_bounds': Tuple of (min%, max%, target%) in decimal
            - 'p_track': Requested track length in multiples of period
        obs_count (Dict): Dictionary of observation downsample requests in the following form:
            - 'sats': List of sat IDs (leave as None if all requested)
            - 'p_bounds': Tuple of (min%, max%, target%) in decimal
            - 'obs_max': Requested maximum obs count
        bins (int): Number of bins for time downsampling. Defaults to 10.
        rand (float): Random seed for reproducability. Defaults to None.

    Returns:
        ref_obs: Downsampled DataFrame.
        p_reached: Tuple of (coverage %, gap %, obs_count %) reached.
    """

    # Set seed if specified
    if rand is not None:
        np.random.seed(rand)
        rng = np.random.default_rng(rand)
    else:
        rng = np.random.default_rng()

    # Coverage
    ref_obs, _ = _lowerOrbitCoverage(
        ref_obs,
        sat_params,
        orbit_coverage["p_bounds"],
        orbit_coverage["p_coverage"],
        rng,
        orbit_coverage["sats"],
    )
    # Gaps
    ref_obs, _ = _increaseTrackDistance(
        ref_obs,
        sat_params,
        track_length["p_bounds"],
        track_length["p_track"],
        rng,
        track_length["sats"],
    )
    # Max count
    ref_obs = _downsampleAbsolute(
        ref_obs,
        sat_params,
        obs_count["p_bounds"],
        obs_count["obs_max"],
        rand,
        rng,
        obs_count["sats"],
    )

    # --------------------------------------------------------------------
    # Determine final metrics
    # --------------------------------------------------------------------

    # Filter satellites with >2 observations
    counts = ref_obs["satNo"].value_counts()
    valid_sats = counts[counts > 2].index  # Only sats eligible for metrics

    # Helper: restrict to user-specified list if provided
    def _filter_sats(candidate_list, valid_sats):
        return (
            set(valid_sats)
            if candidate_list is None
            else set(valid_sats).intersection(candidate_list)
        )

    # Total eligable sats for each metric
    cov_sats = _filter_sats(orbit_coverage["sats"], valid_sats)
    gap_sats = _filter_sats(track_length["sats"], valid_sats)
    cnt_sats = _filter_sats(obs_count["sats"], valid_sats)

    total_cov = len(cov_sats)
    total_gap = len(gap_sats)
    total_cnt = len(cnt_sats)

    # Find current coverages
    grouped_obs = {sat: df for sat, df in ref_obs.groupby("satNo", observed=True)}

    coverages = {}
    for sat, sat_df in grouped_obs.items():
        if len(sat_df) >= 3:
            coverages[sat], _ = orbitCoverage(sat_df, sat_params.get(sat))
        else:
            # Cannot define coverage, 2 points is considered low coverage anyway
            coverages[sat] = 0

    cov = sum(v <= orbit_coverage["p_coverage"] for sat, v in coverages.items() if sat in cov_sats)

    # Find current gaps
    sorted_obs = ref_obs.sort_values(["satNo", "obTime"])
    sorted_obs["time_diff"] = sorted_obs.groupby("satNo", observed=True)["obTime"].diff()
    max_gaps = sorted_obs.groupby("satNo", observed=True)["time_diff"].max()
    periods = pd.Series({sat: elems["Period"] for sat, elems in sat_params.items()}).reindex(
        max_gaps.index
    )
    periods_td = pd.to_timedelta(periods, unit="s")

    gap_exceeds = max_gaps >= (track_length["p_track"] * periods_td)
    gap = gap_exceeds[list(gap_sats)].sum()

    # Find current counts
    count = len([sat for sat in cnt_sats if len(grouped_obs.get(sat, [])) <= obs_count["obs_max"]])

    p_reached = (
        cov / total_cov if total_cov else 0,
        gap / total_gap if total_gap else 0,
        count / total_cnt if total_cnt else 0,
    )

    return ref_obs, p_reached
