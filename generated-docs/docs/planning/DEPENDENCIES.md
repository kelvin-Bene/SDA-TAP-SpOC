# Inter-Team Dependencies

## Overview

This document maps the dependencies between SDA TAP Lab and SpOC teams, identifying critical handoff points, shared interfaces, and coordination requirements.

---

## Dependency Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
│                    (UDL, Space-Track, CelesTrak, ESA)                       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SDA TAP LAB                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │ API Integration │──│ Event Labelling│──│   Database     │                 │
│  └────────────────┘  └────────────────┘  └───────┬────────┘                 │
│                                                   │                          │
│  ┌────────────────┐  ┌────────────────┐          │                          │
│  │ T3/T4 Processing│──│ Data Quality   │──────────┤                          │
│  └────────────────┘  └────────────────┘          │                          │
└──────────────────────────────────────────────────┼──────────────────────────┘
                                                   │
                          HANDOFF INTERFACE        │
                    ┌──────────────────────────────┼──────────────────────────┐
                    │  • Database Query API        │                          │
                    │  • Dataset Generation API    │                          │
                    │  • Data Quality Reports      │                          │
                    │  • Event Label Schema        │                          │
                    └──────────────────────────────┼──────────────────────────┘
                                                   │
┌──────────────────────────────────────────────────┼──────────────────────────┐
│                               SpOC               │                          │
│                                                  ▼                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │ Backend API    │◀─│ Dataset Access │◀─│ Database Query │                 │
│  └───────┬────────┘  └────────────────┘  └────────────────┘                 │
│          │                                                                   │
│          ▼                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │ Web UI         │──│ Submission     │──│ Evaluation     │                 │
│  └────────────────┘  └────────────────┘  └───────┬────────┘                 │
│                                                   │                          │
│  ┌────────────────┐  ┌────────────────┐          │                          │
│  │ Leaderboard    │◀─│ Results Storage│◀─────────┘                          │
│  └────────────────┘  └────────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ALGORITHM DEVELOPERS                                  │
│              (Download datasets, Submit results, View rankings)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Critical Dependencies

### 1. Database Query API (SDA TAP → SpOC)

**Purpose**: Enable SpOC to access stored observation and label data

**Status**: NOT STARTED

**Requirements**:
```
Interface: REST API or Python SDK
Endpoints:
  - Query observations by time window, regime, sensor
  - Query labels by event type
  - Query datasets by parameters
  - Get data quality metrics

Response Format: JSON
Rate Limiting: Required
Authentication: Required
```

**Blocking SpOC Work**:
- Dataset browser UI
- Dataset generation from stored data
- Real data integration tests

**Workaround**: SpOC can develop with mock data until API available

---

### 2. Dataset Generation API (SDA TAP → SpOC)

**Purpose**: Allow SpOC to trigger new dataset generation

**Status**: PARTIAL (CLI exists, no API)

**Current State**:
```python
# Existing function in Create_Dataset.py
def create_datasets_from_codes(datasetCodeDataframe, udl_token=None, ...):
    ...
```

**Required Enhancements**:
- RESTful API wrapper
- Asynchronous execution
- Progress reporting
- Error handling for web context

**Blocking SpOC Work**:
- Dataset generator UI component
- On-demand dataset creation feature

---

### 3. Data Quality Reports (SDA TAP → SpOC)

**Purpose**: Provide tier and quality information for datasets

**Status**: PARTIAL

**Current Output**:
- Tier classification (T1-T5)
- Orbital coverage metrics
- Observation counts

**Required Enhancements**:
- Structured JSON output
- Historical quality tracking
- Quality trend visualization data

---

### 4. Event Label Schema (SDA TAP → SpOC)

**Purpose**: Define format for labelled data

**Status**: NOT STARTED

**Required Definition**:
```json
{
  "observation_id": "uuid",
  "event_type": "launch|maneuver|proximity|breakup|unknown",
  "event_id": "uuid",
  "confidence": 0.95,
  "labelled_by": "system|sme_name",
  "labelled_at": "timestamp",
  "metadata": {
    "parent_object": "norad_id (for breakup)",
    "delta_v": "km/s (for maneuver)",
    "miss_distance": "km (for proximity)"
  }
}
```

**Blocking SpOC Work**:
- Event-aware dataset filtering
- Label-based evaluation (future)

---

### 5. Submission Format (SpOC → SDA TAP)

**Purpose**: Define expected output format from UCTP algorithms

**Status**: PARTIAL (dummy UCTP format exists)

**Current Format** (from dummyUCTP.py):
```json
{
  "idStateVector": 0,
  "sourcedData": ["obs_id1", "obs_id2"],
  "epoch": "ISO timestamp",
  "xpos": 0.0, "ypos": 0.0, "zpos": 0.0,
  "xvel": 0.0, "yvel": 0.0, "zvel": 0.0,
  "cov": [21 floats],
  ...
}
```

**Required Enhancements**:
- Formal JSON schema
- Validation rules
- Error message standards
- Optional confidence fields

**Blocking SDA TAP Work**:
- None currently (format already used internally)

---

### 6. Evaluation Metrics Definition (SpOC → SDA TAP)

**Purpose**: Define how algorithm performance is measured

**Status**: COMPLETE

**Defined Metrics**:
| Category | Metrics |
|----------|---------|
| Binary | TP, FP, FN, Precision, Recall, F1 |
| State | Position error, Velocity error, Mahalanobis |
| Residual | RA/Dec RMS, Range RMS |

**Documentation Location**: `docs/EVALUATION_METRICS.md`

---

## Shared Interfaces

### 1. Configuration Management

**Shared File**: `uct_benchmark/config.py`

**Coordination Required**:
- Changes to thresholds affect both teams
- New parameters need documentation
- Version tracking for configuration changes

**Protocol**:
1. Propose changes in shared channel
2. Document impact on both teams
3. Update config with comments
4. Notify other team after merge

---

### 2. Data Format Standards

**Observation Format**: UDL schema (defined)
**State Vector Format**: UDL schema (defined)
**TLE Format**: Standard 2-line (defined)
**Dataset JSON Format**: Custom (defined in apiIntegration.py)

**Changes Require**:
- Both teams review
- Migration plan for existing data
- Version bump in schema

---

### 3. Error Handling Standards

**Proposed Standard**:
```python
class UCTBenchmarkError(Exception):
    """Base exception for all project errors."""
    pass

class DataSourceError(UCTBenchmarkError):
    """Error accessing data source."""
    pass

class ValidationError(UCTBenchmarkError):
    """Data validation failed."""
    pass

class ProcessingError(UCTBenchmarkError):
    """Data processing failed."""
    pass
```

**Status**: NOT IMPLEMENTED - needs agreement

---

### 4. Logging Standards

**Proposed Standard**:
- Use `loguru` for all logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Include timestamps and module names
- Structured JSON logs for production

**Current State**: Mixed (some print, some logger)

**Status**: Needs standardization

---

## Coordination Requirements

### Weekly Sync Meeting Agenda

1. **Progress Updates** (10 min)
   - SDA TAP: Data pipeline status
   - SpOC: Web platform status

2. **Blockers** (10 min)
   - Identify blocking dependencies
   - Assign resolution owners

3. **Integration Planning** (10 min)
   - Upcoming handoffs
   - Testing requirements

4. **Technical Discussion** (10 min)
   - Architecture decisions
   - Interface changes

---

### Communication Channels

| Purpose | Channel | Response Time |
|---------|---------|---------------|
| Urgent blockers | Direct message | <2 hours |
| Technical questions | Team chat | <1 day |
| Feature requests | GitHub issues | <1 week |
| Documentation | Pull requests | <1 week |

---

### Code Review Protocol

**Cross-Team Reviews Required For**:
- Changes to shared interfaces
- Changes to data formats
- Changes to configuration
- New API endpoints

**Review Checklist**:
- [ ] Does not break other team's code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Backward compatible or migration provided

---

## Dependency Timeline

### Phase 2 Dependencies

```
Week 1-2: SDA TAP completes T3 processing
          SpOC begins frontend with mock data

Week 3-4: SDA TAP starts database design
          SpOC defines submission format

Week 5-6: SDA TAP provides database schema
          SpOC reviews for query requirements
          HANDOFF: Schema agreement

Week 7-8: SDA TAP implements database
          SpOC implements backend with mock data

Week 9-10: SDA TAP completes database
           HANDOFF: Database API access
           SpOC integrates real data
```

### Critical Path Items

| Item | Owner | Blocks | Must Complete By |
|------|-------|--------|------------------|
| Database Schema | SDA TAP | SpOC API design | Week 6 |
| Database API | SDA TAP | SpOC integration | Week 10 |
| Submission Format | SpOC | Final eval pipeline | Week 4 |
| Event Schema | SDA TAP | Event-based features | Week 8 |

---

## Risk Management

### Dependency Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database delayed | SpOC blocked | Mock data development |
| API changes | Rework required | Versioned APIs |
| Format disagreements | Integration issues | Early agreement |
| Resource constraints | Timeline slip | Parallel workstreams |

### Escalation Path

1. **Team Lead Discussion**: 1 day response
2. **Technical Lead Review**: 3 day response
3. **Project Lead Decision**: 5 day response

---

## Interface Contracts

### Contract 1: Database Query API

```yaml
Name: Database Query API
Owner: SDA TAP Lab
Consumer: SpOC
Version: 1.0 (proposed)
Status: NOT STARTED

Endpoints:
  /observations:
    GET:
      params: [start_time, end_time, regime, sensor_type]
      response: ObservationList

  /labels:
    GET:
      params: [event_type, confidence_min]
      response: LabelList

  /datasets:
    GET:
      params: [tier, regime, created_after]
      response: DatasetList
    POST:
      body: DatasetGenerationRequest
      response: DatasetGenerationJob

SLA:
  availability: 99%
  response_time: <2s for queries
  rate_limit: 100 req/min
```

### Contract 2: Evaluation Results Format

```yaml
Name: Evaluation Results Format
Owner: SpOC
Consumer: Both teams
Version: 1.0 (current)
Status: IMPLEMENTED

Format:
  association_results:
    - associated_count: int
    - non_associated_count: int
    - time_elapsed: float

  binary_results:
    - true_positives: int
    - false_positives: int
    - false_negatives: int
    - precision: float
    - recall: float
    - f1_score: float

  state_results:
    - position_error_mean: float
    - position_error_std: float
    - velocity_error_mean: float
    - velocity_error_std: float

  residual_results:
    - ra_rms: float
    - dec_rms: float
```

---

## Appendix: Contact Matrix

| Area | SDA TAP Contact | SpOC Contact |
|------|-----------------|--------------|
| API Integration | TBD | TBD |
| Database | TBD | TBD |
| Evaluation | TBD | TBD |
| Web UI | N/A | TBD |
| Event Labelling | TBD | TBD |
| Overall Coordination | TBD | TBD |
