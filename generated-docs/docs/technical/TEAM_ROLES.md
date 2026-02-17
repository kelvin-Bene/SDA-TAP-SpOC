# Team Roles: SDA TAP Lab vs SpOC

## Overview

This project is a partnership between multiple organizations, each with distinct but complementary responsibilities in developing the UCT Processing benchmarking framework.

## Historical Context: Prior Team Contributions

During the summer internship period, there was another team from **Indiana University (IU)** that worked alongside the main team. Per tech lead Lewis:

> "The other internship group that we were working with, they were working on creating a labeled database of these events and the observations that go together with these events."

The IU team specifically worked on:
- **Parsing NOTSOs** (Notice to Space Operator) - text documents describing space events
- **Creating a labeled database** of space events (breakups, launches, proximity events, maneuvers)
- **Associating observations with events** - linking observation data to classified events

This work provides the foundation for the event labeling system that needs to be integrated into the current pipeline.

## SDA TAP Lab (Space Systems Command)

### Organization
- Part of Space Systems Command (SSC)
- United States Space Force
- Location: Los Angeles AFB area

### Mission
"Accelerates the delivery of space battle management software to operational units."

### Project Responsibilities: Labelling & Data Storage

The SDA TAP Lab team is responsible for the **upstream** portion of the pipeline:

#### 1. Data Source Integration
- Developing API integrations for multiple data sources
- Connecting to the Unified Data Library (UDL)
- Integrating Space-Track, CelesTrak, and ESA DiscoWeb APIs
- Managing authentication and data access

#### 2. Event Labelling
- Defining data label classifications:
  - Launch events
  - Maneuver events
  - Proximity events
  - Breakup events
- Working with Subject Matter Experts (SMEs) to refine label definitions
- Iteratively improving label fidelity over time

#### 3. Data Parsing & Extraction
- Extracting relevant measurement data based on classification
- Parsing observation data from various sensor types
- Handling different data formats (TDM, JSON, CSV)

#### 4. Data Storage
- Cleaning and storing labelled data
- Managing centralized database
- Maintaining data integrity and provenance
- Version control for datasets

#### Key Code Responsibilities
- `uct_benchmark/api/apiIntegration.py` - API integration module
- `uct_benchmark/data/windowCheck.py` - Window selection logic
- `uct_benchmark/data/windowTools.py` - Window utilities
- `uct_benchmark/data/basicScoringFunction.py` - Data quality scoring
- `uct_benchmark/Create_Dataset.py` - Dataset creation driver

---

## SpOC (Space Operations Command)

### Organization
- Space Operations Command
- United States Space Force
- Operational arm of space operations

### Project Responsibilities: Benchmark Dataset Generation & Evaluation Criteria

The SpOC team is responsible for the **downstream** portion of the pipeline:

#### 1. Benchmark Dataset Generation
- Creating standardized benchmark datasets from stored data
- Defining dataset parameters and configurations
- Implementing dataset tiering system (T1-T5)
- Managing dataset versioning and distribution

#### 2. Evaluation Criteria Development
- Defining performance metrics for UCTP algorithms
- Implementing evaluation functions
- Creating standardized testing protocols
- Developing comparison methodologies

#### 3. Algorithm Interface
- Defining input/output formats for UCTP algorithms
- Creating dummy UCTP for testing
- Supporting algorithm developers with documentation
- Managing algorithm submission and evaluation

#### 4. Reporting & Analysis
- Generating evaluation reports
- Creating visualizations
- Comparing algorithm performance
- Publishing benchmark results

#### Key Code Responsibilities
- `uct_benchmark/Evaluation.py` - Main evaluation driver
- `uct_benchmark/evaluation/binaryMetrics.py` - Binary classification metrics
- `uct_benchmark/evaluation/stateMetrics.py` - Orbital state metrics
- `uct_benchmark/evaluation/residualMetrics.py` - Residual analysis
- `uct_benchmark/evaluation/orbitAssociation.py` - Orbit association logic
- `uct_benchmark/uctp/dummyUCTP.py` - Test UCTP implementation
- `uct_benchmark/utils/generatePDF.py` - Report generation

---

## Collaboration Points

### Shared Responsibilities

| Area | SDA TAP Lab | SpOC |
|------|-------------|------|
| Dataset Format | Define storage format | Define benchmark format |
| Data Quality | Score and tier data | Validate for evaluation |
| Documentation | Data labelling docs | Evaluation criteria docs |
| API Design | Data input APIs | Algorithm submission APIs |

### Integration Points

1. **Data Handoff**
   - SDA TAP stores labelled data in database
   - SpOC retrieves data for benchmark generation

2. **Format Specifications**
   - Both teams agree on data formats
   - JSON structure defined in `saveDataset()` and `loadDataset()`

3. **Quality Thresholds**
   - SDA TAP defines data quality tiers
   - SpOC uses tiers for benchmark categorization

### Communication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources                              │
│         (UDL, Space-Track, CelesTrak, ESA)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  SDA TAP Lab                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│   │ API Pull     │───▶│ Label &      │───▶│ Clean &      │  │
│   │              │    │ Parse        │    │ Store        │  │
│   └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
                    Labelled Data Database
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       SpOC                                   │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│   │ Generate     │───▶│ Evaluate     │───▶│ Report &     │  │
│   │ Benchmarks   │    │ Algorithms   │    │ Compare      │  │
│   └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Documentation Responsibilities

### SDA TAP Lab Documentation
- Data source access procedures
- Label definitions and criteria
- Data format specifications
- Storage procedures

### SpOC Documentation
- Benchmark dataset descriptions
- Evaluation metric definitions
- Algorithm submission guidelines
- Performance comparison reports

### Shared Documentation
- Overall system architecture
- API specifications
- Integration procedures
- User guides

---

## Contact and Coordination

Both teams coordinate through:
- Regular sync meetings
- Shared code repository
- Documentation in this folder
- Apollo Accelerator program structure

The partnership leverages industry best practices summarized in "50 Years of Data Science" as the Common Task Framework (Donoho, 2017).
