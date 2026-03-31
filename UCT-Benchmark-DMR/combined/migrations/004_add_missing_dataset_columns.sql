-- Migration 004: Add missing columns to datasets table
-- These columns exist in the DuckDB schema but were missing from the PostgreSQL schema,
-- causing the dataset generation worker UPDATE to fail and leaving stats as NULL/0.

-- Legacy code for dataset lineage tracking
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS legacy_code VARCHAR(16);

-- Actual satellite IDs discovered during generation (JSONB array)
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS actual_satellite_ids JSONB;

-- Performance metadata from generation run (JSONB object)
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS performance_metadata JSONB;

-- Classification marking for dataset provenance
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS classification_marking VARCHAR(50);

-- Index for legacy_code lookups used in version history
CREATE INDEX IF NOT EXISTS idx_datasets_legacy_code ON datasets(legacy_code);

-- Record migration
INSERT INTO _schema_metadata (key, value, updated_at)
VALUES ('migration_004', 'add_missing_dataset_columns', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
