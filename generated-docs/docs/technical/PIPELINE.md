# Data Pipeline and Flow

## Overview

The UCT Benchmarking pipeline transforms raw observational data from space surveillance networks into standardized benchmark datasets for evaluating Uncorrelated Track Processing (UCTP) algorithms.

## Pipeline Phases

The pipeline operates in three main phases:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PHASE 1                                         │
│                         Dataset Creation                                     │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│  │  GUI    │──▶│  API    │──▶│ Window  │──▶│  Score  │──▶│  Save   │       │
│  │ Config  │   │  Pull   │   │ Select  │   │  Data   │   │ Dataset │       │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PHASE 2                                         │
│                          UCTP Processing                                     │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                    │
│  │  Load   │──▶│  Run    │──▶│ Output  │                                    │
│  │ Dataset │   │  UCTP   │   │ Results │                                    │
│  └─────────┘   └─────────┘   └─────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PHASE 3                                         │
│                            Evaluation                                        │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│  │  Load   │──▶│ Orbit   │──▶│ Binary  │──▶│ State   │──▶│ Report  │       │
│  │ Results │   │ Assoc.  │   │ Metrics │   │ Metrics │   │  PDF    │       │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Dataset Creation

### Step 1: Configuration (GUI)
**File**: `uct_benchmark/Create_Dataset.py` → `launch_gui()`

Users configure dataset parameters through a CustomTKinter GUI:
- **Orbital Regime**: LEO, MEO, GEO, or combinations
- **Sensor Type**: Optical, Radar, or specific sensors
- **Time Window**: Duration of observation window (days)
- **Object Count**: Number of satellites in dataset

### Step 2: Dataset Code Generation
**File**: `uct_benchmark/data/windowTools.py` → `codeGenerator()`

Converts user configuration into standardized "Dataset Codes" that encode:
- Regime classification
- Sensor requirements
- Time span parameters
- Object count targets

### Step 3: Batch Data Pull
**File**: `uct_benchmark/data/windowCheck.py` → `batchPull()`

Queries the Unified Data Library (UDL) for observation data:
```
1. Construct query parameters from dataset code
2. Loop through sensor types and orbital regimes
3. Pull data in 10-minute time chunks to avoid timeouts
4. Compile results into a single DataFrame
```

### Step 4: Window Selection
**File**: `uct_benchmark/data/windowCheck.py` → `windowMain()`, `windowCheck()`, `bisect()`, `slide()`

Intelligent window selection algorithm:

1. **Initial Batch Pull**: Pull data for `batchSizeMultiplier × windowSize` days
2. **Threshold Check**: Score the batch against desired tier
3. **Bisection**: Recursively divide batch to find high-quality sub-regions
4. **Sliding Window**: Fine-tune window position for optimal score
5. **Exponential Decay**: If threshold not met, expand search with decaying batch sizes

```python
# Threshold Tiers
T1 = 4  # May require downsampling (best)
T2 = 3  # Requires downsampling
T3 = 2  # Requires observation simulation
T4 = 1  # Requires object simulation
T5 = 0  # Impossible (worst)
```

### Step 5: Scoring
**File**: `uct_benchmark/data/basicScoringFunction.py` → `basicScoring()`

Evaluates data quality based on:
- **Orbital Coverage**: Percentage of orbit observed
- **Observation Count**: Number of observations per period
- **Track Gap**: Longest duration between observations
- **Object Completeness**: Number of objects meeting criteria

Returns a tier classification (T1-T5) that determines subsequent processing.

### Step 5b: Tier-Based Processing

Based on the tier classification, additional processing is applied:

#### T1/T2: Downsampling
**File**: `uct_benchmark/data/dataManipulation.py` → `downsampleData()`

When data quality is too high, downsampling reduces it to target levels:
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

#### T3: Observation Simulation
**File**: `uct_benchmark/simulation/simulateObservations.py` → `epochsToSim()`, `simulateObs()`

When data quality is insufficient, synthetic observations are added:
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

#### T4: Object Simulation (Not Yet Implemented)
For very sparse data, entire synthetic satellites may need to be generated.

### Step 6: Reference State Pull
**File**: `uct_benchmark/api/apiIntegration.py` → `pullStates()`

For selected window, retrieves:
- Reference State Vectors (position, velocity, covariance)
- Reference TLEs (Two-Line Elements)
- Satellite physical parameters (mass, cross-section)

### Step 7: Dataset Save
**File**: `uct_benchmark/api/apiIntegration.py` → `saveDataset()`

Creates output JSON with structure:
```json
{
  "dataset_obs": [...],      // Decorrelated observations (UCTs)
  "dataset_elset": [...],    // Decorrelated TLEs
  "reference": [...]         // Ground truth with correlations
}
```

---

## Phase 2: UCTP Processing

### UCTP Interface
**File**: `uct_benchmark/uctp/dummyUCTP.py`

UCTP algorithms receive:
- **Input**: Decorrelated observations (no satNo identification)
- **Task**: Associate observations and fit orbits

UCTP algorithms output:
- State vectors for each identified object
- Observation-to-object associations
- Covariance estimates

### Current Implementation: Dummy UCTP

The dummy UCTP simulates realistic output for testing:
```python
# Probability distribution for dummy output
60% → True Positive (correct association)
10% → False Negative (missed detection)
30% → False Positive (incorrect association)
```

---

## Phase 3: Evaluation

### Step 1: Data Loading
**File**: `uct_benchmark/api/apiIntegration.py` → `loadDataset()`

Loads:
- Reference observations with ground truth
- UCTP output state vectors
- Association results

### Step 2: Orbit Association
**File**: `uct_benchmark/evaluation/orbitAssociation.py` → `orbitAssociation()`

Associates UCTP output with reference orbits:
1. Propagate reference states to UCTP output epochs
2. Compute position error between each pair
3. Solve Hungarian algorithm for optimal assignment
4. Identify associated and non-associated orbits

### Step 3: Binary Metrics
**File**: `uct_benchmark/evaluation/binaryMetrics.py` → `binaryMetrics()`

Classification metrics:
- True Positives (TP)
- False Positives (FP)
- False Negatives (FN)
- Precision, Recall, F1-Score

### Step 4: State Metrics
**File**: `uct_benchmark/evaluation/stateMetrics.py` → `stateMetrics()`

Orbital state comparison:
- Position error (km)
- Velocity error (km/s)
- Covariance consistency
- Monte Carlo propagation for uncertainty

### Step 5: Residual Metrics
**File**: `uct_benchmark/evaluation/residualMetrics.py` → `residualMetrics()`

Observation residual analysis:
- RA/Dec residuals
- Range/Range-rate residuals (if applicable)
- RMS statistics

### Step 6: Report Generation
**File**: `uct_benchmark/utils/generatePDF.py` → `generatePDF()`

Creates PDF report containing:
- Summary statistics
- Performance charts
- Detailed metrics tables

---

## Data Flow Diagram

```
                    ┌─────────────────────┐
                    │    UDL (Primary)    │
                    │   - Observations    │
                    │   - State Vectors   │
                    │   - TLEs            │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Space-Track  │     │   CelesTrak   │     │ ESA DiscoWeb  │
│  (TLEs)       │     │  (Satcat)     │     │ (Mass/Area)   │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   API Integration   │
                    │  (apiIntegration.py)│
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
          ┌─────────────────┐   ┌─────────────────┐
          │  Observations   │   │  Reference      │
          │  DataFrame      │   │  States/TLEs    │
          └────────┬────────┘   └────────┬────────┘
                   │                     │
                   └──────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Window Selection  │
                    │   & Scoring         │
                    └──────────┬──────────┘
                               │
                              ▼
                    ┌─────────────────────┐
                    │   Dataset JSON      │
                    │   - Decorrelated    │
                    │   - Reference       │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌────────────┐  ┌────────────┐  ┌────────────┐
       │ Training   │  │   UCTP     │  │   Held     │
       │ Set        │  │ Algorithm  │  │   Out Set  │
       └────────────┘  └─────┬──────┘  └────────────┘
                             │
                             ▼
                    ┌─────────────────────┐
                    │   UCTP Output       │
                    │   State Vectors     │
                    └──────────┬──────────┘
                               │
                              ▼
                    ┌─────────────────────┐
                    │    Evaluation       │
                    │   - Association     │
                    │   - Metrics         │
                    └──────────┬──────────┘
                               │
                              ▼
                    ┌─────────────────────┐
                    │   PDF Report        │
                    └─────────────────────┘
```

---

## Key Files Summary

| Phase | File | Purpose |
|-------|------|---------|
| 1 | `Create_Dataset.py` | Main driver for dataset creation |
| 1 | `windowCheck.py` | Window selection algorithm |
| 1 | `windowTools.py` | GUI and code generation |
| 1 | `basicScoringFunction.py` | Data quality scoring |
| 1 | `apiIntegration.py` | API calls and data saving |
| 1 | `dataManipulation.py` | **T1/T2 Downsampling** (3-stage pipeline) |
| 1 | `simulateObservations.py` | **T3 Simulation** (epoch selection + obs generation) |
| 1 | `propagator.py` | Orbit propagation for simulation |
| 2 | `MainMVP.py` | UCTP execution driver |
| 2 | `dummyUCTP.py` | Test UCTP implementation |
| 3 | `Evaluation.py` | Main evaluation driver |
| 3 | `orbitAssociation.py` | Orbit matching |
| 3 | `binaryMetrics.py` | Classification metrics |
| 3 | `stateMetrics.py` | State comparison |
| 3 | `residualMetrics.py` | Residual analysis |
| 3 | `generatePDF.py` | Report generation |

---

## Configuration Parameters

See `uct_benchmark/settings.py` for adjustable parameters:
- Orbital regime thresholds
- Scoring thresholds
- Propagator settings
- Simulation noise parameters
- **Downsampling configuration** (T1/T2):
  - `downsample_coverage_bounds`, `downsample_coverage_target`
  - `downsample_gap_bounds`, `downsample_gap_target`
  - `downsample_obs_bounds`, `downsample_obs_max`
- **T3 Simulation configuration**:
  - `simulation_bins_per_period`, `simulation_min_obs_per_bin`
  - `simulation_max_ratio`, `simulation_target_increase`
  - `simulation_track_size`, `simulation_track_spacing`

See [CONFIGURATION.md](CONFIGURATION.md) for detailed parameter documentation.
