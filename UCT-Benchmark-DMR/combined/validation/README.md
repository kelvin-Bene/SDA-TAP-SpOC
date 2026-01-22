# UCT Benchmark Validation Suite

Comprehensive validation suite for testing the UCT Benchmark implementation.

## Overview

This suite validates all components of the UCT Benchmark:

1. **Data Pull**: Retrieves 100k+ observations from UDL API across LEO/MEO/GEO regimes
2. **Downsampling (T1/T2)**: Tests observation reduction algorithms at multiple retention levels
3. **Gap Analysis**: Tests `epochsToSim()` gap detection for simulation planning
4. **Orekit Simulation**: Tests synthetic observation generation using:
   - TLE propagation (SGP4/SDP4)
   - State vector propagation

## Requirements

- Python 3.12
- Java 17+ (JDK)
- orekit-jpype
- orekitdata
- UDL API access token

## Usage

### Windows (PowerShell)

```powershell
# Run with defaults (100k obs, 30 days)
.\validation\run_validation.ps1

# Custom parameters
.\validation\run_validation.ps1 --target-obs 150000 --days 45
```

### Direct Python

```bash
# Activate virtual environment first
.\.venv\Scripts\activate

# Set Java environment
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

# Run validation
python validation/run_validation.py --target-obs 100000 --days 30
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--target-obs` | 100,000 | Target number of observations to pull |
| `--days` | 30 | Time window in days |
| `--sats-per-regime` | 40 | Number of satellites per orbital regime |

## Output Structure

Results are saved in timestamped directories:

```
validation/results/YYYYMMDD_HHMMSS/
├── input_data/
│   ├── observations.csv      # Raw UDL observations
│   ├── tles.csv              # TLE data for satellites
│   └── pull_metadata.json    # Data pull statistics
├── downsampling/
│   ├── t1_light_observations.csv
│   ├── t1_moderate_observations.csv
│   ├── t2_medium_observations.csv
│   ├── t2_heavy_observations.csv
│   ├── t2_extreme_observations.csv
│   └── metrics.json          # Downsampling metrics
├── simulation/
│   ├── gap_analysis.json     # Gap detection results
│   ├── generated_observations.csv  # Simulated observations
│   └── orekit_metrics.json   # Simulation metrics
└── summary/
    ├── test_report.md        # Human-readable report
    └── metrics_summary.json  # Machine-readable summary
```

## Test Components

### Phase 1: Data Pull
- Queries UDL API for satellite observations
- Retrieves TLE data for orbit propagation
- Covers LEO, MEO, and GEO orbital regimes

### Phase 2: Downsampling
Tests 5 configurations:
| Config | Retention | Description |
|--------|-----------|-------------|
| T1_Light | 80% | Light reduction |
| T1_Moderate | 60% | Moderate reduction |
| T2_Medium | 50% | Medium reduction |
| T2_Heavy | 30% | Heavy reduction |
| T2_Extreme | 20% | Extreme reduction |

### Phase 3: Gap Analysis
- Tests `epochsToSim()` function
- Identifies observation gaps in time series
- Calculates epochs needed for simulation fill

### Phase 4: Orekit Simulation
- **TLE Propagation**: Uses Two-Line Elements with SGP4/SDP4
- **State Vector Propagation**: Uses position/velocity vectors
- Generates synthetic observations with realistic noise models:
  - Position noise: 10m
  - Angular noise: 1 arcsecond

## Pass Criteria

| Component | Pass Threshold |
|-----------|----------------|
| Data Pull | Target observations met |
| Downsampling | ≥80% configurations pass |
| Gap Analysis | ≥80% satellites pass |
| TLE Propagation | ≥80% satellites pass |
| State Vector | ≥80% satellites pass |

## Interpreting Results

The summary report (`test_report.md`) provides:
- Overall PASS/FAIL status
- Per-component metrics
- Detailed breakdown by satellite and configuration

Check `metrics_summary.json` for programmatic access to results.
