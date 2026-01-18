# SpOC Team Plan

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
| Evaluation Metrics | Complete | 90% |
| Orbit Association | Complete | 95% |
| PDF Report Generation | Complete | 80% |
| Dummy UCTP | Complete | 100% |
| Evaluation Pipeline | Partial | 75% |
| Web UI | Not Started | 0% |
| Algorithm Submission | Not Started | 0% |
| Leaderboard | Not Started | 0% |
| Documentation for Developers | Partial | 40% |

---

## TODO List by Priority

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

### PRIORITY 2: Web UI Development

#### TODO 2.1: Frontend Framework Setup
**Estimated Effort**: High
**Dependencies**: None
**Files**: New folder `web/frontend/`

**Tasks**:
- [ ] Select frontend framework (React recommended)
- [ ] Set up project structure
- [ ] Create component library
- [ ] Implement routing
- [ ] Set up build pipeline

**Recommended Technology Stack**:
```
Frontend:
├── React 18+
├── TypeScript
├── Tailwind CSS
├── React Query (data fetching)
└── Recharts (visualizations)

Build:
├── Vite
└── ESLint + Prettier
```

---

#### TODO 2.2: Backend API Development
**Estimated Effort**: High
**Dependencies**: Database (from SDA TAP)
**Files**: New folder `web/backend/`

**Tasks**:
- [ ] Select backend framework (FastAPI recommended)
- [ ] Design REST API endpoints
- [ ] Implement authentication
- [ ] Create dataset endpoints
- [ ] Create submission endpoints
- [ ] Create evaluation endpoints
- [ ] Add rate limiting

**Proposed API Endpoints**:
```
/api/v1/
├── auth/
│   ├── POST /login
│   ├── POST /register
│   └── POST /logout
├── datasets/
│   ├── GET /                   # List available datasets
│   ├── GET /{id}               # Get dataset details
│   ├── POST /generate          # Generate new dataset
│   └── GET /{id}/download      # Download dataset
├── submissions/
│   ├── GET /                   # List user's submissions
│   ├── POST /                  # Submit algorithm results
│   ├── GET /{id}               # Get submission status
│   └── GET /{id}/results       # Get evaluation results
├── leaderboard/
│   ├── GET /                   # Get current rankings
│   └── GET /history            # Get historical rankings
└── users/
    ├── GET /me                 # Get current user
    └── PUT /me                 # Update profile
```

---

#### TODO 2.3: Dataset Browser Component
**Estimated Effort**: Medium
**Dependencies**: Backend API
**Files**: `web/frontend/src/components/DatasetBrowser/`

**Tasks**:
- [ ] Create dataset list view
- [ ] Add filtering by regime, tier, date
- [ ] Show dataset statistics
- [ ] Implement dataset preview
- [ ] Add download functionality

**UI Mockup**:
```
┌─────────────────────────────────────────────────────────┐
│ Dataset Browser                                    [+]   │
├─────────────────────────────────────────────────────────┤
│ Filters: [LEO ▼] [All Tiers ▼] [Last 30 days ▼]        │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Dataset: LEO_T1_2025-01-01                          │ │
│ │ Objects: 42 | Observations: 12,456 | Tier: T1       │ │
│ │ Created: 2025-01-01 | Size: 2.3 MB                  │ │
│ │ [Preview] [Download] [Details]                      │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Dataset: MEO_T2_2025-01-05                          │ │
│ │ ...                                                 │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

#### TODO 2.4: Dataset Generator Component
**Estimated Effort**: Medium
**Dependencies**: Backend API, SDA TAP integration
**Files**: `web/frontend/src/components/DatasetGenerator/`

**Tasks**:
- [ ] Create parameter configuration form
- [ ] Show generation progress
- [ ] Handle errors gracefully
- [ ] Preview generated dataset
- [ ] Save/load configurations

---

#### TODO 2.5: Submission Interface Component
**Estimated Effort**: High
**Dependencies**: Backend API, Evaluation pipeline
**Files**: `web/frontend/src/components/Submission/`

**Tasks**:
- [ ] Create file upload component
- [ ] Validate submission format
- [ ] Show upload progress
- [ ] Display submission status
- [ ] Show evaluation progress
- [ ] Display results when complete

---

#### TODO 2.6: Results Viewer Component
**Estimated Effort**: Medium
**Dependencies**: Submission interface
**Files**: `web/frontend/src/components/ResultsViewer/`

**Tasks**:
- [ ] Display all evaluation metrics
- [ ] Create comparison charts
- [ ] Show metric breakdowns
- [ ] Export results
- [ ] Link to full PDF report

---

### PRIORITY 3: Algorithm Submission System

#### TODO 3.1: Submission Format Specification
**Estimated Effort**: Low
**Dependencies**: None
**Files**: Documentation

**Tasks**:
- [ ] Define JSON schema for submissions
- [ ] Document required fields
- [ ] Create example submissions
- [ ] Write validation guide

**Proposed Submission Format**:
```json
{
  "algorithm_name": "MyUCTP",
  "algorithm_version": "1.0.0",
  "dataset_id": "dataset_uuid",
  "results": [
    {
      "idStateVector": 0,
      "sourcedData": ["obs_id_1", "obs_id_2"],
      "epoch": "2025-01-01T00:00:00.000000Z",
      "xpos": -7365.971,
      "ypos": -1331.400,
      "zpos": 1514.249,
      "xvel": 1.977,
      "yvel": -5.225,
      "zvel": 4.473,
      "cov": [/* 21 elements */],
      "confidence": 0.95
    }
  ],
  "metadata": {
    "runtime_seconds": 123.45,
    "hardware": "description"
  }
}
```

---

#### TODO 3.2: Submission Validation
**Estimated Effort**: Medium
**Dependencies**: Format specification
**Files**: `web/backend/validation/`

**Tasks**:
- [ ] Implement JSON schema validation
- [ ] Validate observation ID references
- [ ] Check state vector reasonableness
- [ ] Verify covariance positive-definiteness
- [ ] Return detailed error messages

---

#### TODO 3.3: Evaluation Queue System
**Estimated Effort**: High
**Dependencies**: Validation
**Files**: `web/backend/queue/`

**Tasks**:
- [ ] Select queue backend (Redis/RabbitMQ)
- [ ] Implement job submission
- [ ] Create worker processes
- [ ] Handle timeouts and failures
- [ ] Store results

---

### PRIORITY 4: Leaderboard System

#### TODO 4.1: Ranking Algorithm Design
**Estimated Effort**: Medium
**Dependencies**: Evaluation metrics finalized
**Files**: `web/backend/leaderboard/`

**Tasks**:
- [ ] Define primary ranking metric (F1-Score recommended)
- [ ] Define tiebreaker metrics
- [ ] Handle different dataset types
- [ ] Consider time-based weighting

**Proposed Ranking Scheme**:
```
Primary Sort: F1-Score (descending)
Tiebreaker 1: Position RMS (ascending)
Tiebreaker 2: Submission time (ascending)

Separate leaderboards per:
- Orbital regime (LEO, MEO, GEO)
- Dataset tier (T1, T2, T3, T4)
- Overall
```

---

#### TODO 4.2: Leaderboard UI Component
**Estimated Effort**: Medium
**Dependencies**: Ranking algorithm, Backend API
**Files**: `web/frontend/src/components/Leaderboard/`

**Tasks**:
- [ ] Create sortable table view
- [ ] Add filtering options
- [ ] Show metric breakdowns
- [ ] Display historical trends
- [ ] Highlight user's submissions

**UI Mockup**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Leaderboard: LEO Datasets                              [Export] │
├─────────────────────────────────────────────────────────────────┤
│ Rank │ Algorithm      │ F1-Score │ Pos RMS │ Submitted         │
├──────┼────────────────┼──────────┼─────────┼───────────────────┤
│ 🥇 1 │ AlgorithmA     │ 0.9543   │ 2.34 km │ 2025-01-10        │
│ 🥈 2 │ AlgorithmB     │ 0.9521   │ 2.56 km │ 2025-01-09        │
│ 🥉 3 │ AlgorithmC     │ 0.9498   │ 3.12 km │ 2025-01-08        │
│   4  │ YourAlgorithm* │ 0.9234   │ 4.56 km │ 2025-01-11        │
│   5  │ AlgorithmD     │ 0.9156   │ 3.89 km │ 2025-01-07        │
└──────┴────────────────┴──────────┴─────────┴───────────────────┘
* Your best submission
```

---

#### TODO 4.3: Historical Tracking
**Estimated Effort**: Low
**Dependencies**: Leaderboard database
**Files**: `web/backend/leaderboard/history.py`

**Tasks**:
- [ ] Store historical rankings
- [ ] Track algorithm improvements over time
- [ ] Generate trend charts
- [ ] Identify state-of-the-art progression

---

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
| Observation data access | Database API | Pending | High |
| Event labels | Database table | Pending | Medium |
| Dataset metadata | JSON/Database | Partial | High |
| Data quality info | Scoring output | Complete | Low |
| Satellite catalog | Database table | Pending | Medium |

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
