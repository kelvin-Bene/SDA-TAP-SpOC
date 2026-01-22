"""Dataset management endpoints."""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from backend_api.database import get_db
from backend_api.jobs import get_job_manager
from backend_api.jobs.workers import submit_dataset_generation
from backend_api.models import (
    DatasetCreate,
    DatasetDetail,
    DatasetObservation,
    DatasetStatus,
    DatasetSummary,
    OrbitalRegime,
    DataTier,
    SensorType,
)
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


def _row_to_dataset_summary(row: tuple, columns: list) -> DatasetSummary:
    """Convert a database row to DatasetSummary model."""
    row_dict = dict(zip(columns, row))

    # Parse sensor types from JSON if present
    sensor_types = []
    if row_dict.get("generation_params"):
        try:
            params = json.loads(row_dict["generation_params"]) if isinstance(
                row_dict["generation_params"], str
            ) else row_dict.get("generation_params", {})
            sensor_types = params.get("sensors", ["optical"])
        except (json.JSONDecodeError, TypeError):
            sensor_types = ["optical"]

    return DatasetSummary(
        id=str(row_dict["id"]),
        name=row_dict["name"],
        description=row_dict.get("code"),  # Use code as description if no separate field
        regime=OrbitalRegime(row_dict.get("orbital_regime", "LEO")),
        tier=DataTier(row_dict.get("tier", "T1")),
        status=DatasetStatus(row_dict.get("status", "created")),
        created_at=row_dict["created_at"] or datetime.utcnow(),
        observation_count=row_dict.get("observation_count") or 0,
        satellite_count=row_dict.get("satellite_count") or 0,
        coverage=float(row_dict.get("avg_coverage") or 0),
        size_bytes=0,  # Would need to calculate from file if available
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
    result = db.execute(
        "SELECT * FROM datasets WHERE id = ?",
        (int(dataset_id),)
    )
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
            params = json.loads(row_dict["generation_params"]) if isinstance(
                row_dict["generation_params"], str
            ) else row_dict.get("generation_params", {})
            satellites = params.get("satIDs", [])
            sensor_types = params.get("sensors", ["optical"])
        except (json.JSONDecodeError, TypeError):
            pass

    return DatasetDetail(
        id=str(row_dict["id"]),
        name=row_dict["name"],
        description=row_dict.get("code"),
        regime=OrbitalRegime(row_dict.get("orbital_regime", "LEO")),
        tier=DataTier(row_dict.get("tier", "T1")),
        status=DatasetStatus(row_dict.get("status", "created")),
        created_at=row_dict["created_at"] or datetime.utcnow(),
        observation_count=row_dict.get("observation_count") or 0,
        satellite_count=row_dict.get("satellite_count") or 0,
        coverage=float(row_dict.get("avg_coverage") or 0),
        size_bytes=0,
        sensor_types=[SensorType(s) for s in sensor_types if s in ["optical", "radar", "rf"]],
        satellites=satellites,
        parameters=params,
        time_window_start=row_dict.get("time_window_start"),
        time_window_end=row_dict.get("time_window_end"),
        avg_obs_count=float(row_dict.get("avg_obs_count") or 0),
        max_track_gap=float(row_dict.get("max_track_gap") or 0),
        json_path=row_dict.get("json_path"),
    )


@router.post("/", response_model=DatasetSummary)
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
    # Prepare generation parameters
    generation_params = {
        "regime": request.regime.value,
        "tier": request.tier.value,
        "object_count": request.object_count,
        "timeframe": request.timeframe,
        "timeunit": request.timeunit,
        "sensors": [s.value for s in request.sensors],
        "coverage": request.coverage,
        "include_hamr": request.include_hamr,
        "name": request.name,
    }

    if request.satellites:
        generation_params["satellites"] = request.satellites

    if request.start_date:
        generation_params["start_date"] = request.start_date.isoformat()

    if request.end_date:
        generation_params["end_date"] = request.end_date.isoformat()

    # Create dataset record in database using RETURNING to get the ID
    result = db.execute(
        """
        INSERT INTO datasets (
            name, code, tier, orbital_regime, status, generation_params, created_at
        ) VALUES (?, ?, ?, ?, 'generating', ?, CURRENT_TIMESTAMP)
        RETURNING id
        """,
        (
            request.name,
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
    # First verify dataset exists
    dataset_check = db.execute(
        "SELECT id, observation_count FROM datasets WHERE id = ?",
        (int(dataset_id),)
    ).fetchone()

    if dataset_check is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    total_count = dataset_check[1] or 0

    # Query observations linked to this dataset
    result = db.execute(
        """
        SELECT o.id, o.ob_time, o.ra, o.declination, o.sensor_name, o.track_id
        FROM observations o
        JOIN dataset_observations do ON o.id = do.observation_id
        WHERE do.dataset_id = ?
        ORDER BY o.ob_time
        LIMIT ? OFFSET ?
        """,
        (int(dataset_id), limit, offset),
    )

    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    observations = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        observations.append(DatasetObservation(
            id=str(row_dict["id"]),
            ob_time=row_dict["ob_time"],
            ra=float(row_dict["ra"] or 0),
            declination=float(row_dict["declination"] or 0),
            sensor_name=row_dict.get("sensor_name"),
            track_id=str(row_dict["track_id"]) if row_dict.get("track_id") else None,
        ))

    return {
        "dataset_id": dataset_id,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "observations": observations,
    }


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
    # Get dataset info
    result = db.execute(
        "SELECT * FROM datasets WHERE id = ?",
        (int(dataset_id),)
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    row_dict = dict(zip(columns, row))

    if row_dict.get("status") != "available":
        raise HTTPException(
            status_code=400,
            detail="Dataset is not available for download"
        )

    # Get observations
    obs_result = db.execute(
        """
        SELECT o.*, do.assigned_track_id, do.assigned_object_id
        FROM observations o
        JOIN dataset_observations do ON o.id = do.observation_id
        WHERE do.dataset_id = ?
        ORDER BY o.ob_time
        """,
        (int(dataset_id),),
    )

    obs_columns = [desc[0] for desc in obs_result.description]
    obs_rows = obs_result.fetchall()

    observations = []
    for obs_row in obs_rows:
        obs_dict = dict(zip(obs_columns, obs_row))
        # Convert datetime to string for JSON
        if obs_dict.get("ob_time"):
            obs_dict["ob_time"] = obs_dict["ob_time"].isoformat() if hasattr(
                obs_dict["ob_time"], "isoformat"
            ) else str(obs_dict["ob_time"])
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
        headers={
            "Content-Disposition": f'attachment; filename="{row_dict["name"]}.json"'
        },
    )
