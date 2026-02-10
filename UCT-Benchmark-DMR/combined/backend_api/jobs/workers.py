"""
Background workers for executing long-running tasks.

Provides worker functions for dataset generation and evaluation
that run in a ThreadPoolExecutor.

Note: Dataset ID is now passed to generateDataset to avoid duplicate creation.
"""

import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from loguru import logger

from . import Job, JobType, get_job_manager
from .progress import DatasetStage, create_job_progress_callback


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
    """
    job_manager = get_job_manager()
    job_manager.start_job(job_id)

    try:
        # Import here to avoid circular imports and ensure Orekit is initialized
        import random

        from backend_api.database import get_db
        from uct_benchmark.api.apiIntegration import generateDataset
        from uct_benchmark.settings import satIDs as DEFAULT_SATELLITES

        # Get tokens from environment
        udl_token = os.getenv("UDL_TOKEN")
        esa_token = os.getenv("ESA_TOKEN")

        if not udl_token:
            raise ValueError(
                "Missing required environment variable: UDL_TOKEN. "
                "Please set it in your .env file."
            )
        if not esa_token:
            logger.warning(
                "ESA_TOKEN not set - Discosweb data (mass/crossSection) will be unavailable. "
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

        # Get satellite list from config or auto-select
        satellites = config.get("satellites", [])
        object_count = config.get("object_count", 5)

        if not satellites:
            # Auto-select satellites from the default calibration list
            # Use object_count to determine how many to select
            available_sats = list(DEFAULT_SATELLITES)
            random.shuffle(available_sats)
            satellites = available_sats[: min(object_count, len(available_sats))]
            logger.info(f"Auto-selected {len(satellites)} satellites: {satellites}")

        timeframe = config.get("timeframe", 7)
        timeunit = config.get("timeunit", "days")

        # Parse start_date and end_date if provided
        # These should be in ISO format (YYYY-MM-DD or full ISO datetime)
        end_time = "now"  # Default to current time
        start_date_str = config.get("start_date")
        end_date_str = config.get("end_date")

        if end_date_str:
            from datetime import datetime

            try:
                # Parse end_date - handle both date-only and full datetime formats
                if "T" in end_date_str:
                    end_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                else:
                    # Date only - set to end of day
                    end_time = datetime.fromisoformat(end_date_str + "T23:59:59")
                logger.info(f"Using end_date from config: {end_time}")

                # If both dates provided, calculate timeframe from them
                if start_date_str:
                    if "T" in start_date_str:
                        start_time = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                    else:
                        start_time = datetime.fromisoformat(start_date_str + "T00:00:00")
                    # Calculate timeframe in days
                    delta = end_time - start_time
                    timeframe = max(1, delta.days)
                    timeunit = "days"
                    logger.info(f"Calculated timeframe from dates: {timeframe} {timeunit}")
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

        # Get regime from config (used for windowed strategy)
        regime = config.get("regime", "LEO")

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
            use_database=True,
            dataset_name=config.get("name"),
            downsample_config=downsample_config,
            simulation_config=simulation_config,
            tier=tier,
            dataset_id=dataset_id,
            progress_callback=progress_callback,
            search_strategy=search_strategy,
            window_size_minutes=window_size_minutes,
            regime=regime,
        )

        # Update progress - persisting to database
        progress_callback(DatasetStage.PERSISTING_DATABASE, 0.0)

        # Update dataset record in database
        db = get_db()
        observation_count = len(dataset_obs) if dataset_obs is not None else 0
        satellite_count = len(actual_sats) if actual_sats is not None else 0

        # Calculate coverage as ratio of satellites with full data vs requested
        requested_count = len(satellites)
        avg_coverage = (satellite_count / requested_count) if requested_count > 0 else 0.0

        # Estimate size in bytes (approx 500 bytes per observation as JSON)
        estimated_size_bytes = observation_count * 500

        # Update the dataset status with all metrics
        db.execute(
            """
            UPDATE datasets
            SET status = 'available',
                observation_count = ?,
                satellite_count = ?,
                avg_coverage = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (observation_count, satellite_count, avg_coverage, dataset_id),
        )

        # Link observations to dataset if we have observation data
        # NOTE: This is a CRITICAL step - if linking fails, the dataset is unusable
        progress_callback(DatasetStage.PERSISTING_DATABASE, 0.5)
        logger.info(f"[WORKER] About to link observations for dataset {dataset_id}")
        if obs_truth is not None and not obs_truth.empty and "id" in obs_truth.columns:
            obs_ids = obs_truth["id"].tolist()
            track_assignments = {}
            if "trackId" in obs_truth.columns:
                import pandas as pd

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
            # Don't catch exceptions here - linking failure should fail the entire job
            # A dataset without linked observations is corrupted and unusable
            db.datasets.add_observations_to_dataset(dataset_id, obs_ids, track_assignments)
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
                logger.debug(f"Rollback not needed or failed: {rollback_error}")
            db.execute(
                "UPDATE datasets SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (dataset_id,),
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

        # Compute binary metrics (TP, FP, FN, precision, recall, F1)
        binary_results = (
            binaryMetrics(associations)
            if associations
            else {
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
            }
        )

        job_manager.update_job(job_id, progress=80)

        # Compute state metrics (position/velocity RMS for true positives)
        state_results = {
            "position_rms_km": 0.0,
            "velocity_rms_km_s": 0.0,
        }

        if associations:
            state_results = stateMetrics(associations) or state_results

        job_manager.update_job(job_id, progress=90)

        # Store results in database
        db.execute(
            """
            INSERT INTO submission_results (
                submission_id,
                true_positives,
                false_positives,
                false_negatives,
                precision,
                recall,
                f1_score,
                position_rms_km,
                velocity_rms_km_s,
                raw_results
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                submission_id,
                binary_results.get("true_positives", 0),
                binary_results.get("false_positives", 0),
                binary_results.get("false_negatives", 0),
                binary_results.get("precision", 0.0),
                binary_results.get("recall", 0.0),
                binary_results.get("f1_score", 0.0),
                state_results.get("position_rms_km", 0.0),
                state_results.get("velocity_rms_km_s", 0.0),
                json.dumps({"binary": binary_results, "state": state_results}),
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
) -> Job:
    """
    Submit a dataset generation job to run in the background.

    Args:
        dataset_id: The database ID for the dataset
        config: Dataset generation configuration

    Returns:
        The created Job instance
    """
    job_manager = get_job_manager()
    job = job_manager.create_job(
        JobType.DATASET_GENERATION,
        metadata={"dataset_id": dataset_id, "config": config},
    )

    executor = get_executor()
    executor.submit(run_dataset_generation, job.id, dataset_id, config)

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
