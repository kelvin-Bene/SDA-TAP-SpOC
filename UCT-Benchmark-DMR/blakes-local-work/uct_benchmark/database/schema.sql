-- ============================================================
-- UCT Benchmark Database Schema
-- Version: 1.0.0
-- ============================================================

-- ============================================================
-- SCHEMA METADATA
-- ============================================================
CREATE TABLE IF NOT EXISTS _schema_metadata (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(500),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- SATELLITE CATALOG (Reference Data)
-- ============================================================
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

-- ============================================================
-- OBSERVATIONS (Time-Series Data)
-- ============================================================
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

-- Time-based index for efficient range queries
CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_sat_time ON observations(sat_no, ob_time);
CREATE INDEX IF NOT EXISTS idx_obs_track ON observations(track_id);

-- ============================================================
-- STATE VECTORS (Orbital State at Epoch)
-- ============================================================
CREATE TABLE IF NOT EXISTS state_vectors (
    id INTEGER PRIMARY KEY,
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

CREATE INDEX IF NOT EXISTS idx_sv_sat_epoch ON state_vectors(sat_no, epoch);

-- ============================================================
-- ELEMENT SETS (TLEs)
-- ============================================================
CREATE TABLE IF NOT EXISTS element_sets (
    id INTEGER PRIMARY KEY,
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

CREATE INDEX IF NOT EXISTS idx_elset_sat_epoch ON element_sets(sat_no, epoch);

-- ============================================================
-- DATASETS (Benchmark Dataset Metadata)
-- ============================================================
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY,
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

-- ============================================================
-- DATASET MEMBERSHIP (Many-to-Many)
-- ============================================================
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

CREATE TABLE IF NOT EXISTS dataset_references (
    dataset_id INTEGER,                   -- References datasets(id)
    sat_no INTEGER,                       -- References satellites(sat_no)
    state_vector_id INTEGER,              -- References state_vectors(id)
    element_set_id INTEGER,               -- References element_sets(id)

    -- Grouped observation IDs (for reference reconstruction)
    grouped_obs_ids JSON,

    PRIMARY KEY (dataset_id, sat_no)
);

-- ============================================================
-- EVENT LABELLING TABLES
-- ============================================================
CREATE TABLE IF NOT EXISTS event_types (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,     -- launch, maneuver, proximity, breakup, reentry
    description TEXT
);

-- Insert default event types
INSERT INTO event_types (name, description)
SELECT 'launch', 'Object launched into orbit'
WHERE NOT EXISTS (SELECT 1 FROM event_types WHERE name = 'launch');

INSERT INTO event_types (name, description)
SELECT 'maneuver', 'Orbital maneuver detected'
WHERE NOT EXISTS (SELECT 1 FROM event_types WHERE name = 'maneuver');

INSERT INTO event_types (name, description)
SELECT 'proximity', 'Close approach between two objects'
WHERE NOT EXISTS (SELECT 1 FROM event_types WHERE name = 'proximity');

INSERT INTO event_types (name, description)
SELECT 'breakup', 'Object fragmentation event'
WHERE NOT EXISTS (SELECT 1 FROM event_types WHERE name = 'breakup');

INSERT INTO event_types (name, description)
SELECT 'reentry', 'Object reentered atmosphere'
WHERE NOT EXISTS (SELECT 1 FROM event_types WHERE name = 'reentry');

INSERT INTO event_types (name, description)
SELECT 'unknown', 'Unknown or unclassified event'
WHERE NOT EXISTS (SELECT 1 FROM event_types WHERE name = 'unknown');

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS event_observations (
    event_id INTEGER,                     -- References events(id)
    observation_id VARCHAR(64),           -- References observations(id)

    PRIMARY KEY (event_id, observation_id)
);

-- ============================================================
-- STORE SCHEMA VERSION
-- ============================================================
INSERT OR REPLACE INTO _schema_metadata (key, value, updated_at)
VALUES ('version', '1.0.0', CURRENT_TIMESTAMP);
