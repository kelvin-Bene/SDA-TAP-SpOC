# Future Implementations

<!-- AI_METADATA
purpose: Single authoritative source for all planned future work
status: active
related_files: [planning/PROJECT_STATUS.md, planning/INTEGRATED_ROADMAP.md, planning/DECISION_LOG.md, technical/DATA_SOURCE_RATIONALE.md]
last_updated: 2026-02-03
-->

This document consolidates all planned future work for the UCT Benchmark project. It serves as the authoritative source for what needs to be implemented, integrated, or enhanced.

---

## Implementation Status Legend

| Status | Meaning |
|--------|---------|
| **Not Started** | No work begun (0%) |
| **Planned** | Designed but not implemented |
| **In Progress** | Actively being worked on |
| **Blocked** | Waiting on dependency |
| **Complete** | Fully implemented |

---

<!-- AI_SECTION: high_priority_features -->

## 1. High Priority Features

### 1.1 Event Labeling System

**Status**: Not Started (0%)
**Owner**: SDA TAP Lab
**Priority**: High

The event labeling system will classify observation data by event type for more realistic benchmark datasets.

**Required Components**:

| Component | Description | Status |
|-----------|-------------|--------|
| Event Schema | Define `EventType` enum (launch, maneuver, proximity, breakup, reentry) | Not Started |
| Launch Detection | Query/detect new objects appearing | Not Started |
| Maneuver Detection | Detect orbital element changes between TLEs | Not Started |
| Proximity Detection | Identify close approach events | Not Started |
| Breakup Detection | Detect fragmentation events | Not Started |
| Label Storage | Database schema for event labels | Not Started |
| SME Review Interface | UI for expert validation of labels | Not Started |

**Implementation Location**: `uct_benchmark/labelling/`

**Proposed Schema**:
```python
class EventType(Enum):
    LAUNCH = "launch"           # New object appearing
    MANEUVER = "maneuver"       # Orbital change
    PROXIMITY = "proximity"     # Close approach
    BREAKUP = "breakup"         # Object fragmentation
    REENTRY = "reentry"         # Atmospheric reentry
    UNKNOWN = "unknown"         # Unclassified
```

<!-- AI_IMPROVEMENT_OPPORTUNITY: Event labeling is a major feature gap. Implementation should start with schema design and SME consultation. -->

---

### 1.2 T4 Object Simulation

**Status**: Not Started (0%)
**Owner**: SDA TAP Lab
**Priority**: Medium-High

T4 processing generates entirely synthetic satellites when real data is insufficient.

**Required Components**:

| Component | Description | Status |
|-----------|-------------|--------|
| Object Generator | Generate realistic orbital elements | Not Started |
| TLE Generator | Create TLEs for synthetic objects | Not Started |
| Observation Generator | Use existing `simulateObs()` for synthetic objects | Available |
| Integration | Connect to main pipeline (`Create_Dataset.py`) | Not Started |

**Conceptual Approach**:
1. Determine how many additional objects needed
2. Generate realistic orbital elements for synthetic objects
3. Create TLEs for these objects
4. Simulate observations using existing `simulateObs()`
5. Add synthetic objects to dataset with proper labeling

**Implementation Location**: New file `uct_benchmark/simulation/simulateObjects.py`

<!-- AI_IMPROVEMENT_OPPORTUNITY: T4 is lower priority since T1-T3 cover most real-world scenarios, but completing this would enable fully synthetic benchmarks. -->

---

### 1.3 ILRS Validation Integration

**Status**: Partial (40%)
**Owner**: Shared
**Priority**: High

ILRS (International Laser Ranging Service) data provides sub-centimeter precision for validating state vector accuracy.

**Benefits**:
- Highest precision tracking data available
- Independent validation source for state vectors
- Ground-truth for orbit accuracy assessment
- Covariance calibration reference

**Implemented Components**:

| Component | Description | Status |
|-----------|-------------|--------|
| ILRS Satellite List | `ilrsGetSatellites()` returns ~100 tracked satellites | ✅ Complete |
| ILRS Station List | `ilrsGetStations()` returns ~40 stations | ✅ Complete |
| Satellite Detection | `DataSourceManager.is_ilrs_satellite()` identifies ILRS targets | ✅ Complete |
| ILRS Query Function | `ilrsQueryPredictions()` for predictions | ⚠️ Requires Earthdata Auth |
| Validation Module | Compare against ILRS ground truth | Not Started |
| Propagator Validation | Use ILRS for propagator accuracy testing | Not Started |

**Data Source**: NASA CDDIS archive (https://cddis.nasa.gov/)

**Implementation Notes**:
- Satellite list is currently hardcoded based on known ILRS-tracked objects
- Full prediction/range measurement API requires NASA Earthdata credentials (free registration)
- Current implementation identifies ILRS satellites in datasets for validation eligibility

**Decision Required**: Which satellites to focus on (LEO, GNSS, or Geodetic) - see [DECISION_LOG.md](DECISION_LOG.md#decision-2-ilrs-precision-validation-focus)

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: data_source_integrations -->

## 2. Data Source Integrations

### 2.1 Phase 1: Quick Wins - ✅ COMPLETE

All quick-win data sources have been fully implemented.

| Source | Data Provided | Status | Implementation |
|--------|--------------|--------|----------------|
| **GCAT** | Comprehensive catalog (57K+ objects), launch/reentry history | ✅ Complete | `open_sources.py:225-390` |
| **UCS Database** | Satellite metadata (mass, power, purpose, operator) | ✅ Complete | `open_sources.py:497-674` |
| **SatNOGS** | Real RF observations, 200+ ground stations | ✅ Complete | `open_sources.py:40-223` |
| **ILRS** | Sub-cm precision laser ranging | ⚠️ Partial | `open_sources.py:676-708` |

**GCAT Integration** (Complete):
- Full satellite catalog query with `gcatQuery()`
- Individual lookup with `gcatLookupByNorad()`
- Launch history with `gcatGetLaunches()`
- Reentry catalog with `gcatGetReentries()`
- 24-hour TTL caching for catalog data

**UCS Database Integration** (Complete):
- Full database query with `ucsQuery()` (7,500+ operational satellites)
- Individual lookup with `ucsLookupByNorad()`
- Country filtering with `ucsGetByCountry()`
- Purpose filtering with `ucsGetByPurpose()`
- Satellite enrichment with mass data for HAMR detection

**SatNOGS Integration** (Complete):
- RF observation query with `satnogsQuery()`
- Satellite database with `satnogsGetSatellites()`
- Ground station info with `satnogsGetStations()`
- Transmitter data with `satnogsGetTransmitters()`
- Paginated API support (250 results/page)

**ILRS Integration** (Partial):
- Satellite list works via `ilrsGetSatellites()` (~100 satellites)
- Station list works via `ilrsGetStations()` (~40 stations)
- ⚠️ Prediction queries (`ilrsQueryPredictions()`) require NASA Earthdata authentication
- Satellite list is currently hardcoded based on known ILRS-tracked objects

---

### 2.2 Remaining Data Source Work

| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| ILRS validation module | Not Started | High | Full prediction/measurement API needs NASA Earthdata auth |
| ccsds-ndm library | Not Started | Medium | Standard CDM/ODM/OMM parsing for CDMs |
| TraCSS evaluation | Not Started | Low | Now in production (Jan 2026), needs API review |

---

### 2.3 Future Consideration (Registration Required)

These sources were deprioritized per [Decision 1](DECISION_LOG.md#decision-1-external-data-provider-registration) but may be revisited.

| Source | Data Provided | Registration | Status |
|--------|--------------|--------------|--------|
| Vimpel | Russian catalog, GEO/HEO debris | Required + citation | Deferred |
| EU SST | European collision avoidance | Operator registration | Deferred |
| TraCSS | Next-gen US space traffic | Production (Jan 2026) | Evaluate |

**Rationale for Deferral**: Starting with fully open sources aligns with open-source project philosophy and ensures all data can be freely redistributed.

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: web_platform_enhancements -->

## 3. Web Platform Enhancements

### 3.1 Authentication System

**Status**: ✅ Complete (95%)
**Owner**: SpOC
**Implementation**: `backend_api/routers/auth.py`, `backend_api/auth/`

| Component | Description | Status |
|-----------|-------------|--------|
| User Registration | Account creation flow | ✅ Complete |
| Login/Logout | Session management with JWT | ✅ Complete |
| Password Reset | Email-based recovery | ⚠️ Partial |
| API Authentication | JWT token system | ✅ Complete |
| Role-Based Access | Admin vs user permissions | ✅ Complete |
| Supabase Integration | Production auth backend | ✅ Complete |
| Anonymous Mode | Works without credentials | ✅ Complete |

**Implemented Endpoints**:
```
/api/v1/auth/
├── POST /signup        ✅ Creates user, returns JWT
├── POST /login         ✅ Authenticates, returns JWT
├── POST /logout        ✅ Invalidates session
├── GET  /me            ✅ Returns current user profile
└── PUT  /me            ✅ Updates profile
```

**Implementation Notes**:
- Dual-mode operation: Supabase auth when configured, in-memory store otherwise
- JWT tokens with configurable expiration
- Frontend integration via `useAuth` hook
- Credential management for external APIs via `useCredentials` hook

---

### 3.2 Multi-Dataset Support Completion

**Status**: In Progress (60%)
**Owner**: Shared

| Component | Description | Status |
|-----------|-------------|--------|
| Dataset Versioning | Track dataset versions | Complete |
| Dataset Comparison | Compare multiple datasets | Partial |
| Dataset Catalog | Browse/search datasets | Complete |
| Batch Operations | Generate multiple datasets | Not Started |

---

### 3.3 Enhanced Report Generation

**Status**: Partial (80%)
**Owner**: SpOC

| Component | Description | Status |
|-----------|-------------|--------|
| Executive Summary | High-level overview | Not Started |
| Comparison Charts | Multi-algorithm comparison | Not Started |
| Historical Trends | Performance over time | Not Started |
| HTML Export | Alternative to PDF | Not Started |
| Configurable Sections | User-selected report content | Not Started |

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: stretch_goals -->

## 4. Stretch Goals

### 4.1 Open Evolve Integration

**Status**: Stretch Goal
**Owner**: Shared
**Priority**: Low (Future)

Per tech lead Lewis:
> "There's this program called Open Evolve, which is a way to optimize code bases using an AI agent. It's an iterative cycle of querying LLM to suggest modifications to a code base followed by an evaluation program that'll say how well the code performed."

**Vision**:
1. Use our evaluation script + benchmark datasets
2. LLM suggests modifications to a UCT processor
3. Evaluate how well those edits performed
4. Iterate to optimize UCT processors using AI

**Prerequisites**:
- [ ] Evaluation script fully validated with real UCTP output
- [ ] Pipeline in stable state
- [ ] Integration architecture designed

**Key Question**: Can an AI agent suggest improvements that actually optimize uncorrelated track processors?

---

### 4.2 Real UCTP Processor Validation

**Status**: Blocked (Waiting on External)
**Owner**: Shared
**Key Contact**: Patrick Ramsey (Aerospace Corp)

Per tech lead Lewis:
> "We still need to verify that our pipeline works with actual UCT processor output."

**Validation Workflow**:
1. Generate benchmark datasets using our pipeline
2. Send datasets to Patrick Ramsey / Aerospace Corp
3. Receive actual UCTP output
4. Run our evaluation pipeline on real results
5. Verify metrics are accurate and meaningful

**Status**: Aerospace Corp has expressed interest. Waiting on dataset generation stability.

---

### 4.3 Additional Evaluation Capabilities

| Feature | Description | Status |
|---------|-------------|--------|
| Radar Metrics | Range/range-rate residuals | Not Started |
| Statistical Testing | Significance analysis | Not Started |
| Covariance Consistency | NEES analysis | Partial |
| Alternative Association | Beyond Hungarian algorithm | Not Started |

<!-- /AI_SECTION -->

---

## Implementation Priorities

Based on current project state (updated 2026-02-03):

### ✅ Completed (Previous Priorities)
- ~~GCAT integration~~ ✅ Complete (`open_sources.py`)
- ~~UCS Database integration~~ ✅ Complete (`open_sources.py`)
- ~~SatNOGS API integration~~ ✅ Complete (`open_sources.py`)
- ~~Authentication system~~ ✅ Complete (`backend_api/auth/`)
- ~~T1/T2 Downsampling~~ ✅ Complete (`dataManipulation.py`)
- ~~T3 Processing~~ ✅ Complete (`simulateObservations.py`)
- ~~Web UI~~ ✅ Complete (`frontend/`)
- ~~Algorithm Submission~~ ✅ Complete (`backend_api/`)
- ~~Leaderboard~~ ✅ Complete (`backend_api/`)
- ~~UCTP Lab Framework~~ ✅ Complete (`uctp_lab/`)

### Immediate (Next Sprint)
1. ILRS validation module completion (full Earthdata integration)
2. Event labeling schema design
3. ccsds-ndm library integration

### Short-term (1-3 Sprints)
1. Event detection modules (launch, maneuver, proximity)
2. T4 object simulation
3. Enhanced report generation (executive summary, HTML export)
4. Multi-dataset batch operations

### Medium-term (4-6 Sprints)
1. Production deployment hardening
2. Real UCTP validation with Aerospace Corp
3. TraCSS API evaluation and integration

### Long-term (Future)
1. Open Evolve integration
2. Registration-required sources (Vimpel, EU SST if needed)

---

## Related Documents

- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Current implementation status
- [INTEGRATED_ROADMAP.md](INTEGRATED_ROADMAP.md) - Project timeline
- [DECISION_LOG.md](DECISION_LOG.md) - Strategic decisions
- [DATA_SOURCE_RATIONALE.md](../technical/DATA_SOURCE_RATIONALE.md) - Data source selection criteria
- [SDA_TAP_LAB_PLAN.md](SDA_TAP_LAB_PLAN.md) - SDA team tasks
- [SPOC_PLAN.md](SPOC_PLAN.md) - SpOC team tasks

---

*Consolidated from multiple planning documents on 2026-02-03*
