# UCT Benchmark: Known Limitations and Data Constraints

This document describes known limitations of the UCT Benchmark implementation based on Lewis's (Louis's) original specifications and available data sources.

## Overview

The UCT Benchmark system is approximately **90% aligned** with Lewis's original vision. However, several features have constraints due to data availability or external dependencies.

---

## Sensor Type Limitations

### Current Support: Optical (OP) Only

**Lewis's Specification:**
> "Currently we've only been working with optical observations, telescope observations. This is because the radar and passive RF observations are not as readily accessible. If we look on the UDL for radar observations or RF observations, we don't really have any."

**Available Sensor Type Codes:**
| Code | Type | Status |
|------|------|--------|
| `OP` | Optical (Telescope) | ✅ Fully Supported |
| `RA` | Radar | ❌ No Data Available |
| `RF` | Passive RF | ❌ No Data Available |
| `FU` | Fusion (Multi-sensor) | ❌ No Data Available |

**Impact:**
- Only optical sensor codes can be used in the 16-character dataset codes
- Radar and RF-based benchmarks cannot be generated from UDL data
- Multi-sensor fusion testing not currently possible

**Workaround:**
- Use simulated radar/RF observations if needed (set `needs_simulation=True`)
- Focus benchmarking on optical-based UCT processors

---

## Event Detection Limitations

### ML Labelling Model Dependency

**Lewis's Specification:**
> "Since the UDL does not contain these events directly, we are relying on the ML Labelling Team to feed us the NORAD IDs and Observation times corresponding to these events. As of the writing of this report, the ML Model is not operating."

**Event Code Reliability:**

| Code | Event Type | Status | Notes |
|------|------------|--------|-------|
| `NE` | No Events | ✅ Reliable | Always works - selects satellites without detected events |
| `MB` | Maneuver Between | ⚠️ Heuristic | Uses TLE discontinuity detection as fallback |
| `BU` | Breakup | ⚠️ Database-dependent | Requires Space-Track/CelesTrak API access |
| `LL` | Long-duration Low-thrust | ⚠️ Heuristic | Uses TLE trend analysis; difficult to distinguish from natural perturbations |

**Configuration:**
To enable ML model integration when available:
```bash
export UCT_ML_EVENT_ENDPOINT="https://your-ml-endpoint.example.com"
export UCT_ML_EVENT_API_KEY="your-api-key"
```

**Recommendations:**
1. For reliable datasets, prefer `NE` (No Events) event code
2. Treat `MB` and `LL` filtered datasets as approximate
3. Validate detected events manually when precision is critical
4. For `BU` filtering, ensure Space-Track credentials are configured

---

## Object Type Filtering Limitations

### Close (C) and Apparent (A) Objects

**Lewis's Specification:**
> "Note: Close objects and close apparent objects have not yet been implemented"

**Current Implementation Status:**

| Code | Object Type | Status | Notes |
|------|-------------|--------|-------|
| `H` | HAMR (High Area-to-Mass Ratio) | ✅ Implemented | Requires ESA DiscoSweb physical data |
| `C` | Close Proximity | ⚠️ Implemented | Requires state vectors with position AND velocity |
| `A` | Apparent Proximity | ✅ Implemented | Uses angular separation from observations |
| `U` | Unspecified | ✅ Implemented | No filtering applied |
| `N` | Calibration | ✅ Implemented | Uses predefined satellite list |

**Close (C) Object Requirements:**
Per Lewis's specification: "distance < X km, velocity < X m/s"
- Distance threshold: 100 km (configurable via `PROXIMITY_DISTANCE_THRESHOLD_KM`)
- Velocity threshold: 100 m/s (configurable via `PROXIMITY_VELOCITY_THRESHOLD_M_S`)
- **Requires:** State data with `position` (x, y, z) and `velocity` (vx, vy, vz) components

**Data Dependency:**
```python
state_data = {
    norad_id: {
        "position": (x_km, y_km, z_km),
        "velocity": (vx_km_s, vy_km_s, vz_km_s),  # Optional but recommended
        "epoch": datetime_object,
    }
}
```

---

## TrackTLE (TLE Generation) Limitations

### Orekit BatchLSEstimator Integration

**Lewis's Specification:**
> "The batch filter uses the rest of the states as pseudo-observations and an SGP4 propagator to converge on a solution"

**Current Status:** ✅ Implemented with full force models

**Requirements:**
- Orekit library properly initialized with OREKIT_DATA_PATH
- Minimum 3 valid angular observations for convergence
- Ground station information (latitude, longitude, altitude)

**Force Models Included:**
1. Holmes-Featherstone gravity (configurable degree/order)
2. NRLMSISE-00 atmospheric drag
3. Solar radiation pressure with umbra/penumbra
4. Sun and Moon third-body perturbations

---

## Window Selection Tier Descriptions

Per Lewis's specification, the tiered window selection system:

| Tier | Name | Description | Action |
|------|------|-------------|--------|
| T1 | Optimal | All criteria met | Use data as-is |
| T2 | Excess | Too many observations | Downsample to target |
| T3 | Insufficient | Not enough quality obs | Simulate additional obs |
| T4 | Poor | Criteria partially met | May need simulation |
| T5 | Impossible | Criteria cannot be met | Error - adjust criteria |

**TIER_5 Detection Conditions:**
- No objects exist in the search space
- Requested more objects than exist in catalog
- Data window far below required fit span
- All satellites have zero orbital coverage

---

## API and Data Source Requirements

### Required Environment Variables

| Variable | Purpose | Required For |
|----------|---------|--------------|
| `OREKIT_DATA_PATH` | Orekit ephemeris data | TrackTLE generation |
| `SPACETRACK_TOKEN` | Space-Track API access | Breakup detection, TLE queries |
| `ESA_DISCOS_API_TOKEN` | ESA DiscoSweb access | HAMR object filtering |
| `UCT_ML_EVENT_ENDPOINT` | ML model endpoint | Event detection (optional) |
| `UCT_ML_EVENT_API_KEY` | ML model authentication | Event detection (optional) |

### UDL Data Requirements

The system expects the following data from UDL:
- Observations with RA/Dec angles, timestamps, site information
- TLE/Elset data for orbital elements
- State vectors (position/velocity) for proximity filtering

---

## Workarounds and Best Practices

### For Missing Radar/RF Data
1. Use `OP` (Optical) sensor type for all real-data benchmarks
2. For multi-sensor testing, use simulation mode

### For Unreliable Event Detection
1. Default to `NE` (No Events) for production datasets
2. Use `BU` when Space-Track access is available
3. Manually validate `MB` and `LL` filtered results

### For Incomplete Physical Data
1. HAMR filtering may return empty results without ESA data
2. Consider falling back to TLE-based B* estimation (approximate)

### For Missing State Vectors
1. Close (C) filtering requires complete state data
2. If only position available, velocity check is skipped
3. Apparent (A) filtering works with observation-only data

---

## Version History

| Date | Change |
|------|--------|
| 2026-01 | Initial documentation based on alignment analysis |

---

## References

- Lewis's Benchmarking Documentation (UCT Common Task Framework)
- Lewis's Transcript (System specifications and design rationale)
- UCT Benchmark Implementation Code
