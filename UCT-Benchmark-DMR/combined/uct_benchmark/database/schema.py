"""
Database schema definitions for UCT Benchmark.

Provides SQL schema creation statements and migration utilities.
Supports both DuckDB and PostgreSQL backends.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .connection import DatabaseManager

# Schema version for migration tracking
SCHEMA_VERSION = "1.0.0"

# ============================================================
# DUCKDB SCHEMA CREATION SQL
# ============================================================

SATELLITES_TABLE = """
CREATE TABLE IF NOT EXISTS satellites (
    sat_no INTEGER PRIMARY KEY,           -- NORAD catalog number
    name VARCHAR(100),
    cospar_id VARCHAR(20),
    object_type VARCHAR(20),              -- PAYLOAD, ROCKET BODY, DEBRIS
    launch_date DATE,
    decay_date DATE,

    -- Physical properties (from ESA DiscoWeb)
    mass_kg DECIMAL(10,2),
    cross_section_m2 DECIMAL(10,4),
    drag_coeff DECIMAL(6,4) DEFAULT 2.5,
    srp_coeff DECIMAL(6,4) DEFAULT 1.5,

    -- Orbital classification
    orbital_regime VARCHAR(10),           -- LEO, MEO, GEO, HEO

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

OBSERVATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS observations (
    id VARCHAR(64) PRIMARY KEY,           -- UDL observation ID
    sat_no INTEGER,                        -- References satellites(sat_no)

    -- Temporal
    ob_time TIMESTAMP NOT NULL,

    -- Positional (Optical - RA/Dec)
    ra DECIMAL(12,8),                     -- Right Ascension (degrees)
    declination DECIMAL(12,8),            -- Declination (degrees)

    -- Positional (Radar - optional)
    range_km DECIMAL(12,4),
    range_rate_km_s DECIMAL(10,6),
    azimuth DECIMAL(12,8),
    elevation DECIMAL(12,8),

    -- Sensor metadata
    sensor_name VARCHAR(100),
    data_mode VARCHAR(20),                -- REAL, SIMULATED

    -- Track association
    track_id VARCHAR(64),

    -- UCT processing flags
    is_uct BOOLEAN DEFAULT FALSE,
    is_simulated BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

OBSERVATIONS_INDEXES = """
-- Time-based index for efficient range queries
CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_sat_time ON observations(sat_no, ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_track ON observations(track_id);
"""

STATE_VECTORS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS state_vectors_id_seq;
"""

STATE_VECTORS_TABLE = """
CREATE TABLE IF NOT EXISTS state_vectors (
    id INTEGER PRIMARY KEY DEFAULT nextval('state_vectors_id_seq'),
    sat_no INTEGER,                        -- References satellites(sat_no)

    -- Epoch
    epoch TIMESTAMP NOT NULL,

    -- Position (J2000 ECI, km)
    x_pos DECIMAL(16,6) NOT NULL,
    y_pos DECIMAL(16,6) NOT NULL,
    z_pos DECIMAL(16,6) NOT NULL,

    -- Velocity (J2000 ECI, km/s)
    x_vel DECIMAL(16,9) NOT NULL,
    y_vel DECIMAL(16,9) NOT NULL,
    z_vel DECIMAL(16,9) NOT NULL,

    -- Covariance (6x6 matrix, stored as JSON array)
    covariance JSON,

    -- Source metadata
    source VARCHAR(50),                   -- UDL, SPACE_TRACK, PROPAGATED
    data_mode VARCHAR(20),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(sat_no, epoch, source)
);
"""

STATE_VECTORS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_sv_sat_epoch ON state_vectors(sat_no, epoch);
"""

ELEMENT_SETS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS element_sets_id_seq;
"""

ELEMENT_SETS_TABLE = """
CREATE TABLE IF NOT EXISTS element_sets (
    id INTEGER PRIMARY KEY DEFAULT nextval('element_sets_id_seq'),
    sat_no INTEGER,                        -- References satellites(sat_no)

    -- Raw TLE lines
    line1 VARCHAR(70) NOT NULL,
    line2 VARCHAR(70) NOT NULL,

    -- Parsed orbital elements
    epoch TIMESTAMP NOT NULL,
    inclination DECIMAL(10,6),            -- degrees
    raan DECIMAL(10,6),                   -- Right Ascension of Ascending Node
    eccentricity DECIMAL(12,10),
    arg_perigee DECIMAL(10,6),            -- Argument of Perigee
    mean_anomaly DECIMAL(10,6),
    mean_motion DECIMAL(14,10),           -- rev/day
    b_star DECIMAL(16,12),

    -- Derived values
    semi_major_axis_km DECIMAL(12,4),
    period_minutes DECIMAL(10,4),

    -- Metadata
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(sat_no, epoch)
);
"""

ELEMENT_SETS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_elset_sat_epoch ON element_sets(sat_no, epoch);
"""

DATASETS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS datasets_id_seq;
"""

DATASETS_TABLE = """
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY DEFAULT nextval('datasets_id_seq'),
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(20),                     -- e.g., "LEO_A_H_H_H"

    -- Version tracking
    version INTEGER DEFAULT 1,
    parent_id INTEGER,                    -- For version lineage

    -- Configuration
    tier VARCHAR(5),                      -- T1, T2, T3, T4, T5
    orbital_regime VARCHAR(10),
    time_window_start TIMESTAMP,
    time_window_end TIMESTAMP,

    -- Statistics
    observation_count INTEGER,
    satellite_count INTEGER,

    -- Quality metrics
    avg_coverage DECIMAL(8,4),
    avg_obs_count DECIMAL(8,2),
    max_track_gap DECIMAL(8,4),

    -- Downsampling and Simulation tracking
    downsampling_applied BOOLEAN DEFAULT FALSE,
    simulation_applied BOOLEAN DEFAULT FALSE,
    simulated_obs_count INTEGER DEFAULT 0,
    downsampling_config JSON,              -- Stores downsampling parameters used
    simulation_config JSON,                -- Stores simulation parameters used

    -- Parameters used (JSON blob)
    generation_params JSON,

    -- Status
    status VARCHAR(20) DEFAULT 'created', -- created, processing, complete, failed

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Optional file paths for export
    json_path VARCHAR(500),
    parquet_path VARCHAR(500)
);
"""

DATASET_OBSERVATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS dataset_observations (
    dataset_id INTEGER,                   -- References datasets(id)
    observation_id VARCHAR(64),           -- References observations(id)

    -- Dataset-specific properties
    assigned_track_id INTEGER,            -- Decorrelated track ID
    assigned_object_id INTEGER,           -- Decorrelated object ID

    PRIMARY KEY (dataset_id, observation_id)
);
"""

DATASET_OBSERVATIONS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ds_obs_dataset ON dataset_observations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_ds_obs_observation ON dataset_observations(observation_id);
"""

DATASET_REFERENCES_TABLE = """
CREATE TABLE IF NOT EXISTS dataset_references (
    dataset_id INTEGER,                   -- References datasets(id)
    sat_no INTEGER,                       -- References satellites(sat_no)
    state_vector_id INTEGER,              -- References state_vectors(id)
    element_set_id INTEGER,               -- References element_sets(id)

    -- Grouped observation IDs (for reference reconstruction)
    grouped_obs_ids JSON,

    PRIMARY KEY (dataset_id, sat_no)
);
"""

# ============================================================
# SUBMISSIONS AND RESULTS TABLES
# ============================================================

SUBMISSIONS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS submissions_id_seq;
"""

SUBMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY DEFAULT nextval('submissions_id_seq'),
    dataset_id INTEGER,                   -- References datasets(id)
    algorithm_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0',
    description TEXT,
    file_path VARCHAR(500),
    status VARCHAR(20) DEFAULT 'queued',  -- queued, validating, processing, completed, failed
    job_id VARCHAR(100),                  -- References jobs(id)
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
"""

SUBMISSIONS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_submissions_dataset ON submissions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
"""

SUBMISSION_RESULTS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS submission_results_id_seq;
"""

SUBMISSION_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS submission_results (
    id INTEGER PRIMARY KEY DEFAULT nextval('submission_results_id_seq'),
    submission_id INTEGER UNIQUE,         -- References submissions(id)

    -- Binary metrics
    true_positives INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    false_negatives INTEGER DEFAULT 0,
    precision DECIMAL(10,6) DEFAULT 0,
    recall DECIMAL(10,6) DEFAULT 0,
    f1_score DECIMAL(10,6) DEFAULT 0,

    -- State metrics
    position_rms_km DECIMAL(12,6),
    velocity_rms_km_s DECIMAL(12,9),
    mahalanobis_distance DECIMAL(12,6),

    -- Residual metrics
    ra_residual_rms_arcsec DECIMAL(12,6),
    dec_residual_rms_arcsec DECIMAL(12,6),

    -- Raw results (JSON blob with full breakdown)
    raw_results JSON,

    -- Processing info
    processing_time_seconds DECIMAL(12,3),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SUBMISSION_RESULTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_results_submission ON submission_results(submission_id);
CREATE INDEX IF NOT EXISTS idx_results_f1 ON submission_results(f1_score DESC);
"""

# ============================================================
# JOBS TABLE
# ============================================================

JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(100) PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,        -- dataset_generation, evaluation
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    progress INTEGER DEFAULT 0,           -- 0-100
    result JSON,
    error TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
"""

JOBS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);
"""

# ============================================================
# EVENT LABELLING TABLES (Future Implementation)
# ============================================================

EVENT_TYPES_TABLE = """
CREATE TABLE IF NOT EXISTS event_types (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,     -- launch, maneuver, proximity, breakup, reentry
    description TEXT
);
"""

EVENTS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS events_id_seq;
"""

EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY DEFAULT nextval('events_id_seq'),
    event_type_id INTEGER,                -- References event_types(id)

    -- Temporal bounds
    event_time_start TIMESTAMP,
    event_time_end TIMESTAMP,

    -- Associated objects
    primary_sat_no INTEGER,               -- References satellites(sat_no)
    secondary_sat_no INTEGER,             -- For proximity events

    -- Classification
    confidence DECIMAL(5,4),              -- 0.0 to 1.0
    detection_method VARCHAR(50),         -- AUTOMATIC, MANUAL, EXTERNAL

    -- Source/provenance
    source VARCHAR(100),
    external_id VARCHAR(100),

    -- Metadata
    labelled_by VARCHAR(100),
    labelled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);
"""

EVENT_OBSERVATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS event_observations (
    event_id INTEGER,                     -- References events(id)
    observation_id VARCHAR(64),           -- References observations(id)

    PRIMARY KEY (event_id, observation_id)
);
"""

# ============================================================
# SCHEMA VERSION TRACKING
# ============================================================

SCHEMA_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS _schema_metadata (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(500),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Default event types to seed
DEFAULT_EVENT_TYPES = [
    ("launch", "Object launched into orbit"),
    ("maneuver", "Orbital maneuver detected"),
    ("proximity", "Close approach between two objects"),
    ("breakup", "Object fragmentation event"),
    ("reentry", "Object reentered atmosphere"),
    ("unknown", "Unknown or unclassified event"),
]


def _get_schema_metadata_upsert(backend: str) -> str:
    """Get backend-specific SQL for upserting schema metadata."""
    if backend == "postgres":
        return """
            INSERT INTO _schema_metadata (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """
    else:  # duckdb
        return """
            INSERT OR REPLACE INTO _schema_metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """


def initialize_schema(db: "DatabaseManager", force: bool = False) -> None:
    """
    Initialize the database schema.

    Creates all tables and indexes if they don't exist.
    Supports both DuckDB and PostgreSQL backends.

    Args:
        db: DatabaseManager instance
        force: If True, drop and recreate all tables
    """
    backend = db.backend

    if force:
        _drop_all_tables(db)

    if backend == "postgres":
        _initialize_postgres_schema(db)
    else:
        _initialize_duckdb_schema(db)


def _initialize_duckdb_schema(db: "DatabaseManager") -> None:
    """Initialize schema using DuckDB-specific SQL."""
    # Create sequences first
    db.execute(STATE_VECTORS_SEQUENCE)
    db.execute(ELEMENT_SETS_SEQUENCE)
    db.execute(DATASETS_SEQUENCE)
    db.execute(EVENTS_SEQUENCE)
    db.execute(SUBMISSIONS_SEQUENCE)
    db.execute(SUBMISSION_RESULTS_SEQUENCE)

    # Create tables in dependency order
    db.execute(SCHEMA_METADATA_TABLE)
    db.execute(SATELLITES_TABLE)
    db.execute(OBSERVATIONS_TABLE)
    db.execute(OBSERVATIONS_INDEXES)
    db.execute(STATE_VECTORS_TABLE)
    db.execute(STATE_VECTORS_INDEXES)
    db.execute(ELEMENT_SETS_TABLE)
    db.execute(ELEMENT_SETS_INDEXES)
    db.execute(DATASETS_TABLE)
    db.execute(DATASET_OBSERVATIONS_TABLE)
    db.execute(DATASET_OBSERVATIONS_INDEXES)
    db.execute(DATASET_REFERENCES_TABLE)

    # Submissions and results tables
    db.execute(SUBMISSIONS_TABLE)
    db.execute(SUBMISSIONS_INDEXES)
    db.execute(SUBMISSION_RESULTS_TABLE)
    db.execute(SUBMISSION_RESULTS_INDEXES)

    # Jobs table
    db.execute(JOBS_TABLE)
    db.execute(JOBS_INDEXES)

    # Event tables
    db.execute(EVENT_TYPES_TABLE)
    db.execute(EVENTS_TABLE)
    db.execute(EVENT_OBSERVATIONS_TABLE)

    # Seed default event types
    _seed_event_types(db)

    # Store schema version
    db.execute(
        """
        INSERT OR REPLACE INTO _schema_metadata (key, value, updated_at)
        VALUES ('version', ?, CURRENT_TIMESTAMP)
        """,
        (SCHEMA_VERSION,),
    )


def _initialize_postgres_schema(db: "DatabaseManager") -> None:
    """Initialize schema using PostgreSQL-specific SQL from schema file."""
    schema_file = Path(__file__).parent / "schema_postgres.sql"

    if schema_file.exists():
        # Read and execute the SQL file
        schema_sql = schema_file.read_text()
        # Split on semicolons and execute each statement
        statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
        for statement in statements:
            if statement and not statement.startswith("--"):
                db.execute(statement)
    else:
        # Fall back to converting DuckDB schema
        _initialize_postgres_schema_fallback(db)


def _initialize_postgres_schema_fallback(db: "DatabaseManager") -> None:
    """Initialize PostgreSQL schema by converting DuckDB SQL (fallback method)."""
    # Create sequences first
    db.execute(STATE_VECTORS_SEQUENCE)
    db.execute(ELEMENT_SETS_SEQUENCE)
    db.execute(DATASETS_SEQUENCE)
    db.execute(EVENTS_SEQUENCE)
    db.execute(SUBMISSIONS_SEQUENCE)
    db.execute(SUBMISSION_RESULTS_SEQUENCE)

    # Create tables (JSON -> JSONB for PostgreSQL)
    def convert_json_to_jsonb(sql: str) -> str:
        return sql.replace(" JSON", " JSONB")

    db.execute(SCHEMA_METADATA_TABLE)
    db.execute(SATELLITES_TABLE)
    db.execute(OBSERVATIONS_TABLE)
    db.execute(OBSERVATIONS_INDEXES)
    db.execute(convert_json_to_jsonb(STATE_VECTORS_TABLE))
    db.execute(STATE_VECTORS_INDEXES)
    db.execute(ELEMENT_SETS_TABLE)
    db.execute(ELEMENT_SETS_INDEXES)
    db.execute(convert_json_to_jsonb(DATASETS_TABLE))
    db.execute(DATASET_OBSERVATIONS_TABLE)
    db.execute(DATASET_OBSERVATIONS_INDEXES)
    db.execute(convert_json_to_jsonb(DATASET_REFERENCES_TABLE))

    # Submissions and results tables
    db.execute(SUBMISSIONS_TABLE)
    db.execute(SUBMISSIONS_INDEXES)
    db.execute(convert_json_to_jsonb(SUBMISSION_RESULTS_TABLE))
    db.execute(SUBMISSION_RESULTS_INDEXES)

    # Jobs table
    db.execute(convert_json_to_jsonb(JOBS_TABLE))
    db.execute(JOBS_INDEXES)

    # Event tables
    db.execute(EVENT_TYPES_TABLE)
    db.execute(EVENTS_TABLE)
    db.execute(EVENT_OBSERVATIONS_TABLE)

    # Seed default event types (PostgreSQL syntax)
    _seed_event_types_postgres(db)

    # Store schema version (PostgreSQL syntax)
    db.execute(
        """
        INSERT INTO _schema_metadata (key, value, updated_at)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """,
        (SCHEMA_VERSION,),
    )


def _drop_all_tables(db: "DatabaseManager") -> None:
    """Drop all tables and sequences (for force initialization)."""
    tables = [
        "event_observations",
        "events",
        "event_types",
        "jobs",
        "submission_results",
        "submissions",
        "dataset_references",
        "dataset_observations",
        "datasets",
        "element_sets",
        "state_vectors",
        "observations",
        "satellites",
        "_schema_metadata",
    ]
    for table in tables:
        db.execute(f"DROP TABLE IF EXISTS {table}")

    # Drop sequences
    sequences = [
        "state_vectors_id_seq",
        "element_sets_id_seq",
        "datasets_id_seq",
        "events_id_seq",
        "submissions_id_seq",
        "submission_results_id_seq",
    ]
    for seq in sequences:
        db.execute(f"DROP SEQUENCE IF EXISTS {seq}")


def _seed_event_types(db: "DatabaseManager") -> None:
    """Seed default event types if they don't exist (DuckDB)."""
    for idx, (name, description) in enumerate(DEFAULT_EVENT_TYPES, start=1):
        # Check if already exists
        existing = db.adapter.fetchone("SELECT 1 FROM event_types WHERE name = ?", (name,))
        if existing is None:
            db.execute(
                "INSERT INTO event_types (id, name, description) VALUES (?, ?, ?)",
                (idx, name, description),
            )


def _seed_event_types_postgres(db: "DatabaseManager") -> None:
    """Seed default event types if they don't exist (PostgreSQL)."""
    for idx, (name, description) in enumerate(DEFAULT_EVENT_TYPES, start=1):
        db.execute(
            """
            INSERT INTO event_types (id, name, description)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (idx, name, description),
        )


def verify_schema(db: "DatabaseManager") -> dict:
    """
    Verify the database schema is correct.

    Returns:
        Dictionary with verification results
    """
    results = {
        "valid": True,
        "missing_tables": [],
        "schema_version": None,
        "tables": {},
        "backend": db.backend,
    }

    required_tables = [
        "satellites",
        "observations",
        "state_vectors",
        "element_sets",
        "datasets",
        "dataset_observations",
        "dataset_references",
        "submissions",
        "submission_results",
        "jobs",
        "event_types",
        "events",
        "event_observations",
        "_schema_metadata",
    ]

    # Get existing tables
    existing_tables = set(db.adapter.get_tables())

    for table in required_tables:
        if table not in existing_tables:
            results["missing_tables"].append(table)
            results["valid"] = False
        else:
            # Get row count
            count = db.adapter.get_row_count(table)
            results["tables"][table] = {"row_count": count}

    # Get schema version
    if "_schema_metadata" in existing_tables:
        version_row = db.adapter.fetchone(
            db.adapter.convert_placeholders(
                "SELECT value FROM _schema_metadata WHERE key = ?"
            ),
            ("version",),
        )
        if version_row:
            results["schema_version"] = version_row[0]

    return results


def get_schema_version(db: "DatabaseManager") -> str | None:
    """
    Get the current schema version.

    Returns:
        Schema version string or None if not found
    """
    try:
        result = db.adapter.fetchone(
            db.adapter.convert_placeholders(
                "SELECT value FROM _schema_metadata WHERE key = ?"
            ),
            ("version",),
        )
        return result[0] if result else None
    except Exception:
        return None


# SQL for common complex queries (for reference/documentation)
QUERY_OBSERVATIONS_BY_REGIME = """
SELECT o.* FROM observations o
JOIN satellites s ON o.sat_no = s.sat_no
WHERE s.orbital_regime = ?
  AND o.ob_time BETWEEN ? AND ?
ORDER BY o.ob_time;
"""

QUERY_TRACK_GAPS = """
WITH sorted_obs AS (
    SELECT
        sat_no,
        ob_time,
        LAG(ob_time) OVER (PARTITION BY sat_no ORDER BY ob_time) as prev_time
    FROM observations
    WHERE sat_no = ?
)
SELECT
    sat_no,
    ob_time,
    prev_time,
    EXTRACT(EPOCH FROM (ob_time - prev_time)) / 3600 as gap_hours
FROM sorted_obs
WHERE prev_time IS NOT NULL
ORDER BY gap_hours DESC
LIMIT 10;
"""

QUERY_ORBITAL_COVERAGE = """
WITH observation_stats AS (
    SELECT
        sat_no,
        COUNT(*) as obs_count,
        MIN(ob_time) as first_obs,
        MAX(ob_time) as last_obs,
        MAX(ob_time) - MIN(ob_time) as time_span
    FROM observations
    WHERE ob_time BETWEEN ? AND ?
    GROUP BY sat_no
)
SELECT
    s.sat_no,
    s.orbital_regime,
    os.obs_count,
    os.time_span,
    os.obs_count / NULLIF(EXTRACT(EPOCH FROM os.time_span), 0) * 86400 as obs_per_day
FROM observation_stats os
JOIN satellites s ON os.sat_no = s.sat_no
ORDER BY os.obs_count DESC;
"""
