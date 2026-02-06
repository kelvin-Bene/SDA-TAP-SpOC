-- PostgreSQL Schema for UCT Benchmark
-- Compatible with Supabase and standard PostgreSQL databases
-- Schema Version: 2.0.0 (matches DuckDB schema.py)
--
-- This file is read by _initialize_postgres_schema() as a fallback
-- when the app initializes against a PostgreSQL database directly.
-- It must NOT contain dollar-quoted functions ($$) since it is
-- split on semicolons for execution.

-- ============================================================
-- SEQUENCES (for auto-increment IDs)
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS state_vectors_id_seq;
CREATE SEQUENCE IF NOT EXISTS element_sets_id_seq;
CREATE SEQUENCE IF NOT EXISTS datasets_id_seq;
CREATE SEQUENCE IF NOT EXISTS events_id_seq;
CREATE SEQUENCE IF NOT EXISTS submissions_id_seq;
CREATE SEQUENCE IF NOT EXISTS submission_results_id_seq;
CREATE SEQUENCE IF NOT EXISTS validation_measurements_id_seq;
CREATE SEQUENCE IF NOT EXISTS uctp_runs_id_seq;
CREATE SEQUENCE IF NOT EXISTS uctp_models_id_seq;
CREATE SEQUENCE IF NOT EXISTS uctp_api_connections_id_seq;
CREATE SEQUENCE IF NOT EXISTS credentials_id_seq;
CREATE SEQUENCE IF NOT EXISTS dataset_queries_id_seq;
CREATE SEQUENCE IF NOT EXISTS dataset_enrichment_log_id_seq;

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Schema metadata for version tracking
CREATE TABLE IF NOT EXISTS _schema_metadata (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(500),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data provenance tracking
CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY,
    source_name VARCHAR(50) NOT NULL UNIQUE,
    source_type VARCHAR(30),
    license VARCHAR(50),
    api_endpoint VARCHAR(500),
    last_sync TIMESTAMPTZ,
    record_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Satellite catalog
CREATE TABLE IF NOT EXISTS satellites (
    sat_no INTEGER PRIMARY KEY,
    name VARCHAR(100),
    cospar_id VARCHAR(20),
    object_type VARCHAR(20),
    launch_date DATE,
    decay_date DATE,
    mass_kg DECIMAL(10,2),
    cross_section_m2 DECIMAL(10,4),
    drag_coeff DECIMAL(6,4) DEFAULT 2.5,
    srp_coeff DECIMAL(6,4) DEFAULT 1.5,
    orbital_regime VARCHAR(10),
    purpose VARCHAR(100),
    operator VARCHAR(100),
    launch_site VARCHAR(100),
    power_watts DECIMAL(10,2),
    amr_m2_kg DECIMAL(12,6),
    ucs_synced_at TIMESTAMPTZ,
    gcat_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Observations table (expanded v2.0.0)
CREATE TABLE IF NOT EXISTS observations (
    id VARCHAR(64) PRIMARY KEY,
    sat_no INTEGER,
    ob_time TIMESTAMPTZ NOT NULL,
    ra DECIMAL(12,8),
    declination DECIMAL(12,8),
    range_km DECIMAL(12,4),
    range_rate_km_s DECIMAL(10,6),
    azimuth DECIMAL(12,8),
    elevation DECIMAL(12,8),
    sensor_name VARCHAR(100),
    data_mode VARCHAR(20),
    track_id VARCHAR(64),
    is_uct BOOLEAN DEFAULT FALSE,
    is_simulated BOOLEAN DEFAULT FALSE,
    source_id INTEGER,
    observation_type VARCHAR(10) DEFAULT 'EO',
    -- Sensor position (geodetic)
    senlat DECIMAL(12,8),
    senlon DECIMAL(12,8),
    senalt DECIMAL(10,4),
    -- Sensor position (ECI cartesian, km)
    senx DECIMAL(16,6),
    seny DECIMAL(16,6),
    senz DECIMAL(16,6),
    -- Sensor velocity (ECI, km/s)
    senvelx DECIMAL(16,9),
    senvely DECIMAL(16,9),
    senvelz DECIMAL(16,9),
    -- Signal / photometric
    los_unc DECIMAL(12,6),
    exp_duration DECIMAL(10,4),
    zeroptd DECIMAL(16,10),
    net_obj_sig DECIMAL(16,6),
    net_obj_sig_unc DECIMAL(16,6),
    mag DECIMAL(8,4),
    mag_unc DECIMAL(8,4),
    -- Computed geo-position
    geolat DECIMAL(12,8),
    geolon DECIMAL(12,8),
    geoalt DECIMAL(12,4),
    georange DECIMAL(12,4),
    -- Solar angles
    solar_phase_angle DECIMAL(12,8),
    solar_eq_phase_angle DECIMAL(12,8),
    solar_dec_angle DECIMAL(12,8),
    -- UDL administrative / publishing fields
    classification_marking VARCHAR(50),
    id_sensor VARCHAR(50),
    id_on_orbit VARCHAR(50),
    orig_object_id VARCHAR(50),
    orig_sensor_id VARCHAR(50),
    shutter_delay DECIMAL(8,4) DEFAULT 0,
    raw_file_uri VARCHAR(500),
    source_name VARCHAR(50),
    created_by VARCHAR(100),
    orig_network VARCHAR(50),
    observation_type_udl VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_sat_time ON observations(sat_no, ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_track ON observations(track_id);

-- State vectors table (expanded v2.0.0)
CREATE TABLE IF NOT EXISTS state_vectors (
    id INTEGER PRIMARY KEY DEFAULT nextval('state_vectors_id_seq'),
    sat_no INTEGER,
    epoch TIMESTAMPTZ NOT NULL,
    x_pos DECIMAL(16,6) NOT NULL,
    y_pos DECIMAL(16,6) NOT NULL,
    z_pos DECIMAL(16,6) NOT NULL,
    x_vel DECIMAL(16,9) NOT NULL,
    y_vel DECIMAL(16,9) NOT NULL,
    z_vel DECIMAL(16,9) NOT NULL,
    covariance JSONB,
    source VARCHAR(50),
    data_mode VARCHAR(20),
    -- Physical parameters (v2.0.0)
    mass_kg DECIMAL(10,2),
    cross_section_m2 DECIMAL(10,4),
    drag_coeff DECIMAL(6,4),
    srp_coeff DECIMAL(6,4),
    -- UDL administrative fields (v2.0.0)
    classification_marking VARCHAR(50),
    reference_frame VARCHAR(20) DEFAULT 'J2000',
    cov_reference_frame VARCHAR(20),
    id_state_vector VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sat_no, epoch, source)
);

CREATE INDEX IF NOT EXISTS idx_sv_sat_epoch ON state_vectors(sat_no, epoch);

-- Element sets table (TLE data)
CREATE TABLE IF NOT EXISTS element_sets (
    id INTEGER PRIMARY KEY DEFAULT nextval('element_sets_id_seq'),
    sat_no INTEGER,
    line1 VARCHAR(70) NOT NULL,
    line2 VARCHAR(70) NOT NULL,
    epoch TIMESTAMPTZ NOT NULL,
    inclination DECIMAL(10,6),
    raan DECIMAL(10,6),
    eccentricity DECIMAL(12,10),
    arg_perigee DECIMAL(10,6),
    mean_anomaly DECIMAL(10,6),
    mean_motion DECIMAL(14,10),
    b_star DECIMAL(16,12),
    semi_major_axis_km DECIMAL(12,4),
    period_minutes DECIMAL(10,4),
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sat_no, epoch)
);

CREATE INDEX IF NOT EXISTS idx_elset_sat_epoch ON element_sets(sat_no, epoch);

-- Datasets table (expanded v2.0.0)
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY DEFAULT nextval('datasets_id_seq'),
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(20),
    version INTEGER DEFAULT 1,
    parent_id INTEGER,
    tier VARCHAR(5),
    orbital_regime VARCHAR(10),
    time_window_start TIMESTAMPTZ,
    time_window_end TIMESTAMPTZ,
    observation_count INTEGER,
    satellite_count INTEGER,
    avg_coverage DECIMAL(8,4),
    avg_obs_count DECIMAL(8,2),
    max_track_gap DECIMAL(8,4),
    downsampling_applied BOOLEAN DEFAULT FALSE,
    simulation_applied BOOLEAN DEFAULT FALSE,
    simulated_obs_count INTEGER DEFAULT 0,
    downsampling_config JSONB,
    simulation_config JSONB,
    generation_params JSONB,
    status VARCHAR(20) DEFAULT 'created',
    -- Deduplication / reuse (v2.0.0)
    config_hash VARCHAR(64),
    sensor_mode VARCHAR(5),
    -- Performance tracking (v2.0.0)
    performance_metrics JSONB,
    total_api_calls INTEGER DEFAULT 0,
    total_api_errors INTEGER DEFAULT 0,
    generation_duration_sec DECIMAL(12,3),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    json_path VARCHAR(500),
    parquet_path VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_datasets_config_hash ON datasets(config_hash);

-- Dataset-Observation junction table
CREATE TABLE IF NOT EXISTS dataset_observations (
    dataset_id INTEGER,
    observation_id VARCHAR(64),
    assigned_track_id INTEGER,
    assigned_object_id INTEGER,
    PRIMARY KEY (dataset_id, observation_id)
);

CREATE INDEX IF NOT EXISTS idx_ds_obs_dataset ON dataset_observations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_ds_obs_observation ON dataset_observations(observation_id);

-- Dataset references (truth data)
CREATE TABLE IF NOT EXISTS dataset_references (
    dataset_id INTEGER,
    sat_no INTEGER,
    state_vector_id INTEGER,
    element_set_id INTEGER,
    grouped_obs_ids JSONB,
    PRIMARY KEY (dataset_id, sat_no)
);

-- ============================================================
-- DATASET TRACKING TABLES (v2.0.0)
-- ============================================================

-- Query parameter tracking for dataset reproducibility
CREATE TABLE IF NOT EXISTS dataset_queries (
    id INTEGER PRIMARY KEY DEFAULT nextval('dataset_queries_id_seq'),
    dataset_id INTEGER NOT NULL,
    service VARCHAR(50) NOT NULL,
    endpoint_url VARCHAR(500),
    query_params JSONB NOT NULL,
    sat_no INTEGER,
    time_range_start TIMESTAMPTZ,
    time_range_end TIMESTAMPTZ,
    response_record_count INTEGER DEFAULT 0,
    response_status_code INTEGER,
    response_time_ms DECIMAL(10,2),
    rate_limit_delay_ms DECIMAL(10,2),
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    success BOOLEAN DEFAULT TRUE,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dq_dataset ON dataset_queries(dataset_id);

-- Per-dataset data source attribution
CREATE TABLE IF NOT EXISTS dataset_data_sources (
    dataset_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    observation_count INTEGER DEFAULT 0,
    state_vector_count INTEGER DEFAULT 0,
    element_set_count INTEGER DEFAULT 0,
    earliest_data TIMESTAMPTZ,
    latest_data TIMESTAMPTZ,
    PRIMARY KEY (dataset_id, source_id)
);

-- Link ILRS validation measurements to datasets
CREATE TABLE IF NOT EXISTS dataset_validation_measurements (
    dataset_id INTEGER NOT NULL,
    validation_measurement_id INTEGER NOT NULL,
    is_in_time_window BOOLEAN DEFAULT TRUE,
    distance_to_nearest_obs_sec DECIMAL(12,2),
    PRIMARY KEY (dataset_id, validation_measurement_id)
);

-- Per-dataset enrichment tracking
CREATE TABLE IF NOT EXISTS dataset_enrichment_log (
    id INTEGER PRIMARY KEY DEFAULT nextval('dataset_enrichment_log_id_seq'),
    dataset_id INTEGER NOT NULL,
    sat_no INTEGER NOT NULL,
    enrichment_source VARCHAR(50) NOT NULL,
    fields_updated JSONB,
    enrichment_success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    enriched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_del_dataset ON dataset_enrichment_log(dataset_id);

-- ============================================================
-- SUBMISSIONS AND RESULTS TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY DEFAULT nextval('submissions_id_seq'),
    dataset_id INTEGER,
    algorithm_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0',
    description TEXT,
    file_path VARCHAR(500),
    status VARCHAR(20) DEFAULT 'queued',
    job_id VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_submissions_dataset ON submissions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);

CREATE TABLE IF NOT EXISTS submission_results (
    id INTEGER PRIMARY KEY DEFAULT nextval('submission_results_id_seq'),
    submission_id INTEGER UNIQUE,
    true_positives INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    false_negatives INTEGER DEFAULT 0,
    "precision" DECIMAL(10,6) DEFAULT 0,
    recall DECIMAL(10,6) DEFAULT 0,
    f1_score DECIMAL(10,6) DEFAULT 0,
    position_rms_km DECIMAL(12,6),
    velocity_rms_km_s DECIMAL(12,9),
    mahalanobis_distance DECIMAL(12,6),
    ra_residual_rms_arcsec DECIMAL(12,6),
    dec_residual_rms_arcsec DECIMAL(12,6),
    raw_results JSONB,
    processing_time_seconds DECIMAL(12,3),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_results_submission ON submission_results(submission_id);
CREATE INDEX IF NOT EXISTS idx_results_f1 ON submission_results(f1_score DESC);

-- ============================================================
-- JOBS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(100) PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    stage VARCHAR(200),
    result JSONB,
    error TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);

-- ============================================================
-- VALIDATION MEASUREMENTS (ILRS Ground Truth)
-- ============================================================

CREATE TABLE IF NOT EXISTS validation_measurements (
    id INTEGER PRIMARY KEY DEFAULT nextval('validation_measurements_id_seq'),
    sat_no INTEGER NOT NULL,
    epoch TIMESTAMPTZ NOT NULL,
    range_m DECIMAL(15,6),
    station_code VARCHAR(10),
    station_name VARCHAR(100),
    normal_point_rms_m DECIMAL(10,6),
    num_returns INTEGER,
    source VARCHAR(20) DEFAULT 'ILRS',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sat_no, epoch, station_code)
);

CREATE INDEX IF NOT EXISTS idx_val_sat_epoch ON validation_measurements(sat_no, epoch);
CREATE INDEX IF NOT EXISTS idx_val_station ON validation_measurements(station_code);

-- ============================================================
-- EVENT LABELLING TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS event_types (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY DEFAULT nextval('events_id_seq'),
    event_type_id INTEGER,
    event_time_start TIMESTAMPTZ,
    event_time_end TIMESTAMPTZ,
    primary_sat_no INTEGER,
    secondary_sat_no INTEGER,
    confidence DECIMAL(5,4),
    detection_method VARCHAR(50),
    source VARCHAR(100),
    external_id VARCHAR(100),
    labelled_by VARCHAR(100),
    labelled_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS event_observations (
    event_id INTEGER,
    observation_id VARCHAR(64),
    PRIMARY KEY (event_id, observation_id)
);

-- ============================================================
-- UCTP LAB TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS uctp_runs (
    id INTEGER PRIMARY KEY DEFAULT nextval('uctp_runs_id_seq'),
    dataset_id INTEGER,
    algorithm_name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    f1_score DOUBLE PRECISION,
    "precision" DOUBLE PRECISION,
    recall DOUBLE PRECISION,
    position_rms_km DOUBLE PRECISION,
    velocity_rms_km_s DOUBLE PRECISION,
    clusters_found INTEGER,
    objects_resolved INTEGER,
    output_path VARCHAR(512),
    log_output TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uctp_runs_status ON uctp_runs(status);
CREATE INDEX IF NOT EXISTS idx_uctp_runs_dataset ON uctp_runs(dataset_id);

CREATE TABLE IF NOT EXISTS uctp_models (
    id INTEGER PRIMARY KEY DEFAULT nextval('uctp_models_id_seq'),
    name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    training_dataset_ids JSONB,
    training_config JSONB,
    training_epochs INTEGER,
    training_loss DOUBLE PRECISION,
    validation_loss DOUBLE PRECISION,
    best_f1_score DOUBLE PRECISION,
    best_position_rms_km DOUBLE PRECISION,
    model_path VARCHAR(512),
    status VARCHAR(20) DEFAULT 'training',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uctp_models_status ON uctp_models(status);

CREATE TABLE IF NOT EXISTS uctp_api_connections (
    id INTEGER PRIMARY KEY DEFAULT nextval('uctp_api_connections_id_seq'),
    service_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time_ms DOUBLE PRECISION,
    last_checked TIMESTAMPTZ DEFAULT NOW(),
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_uctp_api_service ON uctp_api_connections(service_name);

-- ============================================================
-- CREDENTIALS TABLE (encrypted credential storage)
-- ============================================================

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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credentials_service ON credentials(service_name);

-- ============================================================
-- SEED DATA
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

-- Insert default data sources (idempotent)
INSERT INTO data_sources (id, source_name, source_type, license, api_endpoint, notes) VALUES
    (1, 'UDL',         'OBSERVATION', 'RESTRICTED',    'https://unifieddatalibrary.com',   'Primary observation source (authenticated)'),
    (2, 'SATNOGS',     'OBSERVATION', 'CC-BY-SA',      'https://network.satnogs.org/api',  'RF observations from ground stations'),
    (3, 'GCAT',        'CATALOG',     'CC-BY',         'https://planet4589.org/space/gcat', 'Space object catalog by J. McDowell'),
    (4, 'UCS',         'CATALOG',     'OPEN',          'https://www.ucs.org',               'Operational satellite database'),
    (5, 'ILRS',        'VALIDATION',  'PUBLIC_DOMAIN', 'https://ilrs.gsfc.nasa.gov',        'Laser ranging ground truth'),
    (6, 'SPACE_TRACK', 'CATALOG',     'RESTRICTED',    'https://space-track.org',           'Official US space catalog')
ON CONFLICT (id) DO NOTHING;

-- Insert default credential stubs (idempotent)
INSERT INTO credentials (service_name, credential_type, label, description) VALUES
    ('udl',             'bearer_token',      'Unified Data Library', 'UDL API token (Base64-encoded credentials)'),
    ('esa',             'bearer_token',      'ESA Discosweb',       'ESA API bearer token for space debris data'),
    ('nasa_earthdata',  'jwt',               'NASA Earthdata',      'NASA Earthdata JWT authentication token'),
    ('spacetrack',      'username_password', 'Space-Track.org',     'Space-Track.org login credentials'),
    ('orekit',          'path',              'Orekit Data',         'Local file path to Orekit data directory')
ON CONFLICT (service_name) DO NOTHING;

-- Set schema version
INSERT INTO _schema_metadata (key, value, updated_at)
VALUES ('version', '2.0.0', NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
