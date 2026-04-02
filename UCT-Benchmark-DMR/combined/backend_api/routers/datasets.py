"""Dataset management endpoints."""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger

from backend_api.database import get_db
from backend_api.jobs.workers import submit_dataset_generation
from backend_api.middleware.rate_limit import limiter
from backend_api.models import (
    DatasetCreate,
    DatasetDetail,
    DatasetObservation,
    DatasetStatus,
    DatasetSummary,
    DataTier,
    LegacyCodeValidation,
    LegacyDatasetCreate,
    OrbitalRegime,
    SearchStrategy,
    SensorType,
)
from uct_benchmark.config.dataset_schema import (
    LegacyDatasetCode,
    detect_code_format,
    validate_dataset_code,
    validate_legacy_code,
)
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


@router.get("/config")
async def get_dataset_config():
    """
    Return dataset configuration values from backend settings.

    Provides coverage thresholds, track gap multiplier, and observation count
    thresholds so the frontend stays in sync without hardcoding values.
    """
    from uct_benchmark.settings import (
        COVERAGE_THRESHOLDS,
        TRACK_GAP_LONG_MULTIPLIER,
        OBS_COUNT_LOW_THRESHOLD,
    )

    return {
        "coverage_thresholds": COVERAGE_THRESHOLDS,
        "track_gap_long_multiplier": TRACK_GAP_LONG_MULTIPLIER,
        "obs_count_low_threshold": OBS_COUNT_LOW_THRESHOLD,
    }


def _safe_json_parse(value) -> Any:
    """Safely parse a JSON value that may be a string, dict, or None."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


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
        created_at=row_dict["created_at"] or datetime.now(timezone.utc),
        observation_count=obs_count,
        satellite_count=row_dict.get("satellite_count") or 0,
        coverage=float(row_dict.get("avg_coverage") or 0),
        size_bytes=estimated_size,
        sensor_types=[SensorType(s) for s in sensor_types if s in ["optical", "radar", "rf"]],
        job_id=None,  # Could store this in generation_params
        version=int(row_dict.get("version") or 1),
        parent_id=str(row_dict["parent_id"]) if row_dict.get("parent_id") else None,
    )


@router.get("/", response_model=List[DatasetSummary])
async def list_datasets(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    regime: Optional[str] = None,
    tier: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: Optional[str] = None,
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
        search: Text search on dataset name and code
        sort_by: Column to sort by (name, created_at, satellite_count, observation_count)
        order: Sort order (asc, desc)

    Returns:
        List of dataset summaries
    """
    # S10: Clamp to safe ranges
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

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

    if search:
        query += " AND (LOWER(name) LIKE ? OR LOWER(COALESCE(code, '')) LIKE ?)"
        search_term = f"%{search.lower()}%"
        params.extend([search_term, search_term])

    # Sorting — whitelist allowed columns to prevent SQL injection
    allowed_sort = {"name", "created_at", "satellite_count", "observation_count", "tier", "orbital_regime"}
    sort_col = sort_by if sort_by in allowed_sort else "created_at"
    sort_dir = "ASC" if order and order.lower() == "asc" else "DESC"
    query += f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?"
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

    # Parse new JSON columns
    actual_satellite_ids = []
    if row_dict.get("actual_satellite_ids"):
        try:
            raw = row_dict["actual_satellite_ids"]
            actual_satellite_ids = json.loads(raw) if isinstance(raw, str) else (raw or [])
        except (json.JSONDecodeError, TypeError):
            pass

    performance_metadata = None
    if row_dict.get("performance_metadata"):
        try:
            raw = row_dict["performance_metadata"]
            performance_metadata = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: use actual_satellite_ids when generation_params lacks satIDs
    if not satellites and actual_satellite_ids:
        satellites = actual_satellite_ids

    return DatasetDetail(
        id=str(row_dict["id"]),
        name=row_dict["name"],
        description=row_dict.get("code"),
        regime=OrbitalRegime(row_dict.get("orbital_regime", "LEO")),
        tier=DataTier(row_dict.get("tier", "T1")),
        status=DatasetStatus(row_dict.get("status", "created")),
        created_at=row_dict["created_at"] or datetime.now(timezone.utc),
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
        actual_satellite_ids=actual_satellite_ids,
        performance_metadata=performance_metadata,
        downsampling_applied=bool(row_dict.get("downsampling_applied", False)),
        simulation_applied=bool(row_dict.get("simulation_applied", False)),
        simulated_obs_count=int(row_dict.get("simulated_obs_count") or 0),
        downsampling_config=_safe_json_parse(row_dict.get("downsampling_config")),
        simulation_config=_safe_json_parse(row_dict.get("simulation_config")),
        version=int(row_dict.get("version") or 1),
        parent_id=str(row_dict["parent_id"]) if row_dict.get("parent_id") else None,
    )


@router.get("/{dataset_id}/versions", response_model=List[DatasetSummary])
async def get_dataset_versions(
    dataset_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get version history for a dataset.

    Returns all versions of a dataset, linked by parent_id chain or matching
    legacy_code/generation config. Per Louis's transcript.md requirement:
    "if you did have a change, you want to have the ability to go back and look
    at the old data sets, but at the same time, look at the newer data sets"

    Args:
        dataset_id: The dataset ID to get version history for

    Returns:
        List of dataset summaries representing all versions
    """
    id_int = validate_dataset_id(dataset_id)

    # First get the target dataset to find its lineage
    target = db.execute(
        "SELECT id, legacy_code, parent_id, code FROM datasets WHERE id = ?", (id_int,)
    ).fetchone()

    if target is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    target_legacy_code = target[1]
    target_parent_id = target[2]
    target_code = target[3]

    # Find all related versions:
    # 1. Same legacy_code (regenerated datasets)
    # 2. Parent/child chain (versioned datasets)
    version_ids = {id_int}

    # Follow parent chain upward
    current_id = target_parent_id
    while current_id:
        version_ids.add(current_id)
        parent_row = db.execute(
            "SELECT parent_id FROM datasets WHERE id = ?", (current_id,)
        ).fetchone()
        current_id = parent_row[0] if parent_row else None

    # Find children (datasets with this ID as parent)
    children = db.execute(
        "SELECT id FROM datasets WHERE parent_id = ?", (id_int,)
    ).fetchall()
    for child in children:
        version_ids.add(child[0])

    # Also find by matching legacy_code if available
    if target_legacy_code:
        code_matches = db.execute(
            "SELECT id FROM datasets WHERE legacy_code = ?", (target_legacy_code,)
        ).fetchall()
        for match in code_matches:
            version_ids.add(match[0])

    # Query all version datasets
    placeholders = ",".join(["?" for _ in version_ids])
    result = db.execute(
        f"SELECT * FROM datasets WHERE id IN ({placeholders}) ORDER BY version DESC, created_at DESC",
        tuple(version_ids),
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    return [_row_to_dataset_summary(row, columns) for row in rows]


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
@limiter.limit("5/minute")
async def create_dataset(
    request: Request,
    dataset_request: DatasetCreate,
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
        f"Creating dataset with: name={dataset_request.name}, regime={dataset_request.regime}, tier={dataset_request.tier}"
    )
    # Prepare generation parameters (name will be set after uniqueness check)
    generation_params = {
        "regime": dataset_request.regime.value,
        "tier": dataset_request.tier.value,
        "object_count": dataset_request.object_count,
        "timeframe": dataset_request.timeframe,
        "timeunit": dataset_request.timeunit,
        "sensors": [s.value for s in dataset_request.sensors],
        "coverage": dataset_request.coverage,
        "include_hamr": dataset_request.include_hamr,
    }

    if dataset_request.satellites:
        generation_params["satellites"] = dataset_request.satellites

    if dataset_request.start_date:
        generation_params["start_date"] = dataset_request.start_date.isoformat()

    if dataset_request.end_date:
        generation_params["end_date"] = dataset_request.end_date.isoformat()

    # Add downsampling options if specified
    if dataset_request.downsampling:
        generation_params["downsampling"] = {
            "enabled": dataset_request.downsampling.enabled,
            "target_coverage": dataset_request.downsampling.target_coverage,
            "target_gap": dataset_request.downsampling.target_gap,
            "max_obs_per_sat": dataset_request.downsampling.max_obs_per_sat,
            "preserve_tracks": dataset_request.downsampling.preserve_tracks,
            "seed": dataset_request.downsampling.seed,
        }
        logger.info(f"Downsampling enabled: {dataset_request.downsampling.enabled}")

    # Add simulation options if specified
    if dataset_request.simulation:
        generation_params["simulation"] = {
            "enabled": dataset_request.simulation.enabled,
            "fill_gaps": dataset_request.simulation.fill_gaps,
            "sensor_model": dataset_request.simulation.sensor_model,
            "apply_noise": dataset_request.simulation.apply_noise,
            "max_synthetic_ratio": dataset_request.simulation.max_synthetic_ratio,
            "seed": dataset_request.simulation.seed,
        }
        logger.info(f"Simulation enabled: {dataset_request.simulation.enabled}")

    # Add search strategy
    generation_params["search_strategy"] = dataset_request.search_strategy.value
    if dataset_request.search_strategy == SearchStrategy.WINDOWED:
        generation_params["window_size_minutes"] = dataset_request.window_size_minutes or 10
    logger.info(f"Search strategy: {dataset_request.search_strategy.value}")

    # Add non-reference observation options (for True Negative calculation per Louis's spec)
    generation_params["include_non_ref_obs"] = dataset_request.include_non_ref_obs
    generation_params["non_ref_ratio"] = dataset_request.non_ref_ratio
    if dataset_request.include_non_ref_obs:
        logger.info(f"Non-ref observations enabled: ratio={dataset_request.non_ref_ratio}")

    # Add object type and event codes (per Louis's 16-character code spec)
    generation_params["object_type_code"] = getattr(dataset_request, "object_type_code", "U")
    generation_params["event_code"] = getattr(dataset_request, "event_code", "NE")

    # Add window selection option (per Louis's bisecting search spec)
    generation_params["use_window_selection"] = getattr(dataset_request, "use_window_selection", False)
    if generation_params["use_window_selection"]:
        logger.info("Window selection algorithm enabled")

    # Record target percentage and TrackTLE options for full provenance
    generation_params["target_percentage"] = getattr(dataset_request, "target_percentage", "UN")
    generation_params["output_tracktle"] = getattr(dataset_request, "output_tracktle", False)

    # Generate a unique dataset name using timestamp + UUID to avoid race conditions
    # The database has a UNIQUE constraint on name, so this ensures atomicity
    # Format: {user_name}-{YYYYMMDD}-{HHMMSS}-{short_uuid}
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    dataset_name = f"{dataset_request.name}-{timestamp}-{short_uuid}"
    logger.info(f"Generated unique dataset name: {dataset_name}")

    # Add the final unique name to generation params
    generation_params["name"] = dataset_name

    # Version tracking: check for existing datasets with same base name
    # Per undated transcript: "if you did have a change, you want to have the ability
    # to go back and look at the old data sets"
    version = 1
    parent_id = None
    try:
        # Find the latest version of a dataset with the same user-provided base name
        existing = db.execute(
            """
            SELECT id, version FROM datasets
            WHERE name LIKE ?
            ORDER BY version DESC, created_at DESC
            LIMIT 1
            """,
            (f"{dataset_request.name}-%",),
        ).fetchone()
        if existing:
            parent_id = existing[0]
            version = (existing[1] or 1) + 1
            logger.info(f"Dataset version tracking: parent_id={parent_id}, version={version}")
    except Exception as e:
        logger.debug(f"Version tracking lookup failed (non-critical): {e}")

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
                name, code, tier, orbital_regime, status, generation_params,
                version, parent_id, created_at
            ) VALUES (?, ?, ?, ?, 'generating', ?, ?, ?, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (
                dataset_name,
                f"{dataset_request.regime.value}_{dataset_request.tier.value}",
                dataset_request.tier.value,
                dataset_request.regime.value,
                json.dumps(generation_params),
                version,
                parent_id,
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
        name=dataset_request.name,
        description=None,
        regime=dataset_request.regime,
        tier=dataset_request.tier,
        status=DatasetStatus.GENERATING,
        created_at=datetime.now(timezone.utc),
        observation_count=0,
        satellite_count=dataset_request.object_count,
        coverage=0.0,
        size_bytes=0,
        sensor_types=dataset_request.sensors,
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
    # S10: Clamp to safe ranges
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

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

    # Query all observation fields linked to this dataset
    # Per Feb 19 transcript: "Cannot arbitrarily remove fields as unknown processors may need them"
    result = db.execute(
        """
        SELECT o.id, o.ob_time, o.ra, o.declination,
               o.azimuth, o.elevation, o.range_km,
               o.sensor_id, o.sensor_name, o.data_mode, o.type_optical,
               o.send_lat, o.send_long, o.send_alt,
               o.track_id, o.is_simulated
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
                ra=float(row_dict["ra"]) if row_dict.get("ra") is not None else None,
                declination=float(row_dict["declination"]) if row_dict.get("declination") is not None else None,
                azimuth=float(row_dict["azimuth"]) if row_dict.get("azimuth") is not None else None,
                elevation=float(row_dict["elevation"]) if row_dict.get("elevation") is not None else None,
                range_km=float(row_dict["range_km"]) if row_dict.get("range_km") is not None else None,
                sensor_id=row_dict.get("sensor_id"),
                sensor_name=row_dict.get("sensor_name"),
                data_mode=row_dict.get("data_mode"),
                type_optical=row_dict.get("type_optical"),
                send_lat=float(row_dict["send_lat"]) if row_dict.get("send_lat") is not None else None,
                send_long=float(row_dict["send_long"]) if row_dict.get("send_long") is not None else None,
                send_alt=float(row_dict["send_alt"]) if row_dict.get("send_alt") is not None else None,
                track_id=str(row_dict["track_id"]) if row_dict.get("track_id") else None,
                is_simulated=row_dict.get("is_simulated"),
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


@router.get("/{dataset_id}/sample-submission")
async def get_sample_submission(
    dataset_id: str,
    quality: str = "high",
    db: DatabaseManager = Depends(get_db),
):
    """
    Generate a mock UCTP output file for demo mode.

    Returns a downloadable JSON file with synthetic UCTP results
    at the specified quality level.

    Args:
        dataset_id: The dataset ID
        quality: Quality level - 'high', 'medium', or 'low'
    """
    import random as _random

    from backend_api.demo import is_demo_mode

    if not is_demo_mode():
        raise HTTPException(status_code=404, detail="Not found")

    id_int = validate_dataset_id(dataset_id)

    # Get dataset observations
    rows = db.execute(
        """
        SELECT o.id, o.sat_no, o.ob_time, o.ra, o.declination
        FROM observations o
        JOIN dataset_observations dso ON o.id = dso.observation_id
        WHERE dso.dataset_id = ?
        ORDER BY o.ob_time
        LIMIT 2000
        """,
        (id_int,),
    ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No observations found for this dataset")

    # Quality determines match rate and error magnitude
    quality_params = {
        "high": {"match_rate": 0.95, "pos_err": 0.5, "vel_err": 0.01},
        "medium": {"match_rate": 0.75, "pos_err": 5.0, "vel_err": 0.1},
        "low": {"match_rate": 0.50, "pos_err": 20.0, "vel_err": 0.5},
    }
    params = quality_params.get(quality, quality_params["medium"])

    rng = _random.Random(id_int + hash(quality))
    uctp_results = []

    # Group observations by sat_no
    grouped: dict[int, list] = {}
    for row in rows:
        obs_id, sat_no, ob_time, ra, dec = row
        grouped.setdefault(sat_no, []).append((obs_id, ob_time, ra, dec))

    for sat_no, obs_list in grouped.items():
        # Decide if this satellite is correctly matched
        if rng.random() > params["match_rate"]:
            continue

        # Generate a state vector with controlled error
        base_x = rng.uniform(-8000, 8000)
        base_y = rng.uniform(-8000, 8000)
        base_z = rng.uniform(-8000, 8000)

        uctp_results.append({
            "sourcedData": [obs[0] for obs in obs_list],
            "epoch": obs_list[0][1] if isinstance(obs_list[0][1], str) else str(obs_list[0][1]),
            "xpos": round(base_x + rng.gauss(0, params["pos_err"]), 6),
            "ypos": round(base_y + rng.gauss(0, params["pos_err"]), 6),
            "zpos": round(base_z + rng.gauss(0, params["pos_err"]), 6),
            "xvel": round(rng.uniform(-7.5, 7.5) + rng.gauss(0, params["vel_err"]), 9),
            "yvel": round(rng.uniform(-7.5, 7.5) + rng.gauss(0, params["vel_err"]), 9),
            "zvel": round(rng.uniform(-7.5, 7.5) + rng.gauss(0, params["vel_err"]), 9),
        })

    # Add some false positives for low/medium quality
    if quality in ("low", "medium"):
        num_fp = int(len(uctp_results) * (0.15 if quality == "medium" else 0.30))
        for _ in range(num_fp):
            uctp_results.append({
                "sourcedData": [f"false-{rng.randint(10000, 99999)}"],
                "epoch": str(rows[0][2]),
                "xpos": round(rng.uniform(-10000, 10000), 6),
                "ypos": round(rng.uniform(-10000, 10000), 6),
                "zpos": round(rng.uniform(-10000, 10000), 6),
                "xvel": round(rng.uniform(-8, 8), 9),
                "yvel": round(rng.uniform(-8, 8), 9),
                "zvel": round(rng.uniform(-8, 8), 9),
            })

    from fastapi.responses import Response

    content = json.dumps(uctp_results, indent=2)
    filename = f"sample_uctp_dataset{dataset_id}_{quality}.json"

    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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

    # Map DB snake_case columns to Benchmarking Documentation camelCase names
    DB_TO_DOC_FIELD_MAP = {
        "ob_time": "obTime",
        "sat_no": "satNo",
        "range_km": "range",
        "range_rate_km_s": "rangeRate",
        "sensor_id": "idSensor",
        "sensor_name": "sensorName",
        "data_mode": "dataMode",
        "type_optical": "typeOptical",
        "send_lat": "senlat",
        "send_long": "senlon",
        "send_alt": "senalt",
        "track_id": "trackId",
        "is_uct": "uct",
        "is_simulated": "isSimulated",
        "created_at": "createdAt",
        "classification_marking": "classificationMarking",
        "id_on_orbit": "idOnOrbit",
        "task_id": "taskId",
        "orig_object_id": "origObjectId",
        "orig_sensor_id": "origSensorId",
        "sen_x": "senx",
        "sen_y": "seny",
        "sen_z": "senz",
        "sen_vel_x": "senvelx",
        "sen_vel_y": "senvely",
        "sen_vel_z": "senvelz",
        "exp_duration": "expDuration",
        "net_obj_sig": "netObjSig",
        "net_obj_sig_unc": "netObjSigUnc",
        "mag_unc": "magUnc",
        "geo_lat": "geolat",
        "geo_lon": "geolon",
        "geo_alt": "geoalt",
        "geo_range": "georange",
        "solar_phase_angle": "solarPhaseAngle",
        "solar_eq_phase_angle": "solarEqPhaseAngle",
        "solar_dec_angle": "solarDecAngle",
        "shutter_delay": "shutterDelay",
        "raw_file_uri": "rawFileURI",
        "created_by": "createdBy",
        "orig_network": "origNetwork",
        "los_unc": "losUnc",
        "obs_type": "type",
    }

    observations = []
    for obs_row in obs_rows:
        obs_dict = dict(zip(obs_columns, obs_row))
        # Convert non-JSON-serializable types (Decimal, datetime) to primitives
        for key, value in list(obs_dict.items()):
            if hasattr(value, "isoformat"):
                obs_dict[key] = value.isoformat()
            elif isinstance(value, Decimal):
                obs_dict[key] = float(value)
        # Rename DB columns to doc-matching camelCase names
        obs_dict = {DB_TO_DOC_FIELD_MAP.get(k, k): v for k, v in obs_dict.items()}
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


# ============================================================
# LEGACY CODE ENDPOINTS
# ============================================================


@router.post("/legacy", response_model=DatasetSummary, status_code=201)
async def create_dataset_from_legacy_code(
    request: LegacyDatasetCreate,
    db: DatabaseManager = Depends(get_db),
):
    """
    Create a new dataset using legacy 16-character code format.

    This endpoint creates a dataset using Louis's documented 16-character format.
    You can either provide the complete code string or individual components.

    Format: OTTRRREWSSCSNS##
    Example: H50LEONEOPSSSS07 = HAMR, 50% target, LEO, No Events, Optical, Standard metrics, 7 days

    Args:
        request: Legacy dataset creation parameters

    Returns:
        The created dataset summary with job_id for tracking progress
    """
    # Generate or validate the legacy code
    legacy_code = request.to_legacy_code()

    # Validate the code
    is_valid, error_msg = validate_legacy_code(legacy_code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid legacy code: {error_msg}")

    # Parse the code to get all components
    parsed = LegacyDatasetCode.from_code(legacy_code)

    # Map legacy sensor to API sensor type
    sensor_map = {
        "OP": SensorType.OPTICAL,
        "RA": SensorType.RADAR,
        "RF": SensorType.RF,
        "FU": SensorType.OPTICAL,  # Fusion defaults to optical primary
        "OR": SensorType.OPTICAL,
        "RO": SensorType.RADAR,
        "RR": SensorType.RADAR,
    }
    sensor_type = sensor_map.get(parsed.sensor_type, SensorType.OPTICAL)

    # Map object count level to actual count
    object_count = parsed.get_object_count_value()

    # Map coverage level to downsampling configuration
    downsample_config = parsed.get_downsample_config()

    # Generate dataset name
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    dataset_name = request.name or f"{legacy_code}-{timestamp}-{short_uuid}"

    # Build generation parameters
    generation_params = {
        "name": dataset_name,
        "legacy_code": legacy_code,
        "regime": parsed.orbital_regime,
        "tier": "T" + str({'A': 1, 'S': 2, 'N': 3}.get(parsed.orbit_coverage, 2)),
        "object_count": object_count,
        "timeframe": parsed.fitspan_days,
        "timeunit": "days",
        "sensors": [sensor_type.value],
        "coverage": {"A": "high", "S": "standard", "N": "low"}.get(parsed.orbit_coverage, "standard"),
        "include_hamr": parsed.object_type == "H",
        # Store all legacy components
        "legacy_components": {
            "object_type": parsed.object_type,
            "target_percentage": parsed.target_percentage,
            "orbital_regime": parsed.orbital_regime,
            "event": parsed.event,
            "sensor_type": parsed.sensor_type,
            "orbit_coverage": parsed.orbit_coverage,
            "track_gap": parsed.track_gap,
            "observation_count": parsed.observation_count,
            "object_count": parsed.object_count,
            "fitspan_days": parsed.fitspan_days,
        },
    }

    if request.start_date:
        generation_params["start_date"] = request.start_date.isoformat()

    # Add downsampling based on coverage level
    if parsed.orbit_coverage in ["A", "S"]:  # High or Standard coverage = need downsampling
        generation_params["downsampling"] = {
            "enabled": True,
            "target_coverage": downsample_config["target_coverage"],
            "target_gap": 2.0,  # Default gap target
            "max_obs_per_sat": 50,
            "preserve_tracks": True,
        }

    # Add simulation if coverage level is N (low/sparse data needed)
    if parsed.orbit_coverage == "N":
        generation_params["simulation"] = {
            "enabled": False,  # Don't simulate for low coverage - we want sparse data
        }

    logger.info(f"Creating dataset from legacy code: {legacy_code}")

    # Map regime to OrbitalRegime enum
    regime_map = {"LEO": OrbitalRegime.LEO, "MEO": OrbitalRegime.MEO, "GEO": OrbitalRegime.GEO, "HEO": OrbitalRegime.HEO}
    regime = regime_map.get(parsed.orbital_regime, OrbitalRegime.LEO)

    # Map tier
    tier_map = {"A": DataTier.T1, "S": DataTier.T2, "N": DataTier.T3}
    tier = tier_map.get(parsed.orbit_coverage, DataTier.T2)

    # Use transaction for atomicity
    job = None
    dataset_id = None

    try:
        db.execute("BEGIN TRANSACTION")

        # Create dataset with legacy code fields
        result = db.execute(
            """
            INSERT INTO datasets (
                name, code, legacy_code,
                object_type_code, target_percentage, event_code, sensor_code,
                coverage_level, track_gap_level, obs_count_level, object_count_level, fitspan_days,
                tier, orbital_regime, status, generation_params, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'generating', ?, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (
                dataset_name,
                parsed.to_enhanced().to_code(),  # Enhanced code
                legacy_code,
                parsed.object_type,
                parsed.target_percentage,
                parsed.event,
                parsed.sensor_type,
                parsed.orbit_coverage,
                parsed.track_gap,
                parsed.observation_count,
                parsed.object_count,
                parsed.fitspan_days,
                tier.value,
                regime.value,
                json.dumps(generation_params),
            ),
        )
        dataset_id = result.fetchone()[0]

        # Submit background job
        job = submit_dataset_generation(dataset_id, generation_params)

        # Update with job_id
        db.execute(
            "UPDATE datasets SET generation_params = ? WHERE id = ?",
            (json.dumps({**generation_params, "job_id": job.id}), dataset_id),
        )

        db.execute("COMMIT")

    except Exception as e:
        try:
            db.execute("ROLLBACK")
        except Exception as rollback_error:
            logger.warning(f"Rollback failed during legacy dataset creation: {rollback_error}")

        if job is not None:
            try:
                from backend_api.jobs import get_job_manager
                job_manager = get_job_manager()
                job_manager.fail_job(job.id, "Dataset creation failed")
            except Exception as cancel_error:
                logger.warning(f"Failed to cancel orphaned job {job.id}: {cancel_error}")

        logger.error(f"Failed to create dataset from legacy code: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create dataset: {str(e)}")

    return DatasetSummary(
        id=str(dataset_id),
        name=dataset_name,
        description=request.description,
        regime=regime,
        tier=tier,
        status=DatasetStatus.GENERATING,
        created_at=datetime.now(timezone.utc),
        observation_count=0,
        satellite_count=object_count,
        coverage=0.0,
        size_bytes=0,
        sensor_types=[sensor_type],
        job_id=job.id,
        legacy_code=legacy_code,
        code=parsed.to_enhanced().to_code(),
    )


@router.get("/code/{legacy_code}", response_model=DatasetDetail)
async def get_dataset_by_legacy_code(
    legacy_code: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get a dataset by its legacy 16-character code.

    Args:
        legacy_code: The 16-character legacy dataset code

    Returns:
        Dataset details if found
    """
    # Validate the code format
    if len(legacy_code) != 16:
        raise HTTPException(status_code=400, detail="Legacy code must be exactly 16 characters")

    is_valid, error_msg = validate_legacy_code(legacy_code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid legacy code: {error_msg}")

    # Query by legacy_code
    result = db.execute("SELECT * FROM datasets WHERE legacy_code = ?", (legacy_code,))
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No dataset found with legacy code: {legacy_code}")

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
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse generation_params for dataset {legacy_code}: {e}")

    obs_count = row_dict.get("observation_count") or 0
    estimated_size = obs_count * 500

    # Parse new JSON columns
    actual_satellite_ids = []
    if row_dict.get("actual_satellite_ids"):
        try:
            raw = row_dict["actual_satellite_ids"]
            actual_satellite_ids = json.loads(raw) if isinstance(raw, str) else (raw or [])
        except (json.JSONDecodeError, TypeError):
            pass

    performance_metadata = None
    if row_dict.get("performance_metadata"):
        try:
            raw = row_dict["performance_metadata"]
            performance_metadata = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: use actual_satellite_ids when generation_params lacks satIDs
    if not satellites and actual_satellite_ids:
        satellites = actual_satellite_ids

    return DatasetDetail(
        id=str(row_dict["id"]),
        name=row_dict["name"],
        description=row_dict.get("code"),
        regime=OrbitalRegime(row_dict.get("orbital_regime", "LEO")),
        tier=DataTier(row_dict.get("tier", "T1")),
        status=DatasetStatus(row_dict.get("status", "created")),
        created_at=row_dict["created_at"] or datetime.now(timezone.utc),
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
        legacy_code=row_dict.get("legacy_code"),
        code=row_dict.get("code"),
        # Legacy component fields
        object_type_code=row_dict.get("object_type_code"),
        target_percentage=row_dict.get("target_percentage"),
        event_code=row_dict.get("event_code"),
        sensor_code=row_dict.get("sensor_code"),
        coverage_level=row_dict.get("coverage_level"),
        track_gap_level=row_dict.get("track_gap_level"),
        obs_count_level=row_dict.get("obs_count_level"),
        object_count_level=row_dict.get("object_count_level"),
        fitspan_days=row_dict.get("fitspan_days"),
        actual_satellite_ids=actual_satellite_ids,
        performance_metadata=performance_metadata,
        downsampling_applied=bool(row_dict.get("downsampling_applied", False)),
        simulation_applied=bool(row_dict.get("simulation_applied", False)),
        simulated_obs_count=int(row_dict.get("simulated_obs_count") or 0),
        downsampling_config=_safe_json_parse(row_dict.get("downsampling_config")),
        simulation_config=_safe_json_parse(row_dict.get("simulation_config")),
    )


@router.get("/validate/{code}", response_model=LegacyCodeValidation)
async def validate_code(code: str):
    """
    Validate a dataset code in either legacy or enhanced format.

    Args:
        code: Dataset code to validate (legacy 16-char or enhanced underscore-separated)

    Returns:
        Validation result with parsed components if valid
    """
    format_type = detect_code_format(code)

    if format_type == "legacy":
        is_valid, error_msg = validate_legacy_code(code)
        components = None

        if is_valid:
            parsed = LegacyDatasetCode.from_code(code)
            components = {
                "object_type": parsed.object_type,
                "target_percentage": parsed.target_percentage,
                "orbital_regime": parsed.orbital_regime,
                "event": parsed.event,
                "sensor_type": parsed.sensor_type,
                "orbit_coverage": parsed.orbit_coverage,
                "track_gap": parsed.track_gap,
                "observation_count": parsed.observation_count,
                "object_count": parsed.object_count,
                "fitspan_days": parsed.fitspan_days,
                "description": parsed.describe(),
            }

        return LegacyCodeValidation(
            code=code,
            is_valid=is_valid,
            format_type="legacy",
            error_message=error_msg,
            components=components,
        )

    elif format_type == "enhanced":
        is_valid, error_msg = validate_dataset_code(code)
        components = None

        if is_valid:
            from uct_benchmark.config.dataset_schema import EnhancedDatasetCode
            parsed = EnhancedDatasetCode.from_code(code)
            components = {
                "object_type": parsed.object_type,
                "regime": parsed.regime,
                "event": parsed.event,
                "sensor": parsed.sensor,
                "quality_tier": parsed.quality_tier,
                "time_window_days": parsed.time_window_days,
                "version": parsed.version,
            }

        return LegacyCodeValidation(
            code=code,
            is_valid=is_valid,
            format_type="enhanced",
            error_message=error_msg,
            components=components,
        )

    else:
        return LegacyCodeValidation(
            code=code,
            is_valid=False,
            format_type="unknown",
            error_message="Cannot detect code format. Expected 16-char legacy or underscore-separated enhanced format.",
            components=None,
        )
