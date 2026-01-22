# Documentation Consistency Review

**Date:** January 13, 2026
**Purpose:** Ensure all project documentation is consistent and aligned

---

## Executive Summary

After reviewing all documentation across the repository, **12 significant inconsistencies** were identified. This document catalogs each inconsistency and provides the correct/authoritative information.

---

## 1. CRITICAL: Overall Project Progress

### Inconsistency Found

| Document | Progress Stated |
|----------|-----------------|
| `TEAM_SPLIT_READINESS.md` | 60% complete |
| `planning/PROJECT_STATUS.md` | ~40% complete |
| `planning/INTEGRATED_ROADMAP.md` | Phase 1: 90%, Phase 2: 25% |

### Resolution

**Authoritative Answer:** The project is approximately **45-50% complete** toward the final goal of a Web-hosted CTF platform.

**Breakdown:**
- Foundation/Infrastructure: 90% complete
- Data Pipeline Enhancements: 25% complete
- Web Platform: 0% complete
- Algorithm Framework: 0% complete

The discrepancy exists because:
- `TEAM_SPLIT_READINESS.md` focuses on readiness to split teams (60%)
- `PROJECT_STATUS.md` focuses on final deliverable completion (40%)

**Action:** Update all documents to use consistent methodology - recommend using phase-based progress.

---

## 2. CRITICAL: Data Labelling vs Event Labelling

### Inconsistency Found

| Document | Statement |
|----------|-----------|
| `TEAM_SPLIT_READINESS.md` | "Data Labelling - COMPLETE - 100%" |
| `planning/PROJECT_STATUS.md` | "Event Labelling - Not Started - 0%" |
| `planning/SDA_TAP_LAB_PLAN.md` | "Event Labelling - Not Started - 0%" |

### Resolution

**These are TWO DIFFERENT THINGS:**

| Term | Definition | Status |
|------|------------|--------|
| **Data Labelling** | Dataset code system for categorizing datasets by regime, sensor, tier | **COMPLETE** (100%) |
| **Event Labelling** | Classifying observations by event type (launch, maneuver, proximity, breakup) | **NOT STARTED** (0%) |

**Authoritative Definitions:**

1. **Data Labelling (COMPLETE):**
   - Dataset code generation system in `windowTools.py`
   - Tier classification (T1-T5) in `basicScoringFunction.py`
   - Orbital regime classification (LEO, MEO, GEO, HEO)
   - Sensor type classification (Optical, Radar, RF)

2. **Event Labelling (NOT STARTED):**
   - Launch event detection and labelling
   - Maneuver event detection and labelling
   - Proximity event detection and labelling
   - Breakup event detection and labelling

**Action:** Update `TEAM_SPLIT_READINESS.md` to clarify this distinction. The correct status is:
- Dataset Categorization System: COMPLETE (100%)
- Event Classification System: NOT STARTED (0%)

---

## 3. Repository Structure Outdated

### Inconsistency Found

`docs/README.md` shows:
```
├── UCT Benchmarking/
├── SDA x SpOC UCT Processing/
└── uct-benchmark-refactor-joncline/
```

**Actual structure after reorganization:**
```
├── UCT-Benchmark-DMR/combined/          # Active development
├── documentation/              # Provided docs (moved)
│   ├── UCT Benchmarking/
│   └── SDA x SpOC UCT Processing/
├── external-code/              # Reference branches
│   ├── master/
│   ├── jovan-linuxTesting/
│   └── uct-benchmark-refactor-joncline/
├── docs/                       # Root documentation
└── planning/                   # Planning documents
```

### Resolution

**Action Required:** Update `docs/README.md` to reflect the new structure created by the `kelvin-organize` branch.

---

## 4. Main Codebase Location

### Inconsistency Found

| Document | Referenced Location |
|----------|---------------------|
| `docs/ARCHITECTURE.md` | `uct-benchmark-refactor-joncline/uct_benchmark/` |
| `docs/README.md` | `uct-benchmark-refactor-joncline/` |
| `UCT-Benchmark-DMR/combined/README.md` | `UCT-Benchmark-DMR/combined/uct_benchmark/` |

### Resolution

**Authoritative Answer:** The primary development codebase is now at:
```
UCT-Benchmark-DMR/combined/uct_benchmark/
```

The `external-code/uct-benchmark-refactor-joncline/` is a reference copy of the upstream refactored branch.

**Action Required:** Update `docs/ARCHITECTURE.md` and `docs/README.md` to reference `UCT-Benchmark-DMR/combined/uct_benchmark/`.

---

## 5. Web UI Technology Stack

### Inconsistency Found

| Document | Recommendation |
|----------|----------------|
| `TEAM_SPLIT_READINESS.md` | "NextJS per LLNL", "ExpressJS per LLNL" |
| `planning/SPOC_PLAN.md` | "React recommended", "FastAPI recommended" |
| LLNL Paper | "NextJS frontend, ExpressJS API, Python backend" |
| Refactored codebase | Solara (Python web framework) as alternative |

### Resolution

**Options Available:**

| Option | Frontend | Backend | Pros | Cons |
|--------|----------|---------|------|------|
| **LLNL Stack** | NextJS (React) | ExpressJS | Matches LLNL reference implementation | Requires JS expertise |
| **Python Stack** | Solara/Streamlit | FastAPI | All Python, easier for current team | Less standard |
| **Hybrid** | React | FastAPI | Modern, Python backend | Mixed stack |

**Recommendation:** Defer technology decision to mentor/team discussion. Document all options.

**Action Required:** Add note in `SPOC_PLAN.md` acknowledging the LLNL reference architecture while noting alternatives.

---

## 6. API Integration Completeness

### Inconsistency Found

| Document | Status |
|----------|--------|
| `TEAM_SPLIT_READINESS.md` | "100%" |
| `planning/PROJECT_STATUS.md` | "95%" |
| `planning/INTEGRATED_ROADMAP.md` | "95%" |

### Resolution

**Authoritative Answer:** API Integration is **95% complete**.

Remaining work:
- Error retry logic for network failures
- Rate limiting improvements
- Caching for repeated queries

**Action Required:** Update `TEAM_SPLIT_READINESS.md` to show 95%.

---

## 7. Evaluation Pipeline Status

### Inconsistency Found

| Document | Status |
|----------|--------|
| `TEAM_SPLIT_READINESS.md` | "Evaluation Metrics - COMPLETE - 90%" |
| `planning/SPOC_PLAN.md` | "Evaluation Pipeline - Partial - 75%" |

### Resolution

**Clarification:**
- **Evaluation Metrics** (the calculations): 90% complete
- **Evaluation Pipeline** (end-to-end flow): 75% complete

The pipeline is incomplete because `Evaluation.py`'s `main()` function is empty.

**Action Required:** Update documents to distinguish between metrics and pipeline.

---

## 8. Database Status Terminology

### Inconsistency Found

| Document | Term Used | Status |
|----------|-----------|--------|
| `TEAM_SPLIT_READINESS.md` | "Data Storage" | "PARTIAL - 70%" |
| `PROJECT_STATUS.md` | "Centralized Database" | "Not Started - 0%" |

### Resolution

**Clarification:**
- **Local File Storage** (Parquet/JSON): WORKING (the 70%)
- **Centralized Database** (PostgreSQL/etc.): NOT STARTED (0%)

These are different things. The project currently uses local files, which works for development but doesn't support team collaboration or web deployment.

**Action Required:** Update `TEAM_SPLIT_READINESS.md` to clarify:
- Local File Storage: 100% functional
- Centralized Database: 0% (not started)

---

## 9. Package Name Inconsistency

### Inconsistency Found (From Previous Audit)

| Location | Package Name |
|----------|--------------|
| `UCT-Benchmark-DMR/combined/pyproject.toml` | `uct_benchmark` |
| `external-code/master/pyproject.toml` | `uctbenchmark` |
| `external-code/jovan-linuxTesting/pyproject.toml` | `uctbenchmark` |

### Resolution

**Authoritative Answer:** The standard package name is `uct_benchmark` (with underscore) per PEP 8.

**Status:** Documented in `ISSUES_BACKLOG.md` - deferred for future resolution.

---

## 10. Documentation Location Duplication

### Issue Found

Documentation exists in multiple locations:
- `docs/` - Root level documentation
- `UCT-Benchmark-DMR/combined/docs/docs/` - Kelvin's documentation
- `planning/` - Planning documents
- `documentation/` - Provided documentation

### Resolution

**Proposed Documentation Structure:**

| Location | Purpose | Owner |
|----------|---------|-------|
| `docs/` | Technical reference docs (Architecture, Pipeline, etc.) | Shared |
| `UCT-Benchmark-DMR/combined/docs/docs/` | Audit reports, issues backlog, team split analysis | Kelvin |
| `planning/` | Roadmaps, team plans, project status | Shared |
| `documentation/` | Provided PDFs and legacy docs (read-only) | N/A |

**Action Required:** Consolidate or clearly delineate documentation responsibilities.

---

## 11. Semester Timeline

### Inconsistency Found

All documents correctly state:
- Semester 1 (Fall 2025): Teams operated as one
- Semester 2 (Spring 2026): Teams splitting

**Current Date:** January 13, 2026 (Spring semester has begun)

**Status:** Consistent - no action needed.

---

## 12. T3/T4 Processing Status

### Consistency Check

| Document | Status |
|----------|--------|
| `TEAM_SPLIT_READINESS.md` | "T3/T4 processing incomplete" |
| `PROJECT_STATUS.md` | "T3/T4 Processing - Not Started - 5%" |
| `SDA_TAP_LAB_PLAN.md` | "Tier Processing - Not Started - 5%" |
| Code (`Create_Dataset.py:104-107`) | `logger.info("T3 processing not implemented")` |

**Status:** Consistent - T3/T4 processing is NOT STARTED with only placeholder logging.

---

## Summary of Required Actions

### HIGH Priority (Affects accuracy)

| # | Action | File(s) |
|---|--------|---------|
| 1 | Clarify Data Labelling vs Event Labelling distinction | `TEAM_SPLIT_READINESS.md` |
| 2 | Update repository structure diagram | `docs/README.md` |
| 3 | Update codebase location references | `docs/ARCHITECTURE.md`, `docs/README.md` |
| 4 | Align progress percentages | All planning docs |

### MEDIUM Priority (Improves clarity)

| # | Action | File(s) |
|---|--------|---------|
| 5 | Document technology stack options | `planning/SPOC_PLAN.md` |
| 6 | Distinguish metrics vs pipeline status | `TEAM_SPLIT_READINESS.md` |
| 7 | Clarify local storage vs centralized DB | Multiple docs |

### LOW Priority (Nice to have)

| # | Action | File(s) |
|---|--------|---------|
| 8 | Consolidate documentation locations | All |
| 9 | Add cross-references between docs | All |

---

## Authoritative Status Summary

**Use this as the single source of truth:**

| Component | Status | Completeness | Notes |
|-----------|--------|--------------|-------|
| API Integrations | Complete | 95% | Missing retry/cache |
| Window Selection | Complete | 90% | Edge cases pending |
| Dataset Categorization | Complete | 100% | Tier system working |
| Basic Scoring | Complete | 85% | Regime-specific tuning pending |
| Propagators | Complete | 95% | STM propagation pending |
| Evaluation Metrics | Complete | 90% | Radar metrics pending |
| Orbit Association | Complete | 95% | Alternative algorithms pending |
| Evaluation Pipeline | Partial | 75% | `main()` needs implementation |
| PDF Reports | Complete | 80% | Styling improvements pending |
| Observation Simulation | Partial | 60% | `epochsToSim()` incomplete |
| **Event Labelling** | **Not Started** | **0%** | Launch/maneuver/proximity detection |
| **Centralized Database** | **Not Started** | **0%** | Schema design needed |
| **T3/T4 Processing** | **Not Started** | **5%** | Only placeholder code |
| **Downsampling (T1/T2)** | **Not Started** | **0%** | Not implemented |
| **Web UI** | **Not Started** | **0%** | Framework not selected |
| **Algorithm Submission** | **Not Started** | **0%** | Format not finalized |
| **Leaderboard** | **Not Started** | **0%** | Ranking algorithm not designed |

**Overall Project Progress:** ~45% (Foundation complete, major features pending)

---

**Report Generated:** January 13, 2026
**Next Review:** After implementing HIGH priority actions
