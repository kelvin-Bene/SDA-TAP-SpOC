# UCT Benchmark — Deferred Work Backlog

This file tracks work that has been **intentionally deferred** in favour of
closing higher-priority gaps in Louis Caves's vision (see
`D:\DMR\DMR(kelvinallignment)\VISION_ALIGNMENT_AUDIT.md` and the Jan 22 / Feb 19
2026 transcripts in `provided-materials/`).

Nothing here blocks a working end-to-end benchmark MVP. Pick items off this
list once the leaderboard shows real composite scores against real datasets
and Louis's documented gaps (composite scoring, event data, close-object
calibration, target-percentage enforcement) have landed.

---

## Section A — Feedback table cross-project schema sync

**Status:** Dormant — PATCH endpoint returns 501.

**What happened:** On 2026-03-24 the production `feedback` table was rewritten
by the Cross-Project In-App Bug Reporting Widget plan (Claude Code session
`0cbe179f-15ab-4984-96dc-e65b9e3e9326`). Production now has columns
`project`, `environment`, `resolution_notes`, `resolved_at`, `resolved_by`.
The DMR codebase (`backend_api/routers/feedback.py`,
`backend_api/models/feedback.py:43-47`, `uct_benchmark/database/schema.py:557`,
`uct_benchmark/database/schema_postgres.sql:449`) still describes the original
DMR-only shape with `resolution` / `updated_at`.

POST and GET work (the writer only writes columns that exist; the reader uses
`SELECT *`). PATCH used to return 500 on every call; it now returns 501 with a
pointer back here.

**To resolve:**
1. Rename `FeedbackUpdate.resolution` → `resolution_notes` in
   `backend_api/models/feedback.py:43-47`.
2. Rewrite the PATCH UPDATE branches to target `resolution_notes`,
   `resolved_at = now()`, and `resolved_by = user.id`.
3. Sync the two schema source-of-truth files
   (`uct_benchmark/database/schema_postgres.sql:449-470` and
   `uct_benchmark/database/schema.py:557-580`) to match production.
4. Decide whether DMR participates as a tenant in the cross-project ClickUp
   integration (see Section F).

**When to pick this up:** When an admin actually wants to triage feedback
through the UI, or when the cross-project widget becomes unified across all
tenants. Until then, use direct SQL on Supabase.

---

## Section B — Orphaned Alembic chain

**Status:** Dormant — migrations 001–006 are dead code for production.

**What happened:** Production Supabase has **no `alembic_version` table**
(verified live). Migrations in `alembic/versions/` have never been applied.
The production schema was built by the initial `schema_postgres.sql` execution
plus ad-hoc DDL via Supabase Studio (e.g. the cross-project feedback
rewrite). Migration `005_constraints_indexes_composite.py:201` even references
a `'wont_fix'` status that doesn't appear in the production CHECK constraint
(`'open','in_progress','resolved','closed'`).

**To resolve:** Pick one migration system and stamp production accordingly.
Two reasonable paths:

- **Stamp Alembic at 006 and pick up from there.** Create a corrective
  migration 007 that describes everything production actually has that 001–006
  didn't cover (cross-project feedback columns, composite_score column,
  satellites physical params, dataset_references wiring). `alembic stamp head`
  on a clean prod DB, then future changes flow through Alembic.
- **Delete the Alembic chain and commit fully to the inline
  `_migrate_to_*` helpers in `uct_benchmark/database/schema.py`.** These
  already run at app startup. Add a corresponding `_migrate_to_1_9_0` with the
  cross-project feedback columns.

**When to pick this up:** Before the next schema change. Don't do it as its
own sprint.

---

## Section C — Silent DDL swallow at `schema.py:884-887`

**Status:** Dormant — existing behaviour.

**What happened:** `_initialize_postgres_schema` iterates over
`schema_postgres.sql` statements and swallows every `except Exception: pass`.
Intent was idempotent re-runs for `CREATE TABLE IF NOT EXISTS`, but in
practice it has masked every schema drift we've hit — including the feedback
rewrite from Section A. The first boot after a schema change fails silently,
the app keeps running against the old definition, and the DB stays on the new
shape.

**To resolve:** Replace the bare `pass` at `schema.py:884-887` with

```python
except Exception as e:
    logger.warning(f"DDL skipped or failed: {statement.strip()[:120]} -> {e}")
```

The intent (idempotent re-runs) is preserved because `CREATE TABLE IF NOT
EXISTS` and `ADD COLUMN IF NOT EXISTS` still no-op cleanly. The win is that
genuine drift now shows up in the logs instead of being invisible.

**When to pick this up:** Any time. Ten-minute change, high signal, zero
regression risk.

---

## Section D — Reference data backfill for legacy datasets

**Status:** Dormant — legacy datasets (pre-Phase-1) cannot be evaluated.

**What happened:** Production has 31 datasets and 33,711
`dataset_observations` rows but only 1 `dataset_references` row (with NULL
foreign keys). Phase 1 of the 2026-04-07 MVP plan wires up persistence for new
datasets, but there is no backfill path for the 31 existing ones.

**To resolve (when someone actually asks):**
- Short path: mark legacy datasets as `status='archived'` and force users to
  regenerate if they want to submit against them.
- Long path: re-run `generateDataset()` against each legacy dataset's
  parameters, accepting that UDL data may have changed between the original
  run and the backfill. The same dataset name can host a new version via
  `parent_id` for lineage.

**When to pick this up:** Only if a user reports a legacy dataset they care
about. Otherwise leave them as broken placeholders; they have `f1=0` in the
leaderboard anyway (single 2026-01-29 row).

---

## Section E — Phantom RA / Dec residual columns

**Status:** Dormant — single great-circle residual is stored in the `ra`
slot, `dec` is NULL.

**What happened:** The production `submission_results` table has separate
`ra_residual_rms_arcsec` and `dec_residual_rms_arcsec` columns. But
`uct_benchmark/evaluation/residualMetrics.py:103-111` computes the residual
as a **single great-circle scalar** per observation (arccos of the dot
product on the unit sphere, converted to arcseconds). There's no split
anywhere in the code; the dec column has never had a real value.

The Phase 2 worker writes the single great-circle RMS into the `ra` slot and
leaves `dec` NULL, to keep the existing test fixtures and GET /results
response shape working.

**To resolve:** Two options:

1. **Split the residual into RA cos(dec) and dec components.** In
   `residualMetrics.retrieveResiduals` lines 95-108 (which currently does
   `np.arccos(sin·sin + cos·cos·cos)`), replace the great-circle calc with:
   ```
   delta_ra  = (alpha_obs_est - alpha_obs) * cos(delta_obs)
   delta_dec =  delta_obs_est  - delta_obs
   ```
   Return both as separate RMSes. This is ~6 lines, matches what OD textbooks
   call "residual in RA cos(dec)" and "residual in dec", and gives Louis two
   separately-meaningful numbers.

2. **Drop the dec column entirely and rename ra → `residual_rms_arcsec`.**
   Simpler but requires a DDL change, schema_postgres.sql sync, and test
   fixture updates.

**Recommendation:** Option 1 if Louis asks for more residual detail, option 2
otherwise. Defer until we see how the leaderboard actually reads after the
Phase 4 UI ships.

---

## Section F — ClickUp integration parity for DMR feedback

**Status:** Dormant — DMR feedback POST does not create ClickUp tickets.

**What happened:** The Eck Media projects (MasterDB, PromoFlow, OTL) have
ClickUp ticket creation wired into their feedback POST endpoints as part of
the cross-project widget plan. DMR's `backend_api/routers/feedback.py:44-145`
just writes to the `feedback` table and returns.

**To resolve:** Only if Louis (or an Eck Media stakeholder) decides the DMR
benchmark should participate in the shared ticket triage flow. Otherwise
leave it: DMR users still get their feedback persisted and admins can triage
via direct SQL, and there's no cross-project dependency to maintain.

---

## Not in this backlog (explicit non-items)

- **AI chatbot** — Louis explicitly deprioritised this on Feb 19, 2026
  ("I don't know if that necessarily helps advance the project towards our
  minimum success criterias"). Not on the roadmap.
- **3D globe visualisation** — Mentioned by Aidan on Feb 19, implicitly
  deprioritised by Louis. Shipped as of Apr 16, 2026 anyway at user's
  direction, using the pre-existing `OrbitViewer` component. Integrated
  on DatasetDetailPage (owner+admin only, per Apr 9 answer-key separation),
  ResultsPage (own-submissions), and the public LandingPage hero
  (desktop-only, static fixture `/demo-orbits.json`). Backend endpoints:
  `GET /datasets/{id}/reference-orbits` and `GET /submissions/{id}/predictions`.
- **Custom UCT processor** — Louis explicitly told David Xiao's team to
  focus their energies elsewhere (Feb 19, ~line 568). Not on the roadmap.
