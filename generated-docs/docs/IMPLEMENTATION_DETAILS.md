> **Note:** This documentation has moved to `generated-docs/docs/`.
> Please see [generated-docs/docs/technical/](../../../generated-docs/docs/technical/) for the latest version.

# UCT Benchmarking Enhancement - Implementation Details

## Executive Summary

This document details the comprehensive implementation of UCT Benchmarking enhancements covering API optimization, physics-based downsampling, advanced simulation, and dataset management.

---

## Phase 1: API Enhancements

### 1.1 Response Caching

The `QueryCache` class provides TTL-based caching to reduce redundant API calls:

```python
class QueryCache:
    def __init__(self, max_size=1000, ttl_seconds=900):
        self._cache = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
```

Features:
- MD5-based cache key generation from service + params
- Automatic TTL expiration (default 15 minutes)
- LRU-style eviction when max size reached

### 1.2 Count-First Query Strategy

The `smart_query()` function checks record count before fetching:

1. Query `/count` endpoint first
2. If count > threshold (default 10,000), split into chunks
3. Otherwise, proceed with single query

### 1.3 Adaptive Batch Sizing

Batch sizes vary by orbital regime due to different observation densities:

| Regime | Batch Size | Rationale |
|--------|------------|-----------|
| LEO | 6 hours | High observation density |
| MEO | 12 hours | Medium density |
| GEO | 1 day | Low density, long visibility |
| HEO | 8 hours | Variable density |

### 1.4 New UDL Service Wrappers

Added wrappers for:
- `queryRadarObservations()` - Radar sensor data
- `queryRFObservations()` - RF sensor data
- `queryConjunctions()` - CDM data
- `queryManeuvers()` - Maneuver events
- `querySensorCalibration()` - Sensor calibration data

### 1.5 Parallel Service Queries

`pullComprehensiveData()` uses asyncio to query multiple services concurrently:

```python
async def _async_pull_comprehensive_data(token, sat_ids, time_range, services):
    tasks = [query_service(svc) for svc in services]
    results = await asyncio.gather(*tasks)
    return dict(results)
```

---

## Phase 2: Downsampling Improvements

### 2.1 Regime-Specific Profiles

Each orbital regime has tuned parameters:

```python
DOWNSAMPLING_PROFILES = {
    'LEO': {
        'min_coverage_pct': 0.02,
        'max_coverage_pct': 0.15,
        'min_track_gap_periods': 1.5,
        'max_track_gap_periods': 5.0,
        'obs_per_track': (3, 10),
    },
    # ... MEO, GEO, HEO profiles
}
```

### 2.2 Track Identification Algorithm

```python
def identify_tracks(obs_df, gap_threshold_minutes=90):
    # Group by sensor/location + satellite
    # Split on gaps > threshold
    # Return list of track DataFrames
```

### 2.3 Track-Preserving Downsampling

Key principle: Downsample at track level, not observation level.

1. Identify tracks
2. Select subset of tracks for coverage
3. Thin within tracks (preserve boundaries)

### 2.4 3D Coverage Calculation

Improved coverage uses arc-length instead of 2D polygon area:

```python
def compute_3d_coverage(obs_df, orbital_elements):
    mean_anomalies = compute_mean_anomaly_from_obs(obs_df, orbital_elements)
    arc_coverage = compute_arc_coverage(mean_anomalies)
    # Weighted average with polygon coverage
    return 0.7 * arc_coverage + 0.3 * poly_coverage
```

---

## Phase 3: Simulation Enhancements

### 3.1 Atmospheric Refraction Model

Bennett's formula with corrections:

```python
def apply_atmospheric_refraction(elevation_true, wavelength_nm=550):
    # Bennett's formula (arcminutes)
    R = 1/tan(el + 7.31/(el + 4.4))
    
    # Apply corrections:
    # - Pressure/temperature
    # - Chromatic (wavelength)
    # - Humidity
    
    return elevation_true + R_arcsec / 3600
```

### 3.2 Velocity Aberration Model

Classical aberration correction:

```python
def compute_velocity_aberration(ra, dec, observer_velocity, target_velocity):
    # n' = n + v/c - n*(n.v/c)
    # Returns corrected RA, Dec
```

### 3.3 Sensor Noise Models

Sensor-specific noise characteristics:

| Sensor | Angular (arcsec) | Timing (ms) | Notes |
|--------|------------------|-------------|-------|
| GEODSS | 0.5 | 1.0 | Ground-based optical |
| SBSS | 0.3 | 0.5 | Space-based |
| Commercial EO | 1.0 | 5.0 | Variable quality |
| Radar | 0.01 deg | 0.1 | + range noise |

### 3.4 Photometric Simulation

Lambertian diffuse reflection model:

```python
def simulate_magnitude(sat_pos, sun_pos, obs_pos, cross_section, albedo):
    phase_angle = compute_phase_angle(sat_pos, sun_pos, obs_pos)
    phase_function = lambertian_phase_function(phase_angle)
    
    # Magnitude from inverse square law + phase function
    mag = -26.7 - 2.5*log10(albedo * cross_section * phase_function / range^2)
    
    # Add atmospheric extinction
    mag += 0.2 * airmass
    
    return mag
```

---

## Phase 4: Dataset Configuration

### 4.1 Enhanced Dataset Code Format

```
Format: {OBJ}_{REG}_{EVT}_{SEN}_{QTY}_{WIN}_{VER}
Example: HAMR_LEO_MAN_EO_T2S_07D_001

Components:
- OBJ (4 chars): HAMR, PROX, NORM, DEBR
- REG (3 chars): LEO, MEO, GEO, HEO, ALL
- EVT (3 chars): NRM, MAN, BRK, PRX
- SEN (2 chars): EO, RA, RF, MX
- QTY (3 chars): T1H, T1S, T2H, T2S, T3L, T4L
- WIN (3 chars): 01D-99D
- VER (3 chars): Version number
```

### 4.2 YAML Configuration Schema

```yaml
metadata:
  name: "Dataset Name"
  version: "1.0.0"

satellite_selection:
  regimes: [LEO]
  min_observations: 50
  target_count: 40

quality_targets:
  tier: T2
  coverage:
    min: 0.02
    max: 0.10

reproducibility:
  seed: 42
```

### 4.3 Metadata Generation

Each dataset generates comprehensive metadata including:
- Run ID and timestamp
- Configuration hash for reproducibility
- Processing metrics (API calls, records, errors)
- Quality statistics (coverage, gaps)

---

## Phase 5: Logging & Monitoring

### 5.1 Structured Logging

```python
def setup_logging(config, run_id):
    # Main log: uctp_{run_id}.log
    # API log: api_{run_id}.log
    # Metrics: metrics_{run_id}.json
```

### 5.2 Metrics Collection

`MetricsCollector` tracks:
- Total API calls and records fetched
- Per-satellite processing statistics
- Tier distribution
- Coverage and gap statistics

---

## Testing

Test files cover all major components:

| Test File | Coverage |
|-----------|----------|
| `test_api_enhancements.py` | Caching, regime detection, metrics |
| `test_downsampling_enhancements.py` | Track ID, preservation, coverage |
| `test_simulation_enhancements.py` | Refraction, aberration, noise |
| `test_dataset_config.py` | YAML loading, metadata generation |

---

## Dependencies

All implementations use existing project dependencies:
- numpy, pandas (data processing)
- aiohttp (async HTTP)
- pyyaml (configuration)
- loguru (logging)
- orekit-jpype (orbit propagation)
