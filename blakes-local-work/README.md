# Blake's Local Work - UCT Benchmark Database Module

This folder contains the Database & Data Storage Architecture implementation for the UCT Benchmark project.

## Overview

This implementation provides a robust database layer using DuckDB for the UCT (Uncorrelated Track) Benchmarking project. It enables efficient storage, querying, and management of space surveillance data including satellite observations, state vectors, TLEs, and event labels.

## Key Features

- **DuckDB-based storage** - Zero-config, cross-platform, excellent SQL support
- **Repository pattern** - Clean data access abstraction
- **Hybrid storage strategy** - DuckDB + Parquet + JSON for optimal performance
- **Dataset versioning** - Track dataset versions and compare them
- **CLI interface** - Command-line tools for database management
- **Backward compatible** - Opt-in design, existing workflows unchanged

## Directory Structure

```
blakes-local-work/
├── README.md                 # This file
├── CHANGELOG.md              # Detailed change history
├── DATABASE_ARCHITECTURE.md  # Technical architecture documentation
├── uct_benchmark/
│   └── database/             # Database module
│       ├── __init__.py       # Module exports
│       ├── connection.py     # DuckDB connection management
│       ├── schema.py         # Table definitions
│       ├── schema.sql        # Standalone SQL reference
│       ├── repository.py     # Data access repositories
│       ├── export.py         # JSON/Parquet export utilities
│       ├── ingestion.py      # Data ingestion pipeline
│       ├── cli.py            # Command-line interface
│       └── __main__.py       # Module entry point
└── tests/
    ├── __init__.py
    └── test_database.py      # Unit tests (43 test cases)
```

## Installation

The database module is part of the uct_benchmark package. To use it:

```python
from uct_benchmark.database import DatabaseManager

# Initialize database
db = DatabaseManager()
db.initialize()

# Use repositories
satellites = db.satellites.get_all()
observations = db.observations.get_by_satellite_time_window(25544, start, end)
```

## CLI Usage

```bash
# Initialize the database
uv run python -m uct_benchmark.database init

# Check database status
uv run python -m uct_benchmark.database status

# List all datasets
uv run python -m uct_benchmark.database list

# Export a dataset to JSON
uv run python -m uct_benchmark.database export --dataset-id 1 -o output.json

# Create a backup
uv run python -m uct_benchmark.database backup

# Verify schema integrity
uv run python -m uct_benchmark.database verify
```

## Database Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `satellites` | Satellite catalog (NORAD numbers, names, orbital regime) |
| `observations` | Time-series observation data (RA/Dec, timestamps) |
| `state_vectors` | Orbital state at epoch (position/velocity in J2000 ECI) |
| `element_sets` | TLE/element set data |
| `datasets` | Dataset metadata with versioning |
| `dataset_observations` | Many-to-many: observations in datasets |
| `dataset_references` | Truth data linking for datasets |
| `events` | Event labelling (launch, maneuver, proximity, etc.) |
| `event_types` | Event type definitions |

### Repositories

| Repository | Purpose |
|------------|---------|
| `SatelliteRepository` | Satellite catalog CRUD operations |
| `ObservationRepository` | Observation queries and bulk insert |
| `StateVectorRepository` | State vector management |
| `ElementSetRepository` | TLE/element set management |
| `DatasetRepository` | Dataset versioning, comparison, catalog |
| `EventRepository` | Event labelling (future feature) |

## Testing

Run the unit tests:

```bash
# Using pytest (may have import issues due to config circular import)
uv run pytest tests/test_database.py -v

# The module has been verified working with standalone tests
```

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | DuckDB | Already a dependency, zero-config, excellent SQL support |
| Integration | Optional (opt-in) | Backward compatible with existing workflows |
| Priority | Dataset Management First | Version control before raw storage |
| Storage | Hybrid | DuckDB for analytics, Parquet for bulk, JSON for API |

## Author

Blake Mister - 2026-01-19

## Related Documents

- See `DATABASE_ARCHITECTURE.md` for full technical specification
- See `CHANGELOG.md` for detailed change history
