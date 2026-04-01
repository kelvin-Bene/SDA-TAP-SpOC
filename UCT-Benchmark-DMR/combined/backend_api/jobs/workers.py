"""
Background workers for executing long-running tasks.

Provides worker functions for dataset generation and evaluation
that run in a ThreadPoolExecutor.

Note: Dataset ID is now passed to generateDataset to avoid duplicate creation.
"""

import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from loguru import logger

from . import Job, JobType, get_job_manager
from .progress import DatasetStage, create_job_progress_callback

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


# Global thread pool for background tasks
_executor: Optional[ThreadPoolExecutor] = None


def get_executor() -> ThreadPoolExecutor:
    """Get or create the global thread pool executor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="worker")
    return _executor


def shutdown_executor() -> None:
    """Shutdown the thread pool executor."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False)
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
            # Wrap linking in try/except: if linking fails, clean up orphaned observations
            try:
                db.datasets.add_observations_to_dataset(dataset_id, obs_ids, track_assignments)
            except Exception as link_err:
                logger.error(f"Failed to link observations to dataset {dataset_id}: {link_err}. Rolling back inserted observations.")
                try:
                    placeholders = ",".join(["%s"] * len(obs_ids))
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
                db._connection.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback not needed or failed: {rollback_error}")
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
        from backend_api.database import get_db
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics
        from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
        from uct_benchmark.evaluation.stateMetrics import stateMetrics

        job_manager.update_job(job_id, progress=10)

        db = get_db()

        # Load dataset from database
        dataset_row = db.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()

        if not dataset_row:
            raise ValueError(f"Dataset {dataset_id} not found")

        job_manager.update_job(job_id, progress=20)

        # Load the submission file (UCTP output)
        with open(file_path, "r") as f:
            submission_data = json.load(f)

        # Normalize field names in submission to canonical forms
        # This handles different UCTP naming conventions (e.g., VX vs xvel, sourcedData vs grouped_ops)
        from uct_benchmark.utils.field_mapping import normalize_submission, validate_required_fields
        if isinstance(submission_data, list):
            submission_data = normalize_submission(submission_data)

            # Validate required fields on the first record to catch bad submissions early
            if submission_data:
                missing = validate_required_fields(submission_data[0])
                if missing:
                    raise ValueError(
                        f"Submission is missing required UCTP fields: {', '.join(missing)}. "
                        f"Expected fields: grouped_ops, epoch, xpos, ypos, zpos, xvel, yvel, zvel"
                    )

        job_manager.update_job(job_id, progress=30)

        # Get reference data from database
        # This would load the truth observations and states for comparison
        observations = db.adapter.fetchdf(
            """
            SELECT o.* FROM observations o
            JOIN dataset_observations dso ON o.id = dso.observation_id
            WHERE dso.dataset_id = ?
            """,
            (dataset_id,),
        )

        # Load non-reference observations for True Negative calculation
        non_ref_obs_df = db.adapter.fetchdf(
            """
            SELECT
                observation_id as id,
                source_norad_id,
                sensor_id,
                obs_time,
                ra_deg as ra,
                dec_deg as declination
            FROM non_reference_observations
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        )

        # Get reference satellite set from dataset
        reference_satellites = observations["sat_no"].unique().tolist() if not observations.empty else []

        job_manager.update_job(job_id, progress=40)

        # Run orbit association
        # The submission_data should contain predicted track/object assignments
        # compared against the truth from the dataset
        associations = (
            orbitAssociation(
                submission_data.get("predictions", []),
                observations,
            )
            if "predictions" in submission_data
            else {}
        )

        job_manager.update_job(job_id, progress=60)

        # Compute binary metrics (TP, FP, FN, TN, precision, recall, F1)
        # Pass non-reference observations for True Negative calculation
        if associations:
            binary_results = binaryMetrics(
                associations,
                non_ref_obs_df=non_ref_obs_df if not non_ref_obs_df.empty else None,
                reference_satellites=reference_satellites,
            )
        else:
            binary_results = {
                "true_positives": 0,
                "true_negatives": 0,
                "false_positives": 0,
                "false_negatives": 0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "accuracy": 0.0,
                "specificity": 0.0,
            }

        job_manager.update_job(job_id, progress=80)

        # Compute state metrics (position/velocity RMS for true positives)
        state_results = {
            "position_rms_km": 0.0,
            "velocity_rms_km_s": 0.0,
        }

        if associations:
            state_results = stateMetrics(associations) or state_results

        job_manager.update_job(job_id, progress=90)

        # Build enriched raw_results with histogram data for visualization
        raw_results_payload: Dict[str, Any] = {
            "binary": binary_results,
            "state": state_results,
        }

        # Extract residual and position error arrays for histogram visualization
        # These come from the state metrics or associations if available
        if associations:
            try:
                import numpy as np

                # Collect per-satellite position errors for histogram
                position_errors: list[float] = []
                ra_residuals: list[float] = []
                dec_residuals: list[float] = []

                per_satellite = state_results.get("per_satellite", {})
                for sat_id, sat_data in per_satellite.items():
                    if isinstance(sat_data, dict):
                        pe = sat_data.get("position_error_km")
                        if pe is not None:
                            position_errors.append(float(pe))
                        ra_res = sat_data.get("ra_residual_arcsec")
                        dec_res = sat_data.get("dec_residual_arcsec")
                        if ra_res is not None:
                            ra_residuals.append(float(ra_res))
                        if dec_res is not None:
                            dec_residuals.append(float(dec_res))

                # Bin position errors: [0-1, 1-2, 2-3, 3-4, 4-5, 5+] km
                if position_errors:
                    pe_arr = np.array(position_errors)
                    pe_bins = [0, 1, 2, 3, 4, 5, float("inf")]
                    pe_hist, _ = np.histogram(pe_arr, bins=pe_bins)
                    raw_results_payload["position_error_histogram"] = {
                        "labels": ["0-1", "1-2", "2-3", "3-4", "4-5", "5+"],
                        "counts": pe_hist.tolist(),
                    }

                # Bin residuals in sigma units: [-3, -2, -1, 0, 1, 2, 3]
                for name, vals in [("ra_residual_histogram", ra_residuals),
                                   ("dec_residual_histogram", dec_residuals)]:
                    if vals:
                        arr = np.array(vals)
                        rms = float(np.sqrt(np.mean(arr ** 2))) or 1.0
                        sigma_vals = arr / rms
                        bins_edges = [-np.inf, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, np.inf]
                        hist, _ = np.histogram(sigma_vals, bins=bins_edges)
                        raw_results_payload[name] = {
                            "labels": ["-3", "-2", "-1", "0", "1", "2", "3"],
                            "counts": hist.tolist(),
                        }

                raw_results_payload["per_satellite"] = per_satellite
            except Exception as hist_err:
                logger.debug(f"Histogram generation skipped: {hist_err}")

        # Store results in database
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
                raw_results
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                submission_id,
                binary_results.get("true_positives", binary_results.get("TruePositives", 0)),
                binary_results.get("true_negatives", binary_results.get("TrueNegatives", 0)),
                binary_results.get("false_positives", binary_results.get("FalsePositives", 0)),
                binary_results.get("false_negatives", binary_results.get("FalseNegatives", 0)),
                binary_results.get("precision", binary_results.get("Precision", 0.0)),
                binary_results.get("recall", binary_results.get("Sensitivity", 0.0)),
                binary_results.get("f1_score", binary_results.get("F1Score", 0.0)),
                binary_results.get("specificity", binary_results.get("Specificity", 0.0)),
                binary_results.get("accuracy", binary_results.get("Accuracy", 0.0)),
                state_results.get("position_rms_km", 0.0),
                state_results.get("velocity_rms_km_s", 0.0),
                json.dumps(raw_results_payload),
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
) -> Job:
    """
    Submit a dataset generation job to run in the background.

    Args:
        dataset_id: The database ID for the dataset
        config: Dataset generation configuration
        udl_token: User's UDL API token (passed as arg, never stored in job metadata)
        esa_token: User's ESA API token (optional)

    Returns:
        The created Job instance
    """
    job_manager = get_job_manager()
    job = job_manager.create_job(
        JobType.DATASET_GENERATION,
        metadata={"dataset_id": dataset_id, "config": config},
    )

    executor = get_executor()
    executor.submit(run_dataset_generation, job.id, dataset_id, config, udl_token, esa_token)

    return job


def submit_evaluation(
    submission_id: int,
    dataset_id: int,
    file_path: str,
) -> Job:
    """
    Submit an evaluation job to run in the background.

    Args:
        submission_id: The database ID for the submission
        dataset_id: The dataset ID to evaluate against
        file_path: Path to the uploaded results file

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
        },
    )

    executor = get_executor()
    executor.submit(run_evaluation_pipeline, job.id, submission_id, dataset_id, file_path)

    return job
