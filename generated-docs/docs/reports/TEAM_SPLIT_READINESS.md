# Team Split Readiness Report

**Date:** January 13, 2026
**Purpose:** Identify tasks that must be completed before SDA TAP Lab and SpOC teams can work independently

---

## Executive Summary

Based on comprehensive analysis of the official project briefs, LLNL paper, and current codebase, the teams are **NOT YET READY** to split. Several critical shared infrastructure components must be completed first.

**Estimated Readiness:** 60% complete for team split

---

## 1. Official Team Responsibilities

### SDA TAP Lab Team
**Focus:** Labelling & Data Storage

| Responsibility | Description |
|----------------|-------------|
| Pull event data | From UDL and other online sources |
| Label data | According to predefined classifications (launch, maneuver, proximity events) |
| Parse/Extract | Relevant measurement data based on classification |
| Clean & Store | Labelled data in centrally available database |

### SpOC Team
**Focus:** Benchmark Dataset Generation & Evaluation Criteria

| Responsibility | Description |
|----------------|-------------|
| Generate benchmark datasets | From stored/labelled data |
| Define evaluation criteria | Metrics for algorithm performance |
| Build Web UI | For algorithm developers to access benchmarks |
| Evaluation system | Compare and rank submitted algorithms |

---

## 2. Current Implementation Status

### Phase-by-Phase Analysis

| Component | Owner | Status | Completeness | Blocking Issues |
|-----------|-------|--------|--------------|-----------------|
| **API Integration** | Shared | COMPLETE | 95% | Minor: retry/cache logic |
| **Dataset Categorization** | SDA TAP Lab | COMPLETE | 100% | None (tier system working) |
| **Event Labelling** | SDA TAP Lab | NOT STARTED | 0% | Launch/maneuver detection needed |
| **Local File Storage** | SDA TAP Lab | COMPLETE | 100% | Working (Parquet/JSON) |
| **Centralized Database** | SDA TAP Lab | NOT STARTED | 0% | **CRITICAL BLOCKER** |
| **Dataset Creation** | Shared | OPERATIONAL | 85% | T3/T4 processing incomplete |
| **UCTP Algorithm** | N/A* | STUB | 5% | Only dummy implementation |
| **Evaluation Metrics** | SpOC | COMPLETE | 90% | Minor integration issues |
| **Web UI** | SpOC | NOT STARTED | 0% | **CRITICAL BLOCKER** |

**Important Terminology Clarification:**
- **Dataset Categorization** = Tier system (T1-T5), orbital regime classification, sensor type classification - **COMPLETE**
- **Event Labelling** = Classifying observations by event type (launch, maneuver, proximity, breakup) - **NOT STARTED**

*Note: The UCTP algorithm itself is what external developers will submit - it's the "prediction task" in the Common Task Framework. The current dummy implementation is only for testing the evaluation pipeline.

---

## 3. Shared Infrastructure Requirements

### 3.1 CRITICAL: Must Complete Before Split

#### A. Centralized Data Storage (SDA TAP Lab responsibility)
**Current State:** Local file storage (Parquet/JSON files)
**Required:** Centralized database accessible by both teams

```
Current: Local files → Manual handoff → SpOC processes
Needed:  SDA TAP Lab → Central DB API → SpOC consumes
```

**Tasks:**
- [ ] Design database schema for labeled datasets
- [ ] Implement database (PostgreSQL, MongoDB, or cloud solution)
- [ ] Create API endpoints for data access
- [ ] Document data schema for SpOC team

#### B. Dataset Output Format Specification (Joint responsibility)
**Current State:** JSON output with informal schema
**Required:** Formal specification that both teams agree on

**Tasks:**
- [ ] Define formal JSON schema for benchmark datasets
- [ ] Define training/validation/testing split ratios (80/10/10 or 60/20/20 per LLNL paper)
- [ ] Document dataset code encoding system
- [ ] Create validation tooling for dataset format

#### C. API Contract Between Teams (Joint responsibility)
**Current State:** No defined interface
**Required:** Clear API contract for data exchange

**Tasks:**
- [ ] Define REST API endpoints for dataset retrieval
- [ ] Define submission format for algorithm results
- [ ] Implement authentication/authorization
- [ ] Create API documentation

---

## 4. Tasks for Each Team to Work Independently

### 4.1 SDA TAP Lab Must Complete

| Priority | Task | Current Status | Blocks SpOC? |
|----------|------|----------------|--------------|
| **HIGH** | Implement centralized database | Not started | YES |
| **HIGH** | Create data access API | Not started | YES |
| **MEDIUM** | Complete T3/T4 tier processing | Logged only | No |
| **MEDIUM** | Automated labeling refinement workflow | Not implemented | No |
| **LOW** | SME review interface for label validation | Not implemented | No |

**Deliverable for SpOC:** API that returns labeled, cleaned datasets ready for benchmark generation

### 4.2 SpOC Must Complete

| Priority | Task | Current Status | Blocks SDA TAP Lab? |
|----------|------|----------------|---------------------|
| **HIGH** | Web UI frontend (NextJS per LLNL) | Not started | No |
| **HIGH** | API backend (ExpressJS per LLNL) | Not started | No |
| **HIGH** | Leaderboard/ranking system | Not started | No |
| **MEDIUM** | Dataset download functionality | Not started | No |
| **MEDIUM** | Result submission system | Not started | No |
| **LOW** | User authentication | Not started | No |

**Deliverable:** Web-hosted platform where algorithm developers can:
1. Download benchmark datasets
2. Submit algorithm results
3. View evaluation scores and leaderboard

---

## 5. Dependency Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SHARED INFRASTRUCTURE                             │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ Dataset Schema  │  │  API Contract    │  │ Evaluation Metrics │  │
│  └────────┬────────┘  └────────┬─────────┘  └─────────┬──────────┘  │
│           │                    │                      │              │
└───────────┼────────────────────┼──────────────────────┼──────────────┘
            │                    │                      │
            ▼                    ▼                      ▼
┌───────────────────────┐      │        ┌──────────────────────────────┐
│    SDA TAP Lab        │      │        │         SpOC                 │
│                       │      │        │                              │
│ ┌───────────────────┐ │      │        │ ┌──────────────────────────┐ │
│ │ UDL Data Pulling  │ │ COMPLETE      │ │ Web UI (NextJS)          │ │
│ └─────────┬─────────┘ │      │        │ │ - NOT STARTED            │ │
│           ▼           │      │        │ └──────────────────────────┘ │
│ ┌───────────────────┐ │      │        │                              │
│ │ Event Labelling   │ │ COMPLETE      │ ┌──────────────────────────┐ │
│ └─────────┬─────────┘ │      │        │ │ API Backend (ExpressJS)  │ │
│           ▼           │      │        │ │ - NOT STARTED            │ │
│ ┌───────────────────┐ │      │        │ └──────────────────────────┘ │
│ │ Parse/Extract     │ │ 85%           │                              │
│ └─────────┬─────────┘ │      │        │ ┌──────────────────────────┐ │
│           ▼           │      │        │ │ Dataset Generation       │ │
│ ┌───────────────────┐ │ ─────┼─────►  │ │ - Needs data from SDA    │ │
│ │ Central Database  │ │ BLOCKER       │ └──────────────────────────┘ │
│ │ - NOT STARTED     │ │      │        │                              │
│ └───────────────────┘ │      │        │ ┌──────────────────────────┐ │
│                       │      │        │ │ Evaluation Engine        │ │
└───────────────────────┘      │        │ │ - COMPLETE (90%)         │ │
                               │        │ └──────────────────────────┘ │
                               │        │                              │
                               │        │ ┌──────────────────────────┐ │
                               │        │ │ Leaderboard System       │ │
                               │        │ │ - NOT STARTED            │ │
                               │        └──────────────────────────────┘
```

---

## 6. Recommended Action Plan

### Phase 1: Shared Infrastructure (Both Teams - 2-3 sprints)

1. **Define dataset schema** - Joint meeting to formalize JSON structure
2. **Define API contract** - Agree on endpoints, authentication, data formats
3. **Agree on evaluation metrics** - Finalize which metrics will be used for ranking

### Phase 2: Parallel Development (Teams work independently)

**SDA TAP Lab:**
1. Implement centralized database
2. Build data access API
3. Complete T3/T4 processing
4. Add SME review workflow

**SpOC:**
1. Build Web UI frontend
2. Implement API backend
3. Create leaderboard system
4. Build dataset download functionality

### Phase 3: Integration (Both Teams - 1-2 sprints)

1. Connect SpOC frontend to SDA TAP Lab data API
2. End-to-end testing
3. Deploy to cloud environment

---

## 7. Codebase Consolidation Needed

Before splitting, the teams should consolidate the three existing branches:

| Branch | Keep | Reason |
|--------|------|--------|
| `master` | Reference only | Legacy, superseded by refactor |
| `jovan-linuxTesting` | Merge features | DuckDB, Polars, setup automation |
| `uct-benchmark-refactor-joncline` | **PRIMARY** | Best architecture, Solara UI |

**Recommended:** Use `UCT-Benchmark-DMR/combined` as the unified codebase, which is based on the refactored version.

---

## 8. Key Questions to Resolve with Mentors

1. **Database choice:** PostgreSQL, MongoDB, or cloud solution (AWS/GCP)?
2. **Hosting:** Where will the Web UI be deployed? SDA TAP Lab cloud?
3. **Authentication:** How will algorithm developers authenticate?
4. **Data access:** Will SpOC team have direct UDL access or go through SDA TAP Lab?
5. **Timeline:** What is the deadline for the Web UI to be operational?

---

## 9. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| No centralized database | HIGH | HIGH | Prioritize database implementation |
| Web UI not started | HIGH | HIGH | Begin NextJS/ExpressJS development immediately |
| Teams work on incompatible data formats | MEDIUM | MEDIUM | Define schema before splitting |
| Evaluation metrics change after split | LOW | LOW | Finalize metrics in shared infrastructure phase |

---

## 10. Summary Checklist

### Before Teams Can Split:

- [ ] **Database schema defined and documented**
- [ ] **Centralized database implemented** (or clear plan with timeline)
- [ ] **API contract defined** between SDA TAP Lab and SpOC
- [ ] **Dataset output format** formalized
- [ ] **Evaluation metrics** finalized
- [ ] **Code consolidated** into single branch
- [ ] **Package naming** standardized (`uct_benchmark`)

### After Split - SDA TAP Lab Owns:
- [ ] UDL data pulling
- [ ] Event labelling system
- [ ] Data parsing and extraction
- [ ] Centralized database
- [ ] Data access API

### After Split - SpOC Owns:
- [ ] Web UI (frontend)
- [ ] API backend
- [ ] Benchmark dataset generation
- [ ] Evaluation engine
- [ ] Leaderboard and ranking

---

**Report Generated:** January 13, 2026
**Next Review:** Recommend reviewing after shared infrastructure tasks are complete
