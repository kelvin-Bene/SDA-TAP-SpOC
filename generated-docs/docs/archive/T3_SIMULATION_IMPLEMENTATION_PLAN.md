# T3 Simulation Implementation Plan

## Status: ✅ COMPLETE (2026-01-19)

## Overview

This document details the implementation of T3 observation simulation in the dataset creation pipeline. T3 processing is used when real data exists but is insufficient in quality (coverage, track gaps, or observation count).

> **Implementation completed 2026-01-19.** The `epochsToSim()` function has been fully implemented using a time-bin based approach, and integrated into the pipeline.

---

## Current State Analysis

### What EXISTS

1. **`simulateObs()` function** (simulateObservations.py:12-130) - FULLY FUNCTIONAL
   - Takes state vector/TLE + epoch + time list
   - Propagates orbit using `ephemerisPropagator()` or `TLEpropagator()`
   - Randomly selects sensors weighted by observation count
   - Filters for elevation >= 6 degrees
   - Outputs observations in UDL EOobs schema format
   - Adds configurable Gaussian noise (position + angular)

2. **Propagators** (propagator.py) - FULLY FUNCTIONAL
   - `ephemerisPropagator()` - high-fidelity numerical propagation
   - `TLEpropagator()` - SGP4/SDP4 propagation
   - `orbit2OE()` - converts state vector to orbital elements

3. **`epochsToSim()` function** (simulateObservations.py:358-507) - ✅ COMPLETE
   - Fully implemented with time-bin based approach
   - Divides observation window into bins based on orbital period
   - Identifies bins with insufficient observations
   - Returns epochs at center of gap bins for simulation

4. **Sensor data** (src/data/sensorCounts.csv)
   - 17 optical sensors worldwide
   - Columns: idSensor, count, senlat, senlon, senalt

### What Was Implemented

1. ✅ **Complete `epochsToSim()`** - time-bin based epoch selection (lines 358-507)
2. ✅ **Configuration parameters** - added to config.py (lines 164-188)
3. ✅ **Integration ready** - `simulateObs()` can accept epoch list from `epochsToSim()`
4. ✅ **Merge logic** - simulated observations marked with `dataMode='SIMULATED'`

---

## T3 Trigger Conditions

T3 is triggered when data quality is insufficient. From `basicScoringFunction.py`:

### Coverage-Based (T3covg)
- When standard coverage satellites ratio < required percentage
- Target: config.standardPercentage = (0.4, 0.5, 0.6)
- Low coverage thresholds:
  - LEO: < 2.13%
  - MEO: < 4.49%
  - GEO: < 41.656%

### Track Gap-Based (T3Gap)
- When satellites with standard track gaps ratio < required percentage
- Long gap threshold: > 2 orbital periods

### Observation Count-Based (T3Obs)
- When high+standard observation count ratio < required percentage
- Low obs: <= 50 per 3 days
- High obs: >= 150 per 3 days

---

## Potential Issues and Shortcomings

### Issue 1: Orbital Coverage Calculation Complexity
**Problem:** The existing `epochsToSim()` uses geometric triangle area calculation which is complex and error-prone.

**Solution:** Simplify to time-based coverage. Instead of geometric orbital polygon area:
- Divide orbit into N equal time bins (e.g., 10 bins per orbital period)
- Count observations in each bin
- Target bins with zero or few observations
- Much simpler and equally effective for improving coverage

### Issue 2: Propagator Dependency (Orekit)
**Problem:** Propagators require Orekit JVM initialization which is slow and may fail if not configured.

**Solution:**
- Add fallback to simple Keplerian propagation for testing
- Ensure Orekit data files are available
- Add error handling with informative messages

### Issue 3: Missing State Vector for Simulation
**Problem:** T3 processing happens before reference state vectors are pulled from UDL. Need orbital information to simulate.

**Solution:** Two options:
1. Use `orbElms` dict from window selection (already available at T3 stage)
2. Pull reference states earlier in pipeline if needed

### Issue 4: Sensor Visibility Filtering
**Problem:** Current code tries all sensors until one has elevation >= 6 degrees, which can be slow.

**Solution:** Pre-filter sensors by geographic region based on satellite ground track. Accept that some simulated epochs may have no visible sensors (realistic).

### Issue 5: Over-Simulation Risk
**Problem:** Could add too many simulated observations, diluting real data.

**Solution:**
- Set maximum simulation ratio (e.g., simulated <= 50% of total)
- Prioritize coverage gaps over bulk count increase
- Log simulation statistics for transparency

### Issue 6: Realistic Observation Timing
**Problem:** Simple midpoint selection may not reflect realistic observation patterns.

**Solution:**
- Simulate observations in "tracks" (groups of 3-5 obs within minutes)
- Add realistic timing noise (10-60 seconds between track observations)
- Match existing observation temporal patterns

---

## Implementation Approach

### Approach: Time-Bin Based Epoch Selection (Simplified)

Instead of the complex geometric approach in the incomplete `epochsToSim()`, use a simpler time-based method:

```
Algorithm:
1. Calculate orbital period from orbital elements
2. Divide time window into bins (period / N, e.g., N=10)
3. Count observations in each bin
4. Identify bins with zero or few observations
5. Select epoch at center of each empty bin
6. Repeat until:
   - Target observation count reached, OR
   - All bins have minimum observations, OR
   - Maximum simulation ratio reached
```

**Advantages:**
- Simple to implement
- Easy to test and debug
- Naturally improves both coverage and track gap metrics
- Doesn't require complex orbital polygon calculations

---

## Detailed Implementation Plan

### Step 1: Complete `epochsToSim()` Function

**File:** `uct_benchmark/simulation/simulateObservations.py`

Replace incomplete function with time-bin approach:

```python
def epochsToSim(satNo, satObs, orbElems, target_obs_count=None, max_sim_ratio=0.5):
    """
    Determine epochs at which to simulate observations.

    Uses time-bin based approach: divides observation window into bins
    based on orbital period, identifies bins with insufficient observations,
    and returns epochs at the center of each gap bin.

    Args:
        satNo: NORAD ID of satellite
        satObs: DataFrame of existing observations (must have 'obTime' column)
        orbElems: Dict with 'Period' key (orbital period in seconds)
        target_obs_count: Target total observation count (default: current + 50%)
        max_sim_ratio: Maximum ratio of simulated to total (default: 0.5)

    Returns:
        epochs: List of datetime objects for simulation
        bins_info: Dict with bin statistics for logging
    """
```

### Step 2: Add Simulation Config Parameters

**File:** `uct_benchmark/config.py`

```python
## --- T3 Simulation Configuration --- ##
# Time bins per orbital period for epoch selection
simulation_bins_per_period = 10

# Minimum observations per bin to consider "covered"
simulation_min_obs_per_bin = 1

# Maximum ratio of simulated observations to total
simulation_max_ratio = 0.5

# Target increase in observation count (percentage)
simulation_target_increase = 0.5  # 50% more observations

# Observations per simulated track (realistic grouping)
simulation_track_size = 3

# Seconds between observations in a track
simulation_track_spacing = 30
```

### Step 3: Integrate into Create_Dataset.py

**Location:** After T1/T2 downsampling, before reference state pull

```python
# T3 Processing: Simulate observations if needed
if tierThreshold == 'T3':
    print(f'Applying {tierThreshold} simulation...')
    from uct_benchmark.simulation.simulateObservations import simulateObs, epochsToSim

    # Load sensor data
    sensorsDf = pd.read_csv('./data/sensorCounts.csv')

    obs_before = len(observations)
    simulated_count = 0

    for sat_id in observations['satNo'].unique():
        sat_obs = observations[observations['satNo'] == sat_id]

        if sat_id not in orbElms:
            print(f'  Skipping {sat_id}: no orbital elements')
            continue

        # Determine epochs needing simulation
        epochs_to_sim, bins_info = epochsToSim(
            sat_id, sat_obs, orbElms[sat_id]
        )

        if not epochs_to_sim:
            continue

        print(f'  Simulating {len(epochs_to_sim)} epochs for satellite {sat_id}')

        # Get reference state for propagation
        ref_state = get_reference_state(sat_id, orbElms[sat_id])

        # Simulate observations
        sim_obs = simulateObs(
            ref_state['state_vector'],
            ref_state['epoch'],
            epochs_to_sim,  # Pass as list of epochs
            sensorsDf,
            satelliteParameters=[sat_id, 0, 0]
        )

        # Mark as simulated and merge
        sim_obs['dataMode'] = 'SIMULATED'
        observations = pd.concat([observations, sim_obs], ignore_index=True)
        simulated_count += len(sim_obs)

    obs_after = len(observations)
    print(f'T3 simulation complete: {obs_before} -> {obs_after} observations')
    print(f'Added {simulated_count} simulated observations')
```

### Step 4: Create Test Script

**File:** `UCT-Benchmark-DMR/combined/test_simulation.py`

Test:
1. `epochsToSim()` returns correct epochs for sparse data
2. `simulateObs()` generates valid observations
3. Integration adds observations correctly
4. Simulated observations have correct schema
5. Coverage metrics improve after simulation

### Step 5: Test End-to-End Pipeline

Run full pipeline test with T3 scenario to verify:
- T3 detection works
- Simulation executes
- Observations merge correctly
- Evaluation still works

---

## Implementation Order

1. ✅ Complete `epochsToSim()` with time-bin approach (DONE - 2026-01-19)
2. ✅ Add config parameters for simulation (DONE - config.py lines 164-188)
3. ✅ Create helper function for state reference (uses orbElems from window selection)
4. ✅ Integration ready - `simulateObs()` accepts epoch list
5. ✅ Create standalone simulation test (test_simulation.py)
6. ✅ Test with sparse sample data
7. ✅ Run end-to-end pipeline test (test_pipeline_e2e.py)
8. ✅ Update documentation (this document)

---

## Success Criteria

1. `epochsToSim()` returns epochs that fill coverage gaps
2. Simulated observations pass schema validation
3. Coverage/gap metrics improve after simulation
4. Pipeline test passes with T3 processing
5. Simulated observations clearly marked in output
6. No regression in existing functionality

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Orekit initialization fails | Medium | High | Add fallback propagation, clear error messages |
| Over-simulation | Low | Medium | Enforce max_sim_ratio parameter |
| Unrealistic observations | Medium | Low | Use track grouping, realistic timing |
| State vector missing | Medium | High | Use TLE fallback or skip satellite |
| Performance issues | Low | Medium | Batch propagation, limit simulation count |

---

*Created: 2026-01-18*
*Completed: 2026-01-19*
