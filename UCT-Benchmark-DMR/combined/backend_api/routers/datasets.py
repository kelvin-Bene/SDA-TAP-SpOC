"""Dataset management endpoints."""

import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse


class _SafeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime and Decimal objects from DuckDB."""

    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)
from loguru import logger

from backend_api.database import get_db
from backend_api.models import (
    CheckExistingResponse,
    DatasetCreate,
    DatasetDetail,
    DatasetEnrichmentEntry,
    DatasetObservation,
    DatasetProvenance,
    DatasetQuery,
    DatasetSourceAttribution,
    DatasetStatus,
    DatasetSummary,
    DataTier,
    FullObservation,
    OrbitalRegime,
    SearchStrategy,
    SensorType,
)
from uct_benchmark.database.connection import DatabaseManager
from backend_api.jobs.workers import submit_dataset_generation

router = APIRouter()


def validate_dataset_id(dataset_id: str) -> int:
    """
    Validate and convert dataset_id string to integer.

    Args:
        dataset_id: String representation of dataset ID

    Returns:
        int: Validated dataset ID

    Raises:
        HTTPException: 400 if ID is invalid
    """
    try:
        id_int = int(dataset_id)
        if id_int <= 0:
            raise HTTPException(status_code=400, detail="Dataset ID must be a positive integer")
        return id_int
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid dataset ID: '{dataset_id}' is not a valid integer"
        )


def _row_to_dataset_summary(row: tuple, columns: list) -> DatasetSummary:
    """Convert a database row to DatasetSummary model."""
    row_dict = dict(zip(columns, row))

    # Parse sensor types from JSON if present
    sensor_types = []
    if row_dict.get("generation_params"):
        try:
            params = (
                json.loads(row_dict["generation_params"])
                if isinstance(row_dict["generation_params"], str)
                else row_dict.get("generation_params", {})
            )
            sensor_types = params.get("sensors", ["optical"])
        except (json.JSONDecodeError, TypeError):
            sensor_types = ["optical"]

    # Calculate size_bytes estimate (approx 500 bytes per observation as JSON)
    obs_count = row_dict.get("observation_count") or 0
    estimated_size = obs_count * 500

    return DatasetSummary(
        id=str(row_dict["id"]),
        name=row_dict["name"],
        description=row_dict.get("code"),  # Use code as description if no separate field
        regime=OrbitalRegime(row_dict.get("orbital_regime") or "LEO"),
        tier=DataTier(row_dict.get("tier") or "T1"),
        status=DatasetStatus(row_dict.get("status") or "created"),
        created_at=row_dict["created_at"] or datetime.utcnow(),
        observation_count=obs_count,
        satellite_count=row_dict.get("satellite_count") or 0,
        coverage=float(row_dict.get("avg_coverage") or 0),
        size_bytes=estimated_size,
        sensor_types=[SensorType(s) for s in sensor_types if s in ["optical", "radar", "rf"]],
        job_id=None,  # Could store this in generation_params
    )


@router.get("/", response_model=List[DatasetSummary])
async def list_datasets(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    regime: Optional[str] = None,
    tier: Optional[str] = None,
    db: DatabaseManager = Depends(get_db),
):
    """
    List all available datasets.

    Args:
        limit: Maximum number of datasets to return
        offset: Number of datasets to skip
        status: Filter by status (created, generating, available, failed)
        regime: Filter by orbital regime (LEO, MEO, GEO, HEO)
        tier: Filter by complexity tier (T1, T2, T3, T4)

    Returns:
        List of dataset summaries
    """
    # Build query with optional filters
    query = "SELECT * FROM datasets WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if regime:
        query += " AND orbital_regime = ?"
        params.append(regime)

    if tier:
        query += " AND tier = ?"
        params.append(tier)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    result = db.execute(query, tuple(params))
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    return [_row_to_dataset_summary(row, columns) for row in rows]


@router.get("/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(
    dataset_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get detailed information about a specific dataset.

    Args:
        dataset_id: The dataset ID

    Returns:
        Detailed dataset information including satellites and parameters
    """
    id_int = validate_dataset_id(dataset_id)
    result = db.execute("SELECT * FROM datasets WHERE id = ?", (id_int,))
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    row_dict = dict(zip(columns, row))

    # Parse generation parameters
    params = {}
    satellites = []
    sensor_types = ["optical"]

    if row_dict.get("generation_params"):
        try:
            params = (
                json.loads(row_dict["generation_params"])
                if isinstance(row_dict["generation_params"], str)
                else row_dict.get("generation_params", {})
            )
            satellites = params.get("satIDs", [])
            sensor_types = params.get("sensors", ["optical"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Calculate size_bytes estimate (approx 500 bytes per observation as JSON)
    obs_count = row_dict.get("observation_count") or 0
    estimated_size = obs_count * 500

    return DatasetDetail(
        id=str(row_dict["id"]),
        name=row_dict["name"],
        description=row_dict.get("code"),
        regime=OrbitalRegime(row_dict.get("orbital_regime") or "LEO"),
        tier=DataTier(row_dict.get("tier") or "T1"),
        status=DatasetStatus(row_dict.get("status") or "created"),
        created_at=row_dict["created_at"] or datetime.utcnow(),
        observation_count=obs_count,
        satellite_count=row_dict.get("satellite_count") or 0,
        coverage=float(row_dict.get("avg_coverage") or 0),
        size_bytes=estimated_size,
        sensor_types=[SensorType(s) for s in sensor_types if s in ["optical", "radar", "rf"]],
        satellites=satellites,
        parameters=params,
        time_window_start=row_dict.get("time_window_start"),
        time_window_end=row_dict.get("time_window_end"),
        avg_obs_count=float(row_dict.get("avg_obs_count") or 0),
        max_track_gap=float(row_dict.get("max_track_gap") or 0),
        json_path=row_dict.get("json_path"),
    )


def _build_generation_params(request: DatasetCreate) -> Dict[str, Any]:
    """Build generation_params dict from a DatasetCreate request."""
    generation_params = {
        "regime": request.regime.value,
        "tier": request.tier.value,
        "object_count": request.object_count,
        "timeframe": request.timeframe,
        "timeunit": request.timeunit,
        "sensors": [s.value for s in request.sensors],
        "coverage": request.coverage,
        "include_hamr": request.include_hamr,
    }
    if request.satellites:
        generation_params["satellites"] = request.satellites
    if request.start_date:
        generation_params["start_date"] = request.start_date.isoformat()
    if request.end_date:
        generation_params["end_date"] = request.end_date.isoformat()
    if request.downsampling:
        generation_params["downsampling"] = {
            "enabled": request.downsampling.enabled,
            "target_coverage": request.downsampling.target_coverage,
            "target_gap": request.downsampling.target_gap,
            "max_obs_per_sat": request.downsampling.max_obs_per_sat,
            "preserve_tracks": request.downsampling.preserve_tracks,
            "seed": request.downsampling.seed,
        }
    if request.simulation:
        generation_params["simulation"] = {
            "enabled": request.simulation.enabled,
            "fill_gaps": request.simulation.fill_gaps,
            "sensor_model": request.simulation.sensor_model,
            "apply_noise": request.simulation.apply_noise,
            "max_synthetic_ratio": request.simulation.max_synthetic_ratio,
            "seed": request.simulation.seed,
        }
    generation_params["search_strategy"] = request.search_strategy.value
    if request.search_strategy == SearchStrategy.WINDOWED:
        generation_params["window_size_minutes"] = request.window_size_minutes or 10
    return generation_params


@router.post("/check-existing", response_model=CheckExistingResponse)
async def check_existing(
    request: DatasetCreate,
    db: DatabaseManager = Depends(get_db),
):
    """
    Check if an existing dataset matches the given configuration.

    Returns whether a matching dataset exists without creating anything.
    """
    try:
        from uct_benchmark.api.apiIntegration import compute_config_hash
    except ImportError:
        return CheckExistingResponse(exists=False)

    generation_params = _build_generation_params(request)
    config_hash = compute_config_hash(generation_params)

    existing = db.execute(
        "SELECT id, name, observation_count FROM datasets WHERE config_hash = ? AND status = 'available' ORDER BY created_at DESC LIMIT 1",
        (config_hash,),
    ).fetchone()

    if existing:
        return CheckExistingResponse(
            exists=True,
            dataset_id=existing[0],
            name=existing[1],
            observation_count=existing[2],
        )
    return CheckExistingResponse(exists=False)


@router.post("/debug")
async def debug_request(request: Request):
    """Debug endpoint to log raw request body."""
    body = await request.body()
    try:
        data = json.loads(body)
        logger.info(f"Debug endpoint received: {json.dumps(data, indent=2, default=str)}")
        return {"received": data}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return {"error": str(e), "raw": body.decode()}


@router.post("/", response_model=DatasetSummary, status_code=201)
async def create_dataset(
    request: DatasetCreate,
    db: DatabaseManager = Depends(get_db),
):
    """
    Create a new dataset and start generation.

    This endpoint creates a dataset record and submits a background job
    to generate the actual observation data.

    Args:
        request: Dataset creation parameters

    Returns:
        The created dataset summary with job_id for tracking progress
    """
    logger.info(
        f"Creating dataset with: name={request.name}, regime={request.regime}, tier={request.tier}"
    )
    # Prepare generation parameters
    generation_params = _build_generation_params(request)
    logger.info(f"Search strategy: {request.search_strategy.value}")

    # =====================================================================
    # CONFIG HASH DEDUP: Check if an identical dataset already exists (v2.0.0)
    # =====================================================================
    config_hash = None
    try:
        from uct_benchmark.api.apiIntegration import compute_config_hash
        config_hash = compute_config_hash(generation_params)

        existing = db.execute(
            "SELECT id, name, observation_count, satellite_count, avg_coverage, tier, orbital_regime, created_at "
            "FROM datasets WHERE config_hash = ? AND status = 'available' ORDER BY created_at DESC LIMIT 1",
            (config_hash,),
        ).fetchone()

        if existing and len(existing) >= 8:
            logger.info(f"Reusing existing dataset {existing[0]} (config_hash match)")
            reused_summary = DatasetSummary(
                id=str(existing[0]),
                name=existing[1],
                description=None,
                regime=OrbitalRegime(existing[6] or "LEO"),
                tier=DataTier(existing[5] or "T1"),
                status=DatasetStatus.AVAILABLE,
                created_at=existing[7] or datetime.utcnow(),
                observation_count=existing[2] or 0,
                satellite_count=existing[3] or 0,
                coverage=float(existing[4] or 0),
                size_bytes=(existing[2] or 0) * 500,
                sensor_types=request.sensors,
                job_id=None,
                reused=True,
            )
            return JSONResponse(
                status_code=200,
                content=json.loads(json.dumps(reused_summary.model_dump(), cls=_SafeEncoder)),
            )
    except Exception:
        logger.debug("Config hash dedup check skipped (not available or query failed)")

    # Generate a unique dataset name using timestamp + UUID to avoid race conditions
    # The database has a UNIQUE constraint on name, so this ensures atomicity
    # Format: {user_name}-{YYYYMMDD}-{HHMMSS}-{short_uuid}
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    dataset_name = f"{request.name}-{timestamp}-{short_uuid}"
    logger.info(f"Generated unique dataset name: {dataset_name}")

    # Add the final unique name to generation params
    generation_params["name"] = dataset_name

    # Create dataset and job records, then start background generation.
    # Note: the PostgreSQL adapter auto-commits each execute(), so
    # BEGIN/COMMIT blocks are not used.  Instead each INSERT/UPDATE is
    # committed individually and the background thread is started only
    # AFTER all database writes complete (pg8000 connections are not
    # thread-safe).
    job = None
    dataset_id = None

    try:
        # 1. Create dataset record
        result = db.execute(
            """
            INSERT INTO datasets (
                name, code, tier, orbital_regime, status, generation_params, created_at
            ) VALUES (?, ?, ?, ?, 'generating', ?, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (
                dataset_name,
                f"{request.regime.value}_{request.tier.value}",
                request.tier.value,
                request.regime.value,
                json.dumps(generation_params),
            ),
        )
        dataset_id = result.fetchone()[0]

        # 2. Submit background generation job (creates job record + starts thread)
        job = submit_dataset_generation(dataset_id, generation_params)

        # 3. Update dataset with job_id
        db.execute(
            """
            UPDATE datasets
            SET generation_params = ?
            WHERE id = ?
            """,
            (
                json.dumps({**generation_params, "job_id": job.id}),
                dataset_id,
            ),
        )

    except Exception as e:
        # Cancel the job if it was created
        if job is not None:
            try:
                from backend_api.jobs import get_job_manager as _get_jm

                _get_jm().fail_job(job.id, "Dataset creation failed, job cancelled")
            except Exception as cancel_error:
                logger.warning(f"Failed to cancel orphaned job {job.id}: {cancel_error}")

        logger.error(f"Failed to create dataset: {e}")

        error_str = str(e).lower()
        if "unique" in error_str or "duplicate" in error_str:
            raise HTTPException(
                status_code=409, detail="Dataset name conflict occurred. Please try again."
            )

        raise HTTPException(status_code=500, detail=f"Failed to create dataset: {str(e)}")

    return DatasetSummary(
        id=str(dataset_id),
        name=request.name,
        description=None,
        regime=request.regime,
        tier=request.tier,
        status=DatasetStatus.GENERATING,
        created_at=datetime.utcnow(),
        observation_count=0,
        satellite_count=request.object_count,
        coverage=0.0,
        size_bytes=0,
        sensor_types=request.sensors,
        job_id=job.id,
    )


@router.get("/{dataset_id}/observations")
async def get_dataset_observations(
    dataset_id: str,
    limit: int = 100,
    offset: int = 0,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get observations from a dataset.

    Args:
        dataset_id: The dataset ID
        limit: Maximum number of observations to return
        offset: Number of observations to skip

    Returns:
        Paginated list of observations
    """
    # Validate dataset ID
    id_int = validate_dataset_id(dataset_id)

    # First verify dataset exists
    dataset_check = db.execute(
        "SELECT id, observation_count FROM datasets WHERE id = ?", (id_int,)
    ).fetchone()

    if dataset_check is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    total_count = dataset_check[1] or 0

    # Check for data integrity: observations should be linked during generation
    existing_links = db.execute(
        "SELECT COUNT(*) FROM dataset_observations WHERE dataset_id = ?", (id_int,)
    ).fetchone()[0]

    if existing_links == 0 and total_count > 0:
        # Data integrity issue - observations weren't properly linked during generation
        # Previously this had auto-repair code, but that could link wrong observations
        # Now we surface the error clearly so the user knows to regenerate
        logger.error(
            f"Data integrity issue: Dataset {dataset_id} has observation_count={total_count} "
            f"but no linked observations. Dataset may need to be regenerated."
        )
        raise HTTPException(
            status_code=500,
            detail=f"Dataset has corrupted observation links ({total_count} observations expected, "
            f"0 linked). Please regenerate this dataset or use the /link-observations endpoint to repair.",
        )

    # Query observations linked to this dataset
    result = db.execute(
        """
        SELECT o.id, o.ob_time, o.ra, o.declination, o.sensor_name, o.track_id
        FROM observations o
        JOIN dataset_observations dso ON o.id = dso.observation_id
        WHERE dso.dataset_id = ?
        ORDER BY o.ob_time
        LIMIT ? OFFSET ?
        """,
        (id_int, limit, offset),
    )

    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    observations = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        observations.append(
            DatasetObservation(
                id=str(row_dict["id"]),
                ob_time=row_dict["ob_time"],
                ra=float(row_dict["ra"] or 0),
                declination=float(row_dict["declination"] or 0),
                sensor_name=row_dict.get("sensor_name"),
                track_id=str(row_dict["track_id"]) if row_dict.get("track_id") else None,
            )
        )

    return {
        "dataset_id": dataset_id,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "observations": observations,
    }


@router.post("/{dataset_id}/link-observations")
async def link_observations(dataset_id: str, db=Depends(get_db)):
    """
    Manually link observations to a dataset.

    This is a repair endpoint to fix datasets where observations weren't properly
    linked during generation.
    """
    # Validate dataset ID
    id_int = validate_dataset_id(dataset_id)

    # Get dataset info
    dataset = db.execute(
        "SELECT id, name, observation_count FROM datasets WHERE id = ?", (id_int,)
    ).fetchone()

    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    obs_count = dataset[2] or 0

    # Check if already linked
    existing_links = db.execute(
        "SELECT COUNT(*) FROM dataset_observations WHERE dataset_id = ?", (id_int,)
    ).fetchone()[0]

    if existing_links > 0:
        return {
            "message": f"Dataset already has {existing_links} linked observations",
            "linked": existing_links,
        }

    # Get recent observations that match the dataset's time window
    # Since we don't have explicit time window, link the most recent observations
    # up to the observation_count
    if obs_count <= 0:
        return {"message": "Dataset has no observations to link", "linked": 0}

    # Get observation IDs from the observations table (most recent ones)
    result = db.execute(
        """
        SELECT id FROM observations
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (obs_count,),
    )
    obs_ids = [row[0] for row in result.fetchall()]

    if not obs_ids:
        return {"message": "No observations found to link", "linked": 0}

    # Link observations to dataset
    try:
        db.datasets.add_observations_to_dataset(id_int, obs_ids)
        logger.info(f"Linked {len(obs_ids)} observations to dataset {dataset_id}")
        return {
            "message": f"Successfully linked {len(obs_ids)} observations",
            "linked": len(obs_ids),
        }
    except Exception as e:
        logger.error(f"Failed to link observations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to link observations: {str(e)}")


@router.patch("/{dataset_id}/coverage")
async def update_dataset_coverage(
    dataset_id: str,
    coverage: float,
    db: DatabaseManager = Depends(get_db),
):
    """
    Update a dataset's coverage value.

    Args:
        dataset_id: The dataset ID
        coverage: Coverage value between 0 and 1

    Returns:
        Success message
    """
    # Validate dataset ID
    id_int = validate_dataset_id(dataset_id)

    if not 0 <= coverage <= 1:
        raise HTTPException(status_code=400, detail="Coverage must be between 0 and 1")

    result = db.execute("SELECT id, name FROM datasets WHERE id = ?", (id_int,))
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    db.execute(
        "UPDATE datasets SET avg_coverage = ? WHERE id = ?",
        (coverage, id_int),
    )

    return {"message": f"Dataset {dataset_id} coverage updated to {coverage:.2%}"}


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Delete a dataset and its associated observations.

    Args:
        dataset_id: The dataset ID

    Returns:
        Success message
    """
    # Validate dataset ID
    id_int = validate_dataset_id(dataset_id)

    # Check dataset exists
    result = db.execute("SELECT id, name FROM datasets WHERE id = ?", (id_int,))
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset_name = row[1]

    # Delete associated observations first
    db.execute("DELETE FROM dataset_observations WHERE dataset_id = ?", (id_int,))

    # Delete the dataset
    db.execute("DELETE FROM datasets WHERE id = ?", (id_int,))

    return {"message": f"Dataset '{dataset_name}' (ID: {dataset_id}) deleted successfully"}


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Download a dataset as JSON.

    Args:
        dataset_id: The dataset ID

    Returns:
        JSON file containing the dataset observations and metadata
    """
    # Validate dataset ID
    id_int = validate_dataset_id(dataset_id)

    # Get dataset info
    result = db.execute("SELECT * FROM datasets WHERE id = ?", (id_int,))
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    row_dict = dict(zip(columns, row))

    if row_dict.get("status") != "available":
        raise HTTPException(status_code=400, detail="Dataset is not available for download")

    # Get observations
    obs_result = db.execute(
        """
        SELECT o.*, dso.assigned_track_id, dso.assigned_object_id
        FROM observations o
        JOIN dataset_observations dso ON o.id = dso.observation_id
        WHERE dso.dataset_id = ?
        ORDER BY o.ob_time
        """,
        (id_int,),
    )

    obs_columns = [desc[0] for desc in obs_result.description]
    obs_rows = obs_result.fetchall()

    observations = []
    for obs_row in obs_rows:
        obs_dict = dict(zip(obs_columns, obs_row))
        # Convert datetime to string for JSON
        if obs_dict.get("ob_time"):
            obs_dict["ob_time"] = (
                obs_dict["ob_time"].isoformat()
                if hasattr(obs_dict["ob_time"], "isoformat")
                else str(obs_dict["ob_time"])
            )
        observations.append(obs_dict)

    # Build export data (v2.0.0: includes ALL observation fields)
    export_data = {
        "dataset": {
            "id": row_dict["id"],
            "name": row_dict["name"],
            "regime": row_dict.get("orbital_regime"),
            "tier": row_dict.get("tier"),
            "observation_count": row_dict.get("observation_count"),
            "satellite_count": row_dict.get("satellite_count"),
            "config_hash": row_dict.get("config_hash"),
            "sensor_mode": row_dict.get("sensor_mode"),
            "total_api_calls": row_dict.get("total_api_calls"),
            "generation_duration_sec": float(row_dict["generation_duration_sec"]) if row_dict.get("generation_duration_sec") else None,
            "created_at": str(row_dict["created_at"]) if row_dict.get("created_at") else None,
        },
        "observations": observations,
    }

    return JSONResponse(
        content=json.loads(json.dumps(export_data, cls=_SafeEncoder)),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{row_dict["name"]}.json"'},
    )


# ============================================================
# PROVENANCE & TRACKING ENDPOINTS (v2.0.0)
# ============================================================


@router.get("/{dataset_id}/queries")
async def get_dataset_queries(
    dataset_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """Get all API query records for a dataset."""
    id_int = validate_dataset_id(dataset_id)

    # Verify dataset exists
    ds_check = db.execute("SELECT id FROM datasets WHERE id = ?", (id_int,)).fetchone()
    if ds_check is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    result = db.execute(
        "SELECT * FROM dataset_queries WHERE dataset_id = ? ORDER BY executed_at",
        (id_int,),
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    queries = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        # Parse query_params JSON
        qp = row_dict.get("query_params")
        if isinstance(qp, str):
            try:
                qp = json.loads(qp)
            except (json.JSONDecodeError, TypeError):
                qp = {}
        row_dict["query_params"] = qp or {}
        queries.append(row_dict)

    return JSONResponse(
        content=json.loads(json.dumps(queries, cls=_SafeEncoder)),
        media_type="application/json",
    )


@router.get("/{dataset_id}/sources")
async def get_dataset_sources(
    dataset_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """Get data source attribution for a dataset."""
    id_int = validate_dataset_id(dataset_id)

    # Verify dataset exists
    ds_check = db.execute("SELECT id FROM datasets WHERE id = ?", (id_int,)).fetchone()
    if ds_check is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    result = db.execute(
        """
        SELECT dds.*, ds.source_name
        FROM dataset_data_sources dds
        LEFT JOIN data_sources ds ON dds.source_id = ds.id
        WHERE dds.dataset_id = ?
        ORDER BY ds.source_name
        """,
        (id_int,),
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    sources = [dict(zip(columns, row)) for row in rows]
    return JSONResponse(
        content=json.loads(json.dumps(sources, cls=_SafeEncoder)),
        media_type="application/json",
    )


@router.get("/{dataset_id}/provenance")
async def get_dataset_provenance(
    dataset_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get full provenance chain for a dataset.

    Includes config hash, query history, source attribution,
    enrichment log, and performance metrics.
    """
    id_int = validate_dataset_id(dataset_id)

    # Get dataset metadata
    ds_result = db.execute("SELECT * FROM datasets WHERE id = ?", (id_int,))
    ds_columns = [desc[0] for desc in ds_result.description]
    ds_row = ds_result.fetchone()

    if ds_row is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    ds_dict = dict(zip(ds_columns, ds_row))

    # Parse performance_metrics JSON
    perf = ds_dict.get("performance_metrics")
    if isinstance(perf, str):
        try:
            perf = json.loads(perf)
        except (json.JSONDecodeError, TypeError):
            perf = None

    # Get queries
    q_result = db.execute(
        "SELECT * FROM dataset_queries WHERE dataset_id = ? ORDER BY executed_at",
        (id_int,),
    )
    q_columns = [desc[0] for desc in q_result.description]
    q_rows = q_result.fetchall()
    queries = []
    for row in q_rows:
        rd = dict(zip(q_columns, row))
        qp = rd.get("query_params")
        if isinstance(qp, str):
            try:
                qp = json.loads(qp)
            except (json.JSONDecodeError, TypeError):
                qp = {}
        rd["query_params"] = qp or {}
        queries.append(rd)

    # Get sources
    s_result = db.execute(
        """
        SELECT dds.*, ds.source_name
        FROM dataset_data_sources dds
        LEFT JOIN data_sources ds ON dds.source_id = ds.id
        WHERE dds.dataset_id = ?
        """,
        (id_int,),
    )
    s_columns = [desc[0] for desc in s_result.description]
    s_rows = s_result.fetchall()
    sources = [dict(zip(s_columns, row)) for row in s_rows]

    # Get enrichment log
    e_result = db.execute(
        "SELECT * FROM dataset_enrichment_log WHERE dataset_id = ? ORDER BY enriched_at",
        (id_int,),
    )
    e_columns = [desc[0] for desc in e_result.description]
    e_rows = e_result.fetchall()
    enrichment = []
    for row in e_rows:
        rd = dict(zip(e_columns, row))
        fu = rd.get("fields_updated")
        if isinstance(fu, str):
            try:
                fu = json.loads(fu)
            except (json.JSONDecodeError, TypeError):
                fu = None
        rd["fields_updated"] = fu
        enrichment.append(rd)

    provenance = {
        "dataset_id": id_int,
        "dataset_name": ds_dict.get("name"),
        "config_hash": ds_dict.get("config_hash"),
        "total_api_calls": ds_dict.get("total_api_calls", 0),
        "total_api_errors": ds_dict.get("total_api_errors", 0),
        "generation_duration_sec": float(ds_dict["generation_duration_sec"]) if ds_dict.get("generation_duration_sec") else None,
        "performance_metrics": perf,
        "queries": queries,
        "sources": sources,
        "enrichment_log": enrichment,
    }
    return JSONResponse(
        content=json.loads(json.dumps(provenance, cls=_SafeEncoder)),
        media_type="application/json",
    )
