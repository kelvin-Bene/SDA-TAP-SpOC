# UCT Benchmark Documentation

Welcome to the project documentation for the SDA TAP Lab & SpOC UCT Processing project.

## Project Overview

A framework for UCT (Uncorrelated Track) benchmark dataset generation and UCTP (UCT Processing) algorithm evaluation, developed as part of the SDA TAP Lab initiative.

**Goal:** Build a Web-hosted User Interface where algorithm developers can generate benchmark datasets, train algorithms, and compare performance.

## Team Structure

This codebase is **shared between two teams**:

| Team | Primary Focus |
|------|---------------|
| **SDA TAP Lab** | Labelling & Data Storage |
| **SpOC** | Benchmark Dataset Generation & Evaluation Criteria |

**Note:** During Semester 1 (Fall 2025), both teams functioned as one unified team. In Semester 2 (Spring 2026), teams are splitting responsibilities.

## Documentation Sections

### Technical Reference
Detailed documentation about the codebase and system architecture.

- [Architecture](technical/ARCHITECTURE.md) - Code structure and modules
- [Pipeline](technical/PIPELINE.md) - Data flow documentation
- [Data Sources](technical/DATA_SOURCES.md) - API integrations
- [Database](technical/DATABASE.md) - DuckDB storage architecture
- [Frontend](technical/FRONTEND.md) - React web interface
- [Backend API](technical/BACKEND_API.md) - FastAPI integration
- [Configuration](technical/CONFIGURATION.md) - System settings
- [Evaluation Metrics](technical/EVALUATION_METRICS.md) - Scoring algorithms
- [Validation Suite](technical/VALIDATION.md) - Testing framework
- [Team Roles](technical/TEAM_ROLES.md) - Responsibilities breakdown

### User Guides
How-to guides for common tasks.

- [Getting Started](getting-started.md) - Installation and setup
- [Orekit Setup](guides/OREKIT_SETUP.md) - Windows Orekit configuration
- [Dataset Generation](guides/DATASET_GENERATION.md) - Creating datasets
- [Evaluation Guide](guides/EVALUATION_GUIDE.md) - Running evaluations
- [Web UI Guide](guides/UI_GUIDE.md) - Using the web interface

### Project Planning
Project management and planning documents.

- [Project Status](planning/PROJECT_STATUS.md) - Current state assessment
- [Integrated Roadmap](planning/INTEGRATED_ROADMAP.md) - Project timeline
- [Dependencies](planning/DEPENDENCIES.md) - Inter-team dependencies
- [SDA TAP Lab Plan](planning/SDA_TAP_LAB_PLAN.md) - SDA team tasks
- [SpOC Plan](planning/SPOC_PLAN.md) - SpOC team tasks

### Project Reports
Analysis reports and audits.

- [Changelog](reports/CHANGELOG.md) - Version history
- [Team Split Readiness](reports/TEAM_SPLIT_READINESS.md) - What's needed before teams split
- [Consistency Audit](reports/CONSISTENCY_AUDIT_REPORT.md) - Codebase review findings
- [Documentation Review](reports/DOCUMENTATION_CONSISTENCY_REVIEW.md) - Doc consistency check
- [Issues Backlog](reports/ISSUES_BACKLOG.md) - Known issues to address

### Reference
Reference materials and glossaries.

- [Glossary](reference/GLOSSARY.md) - UCT/SDA terminology
- [Provided Materials](reference/PROVIDED_MATERIALS_INDEX.md) - Index of PDFs and documents

## Repository Structure

```
SDA-TAP-SpOC/
├── UCT-Benchmark-DMR/combined/  # Active development codebase
├── generated-docs/              # This documentation (you are here)
├── provided-materials/          # Reference materials provided to us
└── reference-code/              # Code from other branches
```

## Pipeline Overview

The project implements a tiered pipeline system:

| Tier | Processing | Description |
|------|------------|-------------|
| T1 | Light Downsampling | Real data with optional thinning |
| T2 | Heavy Downsampling | Real data with significant gaps |
| T3 | Observation Simulation | Fill gaps with simulated observations |
| T4 | Object Simulation | Synthetic satellites (not implemented) |

### Core Components

1. **Create_Dataset.py**: Dataset creation from UDL data
2. **MainMVP.py**: UCTP algorithm simulation
3. **Evaluation.py**: Performance evaluation and metrics

## Current Status

**Overall Progress: ~85%** *(Updated 2026-01-25)*

| Phase | Status | Progress |
|-------|--------|----------|
| Foundation (APIs, Evaluation, Propagators) | Complete | 95% |
| Data Pipeline (T1-T3, Downsampling, Database) | Complete | 95% |
| Web Platform (UI, Backend, API) | Complete | 90% |
| Authentication | Not Started | 0% |

See [Project Status](planning/PROJECT_STATUS.md) for detailed breakdown.

## Quick Start

1. Clone the repository
2. Navigate to `UCT-Benchmark-DMR/combined/`
3. Follow the [Getting Started Guide](getting-started.md)
4. Review the [Architecture](technical/ARCHITECTURE.md)

## Framework Reference

This project follows the **Common Task Framework** as defined in Donoho's 2017 paper "50 Years of Data Science":

1. Provide training data set
2. Define common prediction task
3. Define benchmark metrics, evaluate submissions

## Future Direction: Open Evolve Integration

As discussed in the initial project meeting with tech lead Lewis, a key future goal is integrating with **Open Evolve** - a program for optimizing codebases using AI agents. The vision:

1. Use the evaluation script and benchmark datasets we're building
2. Have an LLM suggest modifications to UCT processors
3. Evaluate how well those edits performed using our metrics
4. Determine if AI agents can optimize uncorrelated track processors

This represents a potential "stretch goal" once the evaluation pipeline is fully validated.

## Key Contacts

- **Patrick Ramsey** (Aerospace Corp) - Key contact for UCTP validation. Has expressed interest in helping validate our software by running our datasets through their UCT processor.
- **Atulya** - Project coordinator for documentation and communication
