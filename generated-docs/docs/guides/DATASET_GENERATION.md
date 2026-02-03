# Dataset Generation Guide

This guide explains how to generate benchmark datasets for UCTP algorithm evaluation.

## Overview

The UCT Benchmark system generates datasets at different tiers (T1-T5), each with varying levels of data processing:

| Tier | Description | Processing |
|------|-------------|------------|
| T1 | Optimal | All criteria met, no manipulation needed |
| T2 | Excess | Too many observations, requires downsampling |
| T3 | Insufficient | Not enough quality observations, requires simulation |
| T4 | Poor | Criteria partially met, may need simulation |
| T5 | Impossible | Criteria cannot be met, adjust parameters |

## Prerequisites

Before generating datasets:

1. **API Token**: Ensure `UDL_TOKEN` is set in your environment
2. **Java 17+**: Required for Orekit simulation
3. **Dependencies**: Run `pip install -e .` in the project directory

---

## 16-Character Legacy Dataset Code Format

The UCT Benchmark uses a **16-character legacy code** to encode all dataset parameters. This format was defined in Lewis's Benchmarking Documentation.

### Code Structure

| Position | Length | Component | Valid Values |
|----------|--------|-----------|--------------|
| 1 | 1 | Object Type | H, C, A, U, N |
| 2-3 | 2 | Target Object % | 50, 10, 01, UN |
| 4-6 | 3 | Orbital Regime | LEO, MEO, GEO, HEO, ALL |
| 7-8 | 2 | Event | MB, BU, LL, NE |
| 9-10 | 2 | Sensor Type | OP, RA, RF, FU |
| 11 | 1 | Orbit Coverage | A, S, N |
| 12 | 1 | Track Gap | A, S, N |
| 13 | 1 | Observation Count | A, S, N |
| 14 | 1 | Object Count | H, S, L |
| 15-16 | 2 | Fitspan | 01-14 days |

### Example Code

`H50LEONEOPSSSS07` means:
- **H**: HAMR objects (High Area-to-Mass Ratio)
- **50**: 50% of objects are target type
- **LEO**: Low Earth Orbit
- **NE**: No Events (no maneuvers or breakups)
- **OP**: Optical sensors
- **S**: Standard orbit coverage
- **S**: Standard track gap
- **S**: Standard observation count
- **S**: Standard object count (40)
- **07**: 7 days fitspan

---

## Component Descriptions

### Object Type (Position 1)

| Code | Name | Description |
|------|------|-------------|
| H | HAMR | High Area-to-Mass Ratio (A/M > 1.0 m²/kg). Requires ESA DiscoSweb data. |
| C | Close | Physical proximity: distance < 100 km AND relative velocity < 100 m/s. Requires state vectors. |
| A | Apparent | Angular proximity: < 0.5° separation in the sky. Uses observation RA/Dec. |
| U | Unspecified | No filtering, include all objects. |
| N | Calibration | Only well-known calibration satellites from predefined list. |

**Note on Close (C) Objects**: Per Lewis's specification, Close objects must meet BOTH position AND velocity thresholds. Objects that are close in position but have high relative velocity (e.g., head-on collision trajectories) are NOT considered "Close" for UCT purposes.

### Target Percentage (Positions 2-3)

| Code | Meaning |
|------|---------|
| 50 | 50% of objects are target type |
| 10 | 10% of objects are target type |
| 01 | 1% of objects are target type |
| UN | Unspecified percentage (no enforcement) |

### Orbital Regime (Positions 4-6)

| Code | Meaning |
|------|---------|
| LEO | Low Earth Orbit (< 2000 km altitude) |
| MEO | Medium Earth Orbit (2000-35786 km) |
| GEO | Geostationary Orbit (~35786 km) |
| HEO | Highly Elliptical Orbit |
| ALL | All orbital regimes |
| LMO | LEO + MEO combined |
| LMG | LEO + MEO + GEO combined |

### Event Code (Positions 7-8)

| Code | Name | Description | Reliability |
|------|------|-------------|-------------|
| NE | No Events | Satellites without detected events | ✅ Reliable |
| MB | Maneuver Between | Impulsive maneuvers between observations | ⚠️ Heuristic (TLE discontinuity) |
| BU | Breakup | Fragmentation/collision events | ⚠️ Requires Space-Track API |
| LL | Long Low-Thrust | Long-duration low-thrust maneuvers | ⚠️ Heuristic |

**Note**: Event detection reliability depends on ML Labelling Team model availability. When unavailable, TLE-based heuristics are used as fallback.

### Sensor Type (Positions 9-10)

| Code | Name | Description | Status |
|------|------|-------------|--------|
| OP | Optical | Optical/telescope observations | ✅ Fully Supported |
| RA | Radar | Radar observations | ❌ No UDL data |
| RF | RF | Radio frequency observations | ❌ No UDL data |
| FU | Fusion | Multi-sensor fusion | ❌ No UDL data |

**Note**: Only Optical (OP) sensor type is currently available from UDL.

### Quality Levels (Positions 11-13)

The A/S/N quality levels indicate what percentage of objects have "low" quality metrics:

| Code | Meaning | Interpretation |
|------|---------|----------------|
| A | All | >90% objects have LOW quality (sparse data wanted) |
| S | Standard | 40-60% objects have LOW quality (mixed) |
| N | None | <10% objects have LOW quality (dense data wanted) |

Applied to:
- **Orbit Coverage** (Position 11): Fraction of orbit with observations
- **Track Gap** (Position 12): Gap between observation tracks
- **Observation Count** (Position 13): Number of observations per satellite

### Object Count (Position 14)

| Code | Count | Description |
|------|-------|-------------|
| H | 80 | High object count |
| S | 40 | Standard object count |
| L | 10 | Low object count |

### Fitspan (Positions 15-16)

Duration of the dataset in days (01-14).

---

## Method 1: Web Interface (Recommended)

### Step 1: Start the Application

```bash
# Start backend
cd UCT-Benchmark-DMR/combined
uvicorn backend_api.main:app --reload --port 8000

# Start frontend (in another terminal)
cd UCT-Benchmark-DMR/combined/frontend
npm run dev
```

### Step 2: Navigate to Dataset Generator

1. Open http://localhost:5173
2. Click **Datasets** in the navigation
3. Click **Generate New Dataset**

### Step 3: Configure Dataset Parameters

Use the web form to configure parameters, which will generate a 16-character code.

### Step 4: Generate and Download

1. Click **Generate Dataset**
2. Wait for processing (may take several minutes)
3. Click **Download** when complete

---

## Method 2: Python API

### Using LegacyDatasetCode Class

```python
from uct_benchmark.config.dataset_schema import LegacyDatasetCode

# Parse an existing legacy code
code = LegacyDatasetCode.from_code("H50LEONEOPSSSS07")
print(f"Object Type: {code.object_type}")        # H
print(f"Target %: {code.target_percentage}")      # 50
print(f"Regime: {code.orbital_regime}")           # LEO
print(f"Event: {code.event}")                     # NE
print(f"Sensor: {code.sensor_type}")              # OP
print(f"Coverage: {code.orbit_coverage}")         # S
print(f"Gap: {code.track_gap}")                   # S
print(f"Obs Count: {code.observation_count}")     # S
print(f"Obj Count: {code.object_count}")          # S
print(f"Fitspan: {code.fitspan_days} days")       # 7

# Create a new legacy code from parameters
new_code = LegacyDatasetCode(
    object_type="U",
    target_percentage="50",
    orbital_regime="LEO",
    event="NE",
    sensor_type="OP",
    orbit_coverage="S",
    track_gap="S",
    observation_count="S",
    object_count="S",
    fitspan_days=7,
)
print(f"Generated Code: {new_code.to_code()}")  # U50LEONEOPSSSS07
```

### Generating Datasets with Legacy Codes

```python
from uct_benchmark.api.apiIntegration import generateDataset
import os

# Set API token
os.environ["UDL_TOKEN"] = "your_base64_token_here"

# Generate dataset using legacy code
dataset, obs_truth, state_truth, elset_truth = generateDataset(
    UDL_token=os.environ["UDL_TOKEN"],
    legacy_code="H50LEONEOPSSSS07",  # Use 16-char legacy code
    verbose=True
)
```

### Direct API Call with Full Control

```python
from uct_benchmark.api.apiIntegration import generateDataset

dataset, obs_truth, state_truth, elset_truth = generateDataset(
    UDL_token="your_token",
    ESA_token="your_esa_token",  # Required for HAMR (H) objects
    satIDs=[25544, 25545, 25546],  # Specific satellites (optional)
    timeframe=7,  # Days
    timeunit="d",
    tier="T2",
    verbose=True
)
```

---

## Method 3: REST API

### Create Dataset from Legacy Code

```bash
# Create dataset from legacy code
curl -X POST "http://localhost:8000/api/v1/datasets/legacy" \
  -H "Content-Type: application/json" \
  -d '{"legacy_code": "H50LEONEOPSSSS07", "name": "hamr_leo_dataset"}'

# Validate a code
curl "http://localhost:8000/api/v1/datasets/validate/H50LEONEOPSSSS07"
```

---

## Non-Reference Observations for True Negatives

To support True Negative calculation, datasets can include observations from satellites NOT in the reference set. These observations should NOT be matched by the algorithm.

### Generating Datasets with Non-Reference Observations

```python
from uct_benchmark.data.dataManipulation import generate_dataset_with_non_reference

# Generate dataset with 10% non-reference observations
dataset_df, non_ref_truth, metadata = generate_dataset_with_non_reference(
    obs_df=all_observations,  # All available observations
    sat_params=satellite_parameters,
    reference_norad_ids=[25544, 28654, 33591],  # Reference satellites
    include_non_ref_obs=True,
    non_ref_ratio=0.1,  # 10% non-reference
    quality_level="standard",
    seed=42,
)

print(f"Reference obs: {metadata['reference_observation_count']}")
print(f"Non-ref obs: {metadata['non_ref_observation_count']}")
print(f"Total obs: {metadata['total_observation_count']}")
```

---

## Dataset Output Format

Generated datasets are saved as JSON:

```json
{
  "metadata": {
    "name": "H50LEONEOPSSSS07_20260131",
    "legacy_code": "H50LEONEOPSSSS07",
    "tier": "T2",
    "generated_at": "2026-01-31T10:30:00Z",
    "observation_count": 5000,
    "object_count": 40
  },
  "dataset_obs": [
    {
      "id": "obs-uuid-001",
      "obTime": "2026-01-15T12:00:00.000000Z",
      "ra": 123.456,
      "declination": 45.678,
      "trackId": 1,
      "uct": true
    }
  ],
  "reference": [
    {
      "satNo": 25544,
      "epoch": "2026-01-15T12:00:00.000000",
      "xpos": -7365.971,
      "ypos": -1331.400,
      "zpos": 1514.249,
      "line1": "1 25544U ...",
      "line2": "2 25544 ..."
    }
  ]
}
```

---

## Quality Level Thresholds

The A/S/N quality levels map to specific numeric thresholds:

### Orbit Coverage

| Level | Objects with LOW Coverage | Target Coverage |
|-------|--------------------------|-----------------|
| A | >90% | 1-10% orbital coverage |
| S | 40-60% | 5-30% orbital coverage |
| N | <10% | 30-80% orbital coverage |

### Track Gap (Orbital Periods)

| Level | Objects with LONG Gaps | Target Gap |
|-------|------------------------|------------|
| A | >90% | 3-10 orbital periods |
| S | 40-60% | 1-4 orbital periods |
| N | <10% | 0.2-1 orbital periods |

### Observation Count per Satellite

| Level | Objects with LOW Obs | Target Count |
|-------|---------------------|--------------|
| A | >90% | 5-30 observations |
| S | 40-60% | 30-100 observations |
| N | <10% | 100-250 observations |

---

## Pipeline Integration

### Window Selection

```python
from uct_benchmark.data.windowSelection import create_criteria_from_legacy_code

criteria = create_criteria_from_legacy_code(
    legacy_code="H50LEONEOPSSSS07"
)
print(f"Target coverage: {criteria.target_coverage}")
print(f"Target gap: {criteria.target_track_gap_periods} periods")
```

### Downsampling Configuration

```python
from uct_benchmark.data.dataManipulation import get_downsample_config_from_legacy

config = get_downsample_config_from_legacy(
    legacy_code="H50LEONEOPSSSS07"
)
print(f"Target coverage: {config.target_coverage}")
print(f"Max obs per sat: {config.max_obs_per_sat}")
```

---

## Validation

After generation, validate your dataset:

```bash
# Run validation suite
cd UCT-Benchmark-DMR/combined
python validation/run_validation.py --dataset-path data/my_dataset.json
```

---

## Common Issues

### "UDL token not set"

```bash
# Set environment variable
export UDL_TOKEN="your_base64_token"

# Or in Python
import os
os.environ["UDL_TOKEN"] = "your_token"
```

### "Orekit initialization failed"

See [Orekit Setup Guide](OREKIT_SETUP.md) for Java configuration.

### "Not enough observations" or TIER_5 Result

If you receive a TIER_5 (Impossible) result:
- Increase the time window (fitspan)
- Select a different orbital regime
- Lower the object count requirement
- Use "UN" (unspecified) for target percentage
- Switch to "NE" (No Events) for event type

### "HAMR filtering returns empty"

HAMR (H) object type requires ESA DiscoSweb data. Ensure:
- `ESA_DISCOS_API_TOKEN` is set
- ESA API is accessible
- Consider using TLE-based B* estimation as fallback

---

## Related Documentation

- [Orekit Setup](OREKIT_SETUP.md)
- [Pipeline Documentation](../technical/PIPELINE.md)
- [Data Sources](../technical/DATA_SOURCES.md)
- [Configuration](../technical/CONFIGURATION.md)
- [Evaluation Metrics](../technical/EVALUATION_METRICS.md)
