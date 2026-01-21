# Project Planning Documentation

## Overview

This folder contains detailed planning documents for the SDA TAP Lab and SpOC UCT Benchmarking project. The plans are organized by team responsibility and include current status assessments, task breakdowns, and an integrated roadmap.

---

## V1 Fixes (Current Sprint Priority)

Based on the initial meeting with tech lead Lewis (August 28, 2025), the following documents guide V1 completion:

| Document | Purpose |
|----------|---------|
| **[V1_FIXES_MASTER_PLAN.md](./V1_FIXES_MASTER_PLAN.md)** | Comprehensive plan with full details, rationale, code examples, and Lewis quotes |
| **[V1_ACTION_CHECKLIST.md](./V1_ACTION_CHECKLIST.md)** | Quick reference checklist for tracking daily progress |

### V1 Priority Summary
| Priority | Focus | Status |
|----------|-------|--------|
| **P0** | UCTP Validation with Aerospace Corp (Patrick Ramsey) | Not Started |
| **P1** | Complete T1-T4 tier processing (downsampling + simulation) | **75%** - T1/T2/T3 ✅ Complete, T4 Not Started |
| **P2** | PDF report improvements + realistic noise modeling | Not Started |
| **P3** | Event labeling integration + performance optimization | Not Started |
| **P4** | Open Evolve architecture (stretch goal) | Not Started |

### Recent Progress (2026-01-18)
- ✅ **T3 Simulation**: Fully implemented - epochsToSim() rewritten, integrated
- ✅ **T1/T2 Downsampling**: Fully integrated into pipeline
- ✅ **Pipeline Test**: End-to-end test created and passing (8/8 stages)
- ✅ **Simulation Test**: test_simulation.py created and passing (3/3 tests)
- ✅ **Bug Fixes**: Fixed issues in generatePDF.py and dataManipulation.py

---

## Document Index

| Document | Description |
|----------|-------------|
| [V1 Fixes Master Plan](./V1_FIXES_MASTER_PLAN.md) | **START HERE** - Comprehensive V1 completion plan |
| [V1 Action Checklist](./V1_ACTION_CHECKLIST.md) | Quick checklist for tracking progress |
| [Project Status](./PROJECT_STATUS.md) | Current state of all components - what's done vs pending |
| [SDA TAP Lab Plan](./SDA_TAP_LAB_PLAN.md) | Detailed plan and TODO list for SDA TAP Lab team |
| [SpOC Plan](./SPOC_PLAN.md) | Detailed plan and TODO list for SpOC team |
| [Integrated Roadmap](./INTEGRATED_ROADMAP.md) | Combined project roadmap with milestones |
| [Dependencies](./DEPENDENCIES.md) | Inter-team dependencies and handoff points |

## Team Responsibilities Summary

### SDA TAP Lab: Labelling & Data Storage
- Data source integration and API development
- Event labelling (launch, maneuver, proximity, breakup)
- Data parsing and extraction
- Centralized database development
- Data quality and storage

### SpOC: Benchmark Dataset Generation & Evaluation
- Benchmark dataset generation from stored data
- Evaluation criteria and metrics
- Algorithm interface development
- Web UI for algorithm developers
- Reporting and comparison systems

## Project Goal

Build a Web-hosted User Interface where algorithm developers can:
1. Generate and download benchmark datasets for UCT Processing
2. Train their algorithms on standardized data
3. Upload results to be objectively evaluated
4. Compare performance against other solutions

## Quick Reference: Current Priority Items

### SDA TAP Lab Priorities
1. Complete event labelling system
2. Implement T3/T4 data simulation
3. Build centralized database
4. Add multi-dataset support

### SpOC Priorities
1. Complete evaluation pipeline
2. Build Web UI framework
3. Implement algorithm submission interface
4. Create leaderboard system
