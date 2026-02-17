# System Architecture

## Overview

The UCT Benchmark project is a full-stack application for generating and evaluating Uncorrelated Track Processing (UCTP) benchmark datasets. The system consists of:

1. **Python Backend** - Dataset generation, orbit propagation, and evaluation
2. **FastAPI Backend** - REST API for web interface
3. **React Frontend** - Web-based user interface
4. **DuckDB Database** - Data storage and analytics

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UCT BENCHMARK SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         WEB INTERFACE                                │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │   │
│  │  │  React Frontend │  │  FastAPI Backend │  │  Database (DuckDB) │ │   │
│  │  │  (Vite/TS)      │─▶│  (REST API)      │─▶│  (Analytics)       │ │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │   │
│  │         Port 5173          Port 8000                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      PYTHON CORE LIBRARY                             │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│   │
│  │  │   api/      │  │   data/     │  │ simulation/ │  │ evaluation/ ││   │
│  │  │ API Clients │  │ Processing  │  │ Propagation │  │  Metrics    ││   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │  database/  │  │   uctp/     │  │   utils/    │                 │   │
│  │  │  Storage    │  │ Algorithms  │  │  Utilities  │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       EXTERNAL SERVICES                              │   │
│  │                                                                      │   │
│  │  ┌───────────┐  ┌─────────────┐  ┌───────────┐  ┌─────────────────┐│   │
│  │  │   UDL     │  │ Space-Track │  │ CelesTrak │  │  ESA DiscoWeb   ││   │
│  │  │   API     │  │    API      │  │    API    │  │      API        ││   │
│  │  └───────────┘  └─────────────┘  └───────────┘  └─────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

The main codebase is located in `UCT-Benchmark-DMR/combined/`:

```
UCT-Benchmark-DMR/combined/
├── uct_benchmark/              # Python package
│   ├── __init__.py
│   ├── settings.py             # Configuration and constants
│   ├── logging_config.py       # Logging configuration
│   │
│   ├── api/                    # External API integrations
│   │   ├── __init__.py
│   │   └── apiIntegration.py   # UDL, Space-Track, CelesTrak, ESA APIs
│   │
│   ├── config/                 # Configuration module
│   │   ├── __init__.py
│   │   └── dataset_schema.py   # Dataset code schema
│   │
│   ├── data/                   # Data manipulation and processing
│   │   ├── __init__.py
│   │   ├── basicScoringFunction.py  # Data quality scoring
│   │   ├── dataManipulation.py      # Data transformation utilities
│   │   ├── readData.py              # Data loading utilities
│   │   └── windowCheck.py           # Window selection algorithm
│   │
│   ├── database/               # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py       # DuckDB connection management
│   │   ├── schema.py           # Schema definitions (14+ tables)
│   │   ├── repository.py       # Data access layer
│   │   ├── export.py           # Export utilities
│   │   ├── ingestion.py        # Data ingestion pipeline
│   │   └── cli.py              # Command-line interface
│   │
│   ├── evaluation/             # Evaluation metrics and analysis
│   │   ├── __init__.py
│   │   ├── binaryMetrics.py    # Classification metrics
│   │   ├── evaluationReport.py # Report data structures
│   │   ├── orbitAssociation.py # Orbit matching algorithm
│   │   ├── residualMetrics.py  # Residual analysis
│   │   └── stateMetrics.py     # State comparison metrics
│   │
│   ├── simulation/             # Orbit propagation and simulation
│   │   ├── __init__.py
│   │   ├── gauss.py            # Gauss method for IOD
│   │   ├── orbitCoverage.py    # Orbital coverage calculation
│   │   ├── propagator.py       # Orbit propagators
│   │   ├── simulateObservations.py  # Observation simulation
│   │   ├── atmospheric.py      # Atmospheric refraction
│   │   ├── noise_models.py     # Sensor noise models
│   │   └── TLEGeneration.py    # TLE generation utilities
│   │
│   ├── uctp/                   # UCTP algorithm implementations
│   │   ├── __init__.py
│   │   └── dummyUCTP.py        # Test UCTP implementation
│   │
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── generateCov.py      # Covariance generation
│       ├── generatePDF.py      # PDF report generation
│       ├── timeSort.py         # Time sorting utilities
│       ├── timerClass.py       # Performance timing
│       └── unitConversion.py   # Unit conversion utilities
│
├── backend_api/                # FastAPI backend
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── models/                 # Pydantic models
│   ├── routers/                # API route handlers
│   │   ├── datasets.py         # Dataset management
│   │   ├── submissions.py      # Algorithm submissions
│   │   ├── results.py          # Evaluation results
│   │   ├── leaderboard.py      # Leaderboard API
│   │   └── jobs.py             # Background job status
│   └── jobs/                   # Background job processing
│
├── frontend/                   # React web application (45+ components)
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── pages/              # Page components
│   │   ├── stores/             # Zustand stores
│   │   └── types/              # TypeScript types
│   └── vite.config.ts
│
├── data/                       # Data directories
├── notebooks/                  # Jupyter notebooks
├── tests/                      # Test files
└── validation/                 # Validation suite
```

---

## Core Python Modules

### 1. API Integration (`api/apiIntegration.py`)

Central module for all external data source integrations.

#### UDL (Unified Data Library) Functions

```python
def UDLTokenGen(username, password) -> str:
    """Generate Base64 authentication token for UDL."""

def UDLQuery(token, service, params, count=False, history=False) -> DataFrame:
    """
    Perform synchronous UDL query.
    Services: eoobservation, statevector, elset, elset/current
    """

async def _asyncUDLQuery(token, service, params, count=False, history=False):
    """Async version for batch queries."""

def asyncUDLBatchQuery(token, service, params_list, dt=0.1) -> DataFrame:
    """Execute multiple UDL queries with rate limiting."""
```

#### Other Data Sources

```python
def spacetrackQuery(token, params, request="satcat") -> DataFrame:
    """Query Space-Track.org for TLE and catalog data."""

def discoswebQuery(token, params, data="objects") -> DataFrame:
    """Query ESA DiscoWeb for satellite physical properties."""

def celestrakQuery(params, table="gp") -> DataFrame:
    """Query CelesTrak for TLE and catalog data."""
```

#### Dataset Management

```python
def generateDataset(UDL_token, ESA_token, satIDs, timeframe, timeunit, ...) -> tuple:
    """Generate complete benchmark dataset from APIs."""

def saveDataset(ref_obs, ref_track, ref_sv, ref_elset, output_path) -> dict:
    """Save dataset to JSON format."""

def loadDataset(input_path) -> tuple:
    """Load dataset from JSON format."""
```

---

### 2. Window Selection (`data/windowCheck.py`)

Implements intelligent window selection for finding high-quality data windows.

```python
def windowMain(codes, UDL_token) -> list:
    """
    Main driver for window selection.
    Returns: List of tuples (code, threshold, bin_best, orbElems, metadata)
    """

def windowCheck(window_size, batch_size, code, start_epoch, end_epoch, UDL_token) -> tuple:
    """Sub-driver for finding best window for a single dataset code."""

def bisect(batch, window_size, thresh_des, code) -> tuple:
    """Recursively bisect data to find minimum-size valid sub-batch."""

def slide(sub_batch, window_size, code) -> tuple:
    """Slide window through sub-batch to find optimal position."""
```

---

### 3. Propagators (`simulation/propagator.py`)

High-fidelity orbit propagation using Orekit.

```python
def monteCarloPropagator(stateVector, covariance, initialEpoch, finalEpoch,
                         N=0, satelliteParameters=[...]) -> tuple:
    """
    Propagate state with covariance using Monte Carlo simulation.

    Force Model:
    - Earth gravity (120x120 harmonics)
    - Third body (Sun, Moon)
    - Atmospheric drag (NRLMSISE00)
    - Solar radiation pressure
    """

def ephemerisPropagator(stateVector, initialEpoch, finalEpoch,
                        satelliteParameters=[...]) -> list:
    """Propagate state to multiple epochs efficiently."""

def TLEpropagator(input1, input2, finalEpoch) -> tuple:
    """Propagate TLE using SGP4/SDP4."""
```

---

### 4. Orbit Association (`evaluation/orbitAssociation.py`)

Associates UCTP output with reference orbits.

```python
def orbitAssociation(truth, est, propagator, elset_mode=False) -> tuple:
    """
    Globally optimal orbit association using Hungarian algorithm.

    Process:
    1. Build cost matrix (n_est x n_truth)
    2. Propagate truth states to estimated epochs
    3. Compute position error for each pair
    4. Solve linear sum assignment
    5. Return associated and non-associated orbits
    """
```

---

### 5. Evaluation Metrics

#### Binary Metrics (`evaluation/binaryMetrics.py`)

```python
def binaryMetrics(ref_obs, associated_orbits) -> dict:
    """
    Returns: {
        'True Positives': int,
        'False Positives': int,
        'False Negatives': int,
        'Precision': float,
        'Recall': float,
        'F1-Score': float
    }
    """
```

#### State Metrics (`evaluation/stateMetrics.py`)

```python
def stateMetrics(ref_sv, associated_orbits, propagator) -> dict:
    """
    Returns: {
        'Position Error Mean': km,
        'Position Error Std': km,
        'Velocity Error Mean': km/s,
        'Velocity Error Std': km/s,
        'Mahalanobis Distance': unitless
    }
    """
```

---

### 6. Configuration (`settings.py`)

Centralized configuration parameters.

```python
# Path Configuration
PROJ_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJ_ROOT / "data"

# Orbital Regime Thresholds
semiMajorAxis_LEO = 8378    # km (altitude < 2000km)
semiMajorAxis_GEO = 42164   # km
eccentricity_HEO = 0.7

# Quality Thresholds
highPercentage = (0.9, 0.95, 1.0)
standardPercentage = (0.4, 0.5, 0.6)
lowPercentage = (0.0, 0.05, 0.1)

# Downsampling Configuration (T1/T2)
downsample_coverage_target = (0.15, 0.05)
downsample_gap_target = 2.0
downsample_obs_max = 50

# T3 Simulation Configuration
simulation_bins_per_period = 10
simulation_track_size = 3
simulation_track_spacing = 30
```

---

## Data Flow

### Pipeline Flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   UDL API   │───▶│ Create_Dataset│───▶│ Downsampling│───▶│  Simulation  │
│   Data Pull │    │   (T1 Base)   │    │   (T1/T2)   │    │    (T3)      │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│  PDF Report │◀───│  Evaluation  │◀───│   Orbit     │◀───│    UCTP      │
│  Generation │    │   Metrics    │    │ Association │    │  Processing  │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
```

### Tier Processing

| Tier | Input | Processing | Output |
|------|-------|------------|--------|
| T1 | Real observations | Light downsampling | Thinned dataset |
| T2 | T1 output | Heavy downsampling | Gapped dataset |
| T3 | T2 output | Gap filling with simulation | Augmented dataset |
| T4 | T3 output | Object simulation | Synthetic satellites |

---

## Data Structures

### Dataset JSON Format

```json
{
  "dataset_obs": [
    {
      "id": "observation_uuid",
      "obTime": "2025-01-01T00:00:00.000000Z",
      "ra": 123.456,
      "declination": 45.678,
      "trackId": 0,
      "uct": true
    }
  ],
  "reference": [
    {
      "satNo": 12345,
      "xpos": -7365.971,
      "ypos": -1331.400,
      "zpos": 1514.249,
      "xvel": 1.977,
      "yvel": -5.225,
      "zvel": 4.473,
      "epoch": "2025-01-01T00:00:00.000000",
      "line1": "1 12345U ...",
      "line2": "2 12345 ..."
    }
  ]
}
```

### UCTP Output Format

```json
[
  {
    "idStateVector": 0,
    "sourcedData": ["obs_id1", "obs_id2"],
    "epoch": "2025-01-01T00:00:00.000000",
    "xpos": -7365.971,
    "ypos": -1331.400,
    "zpos": 1514.249,
    "xvel": 1.977,
    "yvel": -5.225,
    "zvel": 4.473,
    "referenceFrame": "J2000"
  }
]
```

---

## Dependencies

### Core Dependencies
- `numpy` - Numerical operations
- `pandas` - Data manipulation
- `scipy` - Optimization (Hungarian algorithm)
- `aiohttp` - Async HTTP requests
- `requests` - Sync HTTP requests

### Orekit (Orbit Mechanics)
- `orekit_jpype` - Python wrapper for Orekit
- Requires Java 17+ (JDK)
- Orekit data files for atmospheric/gravitational models

### Database
- `duckdb` - Analytical database
- `pyarrow` - Parquet support

### Web Stack
- `fastapi` - Backend API
- `uvicorn` - ASGI server
- `react` - Frontend framework
- `vite` - Build tool

---

## Related Documentation

- [Database Architecture](DATABASE.md)
- [Frontend Architecture](FRONTEND.md)
- [Backend API](BACKEND_API.md)
- [Pipeline Documentation](PIPELINE.md)
- [Evaluation Metrics](EVALUATION_METRICS.md)
