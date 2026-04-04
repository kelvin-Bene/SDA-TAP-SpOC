# AI Contributor Guide

<!-- AI_METADATA
purpose: Meta-documentation for AI agents (Claude Code) to understand and contribute to the UCT Benchmark project
status: active
related_files: [planning/PROJECT_STATUS.md, planning/FUTURE_IMPLEMENTATIONS.md, technical/ARCHITECTURE.md]
last_updated: 2026-02-03
-->

This guide helps AI agents (such as Claude Code) understand the UCT Benchmark project structure, find actionable tasks, and contribute effectively.

---

## 1. Project Overview for AI

### What UCT Benchmark Does

The UCT (Uncorrelated Track) Benchmark project creates **standardized benchmark datasets** for testing **Uncorrelated Track Processing (UCTP)** algorithms. UCT processing is one of the most difficult problems in Space Domain Awareness (SDA).

**The Core Challenge**: When sensors observe space objects, tracks may fail to correlate to known orbits. UCTP algorithms must:
1. Associate observations that belong together
2. Estimate orbits from sparse, noisy data
3. Match estimated orbits to known objects

**Our Solution**: Generate controlled benchmark datasets with known ground truth, then evaluate how well algorithms perform.

### Key Terminology

| Term | Definition |
|------|------------|
| **UCT** | Uncorrelated Track - observations not yet associated with a known object |
| **UCTP** | Uncorrelated Track Processing - algorithms that correlate and fit orbits |
| **Tier (T1-T5)** | Data quality classification determining required processing |
| **Downsampling** | Reducing data quality (T1/T2) to create challenge |
| **Simulation** | Generating synthetic observations (T3) or objects (T4) |
| **Decorrelation** | Removing satellite IDs from observations for blind testing |

### Project Components

```
1. Dataset Generation Pipeline
   - Pull real data from UDL, Space-Track, CelesTrak
   - Apply tier-based processing (downsampling or simulation)
   - Create decorrelated benchmark datasets

2. Evaluation System
   - Associate UCTP output with reference ground truth
   - Compute binary metrics (precision, recall, F1)
   - Compute state metrics (position/velocity errors)
   - Generate PDF reports

3. Web Platform
   - React frontend for dataset browsing
   - FastAPI backend for API access
   - Leaderboard for algorithm comparison
```

---

## 2. Repository Map

### Active Code (Work Here)

```
UCT-Benchmark-DMR/combined/
├── uct_benchmark/          # Main Python package
│   ├── api/                # API integrations (UDL, Space-Track, etc.)
│   ├── data/               # Data manipulation, windowing, scoring
│   ├── database/           # DuckDB storage layer
│   ├── evaluation/         # Metrics and evaluation algorithms
│   ├── simulation/         # Orbit propagation, observation simulation
│   ├── uctp/               # UCTP implementations (dummy processor)
│   └── settings.py         # Configuration parameters
├── backend_api/            # FastAPI backend
├── frontend/               # React web application
└── tests/                  # Test files
```

### Documentation (You Are Here)

```
generated-docs/docs/
├── index.md                # Documentation home
├── AI_CONTRIBUTOR_GUIDE.md # This file
├── technical/              # Architecture, pipeline, APIs
├── planning/               # Status, roadmap, team plans
├── guides/                 # User guides and tutorials
├── reports/                # Audits, changelogs, issues
├── reference/              # Glossary, materials index
└── archive/                # Historical/superseded documents
```

### Read-Only Reference

```
provided-materials/         # Official briefs, learning materials
reference-code/             # Code from other branches (historical)
```

---

## 3. Finding Actionable Tasks

### AI Task Markers

Search for these markers in documentation:

| Marker | Meaning | Action |
|--------|---------|--------|
| `AI_IMPROVEMENT_OPPORTUNITY` | Identified area for enhancement | Good starting point for contribution |
| `TODO` | Known incomplete item | Specific task to complete |
| `NEEDS_UPDATE` | Potentially outdated content | Review and update if needed |
| `Not Started (0%)` | Feature not implemented | Major development opportunity |

**Search commands**:
```bash
# Find improvement opportunities
grep -r "AI_IMPROVEMENT_OPPORTUNITY" generated-docs/

# Find TODOs in documentation
grep -r "TODO" generated-docs/

# Find not-started items
grep -r "Not Started" generated-docs/docs/planning/
```

### Key Planning Documents

| Document | Check For |
|----------|-----------|
| [PROJECT_STATUS.md](planning/PROJECT_STATUS.md) | Components with <100% completion |
| [FUTURE_IMPLEMENTATIONS.md](planning/FUTURE_IMPLEMENTATIONS.md) | Planned features not yet built |
| [ISSUES_BACKLOG.md](reports/ISSUES_BACKLOG.md) | Known bugs and technical debt |
| [DECISION_LOG.md](planning/DECISION_LOG.md) | Pending decisions needing input |

### High-Value Current Tasks

Based on project status as of 2026-02-03:

1. **Event Labeling System** (0% complete)
   - Location: New `uct_benchmark/labelling/` module
   - See: [FUTURE_IMPLEMENTATIONS.md](planning/FUTURE_IMPLEMENTATIONS.md#11-event-labeling-system)

2. **T4 Object Simulation** (0% complete)
   - Location: New `uct_benchmark/simulation/simulateObjects.py`
   - See: [FUTURE_IMPLEMENTATIONS.md](planning/FUTURE_IMPLEMENTATIONS.md#12-t4-object-simulation)

3. **Open Source Data Integration** (Not started)
   - Sources: GCAT, SatNOGS, ILRS
   - See: [DATA_SOURCE_RATIONALE.md](technical/DATA_SOURCE_RATIONALE.md)

4. **Authentication System** (0% complete)
   - Location: `backend_api/` and `frontend/`
   - See: [FUTURE_IMPLEMENTATIONS.md](planning/FUTURE_IMPLEMENTATIONS.md#31-authentication-system)

---

## 4. AI Task Marker System

When creating or editing documents, use these markers to help future AI agents:

### AI_METADATA Block

Place at the top of each document:

```markdown
<!-- AI_METADATA
purpose: Brief description of document's purpose
status: active|draft|archived
related_files: [path/to/file1.md, path/to/file2.py]
last_updated: YYYY-MM-DD
-->
```

### AI_SECTION Tags

Wrap related content blocks:

```markdown
<!-- AI_SECTION: section_name -->
Content that AI should parse as a coherent unit.
This helps with context extraction.
<!-- /AI_SECTION -->
```

### Improvement Opportunities

Mark areas where AI can add value:

```markdown
<!-- AI_IMPROVEMENT_OPPORTUNITY: Brief description of what could be improved -->
```

### TODOs and Updates Needed

```markdown
<!-- TODO: Specific task description -->
<!-- NEEDS_UPDATE: Reason content may be outdated -->
```

---

## 5. Key Files for Common Tasks

### Pipeline Modifications

| Task | Files to Modify |
|------|-----------------|
| Add data source | `uct_benchmark/api/apiIntegration.py` |
| Change scoring logic | `uct_benchmark/data/basicScoringFunction.py` |
| Modify downsampling | `uct_benchmark/data/dataManipulation.py` |
| Change simulation | `uct_benchmark/simulation/simulateObservations.py` |
| Update config | `uct_benchmark/settings.py` |

### Adding Data Sources

| Task | Files to Modify |
|------|-----------------|
| New API integration | `uct_benchmark/api/apiIntegration.py` |
| Database schema | `uct_benchmark/database/schema.py` |
| Ingestion pipeline | `uct_benchmark/database/ingestion.py` |
| Documentation | `generated-docs/docs/technical/DATA_SOURCES.md` |

### Evaluation Metrics

| Task | Files to Modify |
|------|-----------------|
| Binary metrics | `uct_benchmark/evaluation/binaryMetrics.py` |
| State metrics | `uct_benchmark/evaluation/stateMetrics.py` |
| Residual metrics | `uct_benchmark/evaluation/residualMetrics.py` |
| Orbit association | `uct_benchmark/evaluation/orbitAssociation.py` |
| Report generation | `uct_benchmark/utils/generatePDF.py` |

### Web UI Changes

| Task | Files to Modify |
|------|-----------------|
| Frontend components | `frontend/src/components/` |
| API routes | `backend_api/routers/` |
| State management | `frontend/src/stores/` |
| API models | `backend_api/models/` |

---

## 6. Current High-Value Tasks for AI

### Immediate Priorities

1. **GCAT Integration** (Quick Win)
   - Download TSV from https://planet4589.org/space/gcat/
   - Parse into database
   - Enrich satellite catalog
   - Effort: Low | Value: Medium

2. **ccsds-ndm Library Integration** (Quick Win)
   - Add `pip install ccsds-ndm` to dependencies
   - Create parser wrapper in `uct_benchmark/api/`
   - Enable standard CDM/ODM/OMM parsing
   - Effort: Low | Value: High

3. **Event Labeling Schema Design**
   - Define `EventType` enum
   - Design database schema for labels
   - Document label definitions
   - Location: `uct_benchmark/labelling/`
   - Effort: Medium | Value: High

### Medium-Term Tasks

4. **SatNOGS API Integration**
   - Add `satnogsQuery()` function
   - No auth required (fully open)
   - Real observation timestamps
   - Effort: Medium | Value: High

5. **T4 Object Simulation**
   - Generate realistic orbital elements
   - Create TLEs for synthetic objects
   - Integrate with existing simulation
   - Effort: High | Value: Medium

6. **Authentication System**
   - JWT-based auth for backend
   - Login/register UI components
   - Protected API routes
   - Effort: High | Value: Medium

---

## 7. Code Patterns and Conventions

### Python Style

- Type hints encouraged
- Docstrings for public functions
- Configuration via `settings.py`
- Logging via standard `logging` module

### Database Patterns

- DuckDB for analytical storage
- Repository pattern for data access
- Parquet export for sharing

### Frontend Patterns

- React functional components
- TypeScript for type safety
- Zustand for state management
- TailwindCSS for styling

### Testing

- pytest for Python tests
- Tests in `tests/` directory
- Test files named `test_*.py`

---

## 8. Getting Help

### Documentation Resources

- [ARCHITECTURE.md](technical/ARCHITECTURE.md) - Code structure
- [PIPELINE.md](technical/PIPELINE.md) - Data flow overview
- [PIPELINE_DEEP_DIVE.md](technical/PIPELINE_DEEP_DIVE.md) - Detailed algorithms
- [CONFIGURATION.md](technical/CONFIGURATION.md) - All settings
- [GLOSSARY.md](reference/GLOSSARY.md) - UCT/SDA terminology

### Project Context

- [PROJECT_STATUS.md](planning/PROJECT_STATUS.md) - What's done, what's not
- [INTEGRATED_ROADMAP.md](planning/INTEGRATED_ROADMAP.md) - Timeline
- [DECISION_LOG.md](planning/DECISION_LOG.md) - Why decisions were made

### For Contributors

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [getting-started.md](getting-started.md) - Setup instructions

---

## 9. Tips for AI Contributors

1. **Read before modifying** - Always read relevant files before suggesting changes
2. **Check PROJECT_STATUS.md** - Verify current implementation state
3. **Follow existing patterns** - Match code style of surrounding code
4. **Update documentation** - Keep docs in sync with code changes
5. **Add AI markers** - Help future AI agents find your improvements
6. **Test your changes** - Run existing tests, add new ones if needed
7. **Check DECISION_LOG** - Understand why things are done certain ways

---

*Created 2026-02-03 for AI agent onboarding*
