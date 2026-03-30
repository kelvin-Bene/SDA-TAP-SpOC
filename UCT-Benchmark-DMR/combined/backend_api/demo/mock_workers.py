"""
Mock worker functions for demo mode.

Replaces real dataset generation (UDL API) and evaluation pipeline
with synthetic data generation that simulates realistic progress.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from loguru import logger

from backend_api.demo.seed_data import (
    MOCK_SENSORS,
    SATS_BY_REGIME,
    generate_observations_for_dataset,
    generate_submission_results,
)
from backend_api.jobs import get_job_manager


def run_mock_dataset_generation(
    job_id: str,
    dataset_id: int,
    config: Dict[str, Any],
) -> None:
    """
    Mock dataset generation with simulated progress.

    Generates synthetic observations based on config and inserts them
    into the database, updating progress at each stage.
    """
    import random

    job_manager = get_job_manager()

    try:
        from backend_api.database import get_db

        # Stage 1: Initializing (longer sleeps so frontend polling can track progress)
        job_manager.update_job(job_id, progress=10, stage="Initializing")
        time.sleep(3)

        # Stage 2: Selecting satellites
        job_manager.update_job(job_id, progress=30, stage="Selecting satellites")
        time.sleep(3)

        regime = config.get("regime", "LEO")
        object_count = config.get("object_count", 5)
        timeframe = config.get("timeframe", 7)

        # Calculate observation count based on config
        base_obs = object_count * random.randint(20, 40)
        observation_count = min(base_obs, 5000)

        # Stage 3: Generating observations
        job_manager.update_job(job_id, progress=50, stage="Generating observations")
        time.sleep(3)

        observations = generate_observations_for_dataset(
            dataset_id=dataset_id,
            regime=regime,
            observation_count=observation_count,
            satellite_count=object_count,
            seed=dataset_id,
        )

        # Stage 4: Persisting to database
        job_manager.update_job(job_id, progress=80, stage="Persisting to database")
        time.sleep(3)

        db = get_db()

        # Determine actual satellites used
        actual_sats = list({obs["sat_no"] for obs in observations})

        # Insert satellites (if not exist)
        from backend_api.demo.seed_data import MOCK_SATELLITES
        sat_lookup = {s["sat_no"]: s for s in MOCK_SATELLITES}
        for sat_no in actual_sats:
            sat_info = sat_lookup.get(sat_no)
            if sat_info:
                try:
                    db.execute(
                        """
                        INSERT INTO satellites (sat_no, name, orbital_regime, object_type)
                        VALUES (?, ?, ?, ?)
                        """,
                        (sat_info["sat_no"], sat_info["name"],
                         sat_info["orbital_regime"], sat_info["object_type"]),
                    )
                except Exception:
                    pass  # Already exists

        # Insert observations
        for obs in observations:
            try:
                db.execute(
                    """
                    INSERT INTO observations (
                        id, sat_no, ob_time, ra, declination,
                        sensor_id, sensor_name, send_lat, send_long, send_alt,
                        data_mode, track_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        obs["id"], obs["sat_no"], obs["ob_time"],
                        obs["ra"], obs["declination"],
                        obs["sensor_id"], obs["sensor_name"],
                        obs["send_lat"], obs["send_long"], obs["send_alt"],
                        obs["data_mode"], obs["track_id"],
                    ),
                )
            except Exception:
                pass

        # Link observations to dataset
        for obs in observations:
            try:
                db.execute(
                    """
                    INSERT INTO dataset_observations (dataset_id, observation_id)
                    VALUES (?, ?)
                    """,
                    (dataset_id, obs["id"]),
                )
            except Exception:
                pass

        # Calculate coverage
        avg_coverage = round(len(actual_sats) / max(object_count, 1), 4)
        now = datetime.now(timezone.utc)

        # Update dataset record
        sensor = "optical" if regime != "MEO" else "radar"
        gen_params = json.dumps({"sensors": [sensor]})

        db.execute(
            """
            UPDATE datasets
            SET status = 'available',
                observation_count = ?,
                satellite_count = ?,
                avg_coverage = ?,
                time_window_start = ?,
                time_window_end = ?,
                generation_params = ?,
                actual_satellite_ids = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                len(observations),
                len(actual_sats),
                avg_coverage,
                (now - timedelta(days=timeframe)).isoformat(),
                now.isoformat(),
                gen_params,
                json.dumps(actual_sats),
                dataset_id,
            ),
        )

        # Complete job
        job_manager.update_job(job_id, progress=100)
        result = {
            "dataset_id": dataset_id,
            "observation_count": len(observations),
            "satellite_count": len(actual_sats),
            "actual_satellites": actual_sats,
        }
        job_manager.complete_job(job_id, result)
        logger.info(f"DEMO: Dataset generation completed for job {job_id}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"DEMO: Dataset generation failed for job {job_id}: {error_msg}")

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


def run_mock_evaluation(
    job_id: str,
    submission_id: int,
    dataset_id: int,
    file_path: str,
) -> None:
    """
    Mock evaluation pipeline with simulated progress.

    Generates plausible F1/precision/recall based on a deterministic
    seed derived from the submission ID.
    """
    import random

    job_manager = get_job_manager()

    try:
        from backend_api.database import get_db

        db = get_db()

        # Progress simulation (longer sleeps so frontend polling can track)
        job_manager.update_job(job_id, progress=10, stage="Loading dataset")
        time.sleep(3)

        job_manager.update_job(job_id, progress=30, stage="Loading submission")
        time.sleep(3)

        # Get dataset info for result generation
        ds_row = db.execute(
            "SELECT observation_count, satellite_count FROM datasets WHERE id = ?",
            (dataset_id,),
        ).fetchone()

        observation_count = ds_row[0] if ds_row and ds_row[0] else 500
        satellite_count = ds_row[1] if ds_row and ds_row[1] else 5

        job_manager.update_job(job_id, progress=50, stage="Computing metrics")
        time.sleep(3)

        # Generate plausible metrics from seed
        rng = random.Random(submission_id * 7 + dataset_id)
        f1 = round(rng.uniform(0.55, 0.95), 3)
        precision_val = round(min(1.0, f1 + rng.uniform(-0.03, 0.05)), 3)
        recall_val = round(min(1.0, f1 + rng.uniform(-0.05, 0.03)), 3)
        position_rms = round(rng.uniform(0.5, 15.0), 2)
        velocity_rms = round(position_rms * rng.uniform(0.05, 0.08), 3)

        job_manager.update_job(job_id, progress=70, stage="Generating results")
        time.sleep(3)

        results = generate_submission_results(
            submission_id=submission_id,
            f1=f1,
            precision_val=precision_val,
            recall_val=recall_val,
            position_rms_km=position_rms,
            velocity_rms_km_s=velocity_rms,
            observation_count=observation_count,
            satellite_count=satellite_count,
            seed=submission_id,
        )

        job_manager.update_job(job_id, progress=90, stage="Storing results")
        time.sleep(3)

        # Insert results
        db.execute(
            """
            INSERT INTO submission_results (
                submission_id, true_positives, true_negatives,
                false_positives, false_negatives,
                precision, recall, f1_score, specificity, accuracy,
                position_rms_km, velocity_rms_km_s, raw_results
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                results["submission_id"],
                results["true_positives"],
                results["true_negatives"],
                results["false_positives"],
                results["false_negatives"],
                results["precision"],
                results["recall"],
                results["f1_score"],
                results["specificity"],
                results["accuracy"],
                results["position_rms_km"],
                results["velocity_rms_km_s"],
                json.dumps(results["raw_results"]),
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
        job_manager.update_job(job_id, progress=100)
        result = {
            "submission_id": submission_id,
            "binary_metrics": results["raw_results"]["binary"],
            "state_metrics": results["raw_results"]["state"],
        }
        job_manager.complete_job(job_id, result)
        logger.info(f"DEMO: Evaluation completed for job {job_id}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"DEMO: Evaluation failed for job {job_id}: {error_msg}")

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
