# Dataset Generation Guide

This document describes the dataset generation pipeline for the UCT Benchmark, including the 16-character legacy code format and non-reference observation inclusion for True Negative calculation.

## 16-Character Dataset Code Format

The legacy dataset code format uses a 16-character string to encode all dataset parameters. This format was defined in Louis's Benchmarking Documentation.

### Code Structure

| Position | Length | Component | Valid Values |
|----------|--------|-----------|--------------|
| 1 | 1 | Object Type | H, C, A, U, N |
| 2-3 | 2 | Target Object % | 50, 10, 01, UN |
| 4-6 | 3 | Orbital Regime | LEO, MEO, GEO, HEO, ALL |
| 7-8 | 2 | Event | MB, BU, LL, NE |
| 9-10 | 2 | Sensor Type | OP, RA, RF, FU, OR, RO, RR |
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

## Component Descriptions

### Object Type (Position 1)

| Code | Name | Description |
|------|------|-------------|
| H | HAMR | High Area-to-Mass Ratio (A/M > 1.0 m²/kg) |
| C | Close | Physical proximity (< 100 km between objects) |
| A | Apparent | Angular proximity (< 0.5° separation) |
| U | Unspecified | No filtering, include all objects |
| N | Calibration | Only well-known calibration satellites |

### Target Percentage (Positions 2-3)

| Code | Meaning |
|------|---------|
| 50 | 50% of objects are target type |
| 10 | 10% of objects are target type |
| 01 | 1% of objects are target type |
| UN | Unspecified percentage |

### Orbital Regime (Positions 4-6)

| Code | Meaning |
|------|---------|
| LEO | Low Earth Orbit (< 2000 km) |
| MEO | Medium Earth Orbit (2000-35786 km) |
| GEO | Geostationary Orbit (~35786 km) |
| HEO | Highly Elliptical Orbit |
| ALL | All orbital regimes |
| LMO | LEO + MEO |
| LMG | LEO + MEO + GEO |

### Event Code (Positions 7-8)

| Code | Name | Description |
|------|------|-------------|
| MB | Maneuver Between | Impulsive maneuvers between observations |
| BU | Breakup | Fragmentation/collision events |
| LL | Long Low-Thrust | Long-duration low-thrust maneuvers |
| NE | No Events | Satellites without detected events |

### Sensor Type (Positions 9-10)

| Code | Name | Description |
|------|------|-------------|
| OP | Optical | Optical/telescope observations |
| RA | Radar | Radar observations |
| RF | RF | Radio frequency observations |
| FU | Fusion | Multi-sensor fusion |
| OR | Optical-Radar | Combined optical and radar |
| RO | Radar-Optical | Primarily radar with optical |
| RR | Radar-RF | Combined radar and RF |

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

## Using Legacy Codes

### Python API

```python
from uct_benchmark.config.dataset_schema import LegacyDatasetCode

# Parse a legacy code
code = LegacyDatasetCode.from_code("H50LEONEOPSSSS07")
print(f"Object Type: {code.object_type}")
print(f"Regime: {code.orbital_regime}")
print(f"Fitspan: {code.fitspan_days} days")

# Create a legacy code from parameters
code = LegacyDatasetCode(
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
print(f"Code: {code.to_code()}")  # U50LEONEOPSSSS07
```

### REST API

```bash
# Create dataset from legacy code
curl -X POST "http://localhost:8000/api/v1/datasets/legacy" \
  -H "Content-Type: application/json" \
  -d '{"legacy_code": "H50LEONEOPSSSS07", "name": "hamr_leo_dataset"}'

# Validate a code
curl "http://localhost:8000/api/v1/datasets/validate/H50LEONEOPSSSS07"
```

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
    quality_tier="T2S",
    seed=42,
)

print(f"Reference obs: {metadata['reference_observation_count']}")
print(f"Non-ref obs: {metadata['non_ref_observation_count']}")
print(f"Total obs: {metadata['total_observation_count']}")
```

### Non-Reference Truth DataFrame

The `non_ref_truth` DataFrame contains ground truth for non-reference observations:

| Column | Description |
|--------|-------------|
| id | Observation ID |
| source_norad_id | Actual satellite NORAD ID |
| is_non_reference | Always True |

This is used during evaluation to identify which observations the algorithm should NOT match.

## UDL Export Format

Datasets can be exported in UDL-compatible format for distribution:

```python
from uct_benchmark.output.udl_export import export_dataset_for_udl

result = export_dataset_for_udl(
    obs_df=dataset_df,
    output_dir=Path("./exports"),
    dataset_name="H50LEONEOPSSSS07",
    legacy_code="H50LEONEOPSSSS07",
    metadata=generation_metadata,
)
```

Output structure:
```
H50LEONEOPSSSS07/
  observations.json    # Decorrelated observations (no satNo)
  truth.json          # Ground truth mapping (track_id -> satNo)
  metadata.json       # Dataset metadata with legacy code
  manifest.json       # File checksums
```

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

## Event Detection

### Breakup Events (BU)

Breakup events are fetched from Space-Track and CelesTrak:

```python
from uct_benchmark.data.eventDetection import filter_by_breakup_event

filtered_obs, events, metadata = filter_by_breakup_event(
    obs_df=observations,
    start_date=datetime(2021, 1, 1),
    end_date=datetime(2021, 12, 31),
)
print(f"Found {len(events)} breakup events")
print(f"Affected satellites: {metadata['satellites_matched']}")
```

### Long-Duration Maneuvers (LL)

```python
from uct_benchmark.data.eventDetection import detect_long_duration_maneuvers

events = detect_long_duration_maneuvers(
    tle_df=tle_history,
    satellite_id=25544,
    config=EventDetectionConfig(long_thrust_duration_days=7.0),
)
```

## References

- Louis's Benchmarking Documentation
- [EVALUATION_METRICS.md](EVALUATION_METRICS.md) - Metric definitions
- UCT Benchmark API Documentation
