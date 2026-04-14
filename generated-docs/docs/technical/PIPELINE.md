# Data Pipeline and Flow

<!-- AI_METADATA
purpose: High-level overview of the UCT Benchmark data pipeline and flow
status: active
related_files: [technical/PIPELINE_DEEP_DIVE.md, technical/ARCHITECTURE.md, technical/CONFIGURATION.md]
last_updated: 2026-04-14
-->

## Overview

The UCT Benchmarking pipeline transforms raw observational data from space surveillance networks into standardized benchmark datasets for evaluating Uncorrelated Track Processing (UCTP) algorithms.

<!-- AI_SECTION: pipeline_phases -->

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

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: phase1_dataset_creation -->

## Phase 1: Dataset Creation (Detailed Step Order)

The `generateDataset()` function in `apiIntegration.py` executes the following steps in order. Each step is described below.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  generateDataset() — FULL PIPELINE                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Step 1   Calculate Time Window                                          │
│     │                                                                    │
│     ▼                                                                    │
│  Step 2   Fetch Observations (with fallback strategy)                    │
│     │                                                                    │
│     ▼                                                                    │
│  Step 3   Resilient Satellite Filtering                                  │
│     │     (skip satellites with no data, continue with the rest)         │
│     ▼                                                                    │
│  Step 4   Query State Vectors                                            │
│     │                                                                    │
│     ▼                                                                    │
│  Step 5   Query TLEs                                                     │
│     │                                                                    │
│     ▼                                                                    │
│  Step 6   Window Selection Algorithm (optional)                          │
│     │                                                                    │
│     ▼                                                                    │
│  Step 7   Object Type Filtering (optional)                               │
│     │                                                                    │
│     ▼                                                                    │
│  Step 8   Target Percentage Enforcement (optional)                       │
│     │                                                                    │
│     ▼                                                                    │
│  Step 9   Event Filtering (optional)                                     │
│     │                                                                    │
│     ▼                                                                    │
│  Step 10  Downsampling — T1/T2 (tier-driven)                             │
│     │                                                                    │
│     ▼                                                                    │
│  Step 11  Simulation — T3 (tier-driven)                                  │
│     │                                                                    │
│     ▼                                                                    │
│  Step 12  True Negative Addition (non-reference observations)            │
│     │                                                                    │
│     ▼                                                                    │
│  Step 13  Track Binning                                                  │
│     │                                                                    │
│     ▼                                                                    │
│  Step 14  TrackTLE Generation (optional)                                 │
│     │                                                                    │
│     ▼                                                                    │
│  Step 15  Decorrelation (satNo removal + answer key)                     │
│     │                                                                    │
│     ▼                                                                    │
│  Step 16  Output / Persist                                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### Step 1: Calculate Time Window

**File**: `uct_benchmark/api/apiIntegration.py` — top of `generateDataset()`

Converts user-supplied `timeframe`, `timeunit`, and `end_time` into concrete UTC start/end timestamps used for all subsequent API queries.

- If `end_time` is `"now"`, uses the current UTC time.
- Otherwise, uses the caller-supplied datetime and computes the start via `end_time - Timedelta(timeframe)`.
- Produces the UDL-formatted `sweep_time` range string (e.g. `">now-7 days"` or `"2026-01-01T00:00:00Z..2026-01-08T00:00:00Z"`).

---

### Step 2: Fetch Observations (with Fallback Strategy)

**File**: `uct_benchmark/api/apiIntegration.py` — `_fetch_observations_fast()`, `_fetch_observations_windowed()`, `_fetch_observations_hybrid()`

Queries the Unified Data Library (UDL) for observation records. Three strategies are available, controlled by the `search_strategy` parameter:

| Strategy   | How It Works                                                                 |
|------------|-----------------------------------------------------------------------------|
| `fast`     | Single batch query per satellite using `satNo` filter                       |
| `windowed` | Time-based chunked query in `window_size_minutes`-minute intervals          |
| `hybrid`   | Tries `fast` first; falls back to `windowed` if no results are returned     |

**Automatic fallback**: If the selected strategy (fast or hybrid) returns zero observations, the pipeline automatically retries with the `windowed` strategy. This handles cases where satellite-number-based queries fail but time-based queries succeed.

---

### Step 3: Resilient Satellite Filtering

**File**: `uct_benchmark/api/apiIntegration.py` — "RESILIENT SATELLITE FILTERING" block

This step prevents the pipeline from failing when some of the requested satellites have no observation data in UDL. This is documented as the **number-one failure mode in production** -- randomly selected satellites often have no recent observations.

**How it works:**

1. After observations are fetched, the pipeline identifies which of the requested `satIDs` actually have rows in the returned DataFrame.
2. Satellites with zero observations are logged as warnings and **skipped** rather than causing the entire pipeline to error.
3. The `satIDs` list is culled to include only satellites that returned data.
4. A post-fetch date filter removes any observations outside the requested `[start, end]` range (the UDL API can return slightly out-of-range records).

**Failure conditions:**
- If *zero* satellites have any data, a `ValueError` is raised with a diagnostic message suggesting the user expand the time range or pick different satellites.
- If some satellites are missing, a warning is logged listing the skipped NORAD IDs, and the pipeline continues with the remainder.

```
Requested: [25544, 28654, 99999, 12345]
                │
                ▼
   UDL returns data for: [25544, 28654]
   No data for:          [99999, 12345]  ← logged as warning, skipped
                │
                ▼
   Pipeline continues with satIDs = [25544, 28654]
```

---

### Step 4: Query State Vectors

**File**: `uct_benchmark/api/apiIntegration.py` — `asyncUDLBatchQuery()` for `"statevector"`

For each satellite that survived Step 3, queries UDL for state vectors (position, velocity, covariance) within the sweep time range.

- Duplicate state vectors are deduplicated, preferring records that include covariance data.
- The most recent state vector with covariance is kept per satellite.
- Drag coefficient and solar radiation pressure coefficient are filled with defaults if missing.
- Physical parameters (mass, cross-sectional area) are retrieved from ESA Discosweb. If no ESA token is available, reasonable defaults are applied (1000 kg, 10 m^2).
- If a satellite has observations but no state vector, it is dropped from all downstream data.

---

### Step 5: Query TLEs

**File**: `uct_benchmark/api/apiIntegration.py` — `UDLQuery()` for `"elset/current"` or `asyncUDLBatchQuery()` for `"elset"`

Retrieves Two-Line Element sets for each satellite.

- If `end_time == "now"`, uses the `elset/current` endpoint (single batch call).
- Otherwise, queries individual TLEs within the sweep time range.
- **Fallback**: If the time-ranged query returns empty, falls back to `elset/current`.
- TLE lines are parsed into orbital elements via `parseTLE()`.
- If a satellite has observations and state vectors but no TLE, it is dropped from all downstream data.

---

### Step 6: Window Selection Algorithm (Optional)

**File**: `uct_benchmark/data/windowCheck.py` — `find_optimal_window()`

Enabled when `use_window_selection=True`. Uses a bisecting search to find the optimal sub-window within the fetched observation batch.

1. **Bisection**: Recursively divides the batch to find high-quality sub-regions.
2. **Sliding window**: Fine-tunes window position for optimal score.
3. **Tier assignment**: Maps the window quality to a data tier (`T1`-`T4`), which controls later downsampling/simulation behavior.

If window selection fails, the pipeline logs a warning and continues with the full time range.

---

### Step 7: Object Type Filtering (Optional)

**File**: `uct_benchmark/api/apiIntegration.py` — `filter_by_object_type_code()`

Controlled by the `object_type_code` parameter (positions in the 16-character dataset code):

| Code | Meaning          | Description                                                |
|------|------------------|------------------------------------------------------------|
| `U`  | Unspecified      | No filtering applied (default)                             |
| `H`  | HAMR             | High Area-to-Mass Ratio objects only                       |
| `C`  | Close            | Close-proximity objects (physical proximity filtering)     |
| `A`  | Apparent         | Apparent-magnitude-based filtering                         |
| `N`  | Calibration      | Calibration objects only                                   |

When code is not `U`, satellites and their observations are filtered based on physical properties (mass, cross-section), orbital elements, and state data. The `satIDs`, `state_truth_data`, and `elset_truth_data` are all updated to reflect the filtered set.

---

### Step 8: Target Percentage Enforcement (Optional)

**File**: `uct_benchmark/api/apiIntegration.py` — `enforce_target_percentage()`

Controlled by the `target_percentage` parameter (positions 2-3 of the 16-character dataset code). This step adjusts the ratio of "target" (correlated) objects to "UCT" (uncorrelated) objects in the final dataset.

**How it works:**

1. The step receives the list of satellites that matched the object type filter (from Step 7) as the "target" set and all current satellites as the full pool.
2. It enforces a specific fraction of the dataset's objects to be from the target set.
3. If too many target objects exist, excess targets are randomly removed. If too few exist, additional non-target objects are added or target objects are supplemented.
4. After enforcement, `satIDs`, `state_truth_data`, and `elset_truth_data` are updated.

**Parameter values:**

| Value | Meaning                                               |
|-------|-------------------------------------------------------|
| `UN`  | Unspecified -- no enforcement applied (default)       |
| `25`  | 25% of objects should be targets                      |
| `50`  | 50% of objects should be targets                      |
| `75`  | 75% of objects should be targets                      |

**Precondition**: Only applied when `object_type_code` is not `U` (since targets are defined by the object type filter).

---

### Step 9: Event Filtering (Optional)

**File**: `uct_benchmark/api/apiIntegration.py` — `filter_satellites_by_event_code()`

Controlled by the `event_code` parameter. This step filters the dataset to include only satellites that have experienced (or not experienced) specific orbital events within the observation window.

**How it works:**

1. The filter examines TLE data (`elset_truth_data`) for each satellite to detect orbital events (maneuvers, breakups, long-duration thrusts).
2. Only satellites matching the requested event type are retained.
3. If no satellites match the event code, a warning is logged and the pipeline continues with all satellites (graceful degradation).

**Event codes:**

| Code | Event Type    | Description                                                    |
|------|---------------|----------------------------------------------------------------|
| `NE` | No Events     | Default -- no event filtering applied                          |
| `MB` | Maneuver      | Include only satellites that performed orbital maneuvers       |
| `BU` | Breakup       | Include only satellites involved in breakup events             |
| `LL` | Long Thrust   | Include only satellites with long-duration thrust events       |

**Failure handling**: If event filtering raises an exception, the pipeline logs a warning and continues with unfiltered data.

---

### Step 10: Downsampling (T1/T2) -- Tier-Driven

**File**: `uct_benchmark/data/dataManipulation.py` — `apply_downsampling()`

Automatically enabled for tiers T2, T3, and T4. Disabled for T1 (data quality already sufficient). Reduces observation density to match the target tier's quality profile.

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

---

### Step 11: Simulation (T3) -- Tier-Driven

**File**: `uct_benchmark/data/dataManipulation.py` — `apply_simulation_to_gaps()`

Automatically enabled for tiers T3 and T4. Fills observation gaps with synthetic observations.

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
For very sparse data, entire synthetic satellites may need to be generated. T4 currently behaves identically to T3.

<!-- AI_IMPROVEMENT_OPPORTUNITY: T4 object simulation is not implemented. See planning/FUTURE_IMPLEMENTATIONS.md for details. -->

---

### Step 12: True Negative Addition

**File**: `uct_benchmark/api/apiIntegration.py` — `add_non_reference_observations()`

Enabled when `include_non_ref_obs=True`. Adds observations from satellites that are **not** in the reference set. These serve as True Negatives during evaluation -- observations that a correct UCTP algorithm should *not* associate with any known reference orbit.

- Queries UDL for additional observations in the same time window.
- Selects satellites not in the reference `satIDs` list.
- Adds exactly 2 observations per non-reference satellite (per Louis's spec, this makes Initial Orbit Determination impossible).
- The `non_ref_ratio` parameter controls how many non-reference observations to add relative to the reference count (default 10%).

---

### Step 13: Track Binning

**File**: `uct_benchmark/api/apiIntegration.py` — `binTracks()`

Groups observations into artificial track bins based on temporal proximity. Each bin represents a contiguous observation arc for a single satellite.

- Assigns a `trackId` and `origObjectId` to each observation in the decorrelated dataset.
- These IDs replace the removed `satNo` so that UCTP algorithms can see track structure without knowing true identity.

---

### Step 14: TrackTLE Generation (Optional)

**File**: `uct_benchmark/simulation/tracktle.py` — `generate_tracktle()`

Enabled when `output_tracktle=True`. Performs Initial Orbit Determination (IOD) on each satellite's observation track to produce a fitted TLE.

- Requires at least 3 observations per satellite.
- Outputs TLE line pairs, convergence status, RMS residuals, and iteration count.
- Failures for individual satellites are logged as warnings; the pipeline continues.

---

### Step 15: Decorrelation

**File**: `uct_benchmark/api/apiIntegration.py` — answer key generation + column removal

The decorrelation step removes identifying metadata so that UCTP algorithms cannot trivially correlate observations:

1. **Answer key generation**: Maps each observation `id` to its true `satNo`. Stored separately for evaluation.
2. **Column removal**: Drops `satNo`, `idOnOrbit`, `origObjectId`, `rawFileURI`, `createdAt`, `trackId`, `is_non_reference`, and other identifying columns from the dataset output.
3. **Shuffle**: The dataset is randomly shuffled to prevent ordering-based correlation.

---

### Step 16: Output / Persist

**File**: `uct_benchmark/api/apiIntegration.py` — end of `generateDataset()`

Returns the final artifacts:

| Return Value        | Description                                            |
|---------------------|--------------------------------------------------------|
| `dataset`           | Decorrelated observations (UCTs) -- no `satNo`         |
| `obs_truth_data`    | Truth observations with `satNo` intact                 |
| `state_truth_data`  | Reference state vectors (position, velocity, covariance) |
| `elset_truth_data`  | Reference TLEs (Two-Line Elements)                     |
| `satIDs`            | Array of satellite NORAD IDs that made it through      |
| `performance_data`  | Dict with timing, tier, metadata from all steps        |

If `use_database=True`, all data is also persisted to a DuckDB database.

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: phase2_uctp_processing -->

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

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: phase3_evaluation -->

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

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: data_flow -->

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
                    │  Resilient Filter   │
                    │  (skip missing)     │
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
                    │  Object Type /      │
                    │  Target % / Event   │
                    │  Filtering          │
                    └──────────┬──────────┘
                               │
                              ▼
                    ┌─────────────────────┐
                    │  Downsample / Sim   │
                    │  (Tier-Driven)      │
                    └──────────┬──────────┘
                               │
                              ▼
                    ┌─────────────────────┐
                    │  True Negatives +   │
                    │  Track Binning +    │
                    │  Decorrelation      │
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

<!-- /AI_SECTION -->

---

<!-- AI_SECTION: key_files -->

## Key Files Summary

| Phase | File | Purpose |
|-------|------|---------|
| 1 | `Create_Dataset.py` | Main driver for dataset creation |
| 1 | `apiIntegration.py` | API calls, pipeline orchestration, data saving |
| 1 | `windowCheck.py` | Window selection algorithm |
| 1 | `windowTools.py` | GUI and code generation |
| 1 | `basicScoringFunction.py` | Data quality scoring |
| 1 | `dataManipulation.py` | **T1/T2 Downsampling** (3-stage pipeline) |
| 1 | `simulateObservations.py` | **T3 Simulation** (epoch selection + obs generation) |
| 1 | `propagator.py` | Orbit propagation for simulation |
| 1 | `tracktle.py` | TrackTLE generation from observation tracks |
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
- **Event filtering**: `event_code` (NE, MB, BU, LL)
- **Target percentage**: `target_percentage` (UN, 25, 50, 75)
- **Object type**: `object_type_code` (U, H, C, A, N)

See [CONFIGURATION.md](CONFIGURATION.md) for detailed parameter documentation.

<!-- /AI_SECTION -->
