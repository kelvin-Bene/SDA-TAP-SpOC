# Database Architecture

## UCT Benchmark - Data Storage Layer

**Schema Version:** 2.0.0 (PostgreSQL) / 1.1.0 (DuckDB)
**Updated:** April 2026

---

## 1. Overview

This document describes the database and data storage architecture implemented for the UCT Benchmark project. The system uses a dual-backend design: DuckDB for local analytical workloads and PostgreSQL (Supabase) for the production web application.

### 1.1 Design Goals

- **Dual Backend**: DuckDB for local analytics, PostgreSQL/Supabase for production
- **Backward Compatible**: Existing JSON/Parquet workflows unchanged
- **High Performance**: Sub-second queries for interactive use
- **Portable**: Cross-platform (Windows/Linux)
- **Version Control**: Dataset versioning and comparison

### 1.2 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Local DB | DuckDB v1.4.1+ | Already a dependency, analytical focus |
| Production DB | PostgreSQL (Supabase) | Auth, RLS, real-time subscriptions |
| Bulk Storage | Parquet | Columnar, compressed, DuckDB-native |
| Export Format | JSON | API compatibility, human-readable |
| ORM Layer | Custom Repository Pattern | Lightweight, no external dependencies |

---

## 2. Architecture Diagram

```
+-----------------------------------------------------------------+
|                    APPLICATION LAYER                             |
|  (Python: Pandas, Polars, API Integration)                      |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|                    DATA ACCESS LAYER                             |
|  DatabaseManager + Repository Pattern                           |
|                                                                 |
|  +----------------+ +----------------+ +----------------+       |
|  | Satellite      | | Observation    | | StateVector    |       |
|  | Repository     | | Repository     | | Repository     |       |
|  +----------------+ +----------------+ +----------------+       |
|  +----------------+ +----------------+ +----------------+       |
|  | ElementSet     | | Dataset        | | Event          |       |
|  | Repository     | | Repository     | | Repository     |       |
|  +----------------+ +----------------+ +----------------+       |
+-----------------------------------------------------------------+
                              |
          +-------------------+-------------------+
          v                   v                   v
+-------------------+  +-------------------+  +-------------------+
|   DuckDB          |  |   PostgreSQL      |  |   Parquet/JSON    |
|   (Local)         |  |   (Supabase)      |  |   (Export)        |
|                   |  |                   |  |                   |
| - Complex SQL     |  | - Auth/RLS        |  | - Bulk data       |
| - Aggregations    |  | - Multi-user      |  | - Archival        |
| - Local dev       |  | - Production API  |  | - Portability     |
+-------------------+  +-------------------+  +-------------------+
```

---

## 3. Complete Table Inventory

The schema contains **19 core tables** plus **4 optional audit/logging tables** (DuckDB only). Both backends share the same logical schema; differences are noted below.

| # | Table | Purpose | DuckDB | PostgreSQL |
|---|-------|---------|--------|------------|
| 1 | `_schema_metadata` | Schema version tracking | Yes | Yes |
| 2 | `satellites` | NORAD satellite catalog with physical properties | Yes | Yes |
| 3 | `observations` | Raw observation data (optical + radar, 36 columns) | Yes | Yes |
| 4 | `state_vectors` | Cartesian state vectors (J2000 ECI) | Yes | Yes |
| 5 | `element_sets` | Two-Line Element sets (TLEs) | Yes | Yes |
| 6 | `datasets` | Generated benchmark datasets with challenge fields | Yes | Yes |
| 7 | `dataset_observations` | Junction: dataset to observation mapping with CTF split | Yes | Yes |
| 8 | `dataset_references` | Truth data linking datasets to reference state vectors | Yes | Yes |
| 9 | `submissions` | User algorithm submissions for evaluation | Yes | Yes |
| 10 | `submission_results` | Evaluation metrics (binary, state, residual, composite) | Yes | Yes |
| 11 | `jobs` | Async job tracking (generation, evaluation) | Yes | Yes |
| 12 | `event_types` | Lookup table for event categories | Yes | Yes |
| 13 | `events` | Detected orbital events (maneuver, breakup, proximity) | Yes | Yes |
| 14 | `event_observations` | Junction: event to observation mapping | Yes | Yes |
| 15 | `non_reference_observations` | Decoy observations for true-negative scoring | Yes | Yes |
| 16 | `breakup_events` | Cached breakup/fragmentation events from Space-Track | Yes | Yes |
| 17 | `feedback` | User-submitted bug reports and feedback | Yes | Yes |
| 18 | `profiles` | User profiles with encrypted API tokens | Yes | Yes |
| 19 | `credentials` | Encrypted per-user API credentials (UDL, ESA) | Yes | Yes |
| 20 | `audit_log` | Security audit trail (optional) | Yes* | No |
| 21 | `api_call_log` | API request/response logging (optional) | Yes* | No |
| 22 | `credential_access_log` | Credential access audit (optional) | Yes* | No |
| 23 | `system_log` | System-level event log (optional) | Yes* | No |

\* Audit tables use `SERIAL` type and are created on a best-effort basis in DuckDB; creation failures are silently ignored.

**Backend differences:**
- DuckDB uses `TIMESTAMP` and `JSON` types.
- PostgreSQL uses `TIMESTAMPTZ` and `JSONB` types (conversion is automatic).
- PostgreSQL uses `SERIAL` for audit table IDs; DuckDB uses explicit sequences elsewhere.

---

## 4. Entity Relationship Diagram

```
+----------------+       +--------------------+       +----------------+
|  satellites    |       |   observations     |       | state_vectors  |
+----------------+       +--------------------+       +----------------+
| sat_no (PK)   |<------| sat_no (FK)        |       | id (PK)        |
| name           |       | id (PK)            |       | sat_no (FK)    |
| orbital_regime |       | ob_time            |       | epoch          |
| object_type    |       | ra, declination    |       | x/y/z_pos      |
| mass_kg        |       | sensor_id/name     |       | x/y/z_vel      |
| ...            |       | track_id           |       | covariance     |
+----------------+       | is_uct             |       | source         |
       |                 | [20 EO columns]    |       +----------------+
       |                 +--------------------+              |
       |                          |                          |
       |                 +--------+--------+                 |
       |                 v                 v                 |
       |    +--------------------+ +--------------------+   |
       |    | dataset_           | | event_             |   |
       |    |   observations     | |   observations     |   |
       |    +--------------------+ +--------------------+   |
       |    | dataset_id (FK)    | | event_id (FK)      |   |
       |    | observation_id(FK) | | observation_id(FK) |   |
       |    | assigned_track_id  | +--------------------+   |
       |    | split              |          |               |
       |    +--------------------+          |               |
       |               |                   |               |
       |               v                   v               |
       |    +--------------------+ +--------------------+  |
       |    |    datasets        | |     events         |  |
       +----| id (PK)            | | id (PK)            |--+
            | name, code         | | event_type_id (FK) |
            | legacy_code        | | primary_sat_no(FK) |
            | tier, version      | | confidence         |
            | answer_key         | | event_time_start   |
            | sensor_biases      | +--------------------+
            | maneuver_metadata  |          |
            | generation_params  |          v
            +--------------------+ +--------------------+
                     |             | event_types         |
                     v             +--------------------+
            +--------------------+ | id (PK)            |
            | dataset_references | | name               |
            +--------------------+ +--------------------+
            | dataset_id (FK)    |
            | sat_no (FK)        |
            | state_vector_id(FK)|
            | element_set_id(FK) |
            +--------------------+

+--------------------+    +--------------------+    +--------------------+
|  submissions       |    |  profiles          |    |  breakup_events    |
+--------------------+    +--------------------+    +--------------------+
| id (PK)            |    | id (PK)            |    | id (PK)            |
| dataset_id (FK)    |    | email              |    | parent_norad_id    |
| algorithm_name     |    | role               |    | event_date         |
| user_id            |    | display_name       |    | debris_count       |
| status             |    | organization       |    | debris_norad_ids   |
+--------------------+    | udl_token          |    | event_type         |
         |                | esa_token          |    | source             |
         v                +--------------------+    +--------------------+
+--------------------+
| submission_results |    +--------------------+    +--------------------+
+--------------------+    |  feedback          |    | non_reference_     |
| id (PK)            |    +--------------------+    |   observations     |
| submission_id (FK) |    | id (PK)            |    +--------------------+
| f1_score           |    | description        |    | id (PK)            |
| composite_score    |    | severity           |    | dataset_id (FK)    |
| test_composite_    |    | reporter_id        |    | observation_id     |
|   score            |    | status             |    | source_norad_id    |
+--------------------+    +--------------------+    +--------------------+
```

---

## 5. Table Specifications

### 5.1 satellites

Stores the NORAD satellite catalog with physical properties from ESA DiscoWeb.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| sat_no | INTEGER | PRIMARY KEY | NORAD catalog number |
| name | VARCHAR(100) | | Satellite name |
| cospar_id | VARCHAR(20) | | COSPAR international designator |
| object_type | VARCHAR(20) | | PAYLOAD, ROCKET BODY, DEBRIS |
| launch_date | DATE | | Launch date |
| decay_date | DATE | | Decay/reentry date |
| mass_kg | DECIMAL(10,2) | | Mass in kg (ESA DiscoWeb) |
| cross_section_m2 | DECIMAL(10,4) | | Cross-section area in m^2 |
| drag_coeff | DECIMAL(6,4) | DEFAULT 2.5 | Drag coefficient |
| srp_coeff | DECIMAL(6,4) | DEFAULT 1.5 | Solar radiation pressure coefficient |
| orbital_regime | VARCHAR(10) | | LEO, MEO, GEO, HEO |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Row creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

---

### 5.2 observations

Stores raw observation data from UDL and simulated sources. Contains 36 columns covering optical (RA/Dec), radar (range/azimuth/elevation), sensor metadata, and full EO fields per the Benchmarking Documentation spec.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(64) | PRIMARY KEY | UDL observation ID |
| sat_no | INTEGER | FK -> satellites | NORAD catalog number |
| ob_time | TIMESTAMP | NOT NULL | Observation epoch |
| **Optical position** | | | |
| ra | DECIMAL(12,8) | | Right Ascension (degrees) |
| declination | DECIMAL(12,8) | | Declination (degrees) |
| **Radar position** | | | |
| range_km | DECIMAL(12,4) | | Slant range (km) |
| range_rate_km_s | DECIMAL(10,6) | | Range rate (km/s) |
| azimuth | DECIMAL(12,8) | | Azimuth (degrees) |
| elevation | DECIMAL(12,8) | | Elevation (degrees) |
| **Sensor metadata** | | | |
| sensor_id | VARCHAR(64) | | UDL sensor identifier |
| sensor_name | VARCHAR(100) | | Human-readable sensor name |
| data_mode | VARCHAR(20) | | REAL or SIMULATED |
| type_optical | VARCHAR(20) | | Observation type (e.g., optical) |
| **Sensor location** | | | |
| send_lat | DECIMAL(12,8) | | Sensor latitude (degrees) |
| send_long | DECIMAL(12,8) | | Sensor longitude (degrees) |
| send_alt | DECIMAL(12,4) | | Sensor altitude (km) |
| **Track association** | | | |
| track_id | VARCHAR(64) | | Track association ID |
| **UCT flags** | | | |
| is_uct | BOOLEAN | DEFAULT FALSE | Decorrelated (UCT) flag |
| is_simulated | BOOLEAN | DEFAULT FALSE | Simulated observation flag |
| **Metadata** | | | |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Row creation time |
| **Full EO fields** | | | |
| classification_marking | VARCHAR(200) | | Security classification marking |
| id_on_orbit | VARCHAR(64) | | On-orbit object identifier |
| task_id | VARCHAR(64) | | Tasking request identifier |
| orig_object_id | VARCHAR(100) | | Original object ID from source |
| orig_sensor_id | VARCHAR(100) | | Original sensor ID from source |
| sen_x | DECIMAL(16,9) | | Sensor ECEF X position |
| sen_y | DECIMAL(16,9) | | Sensor ECEF Y position |
| sen_z | DECIMAL(16,9) | | Sensor ECEF Z position |
| exp_duration | DECIMAL(10,4) | | Exposure duration (seconds) |
| mag | DECIMAL(10,6) | | Apparent magnitude |
| mag_unc | DECIMAL(10,6) | | Magnitude uncertainty |
| geo_lat | DECIMAL(12,8) | | Sub-satellite geodetic latitude |
| geo_lon | DECIMAL(12,8) | | Sub-satellite geodetic longitude |
| geo_alt | DECIMAL(16,6) | | Geodetic altitude (km) |
| geo_range | DECIMAL(16,6) | | Geodetic range (km) |

**Indexes:** `idx_obs_time(ob_time)`, `idx_obs_sat_time(sat_no, ob_time)`, `idx_obs_track(track_id)`

---

### 5.3 state_vectors

Cartesian state vectors in the J2000 ECI frame.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY (sequence) | Auto-generated ID |
| sat_no | INTEGER | FK -> satellites | NORAD catalog number |
| epoch | TIMESTAMP | NOT NULL | State epoch |
| x_pos | DECIMAL(16,6) | NOT NULL | X position (km, J2000 ECI) |
| y_pos | DECIMAL(16,6) | NOT NULL | Y position (km, J2000 ECI) |
| z_pos | DECIMAL(16,6) | NOT NULL | Z position (km, J2000 ECI) |
| x_vel | DECIMAL(16,9) | NOT NULL | X velocity (km/s, J2000 ECI) |
| y_vel | DECIMAL(16,9) | NOT NULL | Y velocity (km/s, J2000 ECI) |
| z_vel | DECIMAL(16,9) | NOT NULL | Z velocity (km/s, J2000 ECI) |
| covariance | JSON/JSONB | | 6x6 covariance matrix |
| source | VARCHAR(50) | | UDL, SPACE_TRACK, PROPAGATED |
| data_mode | VARCHAR(20) | | REAL or SIMULATED |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Row creation time |

**Constraints:** UNIQUE(sat_no, epoch, source)
**Indexes:** `idx_sv_sat_epoch(sat_no, epoch)`

---

### 5.4 element_sets

Two-Line Element sets (TLEs) with parsed orbital elements.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY (sequence) | Auto-generated ID |
| sat_no | INTEGER | FK -> satellites | NORAD catalog number |
| line1 | VARCHAR(70) | NOT NULL | TLE line 1 |
| line2 | VARCHAR(70) | NOT NULL | TLE line 2 |
| epoch | TIMESTAMP | NOT NULL | TLE epoch |
| inclination | DECIMAL(10,6) | | Inclination (degrees) |
| raan | DECIMAL(10,6) | | Right Ascension of Ascending Node |
| eccentricity | DECIMAL(12,10) | | Eccentricity |
| arg_perigee | DECIMAL(10,6) | | Argument of Perigee |
| mean_anomaly | DECIMAL(10,6) | | Mean Anomaly |
| mean_motion | DECIMAL(14,10) | | Mean Motion (rev/day) |
| b_star | DECIMAL(16,12) | | B* drag term |
| semi_major_axis_km | DECIMAL(12,4) | | Derived semi-major axis (km) |
| period_minutes | DECIMAL(10,4) | | Derived orbital period (minutes) |
| source | VARCHAR(50) | | Data source |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Row creation time |

**Constraints:** UNIQUE(sat_no, epoch)
**Indexes:** `idx_elset_sat_epoch(sat_no, epoch)`

---

### 5.5 datasets

Generated benchmark datasets. This is the most complex table, containing legacy code fields, challenge configuration (sensor biases, maneuver-during-gap), generation provenance, and the evaluation answer key.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY (sequence) | Auto-generated ID |
| name | VARCHAR(100) | NOT NULL, UNIQUE | Human-readable dataset name |
| code | VARCHAR(20) | | Enhanced code, e.g. "HAMR_LEO_MAN_EO_T2S_07D_001" |
| legacy_code | VARCHAR(16) | | Louis's 16-char code, e.g. "H50LEONEOPSSSS07" |
| **Legacy code components** | | | |
| object_type_code | CHAR(1) | | H=HAMR, C=Close, A=Apparent, U=Unspecified, N=Calibration |
| target_percentage | VARCHAR(2) | | 50, 10, 01, UN |
| event_code | VARCHAR(2) | | MB=Maneuver, BU=Breakup, LL=LongThrust, NE=NoEvents |
| sensor_code | VARCHAR(2) | | OP, RA, RF, FU, OR, RO, RR |
| coverage_level | CHAR(1) | | A=All/High, S=Standard, N=None/Low |
| track_gap_level | CHAR(1) | | A, S, N |
| obs_count_level | CHAR(1) | | A, S, N |
| object_count_level | CHAR(1) | | H=80, S=40, L=10 |
| fitspan_days | INTEGER | | 01-14 days |
| **Version tracking** | | | |
| version | INTEGER | DEFAULT 1 | Version number |
| parent_id | INTEGER | | Parent dataset for version lineage |
| **Configuration** | | | |
| tier | VARCHAR(5) | | T1, T2, T3, T4, T5 |
| orbital_regime | VARCHAR(10) | | LEO, MEO, GEO, HEO |
| time_window_start | TIMESTAMP | | Dataset time window start |
| time_window_end | TIMESTAMP | | Dataset time window end |
| **Statistics** | | | |
| observation_count | INTEGER | | Total observations in dataset |
| satellite_count | INTEGER | | Number of satellites in dataset |
| avg_coverage | DECIMAL(8,4) | | Average coverage metric |
| avg_obs_count | DECIMAL(8,2) | | Average observation count per satellite |
| max_track_gap | DECIMAL(8,4) | | Maximum track gap (hours) |
| **Downsampling/simulation** | | | |
| downsampling_applied | BOOLEAN | DEFAULT FALSE | Whether downsampling was applied |
| simulation_applied | BOOLEAN | DEFAULT FALSE | Whether simulation was applied |
| simulated_obs_count | INTEGER | DEFAULT 0 | Count of simulated observations |
| downsampling_config | JSON/JSONB | | Downsampling parameters used |
| simulation_config | JSON/JSONB | | Simulation parameters used |
| **Non-reference tracking** | | | |
| non_ref_observation_count | INTEGER | DEFAULT 0 | Count of non-reference (decoy) observations |
| include_non_ref_obs | BOOLEAN | DEFAULT FALSE | Whether non-ref obs are included |
| **Challenge fields** | | | |
| answer_key | JSON/JSONB | | Maps observation IDs to satellite NORAD IDs (per decorrelation spec) |
| actual_satellite_ids | JSON/JSONB | | Actual NORAD IDs discovered during generation |
| performance_metadata | JSON/JSONB | | Timing, window selection, filtering provenance |
| sensor_biases | JSON/JSONB | | Per-sensor systematic biases for poor-calibration challenge (UCT challenge #10). Format: `{"GEODSS-1": {"ra_arcsec": 1.7, "dec_arcsec": -2.3}}` |
| calibration_quality | VARCHAR(16) | NOT NULL, DEFAULT 'standard' | 'standard' (no bias) or 'poor' (synthetic per-sensor bias) |
| maneuver_during_gap | BOOLEAN | NOT NULL, DEFAULT FALSE | UCT challenge #6: satellites maneuvered during a 6-hour coverage gap |
| maneuver_metadata | JSON/JSONB | | Per-satellite maneuver answer key (delta-V, epoch, pre/post state vectors). NULL when maneuver_during_gap=FALSE |
| **Ownership and status** | | | |
| user_id | VARCHAR(255) | | Supabase user ID |
| generation_params | JSON/JSONB | | Generation parameters blob |
| status | VARCHAR(20) | DEFAULT 'created' | created, processing, complete, failed |
| error_message | TEXT | | User-facing error when status='failed' |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Row creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |
| json_path | VARCHAR(500) | | Export JSON file path |
| parquet_path | VARCHAR(500) | | Export Parquet file path |

**Constraints:** UNIQUE(code, version)
**Indexes:** `idx_datasets_code(code)`, `idx_datasets_legacy_code(legacy_code)`, `idx_datasets_object_type(object_type_code)`, `idx_datasets_regime(orbital_regime)`, `idx_datasets_event(event_code)`, `idx_datasets_sensor(sensor_code)`, `idx_datasets_user_id(user_id)`

---

### 5.6 dataset_observations

Junction table mapping observations to datasets. Each observation gets a decorrelated track/object ID and a CTF train/validation/test split assignment.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| dataset_id | INTEGER | PK (composite), FK -> datasets | Dataset ID |
| observation_id | VARCHAR(64) | PK (composite), FK -> observations | Observation ID |
| assigned_track_id | INTEGER | | Decorrelated track ID |
| assigned_object_id | INTEGER | | Decorrelated object ID |
| split | VARCHAR(16) | NOT NULL, DEFAULT 'train' | CTF split: 'train', 'validation', or 'test' |

**Indexes:** `idx_ds_obs_dataset(dataset_id)`, `idx_ds_obs_observation(observation_id)`, `idx_ds_obs_split(dataset_id, split)`

---

### 5.7 dataset_references

Truth data linking datasets to reference state vectors and element sets for evaluation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| dataset_id | INTEGER | PK (composite), FK -> datasets | Dataset ID |
| sat_no | INTEGER | PK (composite), FK -> satellites | NORAD catalog number |
| state_vector_id | INTEGER | FK -> state_vectors | Reference state vector |
| element_set_id | INTEGER | FK -> element_sets | Reference element set |
| grouped_obs_ids | JSON/JSONB | | Observation IDs grouped by satellite |

---

### 5.8 submissions

User algorithm submissions for evaluation against a dataset.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY (sequence) | Auto-generated ID |
| dataset_id | INTEGER | FK -> datasets | Target dataset |
| algorithm_name | VARCHAR(100) | NOT NULL | Algorithm/tool name |
| version | VARCHAR(50) | DEFAULT '1.0' | Algorithm version |
| description | TEXT | | Free-text description |
| file_path | VARCHAR(500) | | Uploaded file path |
| classification_marking | VARCHAR(200) | | Organization label (per Louis's spec) |
| status | VARCHAR(20) | DEFAULT 'queued' | queued, validating, processing, completed, failed |
| job_id | VARCHAR(100) | FK -> jobs | Async job reference |
| error_message | TEXT | | Error details on failure |
| user_id | VARCHAR(255) | | Supabase user ID |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Submission time |
| completed_at | TIMESTAMP | | Evaluation completion time |

**Indexes:** `idx_submissions_dataset(dataset_id)`, `idx_submissions_status(status)`, `idx_submissions_user(user_id)`

---

### 5.9 submission_results

Evaluation metrics for each submission, including binary classification, state estimation, and per-split composite scores.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY (sequence) | Auto-generated ID |
| submission_id | INTEGER | UNIQUE, FK -> submissions | One result per submission |
| **Binary classification metrics** | | | |
| true_positives | INTEGER | DEFAULT 0 | Correctly matched observations |
| true_negatives | INTEGER | DEFAULT 0 | Non-ref obs correctly NOT matched |
| false_positives | INTEGER | DEFAULT 0 | Incorrectly matched observations |
| false_negatives | INTEGER | DEFAULT 0 | Missed observations |
| precision | DECIMAL(10,6) | DEFAULT 0 | TP/(TP+FP) |
| recall | DECIMAL(10,6) | DEFAULT 0 | TP/(TP+FN) |
| f1_score | DECIMAL(10,6) | DEFAULT 0 | Harmonic mean of precision and recall |
| specificity | DECIMAL(10,6) | DEFAULT 0 | TN/(TN+FP) |
| accuracy | DECIMAL(10,6) | DEFAULT 0 | (TP+TN)/(TP+TN+FP+FN) |
| **State estimation metrics** | | | |
| position_rms_km | DECIMAL(12,6) | | Position RMS error (km) |
| velocity_rms_km_s | DECIMAL(12,9) | | Velocity RMS error (km/s) |
| mahalanobis_distance | DECIMAL(12,6) | | Statistical distance measure |
| **Residual metrics** | | | |
| ra_residual_rms_arcsec | DECIMAL(12,6) | | RA residual RMS (arcseconds) |
| dec_residual_rms_arcsec | DECIMAL(12,6) | | Dec residual RMS (arcseconds) |
| **Composite scores** | | | |
| raw_results | JSON/JSONB | | Full breakdown blob |
| composite_score | DECIMAL(10,6) | | Legacy: all-splits composite (backward compat) |
| train_composite_score | DECIMAL(10,6) | | Train split composite score |
| val_composite_score | DECIMAL(10,6) | | Validation split composite score |
| test_composite_score | DECIMAL(10,6) | | Test split composite (leaderboard ranking) |
| **Processing** | | | |
| processing_time_seconds | DECIMAL(12,3) | | Evaluation wall-clock time |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Result creation time |

**Indexes:** `idx_results_submission(submission_id)`, `idx_results_f1(f1_score DESC)`, `idx_results_test_composite(test_composite_score DESC)`

---

### 5.10 events

Detected orbital events linked to satellites and optionally to datasets.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY (sequence) | Auto-generated ID |
| event_type_id | INTEGER | FK -> event_types | Event category |
| event_time_start | TIMESTAMP | | Event start time |
| event_time_end | TIMESTAMP | | Event end time |
| primary_sat_no | INTEGER | FK -> satellites | Primary satellite |
| secondary_sat_no | INTEGER | FK -> satellites | Secondary satellite (proximity events) |
| confidence | DECIMAL(5,4) | | Confidence 0.0-1.0 |
| detection_method | VARCHAR(50) | | AUTOMATIC, MANUAL, EXTERNAL |
| source | VARCHAR(100) | | Data source/provenance |
| external_id | VARCHAR(100) | | External system ID |
| detection_config | TEXT | | Detector parameters (JSON string) |
| dataset_id | INTEGER | FK -> datasets | Optional dataset link |
| labelled_by | VARCHAR(100) | | Who labelled the event |
| labelled_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Label timestamp |
| notes | TEXT | | Free-text notes |

**Indexes:** `idx_events_dataset(dataset_id)`, `idx_events_type(event_type_id)`, `idx_events_primary_sat(primary_sat_no)`, `idx_events_time(event_time_start)`

**Default event_types (seeded on init):**

| id | name | description |
|----|------|-------------|
| 1 | launch | Object launched into orbit |
| 2 | maneuver | Orbital maneuver detected |
| 3 | proximity | Close approach between two objects |
| 4 | breakup | Object fragmentation event |
| 5 | reentry | Object reentered atmosphere |
| 6 | unknown | Unknown or unclassified event |

---

### 5.11 jobs

Async job tracking for dataset generation and evaluation pipelines.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(100) | PRIMARY KEY | Job identifier |
| job_type | VARCHAR(50) | NOT NULL | dataset_generation, evaluation |
| status | VARCHAR(20) | DEFAULT 'pending' | pending, running, completed, failed |
| progress | INTEGER | DEFAULT 0 | 0-100 percent |
| result | JSON/JSONB | | Job result data |
| error | TEXT | | Error message on failure |
| metadata | JSON/JSONB | | Additional job context |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Job creation time |
| started_at | TIMESTAMP | | Job start time |
| completed_at | TIMESTAMP | | Job completion time |

**Indexes:** `idx_jobs_status(status)`, `idx_jobs_type(job_type)`

---

### 5.12 non_reference_observations

Decoy observations injected into datasets for true-negative evaluation. These observations belong to known satellites but are not in the dataset's reference set, allowing scoring of false-positive rates.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY (sequence) | Auto-generated ID |
| dataset_id | INTEGER | NOT NULL, FK -> datasets | Parent dataset |
| observation_id | VARCHAR(64) | NOT NULL | Observation identifier |
| sensor_id | VARCHAR(32) | | Sensor identifier |
| obs_time | TIMESTAMP | NOT NULL | Observation time (note: `obs_time` not `ob_time`) |
| ra_deg | DECIMAL(12,8) | | Right Ascension (degrees) |
| dec_deg | DECIMAL(12,8) | | Declination (degrees) |
| source_norad_id | INTEGER | NOT NULL | Actual satellite NORAD ID (ground truth) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Row creation time |

**Indexes:** `idx_non_ref_obs_dataset(dataset_id)`, `idx_non_ref_obs_norad(source_norad_id)`

---

### 5.13 breakup_events

Cached breakup/fragmentation events fetched from Space-Track and CelesTrak. Used by the BU (breakup) event detection pipeline to find debris-generating events within dataset time windows.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY (sequence) | Auto-generated ID |
| parent_norad_id | INTEGER | NOT NULL | Parent object NORAD ID |
| parent_name | VARCHAR(100) | | Parent object name |
| event_date | TIMESTAMP | NOT NULL | Breakup event date |
| debris_count | INTEGER | DEFAULT 0 | Number of debris pieces |
| debris_norad_ids | JSON/JSONB | | Array of debris NORAD IDs |
| event_type | VARCHAR(50) | | FRAGMENTATION, COLLISION, ANOMALY |
| source | VARCHAR(20) | NOT NULL | SPACETRACK or CELESTRAK |
| cached_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Cache timestamp |

**Constraints:** UNIQUE(parent_norad_id, event_date, source)
**Indexes:** `idx_breakup_events_date(event_date)`, `idx_breakup_events_parent(parent_norad_id)`

---

### 5.14 profiles

User profiles storing display information and encrypted API tokens. Keyed by Supabase user ID.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | Supabase user ID |
| email | VARCHAR(255) | | User email |
| role | VARCHAR(50) | DEFAULT 'user' | User role |
| display_name | VARCHAR(100) | | Display name |
| organization | VARCHAR(200) | | Organization/affiliation |
| udl_token | TEXT | | Encrypted UDL API token |
| esa_token | TEXT | | Encrypted ESA API token |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Profile creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

**Indexes:** `idx_profiles_email(email)`

---

### 5.15 feedback

User-submitted bug reports and feedback, including browser context for debugging.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID |
| description | TEXT | NOT NULL | Bug/feedback description |
| severity | VARCHAR(20) | NOT NULL | Severity level |
| screenshot_url | VARCHAR(500) | | Uploaded screenshot URL |
| page_url | VARCHAR(2048) | | Page where feedback was submitted |
| user_agent | VARCHAR(500) | | Browser user agent |
| viewport | VARCHAR(100) | | Browser viewport dimensions |
| recent_actions | JSON/JSONB | | Recent user actions |
| console_errors | JSON/JSONB | | Browser console errors |
| sentry_event_id | VARCHAR(200) | | Linked Sentry event |
| app_version | VARCHAR(50) | | Application version |
| reporter_id | VARCHAR(36) | | Reporter user ID |
| reporter_email | VARCHAR(255) | | Reporter email |
| status | VARCHAR(50) | NOT NULL, DEFAULT 'open' | open, resolved, etc. |
| resolution | TEXT | | Resolution notes |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Submission time |
| updated_at | TIMESTAMP | | Last update time |

**Indexes:** `idx_feedback_status(status)`, `idx_feedback_created(created_at)`

---

### 5.16 credentials

Encrypted per-user API credentials for external services (UDL, ESA, etc.).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-generated (SERIAL in PostgreSQL) |
| user_id | VARCHAR(36) | NOT NULL | Supabase user ID |
| service_name | VARCHAR(50) | NOT NULL | Service name (e.g. UDL, ESA) |
| encrypted_primary | TEXT | | Encrypted primary credential |
| encrypted_secondary | TEXT | | Encrypted secondary credential |
| is_valid | BOOLEAN | | Whether credential is valid |
| validation_status | VARCHAR(20) | DEFAULT 'untested' | untested, valid, invalid |
| last_tested_at | TIMESTAMP | | Last validation timestamp |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Row creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

**Constraints:** UNIQUE(user_id, service_name)
**Indexes:** `idx_credentials_user(user_id)`

---

## 6. Repository Pattern

### 6.1 Class Hierarchy

```python
BaseRepository (ABC)
+-- SatelliteRepository
+-- ObservationRepository
+-- StateVectorRepository
+-- ElementSetRepository
+-- DatasetRepository
+-- EventRepository
```

### 6.2 Key Methods

#### DatasetRepository
```python
create_dataset(name, code, tier, ...) -> int
get_dataset(dataset_id=None, name=None) -> pd.Series
list_datasets(tier=None, regime=None) -> pd.DataFrame
update_dataset(dataset_id, **kwargs) -> bool
delete_dataset(dataset_id, cascade=True) -> bool
create_version(parent_id, changes=None) -> int
get_dataset_versions(dataset_id) -> pd.DataFrame
compare_datasets(id1, id2) -> dict
add_observations_to_dataset(dataset_id, obs_ids) -> int
```

#### ObservationRepository
```python
get_by_satellite_time_window(sat_no, start, end) -> pd.DataFrame
get_by_regime(regime, start, end) -> pd.DataFrame
bulk_insert(df) -> int
get_statistics(start=None, end=None) -> pd.DataFrame
get_track_gaps(sat_no, limit=10) -> pd.DataFrame
```

---

## 7. Query Performance

### 7.1 Indexes

See individual table sections above for complete index listings. Key indexes:

| Index | Columns | Purpose |
|-------|---------|---------|
| idx_obs_time | observations(ob_time) | Time range queries |
| idx_obs_sat_time | observations(sat_no, ob_time) | Satellite + time queries |
| idx_obs_track | observations(track_id) | Track lookups |
| idx_sv_sat_epoch | state_vectors(sat_no, epoch) | State vector queries |
| idx_elset_sat_epoch | element_sets(sat_no, epoch) | TLE queries |
| idx_datasets_code | datasets(code) | Dataset code lookups |
| idx_datasets_legacy_code | datasets(legacy_code) | Legacy code lookups |
| idx_ds_obs_split | dataset_observations(dataset_id, split) | CTF split filtering |
| idx_results_test_composite | submission_results(test_composite_score DESC) | Leaderboard ranking |

### 7.2 Performance Targets

| Query Type | Target Latency | Data Size |
|------------|---------------|-----------|
| Single satellite lookup | <50ms | Any |
| Time window query (1 week) | <200ms | <100K obs |
| Full regime aggregation | <1s | <1M obs |
| Dataset export | <5s | <50K obs |

---

## 8. Data Ingestion

### 8.1 Pipeline Flow

```
External API (UDL/Space-Track)
         |
         v
+---------------------+
| DataIngestion       |
| Pipeline            |
+---------------------+
| - Fetch data        |
| - Validate          |
| - Normalize         |
| - Deduplicate       |
+---------------------+
         |
         v
+---------------------+
| Repository          |
| bulk_insert()       |
+---------------------+
         |
         v
    DuckDB / PostgreSQL
```

### 8.2 Validation Rules

| Field | Rule |
|-------|------|
| ra | 0 <= value <= 360 |
| declination | -90 <= value <= 90 |
| ob_time | Valid timestamp |
| sat_no | Positive integer |

---

## 9. Export Formats

### 9.1 JSON Export (Legacy Compatible)

```json
{
  "metadata": {
    "name": "Dataset Name",
    "code": "LEO_A_H_H_H",
    "tier": "T1",
    "orbital_regime": "LEO",
    "observation_count": 1000
  },
  "observations": [
    {
      "id": "obs-001",
      "ob_time": "2025-01-01T12:00:00.000000Z",
      "ra": 100.0,
      "declination": 45.0,
      "track_id": 1,
      "uct": true
    }
  ],
  "references": [
    {
      "sat_no": 25544,
      "sat_name": "ISS",
      "state_vector": {},
      "tle": {}
    }
  ]
}
```

### 9.2 Parquet Export

- Compression: ZSTD (default)
- Row group size: 100,000 rows
- Partitioning: Optional by orbital_regime

---

## 10. CLI Reference

```bash
# Initialize database
python -m uct_benchmark.database init [--force]

# Show status
python -m uct_benchmark.database status

# Backup/Restore
python -m uct_benchmark.database backup [-o path]
python -m uct_benchmark.database restore <backup_file>

# Export
python -m uct_benchmark.database export --dataset-id ID [-o path]
python -m uct_benchmark.database export --observations -o path.parquet

# Import
python -m uct_benchmark.database import <file> [--name name]

# List datasets
python -m uct_benchmark.database list [--tier T1] [--regime LEO]

# Maintenance
python -m uct_benchmark.database verify
python -m uct_benchmark.database vacuum
```

---

## 11. Schema Versioning

The `_schema_metadata` table tracks the current schema version. Migrations are applied incrementally on initialization:

| Migration | Key Changes |
|-----------|-------------|
| 1.2.0 | Added legacy code fields to datasets |
| 1.3.0 | Added downsampling/simulation tracking |
| 1.4.0 | Added non-reference observation support |
| 1.5.0 | Added breakup events cache |
| 1.6.0 | Added feedback, profiles, credentials tables |
| 1.7.0 | Added challenge fields (sensor_biases, calibration_quality, maneuver_during_gap) |
| 1.8.0 | Added CTF split column, per-split composite scores |
| 2.0.0 | Current version (DuckDB + PostgreSQL parity) |

---

## Related Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [Backend API](BACKEND_API.md)
- [Pipeline](PIPELINE.md)
