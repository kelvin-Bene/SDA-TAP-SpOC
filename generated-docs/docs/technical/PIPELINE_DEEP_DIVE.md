# Pipeline Deep Dive

<!-- AI_METADATA
purpose: Detailed technical documentation of the dataset generation pipeline
status: active
related_files: [technical/PIPELINE.md, technical/CONFIGURATION.md, planning/PROJECT_STATUS.md]
last_updated: 2026-04-14
-->

This document provides in-depth technical details about the UCT Benchmark dataset generation pipeline, including the tier system, downsampling algorithms, simulation processes, and scoring functions.

---

## Overview

The pipeline transforms raw observational data from space surveillance networks into standardized benchmark datasets. The core challenge is creating datasets with controlled difficulty levels for testing UCTP algorithms.

---

<!-- AI_SECTION: tier_system -->

## 1. The Tier System Explained

The tier system classifies data quality and determines what processing is required to create a valid benchmark dataset.

### Tier Definitions

| Tier | Score | Data Quality | Processing Required |
|------|-------|--------------|---------------------|
| **T1** | 4 | High Quality | Light downsampling (optional) |
| **T2** | 3 | Good Quality | Heavy downsampling |
| **T3** | 2 | Moderate Quality | Observation simulation |
| **T4** | 1 | Low Quality | Object simulation |
| **T5** | 0 | Unusable | Reject request |

### Tier Selection Logic

```python
# From basicScoringFunction.py
def classify_tier(score):
    if score >= 4:
        return "T1"  # Best - may need downsampling
    elif score >= 3:
        return "T2"  # Good - needs downsampling
    elif score >= 2:
        return "T3"  # Moderate - needs simulation
    elif score >= 1:
        return "T4"  # Poor - needs object simulation
    else:
        return "T5"  # Unusable
```

### When Each Tier is Used

**T1 (High Quality)**:
- Data exceeds minimum quality thresholds
- Optional light downsampling to create challenge
- Use case: Realistic scenarios with good sensor coverage

**T2 (Good Quality)**:
- Data meets thresholds but is "too easy"
- Required downsampling to reduce observations
- Use case: Testing algorithms with realistic gaps

**T3 (Moderate Quality)**:
- Data has insufficient observations or coverage
- Simulated observations fill gaps
- Use case: Sparse data scenarios

**T4 (Low Quality)** *(Not yet implemented)*:
- Very few objects meet criteria
- Entire synthetic satellites must be generated
- Use case: Extremely challenging scenarios

**T5 (Unusable)**:
- Data quality too poor to salvage
- Request rejected
- User should modify parameters

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: downsampling -->

## 2. Downsampling Deep Dive (T1/T2)

**File**: `uct_benchmark/data/dataManipulation.py`
**Function**: `downsampleData()`

When data quality is too high (T1/T2), a three-stage downsampling pipeline reduces it to target difficulty levels.

### Three-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│              THREE-STAGE DOWNSAMPLING PIPELINE                   │
├─────────────────────────────────────────────────────────────────┤
│  Stage 1: Coverage Reduction                                     │
│  └── _lowerOrbitCoverage() - polygon-based point removal        │
├─────────────────────────────────────────────────────────────────┤
│  Stage 2: Gap Widening                                           │
│  └── _increaseTrackDistance() - sliding window gap increase     │
├─────────────────────────────────────────────────────────────────┤
│  Stage 3: Count Reduction                                        │
│  └── _downsampleAbsolute() - time-binned sampling               │
└─────────────────────────────────────────────────────────────────┘
```

### Stage 1: `_lowerOrbitCoverage()`

**Purpose**: Reduce orbital coverage by removing observations from densely-covered regions.

**Algorithm**:
1. Map observations to orbital position (true anomaly)
2. Divide orbit into angular bins
3. Identify bins exceeding coverage targets
4. Remove observations from over-covered bins using polygon-based selection
5. Preserve track structure (don't break up continuous tracks)

**Configuration** (`settings.py`):
```python
downsample_coverage_bounds = (0.3, 0.5, 0.7)  # (min%, target%, max%) of satellites
downsample_coverage_target = (0.15, 0.05)     # (max, min) orbital coverage targets
```

**Code Location**: `dataManipulation.py:_lowerOrbitCoverage()`

---

### Stage 2: `_increaseTrackDistance()`

**Purpose**: Increase gaps between observation tracks.

**Algorithm**:
1. Identify track boundaries (gaps > threshold)
2. Use sliding window to find tracks that are "too close"
3. Remove intermediate tracks to widen gaps
4. Maintain minimum observations per remaining track

**Configuration** (`settings.py`):
```python
downsample_gap_bounds = (0.3, 0.5, 0.7)  # (min%, target%, max%) of satellites
downsample_gap_target = 2.0              # Target gap duration (orbital periods)
```

**Code Location**: `dataManipulation.py:_increaseTrackDistance()`

---

### Stage 3: `_downsampleAbsolute()`

**Purpose**: Reduce total observation count through time-binned sampling.

**Algorithm**:
1. Divide time window into equal bins
2. Calculate observations per bin
3. For bins exceeding target, randomly sample down
4. Preserve temporal distribution (don't cluster remaining obs)

**Configuration** (`settings.py`):
```python
downsample_obs_bounds = (0.3, 0.5, 0.7)  # (min%, target%, max%) of satellites
downsample_obs_max = 50                  # Max observations per satellite per 3 days
downsample_min_obs = 5                   # Minimum observations to retain
```

**Code Location**: `dataManipulation.py:_downsampleAbsolute()`

---

### Downsampling Example

**Input**: 500 observations over 3 days, 95% orbital coverage, 0.5 period gaps

**Stage 1 Output**: Coverage reduced to 50%, ~300 observations remain

**Stage 2 Output**: Gaps widened to 2 periods, ~200 observations remain

**Stage 3 Output**: Final count reduced to 50 observations

**Result**: Challenging dataset with sparse coverage and wide gaps

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: simulation -->

## 3. Simulation Deep Dive (T3)

**File**: `uct_benchmark/simulation/simulateObservations.py`
**Functions**: `epochsToSim()`, `simulateObs()`

When data quality is insufficient (T3), synthetic observations are generated to fill gaps.

### T3 Simulation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│              T3 SIMULATION PIPELINE                              │
├─────────────────────────────────────────────────────────────────┤
│  Step 1: Gap Detection                                           │
│  └── epochsToSim() - time-bin analysis for sparse bins          │
├─────────────────────────────────────────────────────────────────┤
│  Step 2: Epoch Selection                                         │
│  └── Select epochs at center of empty bins                      │
├─────────────────────────────────────────────────────────────────┤
│  Step 3: Propagation                                             │
│  └── TLEpropagator() or ephemerisPropagator()                   │
├─────────────────────────────────────────────────────────────────┤
│  Step 4: Observation Generation                                  │
│  └── simulateObs() - generate RA/Dec with realistic noise       │
├─────────────────────────────────────────────────────────────────┤
│  Step 5: Merge                                                   │
│  └── Combine with dataMode='SIMULATED' marker                   │
└─────────────────────────────────────────────────────────────────┘
```

### `epochsToSim()` Algorithm

**Purpose**: Determine which epochs need simulated observations.

**Algorithm** (Time-bin based approach):
```python
def epochsToSim(df, satNo, period, bins_per_period, min_obs_per_bin,
                target_increase, track_size, track_spacing):
    """
    1. Calculate time bins based on orbital period
       bin_duration = period / bins_per_period

    2. Count observations in each bin

    3. Identify "empty" bins (obs_count < min_obs_per_bin)

    4. Calculate how many simulated epochs needed
       needed = (target_obs - current_obs) / track_size

    5. Select epochs at center of empty bins

    6. Return list of epochs with track grouping info
    """
```

**Configuration** (`settings.py:164-188`):
```python
# Simulation parameters
simulation_bins_per_period = 10      # Bins per orbital period
simulation_min_obs_per_bin = 1       # Minimum obs per bin
simulation_max_ratio = 0.5           # Max simulated/real ratio
simulation_target_increase = 0.5     # Target improvement factor (50%)

# Track structure
simulation_track_size = 3            # Observations per simulated track
simulation_track_spacing = 30        # Seconds between obs in track
simulation_min_existing_obs = 3      # Minimum real obs required before simulating
```

**Code Location**: `simulateObservations.py:358-507`

---

### `simulateObs()` Algorithm

**Purpose**: Generate realistic synthetic observations at specified epochs.

**Algorithm**:
```python
def simulateObs(epochs, tle_or_sv, sensor_list, noise_model):
    """
    For each epoch:
    1. Propagate orbit to epoch (TLE or state vector)
    2. Select sensor (weighted random from available sensors)
    3. Compute geometric visibility
       - Check elevation > 6 degrees
       - Check sensor operational hours
    4. Calculate RA/Dec from satellite position and sensor location
    5. Add realistic noise
       - RA noise: ~1-5 arcsec (regime dependent)
       - Dec noise: ~1-5 arcsec (regime dependent)
    6. Generate observation record in UDL schema format
    """
```

**Noise Models**:
```python
# By orbital regime
LEO_NOISE = {"ra": 2.0, "dec": 2.0}  # arcsec
MEO_NOISE = {"ra": 3.0, "dec": 3.0}
GEO_NOISE = {"ra": 1.5, "dec": 1.5}
```

**Output Format**: UDL-compatible observation schema with `dataMode='SIMULATED'` marker

---

### Sensor Selection

**Function**: `selectSensor()`

**Algorithm**:
1. Filter sensors by type (optical/radar matching request)
2. Filter by geographic coverage (can see satellite)
3. Apply weighted selection (higher quality sensors preferred)
4. Verify elevation constraint (>6 degrees)

**Available Sensors**: Loaded from configuration/database

---

### Track Grouping

Simulated observations are grouped into "tracks" to mimic real sensor behavior:

```python
# Track structure example
track = [
    obs_t0,           # First observation
    obs_t0 + 30s,     # 30 seconds later
    obs_t0 + 60s,     # 60 seconds later (last observation)
]
# Gap of several hours, then next track
```

**Configuration**:
- `track_size`: Observations per track (default: 3)
- `track_spacing`: Seconds between observations in track (default: 30)

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: scoring -->

## 4. Scoring Function Details

**File**: `uct_benchmark/data/basicScoringFunction.py`
**Function**: `basicScoring()`

The scoring function evaluates data quality to determine tier classification.

### Scoring Criteria

| Criterion | Description | Weight |
|-----------|-------------|--------|
| Orbital Coverage | Percentage of orbit with observations | 30% |
| Observation Count | Number of observations per period | 30% |
| Track Gap | Longest gap between observations | 20% |
| Object Count | Satellites meeting quality criteria | 20% |

### Orbital Coverage Scoring

```python
def score_coverage(coverage_percentage):
    """
    Coverage thresholds (from settings.py):
    - high: (0.9, 0.95, 1.0)
    - standard: (0.4, 0.5, 0.6)
    - low: (0.0, 0.05, 0.1)

    Score:
    - coverage >= 0.9: 4 points (T1)
    - coverage >= 0.5: 3 points (T2)
    - coverage >= 0.1: 2 points (T3)
    - coverage < 0.1: 1 point (T4)
    """
```

### Observation Count Scoring

```python
def score_obs_count(count, period_days=3):
    """
    Count thresholds (per 3-day period):
    - high: >= 150 observations
    - low: <= 50 observations

    Score:
    - count >= 150: 4 points
    - count >= 75: 3 points
    - count >= 50: 2 points
    - count < 50: 1 point
    """
```

### Track Gap Analysis

```python
def score_track_gap(max_gap_periods):
    """
    Gap threshold: 2 orbital periods considered "long"

    Score:
    - max_gap < 1 period: 4 points
    - max_gap < 2 periods: 3 points
    - max_gap < 4 periods: 2 points
    - max_gap >= 4 periods: 1 point
    """
```

### Object Completeness

```python
def score_object_count(qualifying_objects, requested_objects):
    """
    Object count thresholds:
    - high: >= 80 objects
    - standard: >= 40 objects
    - low: >= 10 objects

    Score based on percentage meeting criteria
    """
```

### Combined Tier Classification

```python
def classify_tier(scores):
    """
    Weighted combination:
    final_score = (
        0.30 * coverage_score +
        0.30 * obs_count_score +
        0.20 * gap_score +
        0.20 * object_score
    )

    Return tier based on final_score
    """
```

<!-- /AI_SECTION -->

---

## 5. Configuration Parameters

All pipeline parameters are configurable in `uct_benchmark/settings.py`.

### Downsampling Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `downsample_coverage_bounds` | (0.3, 0.5, 0.7) | (min%, target%, max%) of satellites |
| `downsample_coverage_target` | (0.15, 0.05) | (max, min) orbital coverage targets |
| `downsample_gap_bounds` | (0.3, 0.5, 0.7) | (min%, target%, max%) of satellites |
| `downsample_gap_target` | 2.0 | Target gap duration (orbital periods) |
| `downsample_obs_bounds` | (0.3, 0.5, 0.7) | (min%, target%, max%) of satellites |
| `downsample_obs_max` | 50 | Max observations per satellite per 3 days |
| `downsample_min_obs` | 5 | Minimum observations to retain |

### Simulation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `simulation_bins_per_period` | 10 | Time bins per orbital period |
| `simulation_min_obs_per_bin` | 1 | Minimum obs per bin |
| `simulation_max_ratio` | 0.5 | Max simulated/real ratio |
| `simulation_target_increase` | 0.5 | Target improvement factor (50%) |
| `simulation_track_size` | 3 | Obs per simulated track |
| `simulation_track_spacing` | 30 | Seconds between obs in track |
| `simulation_min_existing_obs` | 3 | Min real obs required before simulating |

### Scoring Thresholds

| Parameter | Default | Description |
|-----------|---------|-------------|
| `highPercentage` | (0.9, 0.95, 1.0) | High coverage range |
| `standardPercentage` | (0.4, 0.5, 0.6) | Standard coverage range |
| `lowPercentage` | (0.0, 0.05, 0.1) | Low coverage range |
| `lowObsCount` | 50 | Low observation threshold |
| `highObsCount` | 150 | High observation threshold |
| `longTrackGap` | 2 | Long gap threshold (periods) |

---

## 6. Key Files Summary

| File | Purpose |
|------|---------|
| `Create_Dataset.py` | Main pipeline driver |
| `dataManipulation.py` | T1/T2 downsampling functions |
| `simulateObservations.py` | T3 simulation functions |
| `basicScoringFunction.py` | Data quality scoring |
| `windowSelection.py` | Time window selection |
| `settings.py` | All configuration parameters |

---

## Related Documents

- [PIPELINE.md](PIPELINE.md) - High-level pipeline overview
- [CONFIGURATION.md](CONFIGURATION.md) - Full configuration reference
- [PROJECT_STATUS.md](../planning/PROJECT_STATUS.md) - Implementation status

---

*Created 2026-02-03 | Updated 2026-04-14*
