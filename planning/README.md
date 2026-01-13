# Project Planning Documentation

## Overview

This folder contains detailed planning documents for the SDA TAP Lab and SpOC UCT Benchmarking project. The plans are organized by team responsibility and include current status assessments, task breakdowns, and an integrated roadmap.

## Document Index

| Document | Description |
|----------|-------------|
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
