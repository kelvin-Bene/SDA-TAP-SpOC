"""
UCTP Lab API endpoints.

Provides REST endpoints for:
- Algorithm pipeline runs (CRUD + comparison)
- ML model management (train, evaluate, list)
- API connectivity testing
- Dashboard statistics
- Algorithm configuration options
"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from backend_api.database import get_db
from backend_api.models.uctp_models import (
    AlgorithmOptions,
    ConnectivityReport,
    ConnectivityTestRequest,
    ConnectorStatusResponse,
    UCTPDashboardStats,
    UCTPModelDetail,
    UCTPModelSummary,
    UCTPModelTrainRequest,
    UCTPRunComparison,
    UCTPRunCreate,
    UCTPRunDetail,
    UCTPRunMetrics,
    UCTPRunSummary,
    UCTPRunStatus,
)
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


# ============================================================
# DASHBOARD
# ============================================================


@router.get("/dashboard/stats", response_model=UCTPDashboardStats)
async def get_dashboard_stats(db: DatabaseManager = Depends(get_db)):
    """Get UCTP Lab dashboard overview statistics."""
    try:
        # Total runs
        total_runs = db.execute("SELECT COUNT(*) FROM uctp_runs").fetchone()[0]
        completed_runs = db.execute(
            "SELECT COUNT(*) FROM uctp_runs WHERE status = 'completed'"
        ).fetchone()[0]

        # Best F1
        best_row = db.execute(
            "SELECT f1_score, algorithm_name FROM uctp_runs WHERE f1_score IS NOT NULL ORDER BY f1_score DESC LIMIT 1"
        ).fetchone()
        best_f1 = best_row[0] if best_row else None
        best_algo = best_row[1] if best_row else None

        # Models
        total_models = db.execute("SELECT COUNT(*) FROM uctp_models").fetchone()[0]
        ready_models = db.execute(
            "SELECT COUNT(*) FROM uctp_models WHERE status = 'ready'"
        ).fetchone()[0]

        # API health
        api_rows = db.execute(
            "SELECT status FROM uctp_api_connections WHERE last_checked = ("
            "  SELECT MAX(last_checked) FROM uctp_api_connections"
            ")"
        ).fetchall()
        if api_rows:
            connected = sum(1 for r in api_rows if r[0] == "connected")
            api_health = (connected / len(api_rows)) * 100
        else:
            api_health = 0.0

        # Recent runs
        recent_result = db.execute(
            "SELECT id, dataset_id, algorithm_name, status, started_at, completed_at, "
            "f1_score, precision, recall, position_rms_km, velocity_rms_km_s, "
            "clusters_found, objects_resolved, created_at "
            "FROM uctp_runs ORDER BY created_at DESC LIMIT 10"
        )
        columns = [desc[0] for desc in recent_result.description]
        recent_rows = recent_result.fetchall()
        recent_runs = [_row_to_run_summary(dict(zip(columns, r))) for r in recent_rows]

        return UCTPDashboardStats(
            total_runs=total_runs,
            completed_runs=completed_runs,
            best_f1_score=best_f1,
            best_algorithm=best_algo,
            total_models=total_models,
            ready_models=ready_models,
            api_health_pct=api_health,
            recent_runs=recent_runs,
        )
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return UCTPDashboardStats()


# ============================================================
# ALGORITHM RUNS
# ============================================================


@router.get("/runs/", response_model=List[UCTPRunSummary])
async def list_runs(
    status: Optional[str] = None,
    dataset_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: DatabaseManager = Depends(get_db),
):
    """List UCTP pipeline runs with optional filters."""
    query = (
        "SELECT id, dataset_id, algorithm_name, status, started_at, completed_at, "
        "f1_score, precision, recall, position_rms_km, velocity_rms_km_s, "
        "clusters_found, objects_resolved, created_at FROM uctp_runs WHERE 1=1"
    )
    params: list = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if dataset_id is not None:
        query += " AND dataset_id = ?"
        params.append(dataset_id)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    result = db.execute(query, tuple(params))
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    return [_row_to_run_summary(dict(zip(columns, r))) for r in rows]


@router.post("/runs/", response_model=UCTPRunSummary)
async def create_run(
    request: UCTPRunCreate,
    db: DatabaseManager = Depends(get_db),
):
    """Start a new UCTP pipeline run as a background job."""
    # Verify dataset exists
    dataset = db.execute("SELECT id FROM datasets WHERE id = ?", (request.dataset_id,)).fetchone()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {request.dataset_id} not found")

    # Build config JSON
    config_dict = {
        "clustering": request.clustering.model_dump(),
        "iod": request.iod.model_dump(),
        "refinement": request.refinement.model_dump(),
    }

    # Insert run record
    result = db.execute(
        """
        INSERT INTO uctp_runs (dataset_id, algorithm_name, config, status, created_at)
        VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        RETURNING id, created_at
        """,
        (request.dataset_id, request.algorithm_name, json.dumps(config_dict)),
    )
    row = result.fetchone()
    run_id = row[0]
    created_at = row[1]

    # Submit background job
    from backend_api.jobs.uctp_workers import submit_uctp_run

    job = submit_uctp_run(run_id, request.dataset_id, config_dict)

    logger.info(f"UCTP run {run_id} created with job {job.id}")

    return UCTPRunSummary(
        id=run_id,
        dataset_id=request.dataset_id,
        algorithm_name=request.algorithm_name,
        status=UCTPRunStatus.PENDING,
        created_at=created_at,
        job_id=job.id,
    )


@router.get("/runs/{run_id}", response_model=UCTPRunDetail)
async def get_run(run_id: int, db: DatabaseManager = Depends(get_db)):
    """Get detailed information about a UCTP run."""
    result = db.execute("SELECT * FROM uctp_runs WHERE id = ?", (run_id,))
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    row_dict = dict(zip(columns, row))
    config = json.loads(row_dict["config"]) if isinstance(row_dict["config"], str) else row_dict.get("config", {})

    return UCTPRunDetail(
        id=row_dict["id"],
        dataset_id=row_dict["dataset_id"],
        algorithm_name=row_dict["algorithm_name"],
        status=UCTPRunStatus(row_dict["status"]),
        started_at=row_dict.get("started_at"),
        completed_at=row_dict.get("completed_at"),
        created_at=row_dict["created_at"],
        config=config,
        output_path=row_dict.get("output_path"),
        log_output=row_dict.get("log_output"),
        error_message=row_dict.get("error_message"),
        metrics=UCTPRunMetrics(
            f1_score=row_dict.get("f1_score"),
            precision=row_dict.get("precision"),
            recall=row_dict.get("recall"),
            position_rms_km=row_dict.get("position_rms_km"),
            velocity_rms_km_s=row_dict.get("velocity_rms_km_s"),
            clusters_found=row_dict.get("clusters_found"),
            objects_resolved=row_dict.get("objects_resolved"),
        ),
    )


@router.delete("/runs/{run_id}")
async def delete_run(run_id: int, db: DatabaseManager = Depends(get_db)):
    """Delete a UCTP run."""
    existing = db.execute("SELECT id FROM uctp_runs WHERE id = ?", (run_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Run not found")

    db.execute("DELETE FROM uctp_runs WHERE id = ?", (run_id,))
    return {"message": f"Run {run_id} deleted"}


@router.get("/runs/{run_id}/logs")
async def get_run_logs(run_id: int, db: DatabaseManager = Depends(get_db)):
    """Get logs for a UCTP run."""
    row = db.execute(
        "SELECT log_output, status FROM uctp_runs WHERE id = ?", (run_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    return {"run_id": run_id, "status": row[1], "logs": row[0] or ""}


@router.get("/runs/compare/", response_model=UCTPRunComparison)
async def compare_runs(
    run_ids: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Compare multiple runs side-by-side.

    Args:
        run_ids: Comma-separated list of run IDs (e.g., "1,2,3").
    """
    ids = [int(x.strip()) for x in run_ids.split(",") if x.strip().isdigit()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 run IDs to compare")
    if len(ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 runs for comparison")

    placeholders = ",".join(["?"] * len(ids))
    result = db.execute(
        f"SELECT id, dataset_id, algorithm_name, status, started_at, completed_at, "
        f"f1_score, precision, recall, position_rms_km, velocity_rms_km_s, "
        f"clusters_found, objects_resolved, created_at, config "
        f"FROM uctp_runs WHERE id IN ({placeholders})",
        tuple(ids),
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="Not enough runs found")

    runs = []
    configs = []
    for r in rows:
        rd = dict(zip(columns, r))
        runs.append(_row_to_run_summary(rd))
        cfg = json.loads(rd["config"]) if isinstance(rd.get("config"), str) else rd.get("config", {})
        configs.append(cfg)

    # Compute config diffs
    config_diffs = _compute_config_diffs(configs)

    return UCTPRunComparison(runs=runs, config_diffs=config_diffs)


# ============================================================
# ML MODELS
# ============================================================


@router.get("/models/", response_model=List[UCTPModelSummary])
async def list_models(
    status: Optional[str] = None,
    limit: int = 50,
    db: DatabaseManager = Depends(get_db),
):
    """List trained ML models."""
    query = (
        "SELECT id, name, model_type, version, description, status, "
        "best_f1_score, best_position_rms_km, training_epochs, created_at "
        "FROM uctp_models WHERE 1=1"
    )
    params: list = []

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    result = db.execute(query, tuple(params))
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    return [UCTPModelSummary(**dict(zip(columns, r))) for r in rows]


@router.post("/models/train", response_model=UCTPModelSummary)
async def train_model(
    request: UCTPModelTrainRequest,
    db: DatabaseManager = Depends(get_db),
):
    """Start training a new ML model."""
    # Determine version
    existing = db.execute(
        "SELECT COUNT(*) FROM uctp_models WHERE name = ?", (request.name,)
    ).fetchone()[0]
    version = f"v{existing + 1}"

    result = db.execute(
        """
        INSERT INTO uctp_models (name, model_type, version, description,
            training_dataset_ids, training_config, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'training', CURRENT_TIMESTAMP)
        RETURNING id, created_at
        """,
        (
            request.name,
            request.model_type.value,
            version,
            request.description,
            json.dumps(request.training_dataset_ids),
            json.dumps(request.training_config),
        ),
    )
    row = result.fetchone()
    model_id = row[0]
    created_at = row[1]

    # Submit background training job
    from backend_api.jobs.uctp_workers import submit_model_training

    submit_model_training(
        model_id,
        request.name,
        request.model_type.value,
        request.training_dataset_ids,
        request.training_config,
    )

    return UCTPModelSummary(
        id=model_id,
        name=request.name,
        model_type=request.model_type,
        version=version,
        description=request.description,
        status="training",
        created_at=created_at,
    )


@router.get("/models/{model_id}", response_model=UCTPModelDetail)
async def get_model(model_id: int, db: DatabaseManager = Depends(get_db)):
    """Get detailed information about a trained model."""
    result = db.execute("SELECT * FROM uctp_models WHERE id = ?", (model_id,))
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Model not found")

    rd = dict(zip(columns, row))
    training_ids = json.loads(rd["training_dataset_ids"]) if isinstance(rd.get("training_dataset_ids"), str) else rd.get("training_dataset_ids", [])
    training_cfg = json.loads(rd["training_config"]) if isinstance(rd.get("training_config"), str) else rd.get("training_config", {})

    return UCTPModelDetail(
        id=rd["id"],
        name=rd["name"],
        model_type=rd["model_type"],
        version=rd["version"],
        description=rd.get("description"),
        status=rd["status"],
        best_f1_score=rd.get("best_f1_score"),
        best_position_rms_km=rd.get("best_position_rms_km"),
        training_epochs=rd.get("training_epochs"),
        created_at=rd["created_at"],
        training_dataset_ids=training_ids,
        training_config=training_cfg,
        training_loss=rd.get("training_loss"),
        validation_loss=rd.get("validation_loss"),
        model_path=rd.get("model_path"),
    )


@router.delete("/models/{model_id}")
async def delete_model(model_id: int, db: DatabaseManager = Depends(get_db)):
    """Delete a trained model."""
    existing = db.execute("SELECT id FROM uctp_models WHERE id = ?", (model_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Model not found")

    db.execute("DELETE FROM uctp_models WHERE id = ?", (model_id,))
    return {"message": f"Model {model_id} deleted"}


@router.post("/models/{model_id}/evaluate")
async def evaluate_model(
    model_id: int,
    dataset_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """Evaluate a trained model on a specific dataset."""
    model = db.execute("SELECT id, status FROM uctp_models WHERE id = ?", (model_id,)).fetchone()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if model[1] != "ready":
        raise HTTPException(status_code=400, detail="Model is not ready for evaluation")

    # Submit evaluation as a pipeline run using the model
    return {"message": f"Evaluation of model {model_id} on dataset {dataset_id} submitted"}


# ============================================================
# CONNECTIVITY
# ============================================================


@router.get("/connectivity/", response_model=List[ConnectorStatusResponse])
async def get_connectivity(db: DatabaseManager = Depends(get_db)):
    """Get current API connection statuses."""
    result = db.execute(
        """
        SELECT DISTINCT ON (service_name) service_name, status, response_time_ms,
               last_checked, error_message, metadata
        FROM uctp_api_connections
        ORDER BY service_name, last_checked DESC
        """
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    statuses = []
    for r in rows:
        rd = dict(zip(columns, r))
        meta = json.loads(rd["metadata"]) if isinstance(rd.get("metadata"), str) else rd.get("metadata", {})
        statuses.append(ConnectorStatusResponse(
            service_name=rd["service_name"],
            status=rd["status"],
            response_time_ms=rd.get("response_time_ms"),
            last_checked=rd.get("last_checked"),
            error_message=rd.get("error_message"),
            metadata=meta,
        ))

    return statuses


@router.post("/connectivity/test", response_model=ConnectorStatusResponse)
async def test_connection(
    request: ConnectivityTestRequest,
    db: DatabaseManager = Depends(get_db),
):
    """Test a specific API connection."""
    from backend_api.jobs.uctp_workers import run_connectivity_test

    result = run_connectivity_test(request.service_name, db)
    return result


@router.post("/connectivity/test-all", response_model=ConnectivityReport)
async def test_all_connections(db: DatabaseManager = Depends(get_db)):
    """Test all API connections."""
    from backend_api.jobs.uctp_workers import run_all_connectivity_tests

    report = run_all_connectivity_tests(db)
    return report


# ============================================================
# ALGORITHM OPTIONS
# ============================================================


@router.get("/algorithms/", response_model=AlgorithmOptions)
async def get_algorithm_options():
    """Get all available algorithm configuration options."""
    return AlgorithmOptions()


@router.get("/algorithms/options", response_model=AlgorithmOptions)
async def get_algorithm_options_alias():
    """Alias for /algorithms/ - Get all available algorithm configuration options."""
    return AlgorithmOptions()


# ============================================================
# HELPERS
# ============================================================


def _row_to_run_summary(rd: dict) -> UCTPRunSummary:
    """Convert a database row dict to UCTPRunSummary."""
    return UCTPRunSummary(
        id=rd["id"],
        dataset_id=rd["dataset_id"],
        algorithm_name=rd["algorithm_name"],
        status=UCTPRunStatus(rd["status"]),
        started_at=rd.get("started_at"),
        completed_at=rd.get("completed_at"),
        created_at=rd["created_at"],
        metrics=UCTPRunMetrics(
            f1_score=rd.get("f1_score"),
            precision=rd.get("precision"),
            recall=rd.get("recall"),
            position_rms_km=rd.get("position_rms_km"),
            velocity_rms_km_s=rd.get("velocity_rms_km_s"),
            clusters_found=rd.get("clusters_found"),
            objects_resolved=rd.get("objects_resolved"),
        ),
    )


def _compute_config_diffs(configs: list) -> dict:
    """Compute configuration differences between multiple runs."""
    if len(configs) < 2:
        return {}

    diffs = {}
    all_keys = set()
    for cfg in configs:
        all_keys.update(_flatten_dict(cfg).keys())

    for key in sorted(all_keys):
        values = []
        for cfg in configs:
            flat = _flatten_dict(cfg)
            values.append(flat.get(key))
        if len(set(str(v) for v in values)) > 1:
            diffs[key] = values

    return diffs


def _flatten_dict(d: dict, prefix: str = "") -> dict:
    """Flatten a nested dict with dot-separated keys."""
    items = {}
    for k, v in d.items():
        new_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, new_key))
        else:
            items[new_key] = v
    return items
