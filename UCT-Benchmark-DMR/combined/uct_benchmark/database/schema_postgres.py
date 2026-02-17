"""
PostgreSQL-adapted database schema definitions for UCT Benchmark.

This is the production PostgreSQL version of schema.py (DuckDB).
Key differences:
  - JSON -> JSONB for binary JSON storage and indexing
  - TIMESTAMP -> TIMESTAMPTZ for timezone-aware timestamps
  - INSERT OR REPLACE -> INSERT ... ON CONFLICT ... DO UPDATE
  - information_schema table_schema = 'public' (not 'main')
  - Six new production tables: users, audit_log, api_call_log,
    query_log, credential_access_log, system_log
  - created_by UUID column on datasets, submissions, uctp_runs

Provides SQL schema creation statements and migration utilities.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .connection import DatabaseManager

# Schema version for migration tracking
SCHEMA_VERSION = "2.0.0"  # PostgreSQL migration

# ============================================================
# SCHEMA CREATION SQL
# ============================================================

# ============================================================
# DATA PROVENANCE TRACKING
# ============================================================

DATA_SOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY,
    source_name VARCHAR(50) NOT NULL UNIQUE,  -- SATNOGS, GCAT, ILRS, UCS
    source_type VARCHAR(30),                   -- CATALOG, OBSERVATION, VALIDATION
    license VARCHAR(50),                       -- CC-BY-SA, CC-BY, PUBLIC_DOMAIN, OPEN
    api_endpoint VARCHAR(500),
    last_sync TIMESTAMPTZ,
    record_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

DATA_SOURCES_SEED = [
    (1, 'UDL', 'OBSERVATION', 'RESTRICTED', 'https://unifieddatalibrary.com', 'Primary observation source (authenticated)'),
    (2, 'SATNOGS', 'OBSERVATION', 'CC-BY-SA', 'https://network.satnogs.org/api', 'RF observations from ground stations'),
    (3, 'GCAT', 'CATALOG', 'CC-BY', 'https://planet4589.org/space/gcat', 'Space object catalog by J. McDowell'),
    (4, 'UCS', 'CATALOG', 'OPEN', 'https://www.ucs.org', 'Operational satellite database'),
    (5, 'ILRS', 'VALIDATION', 'PUBLIC_DOMAIN', 'https://ilrs.gsfc.nasa.gov', 'Laser ranging ground truth'),
    (6, 'SPACE_TRACK', 'CATALOG', 'RESTRICTED', 'https://space-track.org', 'Official US space catalog'),
]

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

    -- Open source enrichment data (UCS/GCAT)
    purpose VARCHAR(100),                 -- Communications, Earth Observation, etc.
    operator VARCHAR(100),                -- Owner/operator organization
    launch_site VARCHAR(100),             -- Launch facility
    power_watts DECIMAL(10,2),            -- Power output from UCS

    -- Area-to-mass ratio for HAMR detection
    amr_m2_kg DECIMAL(12,6),              -- Calculated area-to-mass ratio

    -- Data provenance timestamps
    ucs_synced_at TIMESTAMPTZ,            -- Last sync with UCS database
    gcat_synced_at TIMESTAMPTZ,           -- Last sync with GCAT catalog

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

OBSERVATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS observations (
    id VARCHAR(64) PRIMARY KEY,           -- UDL observation ID
    sat_no INTEGER,                        -- References satellites(sat_no)

    -- Temporal
    ob_time TIMESTAMPTZ NOT NULL,

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

    -- Data source tracking (open source integration)
    source_id INTEGER,                    -- References data_sources(id)
    observation_type VARCHAR(10) DEFAULT 'EO',  -- EO (electro-optical), RF, RADAR

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
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
    epoch TIMESTAMPTZ NOT NULL,

    -- Position (J2000 ECI, km)
    x_pos DECIMAL(16,6) NOT NULL,
    y_pos DECIMAL(16,6) NOT NULL,
    z_pos DECIMAL(16,6) NOT NULL,

    -- Velocity (J2000 ECI, km/s)
    x_vel DECIMAL(16,9) NOT NULL,
    y_vel DECIMAL(16,9) NOT NULL,
    z_vel DECIMAL(16,9) NOT NULL,

    -- Covariance (6x6 matrix, stored as JSONB array)
    covariance JSONB,

    -- Source metadata
    source VARCHAR(50),                   -- UDL, SPACE_TRACK, PROPAGATED
    data_mode VARCHAR(20),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

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
    epoch TIMESTAMPTZ NOT NULL,
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
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

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
    time_window_start TIMESTAMPTZ,
    time_window_end TIMESTAMPTZ,

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
    downsampling_config JSONB,             -- Stores downsampling parameters used
    simulation_config JSONB,               -- Stores simulation parameters used

    -- Parameters used (JSONB blob)
    generation_params JSONB,

    -- Status
    status VARCHAR(20) DEFAULT 'created', -- created, processing, complete, failed

    -- Ownership
    created_by UUID,                       -- References users(id)

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

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
    grouped_obs_ids JSONB,

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

    -- Ownership
    created_by UUID,                       -- References users(id)

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);
"""

SUBMISSIONS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_submissions_dataset ON submissions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_created_by ON submissions(created_by);
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

    -- Raw results (JSONB blob with full breakdown)
    raw_results JSONB,

    -- Processing info
    processing_time_seconds DECIMAL(12,3),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
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
    result JSONB,
    error TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
"""

JOBS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);
"""

# ============================================================
# VALIDATION MEASUREMENTS (ILRS Ground Truth)
# ============================================================

VALIDATION_MEASUREMENTS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS validation_measurements_id_seq;
"""

VALIDATION_MEASUREMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS validation_measurements (
    id INTEGER PRIMARY KEY DEFAULT nextval('validation_measurements_id_seq'),
    sat_no INTEGER NOT NULL,              -- NORAD catalog number
    epoch TIMESTAMPTZ NOT NULL,           -- Measurement epoch

    -- Range measurement
    range_m DECIMAL(15,6),                -- Range in meters (mm precision)

    -- Station info
    station_code VARCHAR(10),             -- ILRS station code (e.g., YARL, GRZL)
    station_name VARCHAR(100),            -- Full station name

    -- Measurement quality
    normal_point_rms_m DECIMAL(10,6),     -- Normal point RMS
    num_returns INTEGER,                   -- Number of laser returns

    -- Data source
    source VARCHAR(20) DEFAULT 'ILRS',

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(sat_no, epoch, station_code)
);
"""

VALIDATION_MEASUREMENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_val_sat_epoch ON validation_measurements(sat_no, epoch);
CREATE INDEX IF NOT EXISTS idx_val_station ON validation_measurements(station_code);
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
    event_time_start TIMESTAMPTZ,
    event_time_end TIMESTAMPTZ,

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
    labelled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

# ============================================================
# UCTP LAB TABLES
# ============================================================

UCTP_RUNS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS uctp_runs_id_seq;
"""

UCTP_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS uctp_runs (
    id INTEGER PRIMARY KEY DEFAULT nextval('uctp_runs_id_seq'),
    dataset_id INTEGER,
    algorithm_name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    f1_score FLOAT,
    precision FLOAT,
    recall FLOAT,
    position_rms_km FLOAT,
    velocity_rms_km_s FLOAT,
    clusters_found INTEGER,
    objects_resolved INTEGER,

    output_path VARCHAR(512),
    log_output TEXT,
    error_message TEXT,

    -- Ownership
    created_by UUID,                       -- References users(id)

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

UCTP_RUNS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_uctp_runs_status ON uctp_runs(status);
CREATE INDEX IF NOT EXISTS idx_uctp_runs_dataset ON uctp_runs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_uctp_runs_created_by ON uctp_runs(created_by);
"""

UCTP_MODELS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS uctp_models_id_seq;
"""

UCTP_MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS uctp_models (
    id INTEGER PRIMARY KEY DEFAULT nextval('uctp_models_id_seq'),
    name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,

    training_dataset_ids JSONB,
    training_config JSONB,
    training_epochs INTEGER,
    training_loss FLOAT,
    validation_loss FLOAT,

    best_f1_score FLOAT,
    best_position_rms_km FLOAT,

    model_path VARCHAR(512),
    status VARCHAR(20) DEFAULT 'training',

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

UCTP_MODELS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_uctp_models_status ON uctp_models(status);
"""

UCTP_API_CONNECTIONS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS uctp_api_connections_id_seq;
"""

UCTP_API_CONNECTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS uctp_api_connections (
    id INTEGER PRIMARY KEY DEFAULT nextval('uctp_api_connections_id_seq'),
    service_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time_ms FLOAT,
    last_checked TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    metadata JSONB
);
"""

UCTP_API_CONNECTIONS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_uctp_api_service ON uctp_api_connections(service_name);
"""

# ============================================================
# CREDENTIALS TABLE (Encrypted credential storage)
# ============================================================

CREDENTIALS_SEQUENCE = """
CREATE SEQUENCE IF NOT EXISTS credentials_id_seq;
"""

CREDENTIALS_TABLE = """
CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY DEFAULT nextval('credentials_id_seq'),
    service_name VARCHAR(50) NOT NULL UNIQUE,
    credential_type VARCHAR(30) NOT NULL,
    encrypted_primary VARCHAR(2000),
    encrypted_secondary VARCHAR(2000),
    label VARCHAR(100),
    description TEXT,
    is_configured BOOLEAN DEFAULT FALSE,
    last_validated TIMESTAMPTZ,
    validation_status VARCHAR(20) DEFAULT 'untested',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

CREDENTIALS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_credentials_service ON credentials(service_name);
"""

# Default credential service definitions to seed
DEFAULT_CREDENTIALS = [
    ("udl", "bearer_token", "Unified Data Library", "UDL API token (Base64-encoded credentials)"),
    ("esa", "bearer_token", "ESA Discosweb", "ESA API bearer token for space debris data"),
    ("nasa_earthdata", "jwt", "NASA Earthdata", "NASA Earthdata JWT authentication token"),
    ("spacetrack", "username_password", "Space-Track.org", "Space-Track.org login credentials"),
    ("orekit", "path", "Orekit Data", "Local file path to Orekit data directory"),
]

# Default event types to seed
DEFAULT_EVENT_TYPES = [
    ("launch", "Object launched into orbit"),
    ("maneuver", "Orbital maneuver detected"),
    ("proximity", "Close approach between two objects"),
    ("breakup", "Object fragmentation event"),
    ("reentry", "Object reentered atmosphere"),
    ("unknown", "Unknown or unclassified event"),
]

# ============================================================
# PRODUCTION TABLES (PostgreSQL-only)
# ============================================================

# --- Users ---
USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID UNIQUE,             -- External auth provider user ID
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    organization VARCHAR(200),
    role VARCHAR(20) NOT NULL DEFAULT 'developer',  -- developer, evaluator, admin
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

USERS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_users_auth_user_id ON users(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
"""

# --- Audit Log ---
AUDIT_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID,                          -- References users(id)
    action VARCHAR(100) NOT NULL,          -- e.g., CREATE, UPDATE, DELETE, LOGIN, EXPORT
    resource_type VARCHAR(100),            -- e.g., dataset, submission, credential
    resource_id VARCHAR(200),              -- ID of the affected resource
    details JSONB,                         -- Additional context
    ip_address VARCHAR(45),               -- IPv4 or IPv6
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

AUDIT_LOG_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
"""

# --- API Call Log ---
API_CALL_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS api_call_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID,                          -- References users(id)
    method VARCHAR(10) NOT NULL,           -- GET, POST, PUT, DELETE, PATCH
    path VARCHAR(500) NOT NULL,
    status_code INTEGER,
    request_body_size INTEGER,             -- Bytes
    response_body_size INTEGER,            -- Bytes
    duration_ms DECIMAL(12,3),
    ip_address VARCHAR(45),
    user_agent TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

API_CALL_LOG_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_api_call_log_user_id ON api_call_log(user_id);
CREATE INDEX IF NOT EXISTS idx_api_call_log_method_path ON api_call_log(method, path);
CREATE INDEX IF NOT EXISTS idx_api_call_log_status_code ON api_call_log(status_code);
CREATE INDEX IF NOT EXISTS idx_api_call_log_created_at ON api_call_log(created_at);
"""

# --- Query Log ---
QUERY_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS query_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_hash VARCHAR(64),                -- SHA-256 hash for deduplication/grouping
    query_text TEXT NOT NULL,
    duration_ms DECIMAL(12,3),
    rows_affected INTEGER,
    source VARCHAR(100),                   -- api, cli, scheduler, migration
    user_id UUID,                          -- References users(id)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

QUERY_LOG_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_query_log_query_hash ON query_log(query_hash);
CREATE INDEX IF NOT EXISTS idx_query_log_user_id ON query_log(user_id);
CREATE INDEX IF NOT EXISTS idx_query_log_source ON query_log(source);
CREATE INDEX IF NOT EXISTS idx_query_log_created_at ON query_log(created_at);
CREATE INDEX IF NOT EXISTS idx_query_log_duration ON query_log(duration_ms DESC);
"""

# --- Credential Access Log ---
CREDENTIAL_ACCESS_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS credential_access_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID,                          -- References users(id)
    service_name VARCHAR(50) NOT NULL,     -- Credential service accessed
    action VARCHAR(50) NOT NULL,           -- read, write, validate, rotate
    source VARCHAR(100),                   -- api, cli, scheduler
    success BOOLEAN NOT NULL DEFAULT TRUE,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

CREDENTIAL_ACCESS_LOG_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_cred_access_user_id ON credential_access_log(user_id);
CREATE INDEX IF NOT EXISTS idx_cred_access_service ON credential_access_log(service_name);
CREATE INDEX IF NOT EXISTS idx_cred_access_action ON credential_access_log(action);
CREATE INDEX IF NOT EXISTS idx_cred_access_created_at ON credential_access_log(created_at);
"""

# --- System Log ---
SYSTEM_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS system_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    level VARCHAR(10) NOT NULL,            -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    component VARCHAR(100) NOT NULL,       -- e.g., schema, api, pipeline, scheduler
    message TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

SYSTEM_LOG_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_system_log_level ON system_log(level);
CREATE INDEX IF NOT EXISTS idx_system_log_component ON system_log(component);
CREATE INDEX IF NOT EXISTS idx_system_log_created_at ON system_log(created_at);
"""

# ============================================================
# FOREIGN KEY CONSTRAINTS (added after all tables exist)
# ============================================================

PG_FOREIGN_KEYS = """
-- Ownership foreign keys (datasets, submissions, uctp_runs -> users)
DO $$ BEGIN
    ALTER TABLE datasets ADD CONSTRAINT fk_datasets_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE submissions ADD CONSTRAINT fk_submissions_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE uctp_runs ADD CONSTRAINT fk_uctp_runs_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Audit and logging foreign keys (-> users)
DO $$ BEGIN
    ALTER TABLE audit_log ADD CONSTRAINT fk_audit_log_user_id
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE api_call_log ADD CONSTRAINT fk_api_call_log_user_id
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE query_log ADD CONSTRAINT fk_query_log_user_id
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE credential_access_log ADD CONSTRAINT fk_cred_access_user_id
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
"""


# ============================================================
# INITIALIZATION FUNCTIONS
# ============================================================

def initialize_schema_postgres(db: "DatabaseManager", force: bool = False) -> None:
    """
    Initialize the PostgreSQL database schema.

    Creates all tables, indexes, and seeds default data.
    Uses PostgreSQL-native types (JSONB, TIMESTAMPTZ, IDENTITY).

    Args:
        db: DatabaseManager instance (connected to PostgreSQL)
        force: If True, drop and recreate all tables
    """
    if force:
        _drop_all_tables_postgres(db)

    # Create sequences first (for legacy-style integer PKs)
    db.execute(STATE_VECTORS_SEQUENCE)
    db.execute(ELEMENT_SETS_SEQUENCE)
    db.execute(DATASETS_SEQUENCE)
    db.execute(EVENTS_SEQUENCE)
    db.execute(SUBMISSIONS_SEQUENCE)
    db.execute(SUBMISSION_RESULTS_SEQUENCE)
    db.execute(VALIDATION_MEASUREMENTS_SEQUENCE)
    db.execute(UCTP_RUNS_SEQUENCE)
    db.execute(UCTP_MODELS_SEQUENCE)
    db.execute(UCTP_API_CONNECTIONS_SEQUENCE)
    db.execute(CREDENTIALS_SEQUENCE)

    # Create core tables in dependency order
    db.execute(SCHEMA_METADATA_TABLE)
    db.execute(DATA_SOURCES_TABLE)  # Provenance tracking
    db.execute(SATELLITES_TABLE)
    db.execute(OBSERVATIONS_TABLE)
    db.execute(OBSERVATIONS_INDEXES)
    db.execute(STATE_VECTORS_TABLE)
    db.execute(STATE_VECTORS_INDEXES)
    db.execute(ELEMENT_SETS_TABLE)
    db.execute(ELEMENT_SETS_INDEXES)

    # Users table must come before datasets/submissions/uctp_runs (FK dependency)
    db.execute(USERS_TABLE)
    db.execute(USERS_INDEXES)

    db.execute(DATASETS_TABLE)
    db.execute(DATASET_OBSERVATIONS_TABLE)
    db.execute(DATASET_OBSERVATIONS_INDEXES)
    db.execute(DATASET_REFERENCES_TABLE)

    # Validation measurements (ILRS ground truth)
    db.execute(VALIDATION_MEASUREMENTS_TABLE)
    db.execute(VALIDATION_MEASUREMENTS_INDEXES)

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

    # UCTP Lab tables
    db.execute(UCTP_RUNS_TABLE)
    db.execute(UCTP_RUNS_INDEXES)
    db.execute(UCTP_MODELS_TABLE)
    db.execute(UCTP_MODELS_INDEXES)
    db.execute(UCTP_API_CONNECTIONS_TABLE)
    db.execute(UCTP_API_CONNECTIONS_INDEXES)

    # Credentials table
    db.execute(CREDENTIALS_TABLE)
    db.execute(CREDENTIALS_INDEX)

    # Production logging tables
    db.execute(AUDIT_LOG_TABLE)
    db.execute(AUDIT_LOG_INDEXES)
    db.execute(API_CALL_LOG_TABLE)
    db.execute(API_CALL_LOG_INDEXES)
    db.execute(QUERY_LOG_TABLE)
    db.execute(QUERY_LOG_INDEXES)
    db.execute(CREDENTIAL_ACCESS_LOG_TABLE)
    db.execute(CREDENTIAL_ACCESS_LOG_INDEXES)
    db.execute(SYSTEM_LOG_TABLE)
    db.execute(SYSTEM_LOG_INDEXES)

    # Foreign key constraints (idempotent via DO $$ blocks)
    db.execute(PG_FOREIGN_KEYS)

    # Seed default data
    _seed_event_types_postgres(db)
    _seed_data_sources_postgres(db)
    _seed_credentials_postgres(db)

    # Store schema version using ON CONFLICT (PostgreSQL upsert)
    db.execute(
        """
        INSERT INTO _schema_metadata (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """,
        ('version', SCHEMA_VERSION),
    )


def _drop_all_tables_postgres(db: "DatabaseManager") -> None:
    """Drop all tables and sequences (for force initialization) -- PostgreSQL."""
    tables = [
        # Production logging tables (no FK dependencies on them)
        "system_log",
        "credential_access_log",
        "query_log",
        "api_call_log",
        "audit_log",
        # Original tables in reverse dependency order
        "credentials",
        "uctp_api_connections",
        "uctp_models",
        "uctp_runs",
        "event_observations",
        "events",
        "event_types",
        "jobs",
        "submission_results",
        "submissions",
        "dataset_references",
        "dataset_observations",
        "datasets",
        "validation_measurements",
        "element_sets",
        "state_vectors",
        "observations",
        "satellites",
        "data_sources",
        "users",
        "_schema_metadata",
    ]
    for table in tables:
        db.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    # Drop sequences
    sequences = [
        "credentials_id_seq",
        "uctp_runs_id_seq",
        "uctp_models_id_seq",
        "uctp_api_connections_id_seq",
        "state_vectors_id_seq",
        "element_sets_id_seq",
        "datasets_id_seq",
        "events_id_seq",
        "submissions_id_seq",
        "submission_results_id_seq",
        "validation_measurements_id_seq",
    ]
    for seq in sequences:
        db.execute(f"DROP SEQUENCE IF EXISTS {seq} CASCADE")


def _seed_event_types_postgres(db: "DatabaseManager") -> None:
    """Seed default event types using PostgreSQL ON CONFLICT."""
    for idx, (name, description) in enumerate(DEFAULT_EVENT_TYPES, start=1):
        db.execute(
            """
            INSERT INTO event_types (id, name, description)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (idx, name, description),
        )


def _seed_data_sources_postgres(db: "DatabaseManager") -> None:
    """Seed default data sources using PostgreSQL ON CONFLICT."""
    for source_id, name, source_type, license_type, endpoint, notes in DATA_SOURCES_SEED:
        db.execute(
            """
            INSERT INTO data_sources (id, source_name, source_type, license, api_endpoint, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_name) DO NOTHING
            """,
            (source_id, name, source_type, license_type, endpoint, notes),
        )


def _seed_credentials_postgres(db: "DatabaseManager") -> None:
    """Seed default credential service entries using PostgreSQL ON CONFLICT."""
    for service_name, cred_type, label, description in DEFAULT_CREDENTIALS:
        db.execute(
            """
            INSERT INTO credentials (service_name, credential_type, label, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (service_name) DO NOTHING
            """,
            (service_name, cred_type, label, description),
        )


def verify_schema_postgres(db: "DatabaseManager") -> dict:
    """
    Verify the PostgreSQL database schema is correct.

    Queries information_schema with table_schema = 'public'
    and checks for all required tables including production tables.

    Returns:
        Dictionary with verification results
    """
    results = {
        "valid": True,
        "missing_tables": [],
        "schema_version": None,
        "tables": {},
    }

    required_tables = [
        # Core domain tables
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
        "data_sources",
        "validation_measurements",
        "uctp_runs",
        "uctp_models",
        "uctp_api_connections",
        "credentials",
        "_schema_metadata",
        # Production tables (PostgreSQL-only)
        "users",
        "audit_log",
        "api_call_log",
        "query_log",
        "credential_access_log",
        "system_log",
    ]

    # Get existing tables -- PostgreSQL uses table_schema = 'public'
    existing_tables = {
        row[0]
        for row in db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchall()
    }

    for table in required_tables:
        if table not in existing_tables:
            results["missing_tables"].append(table)
            results["valid"] = False
        else:
            # Get row count
            count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            results["tables"][table] = {"row_count": count}

    # Get schema version
    if "_schema_metadata" in existing_tables:
        version_row = db.execute(
            "SELECT value FROM _schema_metadata WHERE key = 'version'"
        ).fetchone()
        if version_row:
            results["schema_version"] = version_row[0]

    return results


def get_schema_version_postgres(db: "DatabaseManager") -> str | None:
    """
    Get the current schema version from PostgreSQL.

    Returns:
        Schema version string or None if not found
    """
    try:
        result = db.execute(
            "SELECT value FROM _schema_metadata WHERE key = 'version'"
        ).fetchone()
        return result[0] if result else None
    except Exception:
        return None


# ============================================================
# SQL for common complex queries (PostgreSQL syntax)
# ============================================================

QUERY_OBSERVATIONS_BY_REGIME = """
SELECT o.* FROM observations o
JOIN satellites s ON o.sat_no = s.sat_no
WHERE s.orbital_regime = %s
  AND o.ob_time BETWEEN %s AND %s
ORDER BY o.ob_time;
"""

QUERY_TRACK_GAPS = """
WITH sorted_obs AS (
    SELECT
        sat_no,
        ob_time,
        LAG(ob_time) OVER (PARTITION BY sat_no ORDER BY ob_time) as prev_time
    FROM observations
    WHERE sat_no = %s
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
    WHERE ob_time BETWEEN %s AND %s
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
