# Open Source Data Integration Analysis

## Executive Summary

**Current State**: The `open_sources.py` module provides API wrappers for SatNOGS, GCAT, ILRS, and UCS, but these are **not integrated into the dataset generation pipeline**. The data sources exist but aren't being used to improve datasets.

**Problem**: Users cannot benefit from:
- Higher precision validation (ILRS)
- Richer satellite metadata (UCS, GCAT)
- Additional RF observations (SatNOGS)
- Cross-catalog verification

**Solution**: This document outlines the integration architecture needed to make open source data useful for UCT benchmark dataset generation.

---

## 1. How Open Source Data Improves Dataset Quality

### 1.1 Current Pipeline Limitations

```
Current Flow:
UDL (authenticated) → Database → Dataset Generation → Downsampling → Simulation → Export

Problems:
1. Single source of truth (UDL only)
2. No independent validation
3. Missing satellite metadata (mass, purpose, operator)
4. No RF observation diversity
5. No high-precision ground truth for evaluation
```

### 1.2 How Each Source Improves Quality

| Source | Improvement | Impact on UCT Processing |
|--------|-------------|-------------------------|
| **SatNOGS** | Real RF observation timestamps | Better track gap realism, multi-phenomenology (MX) datasets |
| **GCAT** | 57,000+ objects with launch/reentry history | Better HAMR/debris classification, breakup event labeling |
| **ILRS** | Sub-centimeter range measurements | Ground truth for state vector validation, evaluation accuracy |
| **UCS** | Satellite purpose/operator/mass | Better object selection, HAMR detection, mission classification |

### 1.3 Specific UCT Challenge Improvements

| UCT Challenge | Current Approach | With Open Source Data |
|---------------|------------------|----------------------|
| **HAMR Objects** | Hardcoded threshold (AMR > 1.0) | UCS mass + GCAT area → accurate AMR calculation |
| **Sparse Coverage** | Random downsampling | SatNOGS real coverage patterns for realistic gaps |
| **Multi-Sensor (MX)** | EO only from UDL | Add RF from SatNOGS for true mixed phenomenology |
| **Debris/Small Objects** | Object type flag | GCAT classification + breakup history |
| **Evaluation Accuracy** | Self-referential | ILRS ground truth for validation |

---

## 2. Current Integration Gaps

### 2.1 Pipeline Integration Points

```
                     ┌─────────────────────────────────────────────────────────────┐
                     │                    DATA SOURCES                             │
                     ├─────────────────────────────────────────────────────────────┤
                     │                                                              │
                     │  ┌────────────────┐  ┌────────────────┐                     │
                     │  │  Authenticated │  │  Open Source   │                     │
                     │  │  (UDL, Space-  │  │  (SatNOGS,     │                     │
                     │  │   Track)       │  │   GCAT, ILRS,  │                     │
                     │  │                │  │   UCS)         │                     │
                     │  │  ✓ INTEGRATED  │  │  ✗ NOT         │                     │
                     │  │                │  │    INTEGRATED  │                     │
                     │  └────────┬───────┘  └────────┬───────┘                     │
                     │           │                   │                              │
                     │           │         ┌─────────┴─────────┐                   │
                     │           │         │                   │                   │
                     │           │         │  MISSING:         │                   │
                     │           │         │  1. Ingestion     │                   │
                     │           │         │  2. Enrichment    │                   │
                     │           │         │  3. Selection     │                   │
                     │           │         │  4. Validation    │                   │
                     │           │         │                   │                   │
                     │           │         └───────────────────┘                   │
                     └───────────┴─────────────────────────────────────────────────┘
```

### 2.2 What's Missing

#### A. Data Ingestion from Open Sources

**File**: `database/ingestion.py`
**Gap**: Only supports UDL ingestion, no methods for:
- `ingest_from_satnogs()`
- `ingest_from_gcat()`
- `ingest_from_ucs()`

#### B. Satellite Metadata Enrichment

**File**: `database/schema.py` - `satellites` table
**Gap**: Has columns for mass, cross_section, but no population from open sources:
```python
# MISSING: Enrichment function
def enrich_satellite_metadata(sat_no: int) -> Dict:
    """Combine UCS + GCAT data to populate satellite table."""
    ucs_data = ucsLookupByNorad(sat_no)
    gcat_data = gcatLookupByNorad(sat_no)
    # Return enriched metadata
```

#### C. Data Source Selection Logic

**File**: `backend_api/jobs/workers.py` - `run_dataset_generation()`
**Gap**: No logic to select optimal data source based on:
- Satellite type (HAMR → needs UCS mass)
- Sensor type (RF → use SatNOGS)
- Precision requirements (high precision → use ILRS)

#### D. Validation Pipeline

**File**: `uct_benchmark/evaluation/`
**Gap**: No independent validation using ILRS ground truth

---

## 3. Required Changes

### 3.1 Database Schema Extensions

```sql
-- New table for tracking data provenance
CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name VARCHAR NOT NULL,        -- 'UDL', 'SATNOGS', 'GCAT', 'ILRS', 'UCS'
    source_type VARCHAR,                  -- 'observation', 'catalog', 'validation'
    source_url VARCHAR,
    last_sync TIMESTAMP,
    record_count INTEGER,
    license VARCHAR                       -- 'CC-BY-SA', 'CC-BY', 'Public Domain', etc.
);

-- Extend observations with source tracking
ALTER TABLE observations ADD COLUMN source_id INTEGER REFERENCES data_sources(id);
ALTER TABLE observations ADD COLUMN observation_type VARCHAR;  -- 'EO', 'RADAR', 'RF'

-- New table for ILRS validation data
CREATE TABLE IF NOT EXISTS validation_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sat_no INTEGER NOT NULL,
    epoch TIMESTAMP NOT NULL,
    range_m REAL,                         -- Range in meters (mm precision)
    range_rms_m REAL,                     -- Range RMS residual
    station_code VARCHAR,                 -- ILRS station code
    source VARCHAR DEFAULT 'ILRS',
    UNIQUE(sat_no, epoch, station_code)
);

-- Satellite enrichment tracking
ALTER TABLE satellites ADD COLUMN ucs_synced TIMESTAMP;
ALTER TABLE satellites ADD COLUMN gcat_synced TIMESTAMP;
ALTER TABLE satellites ADD COLUMN purpose VARCHAR;             -- From UCS
ALTER TABLE satellites ADD COLUMN operator VARCHAR;            -- From UCS
ALTER TABLE satellites ADD COLUMN launch_site VARCHAR;         -- From GCAT
```

### 3.2 New Integration Module

**File**: `uct_benchmark/api/data_source_manager.py`

```python
"""
Data Source Manager - Unified interface for all data sources.

Provides intelligent source selection based on:
- Data requirements (precision, coverage, sensor type)
- Availability (some sources may be offline)
- License compatibility
- Freshness (when was data last updated)
"""

class DataSourceManager:
    """Manages multi-source data acquisition and enrichment."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.sources = {
            'udl': UDLSource(),          # Existing
            'spacetrack': SpaceTrackSource(),  # Existing
            'celestrak': CelestrakSource(),    # Existing
            'satnogs': SatNOGSSource(),        # NEW
            'gcat': GCATSource(),              # NEW
            'ilrs': ILRSSource(),              # NEW
            'ucs': UCSSource(),                # NEW
        }

    def get_best_source_for_satellite(
        self,
        sat_no: int,
        data_type: str,  # 'observations', 'catalog', 'validation'
        sensor_preference: str = None,  # 'EO', 'RADAR', 'RF', 'ANY'
        precision_required: str = 'standard'  # 'standard', 'high'
    ) -> str:
        """
        Determine the best data source for a given satellite and requirement.

        Decision logic:
        1. If high precision validation needed → ILRS (if satellite tracked)
        2. If RF observations needed → SatNOGS
        3. If catalog enrichment needed → UCS + GCAT
        4. Default → UDL (most comprehensive)
        """
        pass

    def enrich_satellite(self, sat_no: int) -> Dict:
        """
        Enrich satellite metadata from all available sources.

        Combines:
        - UCS: mass, power, purpose, operator, lifetime
        - GCAT: launch site, decay date, object classification
        - SatNOGS: active transmitters, frequencies

        Returns enriched metadata dict and updates database.
        """
        pass

    def get_validation_data(
        self,
        sat_no: int,
        time_window: Tuple[datetime, datetime]
    ) -> pd.DataFrame:
        """
        Get high-precision validation data from ILRS.

        Used post-generation to validate state vector accuracy.
        """
        pass

    def get_rf_observations(
        self,
        sat_no: int,
        time_window: Tuple[datetime, datetime]
    ) -> pd.DataFrame:
        """
        Get RF observations from SatNOGS.

        Used for mixed-phenomenology (MX) datasets.
        """
        pass
```

### 3.3 Ingestion Pipeline Extensions

**File**: `uct_benchmark/database/ingestion.py`

```python
# Add these methods to DataIngestionPipeline class:

def ingest_from_satnogs(
    self,
    sat_ids: List[int],
    time_window: Tuple[datetime, datetime],
    observation_types: List[str] = ['frames'],
    progress_callback: Optional[Callable] = None,
) -> IngestionReport:
    """
    Ingest RF observation data from SatNOGS.

    Note: SatNOGS data is RF signal detection, not positional.
    Used for: multi-phenomenology datasets, observation timing validation
    """
    from uct_benchmark.api.open_sources import satnogsGetObservations

    report = IngestionReport()

    for sat_id in sat_ids:
        try:
            obs_df = satnogsGetObservations(
                norad_id=sat_id,
                start_time=time_window[0],
                end_time=time_window[1]
            )

            if not obs_df.empty:
                # Transform to observation schema
                obs_df = self._transform_satnogs_to_observations(obs_df)
                obs_df['source'] = 'SATNOGS'
                obs_df['observation_type'] = 'RF'

                sub_report = self.ingest_observations_from_dataframe(
                    obs_df, source='SATNOGS'
                )
                report.inserted_records += sub_report.inserted_records

        except Exception as e:
            report.add_failure(sat_id, str(e))

    report.finalize()
    return report

def ingest_satellite_metadata(
    self,
    sat_ids: Optional[List[int]] = None,
    sources: List[str] = ['ucs', 'gcat'],
) -> IngestionReport:
    """
    Enrich satellite metadata from open sources.

    Pulls from UCS (operational data) and GCAT (catalog data)
    to populate satellite table with mass, purpose, operator, etc.
    """
    from uct_benchmark.api.open_sources import (
        ucsQuery, gcatQuery, ucsLookupByNorad, gcatLookupByNorad
    )

    report = IngestionReport()

    # Get all satellites in database if no list provided
    if sat_ids is None:
        sat_ids = self.db.satellites.get_all_sat_nos()

    for sat_id in sat_ids:
        enriched_data = {}

        if 'ucs' in sources:
            ucs_data = ucsLookupByNorad(sat_id)
            if ucs_data is not None:
                enriched_data.update({
                    'mass_kg': ucs_data.get('Launch Mass (kg.)'),
                    'purpose': ucs_data.get('Purpose'),
                    'operator': ucs_data.get('Operator/Owner'),
                    'power_watts': ucs_data.get('Power (watts)'),
                    'expected_lifetime': ucs_data.get('Expected Lifetime (yrs.)'),
                    'ucs_synced': datetime.now()
                })

        if 'gcat' in sources:
            gcat_data = gcatLookupByNorad(sat_id)
            if gcat_data is not None:
                enriched_data.update({
                    'launch_site': gcat_data.get('Site'),
                    'object_type': gcat_data.get('Type'),
                    'gcat_synced': datetime.now()
                })

        if enriched_data:
            self.db.satellites.update(sat_id, enriched_data)
            report.add_success(sat_id, 1)

    report.finalize()
    return report
```

### 3.4 Dataset Generation Integration

**File**: `backend_api/jobs/workers.py`

```python
# Modify run_dataset_generation() to use open sources:

def run_dataset_generation(job_id, dataset_id, config):
    # ... existing code ...

    # NEW: Determine data sources based on config
    data_sources = select_data_sources(config)

    # NEW: Enrich satellite metadata before processing
    if config.get('enrich_metadata', True):
        pipeline.ingest_satellite_metadata(
            sat_ids=selected_sats,
            sources=['ucs', 'gcat']
        )

    # Fetch primary observations (existing)
    fetch_observations(token, selected_sats, time_window)

    # NEW: Add RF observations if multi-phenomenology requested
    if config.get('sensors') == 'MX' or 'rf' in config.get('sensors', []):
        pipeline.ingest_from_satnogs(selected_sats, time_window)

    # ... downsampling, simulation, export ...

    # NEW: Add validation data if high-precision tier
    if config.get('tier') in ['T1H', 'validation']:
        validation_data = get_ilrs_validation(selected_sats, time_window)
        dataset.add_validation_reference(validation_data)


def select_data_sources(config: Dict) -> List[str]:
    """
    Select optimal data sources based on dataset configuration.

    Logic:
    - If 'HAMR' object type → require UCS (for mass)
    - If 'RF' or 'MX' sensor → include SatNOGS
    - If 'T1H' or 'validation' tier → include ILRS
    - Always include UDL for primary observations
    """
    sources = ['udl']  # Primary source always included

    if config.get('object_types') and 'HAMR' in config['object_types']:
        sources.append('ucs')  # Need mass for AMR calculation

    if config.get('sensors') in ['RF', 'MX']:
        sources.append('satnogs')

    if config.get('tier') in ['T1H', 'validation']:
        sources.append('ilrs')

    # Always enrich with GCAT for catalog info
    sources.append('gcat')

    return sources
```

### 3.5 Improved HAMR Detection

**File**: `uct_benchmark/data/dataManipulation.py` or new file

```python
def calculate_accurate_amr(sat_no: int, db: DatabaseManager) -> float:
    """
    Calculate accurate Area-to-Mass Ratio using enriched satellite data.

    Current approach: Hardcoded threshold (AMR > 1.0)
    Improved approach: Use actual mass from UCS and area from DiscoWeb/GCAT

    Returns:
        AMR in m²/kg, or None if insufficient data
    """
    sat_data = db.satellites.get(sat_no)

    mass_kg = sat_data.get('mass_kg')
    area_m2 = sat_data.get('cross_section_m2')

    if mass_kg and area_m2 and mass_kg > 0:
        return area_m2 / mass_kg

    # Fallback: estimate from orbital behavior
    return estimate_amr_from_decay(sat_no)
```

---

## 4. Integration Priority

### Phase 1: Metadata Enrichment (HIGH VALUE, LOW EFFORT)

1. Add `ingest_satellite_metadata()` to ingestion pipeline
2. Call during dataset generation to populate mass/purpose
3. Use for accurate HAMR detection

**Impact**: Better object classification, accurate AMR calculation
**Effort**: ~1 day

### Phase 2: SatNOGS RF Observations (MEDIUM VALUE, MEDIUM EFFORT)

1. Add `ingest_from_satnogs()` to ingestion pipeline
2. Create observation type field ('EO', 'RADAR', 'RF')
3. Enable MX (mixed) datasets

**Impact**: True multi-phenomenology datasets
**Effort**: ~2 days

### Phase 3: ILRS Validation (HIGH VALUE, MEDIUM EFFORT)

1. Add validation_measurements table
2. Create post-generation validation function
3. Report precision metrics against ground truth

**Impact**: Trustworthy evaluation metrics
**Effort**: ~3 days

### Phase 4: Intelligent Source Selection (MEDIUM VALUE, HIGH EFFORT)

1. Build DataSourceManager class
2. Implement source selection logic
3. Add to dataset configuration UI

**Impact**: Optimal data for each use case
**Effort**: ~1 week

---

## 5. Testing Requirements

### Unit Tests for Open Sources

```python
# tests/test_open_sources.py

def test_satnogs_query():
    """Test SatNOGS API returns valid data structure."""
    df = satnogsGetSatellites()
    assert not df.empty
    assert 'norad_cat_id' in df.columns or similar

def test_gcat_query():
    """Test GCAT catalog download and parsing."""
    df = gcatQuery('satcat')
    assert len(df) > 50000  # Should have 57k+ objects

def test_ucs_query():
    """Test UCS database download and parsing."""
    df = ucsQuery()
    assert len(df) > 7000  # Should have 7500+ satellites

def test_enrich_satellite():
    """Test multi-source satellite enrichment."""
    data = enrichSatelliteData(25544)  # ISS
    assert 'ucs' in data or 'gcat' in data
```

### Integration Tests

```python
# tests/test_open_source_integration.py

def test_metadata_ingestion():
    """Test satellite metadata enrichment updates database."""
    db = DatabaseManager(':memory:')
    pipeline = DataIngestionPipeline(db)

    # Add satellite
    db.satellites.insert({'sat_no': 25544, 'name': 'ISS'})

    # Enrich
    report = pipeline.ingest_satellite_metadata([25544])

    # Verify
    sat = db.satellites.get(25544)
    assert sat['mass_kg'] is not None  # From UCS

def test_hamr_detection_with_ucs():
    """Test HAMR detection uses accurate mass from UCS."""
    # ... setup with enriched data ...
    amr = calculate_accurate_amr(sat_no, db)
    assert amr > 0
```

---

## 6. Summary: What Needs to Happen

| Task | Priority | Effort | Files to Modify |
|------|----------|--------|-----------------|
| Add `ingest_satellite_metadata()` | P0 | 1 day | `ingestion.py` |
| Use enriched data for HAMR detection | P0 | 0.5 day | `dataManipulation.py`, `settings.py` |
| Add SatNOGS observation ingestion | P1 | 2 days | `ingestion.py`, schema |
| Add ILRS validation table & ingestion | P1 | 2 days | `schema.py`, `ingestion.py` |
| Create DataSourceManager | P2 | 1 week | New file |
| Update dataset generation worker | P2 | 2 days | `workers.py` |
| Add tests for all above | P0-P2 | 3 days | `tests/` |

**Total Estimated Effort**: ~2 weeks for full integration

---

## 7. Conclusion

The open source data sources (SatNOGS, GCAT, ILRS, UCS) have significant potential to improve UCT benchmark datasets:

1. **Better Object Classification**: UCS mass + GCAT area → accurate HAMR detection
2. **Multi-Phenomenology**: SatNOGS RF observations enable true mixed-sensor datasets
3. **Validation Ground Truth**: ILRS provides sub-cm accuracy for state vector validation
4. **Richer Metadata**: Purpose, operator, launch site for better dataset filtering

However, **none of this potential is currently realized** because the `open_sources.py` module is not connected to the dataset generation pipeline.

The recommended approach is:
1. Start with metadata enrichment (immediate value, low risk)
2. Add RF observation support (enables new dataset types)
3. Build validation pipeline (improves evaluation trustworthiness)
4. Finally, implement intelligent source selection (full optimization)
