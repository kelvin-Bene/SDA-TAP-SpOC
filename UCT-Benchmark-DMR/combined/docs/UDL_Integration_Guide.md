# UDL Write Integration Guide

## SDA TAP SpOC UCT Benchmark - Pushing Datasets to the Unified Data Library

**Status**: Ready for mentor review
**Module**: `uct_benchmark.api.udl_publisher`
**Default mode**: Dry-run (validates payloads without API calls)

---

## 1. Overview

### What is the UDL?

The Unified Data Library (UDL) is the U.S. Space Force's cloud-based data repository operated by Space Systems Command (SSC) and built by Bluestaq LLC. It aggregates space situational awareness (SSA) data from 25+ countries, 3,500+ users, and 300+ data types across multiple classification levels.

- **Unclassified**: `https://unifieddatalibrary.com`
- **Secret**: `.af.smil.mil`
- **Top Secret**: `.af.ic.gov`

### Current State

Our project **reads** from the UDL via REST API GET queries (`apiIntegration.py`). We query:

| Service | What We Pull |
|---------|-------------|
| `eoobservation` | Electro-optical observations (RA/Dec) |
| `radarobservation` | Radar observations (range/range rate) |
| `rfobservation` | RF observations |
| `statevector` | Position/velocity state vectors |
| `elset` | TLE element sets |
| `elset/history` | Historical TLE data |
| `conjunction` | CDM conjunction data |
| `maneuver` | Maneuver detection data |

### What We Want to Add

Push benchmark datasets (observations, state vectors, element sets) back to UDL so that:
1. Challenge datasets are available to the wider SSA community via UDL
2. Algorithm evaluation results can be centralized
3. Simulated data (T3/T4 tiers) follows the ObsSIM precedent for publishing synthetic data to UDL

---

## 2. UDL API Architecture for Write Operations

### 2.1 Authentication

Same as our existing read operations:
```
Authorization: Basic <base64(username:password)>
```

Generated via `UDLTokenGen(username, password)` in `apiIntegration.py`.

### 2.2 Write Endpoints

Every UDL service follows this pattern:

| Method | Endpoint | Purpose | Auth Level |
|--------|----------|---------|------------|
| `POST` | `/udl/{service}/createBulk` | Bulk data upload (initial integration) | Standard user + write role |
| `POST` | `/filedrop/udl-{service}` | Automated data feed (production) | Specific role from UDL team |

**createBulk** returns `204 No Content` on success (synchronous).
**filedrop** returns `202 Accepted` (asynchronous processing).

### 2.3 Required Fields for ALL Records

Every record pushed to UDL **must** include:

```json
{
  "classificationMarking": "U",
  "source": "SDA-TAP-SpOC-UCT-Benchmark",
  "dataMode": "TEST"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `classificationMarking` | string (1-128) | IC/CAPCO portion marking. `"U"` for Unclassified |
| `source` | string (1-36) | Registered data source identifier |
| `dataMode` | enum | `REAL`, `TEST`, `SIMULATED`, or `EXERCISE` |

**Auto-populated by UDL** (do not include in POST):
- `id` - UUID
- `createdAt` - Timestamp
- `createdBy` - Auth user
- `sourceDL` - Source data library
- `origNetwork` - Originating network

### 2.4 dataMode Mapping for Benchmark Tiers

| Tier | Description | dataMode | Rationale |
|------|------------|----------|-----------|
| T1 (T1H, T1S) | Real data, downsampled (high quality) | `TEST` | Test datasets derived from real data |
| T2 (T2H, T2S) | Real data, downsampled (standard quality) | `TEST` | Test datasets derived from real data |
| T3 (T3L) | Real + simulated blend | `EXERCISE` | Mix of real and synthetic data |
| T4 (T4L) | Fully synthetic | `SIMULATED` | Entirely model-generated data |
| T5 | Fully synthetic (edge cases) | `SIMULATED` | Entirely model-generated data |

### 2.5 Error Responses

| Status | Meaning |
|--------|---------|
| 204 | Success (createBulk) |
| 202 | Accepted (filedrop, async) |
| 400 | Bad request - invalid payload schema |
| 401 | Unauthorized - invalid/missing credentials |
| 403 | Forbidden - user not authorized for write |
| 415 | Unsupported media type |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## 3. Data Mapping: Internal Format to UDL Schema

### 3.1 Observations (eoobservation)

| Internal Field | UDL Field | Type | Notes |
|---------------|-----------|------|-------|
| `ob_time` | `obTime` | datetime | ISO 8601 with microseconds |
| `ra` | `ra` | double | Right ascension (degrees) |
| `declination` | `declination` | double | Declination (degrees) |
| `sat_no` / `orig_object_id` | `satNo` | integer | NORAD catalog number |
| `sensor_name` | `sensorName` | string | Sensor identifier |
| `range_km` | `range` | double | Distance (km) |
| `range_rate_km_s` | `rangeRate` | double | Doppler (km/s) |
| `azimuth` | `azimuth` | double | Compass bearing (degrees) |
| `elevation` | `elevation` | double | Angle above horizon (degrees) |
| _(auto)_ | `classificationMarking` | string | `"U"` |
| _(auto)_ | `source` | string | `"SDA-TAP-SpOC-UCT-Benchmark"` |
| _(auto)_ | `dataMode` | enum | From tier mapping |
| _(auto)_ | `origin` | string | Provenance identifier |

### 3.2 State Vectors (statevector)

| Internal Field | UDL Field | Type | Notes |
|---------------|-----------|------|-------|
| `epoch` | `epoch` | datetime | ISO 8601 |
| `sat_no` | `satNo` | integer | NORAD catalog number |
| `position_km[0]` | `xPosition` | double | ECI J2000 X (km) |
| `position_km[1]` | `yPosition` | double | ECI J2000 Y (km) |
| `position_km[2]` | `zPosition` | double | ECI J2000 Z (km) |
| `velocity_km_s[0]` | `xVelocity` | double | ECI J2000 Vx (km/s) |
| `velocity_km_s[1]` | `yVelocity` | double | ECI J2000 Vy (km/s) |
| `velocity_km_s[2]` | `zVelocity` | double | ECI J2000 Vz (km/s) |
| `covariance` | `covariance` | JSON | 6x6 covariance matrix |

### 3.3 Element Sets (elset)

| Internal Field | UDL Field | Type | Notes |
|---------------|-----------|------|-------|
| `epoch` | `epoch` | datetime | ISO 8601 |
| `sat_no` | `satNo` | integer | NORAD catalog number |
| `line1` | `line1` | string | TLE line 1 (70 chars) |
| `line2` | `line2` | string | TLE line 2 (70 chars) |

---

## 4. Publisher Module Usage

### 4.1 Basic Usage (Dry Run)

```python
from uct_benchmark.api import UDLPublisher

# Create publisher in dry-run mode (default)
publisher = UDLPublisher()

# Validate a dataset without pushing
report = publisher.dry_run("path/to/dataset.json")
print(report.summary)

# Check sample payloads that would be sent
for service, samples in report.sample_payloads.items():
    print(f"\n--- {service} sample ---")
    print(json.dumps(samples[0], indent=2))
```

### 4.2 Publishing a Full Dataset

```python
from uct_benchmark.api import UDLPublisher, UDLTokenGen

# Generate auth token
token = UDLTokenGen("your_username", "your_password")

# Create publisher for live push
publisher = UDLPublisher(token=token, dry_run=False)

# Publish entire dataset (observations + state vectors + element sets)
results = publisher.publish_dataset("path/to/dataset.json")

for service, result in results.items():
    print(f"{service}: {result}")

# Get session summary
print(publisher.get_publish_summary())
```

### 4.3 Publishing Individual Record Types

```python
# Publish just observations
result = publisher.publish_observations(
    observations=obs_list,
    data_mode="SIMULATED",  # Override for T4 data
)

# Publish state vectors
result = publisher.publish_state_vectors(state_vectors=sv_list)

# Publish element sets
result = publisher.publish_element_sets(element_sets=elset_list)
```

### 4.4 Integration with Export Pipeline

```python
from uct_benchmark.database import export_dataset_to_json, DatabaseManager

db = DatabaseManager()
db.initialize()

# Export and optionally publish
path = export_dataset_to_json(
    db, dataset_id=42, publish_to_udl=True, udl_token="your_token"
)
```

---

## 5. Onboarding Checklist

Steps required to get write access to UDL:

- [ ] **1. Create UDL Account** - Register at `https://unifieddatalibrary.com/storefront`
- [ ] **2. Submit Data Onboarding Form** - Log in, click person icon (bottom-left), click "Contribute Data to the UDL"
- [ ] **3. Define Source Name** - Propose `"SDA-TAP-SpOC-UCT-Benchmark"` (or `"SDA-TAP-SpOC"` for broader project use)
- [ ] **4. Document Data Format** - This guide serves as the format documentation
- [ ] **5. Classification Review** - Confirm benchmark datasets with downsampled real data are appropriate for unclassified UDL
- [ ] **6. Receive Write Permissions** - UDL team grants API write role after assessment
- [ ] **7. Test with createBulk** - Use `/udl/{service}/createBulk` for initial integration testing
- [ ] **8. Validate Round-Trip** - POST a record, then GET it back to verify data integrity
- [ ] **9. (Optional) Request Filedrop Role** - For automated feed via `/filedrop/udl-{service}` (production)
- [ ] **10. Activate Publisher** - Set `dry_run=False` in UDLPublisher or `publish_to_udl=True` in export pipeline

### Mentor Decision Points

| Question | Options | Recommendation |
|----------|---------|----------------|
| Source name to register? | `SDA-TAP-SpOC-UCT-Benchmark` or `SDA-TAP-SpOC` | Project-specific name for clear provenance |
| Publish as new service type or into existing services? | New service vs existing eoobservation/statevector/elset | Existing services (standard, no UDL team coordination needed) |
| T1/T2 real-data datasets: dataMode? | `TEST` or `REAL` | `TEST` (they are test datasets derived from real data) |
| T3 blended datasets: dataMode? | `EXERCISE` or `TEST` | `EXERCISE` (contains mix of real + simulated) |
| Classification level needed? | Unclass only vs SIPR/JWICS | Start with Unclass; escalate if mentor identifies CUI content |

---

## 6. License Compatibility Analysis

### Data Sources and Their Licenses

| Source | License | Can Push to UDL? | Notes |
|--------|---------|-------------------|-------|
| **UDL** | Restricted (US Gov) | N/A | Already in UDL |
| **Space-Track** | US Gov restricted | No (redundant) | Data already flows into UDL from authoritative sources |
| **CelesTrak** | Open | No (redundant) | Derived from Space-Track/18th SDS, already in UDL |
| **ESA DiscoWeb** | ESA restricted | No | ESA license may restrict redistribution to US military systems |
| **SatNOGS** | CC-BY-SA 4.0 | Avoid | Copyleft requires derivative works to use same license; UDL's restricted access creates friction |
| **GCAT** | CC-BY | Use for enrichment | Permissive license, but push derived products not raw data |
| **ILRS** | Public Domain | Yes | No restrictions |
| **UCS Database** | Open/educational | Use for enrichment | Push derived metadata, not raw database |

### What to Push

**Strong candidates:**
1. Benchmark datasets (our core output) - observations processed from UDL + enrichment
2. Algorithm evaluation results and scoring metrics
3. Derived products with tier classifications
4. Simulated observations (T3/T4) - ObsSIM precedent exists for publishing synthetic data to UDL

**Avoid pushing:**
1. Raw SatNOGS data (CC-BY-SA copyleft conflict)
2. Raw DiscoWeb physical properties (ESA license)
3. Raw CelesTrak/Space-Track data (redundant, already in UDL from authoritative sources)

### Provenance Tagging

The `origin` field in each UDL record tracks data provenance. Our records use:
- `source`: `"SDA-TAP-SpOC-UCT-Benchmark"` (who is providing the data)
- `origin`: Same as source (we are the originating system)
- `dataMode`: Indicates whether data is real, test, simulated, or exercise

---

## 7. Architecture Diagram

```
  EXISTING READ PIPELINE                    NEW WRITE PIPELINE
  ========================                  =======================

  UDL API (GET)                             udl_publisher.py
    + Space-Track                             UDLPublisher class
    + CelesTrak                                 |
    + Open Sources (enrichment)                 |-- validate_payload()
        |                                       |-- dry_run()
        v                                       |-- publish_dataset()
  apiIntegration.py                             |-- publish_observations()
  (UDLQuery, smart_query,                       |-- publish_state_vectors()
   asyncUDLBatchQuery)                          |-- publish_element_sets()
        |                                       |
        v                                       | POST /udl/{service}/createBulk
  Database Layer                                | POST /filedrop/udl-{service}
  (DuckDB / PostgreSQL)                         |
        |                                       v
        v                                   UDL API (WRITE)
  export.py                                 (when write access granted)
  (export_dataset_to_json)
        |
        +-- publish_to_udl=True ----------> UDLPublisher.publish_dataset()
        |
        v
  Dataset JSON / Parquet
```

---

## 8. Security Considerations

1. **Classification**: All records are marked `classificationMarking: "U"` (Unclassified). If any benchmark data is determined to be CUI or higher, the classification marking must be updated and the appropriate UDL instance (SIPR/JWICS) must be used.

2. **Authentication**: UDL uses Basic Auth with Base64-encoded credentials. The existing `UDLTokenGen()` function handles this. Credentials should not be stored in source code - use environment variables (`UDL_USERNAME`, `UDL_PASSWORD`).

3. **Data Sensitivity**: Downsampled real observation data (T1/T2) may have sensitivity considerations. The `dataMode: "TEST"` marking indicates these are test datasets, not operational data. Mentor review is recommended before publishing real-data-derived tiers.

4. **Rate Limiting**: The publisher implements rate limiting (default 100ms between requests) and exponential backoff on 429/500 responses to avoid overloading UDL infrastructure.

5. **Dry-Run Default**: The publisher defaults to `dry_run=True`. Live publishing requires explicit opt-in and a valid auth token.

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Write access requires onboarding approval | Blocks live testing | Dry-run mode works without write access; mentor initiates onboarding |
| API Gateway migration (target Oct 2025) | Endpoint URLs may change | Module uses configurable `base_url`; update when new gateway is available |
| Classification concerns with real data | Cannot push T1/T2 to unclass UDL | Mentor reviews; start with T4 (fully synthetic) which has no sensitivity |
| OpenAPI spec only covers AIS service | Field names may differ for space services | Built from existing GET response field names; validate with `/queryhelp` endpoints after access is granted |
| UDL Python SDK is alpha (0.1.0a34) | Too immature for production | Using direct REST API calls instead of SDK |

---

## 10. Verification Plan

1. **Dry-run validation**: Generate a benchmark dataset, run `publisher.dry_run()`, verify payloads match UDL schema
2. **Schema validation**: Compare publisher output fields against `/udl/{service}/queryhelp` response (requires UDL access)
3. **Read-back test**: After write access is granted, POST a T4 (simulated) record then GET it back to verify round-trip integrity
4. **Batch test**: Publish a small T4 dataset (10-50 records) and verify all records are retrievable
5. **Unit tests**: Validate schema mapping, provenance tagging, and classification marking logic offline

---

## 11. References

- [UDL Storefront / OpenAPI Docs](https://unifieddatalibrary.com/storefront/#/openapi)
- [UDL Python SDK (PyPI)](https://pypi.org/project/udl-sdk/)
- [Space Force UDL Strategic Action Plan (Breaking Defense, Mar 2025)](https://breakingdefense.com/2025/03/space-force-unveils-multi-front-push-to-fix-its-unified-data-library/)
- [Bluestaq $280M UDL Contract (SpaceNews)](https://spacenews.com/bluestaq-wins-280-million-space-force-contract-to-expand-space-data-catalog/)
- [ObsSIM UDL Publishing Precedent (a.i. solutions)](https://ai-solutions.com/obssim/)
- [UDL-Space Fence Direct Sensor Connection (SSC)](https://www.ssc.spaceforce.mil/Newsroom/Article-Display/Article/3011293/ssc-unified-data-library-and-space-fence-establish-direct-sensor-connection)
