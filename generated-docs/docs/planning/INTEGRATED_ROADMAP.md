# Integrated Project Roadmap

<!-- AI_METADATA
purpose: Project timeline and milestone tracking for UCT Benchmark
status: active
related_files: [planning/PROJECT_STATUS.md, planning/SDA_TAP_LAB_PLAN.md, planning/SPOC_PLAN.md, planning/FUTURE_IMPLEMENTATIONS.md]
last_updated: 2026-04-14
-->

## Project Vision

Deliver a fully functional Web-hosted Common Task Framework for UCT Processing that enables algorithm developers to:
1. Generate and download standardized benchmark datasets
2. Train their algorithms on the data
3. Submit results for objective evaluation
4. Compare performance on a public leaderboard

---

<!-- AI_SECTION: milestone_overview -->

## Milestone Overview

<!-- STATUS_UPDATED: 2026-04-14 - Phases 1-4 complete, Phase 5 at 75% -->

```
Phase 1: Foundation ✅ COMPLETE (90%)
├── API Integrations ✓
├── Window Selection ✓
├── Basic Scoring ✓
├── Evaluation Metrics ✓
└── Propagators ✓

Phase 2: Data Pipeline ✅ COMPLETE (80%)
├── T3 Processing ✓
├── T1/T2 Downsampling ✓
├── Database Setup ✓
├── Open Source Integration ✓
├── Event Labelling (Not Started)
└── T4 Processing (Not Started)

Phase 3: Web Platform ✅ COMPLETE (90%)
├── Backend API ✓
├── Frontend UI ✓
├── Authentication ✓
├── Dataset Management ✓
└── Data Source Status UI ✓

Phase 4: Algorithm Framework ✅ COMPLETE (90%)
├── Submission System ✓
├── Evaluation Queue ✓
├── Results Display ✓
├── Leaderboard ✓
└── UCTP Lab Framework ✓

Phase 5: Production (IN PROGRESS - 75%)
├── Security Hardening ✓
├── Performance Optimization
├── Documentation ← Current
└── Launch ✓ (Deployed to Railway)

Phase 6: Open Evolve Integration (Stretch Goal)
├── Evaluation Script Validation with Real UCTP
├── Open Evolve Architecture Design
├── LLM Integration
└── Iterative Optimization Testing
```

### Critical Validation Milestone

**Before proceeding to later phases**, the pipeline must be validated with actual UCT processor output. Per tech lead Lewis:

> "We still need to verify that our pipeline works with actual UCT processor output."

**Key Contact**: Patrick Ramsey (Aerospace Corp) has expressed interest in helping validate our software by running datasets through their UCT processor. This validation should occur as soon as the data generation pipeline is stable.

---

<!-- /AI_SECTION -->

## Detailed Phase Breakdown

<!-- AI_SECTION: phase1_foundation -->

### PHASE 1: Foundation (COMPLETE - 90%)

**Status**: Nearly complete with minor refinements needed

| Milestone | Owner | Status | Progress |
|-----------|-------|--------|----------|
| 1.1 API Integrations | SDA TAP | Complete | 95% |
| 1.2 Window Selection | SDA TAP | Complete | 90% |
| 1.3 Basic Scoring | SDA TAP | Complete | 85% |
| 1.4 Propagators | Shared | Complete | 95% |
| 1.5 Evaluation Metrics | SpOC | Complete | 90% |
| 1.6 Orbit Association | SpOC | Complete | 95% |
| 1.7 Report Generation | SpOC | Complete | 80% |

**Remaining Items**:
- [ ] Add error retry logic to API calls
- [ ] Improve edge case handling in window selection
- [ ] Add radar support to evaluation metrics
- [ ] Fix Evaluation.py entry point

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: phase2_pipeline -->

### PHASE 2: Data Pipeline (COMPLETE - 80%)

**Status**: Core pipeline complete, event labeling and T4 remaining

| Milestone | Owner | Status | Progress | Dependency |
|-----------|-------|--------|----------|------------|
| 2.1 Complete Observation Simulation | SDA TAP | ✅ Complete | 95% | None |
| 2.2 T3 Processing Integration | SDA TAP | ✅ Complete | 100% | 2.1 |
| 2.3 T4 Processing Implementation | SDA TAP | Not Started | 0% | 2.2 |
| 2.4 Downsampling (T1/T2) | SDA TAP | ✅ Complete | 100% | None |
| 2.5 Event Labelling Schema | SDA TAP | Not Started | 0% | SME Input |
| 2.6 Launch Event Detection | SDA TAP | Not Started | 0% | 2.5 |
| 2.7 Maneuver Event Detection | SDA TAP | Not Started | 0% | 2.5 |
| 2.8 Database Schema Design | SDA TAP | ✅ Complete | 100% | None |
| 2.9 Database Implementation | SDA TAP | ✅ Complete | 95% | 2.8 |
| 2.10 Data Ingestion Pipeline | SDA TAP | ✅ Complete | 90% | 2.9 |
| 2.11 Open Source Data Integration | Shared | ✅ Complete | 90% | None |

**Completed Items**:
- T3 processing with `epochsToSim()` time-bin approach
- T1/T2 downsampling with three-stage pipeline
- DuckDB database with 14+ tables
- Data ingestion from UDL, Space-Track, open sources
- GCAT, UCS, SatNOGS, ILRS (partial) integration

**Remaining Work**:
- Event labeling system (schema design, detection modules)
- T4 object simulation (stretch goal)

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: phase3_web -->

### PHASE 3: Web Platform (COMPLETE - 90%)

**Status**: Full web platform implemented with React frontend and FastAPI backend

| Milestone | Owner | Status | Progress | Dependency |
|-----------|-------|--------|----------|------------|
| 3.1 Frontend Framework Setup | SpOC | ✅ Complete | 100% | None |
| 3.2 Backend API Setup | SpOC | ✅ Complete | 100% | None |
| 3.3 Authentication System | SpOC | ✅ Complete | 95% | 3.2 |
| 3.4 Dataset API Endpoints | SpOC | ✅ Complete | 95% | 3.2, 2.9 |
| 3.5 Dataset Browser UI | SpOC | ✅ Complete | 90% | 3.1, 3.4 |
| 3.6 Dataset Generator UI | SpOC | ✅ Complete | 90% | 3.5 |
| 3.7 Data Source Status UI | SpOC | ✅ Complete | 85% | 3.1 |

**Implementation Details**:
- React 18+ with TypeScript, Vite build system
- 45+ React components in `frontend/src/`
- FastAPI backend with 9 routers (datasets, submissions, results, leaderboard, jobs, events, credentials, feedback, auth)
- Supabase authentication with anonymous fallback mode
- Professional space-themed UI design
- Zustand state management
- DataSourceStatusIndicator for open source data status

**Remaining Work**:
- Password reset email flow
- Enhanced filtering/search in dataset browser

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: phase4_algorithm -->

### PHASE 4: Algorithm Framework (COMPLETE - 90%)

**Status**: Full algorithm submission and evaluation pipeline implemented

| Milestone | Owner | Status | Progress | Dependency |
|-----------|-------|--------|----------|------------|
| 4.1 Submission Format Specification | SpOC | ✅ Complete | 100% | None |
| 4.2 Submission Validation | SpOC | ✅ Complete | 95% | 4.1 |
| 4.3 Submission UI Component | SpOC | ✅ Complete | 90% | 3.1, 4.2 |
| 4.4 Evaluation Queue System | SpOC | ✅ Complete | 90% | 4.2 |
| 4.5 Results Display UI | SpOC | ✅ Complete | 90% | 4.4 |
| 4.6 Leaderboard Backend | SpOC | ✅ Complete | 90% | 4.4 |
| 4.7 Leaderboard UI | SpOC | ✅ Complete | 90% | 4.6, 3.1 |
| 4.8 UCTP Lab Framework | Shared | ✅ Complete | 85% | None |

**Implementation Details**:
- REST API for submissions (`backend_api/routers/submissions.py`)
- Background job processing with status updates (`backend_api/jobs/`)
- Pydantic models for validation (`backend_api/models/`)
- Results stored in DuckDB with full history
- Leaderboard with ranking by F1-score, position RMS
- UCTP Lab for algorithm development and testing

**Remaining Work**:
- Real UCTP validation with Aerospace Corp
- Additional ranking metrics/tiebreakers

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: phase5_production -->

### PHASE 5: Production (IN PROGRESS - 75%)

**Status**: Deployed to production; documentation and optimization in progress

| Milestone | Owner | Status | Progress | Dependency |
|-----------|-------|--------|----------|------------|
| 5.1 Security Hardening | Shared | ✅ Complete | 90% | Phase 4 |
| 5.2 Performance Optimization | Shared | In Progress | 40% | Phase 4 |
| 5.3 User Documentation | Shared | ← Current | 70% | Phase 4 |
| 5.4 Deployment Setup | Shared | ✅ Complete | 95% | 5.1-5.3 |
| 5.5 Beta Testing | Shared | In Progress | 30% | 5.4 |
| 5.6 Public Launch | Shared | ✅ Deployed | 80% | 5.5 |

**Security Hardening (Completed)**:
- SQL injection fixes across backend
- Auth consolidation with Supabase
- IDOR vulnerability closures
- 22 pre-existing test failures resolved

**Current Focus**:
- Documentation synchronization (this update)
- Performance optimization
- Remaining beta testing with stakeholders

### Recent Accomplishments (Apr 2026)

| Accomplishment | Version | Details |
|----------------|---------|---------|
| **Production Deployment** | v2.0.0+ | Railway hosting with Docker + NGINX reverse proxy |
| **Major Rebrand** | v2.0.0 | USSF dark theme, Supabase auth, full UI overhaul |
| **Vision Alignment** | v2.0.1 | Pipeline aligned to Louis's transcript specs |
| **UCT Challenges** | v2.0.0 | 5 CTF-style challenges (physical noise, sensor calibration, train/test split, etc.) |
| **Answer-Key Separation** | v2.0.1 | Download whitelist per Louis's Apr 9 feedback |
| **HEO Scoring Fix** | v2.0.1 | HEO coverage scoring + regime combo pipeline corrections |
| **Security Hardening** | v2.0.1 | SQL injection fixes, auth consolidation, IDOR closures |
| **Test Stability** | v2.0.1 | 22 pre-existing test failures resolved |
| **Regime Combos** | v2.0.1 | All 10 regime combo codes in frontend UI and validator |
| **Backend Expansion** | v2.0.0+ | 9 routers (added events, credentials, feedback, auth) |

<!-- /AI_SECTION -->

---

## Sprint Planning

### ✅ Completed Sprints (1-6)

The following sprints have been completed:
- **Sprint 1-2**: T3 processing, downsampling, database schema - ✅ Complete
- **Sprint 3-4**: Database implementation, authentication, dataset APIs - ✅ Complete
- **Sprint 5-6**: Submission system, evaluation queue, results display - ✅ Complete

---

### Sprint 7 (Current)
**Focus**: Production readiness, Documentation sync

| Task | Owner | Priority | Status |
|------|-------|----------|--------|
| Documentation synchronization | Shared | P1 | In Progress |
| ILRS validation module | SDA TAP | P1 | Not Started |
| Event labelling schema design | SDA TAP | P2 | Not Started |
| Security audit | Shared | P2 | In Progress |
| Performance testing baseline | Shared | P2 | Not Started |

---

### Sprint 8
**Focus**: Event labeling, Production hardening

| Task | Owner | Priority |
|------|-------|----------|
| Implement event labelling schema | SDA TAP | P1 |
| Launch event detection | SDA TAP | P2 |
| Complete ILRS Earthdata integration | Shared | P2 |
| Enhanced report generation | SpOC | P2 |
| Beta testing preparation | Shared | P2 |

---

### Sprint 9-10
**Focus**: Beta testing, Launch preparation

| Task | Owner | Priority |
|------|-------|----------|
| Maneuver event detection | SDA TAP | P2 |
| Real UCTP validation (Aerospace Corp) | Shared | P1 |
| Beta testing with users | Shared | P1 |
| Public launch preparation | Shared | P1 |

---

## Timeline Visualization

```
Sprint:     1    2    3    4    5    6    7    8    9    10
           ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
                                          ↑
                                       Current

SDA TAP:
  T3 Proc   ████ ✓
  T4 Proc                                      ████████
  Downsamp  ████ ✓
  Labelling                              ████████████
  Database       ████████ ✓
  OpenSource          ████████ ✓

SpOC:
  Eval Fix  ████ ✓
  Frontend  ████████████████ ✓
  Backend        ████████████████████ ✓
  Submit                   ████████ ✓
  Leader                        ████████ ✓
  Auth               ████████ ✓

Shared:
  UCTP Lab            ████████████ ✓
  Security                           ████████
  Docs                               ████████ ← Current
  Launch                                  ████████

```

---

## Key Dependencies and Handoffs

### SDA TAP → SpOC Handoffs

| Deliverable | Required By | Phase |
|-------------|-------------|-------|
| Complete T3/T4 processing | Sprint 4 | 2 |
| Database API access | Sprint 4 | 3 |
| Event labelling data | Sprint 5 | 4 |
| Full data ingestion | Sprint 6 | 4 |

### SpOC → SDA TAP Requirements

| Requirement | Needed By | Phase |
|-------------|-----------|-------|
| Evaluation format spec | Sprint 1 | 2 |
| API query requirements | Sprint 3 | 2 |
| Performance requirements | Sprint 4 | 3 |

---

## Risk Mitigation Schedule

| Risk | Mitigation | When |
|------|------------|------|
| Database delays | SpOC develops with mock data | Sprint 2-3 |
| SME unavailability | Document assumptions | Sprint 1-2 |
| Integration issues | Weekly sync meetings | Ongoing |
| Performance problems | Early load testing | Sprint 5 |

---

## Success Criteria by Phase

### Phase 1 Exit Criteria ✅
- [x] All APIs returning valid data
- [x] Window selection finding valid windows
- [x] Evaluation producing accurate metrics
- [x] Core error handling complete

### Phase 2 Exit Criteria (80% Complete)
- [x] T1-T3 processing functional
- [ ] T4 processing functional (stretch goal)
- [ ] Event labelling operational
- [x] Database storing all required data
- [x] Data ingestion automated
- [x] Open source data integration working

### Phase 3 Exit Criteria ✅
- [x] Users can browse datasets
- [x] Users can generate new datasets
- [x] Authentication working
- [x] All CRUD operations functional
- [x] Data source status displayed

### Phase 4 Exit Criteria ✅
- [x] Users can submit results
- [x] Automatic evaluation working
- [x] Leaderboard updating correctly
- [x] Results displayed accurately
- [x] UCTP Lab framework functional

### Phase 5 Exit Criteria (75% Complete)
- [x] Security hardening passed (SQL injection, auth consolidation, IDOR closures)
- [ ] Performance targets met (optimization in progress)
- [ ] Documentation complete ← In progress
- [x] System deployed and accessible (Railway production)

---

## Resource Allocation Recommendation

### SDA TAP Lab Team
| Role | Count | Focus |
|------|-------|-------|
| Backend Developer | 2 | Database, APIs |
| Data Engineer | 1 | Ingestion, ETL |
| Astrodynamics SME | 1 | Simulation, Labelling |

### SpOC Team
| Role | Count | Focus |
|------|-------|-------|
| Frontend Developer | 2 | React UI |
| Backend Developer | 1 | FastAPI |
| DevOps Engineer | 1 | Infrastructure |
