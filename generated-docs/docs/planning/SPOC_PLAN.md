# SpOC Team Plan

<!-- AI_METADATA
purpose: Task planning and tracking for SpOC team
status: active
related_files: [planning/PROJECT_STATUS.md, planning/INTEGRATED_ROADMAP.md, planning/SDA_TAP_LAB_PLAN.md, planning/FUTURE_IMPLEMENTATIONS.md]
last_updated: 2026-02-03
-->

<!-- NEEDS_UPDATE: Web UI is now complete (90%). Many TODO items have been completed - check PROJECT_STATUS.md for current status -->

## Team Mission

**Benchmark Dataset Generation & Evaluation Criteria**: Generate standardized benchmark datasets from stored data, define and implement evaluation criteria for UCTP algorithms, develop the Web UI for algorithm developers, and create comparison/leaderboard systems.

---

## Current Team Responsibilities

1. **Benchmark Dataset Generation** - Create standardized datasets from SDA TAP Lab's stored data
2. **Evaluation Criteria Development** - Define and implement performance metrics
3. **Algorithm Interface** - Define input/output formats for UCTP algorithms
4. **Web UI Development** - Build the Common Task Framework web interface
5. **Reporting & Comparison** - Generate reports and maintain leaderboards

---

## Current Progress Summary

| Area | Status | Progress |
|------|--------|----------|
| Evaluation Metrics | ✅ Complete | 90% |
| Orbit Association | ✅ Complete | 95% |
| PDF Report Generation | ✅ Complete | 80% |
| Dummy UCTP | ✅ Complete | 100% |
| Evaluation Pipeline | ✅ Complete | 90% |
| Web UI | ✅ **Complete** | **90%** |
| Algorithm Submission | ✅ **Complete** | **90%** |
| Leaderboard | ✅ **Complete** | **90%** |
| Authentication System | ✅ **Complete** | **95%** |
| Documentation for Developers | In Progress | 60% |

---

## TODO List by Priority

<!-- AI_SECTION: priority1_evaluation -->

### PRIORITY 1: Complete Evaluation Pipeline

#### TODO 1.1: Fix Evaluation.py Entry Point
**Estimated Effort**: Low
**Dependencies**: None
**Files**: `Evaluation.py`

**Tasks**:
- [ ] Move evaluation logic into `main()` function properly
- [ ] Add command-line argument parsing
- [ ] Implement proper error handling
- [ ] Add progress indicators
- [ ] Create batch evaluation capability

**Current Issue** (`Evaluation.py:34-39`):
```python
def main():
    """Main function for evaluation."""
    # Empty - all code runs outside main()

if __name__ == "__main__":
    main()  # Does nothing, code below runs unconditionally
```

**Fix Required**:
```python
def main(dataset_path, uctp_output_path, report_path):
    """Main function for evaluation."""
    # Move all evaluation code here
    # Add proper argument handling
    # Return evaluation results
```

---

#### TODO 1.2: Add Radar Observation Support

<!-- AI_IMPROVEMENT_OPPORTUNITY: Radar metrics not fully implemented. See FUTURE_IMPLEMENTATIONS.md -->

**Estimated Effort**: Medium
**Dependencies**: None
**Files**: `residualMetrics.py`, `stateMetrics.py`

**Tasks**:
- [ ] Implement range residual calculation
- [ ] Implement range-rate residual calculation
- [ ] Add azimuth/elevation residuals
- [ ] Update metrics output to include radar metrics
- [ ] Test with radar observation datasets

---

#### TODO 1.3: Enhance Report Generation
**Estimated Effort**: Medium
**Dependencies**: None
**Files**: `generatePDF.py`

**Tasks**:
- [ ] Add executive summary section
- [ ] Create comparison charts
- [ ] Add historical trend plots (if available)
- [ ] Improve visual styling
- [ ] Add configurable report sections
- [ ] Export to HTML option

---

<!-- /AI_SECTION -->

<!-- AI_SECTION: priority2_web_ui -->

### ✅ PRIORITY 2: Web UI Development - COMPLETE

**Status**: ✅ Complete (90%) as of 2026-01-25

#### ✅ TODO 2.1: Frontend Framework Setup - COMPLETE
**Files**: `frontend/`

**Completed Tasks**:
- [x] Select frontend framework: **React 18+ with TypeScript**
- [x] Set up project structure with Vite
- [x] Create component library (45+ components)
- [x] Implement routing with React Router
- [x] Set up build pipeline with ESLint + Prettier

**Implemented Technology Stack**:
```
Frontend:
├── React 18+ ✓
├── TypeScript ✓
├── Tailwind CSS ✓
├── Zustand (state management) ✓
├── Recharts (visualizations) ✓
└── shadcn/ui (component library) ✓

Build:
├── Vite ✓
└── ESLint + Prettier ✓
```

---

#### ✅ TODO 2.2: Backend API Development - COMPLETE
**Files**: `backend_api/`

**Completed Tasks**:
- [x] Select backend framework: **FastAPI**
- [x] Design REST API endpoints
- [x] Implement authentication (JWT + Supabase)
- [x] Create dataset endpoints (`routers/datasets.py`)
- [x] Create submission endpoints (`routers/submissions.py`)
- [x] Create evaluation endpoints (`routers/results.py`)
- [x] Create jobs endpoints (`routers/jobs.py`)
- [x] Create leaderboard endpoints (`routers/leaderboard.py`)

**Implemented API Endpoints**:
```
/api/v1/
├── auth/ ✓
│   ├── POST /signup, /login, /logout
│   ├── GET /me
│   └── PUT /me
├── datasets/ ✓
│   ├── GET /, /{id}
│   ├── POST /generate
│   ├── DELETE /{id}
│   └── GET /{id}/download
├── submissions/ ✓
│   ├── GET /, /{id}
│   ├── POST /
│   └── GET /{id}/results
├── leaderboard/ ✓
│   ├── GET /
│   └── GET /history
└── jobs/ ✓
    └── GET /{id}/status
```

---

#### ✅ TODO 2.3-2.6: UI Components - COMPLETE

**All UI Components Implemented**:
- [x] Dataset Browser with filtering
- [x] Dataset Generator with preset configurations
- [x] Submission Interface with file upload
- [x] Results Viewer with metric displays
- [x] DataSourceStatusIndicator for data availability
- [x] Professional space-themed UI design

---

<!-- /AI_SECTION -->

<!-- AI_SECTION: priority3_submission -->

### ✅ PRIORITY 3: Algorithm Submission System - COMPLETE

**Status**: ✅ Complete (90%) as of 2026-01-25

#### ✅ TODO 3.1: Submission Format Specification - COMPLETE
**Completed Tasks**:
- [x] Define JSON schema for submissions (Pydantic models)
- [x] Document required fields
- [x] Validation logic implemented
- [x] Example submissions in tests

---

#### ✅ TODO 3.2: Submission Validation - COMPLETE
**Files**: `backend_api/models/`

**Completed Tasks**:
- [x] Pydantic model validation
- [x] Observation ID reference validation
- [x] State vector validation
- [x] Detailed error messages

---

#### ✅ TODO 3.3: Evaluation Queue System - COMPLETE
**Files**: `backend_api/jobs/`

**Completed Tasks**:
- [x] Background job processing
- [x] Job submission with status tracking
- [x] Worker processes with async handling
- [x] Timeout and failure handling
- [x] Results stored in DuckDB

---

<!-- /AI_SECTION -->

<!-- AI_SECTION: priority4_leaderboard -->

### ✅ PRIORITY 4: Leaderboard System - COMPLETE

**Status**: ✅ Complete (90%) as of 2026-01-25

#### ✅ TODO 4.1: Ranking Algorithm Design - COMPLETE
**Files**: `backend_api/routers/leaderboard.py`

**Implemented Ranking Scheme**:
```
Primary Sort: F1-Score (descending)
Tiebreaker 1: Position RMS (ascending)
Tiebreaker 2: Submission time (ascending)

Separate leaderboards per:
- Orbital regime (LEO, MEO, GEO) ✓
- Dataset tier (T1, T2, T3, T4) ✓
- Overall ✓
```

---

#### ✅ TODO 4.2: Leaderboard UI Component - COMPLETE
**Files**: `frontend/src/components/leaderboard/`

**Completed Tasks**:
- [x] Sortable table view
- [x] Filtering options
- [x] Metric breakdowns
- [x] User submission highlighting
- [x] Medal indicators (🥇🥈🥉)

---

#### ✅ TODO 4.3: Historical Tracking - COMPLETE
**Completed Tasks**:
- [x] Historical rankings stored in DuckDB
- [x] Algorithm improvement tracking
- [x] Comparison by dataset, algorithm, metrics

---

<!-- /AI_SECTION -->

<!-- AI_SECTION: priority5_documentation -->

### PRIORITY 5: Documentation for Algorithm Developers

#### TODO 5.1: Getting Started Guide
**Estimated Effort**: Medium
**Dependencies**: Submission format finalized
**Files**: `docs/developer_guide/`

**Tasks**:
- [ ] Explain Common Task Framework
- [ ] Describe UCT Processing problem
- [ ] Provide dataset format documentation
- [ ] Show submission format examples
- [ ] Include sample code

---

#### TODO 5.2: API Documentation
**Estimated Effort**: Medium
**Dependencies**: Backend API complete
**Files**: Auto-generated from code

**Tasks**:
- [ ] Set up OpenAPI/Swagger documentation
- [ ] Add endpoint descriptions
- [ ] Include request/response examples
- [ ] Document error codes

---

#### TODO 5.3: Evaluation Criteria Documentation
**Estimated Effort**: Low
**Dependencies**: None
**Files**: `docs/evaluation_criteria.md`

**Tasks**:
- [ ] Document all metrics
- [ ] Explain calculation methods
- [ ] Provide interpretation guidance
- [ ] Show example calculations

---

## Detailed Task Breakdown

### Immediate Next Steps (Next Sprint)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| Fix Evaluation.py entry point | TBD | P1 | 4 |
| Add CLI arguments to evaluation | TBD | P1 | 4 |
| Design submission format | TBD | P1 | 8 |
| Select frontend framework | TBD | P2 | 4 |
| Select backend framework | TBD | P2 | 4 |

### Short-term (1-2 Sprints)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| Set up frontend project | TBD | P2 | 16 |
| Set up backend project | TBD | P2 | 16 |
| Implement auth endpoints | TBD | P2 | 24 |
| Add radar metrics | TBD | P1 | 16 |
| Create dataset endpoints | TBD | P2 | 24 |

### Medium-term (3-4 Sprints)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| Dataset browser UI | TBD | P2 | 40 |
| Submission interface | TBD | P3 | 60 |
| Evaluation queue | TBD | P3 | 40 |
| Results viewer | TBD | P3 | 32 |
| Leaderboard | TBD | P4 | 40 |

---

## Handoff Requirements from SDA TAP Lab

| Requirement | Format | Status | Priority |
|-------------|--------|--------|----------|
| Observation data access | Database API | ✅ Complete | High |
| Event labels | Database table | Pending | Medium |
| Dataset metadata | JSON/Database | ✅ Complete | High |
| Data quality info | Scoring output | ✅ Complete | Low |
| Satellite catalog | Database table | ✅ Complete | Medium |
| Open source enrichment | DataSourceManager | ✅ Complete | Medium |
| UCTP Lab framework | Python module | ✅ Complete | Medium |

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Evaluation accuracy | >99% | ~95% |
| Web UI response time | <2s | N/A |
| Submission processing time | <5min | N/A |
| API uptime | >99.9% | N/A |
| User satisfaction | >4.5/5 | N/A |

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Database delays | High | Medium | Mock data for development |
| Evaluation scalability | High | Low | Cloud-based processing |
| Security vulnerabilities | High | Medium | Security audit, penetration testing |
| User adoption | Medium | Medium | Good documentation, easy onboarding |

---

## Critical: UCTP Validation

Before the evaluation pipeline can be considered production-ready, it must be validated with actual UCT processor output. Per tech lead Lewis:

> "We still need to verify that our pipeline works with actual UCT processor output."

**Key Contact for Validation**:
- **Patrick Ramsey** (Aerospace Corp) - Has expressed interest in helping validate our software
- Aerospace Corp runs a UCT processor in the lab
- Can help process our generated datasets to provide real UCTP output for testing

### Validation Workflow
1. Generate benchmark datasets using our pipeline
2. Send datasets to Patrick Ramsey / Aerospace Corp
3. Receive actual UCTP output
4. Run our evaluation pipeline on real results
5. Verify metrics are accurate and meaningful

---

## Integration with SDA TAP Lab

### Required Interfaces
1. **Database Query API**: To retrieve stored observations and labels
2. **Dataset Generation API**: To trigger new dataset creation
3. **Data Quality API**: To get scoring/tier information

### Shared Components
- Configuration files
- Data format specifications
- Error handling patterns
- Logging standards

### Communication Protocol
- Weekly sync meetings
- Shared documentation
- Git-based collaboration
- Issue tracking for cross-team items

<!-- /AI_SECTION -->
