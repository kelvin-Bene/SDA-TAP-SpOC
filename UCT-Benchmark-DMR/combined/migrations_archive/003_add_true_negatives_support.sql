-- ============================================================
-- Migration 003: Add True Negatives Support
-- Version: 1.0.0 -> 1.1.0
-- Description: Adds support for non-reference observations
--              and breakup event caching
-- ============================================================

-- Add non-reference observation support to datasets
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS non_ref_observation_count INTEGER DEFAULT 0;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS include_non_ref_obs BOOLEAN DEFAULT FALSE;

-- Create non_reference_observations table
CREATE TABLE IF NOT EXISTS non_reference_observations (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    observation_id VARCHAR(64) NOT NULL,
    sensor_id VARCHAR(32),
    obs_time TIMESTAMP NOT NULL,
    ra_deg DOUBLE PRECISION,
    dec_deg DOUBLE PRECISION,
    source_norad_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_non_ref_obs_dataset ON non_reference_observations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_non_ref_obs_norad ON non_reference_observations(source_norad_id);

-- Create breakup_events cache table
CREATE TABLE IF NOT EXISTS breakup_events (
    id SERIAL PRIMARY KEY,
    parent_norad_id INTEGER NOT NULL,
    parent_name VARCHAR(100),
    event_date TIMESTAMP NOT NULL,
    debris_count INTEGER DEFAULT 0,
    debris_norad_ids JSONB,
    event_type VARCHAR(50),
    source VARCHAR(20) NOT NULL,
    cached_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(parent_norad_id, event_date, source)
);

CREATE INDEX IF NOT EXISTS idx_breakup_events_date ON breakup_events(event_date);
CREATE INDEX IF NOT EXISTS idx_breakup_events_parent ON breakup_events(parent_norad_id);

-- Backfill: existing datasets have no non-ref obs
UPDATE datasets SET non_ref_observation_count = 0, include_non_ref_obs = FALSE
WHERE non_ref_observation_count IS NULL;

-- Update schema version
INSERT INTO _schema_metadata (key, value, updated_at)
VALUES ('version', '1.1.0', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
