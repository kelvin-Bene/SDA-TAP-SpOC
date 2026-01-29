"""Dataset management endpoints."""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger

from backend_api.database import get_db
from backend_api.jobs.workers import submit_dataset_generation
from backend_api.models import (
    DatasetCreate,
    DatasetDetail,
    DatasetObservation,
    DatasetStatus,
    DatasetSummary,
    DataTier,
    OrbitalRegime,
    SearchStrategy,
    SensorType,
)
from uct_benchmark.database.connection import DatabaseManager

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
        regime=OrbitalRegime(row_dict.get("orbital_regime", "LEO")),
        tier=DataTier(row_dict.get("tier", "T1")),
        status=DatasetStatus(row_dict.get("status", "created")),
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
    # Prepare generation parameters (name will be set after uniqueness check)
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

    # Add downsampling options if specified
    if request.downsampling:
        generation_params["downsampling"] = {
            "enabled": request.downsampling.enabled,
            "target_coverage": request.downsampling.target_coverage,
            "target_gap": request.downsampling.target_gap,
            "max_obs_per_sat": request.downsampling.max_obs_per_sat,
            "preserve_tracks": request.downsampling.preserve_tracks,
            "seed": request.downsampling.seed,
        }
        logger.info(f"Downsampling enabled: {request.downsampling.enabled}")

    # Add simulation options if specified
    if request.simulation:
        generation_params["simulation"] = {
            "enabled": request.simulation.enabled,
            "fill_gaps": request.simulation.fill_gaps,
            "sensor_model": request.simulation.sensor_model,
            "apply_noise": request.simulation.apply_noise,
            "max_synthetic_ratio": request.simulation.max_synthetic_ratio,
            "seed": request.simulation.seed,
        }
        logger.info(f"Simulation enabled: {request.simulation.enabled}")

    # Add search strategy
    generation_params["search_strategy"] = request.search_strategy.value
    if request.search_strategy == SearchStrategy.WINDOWED:
        generation_params["window_size_minutes"] = request.window_size_minutes or 10
    logger.info(f"Search strategy: {request.search_strategy.value}")

    # Generate a unique dataset name using timestamp + UUID to avoid race conditions
    # The database has a UNIQUE constraint on name, so this ensures atomicity
    # Format: {user_name}-{YYYYMMDD}-{HHMMSS}-{short_uuid}
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    dataset_name = f"{request.name}-{timestamp}-{short_uuid}"
    logger.info(f"Generated unique dataset name: {dataset_name}")

    # Add the final unique name to generation params
    generation_params["name"] = dataset_name

    # Use transaction to ensure atomicity of dataset creation
    # If any step fails, rollback to prevent partial/corrupted records
    job = None
    dataset_id = None

    try:
        # Start transaction
        db.execute("BEGIN TRANSACTION")

        # Create dataset record in database using RETURNING to get the ID
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

        # Submit background job for dataset generation
        job = submit_dataset_generation(dataset_id, generation_params)

        # Update dataset with job_id
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

        # Commit transaction
        db.execute("COMMIT")

    except Exception as e:
        # Rollback on any failure
        try:
            db.execute("ROLLBACK")
        except Exception as rollback_error:
            logger.warning(f"Rollback failed: {rollback_error}")

        # Cancel the job if it was created
        if job is not None:
            try:
                from backend_api.jobs import get_job_manager

                job_manager = get_job_manager()
                job_manager.fail_job(job.id, "Dataset creation failed, job cancelled")
            except Exception as cancel_error:
                logger.warning(f"Failed to cancel orphaned job {job.id}: {cancel_error}")

        logger.error(f"Failed to create dataset: {e}")

        # Check for UNIQUE constraint violation (extremely unlikely with UUID, but handle it)
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

    # Build export data
    export_data = {
        "dataset": {
            "id": row_dict["id"],
            "name": row_dict["name"],
            "regime": row_dict.get("orbital_regime"),
            "tier": row_dict.get("tier"),
            "observation_count": row_dict.get("observation_count"),
            "satellite_count": row_dict.get("satellite_count"),
            "created_at": str(row_dict["created_at"]) if row_dict.get("created_at") else None,
        },
        "observations": observations,
    }

    return JSONResponse(
        content=export_data,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{row_dict["name"]}.json"'},
    )
