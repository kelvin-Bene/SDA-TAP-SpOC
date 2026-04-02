-- PostgreSQL Schema for UCT Benchmark
-- Compatible with Supabase and standard PostgreSQL databases
-- Schema Version: 1.6.0

-- ============================================================
-- SEQUENCES (for auto-increment IDs)
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS state_vectors_id_seq;
CREATE SEQUENCE IF NOT EXISTS element_sets_id_seq;
CREATE SEQUENCE IF NOT EXISTS datasets_id_seq;
CREATE SEQUENCE IF NOT EXISTS events_id_seq;
CREATE SEQUENCE IF NOT EXISTS submissions_id_seq;
CREATE SEQUENCE IF NOT EXISTS submission_results_id_seq;

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Schema metadata for version tracking
CREATE TABLE IF NOT EXISTS _schema_metadata (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(500),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Satellite catalog
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
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Observations table
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

    -- Sensor metadata (per Feb 19 transcript: preserve all UDL fields)
    sensor_id VARCHAR(64),                -- UDL sensor identifier
    sensor_name VARCHAR(100),
    data_mode VARCHAR(20),                -- REAL, SIMULATED
    type_optical VARCHAR(20),             -- Observation type (e.g., optical)

    -- Sensor location (per Feb 19 transcript: send_lat, send_long, send_alt)
    send_lat DECIMAL(12,8),              -- Sensor latitude (degrees)
    send_long DECIMAL(12,8),             -- Sensor longitude (degrees)
    send_alt DECIMAL(12,4),              -- Sensor altitude (km)

    -- Track association
    track_id VARCHAR(64),

    -- UCT processing flags
    is_uct BOOLEAN DEFAULT FALSE,
    is_simulated BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Full EO observation fields (per Benchmarking Documentation)
    classification_marking VARCHAR(200),
    id_on_orbit VARCHAR(64),
    task_id VARCHAR(64),
    orig_object_id VARCHAR(100),
    orig_sensor_id VARCHAR(100),
    sen_x DECIMAL(16,9),
    sen_y DECIMAL(16,9),
    sen_z DECIMAL(16,9),
    exp_duration DECIMAL(10,4),
    mag DECIMAL(10,6),
    mag_unc DECIMAL(10,6),
    geo_lat DECIMAL(12,8),
    geo_lon DECIMAL(12,8),
    geo_alt DECIMAL(16,6),
    geo_range DECIMAL(16,6)
);

-- Observation indexes
CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_sat_time ON observations(sat_no, ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_track ON observations(track_id);

-- State vectors table
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

    -- Covariance (6x6 matrix, stored as JSONB)
    covariance JSONB,

    -- Source metadata
    source VARCHAR(50),                   -- UDL, SPACE_TRACK, PROPAGATED
    data_mode VARCHAR(20),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(sat_no, epoch, source)
);

CREATE INDEX IF NOT EXISTS idx_sv_sat_epoch ON state_vectors(sat_no, epoch);

-- Element sets table (TLE data)
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

CREATE INDEX IF NOT EXISTS idx_elset_sat_epoch ON element_sets(sat_no, epoch);

-- Datasets table
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY DEFAULT nextval('datasets_id_seq'),
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(20),                     -- Enhanced format: "HAMR_LEO_MAN_EO_T2S_07D_001"

    -- Legacy 16-character code format (Louis's specification)
    legacy_code VARCHAR(16),              -- e.g., "H50LEONEOPSSSS07"

    -- Legacy code component fields (for querying/filtering)
    object_type_code CHAR(1),             -- H, C, A, U, N (HAMR, Close, Apparent, Unspecified, Calibration)
    target_percentage VARCHAR(2),         -- 50, 10, 01, UN
    event_code VARCHAR(2),                -- MB, BU, LL, NE (Maneuver, Breakup, LongThrust, NoEvents)
    sensor_code VARCHAR(2),               -- OP, RA, RF, FU, OR, RO, RR
    coverage_level CHAR(1),               -- A, S, N (All/High, Standard, None/Low)
    track_gap_level CHAR(1),              -- A, S, N
    obs_count_level CHAR(1),              -- A, S, N
    object_count_level CHAR(1),           -- H, S, L (High=80, Standard=40, Low=10)
    fitspan_days INTEGER,                 -- 01-14 days

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
    downsampling_config JSONB,            -- Stores downsampling parameters used
    simulation_config JSONB,              -- Stores simulation parameters used

    -- Non-reference observation tracking (for True Negative calculation)
    non_ref_observation_count INTEGER DEFAULT 0,
    include_non_ref_obs BOOLEAN DEFAULT FALSE,

    -- Answer key for evaluation (maps observation IDs to satellite NORAD IDs)
    answer_key JSONB,                      -- Per Louis's decorrelation spec

    -- Parameters used (JSONB blob)
    generation_params JSONB,

    -- Actual satellite IDs discovered during generation
    actual_satellite_ids JSONB,

    -- Performance metadata from generation run
    performance_metadata JSONB,

    -- Ownership
    user_id VARCHAR(255),

    -- Status
    status VARCHAR(20) DEFAULT 'created', -- created, processing, complete, failed
    error_message TEXT,                   -- User-facing error when status = 'failed'

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Optional file paths for export
    json_path VARCHAR(500),
    parquet_path VARCHAR(500),

    -- Code is shared across version families; (code, version) must be unique
    UNIQUE(code, version)
);

CREATE INDEX IF NOT EXISTS idx_datasets_code ON datasets(code);
CREATE INDEX IF NOT EXISTS idx_datasets_legacy_code ON datasets(legacy_code);
CREATE INDEX IF NOT EXISTS idx_datasets_object_type ON datasets(object_type_code);
CREATE INDEX IF NOT EXISTS idx_datasets_regime ON datasets(orbital_regime);
CREATE INDEX IF NOT EXISTS idx_datasets_event ON datasets(event_code);
CREATE INDEX IF NOT EXISTS idx_datasets_sensor ON datasets(sensor_code);

-- Dataset-Observation junction table
CREATE TABLE IF NOT EXISTS dataset_observations (
    dataset_id INTEGER,                   -- References datasets(id)
    observation_id VARCHAR(64),           -- References observations(id)

    -- Dataset-specific properties
    assigned_track_id INTEGER,            -- Decorrelated track ID
    assigned_object_id INTEGER,           -- Decorrelated object ID

    PRIMARY KEY (dataset_id, observation_id)
);

CREATE INDEX IF NOT EXISTS idx_ds_obs_dataset ON dataset_observations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_ds_obs_observation ON dataset_observations(observation_id);

-- Dataset references (truth data)
CREATE TABLE IF NOT EXISTS dataset_references (
    dataset_id INTEGER,                   -- References datasets(id)
    sat_no INTEGER,                       -- References satellites(sat_no)
    state_vector_id INTEGER,              -- References state_vectors(id)
    element_set_id INTEGER,               -- References element_sets(id)

    -- Grouped observation IDs (for reference reconstruction)
    grouped_obs_ids JSONB,

    PRIMARY KEY (dataset_id, sat_no)
);

-- ============================================================
-- SUBMISSIONS AND RESULTS TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY DEFAULT nextval('submissions_id_seq'),
    dataset_id INTEGER,                   -- References datasets(id)
    algorithm_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0',
    description TEXT,
    file_path VARCHAR(500),
    classification_marking VARCHAR(200),   -- Organization label (per Louis's spec)
    status VARCHAR(20) DEFAULT 'queued',  -- queued, validating, processing, completed, failed
    job_id VARCHAR(100),                  -- References jobs(id)
    error_message TEXT,
    user_id VARCHAR(255),                 -- Supabase user ID (for ownership checks)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_submissions_dataset ON submissions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_user ON submissions(user_id);

CREATE TABLE IF NOT EXISTS submission_results (
    id INTEGER PRIMARY KEY DEFAULT nextval('submission_results_id_seq'),
    submission_id INTEGER UNIQUE,         -- References submissions(id)

    -- Binary metrics
    true_positives INTEGER DEFAULT 0,
    true_negatives INTEGER DEFAULT 0,     -- Non-ref obs correctly NOT matched
    false_positives INTEGER DEFAULT 0,
    false_negatives INTEGER DEFAULT 0,
    precision DECIMAL(10,6) DEFAULT 0,
    recall DECIMAL(10,6) DEFAULT 0,
    f1_score DECIMAL(10,6) DEFAULT 0,
    specificity DECIMAL(10,6) DEFAULT 0,  -- TN/(TN+FP)
    accuracy DECIMAL(10,6) DEFAULT 0,     -- (TP+TN)/(TP+TN+FP+FN)

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

CREATE INDEX IF NOT EXISTS idx_results_submission ON submission_results(submission_id);
CREATE INDEX IF NOT EXISTS idx_results_f1 ON submission_results(f1_score DESC);

-- ============================================================
-- JOBS TABLE
-- ============================================================

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

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);

-- ============================================================
-- EVENT LABELLING TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS event_types (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,     -- launch, maneuver, proximity, breakup, reentry
    description TEXT
);

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

    -- Detector configuration (JSON string of parameters used)
    detection_config TEXT,

    -- Optional link to a dataset
    dataset_id INTEGER,                   -- References datasets(id)

    -- Metadata
    labelled_by VARCHAR(100),
    labelled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_dataset ON events(dataset_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type_id);
CREATE INDEX IF NOT EXISTS idx_events_primary_sat ON events(primary_sat_no);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(event_time_start);

CREATE TABLE IF NOT EXISTS event_observations (
    event_id INTEGER,                     -- References events(id)
    observation_id VARCHAR(64),           -- References observations(id)

    PRIMARY KEY (event_id, observation_id)
);

-- ============================================================
-- DEFAULT DATA
-- ============================================================

-- Insert default event types (idempotent)
INSERT INTO event_types (id, name, description) VALUES
    (1, 'launch', 'Object launched into orbit'),
    (2, 'maneuver', 'Orbital maneuver detected'),
    (3, 'proximity', 'Close approach between two objects'),
    (4, 'breakup', 'Object fragmentation event'),
    (5, 'reentry', 'Object reentered atmosphere'),
    (6, 'unknown', 'Unknown or unclassified event')
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- FEEDBACK TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS feedback (
    id              VARCHAR(36)  PRIMARY KEY,
    description     TEXT         NOT NULL,
    severity        VARCHAR(20)  NOT NULL,
    screenshot_url  VARCHAR(500),
    page_url        VARCHAR(2048),
    user_agent      VARCHAR(500),
    viewport        VARCHAR(100),
    recent_actions  JSONB,
    console_errors  JSONB,
    sentry_event_id VARCHAR(200),
    app_version     VARCHAR(50),
    reporter_id     VARCHAR(36),
    reporter_email  VARCHAR(255),
    status          VARCHAR(50)  NOT NULL DEFAULT 'open',
    resolution      TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);

CREATE INDEX IF NOT EXISTS idx_datasets_user_id ON datasets(user_id);

-- ============================================================
-- NON-REFERENCE OBSERVATIONS (For True Negative Calculation)
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS non_ref_observations_id_seq;

-- Non-reference observations for true-negative evaluation
CREATE TABLE IF NOT EXISTS non_reference_observations (
    id INTEGER PRIMARY KEY DEFAULT nextval('non_ref_observations_id_seq'),
    dataset_id INTEGER NOT NULL,
    observation_id VARCHAR(64) NOT NULL,
    sensor_id VARCHAR(32),
    obs_time TIMESTAMPTZ NOT NULL,
    ra_deg DECIMAL(12, 8),
    dec_deg DECIMAL(12, 8),
    source_norad_id INTEGER NOT NULL,     -- The actual satellite (for ground truth)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_nonref_obs_dataset ON non_reference_observations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_non_ref_obs_norad ON non_reference_observations(source_norad_id);

-- ============================================================
-- BREAKUP EVENTS CACHE (For BU Event Detection)
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS breakup_events_id_seq;

-- Cached breakup/fragmentation events from Space-Track/CelesTrak
CREATE TABLE IF NOT EXISTS breakup_events (
    id INTEGER PRIMARY KEY DEFAULT nextval('breakup_events_id_seq'),
    parent_norad_id INTEGER NOT NULL,
    parent_name VARCHAR(100),
    event_date TIMESTAMPTZ NOT NULL,
    debris_count INTEGER DEFAULT 0,
    debris_norad_ids JSONB,
    event_type VARCHAR(50),               -- FRAGMENTATION, COLLISION, ANOMALY
    source VARCHAR(20) NOT NULL,          -- SPACETRACK, CELESTRAK
    cached_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(parent_norad_id, event_date, source)
);
CREATE INDEX IF NOT EXISTS idx_breakup_events_date ON breakup_events(event_date);
CREATE INDEX IF NOT EXISTS idx_breakup_events_parent ON breakup_events(parent_norad_id);

-- ============================================================
-- USER PROFILES TABLE
-- ============================================================

-- User profiles with encrypted API tokens
CREATE TABLE IF NOT EXISTS profiles (
    id VARCHAR(36) PRIMARY KEY,              -- Supabase user ID
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    display_name VARCHAR(100),
    organization VARCHAR(200),
    udl_token TEXT,                           -- Encrypted UDL API token
    esa_token TEXT,                           -- Encrypted ESA API token
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- ============================================================
-- CREDENTIALS TABLE (encrypted per-user API credentials)
-- ============================================================

CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    service_name VARCHAR(50) NOT NULL,
    encrypted_primary TEXT,
    encrypted_secondary TEXT,
    is_valid BOOLEAN,
    validation_status VARCHAR(20) DEFAULT 'untested',
    last_tested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, service_name)
);
CREATE INDEX IF NOT EXISTS idx_credentials_user ON credentials(user_id);

-- Set schema version
INSERT INTO _schema_metadata (key, value, updated_at)
VALUES ('version', '1.7.0', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
