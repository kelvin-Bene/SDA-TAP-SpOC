"""
Background workers for executing long-running tasks.

Provides worker functions for dataset generation and evaluation
that run in a ThreadPoolExecutor.

Note: Dataset ID is now passed to generateDataset to avoid duplicate creation.
"""

import json
import os
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from loguru import logger

from . import Job, JobType, get_job_manager
from .progress import DatasetStage, create_job_progress_callback


def compute_composite_score(
    f1_score: Optional[float],
    position_rms_km: Optional[float],
    residual_rms_arcsec: Optional[float],
    mahalanobis_distance: Optional[float] = None,
) -> Dict[str, Any]:
    """Compute weighted composite score from binary, state, and residual metrics.

    Implements Louis Caves's calibration philosophy (Feb 19, 2026 transcript,
    ~lines 553-561): "if the states are off, you lose points there. If your
    observations are incorrectly correlated, you lose points there. If your
    sum of residuals is really high, then you lose points there."

    Weights are tunable via environment variables COMPOSITE_WEIGHT_BINARY /
    COMPOSITE_WEIGHT_STATE / COMPOSITE_WEIGHT_RESIDUAL. Defaults 0.4/0.3/0.3.

    The state component prefers the Mahalanobis p-score (1 - chi2.cdf(MD, 6))
    when a valid Mahalanobis distance is supplied, because MD is the
    covariance-weighted metric Louis's "states are off" criterion describes
    at its most rigorous. It falls back to a position-RMS heuristic when MD
    is unavailable (no Orekit run, singular covariance, etc.).

    Returns a breakdown dict so the GET /results endpoint and the leaderboard
    tooltip can show *which* component cost a submission points — Louis
    explicitly called this out as the interpretability goal.
    """
    w1 = float(os.getenv("COMPOSITE_WEIGHT_BINARY", "0.4"))
    w2 = float(os.getenv("COMPOSITE_WEIGHT_STATE", "0.3"))
    w3 = float(os.getenv("COMPOSITE_WEIGHT_RESIDUAL", "0.3"))

    # --- Binary component (F1 is already in [0, 1], higher is better) ---
    binary_component = float(f1_score) if f1_score is not None else 0.0

    # --- State component ---
    # Preferred: Mahalanobis p-score from chi-squared(6) CDF, matches Louis's
    # "how close is the state" criterion with covariance weighting.
    # Fallback: 1 - position_rms_km/100 (heuristic for when MD is unavailable).
    state_component: Optional[float] = None
    state_source: Optional[str] = None
    if mahalanobis_distance is not None and not _is_nan(mahalanobis_distance) and mahalanobis_distance >= 0:
        try:
            from scipy.stats import chi2 as _chi2

            state_component = float(1.0 - _chi2.cdf(mahalanobis_distance, df=6))
            state_source = "mahalanobis_pscore"
        except Exception:
            state_component = None
    if state_component is None and position_rms_km is not None and not _is_nan(position_rms_km) and position_rms_km >= 0:
        state_component = max(0.0, 1.0 - (float(position_rms_km) / 100.0))
        state_source = "position_rms_heuristic"

    # --- Residual component ---
    # Single great-circle RMS in arcseconds; normalise with 100 arcsec cap.
    residual_component: Optional[float] = None
    if residual_rms_arcsec is not None and not _is_nan(residual_rms_arcsec) and residual_rms_arcsec >= 0:
        residual_component = max(0.0, 1.0 - (float(residual_rms_arcsec) / 100.0))

    # --- Weighted combination with graceful fallback ---
    fallback_reason: Optional[str] = None
    if state_component is None and residual_component is None:
        composite = binary_component
        fallback_reason = "no_state_or_residual"
    elif state_component is None:
        total = w1 + w3
        composite = (w1 * binary_component + w3 * residual_component) / total
        fallback_reason = "no_state"
    elif residual_component is None:
        total = w1 + w2
        composite = (w1 * binary_component + w2 * state_component) / total
        fallback_reason = "no_residual"
    else:
        composite = w1 * binary_component + w2 * state_component + w3 * residual_component

    return {
        "composite_score": float(composite),
        "binary_component": binary_component,
        "state_component": state_component,
        "state_source": state_source,
        "residual_component": residual_component,
        "weights_used": {"binary": w1, "state": w2, "residual": w3},
        "fallback_reason": fallback_reason,
    }


def _is_nan(x: Any) -> bool:
    """Robust NaN check that also handles None and non-numeric values."""
    try:
        import math

        return x is None or (isinstance(x, float) and math.isnan(x))
    except Exception:
        return True


def _check_epoch_sanity(
    ref_obs,
    uctp_output,
    tolerance_days: int = 7,
) -> None:
    """Fail fast if UCTP estimated-orbit epochs fall nowhere near the dataset's
    observation window.

    Catches users who upload a UCTP generated against a different dataset. The
    downstream orbit-association propagator otherwise burns ~10s trying to
    close a months-wide gap before degrading to "0 associations" via the
    linear_sum_assignment guard in orbitAssociation.py.

    Uses pandas.Timedelta so it works for datetime64 columns or datetime
    objects. Skips silently if either dataframe is empty (handled upstream).

    Raises:
        ValueError: if est epochs fall outside obs window by more than
            tolerance_days on both sides.
    """
    import pandas as pd

    if ref_obs is None or len(ref_obs) == 0:
        return
    if uctp_output is None or len(uctp_output) == 0:
        return
    if "obTime" not in ref_obs.columns or "epoch" not in uctp_output.columns:
        return

    obs_times = pd.to_datetime(ref_obs["obTime"])
    est_epochs = pd.to_datetime(uctp_output["epoch"])
    obs_start = obs_times.min()
    obs_end = obs_times.max()
    est_min = est_epochs.min()
    est_max = est_epochs.max()
    tolerance = pd.Timedelta(days=tolerance_days)

    if est_max < obs_start - tolerance or est_min > obs_end + tolerance:
        raise ValueError(
            f"Submission epochs [{est_min} .. {est_max}] fall outside "
            f"dataset observation window [{obs_start} .. {obs_end}] by "
            f"more than {tolerance_days} days. This UCTP was likely "
            f"generated against a different dataset — please verify the "
            f"dataset selection and file match."
        )


# Regime-specific satellite NORAD IDs for auto-selection.
# LEO satellites are loaded at runtime from settings.satIDs (the calibration list).
# MEO/GEO/HEO lists contain well-known satellites in those regimes.
REGIME_SATELLITES = {
    "LEO": None,  # Populated at runtime from settings.satIDs (DEFAULT_SATELLITES)
    "MEO": [24876, 26360, 28190, 28474, 29486, 32260, 36585, 37753, 38833, 39166],  # GPS constellation
    "GEO": [37826, 38087, 39616, 40258, 41028, 41866, 42432, 43039, 43479, 44333],  # GEO comm sats
    "HEO": [25847, 26867, 27434, 28163, 29389, 36744, 39731, 40358],  # Molniya/Tundra orbits
}


def _convert_numpy_to_native(obj: Any) -> Any:
    """Recursively convert numpy arrays and types to native Python types for JSON serialization."""
    import numpy as np

    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: _convert_numpy_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_numpy_to_native(item) for item in obj]
    return obj


def _parse_timestamp(value: Any) -> Any:
    """Parse a timestamp value into a datetime object, or return None."""
    from datetime import datetime

    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


# Global thread pool for background tasks (thread-safe initialization)
_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def get_executor() -> ThreadPoolExecutor:
    """Get or create the global thread pool executor (thread-safe)."""
    global _executor
    if _executor is not None:
        return _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="worker")
    return _executor


def shutdown_executor(wait: bool = True) -> None:
    """Shutdown the thread pool executor.

    Args:
        wait: If True, wait for running futures to complete before returning.
              Defaults to True to avoid losing in-progress jobs.
    """
    global _executor
    with _executor_lock:
        if _executor is not None:
            logger.info(f"Shutting down thread pool executor (wait={wait})")
            _executor.shutdown(wait=wait, cancel_futures=False)
            _executor = None


def run_dataset_generation(
    job_id: str,
    dataset_id: int,
    config: Dict[str, Any],
    udl_token: str,
    esa_token: Optional[str] = None,
) -> None:
    """
    Worker function for dataset generation.

    Runs in a background thread and updates job status as it progresses.

    Args:
        job_id: The job ID to update progress
        dataset_id: The database ID for the dataset being generated
        config: Dataset generation configuration containing:
            - regime: Orbital regime (LEO, MEO, GEO, HEO)
            - object_count: Number of satellites
            - timeframe: Duration in days
            - satellites: Optional list of specific NORAD IDs
        udl_token: User's UDL API token (passed directly, never stored in DB)
        esa_token: User's ESA API token (optional, passed directly)
    """
    job_manager = get_job_manager()
    job_manager.start_job(job_id)

    try:
        # Import here to avoid circular imports and ensure Orekit is initialized
        import random

        from backend_api.database import get_db
        from uct_benchmark.api.apiIntegration import generateDataset
        from uct_benchmark.settings import satIDs as DEFAULT_SATELLITES

        # Tokens are passed directly from the authenticated user's profile
        if not udl_token:
            # DGX local edition: point users at the bundled seed dataset instead
            # of failing opaquely when no UDL token is configured.
            if os.getenv("LOCAL_DGX_MODE", "").lower() == "true":
                raise ValueError(
                    "DGX local edition has no UDL token configured, so new dataset "
                    "generation is unavailable. Open the pre-loaded sample "
                    "'DGX_SEED_SAMPLE' from the Datasets page, or set UDL_TOKEN in "
                    ".env.dgx and restart the stack."
                )
            raise ValueError(
                "The dataset generation service is temporarily unavailable due to a missing API credential. "
                "Please contact the platform administrator or try again later."
            )
        if not esa_token:
            logger.warning(
                "ESA token not provided — Discosweb data (mass/crossSection) will be unavailable. "
                "HAMR object filtering will not work correctly."
            )

        # Check if downsampling/simulation are enabled for progress weights
        downsampling_enabled = bool(
            config.get("downsampling") and config["downsampling"].get("enabled", False)
        )
        simulation_enabled = bool(
            config.get("simulation") and config["simulation"].get("enabled", False)
        )

        # Create progress callback for granular progress updates
        progress_callback = create_job_progress_callback(
            job_id,
            job_manager,
            downsampling_enabled=downsampling_enabled,
            simulation_enabled=simulation_enabled,
        )

        # Update progress - initializing
        progress_callback(DatasetStage.INITIALIZING, 0.0)

        # Get satellite list from config or auto-select based on regime
        satellites = config.get("satellites", [])
        object_count = config.get("object_count", 5)
        regime = config.get("regime", "LEO")

        if not satellites:
            # Auto-select satellites from the regime-appropriate list
            # LEO uses the default calibration list; other regimes use dedicated lists
            if regime == "LEO" or regime not in REGIME_SATELLITES:
                available_sats = list(DEFAULT_SATELLITES)
            else:
                available_sats = list(REGIME_SATELLITES[regime])
            random.shuffle(available_sats)
            satellites = available_sats[: min(object_count, len(available_sats))]
            logger.info(
                f"Auto-selected {len(satellites)} {regime} satellites: {satellites}"
            )

        timeframe = min(int(config.get("timeframe", 7)), 365)
        timeunit = config.get("timeunit", "days")

        # Parse start_date and end_date if provided
        # These should be in ISO format (YYYY-MM-DD or full ISO datetime)
        end_time = "now"  # Default to current time
        start_date_str = config.get("start_date")
        end_date_str = config.get("end_date")

        if end_date_str:
            from datetime import datetime, timezone

            def _parse_iso_datetime(date_str: str, end_of_day: bool = False) -> datetime:
                """Parse an ISO date/datetime string into a timezone-aware UTC datetime.

                Always returns a timezone-aware datetime to avoid naive/aware
                subtraction errors.  Date-only strings (no 'T') get midnight
                (start of day) or 23:59:59 (end of day) in UTC.
                """
                if "T" in date_str:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    suffix = "T23:59:59+00:00" if end_of_day else "T00:00:00+00:00"
                    dt = datetime.fromisoformat(date_str + suffix)
                # Ensure timezone-aware (UTC) even if the source had no tz info
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt

            try:
                end_time = _parse_iso_datetime(end_date_str, end_of_day=True)
                logger.info(f"Using end_date from config: {end_time}")

                # If both dates provided, calculate timeframe from them
                if start_date_str:
                    start_time = _parse_iso_datetime(start_date_str, end_of_day=False)
                    # Calculate timeframe in days (round up to avoid losing partial days)
                    delta = end_time - start_time
                    total_seconds = delta.total_seconds()
                    timeframe = max(1, int(total_seconds / 86400) + (1 if total_seconds % 86400 else 0))
                    timeunit = "days"
                    logger.info(f"Calculated timeframe from dates: {timeframe} {timeunit} "
                                f"(start={start_time}, end={end_time})")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse dates: {e}, falling back to timeframe={timeframe}")
                end_time = "now"

        # Mark initialization complete
        progress_callback(DatasetStage.INITIALIZING, 1.0)

        logger.info(
            f"Starting dataset generation for job {job_id}: "
            f"{len(satellites)} satellites, {timeframe} {timeunit}, end_time={end_time}"
        )

        # Build downsampling config if specified
        downsample_config = None
        if config.get("downsampling"):
            ds_opts = config["downsampling"]
            downsample_config = {
                "enabled": ds_opts.get("enabled", False),
                "target_coverage": ds_opts.get("target_coverage", 0.05),
                "target_gap": ds_opts.get("target_gap", 2.0),
                "max_obs_per_sat": ds_opts.get("max_obs_per_sat", 50),
                "preserve_tracks": ds_opts.get("preserve_tracks", True),
                "seed": ds_opts.get("seed"),
            }

        # Build simulation config if specified
        simulation_config = None
        if config.get("simulation"):
            sim_opts = config["simulation"]
            simulation_config = {
                "enabled": sim_opts.get("enabled", False),
                "apply_noise": sim_opts.get("apply_noise", True),
                "sensor_model": sim_opts.get("sensor_model", "GEODSS"),
                "max_synthetic_ratio": sim_opts.get("max_synthetic_ratio", 0.5),
                "seed": sim_opts.get("seed"),
            }

        # Get tier from config
        tier = config.get("tier", "T2")

        # Get search strategy from config
        search_strategy = config.get("search_strategy", "hybrid")
        window_size_minutes = config.get("window_size_minutes", 10)

        # regime was already extracted above for satellite selection

        # Get non-reference observation config (for True Negative calculation)
        include_non_ref_obs = config.get("include_non_ref_obs", True)
        non_ref_ratio = config.get("non_ref_ratio", 0.1)

        # Get object type and event codes (per Louis's 16-character code spec)
        object_type_code = config.get("object_type_code", "U")
        event_code = config.get("event_code", "NE")

        # Get window selection parameters (per Louis's bisecting search spec)
        use_window_selection = config.get("use_window_selection", True)

        # Get target percentage (positions 2-3 of 16-char code)
        target_percentage = config.get("target_percentage", "UN")

        # Get TrackTLE output option
        output_tracktle = config.get("output_tracktle", False)

        # Call the pipeline function
        # Use dt=0.5 for rate limiting to avoid overwhelming the UDL API
        (
            dataset_obs,
            obs_truth,
            state_truth,
            elset_truth,
            actual_sats,
            performance_data,
        ) = generateDataset(
            UDL_token=udl_token,
            ESA_token=esa_token,
            satIDs=satellites,
            timeframe=timeframe,
            timeunit=timeunit,
            dt=0.5,
            max_datapoints=0,
            end_time=end_time,
            use_database=False,  # Worker persists to production DB directly
            dataset_name=config.get("name"),
            downsample_config=downsample_config,
            simulation_config=simulation_config,
            tier=tier,
            dataset_id=dataset_id,
            progress_callback=progress_callback,
            search_strategy=search_strategy,
            window_size_minutes=window_size_minutes,
            regime=regime,
            include_non_ref_obs=include_non_ref_obs,
            non_ref_ratio=non_ref_ratio,
            object_type_code=object_type_code,
            event_code=event_code,
            use_window_selection=use_window_selection,
            target_percentage=target_percentage,
            output_tracktle=output_tracktle,
        )

        # Update progress - persisting to database
        progress_callback(DatasetStage.PERSISTING_DATABASE, 0.0)

        # Update dataset record in database
        db = get_db()
        observation_count = len(dataset_obs) if dataset_obs is not None else 0
        satellite_count = len(actual_sats) if actual_sats is not None else 0

        # Detect empty results and fail gracefully instead of creating a 0-object dataset
        if satellite_count == 0 or observation_count == 0:
            error_msg = (
                "No observations found for the specified parameters. "
                "The UDL API returned no data for the selected orbital regime and time window. "
                "Try expanding the date range, selecting a different orbital regime, "
                "or verifying that your UDL token has access to the requested data."
            )
            logger.warning(
                f"Dataset generation produced 0 results for job {job_id}: "
                f"satellite_count={satellite_count}, observation_count={observation_count}"
            )
            db.execute(
                """
                UPDATE datasets
                SET status = 'failed',
                    error_message = ?,
                    satellite_count = 0,
                    observation_count = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (error_msg, dataset_id),
            )
            job_manager.fail_job(job_id, error_msg)
            return

        # Calculate coverage as ratio of satellites with full data vs requested
        requested_count = len(satellites)
        avg_coverage = (satellite_count / requested_count) if requested_count > 0 else 0.0

        # Estimate size in bytes (approx 500 bytes per observation as JSON)
        estimated_size_bytes = observation_count * 500

        # Extract time window boundaries from performance_data
        time_window_start = _parse_timestamp(performance_data.get("Actual Start Time"))
        time_window_end = _parse_timestamp(performance_data.get("Actual End Time"))

        # Extract quality metrics from window selection (if used)
        ws_meta = performance_data.get("Window Selection Metadata", {})
        if not isinstance(ws_meta, dict):
            ws_meta = {}
        avg_obs_count = ws_meta.get("avg_obs_count")
        max_track_gap = ws_meta.get("avg_track_gap")

        # Downsampling/simulation flags and configs
        downsampling_applied = performance_data.get("Downsampling Applied", False)
        simulation_applied = performance_data.get("Simulation Applied", False)
        simulated_obs_count = performance_data.get("Simulated Observation Count", 0)

        downsampling_config_json = json.dumps(downsample_config) if downsample_config and downsample_config.get("enabled") else None
        simulation_config_json = json.dumps(simulation_config) if simulation_config and simulation_config.get("enabled") else None

        # Actual satellite NORAD IDs (full list, not just count)
        actual_satellite_ids_json = json.dumps(
            [int(s) for s in actual_sats] if actual_sats is not None else []
        )

        # Full performance metadata blob (captures everything computed during generation)
        performance_metadata_json = json.dumps(_convert_numpy_to_native(performance_data))

        # CTF maneuvering-during-gap challenge (SDA TAP Lab UCT challenge #6).
        # When the user requested maneuver_during_gap=True, pick ~20% of
        # satellites and inject a synthetic delta-V at the dataset midpoint:
        # drop observations from a 6-hour gap window centered on the maneuver,
        # generate replacement observations from the post-maneuver state for
        # the post-gap portion of the window, and replace the satellites'
        # state_truth rows with the post-maneuver state at the gap-end epoch.
        # The existing persistence path then writes everything as if it had
        # come straight from generateDataset(), so dataset_references holds
        # the post-maneuver state vector — which means a UCTP that fails to
        # detect the maneuver will report the pre-maneuver orbit and score
        # zero on those satellites' state metrics. See
        # uct_benchmark/data/maneuver_injection.py for the math and the
        # rationale on the [1, 50] m/s range, 20% fraction, and 6-hour gap.
        maneuver_during_gap = config.get("maneuver_during_gap", False)
        maneuver_metadata: list[dict] = []
        if (
            maneuver_during_gap
            and obs_truth is not None
            and not obs_truth.empty
            and state_truth is not None
            and not state_truth.empty
        ):
            try:
                from datetime import timezone

                import numpy as np
                import pandas as pd

                from uct_benchmark.data.maneuver_injection import (
                    compute_gap_window,
                    compute_post_maneuver_state,
                    pick_maneuvering_satellites,
                )
                from uct_benchmark.simulation.propagator import ephemerisPropagator
                from uct_benchmark.simulation.simulateObservations import simulateObs

                if time_window_start is None or time_window_end is None:
                    raise ValueError(
                        "Cannot inject maneuvers: dataset time window is unknown."
                    )

                # Ensure both endpoints are timezone-aware so timedelta math
                # and the obs_truth timestamp comparison stay consistent.
                if time_window_start.tzinfo is None:
                    tw_start = time_window_start.replace(tzinfo=timezone.utc)
                else:
                    tw_start = time_window_start
                if time_window_end.tzinfo is None:
                    tw_end = time_window_end.replace(tzinfo=timezone.utc)
                else:
                    tw_end = time_window_end

                gap_start, maneuver_epoch, gap_end = compute_gap_window(
                    tw_start, tw_end
                )

                # Pick the satellites to maneuver. Seed by dataset_id so the
                # same dataset always picks the same satellites (idempotent
                # regeneration).
                all_sats = sorted(
                    set(obs_truth["satNo"].dropna().astype(int).tolist())
                )
                maneuvering_sats = pick_maneuvering_satellites(
                    all_sats, fraction=0.20, seed=dataset_id
                )
                logger.info(
                    f"Dataset {dataset_id}: injecting maneuvers into "
                    f"{len(maneuvering_sats)} of {len(all_sats)} satellites "
                    f"(gap {gap_start.isoformat()} -> {gap_end.isoformat()}, "
                    f"maneuver epoch {maneuver_epoch.isoformat()})"
                )

                # Build a sensors DataFrame for simulateObs to draw from. Pull
                # from the existing observations so simulated obs come from
                # the same observatories as the real ones.
                sensor_cols = ["idSensor", "senlat", "senlon", "senalt"]
                if all(c in obs_truth.columns for c in sensor_cols):
                    sensors_df = (
                        obs_truth[sensor_cols]
                        .drop_duplicates(subset=["idSensor"])
                        .copy()
                    )
                    sensors_df["count"] = 1  # equal weight for sampling
                else:
                    sensors_df = None
                    logger.warning(
                        "obs_truth missing sensor columns; "
                        "simulated post-maneuver obs will be skipped"
                    )

                # Coerce obs_truth obTime to timezone-aware UTC so the gap-window
                # comparison below works regardless of how generateDataset
                # serialized the timestamps.
                if "obTime" in obs_truth.columns:
                    obs_truth["obTime"] = pd.to_datetime(
                        obs_truth["obTime"], utc=True
                    )

                for sat_no in maneuvering_sats:
                    sat_state_rows = state_truth[state_truth["satNo"] == sat_no]
                    if sat_state_rows.empty:
                        logger.warning(
                            f"Sat {sat_no} not found in state_truth; "
                            f"skipping maneuver"
                        )
                        continue
                    sat_row = sat_state_rows.iloc[0]
                    pre_state_km = np.array(
                        [
                            float(sat_row["xpos"]),
                            float(sat_row["ypos"]),
                            float(sat_row["zpos"]),
                            float(sat_row["xvel"]),
                            float(sat_row["yvel"]),
                            float(sat_row["zvel"]),
                        ]
                    )
                    pre_epoch = pd.to_datetime(sat_row["epoch"]).to_pydatetime()
                    if pre_epoch.tzinfo is None:
                        pre_epoch = pre_epoch.replace(tzinfo=timezone.utc)

                    # Pull satellite physical params if available so the
                    # propagator uses the right mass / cross-section. Defaults
                    # match the propagator's built-in defaults.
                    sat_params = [
                        float(sat_row.get("mass") or 1000.0),
                        float(sat_row.get("crossSection") or 13.873),
                        float(sat_row.get("dragCoeff") or 0.0),
                        float(sat_row.get("solarRadPressCoeff") or 0.0),
                    ]

                    try:
                        (
                            post_maneuver_state,
                            delta_v_m_s,
                            post_propagated_state,
                        ) = compute_post_maneuver_state(
                            pre_state_km=pre_state_km,
                            pre_epoch=pre_epoch,
                            maneuver_epoch=maneuver_epoch,
                            gap_end_epoch=gap_end,
                            propagator=ephemerisPropagator,
                            sat_params=sat_params,
                            seed=int(sat_no),
                        )
                    except Exception as prop_err:
                        logger.warning(
                            f"Maneuver propagation failed for sat {sat_no}: "
                            f"{prop_err}; skipping this satellite"
                        )
                        continue

                    # Drop this satellite's observations from the gap window.
                    # The existing persistence path at line 562 will only
                    # persist what's left.
                    sat_mask = obs_truth["satNo"] == sat_no
                    before_count = int(sat_mask.sum())
                    obs_truth = obs_truth[
                        ~(
                            sat_mask
                            & (obs_truth["obTime"] >= gap_start)
                            & (obs_truth["obTime"] <= gap_end)
                        )
                    ]
                    after_count = int((obs_truth["satNo"] == sat_no).sum())
                    logger.info(
                        f"Sat {sat_no}: dropped {before_count - after_count} "
                        f"obs in gap window"
                    )

                    # Generate synthetic post-gap observations from the
                    # post-maneuver state. simulateObs needs a list of target
                    # epochs; we use the epochs of the obs that WOULD have been
                    # there in the post-gap half of the window if the satellite
                    # hadn't maneuvered. Replacing the post-gap real obs with
                    # simulated ones is necessary because the satellite has
                    # moved — the old observations no longer match the new
                    # orbit.
                    if sensors_df is not None and not sensors_df.empty:
                        post_gap_epochs = sorted(
                            obs_truth[
                                (obs_truth["satNo"] == sat_no)
                                & (obs_truth["obTime"] > gap_end)
                            ]["obTime"].tolist()
                        )
                        if post_gap_epochs:
                            try:
                                sim_df = simulateObs(
                                    input1=post_propagated_state,
                                    input2=gap_end,
                                    timespan=post_gap_epochs,
                                    sensorsDataFrame=sensors_df,
                                    satelliteParameters=[
                                        int(sat_no),
                                        sat_params[0],
                                        sat_params[1],
                                    ],
                                    seed=int(sat_no),
                                    use_physical_noise=True,
                                    seeing_bias="median",
                                )
                                if sim_df is not None and not sim_df.empty:
                                    obs_truth = obs_truth[
                                        ~(
                                            (obs_truth["satNo"] == sat_no)
                                            & (obs_truth["obTime"] > gap_end)
                                        )
                                    ]
                                    obs_truth = pd.concat(
                                        [obs_truth, sim_df], ignore_index=True
                                    )
                                    logger.info(
                                        f"Sat {sat_no}: replaced post-gap obs "
                                        f"with {len(sim_df)} simulated obs from "
                                        f"post-maneuver state"
                                    )
                            except Exception as sim_err:
                                logger.warning(
                                    f"simulateObs failed for sat {sat_no}: "
                                    f"{sim_err}; keeping pre-maneuver post-gap "
                                    f"obs in place"
                                )

                    # Replace this satellite's row in state_truth with the
                    # post-maneuver state at the gap-end epoch. The existing
                    # persistence path at line 732 will then bulk-insert the
                    # post-maneuver state vector as the canonical reference.
                    # We use gap_end (not the original epoch) so the
                    # state_vectors UNIQUE constraint (sat_no, epoch, source)
                    # doesn't collide with any pre-existing UDL row.
                    sm = state_truth["satNo"] == sat_no
                    state_truth.loc[sm, "xpos"] = post_propagated_state[0]
                    state_truth.loc[sm, "ypos"] = post_propagated_state[1]
                    state_truth.loc[sm, "zpos"] = post_propagated_state[2]
                    state_truth.loc[sm, "xvel"] = post_propagated_state[3]
                    state_truth.loc[sm, "yvel"] = post_propagated_state[4]
                    state_truth.loc[sm, "zvel"] = post_propagated_state[5]
                    state_truth.loc[sm, "epoch"] = gap_end

                    # Record this satellite's maneuver in the answer-key blob.
                    # Never exposed via the download endpoint.
                    maneuver_metadata.append(
                        {
                            "sat_no": int(sat_no),
                            "maneuver_epoch": maneuver_epoch.isoformat(),
                            "delta_v_x_m_s": float(delta_v_m_s[0]),
                            "delta_v_y_m_s": float(delta_v_m_s[1]),
                            "delta_v_z_m_s": float(delta_v_m_s[2]),
                            "delta_v_magnitude_m_s": float(
                                np.linalg.norm(delta_v_m_s)
                            ),
                            "gap_start": gap_start.isoformat(),
                            "gap_end": gap_end.isoformat(),
                            "pre_maneuver_state_km": pre_state_km.tolist(),
                            "post_maneuver_state_km": post_propagated_state.tolist(),
                        }
                    )

                if maneuver_metadata:
                    logger.info(
                        f"Dataset {dataset_id}: injected "
                        f"{len(maneuver_metadata)} maneuvers; updated "
                        f"obs_truth and state_truth in place"
                    )
            except Exception as inj_err:
                # Non-fatal: dataset generation continues without maneuvers if
                # injection fails for any reason. The dataset metadata will
                # show maneuver_during_gap=False so the participant isn't
                # misled.
                logger.error(
                    f"Maneuver injection failed for dataset {dataset_id}: "
                    f"{inj_err}. Dataset will be generated WITHOUT maneuvers."
                )
                maneuver_metadata = []
                maneuver_during_gap = False

        # CTF poor sensor calibration challenge (UCT challenge #10).
        # When the user requested calibration_quality='poor', draw a per-sensor
        # systematic bias from a uniform [-3, +3] arcsec distribution. The
        # biases are persisted on the dataset row and applied virtually at
        # download time and at eval time so the shared observations table
        # stays pristine. See uct_benchmark/data/sensor_biases.py for the
        # rationale on the distribution and range.
        calibration_quality = config.get("calibration_quality", "standard")
        sensor_biases_json = None
        if calibration_quality == "poor" and obs_truth is not None and not obs_truth.empty:
            from uct_benchmark.data.sensor_biases import generate_sensor_biases

            # The truth DataFrame uses 'idSensor' as the camelCase field name
            # in the in-memory representation; the persisted observations
            # table uses 'sensor_id'. Handle both defensively.
            sensor_id_col = (
                "idSensor" if "idSensor" in obs_truth.columns else "sensor_id"
            )
            if sensor_id_col in obs_truth.columns:
                unique_sensors = (
                    obs_truth[sensor_id_col].dropna().unique().tolist()
                )
                sensor_biases_dict = generate_sensor_biases(
                    unique_sensors, seed=dataset_id
                )
                if sensor_biases_dict:
                    sensor_biases_json = json.dumps(sensor_biases_dict)
                    logger.info(
                        f"Dataset {dataset_id}: generated synthetic biases "
                        f"for {len(sensor_biases_dict)} sensors "
                        f"(calibration_quality=poor)"
                    )

        # Update the dataset status with all metrics
        db.execute(
            """
            UPDATE datasets
            SET status = 'available',
                observation_count = ?,
                satellite_count = ?,
                avg_coverage = ?,
                time_window_start = ?,
                time_window_end = ?,
                avg_obs_count = ?,
                max_track_gap = ?,
                downsampling_applied = ?,
                simulation_applied = ?,
                simulated_obs_count = ?,
                downsampling_config = ?,
                simulation_config = ?,
                actual_satellite_ids = ?,
                performance_metadata = ?,
                sensor_biases = ?,
                calibration_quality = ?,
                maneuver_during_gap = ?,
                maneuver_metadata = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                observation_count, satellite_count, avg_coverage,
                time_window_start, time_window_end,
                avg_obs_count, max_track_gap,
                downsampling_applied, simulation_applied, simulated_obs_count,
                downsampling_config_json, simulation_config_json,
                actual_satellite_ids_json, performance_metadata_json,
                sensor_biases_json, calibration_quality,
                maneuver_during_gap,
                json.dumps(maneuver_metadata) if maneuver_metadata else None,
                dataset_id,
            ),
        )

        # Persist observations to the production database, then link them.
        # Previously generateDataset() with use_database=True wrote only to
        # a local DuckDB instance, leaving the production PostgreSQL without
        # the actual observation rows.  The worker now handles persistence
        # directly so the download endpoint's JOIN succeeds.
        progress_callback(DatasetStage.PERSISTING_DATABASE, 0.4)
        logger.info(f"[WORKER] Persisting observations to production DB for dataset {dataset_id}")
        if obs_truth is not None and not obs_truth.empty and "id" in obs_truth.columns:
            import pandas as pd

            # Rename camelCase API columns to snake_case DB columns
            obs_for_db = obs_truth.copy()
            obs_for_db = obs_for_db.rename(
                columns={
                    "satNo": "sat_no",
                    "obTime": "ob_time",
                    "sensorName": "sensor_name",
                    "idSensor": "sensor_id",
                    "dataMode": "data_mode",
                    "trackId": "track_id",
                    "senderLatitude": "send_lat",
                    "senderLongitude": "send_long",
                    "senderAltitude": "send_alt",
                    "typeOptical": "type_optical",
                    "classificationMarking": "classification_marking",
                    "idOnOrbit": "id_on_orbit",
                    "taskId": "task_id",
                    "origObjectId": "orig_object_id",
                    "origSensorId": "orig_sensor_id",
                    "senx": "sen_x",
                    "seny": "sen_y",
                    "senz": "sen_z",
                    "expDuration": "exp_duration",
                    "magUnc": "mag_unc",
                    "geolat": "geo_lat",
                    "geolon": "geo_lon",
                    "geoalt": "geo_alt",
                    "georange": "geo_range",
                    "senlat": "send_lat",
                    "senlon": "send_long",
                    "senalt": "send_alt",
                    "range": "range_km",
                    "rangeRate": "range_rate_km_s",
                    "uct": "is_uct",
                    "isSimulated": "is_simulated",
                    "createdAt": "created_at",
                }
            )
            # Filter out rows with all-NaN coordinates before DB insert
            coord_cols = [c for c in ["ra", "declination", "geo_lat", "geo_lon", "geo_alt", "geo_range"] if c in obs_for_db.columns]
            if coord_cols:
                before_count = len(obs_for_db)
                obs_for_db = obs_for_db.dropna(subset=coord_cols, how="all")
                dropped = before_count - len(obs_for_db)
                if dropped > 0:
                    logger.warning(f"Dropped {dropped} observations with all-NaN coordinates before DB insert")
            inserted = db.observations.bulk_insert(obs_for_db)
            logger.info(f"Persisted {inserted} observations to production DB for dataset {dataset_id}")

            # Link observations to dataset
            # NOTE: This is a CRITICAL step - if linking fails, the dataset is unusable
            progress_callback(DatasetStage.PERSISTING_DATABASE, 0.7)
            logger.info(f"[WORKER] About to link observations for dataset {dataset_id}")
            obs_ids = obs_truth["id"].tolist()
            track_assignments = {}
            if "trackId" in obs_truth.columns:
                INT32_MAX = 2147483647  # Max value for INT32
                for _, row in obs_truth.iterrows():
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
            # CTF train/validation/test split assignment per the LLNL paper.
            # Stratified by satellite so each split contains a representative
            # slice of the dataset (see uct_benchmark/data/dataset_splits.py).
            # Seed is the dataset_id so the same dataset always splits the
            # same way — important if a dataset is regenerated and we want
            # the leaderboard to compare submissions on equivalent ground.
            from uct_benchmark.data.dataset_splits import assign_stratified_splits

            split_assignment = assign_stratified_splits(
                obs_truth, split_ratios=(0.6, 0.2, 0.2), seed=dataset_id
            )

            # Wrap linking in try/except: if linking fails, clean up orphaned observations
            try:
                db.datasets.add_observations_to_dataset(
                    dataset_id,
                    obs_ids,
                    track_assignments,
                    split_assignment=split_assignment,
                )
            except Exception as link_err:
                logger.error(f"Failed to link observations to dataset {dataset_id}: {link_err}. Rolling back inserted observations.")
                try:
                    placeholders = ",".join(["?"] * len(obs_ids))
                    db.execute(f"DELETE FROM observations WHERE id IN ({placeholders})", tuple(obs_ids))
                    logger.info(f"Rolled back {len(obs_ids)} orphaned observations for dataset {dataset_id}")
                except Exception as cleanup_err:
                    logger.error(f"CRITICAL: Failed to clean up orphaned observations for dataset {dataset_id}: {cleanup_err}")
                raise
            logger.info(f"Linked {len(obs_ids)} observations to dataset {dataset_id}")
        else:
            # If we have no observations to link, this is also an error
            if observation_count > 0:
                raise ValueError(
                    f"Dataset has {observation_count} observations in count but no observation IDs to link. "
                    "This indicates a data consistency issue."
                )

        # ============================================================
        # Persist reference state vectors, element sets, and dataset_references
        # so run_evaluation_pipeline can reconstruct the truth DataFrames.
        # Non-fatal on failure: dataset is still downloadable; evaluation
        # of this dataset will surface a clear error until re-generated.
        # ============================================================
        progress_callback(DatasetStage.PERSISTING_DATABASE, 0.8)
        logger.info(f"[WORKER] Persisting reference state vectors for dataset {dataset_id}")
        try:
            if state_truth is not None and not state_truth.empty and "satNo" in state_truth.columns:
                # 1. Upsert satellites table with ESA physical params (propagator needs mass/area
                #    at eval time; these live on satellites, not state_vectors).
                sat_cols_present = [
                    c for c in ["satNo", "mass", "crossSection", "dragCoeff", "solarRadPressCoeff"]
                    if c in state_truth.columns
                ]
                if sat_cols_present:
                    sat_df = (
                        state_truth[sat_cols_present]
                        .drop_duplicates(subset=["satNo"])
                        .rename(
                            columns={
                                "satNo": "sat_no",
                                "mass": "mass_kg",
                                "crossSection": "cross_section_m2",
                                "dragCoeff": "drag_coeff",
                                "solarRadPressCoeff": "srp_coeff",
                            }
                        )
                    )
                    if not sat_df.empty:
                        db.satellites.bulk_upsert(sat_df)
                        logger.info(f"Upserted {len(sat_df)} satellites with physical params")

                # 2. Normalize state_truth → state_vectors schema and bulk insert.
                sv_df = state_truth.rename(
                    columns={
                        "satNo": "sat_no",
                        "xpos": "x_pos",
                        "ypos": "y_pos",
                        "zpos": "z_pos",
                        "xvel": "x_vel",
                        "yvel": "y_vel",
                        "zvel": "z_vel",
                        "cov_matrix": "covariance",
                        "cov": "covariance",
                    }
                )
                sv_keep = [
                    "sat_no", "epoch",
                    "x_pos", "y_pos", "z_pos",
                    "x_vel", "y_vel", "z_vel",
                    "covariance",
                ]
                sv_df = sv_df[[c for c in sv_keep if c in sv_df.columns]].copy()
                sv_df["source"] = "UDL"
                sv_df["data_mode"] = "REAL"
                sv_inserted = db.state_vectors.bulk_insert(sv_df)
                logger.info(
                    f"Persisted {sv_inserted} reference state vectors (of {len(sv_df)} candidates) "
                    f"for dataset {dataset_id}"
                )

                # 3. Normalize elset_truth → element_sets and bulk insert.
                es_inserted = 0
                if elset_truth is not None and not elset_truth.empty and "satNo" in elset_truth.columns:
                    es_df = elset_truth.rename(columns={"satNo": "sat_no"})
                    # Explode parsed orbital elements dict (apiIntegration.py:2206) if present.
                    if "elset" in es_df.columns:
                        def _extract(d, key):
                            return d.get(key) if isinstance(d, dict) else None
                        for field in [
                            "inclination", "raan", "eccentricity", "arg_perigee",
                            "mean_anomaly", "mean_motion", "b_star",
                            "semi_major_axis_km", "period_minutes",
                        ]:
                            if field not in es_df.columns:
                                es_df[field] = es_df["elset"].apply(lambda d, f=field: _extract(d, f))
                    # Element sets need an epoch; borrow from state_truth per-satellite if missing.
                    if "epoch" not in es_df.columns:
                        epoch_by_sat = dict(zip(sv_df["sat_no"], sv_df["epoch"]))
                        es_df["epoch"] = es_df["sat_no"].map(epoch_by_sat)
                    es_keep = [
                        "sat_no", "line1", "line2", "epoch",
                        "inclination", "raan", "eccentricity", "arg_perigee",
                        "mean_anomaly", "mean_motion", "b_star",
                        "semi_major_axis_km", "period_minutes",
                    ]
                    es_df = es_df[[c for c in es_keep if c in es_df.columns]].copy()
                    es_df["source"] = "UDL"
                    es_inserted = db.element_sets.bulk_insert(es_df)
                    logger.info(
                        f"Persisted {es_inserted} reference element sets (of {len(es_df)} candidates) "
                        f"for dataset {dataset_id}"
                    )

                # 4. Build grouped_obs_ids per satellite from obs_truth.
                grouped_obs_ids_by_sat: Dict[int, list] = {}
                if (
                    obs_truth is not None
                    and not obs_truth.empty
                    and "satNo" in obs_truth.columns
                    and "id" in obs_truth.columns
                ):
                    for sat_no, group in obs_truth.groupby("satNo"):
                        grouped_obs_ids_by_sat[int(sat_no)] = group["id"].astype(str).tolist()

                # 5. Resolve state_vector_id + element_set_id per satellite using the
                #    precise UNIQUE keys, then link via dataset_references.
                linked_count = 0
                for sat_no in actual_sats if actual_sats is not None else []:
                    sat_no_int = int(sat_no)

                    sat_sv_rows = sv_df[sv_df["sat_no"] == sat_no_int]
                    sv_epoch = sat_sv_rows.iloc[0]["epoch"] if not sat_sv_rows.empty else None
                    sv_id = None
                    if sv_epoch is not None:
                        sv_lookup = db.adapter.fetchdf(
                            "SELECT id FROM state_vectors WHERE sat_no = ? AND epoch = ? AND source = 'UDL' LIMIT 1",
                            (sat_no_int, sv_epoch),
                        )
                        if not sv_lookup.empty:
                            sv_id = int(sv_lookup.iloc[0]["id"])

                    es_id = None
                    if es_inserted > 0:
                        es_lookup = db.adapter.fetchdf(
                            "SELECT id FROM element_sets WHERE sat_no = ? ORDER BY created_at DESC LIMIT 1",
                            (sat_no_int,),
                        )
                        if not es_lookup.empty:
                            es_id = int(es_lookup.iloc[0]["id"])

                    db.datasets.add_references_to_dataset(
                        dataset_id=dataset_id,
                        sat_no=sat_no_int,
                        state_vector_id=sv_id,
                        element_set_id=es_id,
                        grouped_obs_ids=grouped_obs_ids_by_sat.get(sat_no_int),
                    )
                    linked_count += 1

                logger.info(f"Linked {linked_count} reference entries to dataset {dataset_id}")
        except Exception as ref_err:
            # Non-fatal: dataset is still downloadable, but evaluation of this dataset
            # will need to be re-run once reference persistence is fixed. Logged for follow-up.
            logger.error(
                f"Failed to persist reference data for dataset {dataset_id}: {ref_err}. "
                f"Dataset is still available for download but cannot be evaluated until "
                f"dataset_references is populated."
            )
            logger.debug(traceback.format_exc())

        # Finalize
        progress_callback(DatasetStage.PERSISTING_DATABASE, 1.0)
        progress_callback(DatasetStage.FINALIZING, 0.5)

        # Complete the job
        result = {
            "dataset_id": dataset_id,
            "observation_count": observation_count,
            "satellite_count": satellite_count,
            "actual_satellites": [int(s) for s in actual_sats] if actual_sats is not None else [],
            "performance": performance_data,
        }

        # Convert numpy arrays to native Python types for JSON serialization
        result = _convert_numpy_to_native(result)
        job_manager.complete_job(job_id, result)
        logger.info(f"Dataset generation completed for job {job_id}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Dataset generation failed for job {job_id}: {error_msg}")
        logger.debug(traceback.format_exc())

        # Update dataset status to failed
        try:
            from backend_api.database import get_db

            db = get_db()
            # Rollback any failed transaction state before executing update
            try:
                db.execute("ROLLBACK")
            except Exception as rollback_error:
                logger.debug(f"Rollback not needed or failed (expected if not in transaction): {rollback_error}")
            db.execute(
                "UPDATE datasets SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (error_msg, dataset_id),
            )
        except Exception as db_error:
            # Log the secondary failure - this is critical as the dataset will be stuck in 'generating' state
            logger.error(
                f"CRITICAL: Failed to mark dataset {dataset_id} as failed: {db_error}. "
                "Dataset may be stuck in 'generating' state."
            )
            # Include in error message so it's visible in job status
            error_msg = f"{error_msg} [DB update also failed: {db_error}]"

        job_manager.fail_job(job_id, error_msg)


def run_evaluation_pipeline(
    job_id: str,
    submission_id: int,
    dataset_id: int,
    file_path: str,
) -> None:
    """
    Worker function for running evaluation on a submission.

    Runs in a background thread and updates job status as it progresses.

    Args:
        job_id: The job ID to update progress
        submission_id: The database ID for the submission
        dataset_id: The dataset ID to evaluate against
        file_path: Path to the uploaded UCTP output file
    """
    job_manager = get_job_manager()
    job_manager.start_job(job_id)

    try:
        import numpy as np
        import pandas as pd

        from backend_api.database import get_db
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics
        from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
        from uct_benchmark.evaluation.residualMetrics import residualMetrics
        from uct_benchmark.evaluation.stateMetrics import stateMetrics
        from uct_benchmark.simulation.propagator import (
            ephemerisPropagator,
            monteCarloPropagator,
        )
        from uct_benchmark.utils.field_mapping import (
            normalize_submission,
            validate_required_fields,
        )
        from uct_benchmark.utils.generateCov import generateCov
        from uct_benchmark.utils.unitConversion import unitConversion

        job_manager.update_job(job_id, progress=10)

        db = get_db()

        # --------------------------------------------------------------
        # 1. Load dataset metadata; must exist before anything else.
        # --------------------------------------------------------------
        dataset_row = db.execute(
            "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        if not dataset_row:
            raise ValueError(f"Dataset {dataset_id} not found")

        job_manager.update_job(job_id, progress=15)

        # --------------------------------------------------------------
        # 2. Load and normalise the submission (UCTP output) file.
        #    Field names are harmonised to the canonical
        #    xpos/ypos/zpos/xvel/yvel/zvel/epoch/grouped_ops shape per
        #    Benchmarking Doc §File I/O Format. Covariance (if present)
        #    is parsed into a 6x6 matrix via generateCov. Frame is
        #    forced to J2000 if a non-J2000 frame was declared.
        # --------------------------------------------------------------
        with open(file_path, "r") as f:
            submission_data = json.load(f)
        if isinstance(submission_data, list):
            submission_data = normalize_submission(submission_data)
            if submission_data:
                missing = validate_required_fields(submission_data[0])
                if missing:
                    raise ValueError(
                        f"Submission is missing required UCTP fields: "
                        f"{', '.join(missing)}. Expected: grouped_ops, epoch, "
                        f"xpos, ypos, zpos, xvel, yvel, zvel"
                    )
        else:
            raise ValueError(
                "Submission must be a JSON list of state-vector records "
                "matching the UCTP output schema."
            )
        if not submission_data:
            raise ValueError("Submission contains no records")

        uctp_output = pd.DataFrame(submission_data)
        uctp_output["epoch"] = pd.to_datetime(uctp_output["epoch"])
        uctp_output = generateCov(uctp_output)
        if "referenceFrame" in uctp_output.columns:
            non_j2000 = uctp_output[
                ~uctp_output["referenceFrame"].isin(["J2000", "EME2000"])
            ]
            if not non_j2000.empty:
                logger.info(
                    f"Converting {len(non_j2000)} UCTP state vectors to J2000"
                )
                uctp_output = unitConversion(uctp_output)

        job_manager.update_job(job_id, progress=25)

        # --------------------------------------------------------------
        # 3. Load truth observations (ref_obs) from the database. These
        #    carry the ground-truth satNo that binaryMetrics uses to
        #    classify each observation as TP/FP/FN. Column names are
        #    aliased to the camelCase form that uct_benchmark.evaluation
        #    functions expect (matches loadDataset output shape).
        # --------------------------------------------------------------
        # The ref_obs query now also pulls dso.split so we can compute
        # per-split scores below. The full ref_obs DataFrame is used for
        # the main scoring path (which produces the legacy `composite_score`
        # column); train/validation/test sub-DataFrames are used for the
        # three new per-split composite scores.
        ref_obs = db.adapter.fetchdf(
            """
            SELECT
                o.id,
                o.sat_no        AS "satNo",
                o.ob_time       AS "obTime",
                o.ra,
                o.declination,
                o.sensor_id     AS "idSensor",
                o.sensor_name   AS "sensorName",
                o.azimuth,
                o.elevation,
                o.range_km      AS range,
                o.range_rate_km_s AS "rangeRate",
                o.send_lat      AS "senderLatitude",
                o.send_long     AS "senderLongitude",
                o.send_alt      AS "senderAltitude",
                o.type_optical  AS "typeOptical",
                dso.split       AS split
            FROM observations o
            JOIN dataset_observations dso ON o.id = dso.observation_id
            WHERE dso.dataset_id = ?
            """,
            (dataset_id,),
        )

        # CTF poor calibration: apply per-sensor systematic biases to
        # ref_obs BEFORE orbit association, so the eval scores against the
        # same biased observations the participant downloaded. Without this
        # the leaderboard would compare the participant's UCTP output
        # against pristine observations that they never saw, which would
        # be unfair. Standard-quality datasets have NULL sensor_biases and
        # this block is a no-op.
        _bias_row = db.execute(
            "SELECT sensor_biases, calibration_quality FROM datasets WHERE id = ?",
            (dataset_id,),
        ).fetchone()
        sensor_biases: Dict[str, Dict[str, float]] = {}
        if _bias_row is not None:
            _raw = _bias_row[0]
            if isinstance(_raw, str):
                try:
                    sensor_biases = json.loads(_raw)
                except (ValueError, TypeError):
                    sensor_biases = {}
            elif isinstance(_raw, dict):
                sensor_biases = _raw
            if sensor_biases:
                logger.info(
                    f"Eval worker: applying {len(sensor_biases)} sensor "
                    f"biases to ref_obs for dataset {dataset_id} "
                    f"(calibration_quality={_bias_row[1]})"
                )
        if sensor_biases and not ref_obs.empty and "idSensor" in ref_obs.columns:
            # Vectorised pandas application: build a per-row arcsec offset
            # array via .map and add it to the float ra/declination columns.
            # The dict lookup is O(1) per row; total O(n_obs).
            bias_ra_deg = ref_obs["idSensor"].astype(str).map(
                lambda s: float(sensor_biases.get(s, {}).get("ra_arcsec", 0.0)) / 3600.0
            )
            bias_dec_deg = ref_obs["idSensor"].astype(str).map(
                lambda s: float(sensor_biases.get(s, {}).get("dec_arcsec", 0.0)) / 3600.0
            )
            ref_obs["ra"] = ref_obs["ra"].astype(float) + bias_ra_deg
            ref_obs["declination"] = ref_obs["declination"].astype(float) + bias_dec_deg

        # --------------------------------------------------------------
        # 4. Load non-reference observations for TN calculation.
        # --------------------------------------------------------------
        non_ref_obs = db.adapter.fetchdf(
            """
            SELECT
                observation_id AS id,
                source_norad_id,
                sensor_id,
                obs_time       AS "obTime",
                ra_deg         AS ra,
                dec_deg        AS declination
            FROM non_reference_observations
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        )
        if non_ref_obs.empty:
            non_ref_obs = None
        elif "source_norad_id" not in non_ref_obs.columns:
            non_ref_obs["source_norad_id"] = -1

        # --------------------------------------------------------------
        # 4b. Epoch sanity check. Fail fast with actionable copy if the
        #     UCTP epochs fall outside the dataset's observation window by
        #     more than 7 days — a strong signal the user uploaded a file
        #     generated for a different dataset. The outer try/except at
        #     L1175 catches and persists the message to error_message (H1).
        # --------------------------------------------------------------
        _check_epoch_sanity(ref_obs, uctp_output, tolerance_days=7)

        # --------------------------------------------------------------
        # 5. Load the reference state-vector DataFrame (ref_sv) by
        #    joining state_vectors -> dataset_references -> satellites.
        #    Propagators need mass/crossSection/dragCoeff/solarRadPressCoeff
        #    which live on the satellites table (populated during
        #    dataset generation, see Phase 1 persistence block).
        # --------------------------------------------------------------
        ref_refs = db.datasets.get_dataset_references(dataset_id)
        if ref_refs.empty:
            raise ValueError(
                f"Dataset {dataset_id} has no reference state vectors persisted. "
                f"Re-generate the dataset with the post-Phase-1 worker before "
                f"evaluating, or ask an admin to backfill dataset_references."
            )

        ref_sv = db.adapter.fetchdf(
            """
            SELECT
                sv.sat_no    AS "satNo",
                sv.epoch,
                sv.x_pos     AS xpos,
                sv.y_pos     AS ypos,
                sv.z_pos     AS zpos,
                sv.x_vel     AS xvel,
                sv.y_vel     AS yvel,
                sv.z_vel     AS zvel,
                sv.covariance AS cov_matrix,
                COALESCE(s.mass_kg,          1000.0) AS mass,
                COALESCE(s.cross_section_m2,   10.0) AS "crossSection",
                COALESCE(s.drag_coeff,          2.2) AS "dragCoeff",
                COALESCE(s.srp_coeff,           1.3) AS "solarRadPressCoeff"
            FROM state_vectors sv
            JOIN dataset_references dr ON sv.id = dr.state_vector_id
            LEFT JOIN satellites s ON sv.sat_no = s.sat_no
            WHERE dr.dataset_id = ?
            """,
            (dataset_id,),
        )
        if ref_sv.empty:
            raise ValueError(
                f"Dataset {dataset_id} has dataset_references entries but no "
                f"linked state_vectors rows. Dataset is corrupt; re-generate."
            )
        ref_sv["epoch"] = pd.to_datetime(ref_sv["epoch"])

        # Truth covariance is stored as a 21-element lower-triangular list
        # for UDL-sourced state_vectors (the Benchmarking Doc §State Vector
        # shape). monteCarloPropagator / stateMetrics need a 6x6 symmetric
        # matrix — reconstruct here via the same helper used by generateCov
        # on the submission side. Pass-through 6x6 inputs untouched.
        from uct_benchmark.utils.generateCov import _lower_triangular_to_symmetric

        def _normalize_truth_cov(raw):
            if raw is None:
                return None
            if isinstance(raw, str):
                raw = json.loads(raw)
            arr = np.asarray(raw, dtype=float)
            if arr.ndim == 2 and arr.shape == (6, 6):
                return arr.astype(np.float64)
            if arr.ndim == 1 and arr.size == 21:
                sym = _lower_triangular_to_symmetric(arr.tolist())
                if isinstance(sym, np.ndarray):
                    return sym.astype(np.float64)
                return None
            logger.warning(
                f"Unexpected truth covariance shape {arr.shape}; "
                f"setting to None for this row"
            )
            return None

        ref_sv["cov_matrix"] = ref_sv["cov_matrix"].apply(_normalize_truth_cov)

        # Force state-vector columns to float64 so downstream
        # np.random.multivariate_normal (in stateMetrics -> monteCarloPropagator)
        # doesn't hit "Cannot cast ufunc 'add' output from dtype('O')".
        for _col in ("xpos", "ypos", "zpos", "xvel", "yvel", "zvel"):
            if _col in ref_sv.columns:
                ref_sv[_col] = pd.to_numeric(ref_sv[_col], errors="coerce").astype(
                    np.float64
                )

        job_manager.update_job(job_id, progress=40)

        # --------------------------------------------------------------
        # 6. Orbit association (mirrors Evaluation.py:82-84).
        #    Uses ephemerisPropagator to propagate each reference state
        #    forward to the candidate epoch before computing the L2
        #    vector distance for the linear_sum_assignment cost matrix.
        # --------------------------------------------------------------
        associated_orbits, association_results, nonassociated_orbits = orbitAssociation(
            ref_sv, uctp_output, ephemerisPropagator
        )
        job_manager.update_job(job_id, progress=55)

        # --------------------------------------------------------------
        # 7. Binary metrics (mirrors Evaluation.py:88-90).
        #    binaryMetrics returns a single-row pd.DataFrame; flatten to
        #    dict so the existing INSERT code can .get() fields.
        # --------------------------------------------------------------
        reference_satellites = ref_sv["satNo"].unique().tolist()
        binary_df = binaryMetrics(
            ref_obs,
            associated_orbits,
            non_ref_observations=non_ref_obs,
            reference_satellites=reference_satellites,
        )
        binary_results: Dict[str, Any] = (
            binary_df.iloc[0].to_dict() if len(binary_df) > 0 else {}
        )
        job_manager.update_job(job_id, progress=70)

        # --------------------------------------------------------------
        # 8. State metrics (mirrors Evaluation.py:94). stateMetrics
        #    returns a per-satellite DataFrame; aggregate position and
        #    velocity errors via flat RMS across satellites, and average
        #    Mahalanobis distance (per Louis Feb 19 "states are off").
        # --------------------------------------------------------------
        state_df = stateMetrics(ref_sv, associated_orbits, monteCarloPropagator)
        if state_df is None or state_df.empty:
            state_results: Dict[str, Any] = {
                "position_rms_km": 0.0,
                "velocity_rms_km_s": 0.0,
                "mahalanobis_distance": None,
                "per_satellite": [],
            }
        else:
            pos_err = state_df.get("Position Error Norm", pd.Series(dtype=float)).fillna(0)
            vel_err = state_df.get("Velocity Error Norm", pd.Series(dtype=float)).fillna(0)
            md_series = state_df.get("Mahalanobis Distance")
            md_mean = (
                float(md_series.mean())
                if md_series is not None and md_series.notna().any()
                else None
            )
            # Anonymize per-satellite breakdown: replace NORAD IDs with
            # sequential labels so the results endpoint never leaks the
            # answer key (per Louis, Apr 9 2026: "we don't ever give the
            # answer key away"). Users see "Satellite 1", "Satellite 2" etc.
            state_df_anon = state_df.copy()
            if "satNo" in state_df_anon.columns:
                sat_ids = state_df_anon["satNo"].unique()
                anon_map = {sat: f"Satellite {i+1}" for i, sat in enumerate(sat_ids)}
                state_df_anon["satNo"] = state_df_anon["satNo"].map(anon_map)

            state_results = {
                "position_rms_km": float(np.sqrt(np.mean(pos_err.values ** 2))),
                "velocity_rms_km_s": float(np.sqrt(np.mean(vel_err.values ** 2))),
                "mahalanobis_distance": md_mean,
                "per_satellite": _convert_numpy_to_native(
                    state_df_anon.to_dict(orient="records")
                ),
            }
        job_manager.update_job(job_id, progress=85)

        # --------------------------------------------------------------
        # 9. Residual metrics (mirrors Evaluation.py:99). residualMetrics
        #    produces a per-state RMSE of great-circle residuals in
        #    arcseconds; aggregate via flat RMS of those RMSEs.
        # --------------------------------------------------------------
        residual_rms_arcsec: Optional[float] = None
        try:
            residual_df = residualMetrics(
                ref_obs, associated_orbits, ephemerisPropagator, True
            )
            if residual_df is not None and not residual_df.empty and "RMSE" in residual_df.columns:
                rms_values = residual_df["RMSE"].dropna().astype(float)
                if len(rms_values) > 0:
                    residual_rms_arcsec = float(
                        np.sqrt(np.mean(rms_values.values ** 2))
                    )
        except Exception as res_err:
            logger.warning(
                f"Residual metrics failed for submission {submission_id}: {res_err}. "
                f"Composite score will fall back to binary+state only."
            )
        job_manager.update_job(job_id, progress=92)

        # --------------------------------------------------------------
        # 10. Assemble raw_results_payload with per-satellite breakdown
        #     and histograms for the frontend ResultsPage visualisations.
        # --------------------------------------------------------------
        raw_results_payload: Dict[str, Any] = {
            "binary": _convert_numpy_to_native(binary_results),
            "state": _convert_numpy_to_native(state_results),
            "residual": {"residual_rms_arcsec": residual_rms_arcsec},
            "association": _convert_numpy_to_native(association_results),
        }

        try:
            position_errors: list = []
            per_sat = state_results.get("per_satellite", [])
            if isinstance(per_sat, list):
                for rec in per_sat:
                    pe = rec.get("Position Error Norm") if isinstance(rec, dict) else None
                    if pe is not None and not pd.isna(pe):
                        position_errors.append(float(pe))
            if position_errors:
                pe_arr = np.array(position_errors)
                pe_bins = [0, 1, 2, 3, 4, 5, float("inf")]
                pe_hist, _ = np.histogram(pe_arr, bins=pe_bins)
                raw_results_payload["position_error_histogram"] = {
                    "labels": ["0-1", "1-2", "2-3", "3-4", "4-5", "5+"],
                    "counts": pe_hist.tolist(),
                }
        except Exception as hist_err:
            logger.debug(f"Histogram generation skipped: {hist_err}")

        # --------------------------------------------------------------
        # 11. Composite score: weighted combination of binary + state +
        #     residual components. Feeds compute_composite_score which
        #     returns a breakdown dict (see Phase 3). The scalar float
        #     lands in submission_results.composite_score; the full
        #     breakdown lands in raw_results["composite_breakdown"].
        # --------------------------------------------------------------
        _f1 = binary_results.get("f1_score", binary_results.get("F1Score"))
        _pos_rms = state_results.get("position_rms_km")
        _mahalanobis = state_results.get("mahalanobis_distance")
        composite_breakdown = compute_composite_score(
            _f1, _pos_rms, residual_rms_arcsec, mahalanobis_distance=_mahalanobis
        )
        composite_score = composite_breakdown["composite_score"]
        raw_results_payload["composite_breakdown"] = composite_breakdown
        logger.info(
            f"Composite score for submission {submission_id}: "
            f"{composite_score:.4f} "
            f"(binary={composite_breakdown.get('binary_component')}, "
            f"state={composite_breakdown.get('state_component')}, "
            f"residual={composite_breakdown.get('residual_component')})"
        )

        # ----------------------------------------------------------------
        # 11b. Per-split composite scores (CTF train/validation/test).
        #
        # The legacy `composite_score` above is computed against the entire
        # dataset and stays in the response for backward compat. The three
        # new sub-scores are computed against the train/validation/test
        # partitions of ref_obs respectively. Orbit association is shared
        # across all splits because it's a property of the UCTP output, not
        # of the truth split — so we just re-run the metrics math against
        # each ref_obs subset.
        #
        # The leaderboard ranks by `test_composite_score` (Phase 5),
        # because the test split is the only one whose answers the
        # participant could not have downloaded.
        # ----------------------------------------------------------------
        def _score_one_split(
            split_name: str, ref_obs_split: pd.DataFrame
        ) -> Dict[str, Any] | None:
            """Compute a composite score against a single split's truth."""
            if ref_obs_split is None or ref_obs_split.empty:
                logger.info(
                    f"Split '{split_name}' has zero ref_obs rows; "
                    f"composite_score will be None."
                )
                return None
            try:
                split_binary_df = binaryMetrics(
                    ref_obs_split,
                    associated_orbits,
                    non_ref_observations=non_ref_obs,
                    reference_satellites=ref_obs_split["satNo"].unique().tolist(),
                )
                split_binary = (
                    split_binary_df.iloc[0].to_dict()
                    if len(split_binary_df) > 0
                    else {}
                )
                split_f1 = split_binary.get(
                    "f1_score", split_binary.get("F1Score", 0.0)
                )

                # State metrics over the satellites that appear in this split.
                split_sats = ref_obs_split["satNo"].unique().tolist()
                split_state_df = stateMetrics(
                    ref_sv[ref_sv["satNo"].isin(split_sats)],
                    associated_orbits[
                        associated_orbits["satNo"].isin(split_sats)
                    ]
                    if "satNo" in associated_orbits.columns
                    else associated_orbits,
                    monteCarloPropagator,
                )
                if split_state_df is None or split_state_df.empty:
                    split_pos_rms = 0.0
                    split_md = None
                else:
                    split_pos_err = split_state_df.get(
                        "Position Error Norm", pd.Series(dtype=float)
                    ).fillna(0)
                    split_pos_rms = float(
                        np.sqrt(np.mean(split_pos_err.values ** 2))
                    )
                    split_md_series = split_state_df.get("Mahalanobis Distance")
                    split_md = (
                        float(split_md_series.mean())
                        if split_md_series is not None
                        and split_md_series.notna().any()
                        else None
                    )

                # Residual metrics restricted to this split's truth obs.
                split_residual_rms: Optional[float] = None
                try:
                    split_residual_df = residualMetrics(
                        ref_obs_split,
                        associated_orbits,
                        ephemerisPropagator,
                        True,
                    )
                    if (
                        split_residual_df is not None
                        and not split_residual_df.empty
                        and "RMSE" in split_residual_df.columns
                    ):
                        rms_vals = (
                            split_residual_df["RMSE"].dropna().astype(float)
                        )
                        if len(rms_vals) > 0:
                            split_residual_rms = float(
                                np.sqrt(np.mean(rms_vals.values ** 2))
                            )
                except Exception as res_err:
                    logger.warning(
                        f"Residual metrics failed for split '{split_name}' "
                        f"of submission {submission_id}: {res_err}"
                    )

                split_breakdown = compute_composite_score(
                    split_f1,
                    split_pos_rms,
                    split_residual_rms,
                    mahalanobis_distance=split_md,
                )
                logger.info(
                    f"Split '{split_name}' composite for submission "
                    f"{submission_id}: {split_breakdown['composite_score']:.4f} "
                    f"(n_obs={len(ref_obs_split)})"
                )
                return split_breakdown
            except Exception as e:
                logger.warning(
                    f"Per-split scoring failed for split '{split_name}' of "
                    f"submission {submission_id}: {e}"
                )
                return None

        # The split column may or may not be present depending on whether
        # the dataset was generated post-Phase-2. Default everything to
        # train if missing so legacy datasets still produce a value.
        if "split" not in ref_obs.columns:
            ref_obs["split"] = "train"

        train_breakdown = _score_one_split(
            "train", ref_obs[ref_obs["split"] == "train"]
        )
        val_breakdown = _score_one_split(
            "validation", ref_obs[ref_obs["split"] == "validation"]
        )
        test_breakdown = _score_one_split(
            "test", ref_obs[ref_obs["split"] == "test"]
        )

        train_composite = (
            train_breakdown["composite_score"] if train_breakdown else None
        )
        val_composite = (
            val_breakdown["composite_score"] if val_breakdown else None
        )
        test_composite = (
            test_breakdown["composite_score"] if test_breakdown else None
        )

        raw_results_payload["split_breakdowns"] = {
            "train": train_breakdown,
            "validation": val_breakdown,
            "test": test_breakdown,
        }

        # Store results in database (upsert to handle re-evaluation gracefully).
        # Persists mahalanobis_distance, ra_residual_rms_arcsec (slotting the
        # single great-circle residual here until the phantom dec column is
        # reshaped per BACKLOG.md section E).
        db.execute(
            """
            INSERT INTO submission_results (
                submission_id,
                true_positives,
                true_negatives,
                false_positives,
                false_negatives,
                precision,
                recall,
                f1_score,
                specificity,
                accuracy,
                position_rms_km,
                velocity_rms_km_s,
                mahalanobis_distance,
                ra_residual_rms_arcsec,
                dec_residual_rms_arcsec,
                raw_results,
                composite_score,
                train_composite_score,
                val_composite_score,
                test_composite_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (submission_id) DO UPDATE SET
                true_positives = EXCLUDED.true_positives,
                true_negatives = EXCLUDED.true_negatives,
                false_positives = EXCLUDED.false_positives,
                false_negatives = EXCLUDED.false_negatives,
                precision = EXCLUDED.precision,
                recall = EXCLUDED.recall,
                f1_score = EXCLUDED.f1_score,
                specificity = EXCLUDED.specificity,
                accuracy = EXCLUDED.accuracy,
                position_rms_km = EXCLUDED.position_rms_km,
                velocity_rms_km_s = EXCLUDED.velocity_rms_km_s,
                mahalanobis_distance = EXCLUDED.mahalanobis_distance,
                ra_residual_rms_arcsec = EXCLUDED.ra_residual_rms_arcsec,
                dec_residual_rms_arcsec = EXCLUDED.dec_residual_rms_arcsec,
                raw_results = EXCLUDED.raw_results,
                composite_score = EXCLUDED.composite_score,
                train_composite_score = EXCLUDED.train_composite_score,
                val_composite_score = EXCLUDED.val_composite_score,
                test_composite_score = EXCLUDED.test_composite_score
            """,
            (
                submission_id,
                int(binary_results.get("true_positives", binary_results.get("TruePositives", 0)) or 0),
                int(binary_results.get("true_negatives", binary_results.get("TrueNegatives", 0)) or 0),
                int(binary_results.get("false_positives", binary_results.get("FalsePositives", 0)) or 0),
                int(binary_results.get("false_negatives", binary_results.get("FalseNegatives", 0)) or 0),
                float(binary_results.get("precision", binary_results.get("Precision", 0.0)) or 0.0),
                float(binary_results.get("recall", binary_results.get("Sensitivity", 0.0)) or 0.0),
                float(binary_results.get("f1_score", binary_results.get("F1Score", 0.0)) or 0.0),
                float(binary_results.get("specificity", binary_results.get("Specificity", 0.0)) or 0.0),
                float(binary_results.get("accuracy", binary_results.get("Accuracy", 0.0)) or 0.0),
                float(state_results.get("position_rms_km", 0.0) or 0.0),
                float(state_results.get("velocity_rms_km_s", 0.0) or 0.0),
                state_results.get("mahalanobis_distance"),
                residual_rms_arcsec,
                None,  # dec_residual_rms_arcsec: phantom column; single great-circle is stored in the ra slot
                json.dumps(_convert_numpy_to_native(raw_results_payload)),
                composite_score,
                train_composite,
                val_composite,
                test_composite,
            ),
        )

        # Update submission status
        db.execute(
            """
            UPDATE submissions
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (submission_id,),
        )

        # Complete job
        result = {
            "submission_id": submission_id,
            "binary_metrics": binary_results,
            "state_metrics": state_results,
        }

        # Convert numpy arrays to native Python types for JSON serialization
        result = _convert_numpy_to_native(result)
        job_manager.complete_job(job_id, result)
        logger.info(f"Evaluation completed for job {job_id}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Evaluation failed for job {job_id}: {error_msg}")
        logger.debug(traceback.format_exc())

        # Update submission status to failed
        try:
            from backend_api.database import get_db

            db = get_db()
            db.execute(
                "UPDATE submissions SET status = 'failed' WHERE id = ?",
                (submission_id,),
            )
        except Exception as db_error:
            # Log the secondary failure - this is critical as the submission will be stuck
            logger.error(
                f"CRITICAL: Failed to mark submission {submission_id} as failed: {db_error}. "
                "Submission may be stuck in 'processing' state."
            )
            # Include in error message so it's visible in job status
            error_msg = f"{error_msg} [DB update also failed: {db_error}]"

        job_manager.fail_job(job_id, error_msg)


def submit_dataset_generation(
    dataset_id: int,
    config: Dict[str, Any],
    udl_token: str,
    esa_token: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Job:
    """
    Submit a dataset generation job to run in the background.

    Args:
        dataset_id: The database ID for the dataset
        config: Dataset generation configuration
        udl_token: User's UDL API token (passed as arg, never stored in job metadata)
        esa_token: User's ESA API token (optional)
        user_id: Owner user ID for job ownership tracking

    Returns:
        The created Job instance
    """
    job_manager = get_job_manager()
    job = job_manager.create_job(
        JobType.DATASET_GENERATION,
        metadata={"dataset_id": dataset_id, "config": config, "user_id": user_id},
    )

    executor = get_executor()
    executor.submit(run_dataset_generation, job.id, dataset_id, config, udl_token, esa_token)

    return job


def submit_evaluation(
    submission_id: int,
    dataset_id: int,
    file_path: str,
    user_id: Optional[str] = None,
) -> Job:
    """
    Submit an evaluation job to run in the background.

    Args:
        submission_id: The database ID for the submission
        dataset_id: The dataset ID to evaluate against
        file_path: Path to the uploaded results file
        user_id: Owner user ID for job ownership tracking

    Returns:
        The created Job instance
    """
    job_manager = get_job_manager()
    job = job_manager.create_job(
        JobType.EVALUATION,
        metadata={
            "submission_id": submission_id,
            "dataset_id": dataset_id,
            "file_path": file_path,
            "user_id": user_id,
        },
    )

    executor = get_executor()
    executor.submit(run_evaluation_pipeline, job.id, submission_id, dataset_id, file_path)

    return job


# ============================================================
# Event Detection Worker
# ============================================================


def run_event_detection(
    job_id: str,
    sat_nos: list,
    time_window_start: "datetime",
    time_window_end: "datetime",
    detector_types: list,
) -> None:
    """
    Worker function for event detection.

    Runs in a background thread. Instantiates the requested detectors,
    runs the LabellingPipeline, persists results, and updates job progress.

    Args:
        job_id: The job ID to update progress
        sat_nos: List of NORAD IDs to analyze
        time_window_start: Start of analysis window
        time_window_end: End of analysis window
        detector_types: List of detector type strings (launch, maneuver, proximity, breakup)
    """
    from datetime import datetime

    job_manager = get_job_manager()
    job_manager.start_job(job_id)

    try:
        from backend_api.database import get_db
        from uct_benchmark.database.repository import ObservationRepository
        from uct_benchmark.labelling.pipeline import LabellingPipeline
        from uct_benchmark.labelling.launch_detection import LaunchDetector
        from uct_benchmark.labelling.maneuver_detection import ManeuverDetector
        from uct_benchmark.labelling.proximity_detection import ProximityDetector
        from uct_benchmark.labelling.breakup_detection import BreakupDetector

        db = get_db()
        if db is None:
            raise RuntimeError("Database not available")

        job_manager.update_job(job_id, progress=10, stage="Fetching observations")

        # Fetch observations for the specified satellites and time window
        obs_repo = ObservationRepository(db)
        observations_df = obs_repo.get_by_time_window(
            start_time=time_window_start,
            end_time=time_window_end,
        )

        # Filter to requested satellites if specified
        if sat_nos:
            observations_df = observations_df[observations_df["sat_no"].isin(sat_nos)]

        if observations_df.empty:
            job_manager.complete_job(job_id, result={
                "events_detected": 0,
                "message": "No observations found for the specified parameters",
            })
            return

        job_manager.update_job(
            job_id, progress=25,
            stage=f"Initializing detectors ({len(observations_df)} observations)",
        )

        # Build detector list based on requested types
        detector_map = {
            "launch": LaunchDetector,
            "maneuver": ManeuverDetector,
            "proximity": ProximityDetector,
            "breakup": BreakupDetector,
        }
        detectors = []
        for dt in detector_types:
            cls = detector_map.get(dt)
            if cls:
                detectors.append(cls())

        if not detectors:
            raise ValueError(f"No valid detectors for types: {detector_types}")

        job_manager.update_job(
            job_id, progress=40,
            stage=f"Running {len(detectors)} detectors",
        )

        # Run the pipeline
        pipeline = LabellingPipeline(
            detectors=detectors,
            dataset_id=f"detection_job_{job_id}",
        )

        time_window = (time_window_start, time_window_end)
        labelled_dataset = pipeline.run(observations_df, time_window)

        job_manager.update_job(
            job_id, progress=80,
            stage=f"Persisting {len(labelled_dataset.event_labels)} events",
        )

        # Persist to database
        created_count = pipeline.persist(labelled_dataset, db)

        summary = labelled_dataset.summary()
        job_manager.complete_job(job_id, result={
            "events_detected": summary["total_events"],
            "events_persisted": created_count,
            "events_by_type": summary["events_by_type"],
            "events_by_confidence": summary["events_by_confidence"],
            "observations_analyzed": len(observations_df),
            "satellites_analyzed": observations_df["sat_no"].nunique(),
        })

        logger.info(
            f"Event detection job {job_id} completed: "
            f"{created_count} events persisted"
        )

    except Exception as exc:
        error_msg = f"Event detection failed: {exc}"
        logger.error(f"Job {job_id}: {error_msg}")
        logger.debug(traceback.format_exc())
        job_manager.fail_job(job_id, error_msg)


def submit_event_detection(
    sat_nos: list,
    time_window_start: "datetime",
    time_window_end: "datetime",
    detector_types: list,
    user_id: Optional[str] = None,
) -> Job:
    """
    Submit an event detection job to run in the background.

    Args:
        sat_nos: List of NORAD IDs to analyze
        time_window_start: Start of analysis window
        time_window_end: End of analysis window
        detector_types: Detector types to run
        user_id: Owner user ID for job ownership tracking

    Returns:
        The created Job instance
    """
    job_manager = get_job_manager()
    job = job_manager.create_job(
        JobType.EVENT_DETECTION,
        metadata={
            "sat_nos": sat_nos,
            "time_window_start": time_window_start.isoformat(),
            "time_window_end": time_window_end.isoformat(),
            "detector_types": detector_types,
            "user_id": user_id,
        },
    )

    executor = get_executor()
    executor.submit(
        run_event_detection,
        job.id,
        sat_nos,
        time_window_start,
        time_window_end,
        detector_types,
    )

    return job
