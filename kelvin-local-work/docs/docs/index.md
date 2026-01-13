# UCT Benchmark Documentation

## Project Overview

A framework for UCT (Uncorrelated Track) benchmark dataset generation and UCTP (UCT Processing) algorithm evaluation, developed as part of the SDA TAP Lab initiative.

## Team Structure

This codebase is **shared between two teams**:

| Team | Primary Focus |
|------|---------------|
| **SDA TAP Lab** | Labelling & Data Storage |
| **SpOC** | Benchmark Dataset Generation & Evaluation Criteria |

**Note:** During Semester 1 (Fall 2025), both teams functioned as one unified team. In Semester 2 (Spring 2026), teams are splitting responsibilities while continuing to share the same codebase.

## Pipeline Overview

The project implements a 3-phase pipeline:

1. **Phase 1 - Create_Dataset.py**: Dataset creation from UDL data
2. **Phase 2 - MainMVP.py**: UCTP algorithm simulation
3. **Phase 3 - Evaluation.py**: Performance evaluation and metrics

## Quick Links

- [Getting Started](getting-started.md) - Setup and installation
- [Consistency Audit Report](CONSISTENCY_AUDIT_REPORT.md) - Documentation review findings
- [Issues Backlog](ISSUES_BACKLOG.md) - Known issues to address

## Repository Structure

```
SDA-TAP-SpOC/
├── kelvin-local-work/   # Kelvin's active development
│   ├── docs/            # Created documentation (this site)
│   ├── src/             # Legacy source code
│   ├── uct_benchmark/   # Main Python package
│   └── data/            # Data directories
│
├── documentation/       # Provided documentation (NOT created by us)
│   ├── SDA-Project.pdf
│   ├── SpOC-Project.pdf
│   ├── UCT Benchmarking/
│   └── SDA x SpOC UCT Processing/
│
└── external-code/       # Reference code from other branches/sources
    ├── master/
    ├── jovan-linuxTesting/
    └── uct-benchmark-refactor-joncline/
```

## Commands

The Makefile contains the central entry points for common tasks:

```bash
make requirements  # Install dependencies
make format        # Run code formatting
make test          # Run test suite
```

## Data Sources

- **UDL (Unified Data Library)** - Primary source for satellite observation data
- Requires UDL API token for access

## Framework Reference

This project follows the **Common Task Framework** as defined in Donoho's 2017 paper "50 Years of Data Science":

1. Provide training data set
2. Define common prediction task
3. Define benchmark metrics, evaluate submissions
