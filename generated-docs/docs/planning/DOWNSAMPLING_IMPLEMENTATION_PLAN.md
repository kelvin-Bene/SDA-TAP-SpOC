# Downsampling Implementation Plan

## Status: ✅ COMPLETE (2026-01-18)

## Overview

This document details the plan to integrate the existing downsampling functionality into the dataset creation pipeline.

> **Implementation completed 2026-01-18.** All tests passing (3/3 downsampling tests, 8/8 pipeline tests).

---

## Current State Analysis

### What EXISTS (in `dataManipulation.py`)

```python
def downsampleData(ref_obs, sat_params, orbit_coverage, track_length, obs_count, bins=10, rand=None):
    """
    Does best downsampling of a observation dataset given specified parameters.

    Args:
        ref_obs: DataFrame of reference observations
        sat_params: Dict of orbital elements keyed by satNo
        orbit_coverage: Dict with 'sats', 'p_bounds', 'p_coverage'
        track_length: Dict with 'sats', 'p_bounds', 'p_track'
        obs_count: Dict with 'sats', 'p_bounds', 'obs_max'
        bins: Number of bins for time downsampling
        rand: Random seed

    Returns:
        ref_obs: Downsampled DataFrame
        p_reached: Tuple of percentages reached
    """
```

### What's NOT Connected (in `Create_Dataset.py`)

Lines 69-73 just print "NOT implemented" and pass:
```python
#if tierThreshold == 'T2':
# Everything will be passed to downsample, if no downsample required, function will pass
print('T2 NOT implemented. Moving On')
pass
```

### Data Flow

```
windowMain() returns:
    ├── datasetCode    → Dataset parameters
    ├── tierThreshold  → "T1", "T2", "T3", "T4", "T5"
    ├── observations   → DataFrame of observations
    ├── orbElms        → Dict of orbital elements (EXACTLY what downsampleData needs!)
    └── metaData       → Scoring metadata

downsampleData() needs:
    ├── ref_obs        → observations DataFrame ✓
    ├── sat_params     → orbElms dictionary ✓
    ├── orbit_coverage → Need to construct from config
    ├── track_length   → Need to construct from config
    └── obs_count      → Need to construct from config
```

---

## Implementation Plan

### Step 1: Add Downsampling Parameters to Config

**File:** `uct_benchmark/config.py`

Downsampling parameters (implemented in config.py lines 142-162):
```python
# Downsampling configuration
# p_bounds use 3-tuple format: (min%, target%, max%) of sats to affect
downsample_coverage_bounds = (0.3, 0.5, 0.7)  # (min%, target%, max%) of sats to downsample
downsample_coverage_target = (0.15, 0.05)     # (max, min) orbital coverage threshold
downsample_gap_bounds = (0.3, 0.5, 0.7)       # (min%, target%, max%) of sats to downsample
downsample_gap_target = 2.0                   # Target max gap (2 orbital periods)
downsample_obs_bounds = (0.3, 0.5, 0.7)       # (min%, target%, max%) of sats to downsample
downsample_obs_max = 50                       # Max observations per sat per 3 days
downsample_min_obs = 5                        # Minimum observations to keep (safety threshold)
```

### Step 2: Update Create_Dataset.py

**Location:** After line 58, before getting reference state vectors

```python
# T1/T2 Processing: Apply downsampling if needed
if tierThreshold in ['T1', 'T2']:
    from uct_benchmark.data.dataManipulation import downsampleData
    import uct_benchmark.config as config

    # Build downsampling parameters
    # Note: p_bounds is a 3-tuple (min%, target%, max%) and p_coverage is a 2-tuple (max, min)
    orbit_coverage_params = {
        'sats': None,  # All satellites (or list of satNos)
        'p_bounds': config.downsample_coverage_bounds,  # (0.3, 0.5, 0.7)
        'p_coverage': config.downsample_coverage_target  # (0.15, 0.05) = (max, min) coverage
    }
    track_length_params = {
        'sats': None,
        'p_bounds': config.downsample_gap_bounds,  # (0.3, 0.5, 0.7)
        'p_track': config.downsample_gap_target    # 2.0 (orbital periods)
    }
    obs_count_params = {
        'sats': None,
        'p_bounds': config.downsample_obs_bounds,  # (0.3, 0.5, 0.7)
        'obs_max': config.downsample_obs_max       # 50
    }

    # Apply downsampling - runs three stages:
    # 1. _lowerOrbitCoverage() - reduce orbital coverage
    # 2. _increaseTrackDistance() - widen gaps between tracks
    # 3. _downsampleAbsolute() - reduce absolute observation count
    observations, p_reached = downsampleData(
        observations,
        orbElms,
        orbit_coverage_params,
        track_length_params,
        obs_count_params
    )

    print(f"Downsampling complete. Percentages reached: {p_reached}")
```

### Step 3: Create Standalone Test

**File:** `UCT-Benchmark-DMR/combined/test_downsampling.py`

Create a test that:
1. Loads sample data from `src/data/`
2. Creates mock orbital elements
3. Runs downsampling
4. Verifies observation count reduced
5. Integrates with existing pipeline test

### Step 4: Update Pipeline Test

Modify `test_pipeline_e2e.py` to include a downsampling stage.

---

## Execution Order

1. ✅ Analyze existing code (DONE)
2. ✅ Add config parameters (DONE - `uct_benchmark/config.py`)
3. ✅ Update Create_Dataset.py integration (DONE - lines 71-120)
4. ✅ Create standalone downsampling test (DONE - `test_downsampling.py`)
5. ✅ Update end-to-end pipeline test (DONE - `test_pipeline_e2e.py`)
6. ✅ Run tests and verify (DONE - 3/3 + 8/8 tests pass)
7. ✅ Push changes to v1-fixes branch (DONE)

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| orbElms format mismatch | Verify format in basicScoringFunction matches downsampleData expectations |
| Missing orbital elements | Add fallback defaults for missing satellites |
| Over-downsampling | Add minimum observation threshold check |

---

## Success Criteria

1. Downsampling runs without errors on sample data
2. Observation count is reduced when downsampling is applied
3. Pipeline test still passes 8/8 stages
4. No regression in existing functionality

---

*Created: 2026-01-18*
*Completed: 2026-01-18*
