# V1 Fixes Master Plan

## Document Purpose

This document provides a comprehensive, actionable plan for completing the UCT Benchmarking pipeline to a production-ready "V1" state. All items are derived from the **initial meeting with tech lead Lewis on August 28, 2025**, where he provided detailed guidance on project priorities, current gaps, and future goals.

---

## Executive Summary

Based on Lewis's meeting transcript, the project has strong foundational infrastructure but requires focused work in these critical areas:

| Priority | Area | Current State | Target State |
|----------|------|---------------|--------------|
| P0 | UCTP Validation | Not validated | Validated with Aerospace Corp UCTP |
| P1 | T3 Processing | **✅ 100% functional** | 100% functional |
| P1 | T4 Processing | 0% | 100% functional |
| P1 | T1/T2 Downsampling | **✅ 100% functional** | 100% functional |
| P2 | PDF Report Quality | 80% ("needs work") | Professional quality |
| P2 | Noise Modeling | Basic Gaussian | Realistic (atm. refraction, aberration) |
| P3 | Event Labeling | 0% (IU team work pending) | Integrated |
| P4 | Open Evolve | Not started | Architecture designed |

---

## Source of Truth: Key Quotes from Lewis (August 28, 2025)

### On Project Purpose
> "We're trying to build a common task framework for uncorrelated track processing, and that starts by building a series of standardized data sets that all have a known solution. We can feed those same data sets into many different uncorrelated track processors."

### On What We're NOT Building
> "The thing about this pipeline is we are building the data sets. We are building a way to evaluate the output of the UCTP. We're not actually building the uncorrelated track processor. So we don't get to dictate what their output is going to look like."

### On Validation Status
> "We still need to verify that our pipeline works with actual UCT processor output."
> "This looks kind of sporadic because like I mentioned before, it's just random data to validate that the algorithm works. This is not actually representative of a UCT processor."

### On Current Gaps
> "A lot of our algorithms, we just kind of threw them together rather haphazardly. They're not super efficient. There's probably a lot of room for adding more efficiency."
> "The PDF report needs some work. We want that to look nice by the time we're done with it."

### On Noise Modeling
> "For the simulation piece, we want to be able to more accurately represent sources of uncertainty and noise in the telescope systems. Right now we just added a constant Gaussian blur... there's also other sources of uncertainty, such as atmospheric refraction or stellar aberration that were not accounted for in the simulation."

### On Validation Contact
> "Patrick Ramsey works with Aerospace Corp, and he's been working with us to try and process some of our data sets. So when we get to a point where we've got the data set generation pipeline working well, we can generate some data sets. We'll get a hold of Patrick Ramsey and we'll see if he can help us run some of this data on his UCT processor."

### On Future Goals (Open Evolve)
> "There's this program called Open Evolve, which is a way to optimize code bases using an AI agent. It's an iterative cycle of querying LLM to suggest modifications to a code base followed by an evaluation program that'll say how well that the code performed."

### On General Advice
> "Something that's not great is better than something that doesn't exist. You can always go back and make things better, but before you can make things better, you have to make them work. So the first thing we got to do is we got to make this thing work."

---

## Priority 0: Critical Path - UCTP Validation

### Background
The entire evaluation pipeline is currently untested against real UCT processor output. All current testing uses simulated/random data. Per Lewis, validation with Aerospace Corp's UCTP is essential.

### TODO 0.1: Establish Contact with Patrick Ramsey
**Importance**: CRITICAL - Blocking for all validation work
**Effort**: Low (communication)
**Dependencies**: None

**Actions**:
- [ ] Contact Atulya to get Patrick Ramsey's contact information
- [ ] Draft introduction email explaining current project status
- [ ] Schedule initial meeting to discuss validation collaboration
- [ ] Document Aerospace Corp's UCTP input/output format requirements

**Success Criteria**: Meeting scheduled with Patrick Ramsey

---

### TODO 0.2: Prepare Validation Dataset Package
**Importance**: CRITICAL - Required for validation
**Effort**: Medium
**Dependencies**: T3/T4 processing should be functional (or use T1/T2 only)

**Actions**:
- [ ] Generate 3-5 benchmark datasets of varying complexity:
  - [ ] 1x LEO T1 dataset (high quality, minimal processing needed)
  - [ ] 1x LEO T2 dataset (requires downsampling)
  - [ ] 1x GEO T1 dataset (different orbital regime)
  - [ ] 1x MEO T2 dataset (if data available)
- [ ] Document each dataset's characteristics:
  - Object count
  - Observation count
  - Time window
  - Orbital regimes
  - Data quality tier
- [ ] Package datasets in format suitable for Aerospace Corp
- [ ] Include ground truth reference data (for our evaluation)

**Deliverables**:
- `validation_datasets/` folder with 3-5 datasets
- `validation_datasets/README.md` documenting each dataset
- JSON format matching UCTP input requirements

---

### TODO 0.3: Run Validation Against Real UCTP Output
**Importance**: CRITICAL - Proves pipeline works
**Effort**: High
**Dependencies**: 0.1, 0.2 complete; Aerospace Corp processes our data

**Actions**:
- [ ] Send prepared datasets to Patrick Ramsey
- [ ] Receive UCTP output from Aerospace Corp
- [ ] Run our evaluation pipeline on real UCTP output
- [ ] Compare results to expected outcomes
- [ ] Document any discrepancies or issues
- [ ] Iterate on fixes until evaluation produces valid results

**Success Criteria**:
- Evaluation pipeline produces meaningful metrics on real UCTP output
- Binary metrics (precision, recall, F1) are reasonable
- State metrics (position/velocity error) are in expected ranges
- PDF report generates without errors

---

## Priority 1: Core Pipeline Completion

### Background
Lewis identified several incomplete pieces of the data generation pipeline. The tier system (T1-T5) determines data quality and what processing is needed:

| Tier | Quality | Processing Required | Current Status |
|------|---------|---------------------|----------------|
| T1 | High | May need downsampling | **✅ Implemented** (2026-01-18) |
| T2 | Good | Requires downsampling | **✅ Implemented** (2026-01-18) |
| T3 | Moderate | Requires observation simulation | **✅ Implemented** (2026-01-18) |
| T4 | Low | Requires object simulation | **Not implemented** |
| T5 | Unusable | Cannot create valid dataset | N/A |

---

### TODO 1.1: Complete T3 Processing (Observation Simulation) ✅ COMPLETE
**Importance**: HIGH - Core functionality
**Effort**: Medium-High
**Dependencies**: None (framework exists)
**Status**: ✅ **COMPLETED 2026-01-18**

---

#### Implementation Summary (Completed 2026-01-18)

**What was implemented:**

1. **Complete `epochsToSim()` function** (`simulateObservations.py:358-507`)
   - Time-bin based approach: divides observation window by orbital period
   - Identifies empty bins (gaps in coverage)
   - Generates epochs in tracks (realistic grouping of 3 obs per track)
   - Returns detailed statistics for logging

2. **T3 simulation config parameters** (`config.py:164-188`)
   - `simulation_bins_per_period = 10`
   - `simulation_max_ratio = 0.5`
   - `simulation_track_size = 3`
   - `simulation_track_spacing = 30`
   - `simulation_min_existing_obs = 3`

3. **T3 integration in `Create_Dataset.py`** (lines 66-175)
   - Loads sensor data from `sensorCounts.csv`
   - Calls `epochsToSim()` for each satellite
   - Generates state vectors from orbital elements
   - Calls `simulateObs()` to create observations
   - Marks simulated obs with `dataMode='SIMULATED'`

4. **Test suite** (`test_simulation.py`)
   - Tests epochsToSim() with sparse data (3/3 pass)
   - Tests with real sample data
   - Tests full simulation flow

**Test Results:**
```
Simulation test: 3/3 tests passed
Pipeline test: 8/8 stages passed
```

---

**Original Problem Description** (per Lewis):
> "If there's not enough data, not enough objects, then we need to sample data or simulate data. That's not ideal. We want to try and use as much real data as possible. But if the user really wants that type of data and we can't find it, then we do have infrastructure to be able to simulate new observations."

**Actions**:

#### 1.1.1: Complete `epochsToSim()` Function
**File**: `uct_benchmark/simulation/simulateObservations.py`
**Lines**: ~360-428 (function exists but incomplete)

- [ ] Analyze existing `epochsToSim()` implementation
- [ ] Determine required epochs based on:
  - Current observation coverage percentage
  - Desired observation count
  - Orbital period of object
  - Time window constraints
- [ ] Implement coverage-aware epoch selection
- [ ] Return list of epochs where new observations should be simulated

**Algorithm Design**:
```
Input:
  - existing_observations: DataFrame of current obs
  - target_coverage: float (0.0-1.0)
  - target_obs_count: int
  - orbital_period: float (seconds)
  - time_window: (start, end)

Process:
  1. Calculate current coverage percentage
  2. Identify gaps in orbital coverage
  3. Determine how many additional observations needed
  4. Select epochs that would fill coverage gaps
  5. Prioritize epochs evenly distributed across orbit

Output:
  - List of datetime epochs to simulate
```

#### 1.1.2: Integrate Simulation into Create_Dataset.py
**File**: `uct_benchmark/Create_Dataset.py`

- [ ] After window selection identifies T3 data:
  - [ ] For each satellite with insufficient observations:
    - [ ] Call `epochsToSim()` to get epochs needing simulation
    - [ ] Call `simulateObs()` to generate synthetic observations
    - [ ] Merge simulated observations with real observations
    - [ ] Recalculate quality score to verify improvement
  - [ ] Update dataset metadata to indicate which obs are simulated

**Integration Code Structure**:
```python
if tierThreshold == "T3":
    logger.info("T3 processing: simulating additional observations")

    for sat_id in satellites_needing_simulation:
        # Get satellite's existing observations
        sat_obs = observations[observations['satNo'] == sat_id]

        # Determine what epochs need simulation
        epochs_to_sim = epochsToSim(
            existing_obs=sat_obs,
            target_coverage=config.standardPercentage[1],
            orbital_period=orbital_periods[sat_id],
            time_window=(window_start, window_end)
        )

        # Simulate observations at those epochs
        simulated = simulateObs(
            sat_id=sat_id,
            epochs=epochs_to_sim,
            state_vector=reference_states[sat_id],
            sensors=available_sensors
        )

        # Mark as simulated and merge
        simulated['dataMode'] = 'SIMULATED'
        observations = pd.concat([observations, simulated])

    # Recalculate score
    new_score = basicScoring(code, observations, satData)
    logger.info(f"Score improved from {old_score} to {new_score}")
```

#### 1.1.3: Test T3 Processing
- [ ] Create test case with known sparse dataset
- [ ] Run T3 processing and verify:
  - [ ] Correct number of observations simulated
  - [ ] Simulated observations are physically realistic
  - [ ] Coverage percentage improves as expected
  - [ ] Dataset can still be evaluated correctly

**Success Criteria**:
- T3 datasets can be generated automatically
- Simulated observations are marked appropriately
- Quality score improves after simulation
- Evaluation works on mixed real/simulated data

---

### TODO 1.2: Implement T4 Processing (Object Simulation)
**Importance**: HIGH - Core functionality
**Effort**: High
**Dependencies**: T3 processing should work first

**Current State** (from `Create_Dataset.py:104-107`):
```python
if tierThreshold == "T4":
    logger.info("T4 processing not implemented; continuing")
```

**Problem Description** (per Lewis):
When there aren't enough real objects meeting the criteria, we need to simulate entirely new synthetic objects with their own observations.

**Actions**:

#### 1.2.1: Create `simulateObjects.py` Module
**File**: New file `uct_benchmark/simulation/simulateObjects.py`

- [ ] Design object simulation strategy
- [ ] Implement functions:

```python
def determineObjectsNeeded(current_count: int, target_count: int,
                           regime: str, criteria: dict) -> int:
    """Calculate how many synthetic objects are needed."""
    pass

def generateSyntheticOrbit(regime: str, constraints: dict) -> dict:
    """
    Generate realistic orbital elements for a synthetic object.

    Parameters:
    - regime: 'LEO', 'MEO', 'GEO', 'HEO'
    - constraints: dict with eccentricity range, inclination range, etc.

    Returns:
    - dict with orbital elements (a, e, i, RAAN, argp, M)
    """
    pass

def generateSyntheticTLE(orbital_elements: dict, epoch: datetime) -> tuple:
    """Convert orbital elements to TLE format."""
    pass

def simulateObjectObservations(tle: tuple, time_window: tuple,
                               obs_count: int, sensors: list) -> DataFrame:
    """Generate observations for a synthetic object."""
    pass

def createSyntheticObject(regime: str, time_window: tuple,
                          target_obs_count: int) -> dict:
    """
    Main function to create a complete synthetic object.

    Returns dict with:
    - orbital_elements
    - tle_lines
    - state_vector
    - observations
    - metadata
    """
    pass
```

#### 1.2.2: Design Realistic Orbit Generation

For each orbital regime, define realistic parameter ranges:

**LEO (Low Earth Orbit)**:
- Semi-major axis: 6578-8378 km (200-2000 km altitude)
- Eccentricity: 0.0-0.1 (mostly circular)
- Inclination: 0-98 degrees
- Common inclinations: 28.5° (Cape Canaveral), 51.6° (ISS), 97-98° (sun-sync)

**MEO (Medium Earth Orbit)**:
- Semi-major axis: 8378-35786 km
- Eccentricity: 0.0-0.3
- Inclination: 0-90 degrees
- Common: GPS at ~20,200 km, 55° inclination

**GEO (Geostationary)**:
- Semi-major axis: ~42,164 km
- Eccentricity: <0.001
- Inclination: <1 degree

**HEO (Highly Elliptical)**:
- Semi-major axis: varies widely
- Eccentricity: 0.6-0.9
- Example: Molniya orbits (63.4° inclination, 12-hour period)

#### 1.2.3: Integrate into Create_Dataset.py

```python
if tierThreshold == "T4":
    logger.info("T4 processing: simulating additional objects")

    objects_needed = determineObjectsNeeded(
        current_count=len(current_objects),
        target_count=config.standardObjectCount,
        regime=requested_regime,
        criteria=dataset_code
    )

    for i in range(objects_needed):
        synthetic = createSyntheticObject(
            regime=requested_regime,
            time_window=(window_start, window_end),
            target_obs_count=config.lowObsCount
        )

        # Add to reference data
        reference_states.append(synthetic['state_vector'])
        reference_tles.append(synthetic['tle_lines'])

        # Add observations (marked as synthetic)
        synthetic['observations']['dataMode'] = 'SYNTHETIC_OBJECT'
        observations = pd.concat([observations, synthetic['observations']])

    logger.info(f"Added {objects_needed} synthetic objects")
```

#### 1.2.4: Test T4 Processing
- [ ] Create test case requesting more objects than available
- [ ] Verify synthetic objects have realistic orbital parameters
- [ ] Verify synthetic observations are physically plausible
- [ ] Verify evaluation works correctly with synthetic objects

**Success Criteria**:
- T4 datasets can be generated automatically
- Synthetic objects are distinguishable in metadata
- Orbital parameters are realistic for requested regime
- Dataset evaluation produces valid results

---

### TODO 1.3: Implement Downsampling (T1/T2) ✅ COMPLETE
**Importance**: HIGH - Core functionality
**Effort**: Medium
**Dependencies**: None
**Status**: ✅ **COMPLETED 2026-01-18**

**Problem Description** (per Lewis):
> "If we've got a lot of data and we need to emulate a sparser data set, we can downsample."

T1 and T2 data has MORE observations than needed, requiring intelligent removal.

---

#### Implementation Summary (Completed 2026-01-18)

**What was implemented:**

1. **Configuration parameters added to `uct_benchmark/config.py`:**
   - `downsample_coverage_bounds = (0.3, 0.5, 0.7)` - (min%, target%, max%) of sats to downsample
   - `downsample_coverage_target = (0.15, 0.05)` - (max, min) orbital coverage threshold
   - `downsample_gap_bounds = (0.3, 0.5, 0.7)` - (min%, target%, max%) of sats to downsample
   - `downsample_gap_target = 2.0` - Target max gap (2 orbital periods)
   - `downsample_obs_bounds = (0.3, 0.5, 0.7)` - (min%, target%, max%) of sats to downsample
   - `downsample_obs_max = 50` - Max observations per sat per 3 days
   - `downsample_min_obs = 5` - Minimum observations to keep per satellite

2. **Integration in `src/Create_Dataset.py` (lines 71-120):**
   ```python
   if tierThreshold in ['T1', 'T2']:
       print(f'Applying {tierThreshold} downsampling...')
       observations, p_reached = dataM.downsampleData(
           observations, orbElms,
           orbit_coverage_params, track_length_params, obs_count_params,
           bins=10, rand=42
       )
   ```

3. **Bug fixes during implementation:**
   - Fixed `dataManipulation.py:627` - pandas set indexer bug (changed `gap_df.loc[insufficient_sats]` to `gap_df.loc[list(insufficient_sats)]`)
   - Fixed `generatePDF.py:419` - hardcoded path bug (changed `pdf.output(path, 'F')` to `pdf.output(output_path, 'F')`)

4. **Testing:**
   - Created `test_downsampling.py` - standalone downsampling test (3/3 tests pass)
   - Created `test_pipeline_e2e.py` - end-to-end pipeline test (8/8 stages pass)
   - All tests passing on v1-fixes branch

**Test Results:**
```
RESULT: 3/3 tests passed (downsampling test)
RESULT: 8/8 stages passed (pipeline test)
```

---

**Original Actions (for reference):**

#### 1.3.1: Create `downsample.py` Module
**File**: New file `uct_benchmark/data/downsample.py`

```python
"""
Downsampling strategies for T1/T2 data.

When data quality exceeds requirements, we need to reduce observations
while maintaining dataset validity and representativeness.
"""

from enum import Enum
import pandas as pd
import numpy as np

class DownsampleStrategy(Enum):
    RANDOM = "random"              # Random removal
    SYSTEMATIC = "systematic"      # Remove every Nth observation
    QUALITY_BASED = "quality"      # Remove lower-quality obs first
    TRACK_AWARE = "track_aware"    # Maintain minimum per track
    COVERAGE_PRESERVING = "coverage"  # Maintain orbital coverage

def downsample_random(observations: pd.DataFrame,
                      target_count: int,
                      seed: int = None) -> pd.DataFrame:
    """
    Randomly remove observations to reach target count.

    Pros: Simple, unbiased
    Cons: May create coverage gaps
    """
    if len(observations) <= target_count:
        return observations

    rng = np.random.default_rng(seed)
    indices = rng.choice(len(observations), target_count, replace=False)
    return observations.iloc[sorted(indices)]

def downsample_systematic(observations: pd.DataFrame,
                          target_count: int) -> pd.DataFrame:
    """
    Remove every Nth observation to reach target count.

    Pros: Uniform reduction, maintains temporal distribution
    Cons: May miss certain orbital phases
    """
    if len(observations) <= target_count:
        return observations

    # Sort by time
    obs_sorted = observations.sort_values('obTime')

    # Calculate stride
    stride = len(observations) / target_count
    indices = [int(i * stride) for i in range(target_count)]

    return obs_sorted.iloc[indices]

def downsample_track_aware(observations: pd.DataFrame,
                           target_count: int,
                           min_per_track: int = 3) -> pd.DataFrame:
    """
    Downsample while ensuring minimum observations per track.

    Tracks are observation sequences that likely belong to same object.
    Maintaining minimum per track preserves data structure.
    """
    if len(observations) <= target_count:
        return observations

    # Group by track
    tracks = observations.groupby('trackId')

    # Calculate how many to keep per track
    n_tracks = tracks.ngroups
    per_track = max(min_per_track, target_count // n_tracks)

    result_dfs = []
    for track_id, track_obs in tracks:
        if len(track_obs) <= per_track:
            result_dfs.append(track_obs)
        else:
            # Systematic sample within track
            result_dfs.append(downsample_systematic(track_obs, per_track))

    result = pd.concat(result_dfs)

    # If still over target, do final random trim
    if len(result) > target_count:
        result = downsample_random(result, target_count)

    return result

def downsample_coverage_preserving(observations: pd.DataFrame,
                                   target_count: int,
                                   orbital_elements: dict) -> pd.DataFrame:
    """
    Downsample while maximizing orbital coverage.

    Divides orbit into bins (by mean anomaly or time) and ensures
    observations are retained from each bin.
    """
    if len(observations) <= target_count:
        return observations

    # Calculate mean anomaly for each observation time
    # (requires orbital elements and propagation)
    # ... implementation details ...

    # Bin observations by orbital phase
    n_bins = min(20, target_count // 3)  # At least 3 obs per bin
    # ... binning logic ...

    # Sample from each bin
    # ... sampling logic ...

    return result

def downsample(observations: pd.DataFrame,
               target_count: int,
               strategy: DownsampleStrategy = DownsampleStrategy.TRACK_AWARE,
               **kwargs) -> pd.DataFrame:
    """
    Main downsampling function.

    Parameters:
    - observations: DataFrame of observations
    - target_count: desired number of observations
    - strategy: downsampling strategy to use
    - **kwargs: strategy-specific parameters

    Returns:
    - DataFrame with reduced observations
    """
    strategy_map = {
        DownsampleStrategy.RANDOM: downsample_random,
        DownsampleStrategy.SYSTEMATIC: downsample_systematic,
        DownsampleStrategy.TRACK_AWARE: downsample_track_aware,
        DownsampleStrategy.COVERAGE_PRESERVING: downsample_coverage_preserving,
    }

    func = strategy_map[strategy]
    return func(observations, target_count, **kwargs)
```

#### 1.3.2: Integrate into Create_Dataset.py

```python
from uct_benchmark.data.downsample import downsample, DownsampleStrategy

# After window selection, before saving dataset
if tierThreshold in ["T1", "T2"]:
    logger.info(f"Tier {tierThreshold}: downsampling to target observation count")

    target_obs = config.highObsCount if tierThreshold == "T1" else config.standardObsCount

    for sat_id in satellites:
        sat_obs = observations[observations['satNo'] == sat_id]

        if len(sat_obs) > target_obs:
            # Downsample this satellite's observations
            downsampled = downsample(
                sat_obs,
                target_count=target_obs,
                strategy=DownsampleStrategy.TRACK_AWARE
            )

            # Replace in main dataframe
            observations = observations[observations['satNo'] != sat_id]
            observations = pd.concat([observations, downsampled])

    logger.info(f"Downsampled to {len(observations)} total observations")
```

#### 1.3.3: Test Downsampling
- [ ] Create test with known over-sampled dataset
- [ ] Verify each strategy produces correct count
- [ ] Verify track structure is preserved (for track-aware)
- [ ] Verify evaluation still works on downsampled data
- [ ] Compare evaluation results before/after downsampling

**Success Criteria**:
- T1/T2 datasets automatically downsample as needed
- Multiple strategies available and tested
- Track structure preserved when using track-aware
- No negative impact on evaluation quality

---

## Priority 2: Quality Improvements

### TODO 2.1: Improve PDF Report Generation
**Importance**: MEDIUM - User-facing quality
**Effort**: Medium
**Dependencies**: Evaluation pipeline working

**Problem Statement** (per Lewis):
> "The PDF report needs some work. We want that to look nice by the time we're done with it."
> "This looks kind of sporadic because like I mentioned before, it's just random data to validate that the algorithm works."

**Actions**:

#### 2.1.1: Audit Current Report
**File**: `uct_benchmark/utils/generatePDF.py`

- [ ] Review current PDF structure and layout
- [ ] Identify visual issues:
  - [ ] Formatting inconsistencies
  - [ ] Chart quality/readability
  - [ ] Table alignment
  - [ ] Font consistency
- [ ] Compare against professional benchmark reports

#### 2.1.2: Design Improved Report Structure

**Proposed Sections**:

1. **Cover Page**
   - Project title: "UCT Benchmark Evaluation Report"
   - Dataset identifier
   - Generation date
   - Algorithm/UCTP name

2. **Executive Summary** (1 page)
   - Key metrics at a glance (F1, Position RMS, Recall)
   - Pass/Fail summary
   - Overall performance grade

3. **Dataset Description** (1 page)
   - Number of objects
   - Number of observations
   - Time window
   - Orbital regime distribution
   - Data quality tier

4. **Association Results** (1-2 pages)
   - Total candidates vs references
   - Association success rate
   - Non-associated candidates
   - Undiscovered references
   - Visualization: association diagram

5. **Binary Metrics** (1-2 pages)
   - Confusion matrix (visual)
   - Precision, Recall, F1-Score
   - Accuracy
   - Per-object breakdown table

6. **State Accuracy** (2-3 pages)
   - Position error statistics (mean, std, max, 95th percentile)
   - Velocity error statistics
   - Error histogram charts
   - Error vs. time plots
   - Covariance consistency (NEES)

7. **Residual Analysis** (1-2 pages)
   - RA residual RMS
   - Dec residual RMS
   - Residual distribution plots
   - Residual vs. time

8. **Appendix**
   - Detailed per-object results
   - Methodology notes
   - Configuration parameters used

#### 2.1.3: Implement Visual Improvements

- [ ] Use consistent color scheme
- [ ] Add professional charts using matplotlib/plotly
- [ ] Create confusion matrix heatmap
- [ ] Add error distribution histograms
- [ ] Include time-series plots for errors
- [ ] Add summary icons/badges for quick assessment

#### 2.1.4: Add HTML Export Option
- [ ] Create HTML template with same structure
- [ ] Add interactive charts (plotly)
- [ ] Enable web-based viewing

**Success Criteria**:
- Report looks professional
- All metrics clearly presented
- Charts are readable and informative
- Consistent styling throughout

---

### TODO 2.2: Implement Realistic Noise Modeling
**Importance**: MEDIUM - Simulation accuracy
**Effort**: High
**Dependencies**: T3 processing complete

**Problem Statement** (per Lewis):
> "We want to be able to more accurately represent sources of uncertainty and noise in the telescope systems. Right now we just added a constant Gaussian blur... there's also other sources of uncertainty, such as atmospheric refraction or stellar aberration that were not accounted for in the simulation. We do have some research and some papers that talk about more accurate noise characteristics."

**Actions**:

#### 2.2.1: Research Noise Sources
**References**: Check `provided-materials/` for research papers

Noise sources for optical observations:
1. **Atmospheric Refraction**
   - Light bends passing through atmosphere
   - Depends on zenith angle, atmospheric pressure, temperature
   - Can be several arcseconds at low elevations

2. **Stellar Aberration**
   - Apparent displacement due to Earth's orbital motion
   - Up to ~20 arcseconds
   - Depends on object direction relative to Earth's velocity

3. **Atmospheric Scintillation**
   - Twinkling effect from atmospheric turbulence
   - Random angular displacement

4. **Sensor-Specific Noise**
   - Pixel quantization
   - CCD readout noise
   - Dark current
   - Flat-field variations

5. **Timing Uncertainty**
   - GPS synchronization errors
   - Exposure duration effects

#### 2.2.2: Create `noiseModels.py` Module
**File**: New file `uct_benchmark/simulation/noiseModels.py`

```python
"""
Realistic noise models for observation simulation.

Based on research on optical telescope observation characteristics.
"""

import numpy as np
from scipy import stats

def atmospheric_refraction(elevation_deg: float,
                          pressure_mbar: float = 1013.25,
                          temperature_c: float = 15.0) -> float:
    """
    Calculate atmospheric refraction in arcseconds.

    Uses Bennett's formula for atmospheric refraction.

    Parameters:
    - elevation_deg: elevation angle in degrees
    - pressure_mbar: atmospheric pressure in millibars
    - temperature_c: temperature in Celsius

    Returns:
    - refraction in arcseconds
    """
    if elevation_deg < 0:
        return 0.0

    # Bennett's formula
    h = elevation_deg
    R = 1.0 / np.tan(np.radians(h + 7.31 / (h + 4.4)))

    # Pressure and temperature correction
    R = R * (pressure_mbar / 1010.0) * (283.0 / (273.0 + temperature_c))

    return R * 60.0  # Convert to arcseconds

def stellar_aberration(ra_deg: float, dec_deg: float,
                       earth_velocity: np.ndarray) -> tuple:
    """
    Calculate stellar aberration displacement.

    Parameters:
    - ra_deg: right ascension in degrees
    - dec_deg: declination in degrees
    - earth_velocity: Earth's velocity vector (km/s) in J2000

    Returns:
    - (delta_ra, delta_dec) in arcseconds
    """
    c = 299792.458  # km/s

    # Convert to radians
    ra = np.radians(ra_deg)
    dec = np.radians(dec_deg)

    # Star direction unit vector
    star = np.array([
        np.cos(dec) * np.cos(ra),
        np.cos(dec) * np.sin(ra),
        np.sin(dec)
    ])

    # Aberration formula (first order)
    v_mag = np.linalg.norm(earth_velocity)
    beta = v_mag / c

    # ... full calculation ...

    return delta_ra_arcsec, delta_dec_arcsec

def atmospheric_scintillation(zenith_angle_deg: float,
                               aperture_m: float = 0.3) -> float:
    """
    Calculate scintillation noise standard deviation.

    Based on Dravins et al. scintillation model.

    Parameters:
    - zenith_angle_deg: zenith angle in degrees
    - aperture_m: telescope aperture in meters

    Returns:
    - standard deviation of angular displacement in arcseconds
    """
    # Simplified model
    z = np.radians(zenith_angle_deg)
    sigma = 0.5 * (aperture_m ** -0.67) * (np.cos(z) ** -1.5)
    return sigma

def sensor_noise(pixel_scale_arcsec: float = 1.0,
                 snr: float = 100.0) -> float:
    """
    Calculate sensor-related angular noise.

    Parameters:
    - pixel_scale_arcsec: arcseconds per pixel
    - snr: signal-to-noise ratio

    Returns:
    - centroiding uncertainty in arcseconds
    """
    # Centroiding uncertainty ~ FWHM / SNR
    fwhm_pixels = 2.5  # Typical seeing FWHM
    sigma_pixels = fwhm_pixels / snr
    return sigma_pixels * pixel_scale_arcsec

def total_observation_noise(elevation_deg: float,
                            ra_deg: float = None,
                            dec_deg: float = None,
                            include_refraction: bool = True,
                            include_scintillation: bool = True,
                            include_sensor: bool = True) -> dict:
    """
    Calculate total observation noise from all sources.

    Returns dict with noise components and total.
    """
    noise = {}

    if include_refraction:
        noise['refraction_bias'] = atmospheric_refraction(elevation_deg)

    if include_scintillation:
        zenith = 90.0 - elevation_deg
        noise['scintillation_sigma'] = atmospheric_scintillation(zenith)

    if include_sensor:
        noise['sensor_sigma'] = sensor_noise()

    # Combined random noise (RSS)
    random_sigmas = [v for k, v in noise.items() if 'sigma' in k]
    noise['total_random_sigma'] = np.sqrt(sum(s**2 for s in random_sigmas))

    return noise

def add_realistic_noise(ra_true: float, dec_true: float,
                        elevation_deg: float,
                        rng: np.random.Generator = None) -> tuple:
    """
    Add realistic noise to true RA/Dec measurements.

    Parameters:
    - ra_true, dec_true: true coordinates in degrees
    - elevation_deg: observation elevation
    - rng: random number generator

    Returns:
    - (ra_observed, dec_observed) with noise added
    """
    if rng is None:
        rng = np.random.default_rng()

    noise = total_observation_noise(elevation_deg)

    # Apply random noise
    sigma = noise['total_random_sigma'] / 3600.0  # Convert to degrees

    ra_noise = rng.normal(0, sigma / np.cos(np.radians(dec_true)))
    dec_noise = rng.normal(0, sigma)

    return ra_true + ra_noise, dec_true + dec_noise
```

#### 2.2.3: Integrate into Simulation Pipeline
**File**: `uct_benchmark/simulation/simulateObservations.py`

- [ ] Replace simple Gaussian noise with realistic model
- [ ] Add configuration options for noise levels
- [ ] Allow enabling/disabling specific noise sources
- [ ] Document noise model parameters

#### 2.2.4: Test and Validate Noise Model
- [ ] Compare simulated observation residuals to real data
- [ ] Verify noise magnitude is reasonable
- [ ] Test across different elevation angles
- [ ] Document noise characteristics

**Success Criteria**:
- Noise model produces realistic observation uncertainties
- Configurable noise sources
- Documented and tested

---

## Priority 3: Integration Tasks

### TODO 3.1: Integrate IU Team's Event Labeling Work
**Importance**: MEDIUM - Enables event-based datasets
**Effort**: Medium-High
**Dependencies**: Access to IU team's database/code

**Background** (per Lewis):
> "The other internship group that we were working with, they were working on creating a labeled database of these events and the observations that go together with these events... they were working on a way to automatically parse [NOTSO] information and put it into a database."

**Actions**:

#### 3.1.1: Obtain IU Team Deliverables
- [ ] Contact Atulya about IU team's work
- [ ] Obtain:
  - [ ] Event labeling database (or schema)
  - [ ] NOTSO parsing code
  - [ ] Documentation on label definitions
  - [ ] Any integration instructions

#### 3.1.2: Understand Event Schema

Expected event types:
- **Launch events**: New object appearing
- **Maneuver events**: Orbital changes
- **Proximity events**: Close approaches
- **Breakup events**: Fragmentation

For each event, we need:
- Event type
- Event time
- Objects involved
- Associated observations

#### 3.1.3: Create Integration Layer
**File**: New file `uct_benchmark/labelling/eventIntegration.py`

```python
"""
Integration layer for IU team's event labeling database.
"""

def query_events_in_window(start_time: datetime,
                           end_time: datetime,
                           event_types: list = None) -> list:
    """Query labeled events in a time window."""
    pass

def get_observations_for_event(event_id: str) -> DataFrame:
    """Get observations associated with an event."""
    pass

def filter_datasets_by_event(dataset_code: str,
                            event_type: str) -> DataFrame:
    """Filter data to include only specific event types."""
    pass
```

#### 3.1.4: Add Event Filtering to Dataset Generation
- [ ] Add event type to dataset code parameters
- [ ] Query event database when generating datasets
- [ ] Include event metadata in output

**Success Criteria**:
- Can query IU team's event database
- Can filter datasets by event type
- Event metadata included in dataset output

---

### TODO 3.2: Algorithm Efficiency Improvements
**Importance**: MEDIUM - Performance
**Effort**: Medium
**Dependencies**: None

**Problem Statement** (per Lewis):
> "A lot of our algorithms, we just kind of threw them together rather haphazardly. They're not super efficient. There's probably a lot of room for adding more efficiency, increase runtime, better computation or more memory efficiency."

**Actions**:

#### 3.2.1: Profile Current Pipeline
- [ ] Add timing instrumentation to key functions
- [ ] Identify slowest operations
- [ ] Measure memory usage
- [ ] Document baseline performance

**Key areas to profile**:
- API queries (likely I/O bound)
- Window selection (potentially slow with large datasets)
- Propagation (computationally intensive)
- Scoring functions
- Evaluation metrics

#### 3.2.2: Optimize Identified Bottlenecks
Common optimizations:
- [ ] Add caching for repeated API calls
- [ ] Use vectorized operations instead of loops
- [ ] Parallelize independent operations
- [ ] Optimize propagator calls (batch processing)
- [ ] Use more efficient data structures

#### 3.2.3: Add Progress Indicators
- [ ] Add progress bars for long operations
- [ ] Log estimated time remaining
- [ ] Allow cancellation of long operations

**Success Criteria**:
- Pipeline runs noticeably faster
- Memory usage reasonable for large datasets
- Progress visible during long operations

---

## Priority 4: Future Goals

### TODO 4.1: Open Evolve Architecture Design
**Importance**: LOW (stretch goal) - Future capability
**Effort**: High
**Dependencies**: Evaluation pipeline fully validated

**Background** (per Lewis):
> "There's this program called Open Evolve, which is a way to optimize code bases using an AI agent. It's an iterative cycle of querying LLM to suggest modifications to a code base followed by an evaluation program that'll say how well that the code performed."

> "The idea is that we can plug that into an architecture like this. We could have an LLM suggest a series of edits to a UCT processor. Then we can evaluate how well those edits actually performed."

**Actions**:

#### 4.1.1: Research Open Evolve
- [ ] Understand Open Evolve architecture
- [ ] Review requirements for integration
- [ ] Identify evaluation script requirements

#### 4.1.2: Design Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Open Evolve System                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ LLM Agent   │───▶│ UCTP Code   │───▶│ Modified    │     │
│  │             │    │ Modification │    │ UCTP        │     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│                                               │             │
│                                               ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Improvement │◀───│ Evaluation  │◀───│ Run UCTP    │     │
│  │ Feedback    │    │ Metrics     │    │ on Dataset  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│        │                  ▲                                 │
│        │                  │                                 │
│        └──────────────────┘                                 │
│              (Iterate)                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Our Pipeline    │
                    │ - Datasets      │
                    │ - Evaluation    │
                    │ - Metrics       │
                    └─────────────────┘
```

#### 4.1.3: Create Evaluation API for Open Evolve
- [ ] Design API that Open Evolve can call
- [ ] Standardize evaluation output format
- [ ] Create feedback format for LLM consumption

**Success Criteria**:
- Clear architecture documented
- Integration requirements identified
- Ready for implementation when priority increases

---

## Timeline and Dependencies

```
Week 1-2: Priority 0 (UCTP Validation Setup)
├── Contact Patrick Ramsey
├── Prepare validation datasets
└── Begin T3 work in parallel

Week 3-4: Priority 1 (Core Pipeline)
├── Complete T3 processing
├── Complete downsampling
└── Begin T4 work

Week 5-6: Priority 1 (continued)
├── Complete T4 processing
├── Run validation with Aerospace Corp
└── Iterate on any issues

Week 7-8: Priority 2 (Quality)
├── PDF report improvements
├── Noise modeling (if time)
└── Performance optimization

Week 9+: Priority 3-4 (Integration/Future)
├── Event labeling integration
├── Open Evolve architecture
└── Documentation finalization
```

---

## Dependency Graph

```
                    ┌─────────────────┐
                    │ Contact Patrick │
                    │ Ramsey (0.1)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ T3 Process  │  │ Downsample  │  │ Prepare     │
    │ (1.1)       │  │ (1.3)       │  │ Datasets    │
    └──────┬──────┘  └──────┬──────┘  │ (0.2)       │
           │                │         └──────┬──────┘
           ▼                │                │
    ┌─────────────┐         │                │
    │ T4 Process  │         │                │
    │ (1.2)       │         │                │
    └──────┬──────┘         │                │
           │                │                │
           └────────────────┼────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │ UCTP Validation │
                    │ (0.3)           │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ PDF Report  │  │ Noise Model │  │ Efficiency  │
    │ (2.1)       │  │ (2.2)       │  │ (3.2)       │
    └─────────────┘  └─────────────┘  └─────────────┘
```

---

## Success Metrics

| Milestone | Metric | Target |
|-----------|--------|--------|
| UCTP Validation | Real UCTP output processed | Yes |
| T3 Processing | Simulated observations added correctly | 100% |
| T4 Processing | Synthetic objects generated correctly | 100% |
| Downsampling | Correct observation counts | 100% |
| PDF Report | Professional appearance | Subjective review |
| Noise Model | Realistic uncertainties | Match real data |
| Performance | Dataset generation time | <5 minutes |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Patrick Ramsey unavailable | Medium | High | Find alternative UCTP source |
| T4 synthetic orbits unrealistic | Medium | Medium | Validate against real orbit distribution |
| Noise model too complex | Low | Low | Start simple, add complexity gradually |
| Integration issues with IU work | Medium | Medium | Early communication, clear interfaces |

---

## Document History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-17 | 1.0 | Team | Initial plan based on Lewis transcript |
| 2026-01-18 | 1.1 | Team | **T1/T2 Downsampling COMPLETE**: Integrated existing downsampleData() into pipeline, added config parameters, fixed bugs in dataManipulation.py and generatePDF.py, created test suite (3/3 + 8/8 passing) |
| 2026-01-18 | 1.2 | Team | **T3 Simulation COMPLETE**: Rewrote epochsToSim() with time-bin approach, added simulation config, integrated into Create_Dataset.py, created test_simulation.py (3/3 + 8/8 passing) |

