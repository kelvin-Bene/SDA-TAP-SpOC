-- ============================================================
-- UCT Benchmark DMR -- Supabase / PostgreSQL Initial Schema
-- Migration: 001_initial_schema.sql
-- Schema Version: 2.0.0 (Supabase production)
--
-- Adapted from DuckDB schema.py v1.3.0
-- Key changes:
--   JSON   -> JSONB
--   TIMESTAMP -> TIMESTAMPTZ
--   FLOAT  -> DOUBLE PRECISION
--   Added  created_by UUID on datasets, submissions, uctp_runs
--   Added  6 new production tables (users, audit_log, api_call_log,
--          query_log, credential_access_log, system_log)
--   Seed data uses INSERT ... ON CONFLICT DO NOTHING
--
-- This file is designed to be copy-pasted into the Supabase SQL Editor
-- and executed against a fresh project.
-- ============================================================

-- Enable pgcrypto for gen_random_uuid() if not already enabled
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 1. USERS (new production table)
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id    UUID UNIQUE,                         -- References Supabase auth.users(id)
    email           VARCHAR(255) NOT NULL UNIQUE,
    username        VARCHAR(100) UNIQUE,
    organization    VARCHAR(200),
    role            VARCHAR(30) NOT NULL DEFAULT 'viewer', -- admin, operator, viewer
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  users IS 'Application-level user profile linked to Supabase auth.users';
COMMENT ON COLUMN users.auth_user_id IS 'FK to auth.users(id) managed by Supabase Auth';

CREATE INDEX IF NOT EXISTS idx_users_auth_user ON users(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_users_role      ON users(role);

-- ============================================================
-- 2. SCHEMA METADATA
-- ============================================================

CREATE TABLE IF NOT EXISTS _schema_metadata (
    key         VARCHAR(100) PRIMARY KEY,
    value       VARCHAR(500),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 3. DATA PROVENANCE TRACKING
-- ============================================================

CREATE TABLE IF NOT EXISTS data_sources (
    id              INTEGER PRIMARY KEY,
    source_name     VARCHAR(50) NOT NULL UNIQUE,          -- SATNOGS, GCAT, ILRS, UCS
    source_type     VARCHAR(30),                          -- CATALOG, OBSERVATION, VALIDATION
    license         VARCHAR(50),                          -- CC-BY-SA, CC-BY, PUBLIC_DOMAIN, OPEN
    api_endpoint    VARCHAR(500),
    last_sync       TIMESTAMPTZ,
    record_count    INTEGER DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4. SATELLITES
-- ============================================================

CREATE TABLE IF NOT EXISTS satellites (
    sat_no              INTEGER PRIMARY KEY,              -- NORAD catalog number
    name                VARCHAR(100),
    cospar_id           VARCHAR(20),
    object_type         VARCHAR(20),                      -- PAYLOAD, ROCKET BODY, DEBRIS

    launch_date         DATE,
    decay_date          DATE,

    -- Physical properties (ESA DiscoWeb)
    mass_kg             DECIMAL(10,2),
    cross_section_m2    DECIMAL(10,4),
    drag_coeff          DECIMAL(6,4) DEFAULT 2.5,
    srp_coeff           DECIMAL(6,4) DEFAULT 1.5,

    -- Orbital classification
    orbital_regime      VARCHAR(10),                      -- LEO, MEO, GEO, HEO

    -- Open-source enrichment (UCS / GCAT)
    purpose             VARCHAR(100),
    operator            VARCHAR(100),
    launch_site         VARCHAR(100),
    power_watts         DECIMAL(10,2),

    -- Area-to-mass ratio for HAMR detection
    amr_m2_kg           DECIMAL(12,6),

    -- Data provenance timestamps
    ucs_synced_at       TIMESTAMPTZ,
    gcat_synced_at      TIMESTAMPTZ,

    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. OBSERVATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS observations (
    id                  VARCHAR(64) PRIMARY KEY,          -- UDL observation ID
    sat_no              INTEGER,                          -- References satellites(sat_no)

    -- Temporal
    ob_time             TIMESTAMPTZ NOT NULL,

    -- Positional (Optical - RA/Dec)
    ra                  DECIMAL(12,8),                    -- Right Ascension (degrees)
    declination         DECIMAL(12,8),                    -- Declination (degrees)

    -- Positional (Radar - optional)
    range_km            DECIMAL(12,4),
    range_rate_km_s     DECIMAL(10,6),
    azimuth             DECIMAL(12,8),
    elevation           DECIMAL(12,8),

    -- Sensor metadata
    sensor_name         VARCHAR(100),
    data_mode           VARCHAR(20),                      -- REAL, SIMULATED

    -- Track association
    track_id            VARCHAR(64),

    -- UCT processing flags
    is_uct              BOOLEAN DEFAULT FALSE,
    is_simulated        BOOLEAN DEFAULT FALSE,

    -- Data source tracking
    source_id           INTEGER,                          -- References data_sources(id)
    observation_type    VARCHAR(10) DEFAULT 'EO',         -- EO, RF, RADAR

    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obs_time      ON observations(ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_sat_time  ON observations(sat_no, ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_track     ON observations(track_id);

-- ============================================================
-- 6. STATE VECTORS
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS state_vectors_id_seq;

CREATE TABLE IF NOT EXISTS state_vectors (
    id          INTEGER PRIMARY KEY DEFAULT nextval('state_vectors_id_seq'),
    sat_no      INTEGER,                                  -- References satellites(sat_no)

    -- Epoch
    epoch       TIMESTAMPTZ NOT NULL,

    -- Position (J2000 ECI, km)
    x_pos       DECIMAL(16,6) NOT NULL,
    y_pos       DECIMAL(16,6) NOT NULL,
    z_pos       DECIMAL(16,6) NOT NULL,

    -- Velocity (J2000 ECI, km/s)
    x_vel       DECIMAL(16,9) NOT NULL,
    y_vel       DECIMAL(16,9) NOT NULL,
    z_vel       DECIMAL(16,9) NOT NULL,

    -- Covariance (6x6 matrix stored as JSON array)
    covariance  JSONB,

    -- Source metadata
    source      VARCHAR(50),                              -- UDL, SPACE_TRACK, PROPAGATED
    data_mode   VARCHAR(20),

    -- Metadata
    created_at  TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(sat_no, epoch, source)
);

CREATE INDEX IF NOT EXISTS idx_sv_sat_epoch ON state_vectors(sat_no, epoch);

-- ============================================================
-- 7. ELEMENT SETS (TLEs)
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS element_sets_id_seq;

CREATE TABLE IF NOT EXISTS element_sets (
    id                  INTEGER PRIMARY KEY DEFAULT nextval('element_sets_id_seq'),
    sat_no              INTEGER,                          -- References satellites(sat_no)

    -- Raw TLE lines
    line1               VARCHAR(70) NOT NULL,
    line2               VARCHAR(70) NOT NULL,

    -- Parsed orbital elements
    epoch               TIMESTAMPTZ NOT NULL,
    inclination         DECIMAL(10,6),                    -- degrees
    raan                DECIMAL(10,6),                    -- Right Ascension of Ascending Node
    eccentricity        DECIMAL(12,10),
    arg_perigee         DECIMAL(10,6),
    mean_anomaly        DECIMAL(10,6),
    mean_motion         DECIMAL(14,10),                   -- rev/day
    b_star              DECIMAL(16,12),

    -- Derived values
    semi_major_axis_km  DECIMAL(12,4),
    period_minutes      DECIMAL(10,4),

    -- Metadata
    source              VARCHAR(50),
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(sat_no, epoch)
);

CREATE INDEX IF NOT EXISTS idx_elset_sat_epoch ON element_sets(sat_no, epoch);

-- ============================================================
-- 8. DATASETS
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS datasets_id_seq;

CREATE TABLE IF NOT EXISTS datasets (
    id                      INTEGER PRIMARY KEY DEFAULT nextval('datasets_id_seq'),
    name                    VARCHAR(100) NOT NULL UNIQUE,
    code                    VARCHAR(20),                  -- e.g. "LEO_A_H_H_H"

    -- Version tracking
    version                 INTEGER DEFAULT 1,
    parent_id               INTEGER,                      -- For version lineage

    -- Configuration
    tier                    VARCHAR(5),                    -- T1..T5
    orbital_regime          VARCHAR(10),
    time_window_start       TIMESTAMPTZ,
    time_window_end         TIMESTAMPTZ,

    -- Statistics
    observation_count       INTEGER,
    satellite_count         INTEGER,

    -- Quality metrics
    avg_coverage            DECIMAL(8,4),
    avg_obs_count           DECIMAL(8,2),
    max_track_gap           DECIMAL(8,4),

    -- Downsampling / Simulation tracking
    downsampling_applied    BOOLEAN DEFAULT FALSE,
    simulation_applied      BOOLEAN DEFAULT FALSE,
    simulated_obs_count     INTEGER DEFAULT 0,
    downsampling_config     JSONB,
    simulation_config       JSONB,

    -- Parameters (JSON blob)
    generation_params       JSONB,

    -- Status
    status                  VARCHAR(20) DEFAULT 'created', -- created, processing, complete, failed

    -- Ownership (NEW for production)
    created_by              UUID,                          -- References users(id)

    -- Metadata
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),

    -- Optional export file paths
    json_path               VARCHAR(500),
    parquet_path            VARCHAR(500)
);

-- ============================================================
-- 9. DATASET <-> OBSERVATION JUNCTION
-- ============================================================

CREATE TABLE IF NOT EXISTS dataset_observations (
    dataset_id          INTEGER,                          -- References datasets(id)
    observation_id      VARCHAR(64),                      -- References observations(id)

    -- Dataset-specific properties
    assigned_track_id   INTEGER,                          -- Decorrelated track ID
    assigned_object_id  INTEGER,                          -- Decorrelated object ID

    PRIMARY KEY (dataset_id, observation_id)
);

CREATE INDEX IF NOT EXISTS idx_ds_obs_dataset     ON dataset_observations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_ds_obs_observation  ON dataset_observations(observation_id);

-- ============================================================
-- 10. DATASET REFERENCES
-- ============================================================

CREATE TABLE IF NOT EXISTS dataset_references (
    dataset_id      INTEGER,                              -- References datasets(id)
    sat_no          INTEGER,                              -- References satellites(sat_no)
    state_vector_id INTEGER,                              -- References state_vectors(id)
    element_set_id  INTEGER,                              -- References element_sets(id)

    -- Grouped observation IDs (for reference reconstruction)
    grouped_obs_ids JSONB,

    PRIMARY KEY (dataset_id, sat_no)
);

-- ============================================================
-- 11. SUBMISSIONS
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS submissions_id_seq;

CREATE TABLE IF NOT EXISTS submissions (
    id                  INTEGER PRIMARY KEY DEFAULT nextval('submissions_id_seq'),
    dataset_id          INTEGER,                          -- References datasets(id)
    algorithm_name      VARCHAR(100) NOT NULL,
    version             VARCHAR(50) DEFAULT '1.0',
    description         TEXT,
    file_path           VARCHAR(500),
    status              VARCHAR(20) DEFAULT 'queued',     -- queued, validating, processing, completed, failed
    job_id              VARCHAR(100),                     -- References jobs(id)
    error_message       TEXT,

    -- Ownership (NEW for production)
    created_by          UUID,                             -- References users(id)

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_submissions_dataset ON submissions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status  ON submissions(status);

-- ============================================================
-- 12. SUBMISSION RESULTS
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS submission_results_id_seq;

CREATE TABLE IF NOT EXISTS submission_results (
    id                          INTEGER PRIMARY KEY DEFAULT nextval('submission_results_id_seq'),
    submission_id               INTEGER UNIQUE,           -- References submissions(id)

    -- Binary metrics
    true_positives              INTEGER DEFAULT 0,
    false_positives             INTEGER DEFAULT 0,
    false_negatives             INTEGER DEFAULT 0,
    "precision"                 DECIMAL(10,6) DEFAULT 0,  -- quoted: reserved word in PG
    recall                      DECIMAL(10,6) DEFAULT 0,
    f1_score                    DECIMAL(10,6) DEFAULT 0,

    -- State metrics
    position_rms_km             DECIMAL(12,6),
    velocity_rms_km_s           DECIMAL(12,9),
    mahalanobis_distance        DECIMAL(12,6),

    -- Residual metrics
    ra_residual_rms_arcsec      DECIMAL(12,6),
    dec_residual_rms_arcsec     DECIMAL(12,6),

    -- Raw results (full breakdown)
    raw_results                 JSONB,

    -- Processing info
    processing_time_seconds     DECIMAL(12,3),

    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_results_submission ON submission_results(submission_id);
CREATE INDEX IF NOT EXISTS idx_results_f1         ON submission_results(f1_score DESC);

-- ============================================================
-- 13. JOBS
-- ============================================================

CREATE TABLE IF NOT EXISTS jobs (
    id              VARCHAR(100) PRIMARY KEY,
    job_type        VARCHAR(50) NOT NULL,                 -- dataset_generation, evaluation
    status          VARCHAR(20) DEFAULT 'pending',        -- pending, running, completed, failed
    progress        INTEGER DEFAULT 0,                    -- 0-100
    result          JSONB,
    error           TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type   ON jobs(job_type);

-- ============================================================
-- 14. VALIDATION MEASUREMENTS (ILRS Ground Truth)
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS validation_measurements_id_seq;

CREATE TABLE IF NOT EXISTS validation_measurements (
    id                  INTEGER PRIMARY KEY DEFAULT nextval('validation_measurements_id_seq'),
    sat_no              INTEGER NOT NULL,                  -- NORAD catalog number
    epoch               TIMESTAMPTZ NOT NULL,

    -- Range measurement
    range_m             DECIMAL(15,6),                    -- Range in meters (mm precision)

    -- Station info
    station_code        VARCHAR(10),                      -- ILRS station code (e.g. YARL, GRZL)
    station_name        VARCHAR(100),

    -- Measurement quality
    normal_point_rms_m  DECIMAL(10,6),
    num_returns         INTEGER,

    -- Data source
    source              VARCHAR(20) DEFAULT 'ILRS',

    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(sat_no, epoch, station_code)
);

CREATE INDEX IF NOT EXISTS idx_val_sat_epoch ON validation_measurements(sat_no, epoch);
CREATE INDEX IF NOT EXISTS idx_val_station   ON validation_measurements(station_code);

-- ============================================================
-- 15. EVENT TYPES (lookup)
-- ============================================================

CREATE TABLE IF NOT EXISTS event_types (
    id          INTEGER PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,              -- launch, maneuver, proximity, breakup, reentry
    description TEXT
);

-- ============================================================
-- 16. EVENTS
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS events_id_seq;

CREATE TABLE IF NOT EXISTS events (
    id                  INTEGER PRIMARY KEY DEFAULT nextval('events_id_seq'),
    event_type_id       INTEGER,                          -- References event_types(id)

    -- Temporal bounds
    event_time_start    TIMESTAMPTZ,
    event_time_end      TIMESTAMPTZ,

    -- Associated objects
    primary_sat_no      INTEGER,                          -- References satellites(sat_no)
    secondary_sat_no    INTEGER,                          -- For proximity events

    -- Classification
    confidence          DECIMAL(5,4),                     -- 0.0 to 1.0
    detection_method    VARCHAR(50),                      -- AUTOMATIC, MANUAL, EXTERNAL

    -- Source / provenance
    source              VARCHAR(100),
    external_id         VARCHAR(100),

    -- Metadata
    labelled_by         VARCHAR(100),
    labelled_at         TIMESTAMPTZ DEFAULT NOW(),
    notes               TEXT
);

-- ============================================================
-- 17. EVENT <-> OBSERVATION JUNCTION
-- ============================================================

CREATE TABLE IF NOT EXISTS event_observations (
    event_id        INTEGER,                              -- References events(id)
    observation_id  VARCHAR(64),                          -- References observations(id)

    PRIMARY KEY (event_id, observation_id)
);

-- ============================================================
-- 18. UCTP LAB -- RUNS
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS uctp_runs_id_seq;

CREATE TABLE IF NOT EXISTS uctp_runs (
    id                  INTEGER PRIMARY KEY DEFAULT nextval('uctp_runs_id_seq'),
    dataset_id          INTEGER,
    algorithm_name      VARCHAR(100) NOT NULL,
    config              JSONB NOT NULL,
    status              VARCHAR(20) DEFAULT 'pending',
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,

    f1_score            DOUBLE PRECISION,
    "precision"         DOUBLE PRECISION,
    recall              DOUBLE PRECISION,
    position_rms_km     DOUBLE PRECISION,
    velocity_rms_km_s   DOUBLE PRECISION,
    clusters_found      INTEGER,
    objects_resolved    INTEGER,

    output_path         VARCHAR(512),
    log_output          TEXT,
    error_message       TEXT,

    -- Ownership (NEW for production)
    created_by          UUID,                             -- References users(id)

    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uctp_runs_status  ON uctp_runs(status);
CREATE INDEX IF NOT EXISTS idx_uctp_runs_dataset ON uctp_runs(dataset_id);

-- ============================================================
-- 19. UCTP LAB -- MODELS
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS uctp_models_id_seq;

CREATE TABLE IF NOT EXISTS uctp_models (
    id                      INTEGER PRIMARY KEY DEFAULT nextval('uctp_models_id_seq'),
    name                    VARCHAR(100) NOT NULL,
    model_type              VARCHAR(50) NOT NULL,
    version                 VARCHAR(20) NOT NULL,
    description             TEXT,

    training_dataset_ids    JSONB,
    training_config         JSONB,
    training_epochs         INTEGER,
    training_loss           DOUBLE PRECISION,
    validation_loss         DOUBLE PRECISION,

    best_f1_score           DOUBLE PRECISION,
    best_position_rms_km    DOUBLE PRECISION,

    model_path              VARCHAR(512),
    status                  VARCHAR(20) DEFAULT 'training',

    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uctp_models_status ON uctp_models(status);

-- ============================================================
-- 20. UCTP LAB -- API CONNECTIONS
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS uctp_api_connections_id_seq;

CREATE TABLE IF NOT EXISTS uctp_api_connections (
    id              INTEGER PRIMARY KEY DEFAULT nextval('uctp_api_connections_id_seq'),
    service_name    VARCHAR(50) NOT NULL,
    status          VARCHAR(20) NOT NULL,
    response_time_ms DOUBLE PRECISION,
    last_checked    TIMESTAMPTZ DEFAULT NOW(),
    error_message   TEXT,
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS idx_uctp_api_service ON uctp_api_connections(service_name);

-- ============================================================
-- 21. CREDENTIALS (encrypted credential storage)
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS credentials_id_seq;

CREATE TABLE IF NOT EXISTS credentials (
    id                  INTEGER PRIMARY KEY DEFAULT nextval('credentials_id_seq'),
    service_name        VARCHAR(50) NOT NULL UNIQUE,
    credential_type     VARCHAR(30) NOT NULL,
    encrypted_primary   VARCHAR(2000),
    encrypted_secondary VARCHAR(2000),
    label               VARCHAR(100),
    description         TEXT,
    is_configured       BOOLEAN DEFAULT FALSE,
    last_validated      TIMESTAMPTZ,
    validation_status   VARCHAR(20) DEFAULT 'untested',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credentials_service ON credentials(service_name);

-- ============================================================
-- 22. AUDIT LOG (new production table)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         UUID,                                 -- References users(id)
    action          VARCHAR(100) NOT NULL,                -- e.g. CREATE, UPDATE, DELETE, LOGIN
    resource_type   VARCHAR(100),                         -- e.g. dataset, submission, credential
    resource_id     VARCHAR(200),                         -- PK of the affected resource
    details         JSONB,                                -- Arbitrary context
    ip_address      VARCHAR(45),                          -- IPv4 or IPv6
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user       ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action     ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource   ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_created    ON audit_log(created_at);

-- ============================================================
-- 23. API CALL LOG (new production table)
-- ============================================================

CREATE TABLE IF NOT EXISTS api_call_log (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             UUID,                             -- References users(id)
    method              VARCHAR(10) NOT NULL,             -- GET, POST, PUT, DELETE, PATCH
    path                VARCHAR(500) NOT NULL,
    status_code         INTEGER,
    request_body_size   INTEGER,                          -- bytes
    response_body_size  INTEGER,                          -- bytes
    duration_ms         DOUBLE PRECISION,
    ip_address          VARCHAR(45),
    user_agent          TEXT,
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_call_user      ON api_call_log(user_id);
CREATE INDEX IF NOT EXISTS idx_api_call_path      ON api_call_log(path);
CREATE INDEX IF NOT EXISTS idx_api_call_status    ON api_call_log(status_code);
CREATE INDEX IF NOT EXISTS idx_api_call_created   ON api_call_log(created_at);

-- ============================================================
-- 24. QUERY LOG (new production table)
-- ============================================================

CREATE TABLE IF NOT EXISTS query_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_hash      VARCHAR(64),                          -- SHA-256 of normalized query
    query_text      TEXT NOT NULL,
    params_summary  TEXT,                                  -- Redacted / summarized params
    duration_ms     DOUBLE PRECISION,
    rows_affected   INTEGER,
    source          VARCHAR(100),                         -- api, worker, migration, manual
    user_id         UUID,                                 -- References users(id)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_hash     ON query_log(query_hash);
CREATE INDEX IF NOT EXISTS idx_query_user     ON query_log(user_id);
CREATE INDEX IF NOT EXISTS idx_query_created  ON query_log(created_at);

-- ============================================================
-- 25. CREDENTIAL ACCESS LOG (new production table)
-- ============================================================

CREATE TABLE IF NOT EXISTS credential_access_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         UUID,                                 -- References users(id)
    service_name    VARCHAR(50) NOT NULL,
    action          VARCHAR(50) NOT NULL,                 -- read, write, validate, delete
    source          VARCHAR(100),                         -- api, worker, cli
    success         BOOLEAN NOT NULL DEFAULT TRUE,
    ip_address      VARCHAR(45),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cred_access_user    ON credential_access_log(user_id);
CREATE INDEX IF NOT EXISTS idx_cred_access_service ON credential_access_log(service_name);
CREATE INDEX IF NOT EXISTS idx_cred_access_created ON credential_access_log(created_at);

-- ============================================================
-- 26. SYSTEM LOG (new production table)
-- ============================================================

CREATE TABLE IF NOT EXISTS system_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    level       VARCHAR(20) NOT NULL,                     -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    component   VARCHAR(100),                             -- api, worker, migration, scheduler
    message     TEXT NOT NULL,
    details     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_syslog_level     ON system_log(level);
CREATE INDEX IF NOT EXISTS idx_syslog_component ON system_log(component);
CREATE INDEX IF NOT EXISTS idx_syslog_created   ON system_log(created_at);

-- ============================================================
-- FOREIGN KEY CONSTRAINTS
-- ============================================================
-- Applied after all tables exist to avoid ordering issues.

-- users -> auth.users (Supabase managed)
-- NOTE: Uncomment the following line ONLY if you are running inside
--       Supabase where the auth schema exists.  The reference is kept
--       commented out so this file remains runnable in plain PostgreSQL.
-- ALTER TABLE users ADD CONSTRAINT fk_users_auth FOREIGN KEY (auth_user_id) REFERENCES auth.users(id);

-- observations
ALTER TABLE observations
    ADD CONSTRAINT fk_obs_source FOREIGN KEY (source_id) REFERENCES data_sources(id);

-- state_vectors
ALTER TABLE state_vectors
    ADD CONSTRAINT fk_sv_satellite FOREIGN KEY (sat_no) REFERENCES satellites(sat_no);

-- element_sets
ALTER TABLE element_sets
    ADD CONSTRAINT fk_elset_satellite FOREIGN KEY (sat_no) REFERENCES satellites(sat_no);

-- datasets
ALTER TABLE datasets
    ADD CONSTRAINT fk_datasets_parent FOREIGN KEY (parent_id) REFERENCES datasets(id),
    ADD CONSTRAINT fk_datasets_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- dataset_observations
ALTER TABLE dataset_observations
    ADD CONSTRAINT fk_dsobs_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(id),
    ADD CONSTRAINT fk_dsobs_observation FOREIGN KEY (observation_id) REFERENCES observations(id);

-- dataset_references
ALTER TABLE dataset_references
    ADD CONSTRAINT fk_dsref_dataset   FOREIGN KEY (dataset_id)      REFERENCES datasets(id),
    ADD CONSTRAINT fk_dsref_satellite FOREIGN KEY (sat_no)          REFERENCES satellites(sat_no),
    ADD CONSTRAINT fk_dsref_sv        FOREIGN KEY (state_vector_id) REFERENCES state_vectors(id),
    ADD CONSTRAINT fk_dsref_elset     FOREIGN KEY (element_set_id)  REFERENCES element_sets(id);

-- submissions
ALTER TABLE submissions
    ADD CONSTRAINT fk_sub_dataset    FOREIGN KEY (dataset_id) REFERENCES datasets(id),
    ADD CONSTRAINT fk_sub_job        FOREIGN KEY (job_id)     REFERENCES jobs(id),
    ADD CONSTRAINT fk_sub_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- submission_results
ALTER TABLE submission_results
    ADD CONSTRAINT fk_subres_submission FOREIGN KEY (submission_id) REFERENCES submissions(id);

-- validation_measurements (no FK on sat_no -- may reference objects not yet in satellites)

-- events
ALTER TABLE events
    ADD CONSTRAINT fk_event_type     FOREIGN KEY (event_type_id)    REFERENCES event_types(id),
    ADD CONSTRAINT fk_event_primary  FOREIGN KEY (primary_sat_no)   REFERENCES satellites(sat_no),
    ADD CONSTRAINT fk_event_secondary FOREIGN KEY (secondary_sat_no) REFERENCES satellites(sat_no);

-- event_observations
ALTER TABLE event_observations
    ADD CONSTRAINT fk_evobs_event       FOREIGN KEY (event_id)       REFERENCES events(id),
    ADD CONSTRAINT fk_evobs_observation FOREIGN KEY (observation_id) REFERENCES observations(id);

-- uctp_runs
ALTER TABLE uctp_runs
    ADD CONSTRAINT fk_uctp_run_dataset    FOREIGN KEY (dataset_id) REFERENCES datasets(id),
    ADD CONSTRAINT fk_uctp_run_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- audit_log
ALTER TABLE audit_log
    ADD CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id);

-- api_call_log
ALTER TABLE api_call_log
    ADD CONSTRAINT fk_apicall_user FOREIGN KEY (user_id) REFERENCES users(id);

-- query_log
ALTER TABLE query_log
    ADD CONSTRAINT fk_query_user FOREIGN KEY (user_id) REFERENCES users(id);

-- credential_access_log
ALTER TABLE credential_access_log
    ADD CONSTRAINT fk_credaccess_user FOREIGN KEY (user_id) REFERENCES users(id);

-- ============================================================
-- SEED DATA
-- ============================================================

-- Event Types
INSERT INTO event_types (id, name, description) VALUES
    (1, 'launch',    'Object launched into orbit'),
    (2, 'maneuver',  'Orbital maneuver detected'),
    (3, 'proximity', 'Close approach between two objects'),
    (4, 'breakup',   'Object fragmentation event'),
    (5, 'reentry',   'Object reentered atmosphere'),
    (6, 'unknown',   'Unknown or unclassified event')
ON CONFLICT (id) DO NOTHING;

-- Data Sources
INSERT INTO data_sources (id, source_name, source_type, license, api_endpoint, notes) VALUES
    (1, 'UDL',         'OBSERVATION', 'RESTRICTED',    'https://unifieddatalibrary.com',   'Primary observation source (authenticated)'),
    (2, 'SATNOGS',     'OBSERVATION', 'CC-BY-SA',      'https://network.satnogs.org/api',  'RF observations from ground stations'),
    (3, 'GCAT',        'CATALOG',     'CC-BY',         'https://planet4589.org/space/gcat', 'Space object catalog by J. McDowell'),
    (4, 'UCS',         'CATALOG',     'OPEN',          'https://www.ucs.org',               'Operational satellite database'),
    (5, 'ILRS',        'VALIDATION',  'PUBLIC_DOMAIN', 'https://ilrs.gsfc.nasa.gov',        'Laser ranging ground truth'),
    (6, 'SPACE_TRACK', 'CATALOG',     'RESTRICTED',    'https://space-track.org',           'Official US space catalog')
ON CONFLICT (id) DO NOTHING;

-- Default Credentials (service stubs -- no secrets)
INSERT INTO credentials (service_name, credential_type, label, description) VALUES
    ('udl',             'bearer_token',      'Unified Data Library', 'UDL API token (Base64-encoded credentials)'),
    ('esa',             'bearer_token',      'ESA Discosweb',       'ESA API bearer token for space debris data'),
    ('nasa_earthdata',  'jwt',               'NASA Earthdata',      'NASA Earthdata JWT authentication token'),
    ('spacetrack',      'username_password', 'Space-Track.org',     'Space-Track.org login credentials'),
    ('orekit',          'path',              'Orekit Data',         'Local file path to Orekit data directory')
ON CONFLICT (service_name) DO NOTHING;

-- Schema Version
INSERT INTO _schema_metadata (key, value, updated_at) VALUES
    ('version',    '2.0.0',              NOW()),
    ('migrated_at', NOW()::TEXT,         NOW()),
    ('source',     '001_initial_schema', NOW())
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- ROW-LEVEL SECURITY (RLS) POLICIES
-- ============================================================
-- Enable RLS on tables that should be gated by user identity.
-- Policies are intentionally permissive here; tighten per your
-- access-control requirements.

ALTER TABLE users                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets               ENABLE ROW LEVEL SECURITY;
ALTER TABLE submissions            ENABLE ROW LEVEL SECURITY;
ALTER TABLE uctp_runs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE credentials            ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log              ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_call_log           ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_log              ENABLE ROW LEVEL SECURITY;
ALTER TABLE credential_access_log  ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_log             ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access (Supabase server-side).
-- Authenticated users get read access by default; write policies
-- should be layered on top per business rules.

-- Example: users can read their own row
CREATE POLICY users_self_read ON users
    FOR SELECT
    USING (auth_user_id = auth.uid());

-- Example: admins can read all audit logs
CREATE POLICY audit_admin_read ON audit_log
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.auth_user_id = auth.uid()
              AND users.role = 'admin'
        )
    );

-- ============================================================
-- updated_at TRIGGER FUNCTION
-- ============================================================
-- Automatically maintain updated_at on UPDATE for any table that
-- has the column.

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_satellites_updated_at
    BEFORE UPDATE ON satellites
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_datasets_updated_at
    BEFORE UPDATE ON datasets
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_credentials_updated_at
    BEFORE UPDATE ON credentials
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- DONE
-- ============================================================
