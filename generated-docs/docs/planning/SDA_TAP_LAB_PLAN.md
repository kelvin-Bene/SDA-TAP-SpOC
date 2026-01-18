# SDA TAP Lab Team Plan

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
| API Integrations | Complete | 95% |
| Window Selection | Complete | 90% |
| Basic Scoring | Complete | 85% |
| Observation Simulation | Partial | 60% |
| Event Labelling | Not Started | 0% |
| Centralized Database | Not Started | 0% |
| Tier Processing | Not Started | 5% |

---

## TODO List by Priority

### PRIORITY 1: Critical Path Items

#### TODO 1.1: Implement T3 Processing (Observation Simulation)
**Estimated Effort**: Medium
**Dependencies**: None (framework exists)
**Files**: `Create_Dataset.py`, `simulateObservations.py`

**Tasks**:
- [ ] Complete `epochsToSim()` function in `simulateObservations.py`
- [ ] Integrate observation simulation into `Create_Dataset.py`
- [ ] Add logic to determine which observations need simulation
- [ ] Test with various orbital regimes (LEO, MEO, GEO)
- [ ] Validate simulated observations against real data patterns

**Implementation Notes**:
```python
# In Create_Dataset.py around line 107
if tierThreshold == "T3":
    # For each satellite with insufficient coverage:
    # 1. Determine epochs needing simulation using epochsToSim()
    # 2. Call simulateObs() to generate synthetic observations
    # 3. Merge simulated obs with real observations
    # 4. Recalculate scoring to verify improvement
```

---

#### TODO 1.2: Implement T4 Processing (Object Simulation)
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

#### TODO 1.3: Implement Downsampling (T1/T2)
**Estimated Effort**: Medium
**Dependencies**: None
**Files**: `Create_Dataset.py`, new file `downsample.py`

**Tasks**:
- [ ] Design downsampling strategy (random, systematic, quality-based)
- [ ] Create `downsample.py` module
- [ ] Implement observation reduction while maintaining quality
- [ ] Preserve track structure during downsampling
- [ ] Add configuration options for downsampling parameters
- [ ] Test effect on evaluation metrics

**Downsampling Strategies**:
| Strategy | Description | Use Case |
|----------|-------------|----------|
| Random | Randomly remove observations | General reduction |
| Systematic | Remove every Nth observation | Uniform reduction |
| Quality-based | Remove lower-quality obs first | Preserve best data |
| Track-aware | Maintain minimum obs per track | Preserve structure |

---

### PRIORITY 2: Event Labelling System

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

### PRIORITY 3: Centralized Database

#### TODO 3.1: Database Schema Design
**Estimated Effort**: High
**Dependencies**: Event labelling schema
**Files**: New folder `uct_benchmark/database/`

**Tasks**:
- [ ] Design normalized schema for observations
- [ ] Design schema for state vectors/TLEs
- [ ] Design schema for event labels
- [ ] Design schema for datasets
- [ ] Create migration scripts

**Proposed Tables**:
```
observations
├── id (PK)
├── sat_no
├── ob_time
├── ra, dec, range, etc.
├── sensor_id
├── data_mode
└── created_at

state_vectors
├── id (PK)
├── sat_no
├── epoch
├── x, y, z, vx, vy, vz
├── covariance
└── source

event_labels
├── id (PK)
├── observation_id (FK)
├── event_type
├── confidence
├── labelled_by
└── labelled_at

datasets
├── id (PK)
├── name
├── created_at
├── parameters (JSON)
└── tier
```

---

#### TODO 3.2: Database Implementation
**Estimated Effort**: High
**Dependencies**: Schema design
**Files**: `uct_benchmark/database/`

**Tasks**:
- [ ] Select database backend (PostgreSQL recommended)
- [ ] Implement connection management
- [ ] Create CRUD operations
- [ ] Implement query interface
- [ ] Add indexing for performance
- [ ] Create backup/restore procedures

---

#### TODO 3.3: Data Ingestion Pipeline
**Estimated Effort**: Medium
**Dependencies**: Database implementation
**Files**: New file `uct_benchmark/database/ingestion.py`

**Tasks**:
- [ ] Create batch ingestion from API pulls
- [ ] Implement incremental updates
- [ ] Add data validation
- [ ] Handle duplicates
- [ ] Log ingestion statistics

---

### PRIORITY 4: Infrastructure & Quality

#### TODO 4.1: Complete Observation Simulation
**Estimated Effort**: Medium
**Dependencies**: None
**Files**: `simulateObservations.py`

**Tasks**:
- [ ] Complete `epochsToSim()` function
- [ ] Add radar observation simulation
- [ ] Improve sensor selection logic
- [ ] Add observation uncertainty modeling
- [ ] Create unit tests

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

### Immediate Next Steps (Next Sprint)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| Complete `epochsToSim()` | TBD | P1 | 16 |
| Integrate T3 simulation | TBD | P1 | 24 |
| Design event schema | TBD | P2 | 8 |
| Document current APIs | TBD | P3 | 8 |

### Short-term (1-2 Sprints)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| Implement downsampling | TBD | P1 | 16 |
| Implement T4 processing | TBD | P1 | 40 |
| Launch event detection | TBD | P2 | 32 |
| Database schema design | TBD | P3 | 24 |

### Medium-term (3-4 Sprints)

| Task | Assignee | Priority | Est. Hours |
|------|----------|----------|------------|
| Maneuver detection | TBD | P2 | 40 |
| Database implementation | TBD | P3 | 60 |
| Data ingestion pipeline | TBD | P3 | 24 |
| Proximity detection | TBD | P2 | 24 |

---

## Handoff Points to SpOC

The following items must be delivered to SpOC:

| Deliverable | Format | Status |
|-------------|--------|--------|
| Labelled observation data | JSON/Parquet | Pending |
| Event classification schema | Documentation | Pending |
| Database query interface | API | Pending |
| Data quality reports | PDF | Partial |
| Dataset generation API | Python module | Complete |

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
