# Integrated Project Roadmap

## Project Vision

Deliver a fully functional Web-hosted Common Task Framework for UCT Processing that enables algorithm developers to:
1. Generate and download standardized benchmark datasets
2. Train their algorithms on the data
3. Submit results for objective evaluation
4. Compare performance on a public leaderboard

---

## Milestone Overview

```
Phase 1: Foundation (Current)
├── API Integrations ✓
├── Window Selection ✓
├── Basic Scoring ✓
├── Evaluation Metrics ✓
└── Propagators ✓

Phase 2: Data Pipeline (In Progress)
├── T3/T4 Processing
├── Event Labelling
├── Downsampling
└── Database Setup

Phase 3: Web Platform
├── Backend API
├── Frontend UI
├── Authentication
└── Dataset Management

Phase 4: Algorithm Framework
├── Submission System
├── Evaluation Queue
├── Results Display
└── Leaderboard

Phase 5: Production
├── Security Hardening
├── Performance Optimization
├── Documentation
└── Launch

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

## Detailed Phase Breakdown

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

---

### PHASE 2: Data Pipeline (IN PROGRESS - 25%)

**Status**: Core infrastructure done, major features pending

| Milestone | Owner | Status | Progress | Dependency |
|-----------|-------|--------|----------|------------|
| 2.1 Complete Observation Simulation | SDA TAP | Partial | 60% | None |
| 2.2 T3 Processing Integration | SDA TAP | Not Started | 5% | 2.1 |
| 2.3 T4 Processing Implementation | SDA TAP | Not Started | 0% | 2.2 |
| 2.4 Downsampling (T1/T2) | SDA TAP | Not Started | 0% | None |
| 2.5 Event Labelling Schema | SDA TAP | Not Started | 0% | SME Input |
| 2.6 Launch Event Detection | SDA TAP | Not Started | 0% | 2.5 |
| 2.7 Maneuver Event Detection | SDA TAP | Not Started | 0% | 2.5 |
| 2.8 Database Schema Design | SDA TAP | Not Started | 0% | 2.5 |
| 2.9 Database Implementation | SDA TAP | Not Started | 0% | 2.8 |
| 2.10 Data Ingestion Pipeline | SDA TAP | Not Started | 0% | 2.9 |

**Critical Path**: 2.1 → 2.2 → 2.3 → 2.10 (must be sequential)

**Parallel Work Possible**:
- 2.4 (Downsampling) can proceed independently
- 2.5-2.7 (Event Labelling) can proceed independently
- 2.8-2.9 (Database) can proceed in parallel with 2.1-2.3

---

### PHASE 3: Web Platform (NOT STARTED - 0%)

**Status**: Waiting for Phase 2 database completion

| Milestone | Owner | Status | Progress | Dependency |
|-----------|-------|--------|----------|------------|
| 3.1 Frontend Framework Setup | SpOC | Not Started | 0% | None |
| 3.2 Backend API Setup | SpOC | Not Started | 0% | None |
| 3.3 Authentication System | SpOC | Not Started | 0% | 3.2 |
| 3.4 Dataset API Endpoints | SpOC | Not Started | 0% | 3.2, 2.9 |
| 3.5 Dataset Browser UI | SpOC | Not Started | 0% | 3.1, 3.4 |
| 3.6 Dataset Generator UI | SpOC | Not Started | 0% | 3.5 |

**Can Start Now**:
- 3.1 Frontend Framework Setup
- 3.2 Backend API Setup (with mock data)

**Blocked Until Database Ready**:
- 3.4 Dataset API Endpoints
- 3.5 Dataset Browser UI

---

### PHASE 4: Algorithm Framework (NOT STARTED - 0%)

**Status**: Waiting for Phase 3 web platform

| Milestone | Owner | Status | Progress | Dependency |
|-----------|-------|--------|----------|------------|
| 4.1 Submission Format Specification | SpOC | Not Started | 0% | None |
| 4.2 Submission Validation | SpOC | Not Started | 0% | 4.1 |
| 4.3 Submission UI Component | SpOC | Not Started | 0% | 3.1, 4.2 |
| 4.4 Evaluation Queue System | SpOC | Not Started | 0% | 4.2 |
| 4.5 Results Display UI | SpOC | Not Started | 0% | 4.4 |
| 4.6 Leaderboard Backend | SpOC | Not Started | 0% | 4.4 |
| 4.7 Leaderboard UI | SpOC | Not Started | 0% | 4.6, 3.1 |

**Can Start Now**:
- 4.1 Submission Format Specification

---

### PHASE 5: Production (NOT STARTED - 0%)

**Status**: Future phase

| Milestone | Owner | Status | Progress | Dependency |
|-----------|-------|--------|----------|------------|
| 5.1 Security Audit | Shared | Not Started | 0% | Phase 4 |
| 5.2 Performance Testing | Shared | Not Started | 0% | Phase 4 |
| 5.3 User Documentation | Shared | Not Started | 0% | Phase 4 |
| 5.4 Deployment Setup | Shared | Not Started | 0% | 5.1-5.3 |
| 5.5 Beta Testing | Shared | Not Started | 0% | 5.4 |
| 5.6 Public Launch | Shared | Not Started | 0% | 5.5 |

---

## Sprint Planning

### Sprint 1 (Current)
**Focus**: Complete Phase 1 remnants, Start Phase 2 critical path

| Task | Owner | Priority |
|------|-------|----------|
| Complete `epochsToSim()` | SDA TAP | P1 |
| Fix Evaluation.py entry point | SpOC | P1 |
| Integrate T3 simulation | SDA TAP | P1 |
| Define submission format | SpOC | P1 |
| Design event labelling schema | SDA TAP | P2 |
| Set up frontend framework | SpOC | P2 |

---

### Sprint 2
**Focus**: T3/T4 processing, Begin database work

| Task | Owner | Priority |
|------|-------|----------|
| Complete T3 processing | SDA TAP | P1 |
| Begin T4 implementation | SDA TAP | P1 |
| Implement downsampling | SDA TAP | P1 |
| Set up backend framework | SpOC | P2 |
| Design database schema | SDA TAP | P2 |
| Add radar metrics | SpOC | P2 |

---

### Sprint 3
**Focus**: Event labelling, Database implementation

| Task | Owner | Priority |
|------|-------|----------|
| Complete T4 processing | SDA TAP | P1 |
| Implement launch detection | SDA TAP | P2 |
| Begin database implementation | SDA TAP | P2 |
| Implement auth endpoints | SpOC | P2 |
| Create dataset API (mock) | SpOC | P2 |

---

### Sprint 4
**Focus**: Database completion, Begin Web UI

| Task | Owner | Priority |
|------|-------|----------|
| Complete database implementation | SDA TAP | P1 |
| Implement maneuver detection | SDA TAP | P2 |
| Create data ingestion pipeline | SDA TAP | P2 |
| Dataset browser UI | SpOC | P2 |
| Dataset API (real data) | SpOC | P2 |

---

### Sprint 5-6
**Focus**: Submission system, Evaluation integration

| Task | Owner | Priority |
|------|-------|----------|
| Complete event labelling | SDA TAP | P2 |
| Submission UI component | SpOC | P1 |
| Evaluation queue | SpOC | P1 |
| Results display | SpOC | P1 |

---

### Sprint 7-8
**Focus**: Leaderboard, Polish

| Task | Owner | Priority |
|------|-------|----------|
| Leaderboard backend | SpOC | P1 |
| Leaderboard UI | SpOC | P1 |
| Security audit | Shared | P1 |
| Documentation | Shared | P1 |

---

## Timeline Visualization

```
Sprint:     1    2    3    4    5    6    7    8
           ├────┼────┼────┼────┼────┼────┼────┼────┤

SDA TAP:
  T3 Proc   ████
  T4 Proc        ████████
  Downsamp       ████
  Labelling           ████████████
  Database            ████████████

SpOC:
  Eval Fix  ████
  Frontend  ████████████████
  Backend        ████████████████████
  Submit                   ████████████
  Leader                        ████████████

Shared:
  Security                           ████████
  Docs                               ████████
  Launch                                  ████

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

### Phase 1 Exit Criteria
- [x] All APIs returning valid data
- [x] Window selection finding valid windows
- [x] Evaluation producing accurate metrics
- [ ] All error handling complete

### Phase 2 Exit Criteria
- [ ] T1-T4 processing all functional
- [ ] Event labelling operational
- [ ] Database storing all required data
- [ ] Data ingestion automated

### Phase 3 Exit Criteria
- [ ] Users can browse datasets
- [ ] Users can generate new datasets
- [ ] Authentication working
- [ ] All CRUD operations functional

### Phase 4 Exit Criteria
- [ ] Users can submit results
- [ ] Automatic evaluation working
- [ ] Leaderboard updating correctly
- [ ] Results displayed accurately

### Phase 5 Exit Criteria
- [ ] Security audit passed
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] System deployed and accessible

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
