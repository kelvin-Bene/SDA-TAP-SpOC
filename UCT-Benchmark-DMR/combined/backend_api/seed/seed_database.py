"""
seed_database.py — populate an empty DuckDB with bundled sample data on first
DGX Spark boot.

Idempotent. Safe to call on every startup; bails out within a single SQL query
if the observations table already has rows.

Search order for the seed_data directory:
    1. $DGX_SEED_DATA_PATH (env var override)
    2. /app/data/seed                   (canonical container mount)
    3. <repo>/data/seed                 (dev box checkout)
    4. <repo>/deploy/dgx-spark/seed_data (when run from the source tree)
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

if TYPE_CHECKING:
    from uct_benchmark.database.connection import DatabaseManager


# ───────────────────────────────────────────────────────────────────────────
# Seed file expectations + column maps (CSV column → DB column)
# ───────────────────────────────────────────────────────────────────────────

_SEED_FILES = {
    "satellites": "satelliteData_Full.csv",
    "observations": "observations_.csv",
}

# observations_.csv → observations table
_OBSERVATIONS_COLUMN_MAP: dict[str, str] = {
    "id": "id",
    "satNo": "sat_no",
    "obTime": "ob_time",
    "ra": "ra",
    "declination": "declination",
    "range": "range_km",
    "azimuth": "azimuth",
    "elevation": "elevation",
    "idSensor": "sensor_id",
    "dataMode": "data_mode",
    "type": "type_optical",
    "senlat": "send_lat",
    "senlon": "send_long",
    "senalt": "send_alt",
    "uct": "is_uct",
    "classificationMarking": "classification_marking",
    "idOnOrbit": "id_on_orbit",
    "taskId": "task_id",
    "origObjectId": "orig_object_id",
    "origSensorId": "orig_sensor_id",
    "senx": "sen_x",
    "seny": "sen_y",
    "senz": "sen_z",
    "expDuration": "exp_duration",
    "mag": "mag",
    "magUnc": "mag_unc",
    "geolat": "geo_lat",
    "geolon": "geo_lon",
    "geoalt": "geo_alt",
    "georange": "geo_range",
}

# satelliteData_Full.csv → satellites table
_SATELLITES_COLUMN_MAP: dict[str, str] = {
    "satNo": "sat_no",
    "name": "name",
    "cosparId": "cospar_id",
    "objectClass": "object_type",
    "mass": "mass_kg",
    "xSectAvg": "cross_section_m2",
}

_DGX_SEED_DATASET_NAME = "DGX_SEED_SAMPLE"


def _candidate_seed_dirs() -> list[Path]:
    """All directories the loader will inspect, in priority order."""
    candidates: list[Path] = []
    env = os.getenv("DGX_SEED_DATA_PATH")
    if env:
        candidates.append(Path(env))
    candidates.append(Path("/app/data/seed"))
    # Walk up from this file: backend_api/seed/seed_database.py → combined/
    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / "data" / "seed")
    candidates.append(repo_root / "deploy" / "dgx-spark" / "seed_data")
    return candidates


def find_seed_dir() -> Optional[Path]:
    """Locate the bundled seed data directory by searching common paths."""
    for path in _candidate_seed_dirs():
        if path.is_dir() and (path / _SEED_FILES["observations"]).exists():
            return path
    return None


def maybe_seed_database(db: "DatabaseManager") -> None:
    """
    Populate the database with bundled sample data if it's empty.

    No-ops on PostgreSQL backends, when the observations table already has rows,
    or when no seed_data directory can be located. Logged at INFO level so the
    skip reason is visible in container logs.
    """
    if db.backend != "duckdb":
        logger.debug("Seed loader: backend is {}, skipping", db.backend)
        return

    # Idempotency check — single SQL query, cheap.
    try:
        result = db.execute("SELECT COUNT(*) FROM observations").fetchone()
        existing_count = int(result[0]) if result else 0
    except Exception as exc:
        logger.warning("Seed loader: could not query observations count: {}", exc)
        return

    if existing_count > 0:
        logger.info("Seed loader: observations table already has {} rows, skipping", existing_count)
        return

    seed_dir = find_seed_dir()
    if not seed_dir:
        logger.info(
            "Seed loader: no seed_data directory found in any of {}",
            [str(p) for p in _candidate_seed_dirs()],
        )
        return

    logger.info("Seed loader: populating empty DuckDB from {}", seed_dir)

    sats_loaded = _load_satellites(db, seed_dir)
    obs_loaded = _load_observations(db, seed_dir)

    if obs_loaded > 0:
        _create_seed_dataset(db, sat_count=sats_loaded, obs_count=obs_loaded)

    logger.info(
        "Seed loader: complete — {} satellites, {} observations",
        sats_loaded,
        obs_loaded,
    )


# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────


def _build_select_clauses(column_map: dict[str, str]) -> tuple[str, str]:
    """
    Return (select_list, target_columns) for an `INSERT ... SELECT` statement
    that maps CSV columns (camelCase, quoted) to DB columns (snake_case).
    """
    select_list = ", ".join(f'"{src}" AS {dst}' for src, dst in column_map.items())
    target_columns = ", ".join(column_map.values())
    return select_list, target_columns


def _load_satellites(db: "DatabaseManager", seed_dir: Path) -> int:
    csv_path = seed_dir / _SEED_FILES["satellites"]
    if not csv_path.exists():
        logger.info("Seed loader: {} not found, skipping satellites", csv_path.name)
        return 0

    select_list, target_columns = _build_select_clauses(_SATELLITES_COLUMN_MAP)
    csv_uri = csv_path.as_posix()

    # Bundled CSVs may have multiple rows per satNo (e.g. catalog refreshes
    # over time). Deduplicate by satNo before insert; the first row wins.
    sql = f"""
        INSERT INTO satellites ({target_columns})
        SELECT {select_list}
        FROM (
            SELECT * EXCLUDE rn FROM (
                SELECT
                    *,
                    row_number() OVER (PARTITION BY "satNo" ORDER BY "satNo") AS rn
                FROM read_csv_auto('{csv_uri}', header=true, ignore_errors=true)
                WHERE "satNo" IS NOT NULL
            )
            WHERE rn = 1
        )
    """
    try:
        db.execute(sql)
        result = db.execute("SELECT COUNT(*) FROM satellites").fetchone()
        return int(result[0]) if result else 0
    except Exception as exc:
        logger.warning("Seed loader: satellites load failed ({}): {}", csv_path.name, exc)
        return 0


def _load_observations(db: "DatabaseManager", seed_dir: Path) -> int:
    csv_path = seed_dir / _SEED_FILES["observations"]
    if not csv_path.exists():
        logger.info("Seed loader: {} not found, skipping observations", csv_path.name)
        return 0

    select_list, target_columns = _build_select_clauses(_OBSERVATIONS_COLUMN_MAP)
    csv_uri = csv_path.as_posix()

    sql = f"""
        INSERT INTO observations ({target_columns})
        SELECT {select_list}
        FROM read_csv_auto('{csv_uri}', header=true, ignore_errors=true)
        WHERE "id" IS NOT NULL
    """
    try:
        db.execute(sql)
        result = db.execute("SELECT COUNT(*) FROM observations").fetchone()
        return int(result[0]) if result else 0
    except Exception as exc:
        logger.warning("Seed loader: observations load failed ({}): {}", csv_path.name, exc)
        return 0


def _create_seed_dataset(db: "DatabaseManager", *, sat_count: int, obs_count: int) -> None:
    """Create a single sample dataset row that links to all loaded observations."""
    try:
        existing = db.execute(
            "SELECT id FROM datasets WHERE name = ?", (_DGX_SEED_DATASET_NAME,)
        ).fetchone()
        if existing:
            logger.info("Seed loader: dataset '{}' already exists (id={}), skipping", _DGX_SEED_DATASET_NAME, existing[0])
            return

        db.execute(
            """
            INSERT INTO datasets (
                name, code, legacy_code, tier, orbital_regime,
                observation_count, satellite_count, status,
                generation_params, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _DGX_SEED_DATASET_NAME,
                "A50LEONOPSAAA07",
                "A50LEONOPSAAA07",
                "T2",
                "LEO",
                obs_count,
                sat_count,
                "complete",
                '{"source": "dgx_seed", "bundled": true}',
                "demo-user",
            ),
        )

        result = db.execute(
            "SELECT id FROM datasets WHERE name = ?", (_DGX_SEED_DATASET_NAME,)
        ).fetchone()
        if not result:
            logger.warning("Seed loader: dataset insert succeeded but row not found")
            return
        dataset_id = int(result[0])

        # Link every loaded observation to the seed dataset.
        db.execute(
            f"""
            INSERT INTO dataset_observations (dataset_id, observation_id)
            SELECT {dataset_id}, id FROM observations
            """
        )

        logger.info(
            "Seed loader: created dataset id={} ('{}') with {} observations",
            dataset_id,
            _DGX_SEED_DATASET_NAME,
            obs_count,
        )
    except Exception as exc:
        logger.warning("Seed loader: dataset creation failed: {}", exc)
