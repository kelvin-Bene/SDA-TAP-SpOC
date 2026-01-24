# Planning Prompt: Space Data Sources Integration Strategy

## Instructions for Claude

You are helping plan data source integrations for the **SDA-TAP-SpOC UCT Benchmark** project. Your task is to analyze the research document and create a detailed implementation plan that maps each data source to **specific functional improvements** in the application.

**CRITICAL**: This is not about adding data for the sake of having more data. Every integration must directly improve one of the core functionalities listed below. If a data source doesn't clearly improve a core function, deprioritize it.

---

## Project Context

### What This Project Does

The UCT Benchmark project creates **standardized benchmark datasets** for testing **Uncorrelated Track Processing (UCTP)** algorithms. UCT processing is one of the most difficult problems in Space Domain Awareness (SDA).

From the project lead Lewis:
> "The UCT processor is not going to tell us 'Oh, we think this is this object.' It's just gonna say all of these observations are correlated with each other and this is the orbit the object is in. So we need to figure out which one of the candidate orbits that the UCT processor identified corresponds to which one of the reference objects that we put into the initial data set."

### The Core Problem Being Solved

When sensors observe space objects, tracks may fail to correlate to known orbits due to:
- **Camouflage, Concealment, Deception, and Maneuver (CCDM)** by adversaries
- Sensor limitations and gaps
- Poor data quality
- Unknown object characteristics

UCT processors must **quickly estimate an orbit with poor data and limited time**.

### Core Functionalities (From Lewis & Project Docs)

1. **Dataset Generation** - Create realistic benchmark datasets with:
   - Decorrelated observations (removed satellite IDs)
   - Reference ground truth for evaluation
   - Configurable difficulty tiers (T1-T4)
   - Multiple orbital regimes (LEO, MEO, GEO, HEO)

2. **Data Quality Scoring** - Assess observation quality based on:
   - Orbital coverage percentage
   - Observation count per time period
   - Track gaps (time between observations)
   - Object completeness

3. **Tier-Based Processing**:
   - T1/T2: High-quality data that needs downsampling to create challenge
   - T3: Data gaps filled with simulated observations
   - T4: Fully synthetic satellites (not yet implemented)

4. **Evaluation Metrics** - Compare UCTP algorithm output against ground truth:
   - **Binary Metrics**: Precision, Recall, F1-Score (did it correctly associate?)
   - **State Metrics**: Position/velocity errors (how accurate is the orbit?)
   - **Residual Metrics**: Observation fit quality (how well does orbit explain observations?)

5. **Orbit Association** - Match UCTP output to reference objects using:
   - Hungarian algorithm for optimal assignment
   - Euclidean norm in position/velocity space
   - Covariance consistency checking

---

## UCT Processing Challenges to Address

The benchmark must test algorithms against these real-world challenges (from project documentation):

| Challenge | Description | Data Needed |
|-----------|-------------|-------------|
| High area-to-mass ratio objects | Unpredictable drag/SRP effects | Physical properties (mass, area) |
| Long-duration low-thrust maneuvers | Orbit changes difficult to detect | Maneuver history data |
| Long periods between tracks | Sparse observation coverage | Multi-source observations |
| Very few tracks | Minimal data for orbit determination | High-confidence reference orbits |
| Small orbital arc observed | Limited geometry for IOD | Precision validation data |
| Objects in close angular space | "Cross-tag" mis-associations | High-resolution catalogs |
| Maneuvers during coverage gaps | Lost track correlation | Maneuver event databases |
| Optical-only limitation | No range data | Radar/laser ranging data |
| Unknown target characteristics | Can't model perturbations | Object characterization data |
| Poor sensor calibration | Systematic observation errors | Multi-sensor cross-validation |

---

## Research Document to Analyze

Read and analyze: `RESEARCH_SPACE_DATA_SOURCES.md`

This document contains research on these data sources:
- **EU SST** (European Space Surveillance and Tracking)
- **JSC Vimpel** (Russian space catalog)
- **SatNOGS** (Open-source ground station network)
- **ASTRIAGraph** (UT Austin multi-source aggregation)
- **GCAT** (Jonathan McDowell's comprehensive catalog)
- **ILRS** (International Laser Ranging Service)
- **UCS Satellite Database** (Operational satellite metadata)
- **TraCSS** (Upcoming US Dept of Commerce system)
- **NASA CARA Tools** (Conjunction risk algorithms)
- **LeoLabs** (Commercial radar tracking)
- **CORDS** (Aerospace Corporation reentry database)

---

## Your Planning Tasks

### Task 1: Functional Mapping

For EACH data source in the research document, answer:

1. **Which core functionality does this improve?** (Dataset Generation, Scoring, Evaluation, etc.)
2. **Which UCT challenge does this help test?** (From the table above)
3. **What specific data fields are useful?** (Not just "TLEs" - which fields specifically?)
4. **How does this make benchmarks more realistic?**
5. **What's the integration complexity?** (API available? Auth required? Data format?)

Format as a table:
```
| Data Source | Core Function Improved | UCT Challenge Addressed | Key Data Fields | Realism Benefit | Complexity |
```

### Task 2: Priority Ranking

Rank the data sources by impact on core functionality:

**HIGH PRIORITY** = Directly improves evaluation accuracy or dataset realism
**MEDIUM PRIORITY** = Provides useful supplementary data
**LOW PRIORITY** = Nice to have but doesn't address core challenges

For each priority level, explain WHY it has that ranking based on the functional requirements.

### Task 3: Implementation Sequences

Create implementation sequences that maximize value:

**Sequence A: Evaluation Accuracy**
Which sources should be integrated first to improve how accurately we can evaluate UCTP algorithms?

**Sequence B: Dataset Diversity**
Which sources help create more diverse and challenging benchmark datasets?

**Sequence C: Open-Source Compatibility**
Which sources have no authentication barriers and can be freely redistributed?

### Task 4: Architecture Recommendations

Based on the functional analysis:

1. **New API Functions Needed**: List specific functions to add to `apiIntegration.py`
2. **Database Schema Changes**: What new tables/columns support these sources?
3. **Evaluation Module Enhancements**: How do new sources improve metrics?
4. **Configuration Parameters**: What new settings are needed?

### Task 5: Validation Improvements

Lewis emphasized the project "still needs validation with actual UCT processor output."

How can the new data sources help with:
1. **Ground Truth Validation**: Better reference data for comparison
2. **Cross-Catalog Verification**: Confirming object identities across sources
3. **Covariance Calibration**: Improving uncertainty estimates
4. **Residual Analysis**: More observation sources for fit testing

---

## Output Format

Structure your response as:

```markdown
# Data Sources Integration Plan

## 1. Functional Mapping Table
[Table mapping each source to functions]

## 2. Priority Ranking
### High Priority
[Sources with justification]

### Medium Priority
[Sources with justification]

### Low Priority
[Sources with justification]

## 3. Implementation Sequences
### Sequence A: Evaluation Accuracy
[Ordered list with rationale]

### Sequence B: Dataset Diversity
[Ordered list with rationale]

### Sequence C: Open-Source Compatibility
[Ordered list with rationale]

## 4. Architecture Recommendations
### API Functions
[Specific function signatures]

### Database Schema
[Table definitions]

### Evaluation Enhancements
[Metric improvements]

### Configuration
[New parameters]

## 5. Validation Improvements
[How sources improve validation]

## 6. Recommended First Integration
[Single source to start with and why]
```

---

## Files to Reference

When creating your plan, reference these key files in the codebase:

- `UCT-Benchmark-DMR/combined/uct_benchmark/api/apiIntegration.py` - Current API integrations
- `UCT-Benchmark-DMR/combined/uct_benchmark/evaluation/` - Evaluation modules
- `UCT-Benchmark-DMR/combined/uct_benchmark/data/basicScoringFunction.py` - Data quality scoring
- `UCT-Benchmark-DMR/combined/uct_benchmark/database/` - Database schema
- `UCT-Benchmark-DMR/combined/uct_benchmark/settings.py` - Configuration
- `generated-docs/docs/technical/EVALUATION_METRICS.md` - Evaluation methodology
- `generated-docs/docs/technical/PIPELINE.md` - Pipeline architecture
- `provided-materials/UCT Benchmarking/Need for UCT Benchmarking.pdf` - Core requirements

---

## Remember

The goal is NOT to add every possible data source. The goal is to:

1. **Make benchmarks more realistic** - Test against real-world UCT challenges
2. **Improve evaluation accuracy** - Better ground truth = better algorithm comparison
3. **Support open-source distribution** - Data must be redistributable
4. **Minimize integration complexity** - Start with highest-value, lowest-effort sources

Every recommendation must trace back to a specific functional improvement.
