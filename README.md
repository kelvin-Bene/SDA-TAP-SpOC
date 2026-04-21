# SDA TAP Lab & UCT Benchmark Project

A collaborative project between the **Space Domain Awareness (SDA) Tools, Applications, & Processing (TAP) Lab** and the **Combat Forces Command (CFC)** to develop a fully automated data annotation pipeline for processing Uncorrelated Tracks (UCTs) within the Common Task Framework (CTF).

> **Naming note**: The platform was originally scoped as "SpOC UCT Processing" (Space Operations Command). The v2.0.0 rebrand (Apr 2026) renamed the platform to **UCT Benchmark** under the **Combat Forces Command (CFC)** banner. Both names appear in older docs — they refer to the same project.

## Repository Structure

This repository is organized into **4 clear folders**:

```
SDA-TAP-SpOC/
│
├── UCT-Benchmark-DMR/combined/  # YOUR CODE - Active development
├── generated-docs/              # OUR DOCUMENTATION - Created by the team
├── provided-materials/          # GIVEN TO US - Reference materials and briefs
└── reference-code/              # OTHERS' CODE - Previous implementations
```

---

## Quick Navigation

| Folder | What's Inside | When to Use |
|--------|---------------|-------------|
| [`UCT-Benchmark-DMR/combined/`](./UCT-Benchmark-DMR/combined/) | Active Python codebase | **Develop here** |
| [`generated-docs/`](./generated-docs/) | All project documentation | Read docs, build MkDocs site |
| [`provided-materials/`](./provided-materials/) | Official briefs, learning materials | Reference only |
| [`reference-code/`](./reference-code/) | Code from master, jovan, joncline branches | Feature reference |

---

## Folder Details

### 1. `UCT-Benchmark-DMR/combined/` - Active Development
**This is where all new code development happens.**

```
UCT-Benchmark-DMR/combined/
├── uct_benchmark/          # Main Python package
│   ├── api/                # API integrations (UDL, Space-Track, etc.)
│   ├── data/               # Data manipulation and windowing
│   ├── database/           # DuckDB storage layer
│   ├── evaluation/         # Metrics and evaluation
│   ├── simulation/         # Orbit propagation
│   └── uctp/               # UCTP implementations
├── backend_api/            # FastAPI backend
├── frontend/               # React web application
├── data/                   # Data directories
├── notebooks/              # Jupyter notebooks
└── tests/                  # Test files
```

### 2. `generated-docs/` - Project Documentation
**All documentation created by the team** - technical reference, planning, and reports.

```
generated-docs/
├── docs/
│   ├── technical/          # Architecture, Pipeline, APIs, Database
│   ├── planning/           # Status, Roadmap, Team Plans
│   ├── reports/            # Changelog, Audits, Issues
│   ├── guides/             # User guides and tutorials
│   └── reference/          # Glossary, provided materials index
└── mkdocs.yml              # Build docs with: mkdocs serve
```

**Key documents:**
- [Getting Started](./generated-docs/docs/getting-started.md) - Installation and setup guide
- [Project Status](./generated-docs/docs/planning/PROJECT_STATUS.md) - Current state of all components
- [Architecture](./generated-docs/docs/technical/ARCHITECTURE.md) - Code structure overview
- [Vision Alignment Audit](./generated-docs/docs/reports/VISION_ALIGNMENT_AUDIT.md) - How the implementation maps to Louis Caves's transcripts (authoritative)
- [Backlog](./UCT-Benchmark-DMR/combined/BACKLOG.md) - Deferred work tracked against Louis's vision
- [Changelog](./UCT-Benchmark-DMR/combined/CHANGELOG.md) - Release history

### 3. `provided-materials/` - Reference Materials
**Materials provided to us** - do not modify.

```
provided-materials/
├── SDA-Project.pdf         # Official SDA TAP Lab project brief
├── SpOC-Project.pdf        # Official SpOC project brief
├── SpOC-SDA-Description.pdf
├── SDA x SpOC UCT Processing/   # Setup guides
└── UCT Benchmarking/            # Learning materials, papers
```

### 4. `reference-code/` - Previous Implementations
**Code from other branches** - preserved for reference.

```
reference-code/
├── master/                 # Original implementation
├── jovan-linuxTesting/     # DuckDB, Polars, Linux automation
└── uct-benchmark-refactor-joncline/  # Refactored architecture
```

---

## Project Goal

Build a **Web-hosted User Interface** where algorithm developers can:
1. Generate and download benchmark datasets for UCT Processing
2. Train their algorithms on standardized data
3. Upload results to be objectively evaluated
4. Compare performance against other solutions

---

## Team Responsibilities

| Team | Focus | Key Deliverables |
|------|-------|------------------|
| **SDA TAP Lab** | Labelling & Data Storage | UDL data pulling, Event labelling, Centralized database |
| **SpOC** | Benchmark & Evaluation | Web UI, Algorithm submission, Leaderboard |

---

## Current Status (April 2026)

**Overall Progress: ~90%** — v2.0.2 deployed to production on Railway.

| Phase | Status | Progress |
|-------|--------|----------|
| Foundation (APIs, Evaluation, Propagators) | Complete | 95% |
| Data Pipeline (T1-T3, Downsampling, Database) | Complete | 85% |
| Web Platform (UI, Backend, Auth) | Complete | 95% |
| Production Deployment (Railway, Docker, NGINX) | Live | 95% |
| Composite Scoring + 3D Globe UI | Complete | 90% |
| Event Labelling | Infrastructure only | 15% |

**First completed submission in prod history** landed 2026-04-17 (submission 44 against dataset 158, `composite_score=1.0`). 79/79 end-to-end tests green on desktop-auth + mobile-safari-auth.

See [Project Status](./generated-docs/docs/planning/PROJECT_STATUS.md), [Vision Alignment Audit](./generated-docs/docs/reports/VISION_ALIGNMENT_AUDIT.md), and [Backlog](./UCT-Benchmark-DMR/combined/BACKLOG.md) for detailed breakdowns.

### Production URLs

- **Frontend**: https://frontend-production-6d80.up.railway.app
- **Backend**: https://backend-production-4b02.up.railway.app (`/health` for status)

Auto-deploys from `master` via GitHub Actions. See [DEPLOYMENT.md](./UCT-Benchmark-DMR/combined/DEPLOYMENT.md) for the full pipeline.

---

## Getting Started

1. **Review documentation:** Start with [`generated-docs/`](./generated-docs/)
2. **Set up development:** Follow the [Getting Started Guide](./generated-docs/docs/getting-started.md)
3. **Understand the pipeline:** Read [Pipeline Overview](./generated-docs/docs/technical/PIPELINE.md)
4. **Check team tasks:** See [SDA TAP Plan](./generated-docs/docs/planning/SDA_TAP_LAB_PLAN.md) or [SpOC Plan](./generated-docs/docs/planning/SPOC_PLAN.md)

---

## Building Documentation Site

```bash
cd generated-docs
pip install mkdocs mkdocs-material
mkdocs serve
```

Then open http://localhost:8000

---

## Running the Application

### Backend API
```bash
cd UCT-Benchmark-DMR/combined
uvicorn backend_api.main:app --reload --port 8000
```

### Frontend
```bash
cd UCT-Benchmark-DMR/combined/frontend
npm install
npm run dev
```

Access the application at http://localhost:3000 (frontend dev server — see `frontend/vite.config.ts`).

---

## Contributors

- SDA TAP Lab Team (Space Systems Command, USSF)
- Space Operations Command (SpOC) Team
- AFRL Summer 2025 Interns
