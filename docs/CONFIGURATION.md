# Configuration Reference

## Overview

System configuration is centralized in `uct_benchmark/config.py`. This document explains all configurable parameters and their impacts.

---

## Path Configuration

```python
from pathlib import Path

# Project root (automatically determined)
PROJ_ROOT = Path(__file__).resolve().parents[1]

# Data directories
DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"           # Original API responses
INTERIM_DATA_DIR = DATA_DIR / "interim"   # Intermediate processed data
PROCESSED_DATA_DIR = DATA_DIR / "processed"  # Final datasets
EXTERNAL_DATA_DIR = DATA_DIR / "external"    # Third-party data files

# Output directories
MODELS_DIR = PROJ_ROOT / "models"
REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
```

---

## Orbital Regime Thresholds

Define boundaries between LEO, MEO, and GEO orbital regimes.

```python
# Semi-major axis thresholds (km)
semiMajorAxis_LEO = 8378   # LEO: a < 8378 km (altitude < 2000 km)
semiMajorAxis_GEO = 42164  # GEO: a >= 42164 km
# MEO: 8378 km <= a < 42164 km

# Highly eccentric orbit threshold
eccentricity_HEO = 0.7     # HEO: e >= 0.7
```

### Regime Classification Logic

```
if semi_major_axis < semiMajorAxis_LEO:
    regime = "LEO"
elif semi_major_axis >= semiMajorAxis_GEO:
    regime = "GEO"
else:
    regime = "MEO"

if eccentricity >= eccentricity_HEO:
    regime = "HEO"
```

---

## Quality Percentage Thresholds

Define what constitutes high, standard, and low quality for various metrics.

```python
# (lower_bound, target, upper_bound)
highPercentage = (0.9, 0.95, 1.0)      # High quality range
standardPercentage = (0.4, 0.5, 0.6)   # Standard quality range
lowPercentage = (0.0, 0.05, 0.1)       # Low quality range
```

### Usage
These thresholds are used in the scoring function to classify data quality:
- Values in `highPercentage` range → excellent quality
- Values in `standardPercentage` range → acceptable quality
- Values in `lowPercentage` range → marginal quality
- Values below `lowPercentage` → poor quality

---

## Orbital Coverage Thresholds

Define minimum orbital coverage for each regime.

```python
# Low orbital coverage thresholds (percentage)
# Based on 25th percentile of real data over 10-day window
lowCoverage_LEO = 0.0213   # 2.13%
lowCoverage_MEO = 0.0449   # 4.49%
lowCoverage_GEO = 41.656   # Note: GEO uses different metric

# Minimum threshold for dataset inclusion
tooLowtoInclude = 0.001    # 0.1% - below this, data is rejected
```

### Orbital Coverage Calculation
Coverage is computed over 3 orbital periods:
```
coverage = (observed_arc / total_orbit) * 100
```

---

## Observation Count Thresholds

Define observation density requirements.

```python
# Observations per 3-day window
lowObsCount = 50     # Below this is considered sparse
highObsCount = 150   # Above this is considered dense
```

### Impact on Scoring
- `obs_count < lowObsCount` → Lower tier (may need simulation)
- `lowObsCount <= obs_count <= highObsCount` → Standard tier
- `obs_count > highObsCount` → Higher tier (may need downsampling)

---

## Track Gap Threshold

Define maximum acceptable gap between observations.

```python
# Gap threshold in orbital periods
longTrackGap = 2   # Gap > 2 orbital periods is considered long
```

### Calculation
```python
gap_periods = max_gap_seconds / orbital_period_seconds
```

A long track gap indicates potential for:
- Lost tracking
- Maneuver detection difficulty
- Initial orbit determination challenges

---

## Object Count Targets

Define target numbers of satellites per dataset.

```python
highObjectCount = 80       # Large dataset
standardObjectCount = 40   # Medium dataset
lowObjectCount = 10        # Small dataset
```

### Usage
Dataset codes specify object count targets:
- "H" → `highObjectCount` satellites
- "S" → `standardObjectCount` satellites
- "L" → `lowObjectCount` satellites

---

## Window Selection Parameters

Configure the window selection algorithm behavior.

```python
# Batch size multiplier
batchSizeMultiplier = 5    # Initial batch = 5 * window_size

# Exponential decay rate for batch sizing
batchSizeDecayRate = 0.01  # Slower decay = more data pulled per iteration

# Sliding window resolution (days)
slide_resolution = 0.1     # 0.1 days = 2.4 hours
                           # Set to 0 for observation-by-observation sliding
```

### Batch Size Decay Function
```python
new_batch = window_size + (initial_batch - window_size) * exp(-decay_rate * iteration)
```

---

## Tier Threshold Sequence

Define the sequence of quality tiers to attempt.

```python
thresholds = ["T1", "T2", "T2", "T3", "T3", "T3", "T4", "T4", "T4", "T4"]
```

### Interpretation
- First attempt targets T1 (best quality)
- If T1 not achieved, try T2 (twice)
- If T2 not achieved, try T3 (three times)
- Final attempts target T4 (minimum acceptable)

### Tier Definitions

| Tier | Score | Meaning |
|------|-------|---------|
| T1 | 4 | May require downsampling |
| T2 | 3 | Requires downsampling |
| T3 | 2 | Requires observation simulation |
| T4 | 1 | Requires object simulation |
| T5 | 0 | Unusable |

---

## Propagator Parameters

Configure the force model for orbit propagation.

```python
# Default coefficients
solarRadPresCoef = 1.5    # Solar radiation pressure coefficient
dragCoef = 2.5            # Atmospheric drag coefficient

# Monte Carlo simulation points
monteCarloPoints = 100    # Number of samples for covariance propagation
```

### Force Model Components

The propagator includes:
1. **Earth Gravity**: 120x120 spherical harmonics
2. **Third Body**: Sun and Moon perturbations
3. **Atmospheric Drag**: NRLMSISE00 atmosphere model
4. **Solar Radiation Pressure**: Cannonball model

### Coefficient Impact

| Parameter | Low Value | High Value |
|-----------|-----------|------------|
| `solarRadPresCoef` | Less SRP force | More SRP force |
| `dragCoef` | Less drag (higher altitude) | More drag (lower altitude) |

---

## Simulation Parameters

Configure noise for synthetic observation generation.

```python
# Position noise standard deviation (km)
positionNoise = 0.01   # 10 meters

# Angular noise (arcseconds, converted to radians)
arcseconds2radians = 3600
angularNoise = 1 * arcseconds2radians   # 1 arcsecond
```

### Usage
When simulating observations:
```python
noisy_position = true_position + np.random.normal(0, positionNoise, 3)
noisy_angle = true_angle + np.random.normal(0, angularNoise)
```

---

## Calibration Satellites

List of satellites with known high-quality tracking data.

```python
satIDs = [
    1328,   # Vanguard 1
    5398,   # OAO 2
    7646,   # OPS 6073
    8820,   # NOAA 3
    16908,  # Cosmos 1867
    19751,  # USA 60
    20026,  # USA 67
    22195,  # Cosmos 2219
    22314,  # USA 82
    22824,  # Cosmos 2227
    23613,  # MILSTAR 1-F1
    24876,  # GPS BIIA-27
    25544,  # ISS (ZARYA)
    26360,  # GPS BIIR-4
    27566,  # ANIK F1
    27944,  # GPS BIIR-10
    32711,  # SDS 3-5
    36508,  # GPS IIF-1
    39070,  # GPS IIF-6
    39086,  # Cosmos 2486
    39504,  # Resurs P1
    40730,  # GPS IIF-10
    41240,  # Jason-3
    41335,  # GPS IIF-12
    42915,  # MUOS 4
    43476,  # GPS III-01
    43477,  # Zenit-2
    43873,  # GPS III-02
    46826,  # GPS III-05
    48859,  # GPS III-06
]
```

These satellites are used for:
- Testing and validation
- Baseline performance comparison
- Algorithm development

---

## Environment Variables

Required environment configuration (`.env` file):

```bash
# UDL Authentication
UDL_TOKEN=<base64_encoded_credentials>

# ESA DiscoWeb Token
ESA_TOKEN=<bearer_token>

# Optional: Orekit data path
OREKIT_DATA_PATH=./orekit-data-main

# Optional: Logging level
LOG_LEVEL=INFO
```

### Token Generation

```python
import base64

# UDL token
credentials = f"{username}:{password}"
udl_token = base64.b64encode(credentials.encode()).decode()

# ESA token - generate at https://discosweb.esoc.esa.int/tokens
```

---

## Modifying Configuration

### Runtime Override

```python
import uct_benchmark.config as config

# Override specific values
config.lowObsCount = 30
config.highObsCount = 200
```

### Permanent Changes

Edit `uct_benchmark/config.py` directly and commit changes.

### Per-Dataset Configuration

Dataset codes encode configuration that overrides defaults:
```
N<regime><sensor><coverage><count><trackgap><timewindow>
```

---

## Recommended Settings by Use Case

### High-Precision Evaluation
```python
monteCarloPoints = 500
slide_resolution = 0
thresholds = ["T1", "T1", "T1", "T2", "T2"]
```

### Fast Development/Testing
```python
monteCarloPoints = 50
slide_resolution = 0.5
thresholds = ["T2", "T3", "T4"]
```

### Production Benchmark
```python
monteCarloPoints = 100
slide_resolution = 0.1
thresholds = ["T1", "T2", "T2", "T3", "T3", "T3"]
```
