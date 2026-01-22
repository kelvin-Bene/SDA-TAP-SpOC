"""
Background workers for executing long-running tasks.

Provides worker functions for dataset generation and evaluation
that run in a ThreadPoolExecutor.
"""

import os
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from . import Job, JobManager, JobStatus, JobType, get_job_manager


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
        from uct_benchmark.api.apiIntegration import generateDataset
        from uct_benchmark.settings import satIDs as DEFAULT_SATELLITES
        from backend_api.database import get_db
        import random

        # Get tokens from environment
        udl_token = os.getenv("UDL_TOKEN")
        esa_token = os.getenv("ESA_TOKEN")

        if not udl_token or not esa_token:
            raise ValueError(
                "Missing required environment variables: UDL_TOKEN and ESA_TOKEN. "
                "Please set these in your .env file."
            )

        # Update progress - starting
        job_manager.update_job(job_id, progress=10)

        # Get satellite list from config or auto-select
        satellites = config.get("satellites", [])
        object_count = config.get("object_count", 5)

        if not satellites:
            # Auto-select satellites from the default calibration list
            # Use object_count to determine how many to select
            available_sats = list(DEFAULT_SATELLITES)
            random.shuffle(available_sats)
            satellites = available_sats[:min(object_count, len(available_sats))]
            logger.info(f"Auto-selected {len(satellites)} satellites: {satellites}")

        timeframe = config.get("timeframe", 7)
        timeunit = config.get("timeunit", "days")

        # Update progress - calling API
        job_manager.update_job(job_id, progress=20)

        logger.info(
            f"Starting dataset generation for job {job_id}: "
            f"{len(satellites)} satellites, {timeframe} {timeunit}"
        )

        # Call the pipeline function
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
            dt=0.1,
            max_datapoints=0,
            end_time="now",
            use_database=True,
            dataset_name=config.get("name"),
        )

        # Update progress - processing results
        job_manager.update_job(job_id, progress=80)

        # Update dataset record in database
        db = get_db()
        observation_count = len(dataset_obs) if dataset_obs is not None else 0
        satellite_count = len(actual_sats) if actual_sats is not None else 0

        # Update the dataset status
        db.execute(
            """
            UPDATE datasets
            SET status = 'available',
                observation_count = ?,
                satellite_count = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (observation_count, satellite_count, dataset_id),
        )

        # Complete the job
        result = {
            "dataset_id": dataset_id,
            "observation_count": observation_count,
            "satellite_count": satellite_count,
            "actual_satellites": [int(s) for s in actual_sats] if actual_sats is not None else [],
            "performance": performance_data,
        }

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
            db.execute(
                "UPDATE datasets SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (dataset_id,),
            )
        except Exception:
            pass

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
        from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics
        from uct_benchmark.evaluation.stateMetrics import stateMetrics

        job_manager.update_job(job_id, progress=10)

        db = get_db()

        # Load dataset from database
        dataset_row = db.execute(
            "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()

        if not dataset_row:
            raise ValueError(f"Dataset {dataset_id} not found")

        job_manager.update_job(job_id, progress=20)

        # Load the submission file (UCTP output)
        with open(file_path, "r") as f:
            submission_data = json.load(f)

        job_manager.update_job(job_id, progress=30)

        # Get reference data from database
        # This would load the truth observations and states for comparison
        observations = db.execute(
            """
            SELECT o.* FROM observations o
            JOIN dataset_observations do ON o.id = do.observation_id
            WHERE do.dataset_id = ?
            """,
            (dataset_id,),
        ).fetchdf()

        job_manager.update_job(job_id, progress=40)

        # Run orbit association
        # The submission_data should contain predicted track/object assignments
        # compared against the truth from the dataset
        associations = orbitAssociation(
            submission_data.get("predictions", []),
            observations,
        ) if "predictions" in submission_data else {}

        job_manager.update_job(job_id, progress=60)

        # Compute binary metrics (TP, FP, FN, precision, recall, F1)
        binary_results = binaryMetrics(associations) if associations else {
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
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
        except Exception:
            pass

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
