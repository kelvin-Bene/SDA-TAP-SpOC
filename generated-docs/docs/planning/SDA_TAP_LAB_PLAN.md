# SDA TAP Lab Team Plan

<!-- AI_METADATA
purpose: Task planning and tracking for SDA TAP Lab team
status: active
related_files: [planning/PROJECT_STATUS.md, planning/INTEGRATED_ROADMAP.md, planning/SPOC_PLAN.md, planning/FUTURE_IMPLEMENTATIONS.md]
last_updated: 2026-02-03
-->

<!-- NEEDS_UPDATE: Some TODO items in this document have been completed - check PROJECT_STATUS.md for current status -->

## Team Mission

**Labelling & Data Storage**: Develop software tools to pull event data from available data sources, label that data according to predefined classifications, parse and extract relevant measurement data, and clean and store the labelled data in a centrally available database.

---

## Current Team Responsibilities

1. **Data Source Integration** - Connect to UDL, Space-Track, CelesTrak, ESA DiscoWeb
2. **Event Labelling** - Classify data as launch, maneuver, proximity, breakup events
3. **Data Parsing & Extraction** - Extract measurement data based on classification
4. **Data Storage** - Store labelled data in centralized database
5. **Data Quality** - Ensure data meets quality thresholds via scoring/tiering

---

## Current Progress Summary

| Area | Status | Progress |
|------|--------|----------|
| API Integrations | ✅ Complete | 95% |
| Window Selection | ✅ Complete | 90% |
| Basic Scoring | ✅ Complete | 85% |
| Observation Simulation | ✅ Complete | 95% |
| Event Labelling | Not Started | 0% |
| Centralized Database | ✅ Complete | 95% |
| Tier Processing (T1-T3) | ✅ Complete | 100% |
| T4 Processing | Not Started | 0% |
| Open Source Integration | ✅ Complete | 90% |
| UCTP Lab Framework | ✅ Complete | 85% |

---

## TODO List by Priority

<!-- AI_SECTION: priority1_todos -->

### PRIORITY 1: Critical Path Items

#### ✅ TODO 1.1: Implement T3 Processing (Observation Simulation) - COMPLETE
**Status**: ✅ Complete (2026-01-19)
**Files**: `Create_Dataset.py`, `simulateObservations.py`

**Completed Tasks**:
- [x] Complete `epochsToSim()` function in `simulateObservations.py` (lines 358-507)
- [x] Integrate observation simulation into `Create_Dataset.py`
- [x] Time-bin based approach for epoch selection
- [x] Track grouping with configurable size and spacing
- [x] Test coverage: `test_simulation.py` (3/3 pass)

**Implementation Details**:
- Time-bin approach divides observation window into bins (period / bins_per_period)
- Identifies bins with insufficient observations
- Selects epochs at center of empty bins
- Configuration in `uct_benchmark/settings.py` (lines 164-188)

---

#### TODO 1.2: Implement T4 Processing (Object Simulation)

<!-- AI_IMPROVEMENT_OPPORTUNITY: T4 is the main remaining tier processing work. See FUTURE_IMPLEMENTATIONS.md -->

**Estimated Effort**: High
**Dependencies**: T3 Processing should be complete first
**Files**: `Create_Dataset.py`, new file `simulateObjects.py`

**Tasks**:
- [ ] Design object simulation strategy
- [ ] Create `simulateObjects.py` module
- [ ] Implement orbit generation for simulated objects
- [ ] Generate observations for simulated objects
- [ ] Integrate with T3 simulation pipeline
- [ ] Test with various population scenarios

**Conceptual Approach**:
```
T4 Scenario: Not enough real objects meet criteria
Solution:
1. Determine how many additional objects needed
2. Generate realistic orbital elements for synthetic objects
3. Create TLEs for these objects
4. Simulate observations using existing simulateObs()
5. Add synthetic objects to dataset with proper labelling
```

---

#### ✅ TODO 1.3: Implement Downsampling (T1/T2) - COMPLETE
**Status**: ✅ Complete (2026-01-18)
**Files**: `Create_Dataset.py`, `dataManipulation.py`

**Completed Tasks**:
- [x] Design downsampling strategy (three-stage pipeline)
- [x] Implement in `dataManipulation.py`
- [x] Preserve track structure during downsampling
- [x] Configuration in `uct_benchmark/settings.py` (lines 142-162)
- [x] Test coverage: `test_downsampling.py` (3/3 pass), `test_pipeline_e2e.py` (8/8 pass)

**Implementation Details**:
Three-stage downsampling pipeline:
1. `_lowerOrbitCoverage()` - Polygon-based coverage reduction
2. `_increaseTrackDistance()` - Sliding window gap widening
3. `_downsampleAbsolute()` - Time-binned count reduction

| Strategy | Description | Implementation |
|----------|-------------|----------------|
| Coverage-based | Reduce orbital coverage | `_lowerOrbitCoverage()` |
| Gap-widening | Increase time between tracks | `_increaseTrackDistance()` |
| Count-based | Reduce total observation count | `_downsampleAbsolute()` |

---

<!-- /AI_SECTION -->

<!-- AI_SECTION: priority2_event_labelling -->

### PRIORITY 2: Event Labelling System

<!-- AI_IMPROVEMENT_OPPORTUNITY: Event labelling is a major feature gap (0% complete). High value for benchmark realism. -->

#### TODO 2.1: Design Event Labelling Schema
**Estimated Effort**: Medium
**Dependencies**: SME input required
**Files**: New file `uct_benchmark/labelling/schema.py`

**Tasks**:
- [ ] Define event type taxonomy
- [ ] Create data structures for labels
- [ ] Design label storage format
- [ ] Document label definitions for SME review

**Proposed Event Types**:
```python
class EventType(Enum):
    LAUNCH = "launch"           # New object appearing
    MANEUVER = "maneuver"       # Orbital change
    PROXIMITY = "proximity"     # Close approach
    BREAKUP = "breakup"         # Object fragmentation
    REENTRY = "reentry"         # Atmospheric reentry
    UNKNOWN = "unknown"         # Unclassified
```

---

#### TODO 2.2: Implement Launch Event Detection
**Estimated Effort**: High
**Dependencies**: Schema design
**Files**: New file `uct_benchmark/labelling/launch_detection.py`

**Tasks**:
- [ ] Query UDL for launch event data
- [ ] Cross-reference with Space-Track launch data
- [ ] Match observations to launch events
- [ ] Label associated observations
- [ ] Store with provenance information

**Detection Approach**:
1. Query known launch events from data sources
2. Identify objects appearing near launch time/location
3. Associate subsequent observations with launch event
4. Label observation windows as "post-launch"

---

#### TODO 2.3: Implement Maneuver Event Detection
**Estimated Effort**: High
**Dependencies**: Schema design
**Files**: New file `uct_benchmark/labelling/maneuver_detection.py`

**Tasks**:
- [ ] Detect orbital element changes between TLEs
- [ ] Identify observation gaps suggesting maneuver
- [ ] Cross-reference with known maneuver data
- [ ] Label maneuver-related observations
- [ ] Handle uncertainty in maneuver timing

**Detection Indicators**:
- Semi-major axis change > threshold
- Eccentricity change > threshold
- Inclination change > threshold
- Observation gap during predicted maneuver

---

#### TODO 2.4: Implement Proximity Event Detection
**Estimated Effort**: Medium
**Dependencies**: Schema design
**Files**: New file `uct_benchmark/labelling/proximity_detection.py`

**Tasks**:
- [ ] Query conjunction data from data sources
- [ ] Propagate orbits to find close approaches
- [ ] Label observations near proximity events
- [ ] Classify by miss distance and relative velocity

---

#### TODO 2.5: Implement Breakup Event Detection
**Estimated Effort**: High
**Dependencies**: Schema design
**Files**: New file `uct_benchmark/labelling/breakup_detection.py`

**Tasks**:
- [ ] Query known breakup events
- [ ] Detect sudden increase in debris count
- [ ] Associate debris with parent object
- [ ] Label debris observations

---

<!-- /AI_SECTION -->

<!-- AI_SECTION: priority3_database -->

### ✅ PRIORITY 3: Centralized Database - COMPLETE

**Status**: ✅ Complete (95%) as of 2026-01-25 using DuckDB
**Files**: `uct_benchmark/database/`

#### ✅ TODO 3.1: Database Schema Design - COMPLETE
**Completed Tasks**:
- [x] Design normalized schema for observations
- [x] Design schema for state vectors/TLEs
- [x] Design schema for datasets
- [x] 14+ tables in `uct_benchmark/database/schema.py`

**Implemented Tables**:
- satellites, observations, state_vectors, element_sets
- datasets, events, data_sources, validation_measurements
- Plus additional supporting tables

---

#### ✅ TODO 3.2: Database Implementation - COMPLETE
**Completed Tasks**:
- [x] Select database backend: **DuckDB** (columnar, embedded, fast analytics)
- [x] Implement connection management (`connection.py`)
- [x] Create CRUD operations (`repository.py`)
- [x] Implement query interface
- [x] Repository pattern for data access
- [x] Export to JSON/Parquet formats
- [x] CLI interface (`uct_benchmark/database/cli.py`)

---

#### ✅ TODO 3.3: Data Ingestion Pipeline - COMPLETE
**Completed Tasks**:
- [x] Batch ingestion from API pulls (`ingestion.py`)
- [x] Incremental updates support
- [x] Data validation
- [x] Duplicate handling
- [x] Open source data integration (GCAT, UCS, SatNOGS, ILRS)

---

<!-- /AI_SECTION -->

<!-- AI_SECTION: priority4_infrastructure -->

### PRIORITY 4: Infrastructure & Quality

#### ✅ TODO 4.1: Complete Observation Simulation - COMPLETE
**Status**: ✅ Complete (95%)
**Files**: `simulateObservations.py`

**Completed Tasks**:
- [x] Complete `epochsToSim()` function (lines 358-507)
- [x] Sensor selection with weighted random selection
- [x] Observation uncertainty modeling with noise
- [x] Unit tests: `test_simulation.py` (3/3 pass)
- [ ] Add radar observation simulation (future enhancement)

---

#### TODO 4.2: Error Handling Improvements
**Estimated Effort**: Low
**Dependencies**: None
**Files**: Various

**Tasks**:
- [ ] Add try/except blocks to API calls
- [ ] Implement retry logic with exponential backoff
- [ ] Add meaningful error messages
- [ ] Create error logging
- [ ] Handle edge cases in window selection

---

#### TODO 4.3: Linux Setup Script
**Estimated Effort**: Low
**Dependencies**: None
**Files**: New file `setup.sh`

**Tasks**:
- [ ] Create bash script equivalent to `setup.bat`
- [ ] Handle Python/uv installation
- [ ] Configure environment variables
- [ ] Create data directory structure
- [ ] Test on common Linux distributions

---

#### TODO 4.4: Multi-Dataset Support
**Estimated Effort**: Medium
**Dependencies**: Database
**Files**: `Create_Dataset.py`, `windowTools.py`

**Tasks**:
- [ ] Modify dataset saving to support versioning
- [ ] Update GUI for multi-dataset management
- [ ] Create dataset catalog/index
- [ ] Implement dataset comparison tools

---

## Detailed Task Breakdown

### ✅ Completed Tasks

| Task | Status | Completed |
|------|--------|-----------|
| Complete `epochsToSim()` | ✅ Complete | 2026-01-19 |
| Integrate T3 simulation | ✅ Complete | 2026-01-19 |
| Implement downsampling (T1/T2) | ✅ Complete | 2026-01-18 |
| Database schema design | ✅ Complete | 2026-01-25 |
| Database implementation | ✅ Complete | 2026-01-25 |
| Data ingestion pipeline | ✅ Complete | 2026-01-25 |
| Open source integration | ✅ Complete | 2026-02-03 |

### Immediate Next Steps (Current Sprint)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| ILRS validation module | TBD | P1 | 24 |
| Design event schema | TBD | P2 | 8 |
| Document open source APIs | TBD | P3 | 8 |

### Short-term (1-2 Sprints)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| Implement T4 processing | TBD | P2 | 40 |
| Launch event detection | TBD | P2 | 32 |
| Maneuver event detection | TBD | P2 | 40 |

### Medium-term (3-4 Sprints)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| Proximity detection | TBD | P2 | 24 |
| Breakup detection | TBD | P2 | 32 |
| ccsds-ndm integration | TBD | P3 | 16 |

---

## Handoff Points to SpOC

The following items must be delivered to SpOC:

| Deliverable | Format | Status |
|-------------|--------|--------|
| Labelled observation data | JSON/Parquet | Pending (event labeling not started) |
| Event classification schema | Documentation | Pending |
| Database query interface | API | ✅ Complete (`repository.py`) |
| Data quality reports | PDF | ✅ Complete (`generatePDF.py`) |
| Dataset generation API | Python module | ✅ Complete |
| Open source data enrichment | API | ✅ Complete (`DataSourceManager`) |
| UCTP Lab framework | Python module | ✅ Complete (`uctp_lab/`) |

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| API query success rate | >99% | ~95% |
| Data labelling accuracy | >95% | N/A |
| Tier classification accuracy | >90% | ~85% |
| Database query latency | <1s | N/A |
| Dataset generation time | <5min | ~3min |

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| UDL API changes | High | Low | Version API integration |
| Data quality issues | High | Medium | Improve validation |
| Performance bottlenecks | Medium | Medium | Add caching, indexing |
| SME availability | High | Medium | Document assumptions |

---

## Dependencies on SpOC

| Dependency | Description | Status |
|------------|-------------|--------|
| Evaluation criteria | Metrics definitions | Complete |
| Dataset format spec | Output format requirements | Complete |
| Web API requirements | Database query needs | Pending |
| Algorithm interface spec | Data format for algorithms | Pending |

---

<!-- /AI_SECTION -->

<!-- AI_SECTION: stretch_goals -->

## Stretch Goal: Open Evolve Integration

As outlined by tech lead Lewis in the initial project meeting, once the evaluation pipeline is fully validated, a potential future use case is **Open Evolve** integration:

> "There's this program called Open Evolve, which is a way to optimize code bases using an AI agent. It's an iterative cycle of querying LLM to suggest modifications to a code base followed by an evaluation program that'll say how well the code performed."

### Vision
1. Use our evaluation script + benchmark datasets
2. LLM suggests modifications to a UCT processor
3. Evaluate how well those edits performed
4. Iterate to optimize UCT processors using AI

### Prerequisites
- Evaluation script must be fully validated with real UCTP output
- Pipeline must be in a "good enough spot" (per Lewis)
- Integration architecture design needed

### Success Criteria
- Can an AI agent suggest improvements that actually optimize uncorrelated track processors?
- Does the iterative process produce meaningful performance gains?

**Timeline**: "Towards the end of the semester if things are in a good spot" - Lewis

<!-- /AI_SECTION -->
