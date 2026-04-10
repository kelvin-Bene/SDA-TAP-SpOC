# UCT Benchmark — Transition Document

**Date:** April 9, 2026
**Prepared by:** DataMine Team (Spring 2026)
**For:** Next development team / stakeholders

This document captures the state of the UCT Benchmark system at project handover, including what was built, what remains, and where to focus next. Per Louis Caves (AFRL Scholars), this should communicate: "This is the vision of what we wanted the system to be," alongside what is implemented, suboptimal, and aspirational.

---

## 1. System Overview — What We Built

The UCT Benchmark is a web platform for generating space domain awareness (SDA) datasets and evaluating UCT (Uncorrelated Track) processors. Users generate observation datasets from real UDL (Unified Data Library) data, download them, run their UCT processors, and submit results for scoring on a leaderboard.

**Tech stack:** Python 3.12 + FastAPI backend, React/TypeScript frontend, PostgreSQL (Supabase) database, Orekit (Java) for orbit propagation.

**Overall implementation: ~85% of vision realized.**

---

## 2. What Works (Implemented & Functional)

| Component | Status | Notes |
|-----------|--------|-------|
| Dataset generation (T1/T2/T3) | 95% | Queries UDL, applies downsampling + simulation |
| Web UI | 90% | 13 pages, dataset wizard, profile, settings |
| Submission upload & validation | 90% | JSON upload, UCTP schema validation, state vector + TLE formats |
| Evaluation pipeline | 95% | Binary metrics (F1), state metrics (Mahalanobis), residual metrics |
| Composite scoring | 100% | Weighted: 0.4 binary + 0.3 state + 0.3 residual |
| Leaderboard | 90% | Ranked by test_composite_score, per-split breakdown |
| Authentication | 95% | JWT, Supabase, role-based access |
| Dataset download | 100% | Minimized fields, no answer-key leakage (Apr 2026 fix) |
| CTF challenges | 85% | Poor calibration (sensor biases), maneuver-during-gap |
| Train/val/test splits | 100% | 60/20/20 stratified, test never downloadable |
| Database | 95% | 14+ tables, repository pattern, DuckDB dev / Postgres prod |

---

## 3. What's Suboptimal (Works, But Could Be Better)

### 3.1 Monte Carlo Covariance Propagation (Evaluator Performance)
**File:** `uct_benchmark/simulation/propagator.py:171-215`, `uct_benchmark/evaluation/stateMetrics.py`

**Current behavior:** The state metrics evaluator propagates covariance using Monte Carlo sampling — it draws ~100 sample points from the initial covariance, propagates each through a full force model (gravity harmonics, drag, SRP), then computes posterior covariance from the sample distribution.

**Problem:** This requires ~100 expensive orbit integrations per state vector pair. Evaluation of a 10-satellite dataset means ~1,000 integrations.

**Better approach (per Louis):** Linear covariance propagation via State Transition Matrix (STM). Compute the STM once, then propagate covariance directly: `P(tf) = Phi * P(t0) * Phi^T`. This reduces N integrations to 1 integration + a matrix multiplication — approximately 100x speedup.

**Tradeoff:** Linear propagation assumes Gaussian uncertainty; loses accuracy for highly nonlinear regimes (multi-day propagation in LEO with significant drag uncertainty). For the typical benchmark evaluation windows, linear propagation would be sufficient.

### 3.2 Orekit Java Dependency
**File:** `uct_benchmark/simulation/propagator.py`

The full evaluation pipeline (state metrics, residual metrics) depends on Orekit via `orekit-jpype`, which requires a Java 17+ JDK at runtime. This is the main production deployment blocker. Without Orekit, only binary metrics (F1/precision/recall) can be computed.

**Options for next team:**
1. Ensure Java is available in production Docker image
2. Switch to a Python-native propagator (SGP4 for TLE-based, or Poliastro for numerical)
3. Pre-compute propagations during dataset generation and cache results

### 3.3 Event Detection Data Source
**File:** `uct_benchmark/labelling/eventDetection.py`

Infrastructure for event labeling (maneuver, breakup, proximity, launch detection) is built, but there is no operational data source feeding real event data. The database schema supports it (`events` and `event_types` tables), but the event detection algorithms have nothing to process.

### 3.4 Dataset JSON Size
While we now whitelist only essential fields in downloads (Apr 2026), the raw `observations` table still stores all UDL metadata. For very large datasets, consider also trimming what's persisted at generation time, or switching to Parquet format for storage.

---

## 4. What We Wanted to Build But Didn't Have Time

### 4.1 Dataset Answer Key Encryption (DGX Spark)
For the local/DGX Spark deployment, datasets and answer keys are co-located on the same machine. An encryption layer for the answer key file would prevent casual inspection. Not needed for the web version (answer keys never leave the server), but important for local deployments.

### 4.2 Dataset Sync for Local Instances
Louis suggested: "Every so often, if it can be hooked up to the Internet, have some sort of sync that can go grab datasets from a remote server." This would allow DGX Spark units deployed offline to periodically sync new datasets when Internet is available.

### 4.3 T4 Object Simulation
Tier 4 processing (synthetic satellite generation) — 0% implemented. T1-T3 cover most real-world scenarios. T4 would allow benchmarking against entirely synthetic objects with controlled parameters.

### 4.4 ILRS Validation Integration
International Laser Ranging Service validation is 40% complete (satellite/station lists done). Blocked on NASA Earthdata authentication for prediction queries.

### 4.5 S3/Cloud Storage for Datasets
Team explored Amazon S3 for scalable dataset storage. Put on hold pending clarity on whether the system will be deployed remotely or locally (DGX Spark). If deploying to SDA TapLab infrastructure, S3 may not be needed.

### 4.6 Cross-Instance Leaderboard Federation
If multiple DGX Spark units each have local leaderboards, a federation mechanism to aggregate scores across instances would be valuable for organization-wide benchmarking.

---

## 5. "Wouldn't It Be Nice" Features

- **LLM chatbot for result interpretation:** Partially implemented in DGX local edition. Users can ask questions about their evaluation results, leaderboard standings, and dataset characteristics. Could be integrated into the main web platform.
- **3D globe visualization:** Render satellite orbits and sensor locations on an interactive globe. Low priority but impressive for demos.
- **Radar/statistical testing metrics:** Additional evaluation metrics beyond optical-based scoring.
- **Real UCTP validation with Aerospace Corp:** Blocked on dataset stability and availability of a reference UCT processor.
- **Report generation improvements:** PDF export of evaluation results exists but could be more polished.

---

## 6. Known Bugs & Open Items

| Issue | Severity | Details |
|-------|----------|---------|
| Feedback PATCH returns 501 | Low | Schema mismatch between model and production columns (`BACKLOG.md` Section A) |
| Orphaned Alembic migration chain | Low | `alembic_version` table never created; migrations 001-006 dead code (Section B) |
| Silent DDL exception swallow | Medium | `schema.py:884-887` masks schema drift with `pass` (Section C) |
| 31 legacy datasets can't be evaluated | Medium | Pre-Phase-1 datasets have no `dataset_references` rows (Section D) |
| RA/Dec residual column naming | Low | `dec_residual_rms_arcsec` always NULL; single great-circle residual in `ra` column (Section E) |
| Linux setup.sh syntax errors | Medium | Missing spaces before `]` in bash conditionals (ISSUES_BACKLOG #3) |
| Python version docs conflict | Low | Docs say 3.9-3.12, pyproject.toml requires 3.12 only (ISSUES_BACKLOG #2) |

---

## 7. Architecture Decisions Worth Knowing

1. **Database adapter pattern:** `uct_benchmark/database/adapters/` — DuckDB for local dev, PostgreSQL for production. Adding a new adapter (e.g., SQLite for DGX Spark) just means implementing the `BaseAdapter` interface.

2. **Answer key is the database, not a file:** State vectors, covariances, and satellite-observation mappings are stored in `state_vectors` + `dataset_references` tables. Downloads never contain identifying information. Evaluation reads truth data directly from the database.

3. **CTF design:** Inspired by LLNL CTF paper. Train rows provide labeled data; validation rows have satellite IDs stripped; test rows are never downloadable. Leaderboard ranks by test split composite score.

4. **Composite scoring weights:** `0.4 * F1 + 0.3 * state_component + 0.3 * residual_component`. Configurable via environment variables (`COMPOSITE_WEIGHT_BINARY`, etc.).

5. **Streaming downloads:** Dataset downloads are streamed in 5,000-row batches to avoid OOM on large datasets.

---

## 8. Deployment Notes

- **Production:** Supabase (PostgreSQL) + Vercel/Docker
- **Demo:** Dockerfile.demo with DuckDB, no external dependencies
- **DGX Spark:** ARM64 local build (Kelvin's branch), offline-capable with bundled datasets
- **SDA TapLab:** Deployment discussion deferred to end-of-month expo; likely will be handed off to TapLab infrastructure team

---

## 9. Key People

| Person | Role | Contact For |
|--------|------|-------------|
| Louis Caves | AFRL Scholars, Project Stakeholder | Vision, evaluation methodology, orbital mechanics questions |
| Dr. Cline | Mentor | Project continuity, academic guidance |
| Kelvin | Lead Developer | Codebase, deployment, DGX Spark local edition |
| David | Developer | Frontend, demo walkthrough |
| Bryant | Project Lead | Handover logistics, team coordination |
| Pete Dragniv / Dan Herlumen | Space Force contacts | DGX Spark hardware, deployment requirements |

---

## 10. Where to Start

If you're picking up this project:

1. **Read the Quick Start Guide** (`generated-docs/docs/QUICK_START.md`) to get the system running
2. **Read VISION_ALIGNMENT_AUDIT.md** at the repo root for the full alignment assessment
3. **Focus on:** Getting Orekit working in your production environment — this unblocks full evaluation
4. **Then:** Address items in Section 3 (suboptimal solutions) to improve performance
5. **Refer to:** `provided-materials/` for all stakeholder transcripts and original project documentation
