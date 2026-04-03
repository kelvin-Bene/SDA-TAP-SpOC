-- Migration 005: Add error_message column to datasets table
-- When dataset generation fails (e.g., 0 satellites found for given parameters),
-- this column stores a user-facing explanation of why generation failed.

ALTER TABLE datasets ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Record migration
INSERT INTO _schema_metadata (key, value, updated_at)
VALUES ('migration_005', 'add_dataset_error_message', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
