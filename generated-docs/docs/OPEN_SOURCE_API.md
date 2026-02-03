# Open Source Data API Reference

This document describes the open source data integration APIs available in the UCT Benchmark pipeline.

## Overview

The UCT Benchmark integrates four open source data providers to enable:
- **Accurate HAMR detection** using real satellite mass data
- **Multi-phenomenology (MX) datasets** with RF observations
- **Independent validation** against ILRS ground truth
- **Rich metadata** for satellite filtering and analysis

## Data Sources

| Source | Type | License | Authentication |
|--------|------|---------|----------------|
| **UCS** | Metadata | Open | None |
| **GCAT** | Catalog | CC-BY | None |
| **SatNOGS** | RF Observations | CC-BY-SA | None |
| **ILRS** | Validation | Public Domain | None* |

*Full ILRS range data requires NASA Earthdata account (free registration)

---

## DataSourceManager

The `DataSourceManager` class is the primary interface for open source data integration.

### Basic Usage

```python
from uct_benchmark.database import DatabaseManager
from uct_benchmark.api.data_source_manager import DataSourceManager

# Initialize
db = DatabaseManager('data/uct_benchmark.db')
dsm = DataSourceManager(db)

# Enrich a single satellite
data = dsm.enrich_satellite(25544)  # ISS
print(data['data']['purpose'])  # "Science/Research"

# Check if satellite is HAMR
if dsm.is_hamr_object(12345):
    print("High area-to-mass ratio object detected!")

# Get ILRS-tracked satellites
ilrs_sats = dsm.get_ilrs_tracked_satellites()
print(f"{len(ilrs_sats)} satellites available for validation")
```

### Methods

#### `enrich_satellite(sat_no: int, force_refresh: bool = False) -> Dict`

Enrich a single satellite with data from UCS and GCAT.

**Returns:**
```python
{
    "sat_no": 25544,
    "enriched": True,
    "ucs_match": True,
    "gcat_match": True,
    "data": {
        "purpose": "Science/Research",
        "operator": "NASA",
        "launch_site": "TYMSC",
        "mass_kg": 419725.0,
        "amr_m2_kg": 0.00238
    }
}
```

#### `enrich_satellites_batch(sat_nos: List[int], ...) -> EnrichmentReport`

Batch enrich multiple satellites (more efficient for large lists).

```python
report = dsm.enrich_satellites_batch([25544, 43013, 8820])
print(f"Enriched: {report.enriched_count}/{report.total_satellites}")
print(f"HAMR detected: {report.hamr_detected}")
```

#### `calculate_accurate_amr(sat_no: int) -> Optional[float]`

Calculate area-to-mass ratio using real mass data from UCS.

```python
amr = dsm.calculate_accurate_amr(25544)
if amr and amr > 0.1:
    print("HAMR object")
```

#### `is_hamr_object(sat_no: int) -> bool`

Determine if satellite is High Area-to-Mass Ratio (AMR > 0.1 m²/kg).

#### `get_ilrs_tracked_satellites() -> List[int]`

Get NORAD IDs of all ILRS-tracked satellites.

---

## Open Source API Wrappers

Lower-level API wrappers for direct data source access.

### SatNOGS Functions

```python
from uct_benchmark.api import (
    satnogsGetObservations,
    satnogsGetTransmitters,
    satnogsGetStations,
)

# Get RF observations for a satellite
obs = satnogsGetObservations(
    norad_id=25544,
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 1, 7),
    status="good"
)

# Get transmitter information
tx = satnogsGetTransmitters(norad_id=25544)

# Get ground station list
stations = satnogsGetStations(status="Online")
```

### GCAT Functions

```python
from uct_benchmark.api import (
    gcatGetSatelliteCatalog,
    gcatLookupByNorad,
    gcatGetLaunches,
)

# Get full satellite catalog (57,000+ objects)
catalog = gcatGetSatelliteCatalog()

# Look up single satellite
sat = gcatLookupByNorad(25544)

# Get launch catalog
launches = gcatGetLaunches()
```

### UCS Functions

```python
from uct_benchmark.api import (
    ucsQuery,
    ucsLookupByNorad,
    ucsGetByCountry,
    ucsGetByPurpose,
)

# Get full database (7,500+ operational satellites)
ucs = ucsQuery()

# Look up satellite
sat = ucsLookupByNorad(25544)

# Filter by country
us_sats = ucsGetByCountry("USA")

# Filter by purpose
comms = ucsGetByPurpose("Communications")
```

### ILRS Functions

```python
from uct_benchmark.api import (
    ilrsGetSatellites,
    ilrsGetStations,
)

# Get ILRS-tracked satellites
ilrs = ilrsGetSatellites()  # ~100 satellites

# Get laser ranging stations
stations = ilrsGetStations()  # ~40 stations
```

---

## Data Ingestion

### Satellite Metadata Ingestion

```python
from uct_benchmark.database.ingestion import DataIngestionPipeline

pipeline = DataIngestionPipeline(db)

# Enrich satellites with open source metadata
report = pipeline.ingest_satellite_metadata(
    sat_nos=[25544, 43013, 8820],
    force_refresh=False
)
print(report)
```

### RF Observation Ingestion

```python
# Fetch SatNOGS RF observations
report = pipeline.ingest_rf_observations(
    sat_nos=[25544],
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 1, 7)
)
```

### ILRS Validation Data

```python
# Ingest ILRS satellite tracking info
report = pipeline.ingest_validation_data()
```

---

## Validation Metrics

### ILRS Validation

```python
from uct_benchmark.evaluation import (
    validate_against_ilrs,
    get_validation_summary,
    get_ilrs_coverage_for_dataset,
)

# Check ILRS coverage for a dataset
coverage = get_ilrs_coverage_for_dataset(dataset_id, db)
print(f"ILRS satellites: {coverage['ilrs_tracked_count']}")
print(f"Validation eligible: {coverage['validation_eligible']}")

# Validate algorithm output against ILRS
results = validate_against_ilrs(
    algorithm_states=predicted_states,
    ilrs_satellites=[8820, 22195],  # LAGEOS-1/2
    db=db
)

# Generate summary report
summary = get_validation_summary("MyAlgorithm", dataset_id, results)
print(summary)
```

---

## Configuration

### OpenSourceConfig

```python
from uct_benchmark.settings import OpenSourceConfig

config = OpenSourceConfig(
    enable_enrichment=True,
    hamr_amr_threshold=0.1,  # m²/kg
    sensor_modes=['EO', 'RF', 'MX'],
    default_sensor_mode='EO',
    enable_satnogs=True,
    enable_ilrs_validation=True,
)
```

### Dataset Generation with Open Source Integration

```python
# Enable enrichment and MX mode in dataset config
config = {
    "satellites": [25544, 43013],
    "timeframe": 7,
    "open_source": {
        "enable_enrichment": True,
        "sensor_mode": "MX"  # Multi-phenomenology
    }
}
```

---

## Database Schema

### New Tables

#### `data_sources`
Tracks data provenance for all records.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| source_name | VARCHAR(50) | SATNOGS, GCAT, UCS, ILRS |
| source_type | VARCHAR(30) | CATALOG, OBSERVATION, VALIDATION |
| license | VARCHAR(50) | CC-BY-SA, CC-BY, etc. |
| last_sync | TIMESTAMP | Last synchronization time |
| record_count | INTEGER | Number of records |

#### `validation_measurements`
Stores ILRS laser ranging measurements.

| Column | Type | Description |
|--------|------|-------------|
| sat_no | INTEGER | NORAD catalog number |
| epoch | TIMESTAMP | Measurement time |
| range_m | DECIMAL(15,6) | Range in meters |
| station_code | VARCHAR(10) | ILRS station code |

### Extended Columns

#### `satellites` (new columns)
- `purpose` - Mission purpose (Communications, Earth Observation, etc.)
- `operator` - Owner/operator organization
- `launch_site` - Launch facility
- `amr_m2_kg` - Area-to-mass ratio
- `ucs_synced_at` - Last UCS sync timestamp
- `gcat_synced_at` - Last GCAT sync timestamp

#### `observations` (new columns)
- `source_id` - References data_sources(id)
- `observation_type` - EO, RF, RADAR

---

## Best Practices

### Rate Limiting

Open source APIs should be queried respectfully:

```python
# SatNOGS: < 1 request/second recommended
# GCAT/UCS: Downloaded as files, cache for 24 hours
```

The module implements automatic caching with 24-hour TTL.

### Error Handling

All API functions return empty DataFrames on failure:

```python
result = satnogsGetObservations(norad_id=25544)
if result.empty:
    print("No data available or API error")
```

### Batch Operations

For large satellite lists, use batch methods:

```python
# More efficient than individual calls
report = dsm.enrich_satellites_batch(satellite_list)
```

---

## Attribution

When using data from open sources, please cite:

- **GCAT**: "data from GCAT (J. McDowell, planet4589.org/space/gcat)"
- **UCS**: "Union of Concerned Scientists Satellite Database"
- **SatNOGS**: "SatNOGS Network, CC-BY-SA"
- **ILRS**: "International Laser Ranging Service"
