# Data Sources

## Overview

The UCT Benchmarking framework integrates with multiple space surveillance data sources to obtain observation data, state vectors, TLEs, and satellite physical properties.

---

## Primary Data Source: Unified Data Library (UDL)

### Description
The Unified Data Library (UDL) is the primary data source, providing access to:
- Electro-optical observations
- Radar observations
- State vectors with covariance
- Element sets (TLEs)
- Space event data

### Current Usage Note

Per tech lead Lewis, the project currently focuses on **optical observations** (azimuth and elevation from telescopes):

> "We in particular have been looking at optical observations, so from a telescope, and the reason is because in the UDL we only had access to optical observations. Radar observations and passive RF observations are a lot more difficult to come by. We didn't have a lot of government purpose rights access to radar observations."

The infrastructure is being designed to support radar and RF observations when they become available, but the current pipeline presupposes optical observations.

**Observation Definition**: A single measurement from a telescope, consisting of:
- Azimuth (angle in the horizontal plane)
- Elevation (angle above the horizon)
- Timestamp

### Authentication
```python
# Generate token from credentials
from uct_benchmark.api.apiIntegration import UDLTokenGen
token = UDLTokenGen(username, password)

# Or use environment variable
# UDL_TOKEN in .env file (Base64 encoded)
```

### Available Services

| Service | Description | Key Fields |
|---------|-------------|------------|
| `eoobservation` | Electro-optical observations | ra, declination, obTime, satNo |
| `radarobservation` | Radar observations | range, rangeRate, az, el |
| `statevector` | State vectors | xpos, ypos, zpos, xvel, yvel, zvel, cov |
| `elset` | Element sets (TLEs) | line1, line2, epoch |
| `elset/current` | Latest TLEs | line1, line2 |

### Query Parameters

```python
# Standard parameters
params = {
    "satNo": "12345",           # Satellite NORAD ID
    "obTime": ">now-10 days",   # Time range (relative)
    "obTime": "2025-01-01T00:00:00.000000Z..2025-01-10T00:00:00.000000Z",  # Absolute
    "uct": "false",             # Include UCTs
    "dataMode": "REAL",         # REAL or SIMULATED
    "sort": "epoch,DESC",       # Sort order
    "maxResults": "1000"        # Limit results
}

# Inequality operators
# '>value' - greater than or equal
# '<value' - less than or equal
# '~value' - not equal
# '*value*' - like
# 'val1..val2' - between
# 'val1,val2' - in list
```

### Usage Example

```python
from uct_benchmark.api.apiIntegration import UDLQuery, asyncUDLBatchQuery

# Single query
observations = UDLQuery(token, "eoobservation", {
    "satNo": "25544",
    "obTime": ">now-7 days",
    "dataMode": "REAL"
})

# Batch queries (rate-limited)
params_list = [{"satNo": str(id)} for id in satellite_ids]
all_obs = asyncUDLBatchQuery(token, "eoobservation", params_list, dt=0.1)
```

---

## Secondary Data Sources

### Space-Track

**Purpose**: TLE history, satellite catalog data

**Website**: https://www.space-track.org

**Authentication**:
```python
from uct_benchmark.api.apiIntegration import spacetrackTokenGen
token = spacetrackTokenGen(username, password)
```

**Available Data**:
- TLE archives
- Satellite catalog (SATCAT)
- Decay predictions
- Launch information

**Query Example**:
```python
from uct_benchmark.api.apiIntegration import spacetrackQuery

satcat = spacetrackQuery(token, {
    "NORAD_CAT_ID": "25544"
}, request="satcat")
```

---

### CelesTrak

**Purpose**: Public TLE data, satellite catalog

**Website**: https://celestrak.org

**Authentication**: None required

**Available Data**:
- Current TLEs (GP data)
- Supplemental TLEs
- Satellite catalog

**Query Example**:
```python
from uct_benchmark.api.apiIntegration import celestrakQuery, celestrakSatcat

# Get TLE for specific satellite
tle_data = celestrakQuery({"CATNR": "25544"}, table="gp")

# Get full catalog
catalog = celestrakSatcat()
```

---

### ESA DiscoWeb

**Purpose**: Satellite physical properties (mass, cross-sectional area)

**Website**: https://discosweb.esoc.esa.int

**Authentication**: Bearer token (generate at website)

**Available Data**:
- Satellite mass
- Cross-sectional area
- Object dimensions
- Launch information

**Query Example**:
```python
from uct_benchmark.api.apiIntegration import discoswebQuery

# Query by NORAD ID
sat_properties = discoswebQuery(
    esa_token,
    "in(satno,(25544,12345))",
    data="objects"
)
```

---

## Data Fields Reference

### Observation Data Fields

| Field | Type | Description | Unit |
|-------|------|-------------|------|
| `id` | string | Unique observation ID | - |
| `satNo` | int | NORAD catalog number | - |
| `obTime` | datetime | Observation timestamp | UTC |
| `ra` | float | Right ascension | degrees |
| `declination` | float | Declination | degrees |
| `range` | float | Slant range (radar) | km |
| `rangeRate` | float | Range rate (radar) | km/s |
| `az` | float | Azimuth | degrees |
| `el` | float | Elevation | degrees |
| `trackId` | string | Track identifier | - |
| `sensorName` | string | Sensor designation | - |
| `dataMode` | string | REAL or SIMULATED | - |
| `uct` | bool | Uncorrelated track flag | - |

### State Vector Fields

| Field | Type | Description | Unit |
|-------|------|-------------|------|
| `satNo` | int | NORAD catalog number | - |
| `epoch` | datetime | State epoch | UTC |
| `xpos` | float | X position (J2000 ECI) | km |
| `ypos` | float | Y position | km |
| `zpos` | float | Z position | km |
| `xvel` | float | X velocity | km/s |
| `yvel` | float | Y velocity | km/s |
| `zvel` | float | Z velocity | km/s |
| `cov` | array | 6x6 covariance matrix | km^2, km^2/s, km^2/s^2 |
| `dragCoeff` | float | Drag coefficient | - |
| `solarRadPressCoeff` | float | SRP coefficient | - |

### TLE Fields (Parsed)

| Field | Type | Description |
|-------|------|-------------|
| `NORAD_ID` | int | Catalog number |
| `classification` | string | U/C/S |
| `COSPAR_ID` | string | International designator |
| `epoch` | datetime | TLE epoch |
| `inclination` | float | Orbital inclination (deg) |
| `RAAN` | float | Right ascension of ascending node (deg) |
| `eccentricity` | float | Orbital eccentricity |
| `perigee` | float | Argument of perigee (deg) |
| `mean_anomaly` | float | Mean anomaly (deg) |
| `mean_motion` | float | Mean motion (rev/day) |
| `B_star` | float | Drag term |
| `line1` | string | TLE line 1 |
| `line2` | string | TLE line 2 |

---

## Data Quality Considerations

### Observation Data Quality

| Quality Factor | Good | Moderate | Poor |
|----------------|------|----------|------|
| Observation Count | >150/3 days | 50-150/3 days | <50/3 days |
| Orbital Coverage | >95% | 40-95% | <40% |
| Track Gap | <2 periods | 2-5 periods | >5 periods |

### State Vector Quality

- Prefer state vectors with covariance (`cov` field populated)
- More recent epochs are generally more accurate
- Check for missing physical parameters (mass, area)

### TLE Limitations

- SGP4/SDP4 propagation accuracy degrades over time
- TLE fit errors typically 1-10 km at epoch
- Not suitable for high-precision applications

---

## Environment Configuration

Required environment variables (`.env` file):

```bash
# UDL Authentication (Base64 encoded username:password)
UDL_TOKEN=dXNlcm5hbWU6cGFzc3dvcmQ=

# ESA DiscoWeb API Token
ESA_TOKEN=your_bearer_token_here

# Optional: Orekit data path
OREKIT_DATA_PATH=./orekit-data-main
```

---

## Rate Limiting

| Source | Rate Limit | Implementation |
|--------|------------|----------------|
| UDL | ~10 req/sec | `asyncUDLBatchQuery(dt=0.1)` |
| Space-Track | 20 req/min | Session-based throttling |
| CelesTrak | Unlimited | None |
| DiscoWeb | 100 req/hr | Retry with backoff |

---

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check token validity, regenerate if expired
2. **500 Internal Error**: Query timeout, reduce time window or result count
3. **429 Too Many Requests**: Increase rate limit delay
4. **Empty Results**: Verify satellite exists in timeframe, check dataMode

### Data Gaps

If expected data is missing:
1. Check satellite observability in time window
2. Verify sensor coverage for orbital regime
3. Confirm data classification (REAL vs SIMULATED)
4. Check for maintenance outages on data providers
