# Generated Documentation

This folder contains **all documentation created by the project team** for the UCT Benchmark project.

## Structure

```
generated-docs/
├── docs/
│   ├── index.md                 # Home page
│   ├── getting-started.md       # Quick start guide
│   ├── technical/               # Technical reference documentation
│   │   ├── ARCHITECTURE.md      # Code architecture and modules
│   │   ├── PIPELINE.md          # Data pipeline flow
│   │   ├── DATA_SOURCES.md      # API integrations
│   │   ├── CONFIGURATION.md     # System configuration
│   │   ├── EVALUATION_METRICS.md # Evaluation metrics
│   │   └── TEAM_ROLES.md        # Team responsibilities
│   ├── planning/                # Project planning documents
│   │   ├── PROJECT_STATUS.md    # Current status assessment
│   │   ├── INTEGRATED_ROADMAP.md # Project roadmap
│   │   ├── DEPENDENCIES.md      # Inter-team dependencies
│   │   ├── SDA_TAP_LAB_PLAN.md  # SDA TAP Lab tasks
│   │   └── SPOC_PLAN.md         # SpOC tasks
│   └── reports/                 # Analysis reports
│       ├── TEAM_SPLIT_READINESS.md      # Team split analysis
│       ├── CONSISTENCY_AUDIT_REPORT.md  # Codebase audit
│       ├── DOCUMENTATION_CONSISTENCY_REVIEW.md # Doc review
│       └── ISSUES_BACKLOG.md    # Known issues
└── mkdocs.yml                   # MkDocs configuration
```

## Building the Documentation Site

This folder is configured as a MkDocs site. To build and view:

```bash
cd generated-docs
pip install mkdocs mkdocs-material
mkdocs serve
```

Then open http://localhost:8000 in your browser.

## Key Documents

| Document | Description |
|----------|-------------|
| [Team Split Readiness](docs/reports/TEAM_SPLIT_READINESS.md) | Analysis of what's needed before teams can work independently |
| [Project Status](docs/planning/PROJECT_STATUS.md) | Current state of all components |
| [Architecture](docs/technical/ARCHITECTURE.md) | Code structure and modules |
| [Pipeline](docs/technical/PIPELINE.md) | Complete data flow documentation |

## Document Categories

### Technical Reference (`docs/technical/`)
Detailed technical documentation about the codebase, APIs, and system architecture.

### Project Planning (`docs/planning/`)
Project management documents including status, roadmaps, and team-specific plans.

### Project Reports (`docs/reports/`)
Analysis reports and audits produced during the project.
