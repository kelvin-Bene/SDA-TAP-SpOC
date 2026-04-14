# Configuration Reference

> **last_updated:** 2026-04-14

## Overview

System configuration is centralized in `uct_benchmark/settings.py`. This document explains all configurable parameters and their impacts.

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
if eccentricity >= eccentricity_HEO:
    regime = "HEO"
elif semi_major_axis < semiMajorAxis_LEO:
    regime = "LEO"
elif semi_major_axis >= semiMajorAxis_GEO:
    regime = "GEO"
else:
    regime = "MEO"
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
- Values in `highPercentage` range -> excellent quality
- Values in `standardPercentage` range -> acceptable quality
- Values in `lowPercentage` range -> marginal quality
- Values below `lowPercentage` -> poor quality

---

## QUALITY_RANGES (A/S/N)

The `QUALITY_RANGES` dictionary controls the percentage of objects that must have "LOW" quality in a given metric to satisfy each quality code. These codes appear in positions 11-13 of the 16-character dataset code.

| Code | Label | `min_pct` | `max_pct` | Meaning |
|------|-------|-----------|-----------|---------|
| **A** | All / Sparse | 0.90 | 1.00 | >90% of objects have LOW quality (hard dataset) |
| **S** | Standard / Mixed | 0.40 | 0.60 | 40-60% of objects have LOW quality (mixed dataset) |
| **N** | None / Dense | 0.00 | 0.10 | <10% of objects have LOW quality (easy dataset) |

```python
QUALITY_RANGES = {
    'A': {'min_pct': 0.90, 'max_pct': 1.0},   # >90% have LOW quality (sparse)
    'S': {'min_pct': 0.40, 'max_pct': 0.60},   # 40-60% have LOW quality (mixed)
    'N': {'min_pct': 0.0,  'max_pct': 0.10},   # <10% have LOW quality (dense)
}
```

The same A/S/N logic applies independently to three quality dimensions:

| Position | Dimension | What "LOW" means |
|----------|-----------|------------------|
| 11 | Coverage Quality | Object's orbital coverage < regime-specific threshold |
| 12 | Track Gap Quality | Object's longest track gap > 2 orbital periods |
| 13 | Obs Count Quality | Object has < 50 observations per 3-day span |

---

## Orbital Coverage Thresholds

Define what constitutes "LOW" orbital coverage for each regime. Values are **fractions of the orbital arc** (not percentages), calculated using a convex-polygon-on-circumscribed-circle approach over a 3-orbital-period timespan.

```python
COVERAGE_THRESHOLDS = {
    "LEO": 0.000213,   # fraction  =  0.0213% of orbital arc
    "MEO": 0.000449,   # fraction  =  0.0449% of orbital arc
    "GEO": 0.41656,    # fraction  = 41.656%  of orbital arc
    "HEO": 0.20,       # fraction  = 20.0%    of orbital arc (estimate)
}
```

| Regime | Fraction | Percentage | Source |
|--------|----------|------------|--------|
| LEO | 0.000213 | 0.0213% | Lewis's Benchmarking Documentation |
| MEO | 0.000449 | 0.0449% | Lewis's Benchmarking Documentation |
| GEO | 0.41656 | 41.656% | Lewis's Benchmarking Documentation |
| HEO | 0.20 | 20.0% | Estimate (not in Lewis's doc) |

An object whose orbital coverage falls **below** its regime threshold is classified as having LOW coverage.

```python
# Minimum threshold for dataset inclusion (all regimes)
tooLowtoInclude = 0.001   # 0.1% -- below this, the object is excluded entirely
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
- `obs_count < lowObsCount` -> Lower tier (may need simulation)
- `lowObsCount <= obs_count <= highObsCount` -> Standard tier
- `obs_count > highObsCount` -> Higher tier (may need downsampling)

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
- "H" -> `highObjectCount` satellites
- "S" -> `standardObjectCount` satellites
- "L" -> `lowObjectCount` satellites

---

## Object Type Filtering Thresholds

```python
# High Area-to-Mass Ratio (HAMR)
HAMR_THRESHOLD = 1.0  # m^2/kg -- objects with A/M above this are HAMR

# Close Proximity thresholds (per Louis's UCT Labelling.xlsx)
PROXIMITY_ANGULAR_THRESHOLD_DEG = 30.0 / 3600.0  # 30 arcsec ~ 0.00833 deg
PROXIMITY_DISTANCE_THRESHOLD_KM = 10.0            # km
PROXIMITY_VELOCITY_THRESHOLD_M_S = 10.0            # m/s
```

---

## DOWNSAMPLING_PROFILES (Regime-Specific)

The `DOWNSAMPLING_PROFILES` dictionary provides per-regime parameters that control how aggressively observations are removed during downsampling. Each profile constrains orbital-arc coverage, track-gap size, per-track observation counts, and track duration.

```python
DOWNSAMPLING_PROFILES: Dict[str, Dict] = {
    "LEO": { ... },
    "MEO": { ... },
    "GEO": { ... },
    "HEO": { ... },
}
```

### Full Parameter Table

| Parameter | LEO | MEO | GEO | HEO | Unit / Notes |
|-----------|-----|-----|-----|-----|-------------|
| `min_coverage_pct` | 0.02 | 0.03 | 0.05 | 0.01 | Fraction of orbital arc (lower bound) |
| `max_coverage_pct` | 0.15 | 0.20 | 0.30 | 0.10 | Fraction of orbital arc (upper bound) |
| `min_track_gap_periods` | 1.5 | 1.0 | 0.5 | 2.0 | Minimum gap between tracks (orbital periods) |
| `max_track_gap_periods` | 5.0 | 3.0 | 2.0 | 8.0 | Maximum gap between tracks (orbital periods) |
| `obs_per_track` | (3, 10) | (5, 15) | (10, 30) | (3, 8) | (min, max) observations per track |
| `track_duration_periods` | 0.1 | 0.15 | 0.25 | 0.05 | Track span as fraction of orbital period |

### Interpretation

- **LEO**: Short tracks (10% of period), moderate gaps (1.5-5 periods), small coverage window (2-15%).
- **MEO**: Slightly longer tracks, narrower gaps, moderate coverage (3-20%).
- **GEO**: Longest tracks (25% of period), shortest gaps (0.5-2 periods), widest coverage (5-30%). GEO objects are continuously visible, so coverage is naturally high.
- **HEO**: Shortest tracks (5% of period), widest gaps (2-8 periods), smallest coverage (1-10%). HEO coverage varies greatly due to changing altitude along the orbit.

---

## Downsampling Configuration (T1/T2)

Parameters for reducing data quality to target levels for T1/T2 tier datasets.

```python
## --- Downsampling Configuration --- ##
# p_bounds: 3-tuple of (min%, target%, max%) of satellites to apply downsampling to

# Orbital coverage downsampling
downsample_coverage_bounds = (0.3, 0.5, 0.7)  # (min%, target%, max%) of sats to downsample
downsample_coverage_target = (0.15, 0.05)     # (max, min) orbital coverage threshold

# Track gap downsampling
downsample_gap_bounds = (0.3, 0.5, 0.7)       # (min%, target%, max%) of sats to downsample
downsample_gap_target = 2.0                   # Target max gap (2 orbital periods)

# Observation count downsampling
downsample_obs_bounds = (0.3, 0.5, 0.7)       # (min%, target%, max%) of sats to downsample
downsample_obs_max = 50                       # Max observations per sat per 3 days

# Minimum observations to keep per satellite (safety threshold)
downsample_min_obs = 5
```

### Three-Stage Downsampling Pipeline

1. **Coverage Reduction** (`_lowerOrbitCoverage()`): Removes observations to reduce orbital coverage
2. **Gap Widening** (`_increaseTrackDistance()`): Increases gaps between observation tracks
3. **Count Reduction** (`_downsampleAbsolute()`): Reduces total observation count using time-binned sampling

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
thresholds = ["T1", "T2", "T2", "T3", "T3", "T3", "T4", "T4", "T4", "T4", "T5"]
```

### Interpretation
- First attempt targets T1 (best quality)
- If T1 not achieved, try T2 (twice)
- If T2 not achieved, try T3 (three times)
- Final attempts target T4 (minimum acceptable)
- T5 = "Impossible" (criteria cannot be met)

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

## Simulation Noise Parameters

Configure noise for synthetic observation generation.

```python
# Position noise standard deviation (km)
positionNoise = 0.01   # 10 meters (0.01 km)

# Angular noise (degrees) -- 1 arcsecond
angularNoise = 1.0 / 3600.0   # 1 arcsecond in degrees
```

### Usage
When simulating observations:
```python
noisy_position = true_position + np.random.normal(0, positionNoise, 3)
noisy_angle = true_angle + np.random.normal(0, angularNoise)
```

---

## T3 Simulation Configuration

Parameters for T3 simulation to increase data quality by adding synthetic observations.

```python
## --- T3 Simulation Configuration --- ##

# Time bins per orbital period for epoch selection
# Higher = finer granularity but more computation
simulation_bins_per_period = 10

# Minimum observations per bin to consider "covered"
simulation_min_obs_per_bin = 1

# Maximum ratio of simulated observations to total (prevents over-simulation)
simulation_max_ratio = 0.5

# Target increase in observation count (percentage)
simulation_target_increase = 0.5  # 50% more observations

# Observations per simulated track (realistic grouping)
# Real observations come in tracks of 3-5 obs within minutes
simulation_track_size = 3

# Seconds between observations in a track
simulation_track_spacing = 30

# Minimum observations required before simulation is worthwhile
simulation_min_existing_obs = 3
```

### T3 Simulation Pipeline

1. **Gap Detection**: `epochsToSim()` identifies time bins with insufficient observations
2. **Epoch Selection**: Selects epochs at center of empty bins
3. **Propagation**: Uses `ephemerisPropagator()` or `TLEpropagator()` to generate state vectors
4. **Observation Generation**: `simulateObs()` creates synthetic observations with realistic noise
5. **Merge**: Simulated observations marked with `dataMode='SIMULATED'` and combined with real data

---

## 16-Character Dataset Code Format

Every generated dataset is identified by a 16-character code that fully encodes its configuration. The code is structured as follows:

```
Position(s):  1   2-3   4-6   7-8   9-10  11  12  13  14  15-16
Example:      U   50    LEO   NE    OP    S   S   S   S   07
```

### Position-by-Position Reference

#### Position 1 -- Object Type (1 character)

| Code | Internal Map | Description |
|------|-------------|-------------|
| **H** | HAMR | High Area-to-Mass Ratio objects (A/M > 1.0 m^2/kg) |
| **C** | PROX | Close physical proximity objects (distance < 10 km, velocity < 10 m/s) |
| **A** | APRX | Apparent (angular) proximity objects (separation < 30 arcsec) |
| **U** | NORM | Unspecified / Normal satellites |
| **N** | CALIB | Calibration satellites (30 well-known objects with high-quality orbits) |

#### Positions 2-3 -- Target Percentage (2 characters)

Percentage of objects in the dataset that are of the specified object type.

| Code | Meaning |
|------|---------|
| **50** | 50% target objects |
| **10** | 10% target objects |
| **01** | 1% target objects |
| **UN** | Unspecified / not applicable |

#### Positions 4-6 -- Orbital Regime (3 characters)

| Code | Regimes Included |
|------|-----------------|
| **LEO** | Low Earth Orbit only |
| **MEO** | Medium Earth Orbit only |
| **GEO** | Geosynchronous Orbit only |
| **HEO** | Highly Eccentric Orbit only |
| **ALL** | All regimes |

**2-regime combinations:**

| Code | Regimes |
|------|---------|
| **LMO** | LEO + MEO |
| **LGO** | LEO + GEO |
| **LHO** | LEO + HEO |
| **MGO** | MEO + GEO |
| **MHO** | MEO + HEO |
| **GHO** | GEO + HEO |

**3-regime combinations:**

| Code | Regimes |
|------|---------|
| **LMG** | LEO + MEO + GEO |
| **LMH** | LEO + MEO + HEO |
| **LGH** | LEO + GEO + HEO |
| **MGH** | MEO + GEO + HEO |

#### Positions 7-8 -- Event Type (2 characters)

| Code | Internal Map | Description |
|------|-------------|-------------|
| **MB** | MAN | Maneuver between observations |
| **BU** | BRK | Breakup event |
| **LL** | LLT | Long-duration / Low-thrust maneuver |
| **NE** | NRM | No events (normal operations) |

#### Positions 9-10 -- Sensor Type (2 characters)

| Code | Internal Map | Description |
|------|-------------|-------------|
| **OP** | EO | Optical only |
| **RA** | RA | Radar only |
| **RF** | RF | RF only |
| **FU** | MX | Fusion (all sensor types) |
| **OR** | EO_RA | Optical primary + Radar secondary |
| **RO** | RA_EO | Radar primary + Optical secondary |
| **RR** | RA_RF | Radar + RF |

#### Position 11 -- Coverage Quality (1 character)

Percentage of objects with LOW orbital coverage (below regime-specific `COVERAGE_THRESHOLDS`).

| Code | Label | % of objects with LOW coverage |
|------|-------|-------------------------------|
| **A** | All / Sparse | 90-100% |
| **S** | Standard / Mixed | 40-60% |
| **N** | None / Dense | 0-10% |

#### Position 12 -- Track Gap Quality (1 character)

Percentage of objects with LONG track gaps (gap > 2 orbital periods).

| Code | Label | % of objects with LONG gaps |
|------|-------|-----------------------------|
| **A** | All / Sparse | 90-100% |
| **S** | Standard / Mixed | 40-60% |
| **N** | None / Dense | 0-10% |

#### Position 13 -- Observation Count Quality (1 character)

Percentage of objects with LOW observation count (< 50 obs per 3 days).

| Code | Label | % of objects with LOW obs count |
|------|-------|--------------------------------|
| **A** | All / Sparse | 90-100% |
| **S** | Standard / Mixed | 40-60% |
| **N** | None / Dense | 0-10% |

#### Position 14 -- Object Count (1 character)

Number of satellites in the dataset.

| Code | Count |
|------|-------|
| **H** | 80 objects (high) |
| **S** | 40 objects (standard) |
| **L** | 10 objects (low) |

#### Positions 15-16 -- Fitspan (2 digits)

Duration of the dataset time window in days.

| Value | Meaning |
|-------|---------|
| **01** - **14** | 1 to 14 days |

### Example Decode

```
U  50  LEO  NE  OP  S  S  S  S  07
|  |   |    |   |   |  |  |  |  |
|  |   |    |   |   |  |  |  |  +-- 07-day fitspan
|  |   |    |   |   |  |  |  +---- Standard object count (40)
|  |   |    |   |   |  |  +------ 40-60% have LOW obs count
|  |   |    |   |   |  +-------- 40-60% have LONG track gaps
|  |   |    |   |   +---------- 40-60% have LOW coverage
|  |   |    |   +------------- Optical only
|  |   |    +----------------- No events
|  |   +---------------------- LEO regime
|  +-------------------------- 50% target objects
+----------------------------- Unspecified / Normal objects
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
ESA_DISCOS_API_TOKEN=<bearer_token>

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
import uct_benchmark.settings as settings

# Override specific values
settings.lowObsCount = 30
settings.highObsCount = 200
```

### Permanent Changes

Edit `uct_benchmark/settings.py` directly and commit changes.

### Per-Dataset Configuration

Dataset codes encode configuration that overrides defaults. See the **16-Character Dataset Code Format** section above for the full schema.

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
