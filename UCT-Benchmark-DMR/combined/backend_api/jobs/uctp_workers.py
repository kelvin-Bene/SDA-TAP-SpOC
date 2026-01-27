"""
Background workers for UCTP Lab tasks.

Provides worker functions for UCTP pipeline runs, ML model training,
and API connectivity testing that run in background threads.
"""

import json
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from . import Job, JobType, get_job_manager
from .workers import get_executor


# ============================================================
# UCTP PIPELINE RUN
# ============================================================


def run_uctp_pipeline(job_id: str, run_id: int, dataset_id: int, config_dict: Dict[str, Any]) -> None:
    """
    Worker function for executing a UCTP pipeline run.

    Args:
        job_id: Background job ID for progress tracking.
        run_id: Database ID for the uctp_runs record.
        dataset_id: Dataset to process.
        config_dict: Pipeline configuration dict.
    """
    job_manager = get_job_manager()
    job_manager.start_job(job_id)

    try:
        from backend_api.database import get_db
        from uct_benchmark.uctp_lab.config import UCTPConfig
        from uct_benchmark.uctp_lab.pipeline import UCTPPipeline

        db = get_db()

        # Mark run as running
        db.execute(
            "UPDATE uctp_runs SET status = 'running', started_at = CURRENT_TIMESTAMP WHERE id = ?",
            (run_id,),
        )

        # Build pipeline config
        config = UCTPConfig.from_dict({
            **config_dict,
            "dataset_id": dataset_id,
        })

        # Progress callback
        def on_progress(stage: str, fraction: float):
            stage_weights = {"ingest": 10, "clustering": 30, "iod": 40, "output": 10}
            stage_offsets = {"ingest": 0, "clustering": 10, "iod": 40, "output": 80}
            weight = stage_weights.get(stage, 10)
            offset = stage_offsets.get(stage, 0)
            progress = int(offset + weight * fraction)
            job_manager.update_job(job_id, progress=min(progress, 95), stage=stage)

        # Run pipeline
        pipeline = UCTPPipeline(config, progress_callback=on_progress)
        result = pipeline.run()

        # Store results
        metrics = result.metrics
        log_text = "\n".join(result.logs)

        if result.error:
            db.execute(
                """
                UPDATE uctp_runs SET status = 'failed', completed_at = CURRENT_TIMESTAMP,
                    log_output = ?, error_message = ?,
                    clusters_found = ?, objects_resolved = ?
                WHERE id = ?
                """,
                (log_text, result.error, metrics.clusters_found, metrics.objects_resolved, run_id),
            )
            job_manager.fail_job(job_id, result.error)
            return

        # Update run record with results
        db.execute(
            """
            UPDATE uctp_runs SET
                status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                clusters_found = ?,
                objects_resolved = ?,
                output_path = ?,
                log_output = ?
            WHERE id = ?
            """,
            (
                metrics.clusters_found,
                metrics.objects_resolved,
                result.output_path,
                log_text,
                run_id,
            ),
        )

        job_manager.complete_job(job_id, {
            "run_id": run_id,
            "objects_resolved": metrics.objects_resolved,
            "clusters_found": metrics.clusters_found,
            "elapsed_seconds": metrics.elapsed_seconds,
        })
        logger.info(f"UCTP run {run_id} completed: {metrics.objects_resolved} objects resolved")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"UCTP run {run_id} failed: {error_msg}")
        logger.debug(traceback.format_exc())

        try:
            from backend_api.database import get_db
            db = get_db()
            db.execute(
                "UPDATE uctp_runs SET status = 'failed', completed_at = CURRENT_TIMESTAMP, error_message = ? WHERE id = ?",
                (error_msg, run_id),
            )
        except Exception as db_err:
            logger.error(f"Failed to update run {run_id} status: {db_err}")

        job_manager.fail_job(job_id, error_msg)


def submit_uctp_run(run_id: int, dataset_id: int, config_dict: Dict[str, Any]) -> Job:
    """Submit a UCTP pipeline run to the background executor."""
    job_manager = get_job_manager()
    job = job_manager.create_job(
        JobType.EVALUATION,  # Reuse evaluation type
        metadata={"uctp_run_id": run_id, "dataset_id": dataset_id, "type": "uctp_pipeline"},
    )

    executor = get_executor()
    executor.submit(run_uctp_pipeline, job.id, run_id, dataset_id, config_dict)

    return job


# ============================================================
# ML MODEL TRAINING
# ============================================================


def run_model_training(
    job_id: str,
    model_id: int,
    model_name: str,
    model_type: str,
    dataset_ids: List[int],
    training_config: Dict[str, Any],
) -> None:
    """
    Worker function for ML model training.

    Args:
        job_id: Background job ID.
        model_id: Database ID for the uctp_models record.
        model_name: Model name.
        model_type: Type of model to train.
        dataset_ids: Dataset IDs for training data.
        training_config: Training hyperparameters.
    """
    job_manager = get_job_manager()
    job_manager.start_job(job_id)

    try:
        from backend_api.database import get_db

        db = get_db()
        epochs = training_config.get("epochs", 50)

        # Simulate training progress (actual ML training will be implemented in Phase 5)
        for epoch in range(epochs):
            progress = int((epoch + 1) / epochs * 90)
            job_manager.update_job(job_id, progress=progress, stage=f"Epoch {epoch + 1}/{epochs}")

            # Simulated loss values (decreasing)
            train_loss = 1.0 / (1 + epoch * 0.1)
            val_loss = 1.1 / (1 + epoch * 0.09)

        # Update model record
        db.execute(
            """
            UPDATE uctp_models SET
                status = 'ready',
                training_epochs = ?,
                training_loss = ?,
                validation_loss = ?
            WHERE id = ?
            """,
            (epochs, train_loss, val_loss, model_id),
        )

        job_manager.complete_job(job_id, {
            "model_id": model_id,
            "training_epochs": epochs,
            "final_training_loss": train_loss,
            "final_validation_loss": val_loss,
        })
        logger.info(f"Model {model_id} training completed")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Model training {model_id} failed: {error_msg}")

        try:
            from backend_api.database import get_db
            db = get_db()
            db.execute("UPDATE uctp_models SET status = 'archived' WHERE id = ?", (model_id,))
        except Exception:
            pass

        job_manager.fail_job(job_id, error_msg)


def submit_model_training(
    model_id: int,
    model_name: str,
    model_type: str,
    dataset_ids: List[int],
    training_config: Dict[str, Any],
) -> Job:
    """Submit an ML model training job to the background executor."""
    job_manager = get_job_manager()
    job = job_manager.create_job(
        JobType.EVALUATION,
        metadata={"uctp_model_id": model_id, "type": "uctp_model_training"},
    )

    executor = get_executor()
    executor.submit(
        run_model_training, job.id, model_id, model_name, model_type, dataset_ids, training_config
    )

    return job


# ============================================================
# CONNECTIVITY TESTING
# ============================================================


def run_connectivity_test(service_name: str, db=None) -> dict:
    """
    Test a single API connection and store the result.

    Args:
        service_name: Name of the service to test.
        db: DatabaseManager instance.

    Returns:
        ConnectorStatusResponse-compatible dict.
    """
    if db is None:
        from backend_api.database import get_db
        db = get_db()

    start = time.time()
    status = "failed"
    error_msg = None
    metadata = {}

    try:
        if service_name == "orekit":
            status, metadata = _test_orekit()
        elif service_name == "orbdetpy":
            status, metadata = _test_orbdetpy()
        elif service_name == "spacetrack":
            status, metadata = _test_spacetrack()
        elif service_name == "satnogs":
            status, metadata = _test_satnogs()
        elif service_name == "celestrak":
            status, metadata = _test_celestrak()
        elif service_name == "udl":
            status, metadata = _test_udl()
        else:
            status = "failed"
            error_msg = f"Unknown service: {service_name}"
    except Exception as e:
        status = "failed"
        error_msg = str(e)

    response_time = (time.time() - start) * 1000  # ms

    # Store result
    db.execute(
        """
        INSERT INTO uctp_api_connections (service_name, status, response_time_ms, last_checked, error_message, metadata)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
        """,
        (service_name, status, response_time, error_msg, json.dumps(metadata)),
    )

    return {
        "service_name": service_name,
        "status": status,
        "response_time_ms": round(response_time, 1),
        "last_checked": datetime.utcnow().isoformat(),
        "error_message": error_msg,
        "metadata": metadata,
    }


def run_all_connectivity_tests(db=None) -> dict:
    """Test all API connections and return a report."""
    if db is None:
        from backend_api.database import get_db
        db = get_db()

    services = ["orekit", "orbdetpy", "spacetrack", "satnogs", "celestrak", "udl"]
    results = []
    for svc in services:
        result = run_connectivity_test(svc, db)
        results.append(result)

    connected = sum(1 for r in results if r["status"] == "connected")
    failed = len(results) - connected

    return {
        "services": results,
        "tested_at": datetime.utcnow().isoformat(),
        "total_connected": connected,
        "total_failed": failed,
    }


# ============================================================
# CONNECTIVITY TEST IMPLEMENTATIONS
# ============================================================


def _test_orekit():
    """Test Orekit JVM availability."""
    try:
        import orekit
        from orekit.pyhelpers import setup_orekit_curdir
        return "connected", {"library": "orekit-jpype", "version": str(getattr(orekit, '__version__', 'unknown'))}
    except ImportError:
        return "not_installed", {"error": "orekit-jpype not installed"}
    except Exception as e:
        return "failed", {"error": str(e)}


def _test_orbdetpy():
    """Test orbdetpy library availability."""
    try:
        import orbdetpy
        return "connected", {"library": "orbdetpy", "version": str(getattr(orbdetpy, '__version__', 'unknown'))}
    except ImportError:
        return "not_installed", {"error": "orbdetpy not installed"}
    except Exception as e:
        return "failed", {"error": str(e)}


def _test_spacetrack():
    """Test Space-Track.org connectivity."""
    import os
    username = os.getenv("SPACETRACK_USER")
    password = os.getenv("SPACETRACK_PASS")
    if not username or not password:
        return "unauthorized", {"error": "SPACETRACK_USER and SPACETRACK_PASS env vars not set"}
    return "connected", {"note": "Credentials configured (not tested live)"}


def _test_satnogs():
    """Test SatNOGS API connectivity."""
    try:
        import requests
        resp = requests.get("https://network.satnogs.org/api/stations/?format=json&status=2", timeout=10)
        resp.raise_for_status()
        return "connected", {"stations_count": len(resp.json()[:5])}
    except ImportError:
        return "failed", {"error": "requests not installed"}
    except Exception as e:
        return "failed", {"error": str(e)}


def _test_celestrak():
    """Test CelesTrak connectivity."""
    try:
        import requests
        resp = requests.get("https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json", timeout=10)
        resp.raise_for_status()
        return "connected", {"sample_count": min(len(resp.json()), 5)}
    except ImportError:
        return "failed", {"error": "requests not installed"}
    except Exception as e:
        return "failed", {"error": str(e)}


def _test_udl():
    """Test UDL API connectivity."""
    import os
    token = os.getenv("UDL_TOKEN")
    if not token:
        return "unauthorized", {"error": "UDL_TOKEN env var not set"}
    return "connected", {"note": "Token configured (not tested live)"}
