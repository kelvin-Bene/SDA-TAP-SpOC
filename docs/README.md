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
├── docs/                          # This documentation folder
├── UCT Benchmarking/              # Learning materials and resources
│   ├── Documentation/             # Project documentation (legacy)
│   ├── Learning Docs/             # Educational materials
│   ├── UCT Papers/                # Research papers
│   ├── Data Resources/            # Data source information
│   └── Measurement Simulation/    # Sensor simulation data
├── SDA x SpOC UCT Processing/     # SpOC team documentation
│   ├── Documentation(s)/          # Setup guides and demos
│   └── UDL Queries/               # Sample UDL query results
└── uct-benchmark-refactor-joncline/  # Main codebase
    ├── src/                       # Legacy source code
    ├── uct_benchmark/             # Refactored module
    │   ├── api/                   # API integrations
    │   ├── data/                  # Data manipulation
    │   ├── evaluation/            # Metrics and evaluation
    │   ├── simulation/            # Orbit propagation
    │   ├── uctp/                  # UCTP implementations
    │   └── utils/                 # Utility functions
    └── tests/                     # Test files
```

## Quick Start

1. Review the [Team Roles](./TEAM_ROLES.md) to understand project responsibilities
2. Read the [Pipeline Overview](./PIPELINE.md) to understand data flow
3. Check the [Architecture](./ARCHITECTURE.md) for code structure
4. See the setup guides in `SDA x SpOC UCT Processing/Documentation(s)/`

## Current Status

The project is in active development with the following major components:
- **Completed**: API integrations, window selection, basic scoring, evaluation metrics
- **In Progress**: Dataset tiering, data simulation, web UI
- **Planned**: Full CTF web interface, additional UCTP algorithm support

## Contributors

- SDA TAP Lab Team (Space Systems Command, USSF)
- Space Operations Command (SpOC) Team
- AFRL Summer 2025 Interns

## References

- Donoho, D. (2017). "50 Years of Data Science"
- SDA TAP Lab Website: sdataplab.org
