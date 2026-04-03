"""Add FK constraints, CHECK constraints, indexes, composite_score, and RLS policies.

Cleans up orphan records, adds remaining foreign key constraints,
CHECK constraints for status/progress columns, performance indexes,
composite_score column to submission_results, and RLS policies.

Revision ID: 005
Revises: 004
Create Date: 2026-04-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # 1. Clean up orphan records in junction / child tables
    # ----------------------------------------------------------------
    op.execute(
        "DELETE FROM dataset_observations do_ "
        "WHERE NOT EXISTS (SELECT 1 FROM observations o WHERE o.id = do_.observation_id)"
    )
    op.execute(
        "DELETE FROM dataset_references dr "
        "WHERE NOT EXISTS (SELECT 1 FROM satellites s WHERE s.sat_no = dr.sat_no)"
    )
    op.execute(
        "DELETE FROM dataset_references dr "
        "WHERE NOT EXISTS (SELECT 1 FROM state_vectors sv WHERE sv.id = dr.state_vector_id) "
        "AND dr.state_vector_id IS NOT NULL"
    )
    op.execute(
        "DELETE FROM dataset_references dr "
        "WHERE NOT EXISTS (SELECT 1 FROM element_sets es WHERE es.id = dr.element_set_id) "
        "AND dr.element_set_id IS NOT NULL"
    )
    op.execute(
        "DELETE FROM observations o "
        "WHERE o.sat_no IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM satellites s WHERE s.sat_no = o.sat_no)"
    )
    op.execute(
        "DELETE FROM state_vectors sv "
        "WHERE sv.sat_no IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM satellites s WHERE s.sat_no = sv.sat_no)"
    )
    op.execute(
        "DELETE FROM element_sets es "
        "WHERE es.sat_no IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM satellites s WHERE s.sat_no = es.sat_no)"
    )
    op.execute(
        "DELETE FROM events e "
        "WHERE e.event_type_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM event_types et WHERE et.id = e.event_type_id)"
    )
    op.execute(
        "DELETE FROM events e "
        "WHERE e.primary_sat_no IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM satellites s WHERE s.sat_no = e.primary_sat_no)"
    )
    op.execute(
        "DELETE FROM event_observations eo "
        "WHERE NOT EXISTS (SELECT 1 FROM events e WHERE e.id = eo.event_id)"
    )
    op.execute(
        "DELETE FROM event_observations eo "
        "WHERE NOT EXISTS (SELECT 1 FROM observations o WHERE o.id = eo.observation_id)"
    )
    op.execute(
        "DELETE FROM datasets d "
        "WHERE d.parent_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM datasets p WHERE p.id = d.parent_id)"
    )

    # ----------------------------------------------------------------
    # 2. Add remaining FK constraints
    # ----------------------------------------------------------------

    # observations.sat_no -> satellites.sat_no
    op.execute(
        "ALTER TABLE observations "
        "ADD CONSTRAINT fk_obs_satellite "
        "FOREIGN KEY (sat_no) REFERENCES satellites(sat_no) ON DELETE SET NULL"
    )

    # state_vectors.sat_no -> satellites.sat_no
    op.execute(
        "ALTER TABLE state_vectors "
        "ADD CONSTRAINT fk_sv_satellite "
        "FOREIGN KEY (sat_no) REFERENCES satellites(sat_no) ON DELETE CASCADE"
    )

    # element_sets.sat_no -> satellites.sat_no
    op.execute(
        "ALTER TABLE element_sets "
        "ADD CONSTRAINT fk_elset_satellite "
        "FOREIGN KEY (sat_no) REFERENCES satellites(sat_no) ON DELETE CASCADE"
    )

    # dataset_references.sat_no -> satellites.sat_no
    op.execute(
        "ALTER TABLE dataset_references "
        "ADD CONSTRAINT fk_ds_ref_satellite "
        "FOREIGN KEY (sat_no) REFERENCES satellites(sat_no) ON DELETE CASCADE"
    )

    # dataset_references.state_vector_id -> state_vectors.id
    op.execute(
        "ALTER TABLE dataset_references "
        "ADD CONSTRAINT fk_ds_ref_state_vector "
        "FOREIGN KEY (state_vector_id) REFERENCES state_vectors(id) ON DELETE SET NULL"
    )

    # dataset_references.element_set_id -> element_sets.id
    op.execute(
        "ALTER TABLE dataset_references "
        "ADD CONSTRAINT fk_ds_ref_element_set "
        "FOREIGN KEY (element_set_id) REFERENCES element_sets(id) ON DELETE SET NULL"
    )

    # dataset_observations.observation_id -> observations.id
    op.execute(
        "ALTER TABLE dataset_observations "
        "ADD CONSTRAINT fk_ds_obs_observation "
        "FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE"
    )

    # events.event_type_id -> event_types.id
    op.execute(
        "ALTER TABLE events "
        "ADD CONSTRAINT fk_events_type "
        "FOREIGN KEY (event_type_id) REFERENCES event_types(id) ON DELETE SET NULL"
    )

    # events.primary_sat_no -> satellites.sat_no
    op.execute(
        "ALTER TABLE events "
        "ADD CONSTRAINT fk_events_primary_sat "
        "FOREIGN KEY (primary_sat_no) REFERENCES satellites(sat_no) ON DELETE SET NULL"
    )

    # event_observations.event_id -> events.id
    op.execute(
        "ALTER TABLE event_observations "
        "ADD CONSTRAINT fk_evobs_event "
        "FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE"
    )

    # event_observations.observation_id -> observations.id
    op.execute(
        "ALTER TABLE event_observations "
        "ADD CONSTRAINT fk_evobs_observation "
        "FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE"
    )

    # datasets.parent_id -> datasets.id (self-referencing for version lineage)
    op.execute(
        "ALTER TABLE datasets "
        "ADD CONSTRAINT fk_datasets_parent "
        "FOREIGN KEY (parent_id) REFERENCES datasets(id) ON DELETE SET NULL"
    )

    # ----------------------------------------------------------------
    # 3. CHECK constraints for status columns and progress ranges
    # ----------------------------------------------------------------

    op.execute(
        "ALTER TABLE datasets "
        "ADD CONSTRAINT chk_datasets_status "
        "CHECK (status IN ('created', 'processing', 'complete', 'failed'))"
    )

    op.execute(
        "ALTER TABLE submissions "
        "ADD CONSTRAINT chk_submissions_status "
        "CHECK (status IN ('queued', 'validating', 'processing', 'completed', 'failed'))"
    )

    op.execute(
        "ALTER TABLE jobs "
        "ADD CONSTRAINT chk_jobs_status "
        "CHECK (status IN ('pending', 'running', 'completed', 'failed'))"
    )

    op.execute(
        "ALTER TABLE jobs "
        "ADD CONSTRAINT chk_jobs_progress "
        "CHECK (progress >= 0 AND progress <= 100)"
    )

    op.execute(
        "ALTER TABLE feedback "
        "ADD CONSTRAINT chk_feedback_status "
        "CHECK (status IN ('open', 'in_progress', 'resolved', 'closed', 'wont_fix'))"
    )

    # ----------------------------------------------------------------
    # 4. NOT NULL on datasets.status (set default first for any NULLs)
    # ----------------------------------------------------------------

    op.execute("UPDATE datasets SET status = 'created' WHERE status IS NULL")
    op.execute(
        "ALTER TABLE datasets ALTER COLUMN status SET NOT NULL"
    )

    # ----------------------------------------------------------------
    # 5. New performance indexes
    # ----------------------------------------------------------------

    op.execute("CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_datasets_created_at ON datasets(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_feedback_reporter ON feedback(reporter_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_primary_sat ON events(primary_sat_no)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_time_range ON events(event_time_start, event_time_end)")

    # ----------------------------------------------------------------
    # 6. Add composite_score column to submission_results
    # ----------------------------------------------------------------

    op.execute(
        "ALTER TABLE submission_results "
        "ADD COLUMN composite_score DECIMAL(10,6)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_results_composite ON submission_results(composite_score DESC)"
    )

    # ----------------------------------------------------------------
    # 7. RLS policies for multi-tenant security
    # ----------------------------------------------------------------

    # Enable RLS on relevant tables
    op.execute("ALTER TABLE datasets ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE submissions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE submission_results ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feedback ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE profiles ENABLE ROW LEVEL SECURITY")

    # datasets: owners can manage their own, everyone can read
    op.execute(
        "CREATE POLICY datasets_select_policy ON datasets "
        "FOR SELECT USING (true)"
    )
    op.execute(
        "CREATE POLICY datasets_modify_policy ON datasets "
        "FOR ALL USING (user_id = current_setting('app.current_user_id', true))"
    )

    # submissions: owners can manage their own, everyone can read
    op.execute(
        "CREATE POLICY submissions_select_policy ON submissions "
        "FOR SELECT USING (true)"
    )
    op.execute(
        "CREATE POLICY submissions_modify_policy ON submissions "
        "FOR ALL USING (user_id = current_setting('app.current_user_id', true))"
    )

    # submission_results: readable by all (via join to submissions for ownership)
    op.execute(
        "CREATE POLICY results_select_policy ON submission_results "
        "FOR SELECT USING (true)"
    )
    op.execute(
        "CREATE POLICY results_modify_policy ON submission_results "
        "FOR ALL USING ("
        "  EXISTS ("
        "    SELECT 1 FROM submissions s "
        "    WHERE s.id = submission_results.submission_id "
        "    AND s.user_id = current_setting('app.current_user_id', true)"
        "  )"
        ")"
    )

    # feedback: reporters can manage their own, everyone can read
    op.execute(
        "CREATE POLICY feedback_select_policy ON feedback "
        "FOR SELECT USING (true)"
    )
    op.execute(
        "CREATE POLICY feedback_modify_policy ON feedback "
        "FOR ALL USING (reporter_id = current_setting('app.current_user_id', true))"
    )

    # profiles: users can only see and modify their own profile
    op.execute(
        "CREATE POLICY profiles_select_policy ON profiles "
        "FOR SELECT USING (id = current_setting('app.current_user_id', true))"
    )
    op.execute(
        "CREATE POLICY profiles_modify_policy ON profiles "
        "FOR ALL USING (id = current_setting('app.current_user_id', true))"
    )


def downgrade() -> None:
    # ----------------------------------------------------------------
    # 7. Drop RLS policies (reverse order)
    # ----------------------------------------------------------------

    op.execute("DROP POLICY IF EXISTS profiles_modify_policy ON profiles")
    op.execute("DROP POLICY IF EXISTS profiles_select_policy ON profiles")
    op.execute("DROP POLICY IF EXISTS feedback_modify_policy ON feedback")
    op.execute("DROP POLICY IF EXISTS feedback_select_policy ON feedback")
    op.execute("DROP POLICY IF EXISTS results_modify_policy ON submission_results")
    op.execute("DROP POLICY IF EXISTS results_select_policy ON submission_results")
    op.execute("DROP POLICY IF EXISTS submissions_modify_policy ON submissions")
    op.execute("DROP POLICY IF EXISTS submissions_select_policy ON submissions")
    op.execute("DROP POLICY IF EXISTS datasets_modify_policy ON datasets")
    op.execute("DROP POLICY IF EXISTS datasets_select_policy ON datasets")

    op.execute("ALTER TABLE profiles DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feedback DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE submission_results DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE submissions DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE datasets DISABLE ROW LEVEL SECURITY")

    # ----------------------------------------------------------------
    # 6. Drop composite_score column and index
    # ----------------------------------------------------------------

    op.execute("DROP INDEX IF EXISTS idx_results_composite")
    op.execute("ALTER TABLE submission_results DROP COLUMN IF EXISTS composite_score")

    # ----------------------------------------------------------------
    # 5. Drop performance indexes
    # ----------------------------------------------------------------

    op.execute("DROP INDEX IF EXISTS idx_events_time_range")
    op.execute("DROP INDEX IF EXISTS idx_events_primary_sat")
    op.execute("DROP INDEX IF EXISTS idx_feedback_reporter")
    op.execute("DROP INDEX IF EXISTS idx_jobs_created_at")
    op.execute("DROP INDEX IF EXISTS idx_submissions_created_at")
    op.execute("DROP INDEX IF EXISTS idx_datasets_created_at")
    op.execute("DROP INDEX IF EXISTS idx_datasets_status")

    # ----------------------------------------------------------------
    # 4. Revert NOT NULL on datasets.status
    # ----------------------------------------------------------------

    op.execute("ALTER TABLE datasets ALTER COLUMN status DROP NOT NULL")

    # ----------------------------------------------------------------
    # 3. Drop CHECK constraints
    # ----------------------------------------------------------------

    op.execute("ALTER TABLE feedback DROP CONSTRAINT IF EXISTS chk_feedback_status")
    op.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS chk_jobs_progress")
    op.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS chk_jobs_status")
    op.execute("ALTER TABLE submissions DROP CONSTRAINT IF EXISTS chk_submissions_status")
    op.execute("ALTER TABLE datasets DROP CONSTRAINT IF EXISTS chk_datasets_status")

    # ----------------------------------------------------------------
    # 2. Drop FK constraints
    # ----------------------------------------------------------------

    op.execute("ALTER TABLE datasets DROP CONSTRAINT IF EXISTS fk_datasets_parent")
    op.execute("ALTER TABLE event_observations DROP CONSTRAINT IF EXISTS fk_evobs_observation")
    op.execute("ALTER TABLE event_observations DROP CONSTRAINT IF EXISTS fk_evobs_event")
    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS fk_events_primary_sat")
    op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS fk_events_type")
    op.execute("ALTER TABLE dataset_observations DROP CONSTRAINT IF EXISTS fk_ds_obs_observation")
    op.execute("ALTER TABLE dataset_references DROP CONSTRAINT IF EXISTS fk_ds_ref_element_set")
    op.execute("ALTER TABLE dataset_references DROP CONSTRAINT IF EXISTS fk_ds_ref_state_vector")
    op.execute("ALTER TABLE dataset_references DROP CONSTRAINT IF EXISTS fk_ds_ref_satellite")
    op.execute("ALTER TABLE element_sets DROP CONSTRAINT IF EXISTS fk_elset_satellite")
    op.execute("ALTER TABLE state_vectors DROP CONSTRAINT IF EXISTS fk_sv_satellite")
    op.execute("ALTER TABLE observations DROP CONSTRAINT IF EXISTS fk_obs_satellite")

    # ----------------------------------------------------------------
    # 1. Orphan cleanup is not reversible (data already deleted)
    # ----------------------------------------------------------------
