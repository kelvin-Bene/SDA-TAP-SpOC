# Blake's Local Work - UCT Benchmark Enhancements

This folder contains comprehensive enhancements to the UCT (Uncorrelated Tracks) Benchmarking system, including:

1. **Database & Data Storage Architecture** - DuckDB-based storage layer
2. **UCT Benchmarking Enhancement** - Physics-based simulation, improved downsampling, enhanced API

**Author:** Blake Mister
**Date:** January 2026
**Branch:** `blakes-local-work`

---

# Part 1: Database & Data Storage Architecture

This implementation provides a robust database layer using DuckDB for the UCT Benchmarking project. It enables efficient storage, querying, and management of space surveillance data including satellite observations, state vectors, TLEs, and event labels.

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

---

# Part 2: UCT Benchmarking Enhancement

Comprehensive enhancements to the UCT Benchmarking system with improved UDL data access, physics-based downsampling, advanced simulation models, and flexible dataset generation.

## Implementation Summary

### Phase 1: API Enhancements

**File:** `uct_benchmark/api/apiIntegration.py`

| Feature | Description |
|---------|-------------|
| Response Caching | `QueryCache` class with TTL-based caching to reduce redundant API calls |
| Count-First Strategy | `smart_query()` checks record count before fetching, splits large queries |
| Adaptive Batch Sizing | `get_batch_size_for_regime()` uses regime-specific time windows |
| New Service Wrappers | `queryRadarObservations()`, `queryRFObservations()`, `queryConjunctions()`, `queryManeuvers()` |
| Parallel Queries | `pullComprehensiveData()` for concurrent multi-service data fetching |
| API Logging | `_log_api_call()`, `get_api_metrics()` for performance tracking |
| Maneuver Flags | `addManeuverFlags()` to flag observations near detected maneuvers |

### Phase 2: Downsampling Improvements

**File:** `uct_benchmark/data/dataManipulation.py`

| Feature | Description |
|---------|-------------|
| Regime Detection | `determine_orbital_regime()` classifies LEO/MEO/GEO/HEO based on SMA and eccentricity |
| Track Identification | `identify_tracks()` groups observations into pseudo-tracks using 90-min gap criterion |
| Track Preservation | `thin_within_tracks()` preserves first/last observations for OD quality |
| Regime-Specific Profiles | `DOWNSAMPLING_PROFILES` dict with LEO/MEO/GEO/HEO parameters |
| 3D Coverage | `compute_3d_coverage()` uses arc-length instead of 2D polygon area |

### Phase 3: Simulation Enhancements

**New Files:** `uct_benchmark/simulation/atmospheric.py`, `uct_benchmark/simulation/noise_models.py`

| Feature | Description |
|---------|-------------|
| Atmospheric Refraction | Bennett's formula with temperature, pressure, and chromatic corrections |
| Velocity Aberration | Classical aberration correction for observer/satellite motion |
| Sensor Noise Models | `OpticalNoiseModel`, `RadarNoiseModel`, `RFNoiseModel` classes |
| GEODSS, SBSS, Commercial | Pre-defined noise parameters for major sensor types |
| Photometric Simulation | `simulate_magnitude()` with Lambertian phase function |
| Illumination Check | `is_satellite_illuminated()` for eclipse detection |

### Phase 4: Dataset Configuration System

**New Files:** `uct_benchmark/config.py` (enhanced), `uct_benchmark/config/dataset_schema.py`

| Feature | Description |
|---------|-------------|
| Configuration Dataclasses | `APIConfig`, `DownsampleConfig`, `SimulationConfig`, `DatasetConfig`, `LoggingConfig` |
| Enhanced Dataset Codes | Format: `HAMR_LEO_MAN_EO_T2S_07D_001` |
| YAML Configuration | `load_dataset_config()` and `save_dataset_config()` |
| Metadata Generation | `generate_dataset_metadata()` with config hash and stats |
| Reproducibility | `verify_reproducibility()` for dataset verification |

### Phase 5: Logging & Monitoring

**New File:** `uct_benchmark/logging_config.py`

| Feature | Description |
|---------|-------------|
| Structured Logging | `setup_logging()` with file rotation and retention |
| Metrics Collection | `MetricsCollector` class for API calls and processing stats |
| Performance Timing | `PerformanceTimer` context manager |
| Log Analysis | `parse_api_log()` and `summarize_api_performance()` |

## Enhanced File Structure

```
blakes-local-work/
├── README.md                          # This file
├── CHANGELOG.md                       # Detailed change history
├── DATABASE_ARCHITECTURE.md           # Database technical spec
├── docs/
│   └── IMPLEMENTATION_DETAILS.md      # UCT enhancement details
├── uct_benchmark/
│   ├── config.py                      # Enhanced configuration dataclasses
│   ├── logging_config.py              # Structured logging setup
│   ├── api/
│   │   └── apiIntegration.py          # Enhanced API with caching, logging
│   ├── config/
│   │   ├── __init__.py
│   │   └── dataset_schema.py          # YAML config and metadata
│   ├── data/
│   │   └── dataManipulation.py        # Track-preserving downsampling
│   ├── database/                      # Database module
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── schema.py
│   │   ├── repository.py
│   │   ├── export.py
│   │   ├── ingestion.py
│   │   └── cli.py
│   └── simulation/
│       ├── simulateObservations.py    # Enhanced simulation
│       ├── atmospheric.py             # Refraction & aberration
│       └── noise_models.py            # Sensor noise & photometry
└── tests/
    ├── test_database.py               # Database tests
    ├── test_api_enhancements.py       # API enhancement tests
    ├── test_downsampling_enhancements.py
    ├── test_simulation_enhancements.py
    └── test_dataset_config.py
```

## Usage Examples

### API with Caching and Logging

```python
from uct_benchmark.api.apiIntegration import smart_query, pullComprehensiveData

# Smart query with automatic count-first and caching
obs = smart_query(token, 'eoobservation', {
    'satNo': '25544',
    'obTime': '>now-7 days',
})

# Parallel multi-service query
data = pullComprehensiveData(
    token, [25544, 48274], '>now-7 days',
    services=['eoobservation', 'radarobservation', 'statevector']
)
```

### Regime-Specific Downsampling

```python
from uct_benchmark.data.dataManipulation import downsample_by_regime
from uct_benchmark.config import DownsampleConfig

config = DownsampleConfig(
    target_coverage=0.05,
    target_gap=2.0,
    preserve_track_boundaries=True,
    seed=42,
)
downsampled = downsample_by_regime(obs_df, sat_params, config)
```

### Physics-Based Simulation

```python
from uct_benchmark.simulation.simulateObservations import simulateObsEnhanced
from uct_benchmark.config import SimulationConfig

config = SimulationConfig(
    apply_atmospheric_refraction=True,
    apply_velocity_aberration=True,
    apply_sensor_noise=True,
    sensor_model='GEODSS',
    simulate_magnitude=True,
)
simulated_obs = simulateObsEnhanced(tle_line1, tle_line2, 3600, sensors_df, sim_config=config)
```

## Running Tests

```bash
cd blakes-local-work
pytest tests/ -v
```

## Key Design Decisions

1. **Multi-Phenomenology Support**: Both combined (EO + Radar) and separate dataset modes
2. **Maneuver Event Flags**: Observations flagged within N hours of detected maneuvers
3. **Simulation Priority**: Sensor noise (highest), refraction (second), photometry (third)
4. **TLE Selection**: Support for both historical and current TLEs
