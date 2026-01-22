# SDA TAP Lab & SpOC UCT Processing Project Documentation

## Overview

This project is a collaborative effort between the **Space Domain Awareness (SDA) Tools, Applications, & Processing (TAP) Lab** and the **Space Operations Command (SpOC)** to develop a fully automated data annotation pipeline for processing Uncorrelated Tracks (UCTs) within the Common Task Framework (CTF).

### Project Mission

The SDA TAP Lab accelerates the delivery of space battle management software to operational units by:
- Decomposing kill chains
- Prioritizing needs with operators
- Mapping needs to technologies
- Onboarding technology to existing platforms

### Project Goal

Develop Labelling & Data Storage approaches for processing Uncorrelated Tracks (UCTs) in the Common Task Framework. The end result is a Web-hosted User Interface that algorithm developers can:
1. Generate and download benchmark datasets related to UCT processing
2. Train their algorithms on standardized data
3. Upload results to be objectively evaluated and compared

## Documentation Index

| Document | Description |
|----------|-------------|
| [Team Roles](./TEAM_ROLES.md) | Differences between SDA TAP Lab and SpOC responsibilities |
| [Pipeline Overview](./PIPELINE.md) | Complete data pipeline and flow documentation |
| [Architecture](./ARCHITECTURE.md) | Code architecture, modules, and logic |
| [Data Sources](./DATA_SOURCES.md) | Data sources and API integrations |
| [Evaluation Metrics](./EVALUATION_METRICS.md) | Metrics used for UCTP algorithm evaluation |
| [Configuration](./CONFIGURATION.md) | System configuration and thresholds |

## Key Concepts

### Space Domain Awareness (SDA)
Rapidly predict, detect, track, identify, warn, characterize, and attribute threats to U.S., commercial, allied, and partner space systems.

### Uncorrelated Tracks (UCTs)
Observation data that cannot be immediately associated with known catalogued objects. Processing UCTs is critical for:
- Detecting new objects (launches, debris from breakups)
- Tracking maneuvering satellites
- Identifying potentially hostile objects

### Common Task Framework (CTF)
A standardized methodology (based on Donoho's 2017 "50 Years of Data Science" paper) for:
- Creating benchmark datasets
- Evaluating algorithm performance
- Comparing solutions objectively

## Project Structure

```
SDA-TAP-SpOC/
├── UCT-Benchmark-DMR/combined/             # Primary active development
│   ├── uct_benchmark/             # Main Python package
│   │   ├── api/                   # API integrations (UDL, Space-Track, etc.)
│   │   ├── data/                  # Data manipulation and windowing
│   │   ├── evaluation/            # Metrics and evaluation
│   │   ├── simulation/            # Orbit propagation
│   │   ├── uctp/                  # UCTP implementations
│   │   └── utils/                 # Utility functions
│   ├── docs/                      # MkDocs documentation site
│   ├── data/                      # Data directories
│   └── src/                       # Legacy source code
│
├── docs/                          # Technical reference documentation
│   ├── ARCHITECTURE.md            # Code architecture
│   ├── PIPELINE.md                # Data pipeline flow
│   ├── TEAM_ROLES.md              # Team responsibilities
│   └── ...                        # Other technical docs
│
├── planning/                      # Project planning documents
│   ├── PROJECT_STATUS.md          # Current status
│   ├── INTEGRATED_ROADMAP.md      # Project roadmap
│   ├── SDA_TAP_LAB_PLAN.md        # SDA TAP team tasks
│   └── SPOC_PLAN.md               # SpOC team tasks
│
├── documentation/                 # Provided documentation (NOT created by us)
│   ├── SDA-Project.pdf            # Official SDA TAP Lab project brief
│   ├── SpOC-Project.pdf           # Official SpOC project brief
│   ├── UCT Benchmarking/          # Learning materials and resources
│   └── SDA x SpOC UCT Processing/ # Setup guides and demos
│
└── external-code/                 # Reference code from other branches
    ├── master/                    # Original master branch
    ├── jovan-linuxTesting/        # Linux testing branch
    └── uct-benchmark-refactor-joncline/  # Refactored codebase (reference)
```

## Quick Start

1. Review the [Team Roles](./TEAM_ROLES.md) to understand project responsibilities
2. Read the [Pipeline Overview](./PIPELINE.md) to understand data flow
3. Check the [Architecture](./ARCHITECTURE.md) for code structure
4. See the setup guides in `documentation/SDA x SpOC UCT Processing/Documentation(s)/`

## Current Status (January 2026)

**Overall Progress: ~60% toward final Web-hosted CTF platform**

| Phase | Status | Progress |
|-------|--------|----------|
| Foundation (APIs, Evaluation, Propagators) | Complete | 95% |
| Data Pipeline (T1-T3 Downsampling/Simulation) | Complete | 85% |
| Database (DuckDB) | Complete | 100% |
| Web Platform (React UI, FastAPI Backend) | Complete | 95% |
| Algorithm Framework (Submission, Leaderboard) | In Progress | 60% |

**Completed:**
- API integrations (UDL, Space-Track, CelesTrak, ESA DiscoWeb)
- Window selection algorithm
- Dataset categorization system (tiers T1-T5)
- Evaluation metrics (binary, state, residual)
- Orbit propagators (Monte Carlo, Ephemeris, TLE)
- T1/T2 downsampling pipeline
- T3 observation simulation
- DuckDB database with repository pattern
- React + Vite + shadcn/ui frontend
- FastAPI backend with REST endpoints

**In Progress:**
- T4 tier processing (synthetic object simulation)
- Event labelling system (launch, maneuver, proximity detection)
- Leaderboard ranking algorithm

**Not Started:**
- User authentication (OAuth/JWT)
- Full production deployment

## Contributors

- SDA TAP Lab Team (Space Systems Command, USSF)
- Space Operations Command (SpOC) Team
- AFRL Summer 2025 Interns

## References

- Donoho, D. (2017). "50 Years of Data Science"
- SDA TAP Lab Website: sdataplab.org
