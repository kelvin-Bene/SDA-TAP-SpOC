# UCT Benchmark + UCTP Lab — System Architecture Report

**Version:** 1.0.0
**Date:** 2026-01-27
**Scope:** Complete system documentation covering database architecture, data sources, credential management, authentication, dataset generation, ML training, evaluation pipeline, and component integration.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Database Architecture (26 Tables)](#2-database-architecture-26-tables)
3. [Database Abstraction Layer](#3-database-abstraction-layer)
4. [Data Sources & External APIs](#4-data-sources--external-apis)
5. [Credential Management](#5-credential-management)
6. [Authentication System](#6-authentication-system)
7. [Dataset Generation Pipeline](#7-dataset-generation-pipeline)
8. [UCTP Lab — Complete Pipeline](#8-uctp-lab--complete-pipeline)
9. [ML Training System](#9-ml-training-system)
10. [Evaluation & Leaderboard](#10-evaluation--leaderboard)
11. [Audit & Monitoring (PostgreSQL Only)](#11-audit--monitoring-postgresql-only)
12. [Data Flow Diagrams](#12-data-flow-diagrams)
13. [Foreign Key Relationships](#13-foreign-key-relationships)
14. [Configuration Reference](#14-configuration-reference)

---

## 1. System Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                       │
│  ┌────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ │
│  │Dashboard│ │ Dataset  │ │ Submit    │ │ Results / │ │ Settings  │ │
│  │  Page   │ │ Browser  │ │   Page    │ │Leaderboard│ │   (Auth)  │ │
│  └────────┘ └──────────┘ └───────────┘ └───────────┘ └───────────┘ │
│         Zustand State  |  Shadcn/UI  |  Cesium 3D  |  TailwindCSS  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTP (localhost:5173 → :8000)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     BACKEND API (FastAPI :8000)                       │
│                                                                      │
│  Routers:  /datasets  /submissions  /results  /leaderboard           │
│            /jobs      /uctp         /credentials  /auth              │
│                                                                      │
│  Middleware:  CORS  │  AuditMiddleware  │  QueryLoggingMiddleware     │
│  Auth:        JWT (HS256) via Supabase  │  Feature-flagged           │
│  Jobs:        ThreadPoolExecutor (4 workers)                         │
│  Services:    CredentialService  │  AuditService                     │
└──────────────┬───────────────────┬───────────────────────────────────┘
               │                   │
     ┌─────────▼─────────┐  ┌─────▼──────────────────────────────┐
     │  DatabaseManager   │  │      External APIs                  │
     │  ┌──────┐┌───────┐ │  │  UDL  ESA  Space-Track  ILRS       │
     │  │DuckDB││Postgre│ │  │  SatNOGS  GCAT  UCS                │
     │  │(dev) ││(prod) │ │  └─────────────────────────────────────┘
     │  └──────┘└───────┘ │
     │   DB_BACKEND flag   │
     └─────────────────────┘
```

### Three Main Subsystems

| Subsystem | Purpose | Key Entry Points |
|-----------|---------|------------------|
| **UCT Benchmark** | Dataset generation + evaluation scoring | `Create_Dataset.py`, `Evaluation.py`, `uct_benchmark/api/apiIntegration.py` |
| **UCTP Lab** | ML pipeline: clustering, IOD, refinement, training | `run_uctp_lab.py`, `uct_benchmark/uctp_lab/pipeline.py` |
| **Backend API** | REST API + auth + audit + job management | `backend_api/main.py`, FastAPI routers |

### Dual-Backend Database Strategy

The system supports two database backends controlled by the `DB_BACKEND` environment variable:

| Feature | DuckDB (default) | PostgreSQL / Supabase |
|---------|-------------------|-----------------------|
| **Use case** | Local development, single-user | Production, multi-user |
| **Schema version** | 1.3.0 (`schema.sql`) | 2.0.0 (`001_initial_schema.sql`) |
| **Tables** | 20 core tables | 26 tables (20 core + 6 production) |
| **Auth** | None (anonymous admin) | Supabase JWT (HS256) |
| **Audit** | None | Full audit trail (6 log tables) |
| **JSON type** | `JSON` | `JSONB` |
| **Timestamps** | `TIMESTAMP` | `TIMESTAMPTZ` |
| **FKs** | Application-enforced | Database-enforced with CASCADE |
| **RLS** | None | Row-Level Security policies |
| **Connection** | Thread-local file connections | `psycopg_pool.ConnectionPool` |

---

## 2. Database Architecture (26 Tables)

### 2.1 Core Data (5 Tables)

#### `data_sources` — External Data Source Registry

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Source identifier |
| `source_name` | `VARCHAR(50) UNIQUE` | UDL, SATNOGS, GCAT, UCS, ILRS, SPACE_TRACK |
| `source_type` | `VARCHAR(30)` | CATALOG, OBSERVATION, VALIDATION |
| `license` | `VARCHAR(50)` | CC-BY-SA, CC-BY, PUBLIC_DOMAIN, RESTRICTED, OPEN |
| `api_endpoint` | `VARCHAR(500)` | Base API URL |
| `last_sync` | `TIMESTAMPTZ` | Last data synchronization time |
| `record_count` | `INTEGER` | Number of records from this source |
| `notes` | `TEXT` | Description of the source |
| `created_at` | `TIMESTAMPTZ` | Record creation time |

**Seeded data (6 sources):**

| ID | Name | Type | License | Endpoint |
|----|------|------|---------|----------|
| 1 | UDL | OBSERVATION | RESTRICTED | `https://unifieddatalibrary.com` |
| 2 | SATNOGS | OBSERVATION | CC-BY-SA | `https://network.satnogs.org/api` |
| 3 | GCAT | CATALOG | CC-BY | `https://planet4589.org/space/gcat` |
| 4 | UCS | CATALOG | OPEN | `https://www.ucs.org` |
| 5 | ILRS | VALIDATION | PUBLIC_DOMAIN | `https://ilrs.gsfc.nasa.gov` |
| 6 | SPACE_TRACK | CATALOG | RESTRICTED | `https://space-track.org` |

**Written by:** `001_initial_schema.sql` seed data, `DataIngestionPipeline`
**Read by:** `DataSourceManager`, observation queries with source tracking

---

#### `satellites` — Space Object Catalog

| Column | Type | Description |
|--------|------|-------------|
| `sat_no` | `INTEGER PK` | NORAD catalog number |
| `name` | `VARCHAR(100)` | Satellite name |
| `cospar_id` | `VARCHAR(20)` | International designator |
| `object_type` | `VARCHAR(20)` | PAYLOAD, ROCKET BODY, DEBRIS |
| `launch_date` | `DATE` | Launch date |
| `decay_date` | `DATE` | Decay date (if applicable) |
| `mass_kg` | `DECIMAL(10,2)` | Mass in kg (from ESA DiscoWeb) |
| `cross_section_m2` | `DECIMAL(10,4)` | Cross-section area |
| `drag_coeff` | `DECIMAL(6,4)` | Drag coefficient (default 2.5) |
| `srp_coeff` | `DECIMAL(6,4)` | Solar radiation pressure coefficient (default 1.5) |
| `orbital_regime` | `VARCHAR(10)` | LEO, MEO, GEO, HEO |
| `purpose` | `VARCHAR(100)` | Satellite purpose (from UCS) |
| `operator` | `VARCHAR(100)` | Operating organization (from UCS) |
| `launch_site` | `VARCHAR(100)` | Launch site (from GCAT) |
| `power_watts` | `DECIMAL(10,2)` | Power output (from UCS) |
| `amr_m2_kg` | `DECIMAL(12,6)` | Area-to-mass ratio for HAMR detection |
| `ucs_synced_at` | `TIMESTAMPTZ` | Last UCS sync timestamp |
| `gcat_synced_at` | `TIMESTAMPTZ` | Last GCAT sync timestamp |
| `created_at` | `TIMESTAMPTZ` | Record creation time |
| `updated_at` | `TIMESTAMPTZ` | Last update time (trigger-maintained in PG) |

**Written by:** `SatelliteRepository.create()`, `DataSourceManager.enrich_satellites_batch()`, `apiIntegration.py`
**Read by:** `SatelliteRepository.get()`, `get_by_regime()`, dataset generation, HAMR detection

---

#### `observations` — Sensor Measurements

| Column | Type | Description |
|--------|------|-------------|
| `id` | `VARCHAR(64) PK` | UDL observation ID |
| `sat_no` | `INTEGER` | NORAD catalog number |
| `ob_time` | `TIMESTAMPTZ NOT NULL` | Observation timestamp |
| `ra` | `DECIMAL(12,8)` | Right Ascension (degrees) |
| `declination` | `DECIMAL(12,8)` | Declination (degrees) |
| `range_km` | `DECIMAL(12,4)` | Radar range (km) |
| `range_rate_km_s` | `DECIMAL(10,6)` | Range rate (km/s) |
| `azimuth` | `DECIMAL(12,8)` | Azimuth (degrees) |
| `elevation` | `DECIMAL(12,8)` | Elevation (degrees) |
| `sensor_name` | `VARCHAR(100)` | Sensor identifier |
| `data_mode` | `VARCHAR(20)` | REAL or SIMULATED |
| `track_id` | `VARCHAR(64)` | Track association ID |
| `is_uct` | `BOOLEAN` | Uncorrelated track flag |
| `is_simulated` | `BOOLEAN` | Simulation flag |
| `source_id` | `INTEGER` | FK to `data_sources(id)` |
| `observation_type` | `VARCHAR(10)` | EO, RF, RADAR (default EO) |
| `created_at` | `TIMESTAMPTZ` | Record creation time |

**Indexes:** `idx_obs_time(ob_time)`, `idx_obs_sat_time(sat_no, ob_time)`, `idx_obs_track(track_id)`
**Written by:** `ObservationRepository.bulk_insert()`, `apiIntegration.generateDataset()`, SatNOGS RF ingestion
**Read by:** `ObservationRepository` queries, dataset observation joining, UCTP pipeline ingest

---

#### `state_vectors` — J2000 ECI Position/Velocity

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `sat_no` | `INTEGER` | FK to `satellites(sat_no)` |
| `epoch` | `TIMESTAMPTZ NOT NULL` | State vector epoch |
| `x_pos` | `DECIMAL(16,6) NOT NULL` | X position (km, J2000 ECI) |
| `y_pos` | `DECIMAL(16,6) NOT NULL` | Y position (km) |
| `z_pos` | `DECIMAL(16,6) NOT NULL` | Z position (km) |
| `x_vel` | `DECIMAL(16,9) NOT NULL` | X velocity (km/s) |
| `y_vel` | `DECIMAL(16,9) NOT NULL` | Y velocity (km/s) |
| `z_vel` | `DECIMAL(16,9) NOT NULL` | Z velocity (km/s) |
| `covariance` | `JSONB` | 6x6 covariance matrix (JSON array) |
| `source` | `VARCHAR(50)` | UDL, SPACE_TRACK, PROPAGATED |
| `data_mode` | `VARCHAR(20)` | REAL or SIMULATED |
| `created_at` | `TIMESTAMPTZ` | Record creation time |

**Unique constraint:** `(sat_no, epoch, source)`
**Written by:** `StateVectorRepository.create()`, `bulk_insert()`, dataset generation
**Read by:** Dataset references, UCTP evaluation, state metrics computation

---

#### `element_sets` — Two-Line Element Sets (TLEs)

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `sat_no` | `INTEGER` | FK to `satellites(sat_no)` |
| `line1` | `VARCHAR(70) NOT NULL` | TLE line 1 |
| `line2` | `VARCHAR(70) NOT NULL` | TLE line 2 |
| `epoch` | `TIMESTAMPTZ NOT NULL` | Element set epoch |
| `inclination` | `DECIMAL(10,6)` | Inclination (degrees) |
| `raan` | `DECIMAL(10,6)` | Right Ascension of Ascending Node |
| `eccentricity` | `DECIMAL(12,10)` | Eccentricity |
| `arg_perigee` | `DECIMAL(10,6)` | Argument of Perigee |
| `mean_anomaly` | `DECIMAL(10,6)` | Mean Anomaly |
| `mean_motion` | `DECIMAL(14,10)` | Mean motion (rev/day) |
| `b_star` | `DECIMAL(16,12)` | B* drag term |
| `semi_major_axis_km` | `DECIMAL(12,4)` | Derived semi-major axis |
| `period_minutes` | `DECIMAL(10,4)` | Derived orbital period |
| `source` | `VARCHAR(50)` | Data source identifier |
| `created_at` | `TIMESTAMPTZ` | Record creation time |

**Unique constraint:** `(sat_no, epoch)`
**Written by:** `ElementSetRepository.create()`, `bulk_insert()`, Space-Track ingestion
**Read by:** Dataset references, orbit propagation, TLE-based orbit determination

---

### 2.2 Dataset Management (3 Tables)

#### `datasets` — Benchmark Dataset Metadata

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `name` | `VARCHAR(100) UNIQUE NOT NULL` | Human-readable name |
| `code` | `VARCHAR(20)` | Shortcode (e.g., `LEO_A_H_H_H`) |
| `version` | `INTEGER` | Version number (default 1) |
| `parent_id` | `INTEGER` | FK to `datasets(id)` for versioning |
| `tier` | `VARCHAR(5)` | T1, T2, T3, T4, T5 |
| `orbital_regime` | `VARCHAR(10)` | LEO, MEO, GEO, HEO |
| `time_window_start` | `TIMESTAMPTZ` | Observation window start |
| `time_window_end` | `TIMESTAMPTZ` | Observation window end |
| `observation_count` | `INTEGER` | Total observations in dataset |
| `satellite_count` | `INTEGER` | Total satellites in dataset |
| `avg_coverage` | `DECIMAL(8,4)` | Average orbital coverage |
| `avg_obs_count` | `DECIMAL(8,2)` | Average observations per satellite |
| `max_track_gap` | `DECIMAL(8,4)` | Maximum gap between tracks |
| `downsampling_applied` | `BOOLEAN` | Whether downsampling was applied |
| `simulation_applied` | `BOOLEAN` | Whether simulation was applied |
| `simulated_obs_count` | `INTEGER` | Count of simulated observations |
| `downsampling_config` | `JSONB` | Downsampling parameters |
| `simulation_config` | `JSONB` | Simulation parameters |
| `generation_params` | `JSONB` | Full generation configuration |
| `status` | `VARCHAR(20)` | created, processing, available, failed |
| `created_by` | `UUID` | FK to `users(id)` (PostgreSQL only) |
| `created_at` | `TIMESTAMPTZ` | Record creation time |
| `updated_at` | `TIMESTAMPTZ` | Last update (trigger-maintained) |
| `json_path` | `VARCHAR(500)` | Export JSON file path |
| `parquet_path` | `VARCHAR(500)` | Export Parquet file path |

**Written by:** `DatasetRepository.create_dataset()`, `update_dataset()`, worker `run_dataset_generation()`
**Read by:** `DatasetRepository.get_dataset()`, `list_datasets()`, API routers

---

#### `dataset_observations` — Dataset ↔ Observation Junction

| Column | Type | Description |
|--------|------|-------------|
| `dataset_id` | `INTEGER` | FK to `datasets(id)` |
| `observation_id` | `VARCHAR(64)` | FK to `observations(id)` |
| `assigned_track_id` | `INTEGER` | Decorrelated track assignment |
| `assigned_object_id` | `INTEGER` | Decorrelated object assignment |

**Primary key:** `(dataset_id, observation_id)`
**Written by:** `DatasetRepository.add_observations_to_dataset()`, worker persistence step
**Read by:** `DatasetRepository.get_dataset_observations()`, UCTP ingest, evaluation

---

#### `dataset_references` — Truth Data for Evaluation

| Column | Type | Description |
|--------|------|-------------|
| `dataset_id` | `INTEGER` | FK to `datasets(id)` |
| `sat_no` | `INTEGER` | FK to `satellites(sat_no)` |
| `state_vector_id` | `INTEGER` | FK to `state_vectors(id)` |
| `element_set_id` | `INTEGER` | FK to `element_sets(id)` |
| `grouped_obs_ids` | `JSONB` | Observation IDs belonging to this satellite |

**Primary key:** `(dataset_id, sat_no)`
**Written by:** `DatasetRepository.add_references_to_dataset()`, dataset generation pipeline
**Read by:** `DatasetRepository.get_dataset_references()`, evaluation pipeline

---

### 2.3 Submission & Evaluation (3 Tables)

#### `submissions` — Algorithm Result Uploads

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `dataset_id` | `INTEGER` | FK to `datasets(id)` |
| `algorithm_name` | `VARCHAR(100) NOT NULL` | Name of the algorithm |
| `version` | `VARCHAR(50)` | Algorithm version (default '1.0') |
| `description` | `TEXT` | Algorithm description |
| `file_path` | `VARCHAR(500)` | Path to uploaded UCTP output file |
| `status` | `VARCHAR(20)` | queued, validating, processing, completed, failed |
| `job_id` | `VARCHAR(100)` | FK to `jobs(id)` for background eval |
| `error_message` | `TEXT` | Error details if failed |
| `created_by` | `UUID` | FK to `users(id)` (PostgreSQL only) |
| `created_at` | `TIMESTAMPTZ` | Submission time |
| `completed_at` | `TIMESTAMPTZ` | Evaluation completion time |

**Written by:** Submissions router (`POST /api/v1/submissions/`), evaluation worker
**Read by:** Results router, leaderboard queries

---

#### `submission_results` — Evaluation Metrics

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `submission_id` | `INTEGER UNIQUE` | FK to `submissions(id)` |
| `true_positives` | `INTEGER` | Correctly associated objects |
| `false_positives` | `INTEGER` | Incorrectly associated objects |
| `false_negatives` | `INTEGER` | Missed objects |
| `precision` | `DECIMAL(10,6)` | TP / (TP + FP) |
| `recall` | `DECIMAL(10,6)` | TP / (TP + FN) |
| `f1_score` | `DECIMAL(10,6)` | Harmonic mean of precision and recall |
| `position_rms_km` | `DECIMAL(12,6)` | Position RMS error (km) |
| `velocity_rms_km_s` | `DECIMAL(12,9)` | Velocity RMS error (km/s) |
| `mahalanobis_distance` | `DECIMAL(12,6)` | Statistical distance metric |
| `ra_residual_rms_arcsec` | `DECIMAL(12,6)` | RA residual RMS (arcsec) |
| `dec_residual_rms_arcsec` | `DECIMAL(12,6)` | Dec residual RMS (arcsec) |
| `raw_results` | `JSONB` | Full breakdown (binary + state metrics) |
| `processing_time_seconds` | `DECIMAL(12,3)` | Evaluation duration |
| `created_at` | `TIMESTAMPTZ` | Result creation time |

**Written by:** `run_evaluation_pipeline()` in `workers.py:570-597`
**Read by:** Results router, leaderboard (ranked by `f1_score DESC`)

---

#### `jobs` — Background Task Tracking

| Column | Type | Description |
|--------|------|-------------|
| `id` | `VARCHAR(100) PK` | UUID job identifier |
| `job_type` | `VARCHAR(50) NOT NULL` | dataset_generation, evaluation |
| `status` | `VARCHAR(20)` | pending, running, completed, failed |
| `progress` | `INTEGER` | 0–100 completion percentage |
| `result` | `JSONB` | Job output data |
| `error` | `TEXT` | Error message if failed |
| `metadata` | `JSONB` | Job configuration context |
| `created_at` | `TIMESTAMPTZ` | Job creation time |
| `started_at` | `TIMESTAMPTZ` | Execution start time |
| `completed_at` | `TIMESTAMPTZ` | Completion time |

**Written by:** `DbJobManager`, worker functions (`start_job`, `complete_job`, `fail_job`)
**Read by:** Jobs router (`GET /api/v1/jobs/{id}`), frontend polling

---

### 2.4 Validation (1 Table)

#### `validation_measurements` — ILRS Laser Ranging Ground Truth

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `sat_no` | `INTEGER NOT NULL` | NORAD catalog number |
| `epoch` | `TIMESTAMPTZ NOT NULL` | Measurement epoch |
| `range_m` | `DECIMAL(15,6)` | Range in meters (mm precision) |
| `station_code` | `VARCHAR(10)` | ILRS station code (e.g., YARL, GRZL) |
| `station_name` | `VARCHAR(100)` | Station name |
| `normal_point_rms_m` | `DECIMAL(10,6)` | Normal point RMS (meters) |
| `num_returns` | `INTEGER` | Number of photon returns |
| `source` | `VARCHAR(20)` | Default 'ILRS' |
| `created_at` | `TIMESTAMPTZ` | Record creation time |

**Unique constraint:** `(sat_no, epoch, station_code)`
**Written by:** `DataIngestionPipeline.ingest_validation_data()`, ILRS open source connector
**Read by:** `validationMetrics.py`, ILRS coverage analysis

---

### 2.5 Event Labeling (3 Tables)

#### `event_types` — Event Type Lookup

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Type identifier |
| `name` | `VARCHAR(50) UNIQUE NOT NULL` | Type name |
| `description` | `TEXT` | Human-readable description |

**Seeded data (6 types):**

| ID | Name | Description |
|----|------|-------------|
| 1 | launch | Object launched into orbit |
| 2 | maneuver | Orbital maneuver detected |
| 3 | proximity | Close approach between two objects |
| 4 | breakup | Object fragmentation event |
| 5 | reentry | Object reentered atmosphere |
| 6 | unknown | Unknown or unclassified event |

---

#### `events` — Detected Space Events

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `event_type_id` | `INTEGER` | FK to `event_types(id)` |
| `event_time_start` | `TIMESTAMPTZ` | Event start time |
| `event_time_end` | `TIMESTAMPTZ` | Event end time |
| `primary_sat_no` | `INTEGER` | FK to `satellites(sat_no)` |
| `secondary_sat_no` | `INTEGER` | FK to `satellites(sat_no)` (proximity events) |
| `confidence` | `DECIMAL(5,4)` | Score 0.0–1.0 |
| `detection_method` | `VARCHAR(50)` | AUTOMATIC, MANUAL, EXTERNAL |
| `source` | `VARCHAR(100)` | Data source |
| `external_id` | `VARCHAR(100)` | External reference ID |
| `labelled_by` | `VARCHAR(100)` | Person/system identifier |
| `labelled_at` | `TIMESTAMPTZ` | Label creation time |
| `notes` | `TEXT` | Additional notes |

**Written by:** `EventRepository.create_event()`
**Read by:** `EventRepository.get_events_for_satellite()`

---

#### `event_observations` — Event ↔ Observation Junction

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | `INTEGER` | FK to `events(id)` |
| `observation_id` | `VARCHAR(64)` | FK to `observations(id)` |

**Primary key:** `(event_id, observation_id)`
**Written by:** `EventRepository.link_observations_to_event()`
**Read by:** `EventRepository.get_event_observations()`

---

### 2.6 UCTP Lab / ML (3 Tables)

#### `uctp_runs` — Pipeline Execution Records

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `dataset_id` | `INTEGER` | FK to `datasets(id)` |
| `algorithm_name` | `VARCHAR(100) NOT NULL` | Pipeline configuration name |
| `config` | `JSONB NOT NULL` | Full pipeline configuration |
| `status` | `VARCHAR(20)` | pending, running, completed, failed |
| `started_at` | `TIMESTAMPTZ` | Execution start time |
| `completed_at` | `TIMESTAMPTZ` | Completion time |
| `f1_score` | `DOUBLE PRECISION` | F1 score result |
| `precision` | `DOUBLE PRECISION` | Precision result |
| `recall` | `DOUBLE PRECISION` | Recall result |
| `position_rms_km` | `DOUBLE PRECISION` | Position RMS |
| `velocity_rms_km_s` | `DOUBLE PRECISION` | Velocity RMS |
| `clusters_found` | `INTEGER` | Number of clusters found |
| `objects_resolved` | `INTEGER` | Number of objects resolved |
| `output_path` | `VARCHAR(512)` | Path to output JSON file |
| `log_output` | `TEXT` | Pipeline log text |
| `error_message` | `TEXT` | Error message if failed |
| `created_by` | `UUID` | FK to `users(id)` |
| `created_at` | `TIMESTAMPTZ` | Record creation time |

**Written by:** UCTP router (`POST /api/v1/uctp/runs/`), `uctp_workers.py`
**Read by:** UCTP router (`GET /api/v1/uctp/runs/`)

---

#### `uctp_models` — Trained ML Models

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `name` | `VARCHAR(100) NOT NULL` | Model name |
| `model_type` | `VARCHAR(50) NOT NULL` | clustering_nn, propagation_ml, hybrid |
| `version` | `VARCHAR(20) NOT NULL` | Auto-incremented version |
| `description` | `TEXT` | Model description |
| `training_dataset_ids` | `JSONB` | Dataset IDs used for training |
| `training_config` | `JSONB` | Training hyperparameters |
| `training_epochs` | `INTEGER` | Total epochs trained |
| `training_loss` | `DOUBLE PRECISION` | Final training loss |
| `validation_loss` | `DOUBLE PRECISION` | Final validation loss |
| `best_f1_score` | `DOUBLE PRECISION` | Best F1 score during training |
| `best_position_rms_km` | `DOUBLE PRECISION` | Best position RMS |
| `model_path` | `VARCHAR(512)` | Path to serialized model file |
| `status` | `VARCHAR(20)` | training, ready, failed |
| `created_at` | `TIMESTAMPTZ` | Record creation time |

**Written by:** ML training pipeline, UCTP API training endpoint
**Read by:** Model registry, UCTP pipeline for inference

---

#### `uctp_api_connections` — External Service Health

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `service_name` | `VARCHAR(50) NOT NULL` | Service identifier |
| `status` | `VARCHAR(20) NOT NULL` | connected, error, timeout |
| `response_time_ms` | `DOUBLE PRECISION` | Response time |
| `last_checked` | `TIMESTAMPTZ` | Last check timestamp |
| `error_message` | `TEXT` | Error details |
| `metadata` | `JSONB` | Additional context |

**Written by:** UCTP connectivity checks, `test_uctp_lab_connectivity.py`
**Read by:** Health monitoring, UCTP status endpoint

---

### 2.7 Credentials (1 Table)

#### `credentials` — Encrypted Credential Storage

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incremented ID |
| `service_name` | `VARCHAR(50) UNIQUE NOT NULL` | Service identifier |
| `credential_type` | `VARCHAR(30) NOT NULL` | bearer_token, username_password, jwt, path |
| `encrypted_primary` | `VARCHAR(2000)` | Fernet-encrypted primary credential |
| `encrypted_secondary` | `VARCHAR(2000)` | Fernet-encrypted secondary credential |
| `label` | `VARCHAR(100)` | Human-readable label |
| `description` | `TEXT` | Service description |
| `is_configured` | `BOOLEAN` | Whether credentials are stored |
| `last_validated` | `TIMESTAMPTZ` | Last validation check time |
| `validation_status` | `VARCHAR(20)` | valid, invalid, untested |
| `created_at` | `TIMESTAMPTZ` | Record creation time |
| `updated_at` | `TIMESTAMPTZ` | Last update time |

**Seeded data (5 services):**

| Service | Type | Label |
|---------|------|-------|
| `udl` | bearer_token | Unified Data Library |
| `esa` | bearer_token | ESA Discosweb |
| `nasa_earthdata` | jwt | NASA Earthdata |
| `spacetrack` | username_password | Space-Track.org |
| `orekit` | path | Orekit Data |

**Written by:** `CredentialService.save_credentials()`, seed data
**Read by:** `CredentialService.resolve()`, credentials router

---

### 2.8 Metadata (1 Table)

#### `_schema_metadata` — Schema Version Tracking

| Column | Type | Description |
|--------|------|-------------|
| `key` | `VARCHAR(100) PK` | Metadata key |
| `value` | `VARCHAR(500)` | Metadata value |
| `updated_at` | `TIMESTAMPTZ` | Last update time |

**Stored keys:** `version` (DuckDB: `1.0.0`, PostgreSQL: `2.0.0`), `migrated_at`, `source`

---

### 2.9 Production-Only / PostgreSQL (6 Tables)

#### `users` — Application User Profiles

| Column | Type | Description |
|--------|------|-------------|
| `id` | `UUID PK` | Application user ID (`gen_random_uuid()`) |
| `auth_user_id` | `UUID UNIQUE` | FK to Supabase `auth.users(id)` |
| `email` | `VARCHAR(255) UNIQUE NOT NULL` | User email |
| `username` | `VARCHAR(100) UNIQUE` | Display name |
| `organization` | `VARCHAR(200)` | User's organization |
| `role` | `VARCHAR(30)` | admin, operator, viewer (default: viewer) |
| `is_active` | `BOOLEAN` | Account active flag (default: true) |
| `created_at` | `TIMESTAMPTZ` | Registration time |
| `updated_at` | `TIMESTAMPTZ` | Last update (trigger-maintained) |

---

#### `audit_log` — CRUD Audit Trail

| Column | Type | Description |
|--------|------|-------------|
| `id` | `BIGINT PK (IDENTITY)` | Auto-generated ID |
| `user_id` | `UUID` | FK to `users(id)` |
| `action` | `VARCHAR(100) NOT NULL` | CREATE, UPDATE, DELETE, LOGIN, ACCESS |
| `resource_type` | `VARCHAR(100)` | dataset, submission, credential, etc. |
| `resource_id` | `VARCHAR(200)` | Primary key of affected resource |
| `details` | `JSONB` | Context (old/new values, etc.) |
| `ip_address` | `VARCHAR(45)` | IPv4 or IPv6 |
| `user_agent` | `TEXT` | Browser/client identifier |
| `created_at` | `TIMESTAMPTZ NOT NULL` | Event timestamp |

---

#### `api_call_log` — HTTP Request Metrics

| Column | Type | Description |
|--------|------|-------------|
| `id` | `BIGINT PK (IDENTITY)` | Auto-generated ID |
| `user_id` | `UUID` | FK to `users(id)` |
| `method` | `VARCHAR(10) NOT NULL` | GET, POST, PUT, DELETE, PATCH |
| `path` | `VARCHAR(500) NOT NULL` | Request path |
| `status_code` | `INTEGER` | HTTP status code |
| `request_body_size` | `INTEGER` | Request body size (bytes) |
| `response_body_size` | `INTEGER` | Response body size (bytes) |
| `duration_ms` | `DOUBLE PRECISION` | Request duration |
| `ip_address` | `VARCHAR(45)` | Client IP |
| `user_agent` | `TEXT` | Client identifier |
| `error_message` | `TEXT` | Error details |
| `created_at` | `TIMESTAMPTZ NOT NULL` | Request timestamp |

---

#### `query_log` — Slow Query Tracking

| Column | Type | Description |
|--------|------|-------------|
| `id` | `BIGINT PK (IDENTITY)` | Auto-generated ID |
| `query_hash` | `VARCHAR(64)` | SHA-256 of normalized query |
| `query_text` | `TEXT NOT NULL` | Query SQL |
| `params_summary` | `TEXT` | Redacted parameters |
| `duration_ms` | `DOUBLE PRECISION` | Execution time |
| `rows_affected` | `INTEGER` | Rows returned/modified |
| `source` | `VARCHAR(100)` | api, worker, migration, manual |
| `user_id` | `UUID` | FK to `users(id)` |
| `created_at` | `TIMESTAMPTZ NOT NULL` | Query timestamp |

---

#### `credential_access_log` — Credential Security Trail

| Column | Type | Description |
|--------|------|-------------|
| `id` | `BIGINT PK (IDENTITY)` | Auto-generated ID |
| `user_id` | `UUID` | FK to `users(id)` |
| `service_name` | `VARCHAR(50) NOT NULL` | Credential service name |
| `action` | `VARCHAR(50) NOT NULL` | read, write, validate, delete |
| `source` | `VARCHAR(100)` | api, worker, cli |
| `success` | `BOOLEAN NOT NULL` | Whether access succeeded |
| `ip_address` | `VARCHAR(45)` | Client IP |
| `created_at` | `TIMESTAMPTZ NOT NULL` | Access timestamp |

---

#### `system_log` — Application Diagnostics

| Column | Type | Description |
|--------|------|-------------|
| `id` | `BIGINT PK (IDENTITY)` | Auto-generated ID |
| `level` | `VARCHAR(20) NOT NULL` | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `component` | `VARCHAR(100)` | api, worker, migration, scheduler |
| `message` | `TEXT NOT NULL` | Log message |
| `details` | `JSONB` | Structured context |
| `created_at` | `TIMESTAMPTZ NOT NULL` | Event timestamp |

---

## 3. Database Abstraction Layer

### Architecture

```
                   DatabaseManager
                   ┌──────────────┐
                   │  execute()   │
                   │  bulk_insert │
                   │  connection()│
                   │  initialize()│
                   │  6 repos     │──── SatelliteRepository
                   └──────┬───────┘     ObservationRepository
                          │             StateVectorRepository
                 ┌────────┴────────┐    ElementSetRepository
                 │                 │    DatasetRepository
          ┌──────▼──────┐  ┌──────▼──────┐  EventRepository
          │ DuckDBBackend│  │PostgresBackend│
          │  thread-local│  │ psycopg_pool │
          └──────────────┘  └──────────────┘
```

### `DatabaseBackendInterface` (Abstract Base)

**File:** `uct_benchmark/database/backend_interface.py`

Defines the contract all backends must implement:

| Method | Description |
|--------|-------------|
| `execute(query, params)` | Execute SQL with `?` placeholders |
| `executemany(query, params_list)` | Batch execution |
| `execute_df_insert(table, df, columns, conflict_clause)` | Bulk DataFrame insert |
| `connection()` | Context manager for raw connection |
| `initialize_schema(force)` | Create/recreate tables |
| `close()` | Release all resources |
| `is_initialized()` | Check if schema exists |
| `schema_name` | Property: `'main'` (DuckDB) or `'public'` (PG) |

Also provides `QueryResult` — a unified wrapper normalizing DuckDB and PostgreSQL results into a consistent interface with `fetchone()`, `fetchall()`, and `fetchdf()` methods.

### `DuckDBBackend`

**File:** `uct_benchmark/database/duckdb_backend.py`

- **Threading:** Thread-local connections via `threading.local()`. Each thread gets its own DuckDB connection to the same file.
- **In-memory mode:** Shared connection via `_shared_connection` for testing.
- **Bulk insert:** Register/unregister pattern — registers a DataFrame as a temporary view, then `INSERT ... SELECT FROM` the view, and unregisters immediately after.
- **Schema init:** Delegates to `schema.initialize_schema()` which reads `schema.sql`.

### `PostgresBackend`

**File:** `uct_benchmark/database/postgres_backend.py`

- **Connection pool:** `psycopg_pool.ConnectionPool` with configurable `min_size` (default 2) and `max_size` (default 10). Thread-safe by design.
- **Placeholder conversion:** Automatically converts `?` placeholders to `%s` at query time via `_convert_query()`. Also handles `INSERT OR REPLACE` → `ON CONFLICT DO UPDATE` and `INSERT OR IGNORE` → `ON CONFLICT DO NOTHING`.
- **Bulk insert:** Uses `executemany` with `INSERT ... VALUES (%s, ...)` since PostgreSQL `COPY` doesn't support `ON CONFLICT`. Replaces `NaN`/`NaT` with `None` for PG compatibility.
- **Schema init:** Delegates to `schema_postgres.initialize_schema_postgres()` or expects the `001_initial_schema.sql` migration to have been run.
- **Autocommit:** Pool configured with `autocommit=True`.

### `DatabaseManager`

**File:** `uct_benchmark/database/connection.py`

The central orchestrator that:

1. **Resolves backend** via `_resolve_backend()` — reads `DB_BACKEND` from `AppConfig` (defaults to `"duckdb"`)
2. **Delegates all operations** to the selected backend
3. **Exposes lazy-loaded repository properties:**

```python
db.satellites      # SatelliteRepository
db.observations    # ObservationRepository
db.state_vectors   # StateVectorRepository
db.element_sets    # ElementSetRepository
db.datasets        # DatasetRepository
db.events          # EventRepository
```

Each repository is instantiated on first access with a reference back to the `DatabaseManager`.

### Repository Pattern

**File:** `uct_benchmark/database/repository.py`

All 6 repositories extend `BaseRepository` which provides:
- `execute(query, params)` — delegates to `db.execute()`
- `to_dataframe(query, params)` — returns `pd.DataFrame`
- `fetchone()` / `fetchall()` — convenience wrappers

| Repository | Table | Key Operations |
|------------|-------|----------------|
| `SatelliteRepository` | `satellites` | `create`, `get`, `get_by_regime`, `update`, `upsert`, `bulk_upsert` |
| `ObservationRepository` | `observations` | `get_by_satellite_time_window`, `get_by_regime`, `get_uct_observations`, `bulk_insert`, `get_track_gaps`, `get_statistics` |
| `StateVectorRepository` | `state_vectors` | `create`, `get_by_satellite_epoch`, `get_latest`, `bulk_insert` |
| `ElementSetRepository` | `element_sets` | `create`, `get_by_satellite_epoch`, `get_latest`, `bulk_insert` |
| `DatasetRepository` | `datasets`, `dataset_observations`, `dataset_references` | `create_dataset`, `list_datasets`, `update_dataset`, `create_version`, `compare_datasets`, `add_observations_to_dataset`, `add_references_to_dataset` |
| `EventRepository` | `events`, `event_types`, `event_observations` | `create_event`, `get_events_for_satellite`, `link_observations_to_event` |

---

## 4. Data Sources & External APIs

### 4.1 Authenticated Sources

#### UDL (Unified Data Library)

| Property | Value |
|----------|-------|
| **URL** | `https://unifieddatalibrary.com` |
| **Auth** | Bearer token (Base64-encoded credentials) |
| **Data type** | Radar, RF, and optical observations; state vectors |
| **License** | Restricted (US government) |
| **Env var** | `UDL_TOKEN` |
| **DB service** | `udl` / `bearer_token` |
| **Code path** | `uct_benchmark/api/apiIntegration.py`, `uctp_lab/connectors/udl_connector.py` |
| **Ingestion** | Primary observation source for dataset generation. Queried per-satellite with time windows. |

#### ESA DiscoSweb

| Property | Value |
|----------|-------|
| **URL** | `https://discosweb.esoc.esa.int` |
| **Auth** | Bearer token |
| **Data type** | Satellite physical properties (mass, cross-section, drag/SRP coefficients) |
| **License** | Restricted |
| **Env var** | `ESA_TOKEN` |
| **DB service** | `esa` / `bearer_token` |
| **Code path** | `uct_benchmark/api/apiIntegration.py` |
| **Ingestion** | Enriches `satellites` table with physical properties during dataset generation. |

#### Space-Track

| Property | Value |
|----------|-------|
| **URL** | `https://space-track.org` |
| **Auth** | Username/password (session-based) |
| **Data type** | Official US catalog, TLEs, conjunction data |
| **License** | Restricted |
| **Env vars** | `SPACETRACK_USER`, `SPACETRACK_PASS` |
| **DB service** | `spacetrack` / `username_password` |
| **Code path** | `uctp_lab/connectors/spacetrack_connector.py` |
| **Ingestion** | TLEs stored in `element_sets`, catalog data in `satellites`. |

#### ILRS / NASA Earthdata

| Property | Value |
|----------|-------|
| **URL** | `https://ilrs.gsfc.nasa.gov`, `https://urs.earthdata.nasa.gov` |
| **Auth** | JWT token |
| **Data type** | Satellite laser ranging (sub-cm precision ground truth) |
| **License** | Public domain |
| **Env var** | `NASA_EARTHDATA_TOKEN` |
| **DB service** | `nasa_earthdata` / `jwt` |
| **Code path** | `uct_benchmark/api/open_sources.py` (`ilrsGetSatellites()`) |
| **Ingestion** | Stored in `validation_measurements`. Used for T1H tier validation. |

### 4.2 Open Sources (No Auth Required)

#### SatNOGS (Satellite Observation Network)

| Property | Value |
|----------|-------|
| **URL** | Network: `https://network.satnogs.org/api`, DB: `https://db.satnogs.org/api` |
| **Auth** | None |
| **Data type** | RF observations from 200+ ground stations |
| **License** | CC-BY-SA 4.0 |
| **Code path** | `uct_benchmark/api/open_sources.py` (`satnogsQuery()`) |
| **Ingestion** | RF observations added to `observations` table with `observation_type='RF'` and `source_id=2`. Used for multi-phenomenology (MX) datasets. |

#### GCAT (General Catalog of Artificial Space Objects)

| Property | Value |
|----------|-------|
| **URL** | `https://planet4589.org/space/gcat` |
| **Auth** | None |
| **Data type** | 57,000+ object catalog by Jonathan McDowell |
| **License** | CC-BY |
| **Code path** | `uct_benchmark/api/open_sources.py` (`gcatQuery()`, `gcatLookupByNorad()`) |
| **Ingestion** | Enriches `satellites` table with launch site, COSPAR ID. Cached locally with 24-hour TTL. |

#### UCS (Union of Concerned Scientists Satellite Database)

| Property | Value |
|----------|-------|
| **URL** | `https://www.ucs.org` |
| **Auth** | None |
| **Data type** | 7,500+ operational satellite records (purpose, operator, mass, power) |
| **License** | Open (quarterly updates) |
| **Code path** | `uct_benchmark/api/open_sources.py` (`ucsQuery()`, `ucsLookupByNorad()`) |
| **Ingestion** | Enriches `satellites` table with `purpose`, `operator`, `mass_kg`, `power_watts`. Cached locally with 24-hour TTL. |

---

## 5. Credential Management

### Architecture

**File:** `backend_api/services/credential_service.py`

The credential system uses a three-tier resolution chain:

```
resolve(service_name)
    │
    ├─ 1. Encrypted DB → SELECT encrypted_primary FROM credentials
    │      └─ Fernet.decrypt() using CREDENTIAL_ENCRYPTION_KEY
    │      └─ Returns (primary, secondary, "database")
    │
    ├─ 2. Environment Variables → os.environ.get(ENV_VAR_MAP[service])
    │      └─ Returns (primary, secondary, "environment")
    │
    └─ 3. None → Returns (None, None, "none")
```

### Encryption Details

- **Algorithm:** Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
- **Key source:** `CREDENTIAL_ENCRYPTION_KEY` environment variable
- **Key generation:** `Fernet.generate_key()` (URL-safe base64-encoded 32-byte key)
- **Fallback:** If encryption key is not set, service operates in env-only mode

### Environment Variable Mapping

**Defined in:** `credential_service.py:21-27`

```python
ENV_VAR_MAP = {
    "udl":            ("UDL_TOKEN", None),
    "esa":            ("ESA_TOKEN", None),
    "nasa_earthdata": ("NASA_EARTHDATA_TOKEN", None),
    "spacetrack":     ("SPACETRACK_USER", "SPACETRACK_PASS"),
    "orekit":         ("OREKIT_DATA_PATH", None),
}
```

### Startup Wiring

At application startup (`backend_api/main.py:52-57`), the credential resolver is injected into UCTP Lab connectors:

```python
from uct_benchmark.uctp_lab.connectors import init_credential_resolver
init_credential_resolver(cred_service.resolve)
```

This allows all connectors (UDL, Space-Track, Orekit, etc.) to resolve credentials transparently.

### API Endpoints

**Router:** `backend_api/routers/credentials.py`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/credentials/` | List all services (no secrets) |
| `GET` | `/api/v1/credentials/{service}` | Get service metadata |
| `POST` | `/api/v1/credentials/{service}` | Save encrypted credentials |
| `DELETE` | `/api/v1/credentials/{service}` | Clear stored credentials |
| `POST` | `/api/v1/credentials/{service}/test` | Test connectivity |
| `POST` | `/api/v1/credentials/generate-key` | Generate new encryption key |

---

## 6. Authentication System

### Feature Flag

**Controlled by:** `AUTH_ENABLED` environment variable (default: `false`)

When disabled, the system runs in anonymous admin mode — `require_auth()` returns a synthetic payload:
```python
{"sub": "anonymous", "role": "admin", "email": "anonymous@localhost"}
```

### JWT Verification

**File:** `backend_api/auth/middleware.py`

- **Library:** `python-jose` (`jose.jwt.decode()`)
- **Algorithm:** HS256
- **Secret:** `SUPABASE_JWT_SECRET` environment variable
- **Audience verification:** Disabled (`verify_aud: False`)
- **Token source:** `Authorization: Bearer <token>` header

### FastAPI Dependencies

**File:** `backend_api/auth/dependencies.py`

| Dependency | Behavior (Auth Disabled) | Behavior (Auth Enabled) |
|------------|--------------------------|-------------------------|
| `get_current_user()` | Returns `None` | Decodes JWT, returns payload or `None` |
| `require_auth()` | Returns anonymous admin payload | Raises 401 if no/invalid token |
| `require_admin()` | Returns anonymous admin payload | Raises 403 if role != admin |

### Frontend Integration

- **State management:** Zustand store (`frontend/src/stores/authStore.ts`)
- **Auth provider:** Supabase JS SDK for client-side token management
- **Protected routes:** Components check auth state before rendering
- **API calls:** Bearer token automatically included in HTTP headers

---

## 7. Dataset Generation Pipeline

### End-to-End Flow

The dataset generation pipeline is triggered by `POST /api/v1/datasets/` and runs as a background job. Here is the step-by-step flow with file references:

```
User Request → API Router → Background Job → External APIs → Database → Export
```

#### Step 1: Dataset Creation

**File:** `backend_api/routers/datasets.py`

User sends `POST /api/v1/datasets/` with configuration:
```json
{
  "name": "LEO_Test_7Day",
  "regime": "LEO",
  "tier": "T2",
  "object_count": 5,
  "timeframe": 7,
  "satellites": [25544, 43013, ...],
  "downsampling": { "enabled": true, "target_gap": 2.0 },
  "simulation": { "enabled": false }
}
```

A `datasets` row is created with `status='generating'` and a job is submitted.

#### Step 2: Background Job Launch

**File:** `backend_api/jobs/workers.py:66-70`

```python
executor = get_executor()  # ThreadPoolExecutor(max_workers=4)
executor.submit(run_dataset_generation, job.id, dataset_id, config)
```

The job manager (`DbJobManager`) creates a `jobs` row and tracks progress 0-100.

#### Step 3: Credential Resolution

**File:** `backend_api/jobs/workers.py:97-106`

```python
cred_service = get_credential_service()
udl_token, _, _ = cred_service.resolve_or_raise("udl")
esa_token, _, _ = cred_service.resolve_or_raise("esa")
```

Falls back to `os.getenv("UDL_TOKEN")` and `os.getenv("ESA_TOKEN")` if DB credentials unavailable.

#### Step 4: Satellite Selection

**File:** `backend_api/jobs/workers.py:134-143`

If no satellites specified, auto-selects from default calibration list (`uct_benchmark/settings.py:satIDs`), shuffled and capped at `object_count`.

#### Step 5: Open Source Enrichment

**File:** `backend_api/jobs/workers.py:154-185`

Uses `DataSourceManager.enrich_satellites_batch()` (`uct_benchmark/api/data_source_manager.py`):
- Queries UCS database for purpose, operator, mass, power
- Queries GCAT catalog for launch site, COSPAR ID
- Computes area-to-mass ratio (`amr_m2_kg`) for each satellite
- Updates `satellites` table with enriched data
- Generates `EnrichmentReport` with counts

#### Step 6: HAMR Detection

**File:** `uct_benchmark/api/data_source_manager.py:34`

Objects with area-to-mass ratio > 0.1 m²/kg are flagged as High Area-to-Mass Ratio (HAMR) objects. The threshold is defined as `HAMR_AMR_THRESHOLD = 0.1` m²/kg. AMR is computed as:
```
amr = cross_section_m2 / mass_kg
```
If mass is unknown, a default cross-section of 1.0 m² is assumed.

#### Step 7: Observation Query

**File:** `uct_benchmark/api/apiIntegration.py`

The core observation retrieval uses several intelligent strategies:

- **QueryCache:** TTL 15 minutes, max 1000 entries, avoids duplicate API calls
- **Count-first strategy:** For large result sets (>5000), switches to chunked time windows
- **Regime-based batch sizing:**
  - LEO: 6-hour windows (fast-moving objects)
  - MEO: 12-hour windows
  - GEO: 24-hour windows (slow-moving objects)
  - HEO: 3-hour windows (highly variable)
- **Pagination fallback:** Standard paginated API queries when other strategies aren't applicable
- **Search strategy options:** `hybrid` (default), `windowed`, `paginated`

#### Step 8: Optional RF Data (SatNOGS)

**File:** `backend_api/jobs/workers.py:188-206`

For multi-phenomenology (MX) or RF-only datasets, fetches SatNOGS observations via `DataIngestionPipeline.ingest_rf_observations()`. These are stored with `observation_type='RF'` and `source_id=2`.

#### Step 9: Optional ILRS Validation Data

**File:** `backend_api/jobs/workers.py:209-227`

For T1/T1H tier datasets, fetches ILRS laser ranging validation data via `DataIngestionPipeline.ingest_validation_data()`. Stored in `validation_measurements` table.

#### Step 10: Downsampling

**File:** `uct_benchmark/data/dataManipulation.py`

When enabled, applies track-aware downsampling with regime-specific profiles:
- `target_coverage`: Fraction of orbital period to cover
- `target_gap`: Target gap between observations (hours)
- `max_obs_per_sat`: Cap on observations per satellite
- `preserve_tracks`: Maintains track integrity during downsampling

#### Step 11: Optional Simulation

**File:** `uct_benchmark/simulation/`

When enabled, adds simulated observations with noise models:
- Sensor model: GEODSS or custom
- Noise: Gaussian measurement noise on RA/Dec/range
- Atmospheric effects: Refraction and tropospheric delay
- `max_synthetic_ratio`: Caps synthetic observations at 50% of total

#### Step 12: Database Persistence

**File:** `backend_api/jobs/workers.py:339-403`

Three-phase persistence:
1. Update `datasets` row with `observation_count`, `satellite_count`, `avg_coverage`, set `status='available'`
2. Link observations via `DatasetRepository.add_observations_to_dataset()` — populates `dataset_observations` junction table with decorrelated `track_id` assignments
3. Add truth references via `DatasetRepository.add_references_to_dataset()` — populates `dataset_references` with satellite → state vector → element set mappings

#### Step 13: Export

**File:** `uct_benchmark/database/export.py`

Datasets can be exported to:
- **JSON:** Full observation data with metadata
- **Parquet:** Columnar format for efficient ML ingestion

Export paths stored in `datasets.json_path` and `datasets.parquet_path`.

#### Step 14: Job Completion

**File:** `backend_api/jobs/workers.py:430-443`

Job result includes:
```json
{
  "dataset_id": 42,
  "observation_count": 15000,
  "satellite_count": 5,
  "actual_satellites": [25544, 43013, ...],
  "performance": { ... },
  "sensor_mode": "EO",
  "validation_info": { ... }
}
```

Job status updated to `completed` with progress 100.

---

## 8. UCTP Lab — Complete Pipeline

### Architecture Overview

The UCTP Lab provides two entry points:

1. **CLI:** `run_uctp_lab.py` — direct command-line execution
2. **REST API:** `POST /api/v1/uctp/runs/` — background job execution

Both converge on `UCTPPipeline.run()` in `uct_benchmark/uctp_lab/pipeline.py`.

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Ingest  │───▶│ Cluster  │───▶│   IOD    │───▶│  Refine  │───▶│  Output  │
│          │    │ (DBSCAN) │    │ (Gauss)  │    │(BLS/EKF) │    │ (JSON)   │
└─────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### Configuration

**File:** `uct_benchmark/uctp_lab/config.py`

```python
@dataclass
class UCTPConfig:
    clustering: ClusteringConfig   # Method, eps, min_samples, time_weight
    iod: IODConfig                 # Method, min_obs, convergence_tol
    refinement: RefinementConfig   # Method, max_iterations
    name: str = "default"
    reference_frame: str = "J2000"
    dataset_id: Optional[int] = None
    input_path: Optional[str] = None
    output_path: Optional[str] = None
```

**Clustering methods:** `angular_dbscan`, `stonesoup_mht`, `stonesoup_gnn`
**IOD methods:** `gauss`, `orbdetpy_laplace`, `orekit_gooding`
**Refinement methods:** `none`, `batch_least_squares`, `ekf`, `ukf`

### Stage 1 — Ingest

**File:** `uct_benchmark/uctp_lab/ingest.py`

Three input sources:

| Source | Function | Description |
|--------|----------|-------------|
| JSON file | `load_observations_from_json()` | Loads from file path, supports list or `{"observations": [...]}` format |
| Database | `load_observations_from_database()` | Loads via `dataset_observations` junction table JOIN |
| DataFrame | `load_observations_from_dataframe()` | Normalizes existing DataFrame |

All sources converge through `_normalize_columns()` which:
- Renames columns: `obTime` → `ob_time`, `satNo` → `sat_no`, etc.
- Validates required columns: `id`, `ob_time`, `ra`, `declination`
- Parses timestamps to UTC datetime
- Coerces coordinates to numeric, drops NaN rows
- Sorts by `ob_time`

### Stage 2 — Clustering

**File:** `uct_benchmark/uctp_lab/clustering/angular_clustering.py`

`AngularDBSCANClusterer` implements `AbstractClusterer` and performs:

1. **Feature construction** (`_build_features()`):
   - Convert RA/Dec to unit direction vectors: `(ux, uy, uz)` via `radec_to_unit_vector()`
   - Normalize time to [0, 1] range scaled by `time_weight` (default 0.1)
   - Compute angular rates via finite difference of great-circle distances
   - Scale rates by `rate_weight` (default 0.05)

   **Feature vector per observation:** `[ux, uy, uz, time_norm, angular_rate_norm]`

2. **Feature scaling:** `StandardScaler` from scikit-learn (zero mean, unit variance)

3. **DBSCAN execution:**
   ```python
   DBSCAN(eps=config.eps_deg, min_samples=config.min_samples, metric="euclidean")
   ```
   Default: `eps=0.5°`, `min_samples=3`

4. **Output:** `Dict[cluster_id → List[observation_id]]` where `-1` denotes noise

### Stage 3 — IOD (Initial Orbit Determination)

**File:** `uct_benchmark/uctp_lab/iod/gauss_iod.py`

`GaussIOD` implements `AbstractIOD` with two modes:

**Full Gauss mode** (sensor location available — `senlon`, `senlat`, `senalt` columns):
- Delegates to `uct_benchmark/simulation/gauss.py:gauss()`
- Uses three or more observations with sensor positions
- Applies state culling (`cullStates()`) to remove outlier solutions
- Returns best state vector `[x, y, z, vx, vy, vz]` with epoch and iteration count

**Simplified Gauss mode** (no sensor data):
- Selects three observations: first, middle, last
- Converts RA/Dec to line-of-sight unit vectors
- Assumes circular orbit at ~7000 km altitude
- Estimates position: `r_vec = los_middle * 7000`
- Estimates velocity via finite difference: `v_vec = (r_last - r_first) / dt_total`
- Returns `IODResult` with `method="gauss_simplified"`

**IOD output:** `IODResult(state=[x,y,z,vx,vy,vz], epoch, observation_ids, method, iterations, covariance)`

### Stage 4 — Refinement

**File:** `uct_benchmark/uctp_lab/refinement/`

Four options, selected via `RefinementConfig.method`:

| Method | File | Description |
|--------|------|-------------|
| `none` | — | Skip refinement (default) |
| `batch_least_squares` | `least_squares.py` | Iterative batch least squares using full observation set |
| `ekf` | `kalman_filter.py` | Extended Kalman Filter with configurable process noise |
| `ukf` | `kalman_filter.py` | Unscented Kalman Filter |

Process noise defaults: position 0.01 km, velocity 0.001 km/s.

Each refiner takes an `IODResult` and returns a refined `IODResult` with updated state, covariance, and iteration count.

### Stage 5 — Output

**File:** `uct_benchmark/uctp_lab/output.py`

`build_output()` formats resolved clusters into UCTP JSON format:

```json
{
  "idStateVector": 0,
  "sourcedData": ["obs_id_1", "obs_id_2", ...],
  "epoch": "2025-01-01T00:00:00",
  "xpos": 6778.0, "ypos": 0.0, "zpos": 0.0,
  "xvel": 0.0, "yvel": 7.5, "zvel": 0.0,
  "cov": [1.0, 0.0, ...],
  "uct": true,
  "referenceFrame": "J2000"
}
```

`save_output()` writes to file and returns the absolute path.

### Pipeline Metrics

**Dataclass:** `PipelineMetrics` in `pipeline.py:37-59`

| Metric | Description |
|--------|-------------|
| `total_observations` | Total input observations |
| `clusters_found` | Non-noise clusters from DBSCAN |
| `noise_observations` | Observations labeled as noise (-1) |
| `iod_attempted` | Number of clusters IOD was attempted on |
| `iod_succeeded` | Number of successful IOD results |
| `refinement_attempted` | Number of refinement attempts |
| `refinement_succeeded` | Number of successful refinements |
| `objects_resolved` | Final resolved objects with state vectors |
| `elapsed_seconds` | Total pipeline execution time |

Metrics are stored in `uctp_runs` table when run via the API.

---

## 9. ML Training System

### Model Types

**File:** `uct_benchmark/uctp_lab/ml/models.py`

#### ClusteringMLP

Purpose: Embed observations into a latent space where same-object observations cluster together.

```
Input(7) → FC(64) → ReLU → Dropout(0.1) → FC(32) → ReLU → FC(embed_dim) → L2 Normalize
```

- Input features: `[ra_norm, dec_norm, ux, uy, uz, time_norm, angular_rate]`
- Output: L2-normalized embedding vector (default `embed_dim=16`)
- Training: Contrastive or triplet loss

#### PropagationLSTM

Purpose: Predict the next state vector from a sequence of previous states.

```
LSTM(input=6, hidden=64, layers=2, dropout=0.1) → FC(6)
```

- Input: Sliding window of `[x, y, z, vx, vy, vz]` (normalized by [10000, 10000, 10000, 10, 10, 10])
- Output: Next state vector `[x, y, z, vx, vy, vz]`
- Uses last LSTM hidden state for prediction

### Feature Preparation

**File:** `uct_benchmark/uctp_lab/ml/dataset_prep.py`

#### `prepare_clustering_features()`

Builds feature matrix for clustering model:

| Feature Index | Name | Computation |
|---------------|------|-------------|
| 0 | `ra_norm` | `ra / 360.0` |
| 1 | `dec_norm` | `(dec + 90.0) / 180.0` |
| 2 | `ux` | `cos(dec_rad) * cos(ra_rad)` |
| 3 | `uy` | `cos(dec_rad) * sin(ra_rad)` |
| 4 | `uz` | `sin(dec_rad)` |
| 5 | `time_norm` | Seconds from first observation, normalized to [0, 1] |
| 6 | `angular_rate` | Finite-difference angular rate |

Returns: `(features: ndarray[N, 7], labels: ndarray[N] or None)`

#### `prepare_propagation_features()`

Builds sliding-window input/target pairs:

- Input: `(N, window_size, 6)` — sequences of state vectors
- Target: `(N, 6)` — next state vector
- Normalization: Position / 10000 km, velocity / 10 km/s

### Training Loop

**File:** `uct_benchmark/uctp_lab/ml/trainer.py`

```python
def train_model(model, features, targets, config, progress_callback=None):
```

**Configuration** (`TrainingConfig`):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `epochs` | 50 | Maximum training epochs |
| `batch_size` | 32 | Mini-batch size |
| `learning_rate` | 1e-3 | Adam optimizer learning rate |
| `weight_decay` | 1e-5 | L2 regularization |
| `early_stopping_patience` | 10 | Epochs without improvement before stopping |
| `validation_split` | 0.2 | Fraction held out for validation |
| `seed` | 42 | Random seed for reproducibility |

**Training procedure:**

1. Convert features/targets to PyTorch tensors
2. Determine loss function:
   - Integer targets → `CrossEntropyLoss` (classification)
   - Float targets → `MSELoss` (regression)
3. Random 80/20 train/val split (seeded)
4. Create `DataLoader` instances with shuffling
5. Initialize `Adam` optimizer
6. For each epoch:
   - Train phase: forward → loss → backward → step
   - Validation phase: forward → loss (no gradient)
   - Early stopping check: save best model state, increment patience counter
7. Restore best model weights
8. Return `TrainingResult` with loss histories

**Results stored in `uctp_models`:**
- `training_epochs`: Total epochs (may be less than max due to early stopping)
- `training_loss`: Final training loss
- `validation_loss`: Final validation loss
- `best_f1_score`: Best F1 during evaluation (if computed)
- `model_path`: File path to serialized model state dict

**Model versioning:** Auto-incremented per model name (e.g., `clustering_v1`, `clustering_v2`).

---

## 10. Evaluation & Leaderboard

### Evaluation Pipeline

**Trigger:** Submission upload via `POST /api/v1/submissions/` with a UCTP output JSON file.

**Worker:** `run_evaluation_pipeline()` in `backend_api/jobs/workers.py:471-644`

**Steps:**

1. **Load submission file** — parse JSON UCTP output with predicted state vectors
2. **Load reference data** — query `observations` via `dataset_observations` for the target dataset
3. **Orbit association** — `orbitAssociation()` matches predicted objects to truth objects
4. **Binary metrics** — `binaryMetrics()` computes:
   - True Positives (TP): Correctly matched objects
   - False Positives (FP): Predicted objects with no truth match
   - False Negatives (FN): Truth objects with no prediction match
   - Precision = TP / (TP + FP)
   - Recall = TP / (TP + FN)
   - F1 Score = 2 * (Precision * Recall) / (Precision + Recall)
5. **State metrics** — `stateMetrics()` computes for true positive matches:
   - Position RMS (km)
   - Velocity RMS (km/s)
   - Mahalanobis distance (statistical consistency)
6. **Residual metrics** — RA/Dec residuals in arcseconds
7. **Persist results** — INSERT into `submission_results` table
8. **Update submission** — SET `status='completed'`, `completed_at=NOW()`

### Leaderboard

**Router:** `backend_api/routers/leaderboard.py`

Leaderboard queries join `submissions` → `submission_results` → `datasets`:
- **Ranked by:** `f1_score DESC`
- **Filterable by:** `orbital_regime`, `tier`, `dataset_id`
- **Fields shown:** algorithm name, version, F1, precision, recall, position RMS, velocity RMS, submission date

**History and statistics endpoints** enable trend analysis across submissions.

---

## 11. Audit & Monitoring (PostgreSQL Only)

All audit functionality is conditional on `DB_BACKEND=postgres`. When using DuckDB, audit functions return immediately without side effects.

### AuditMiddleware

**File:** `backend_api/middleware/audit.py`

- Captures **POST, PUT, PATCH, DELETE** requests only (mutation methods)
- Records: user_id (from JWT), method, path, status_code, request_body_size, duration_ms, IP, user-agent
- Persists to `api_call_log` table via `audit_service.log_api_call()`
- **Exception swallowing:** Audit logging never breaks the request (`try/except` with `logger.warning`)

### QueryLoggingMiddleware

**File:** `backend_api/middleware/query_logging.py`

- Monitors all HTTP requests (not just mutations)
- Logs requests exceeding `SLOW_THRESHOLD_MS = 500` milliseconds
- Persists to `system_log` table via `audit_service.log_system_event()` with level `WARNING`
- Only active when `DB_BACKEND=postgres`

### Audit Service Functions

**File:** `backend_api/services/audit_service.py`

| Function | Target Table | Parameters |
|----------|-------------|------------|
| `log_audit_event()` | `audit_log` | user_id, action, resource_type, resource_id, details, ip, user_agent |
| `log_api_call()` | `api_call_log` | user_id, method, path, status_code, sizes, duration_ms, ip, user_agent |
| `log_credential_access()` | `credential_access_log` | user_id, service_name, action (resolve/save/delete), source, success, ip |
| `log_system_event()` | `system_log` | level, component, message, details |

**All functions:**
- Check `_is_postgres()` first; return immediately for DuckDB
- Swallow all exceptions (logging must never break requests)
- Log failures at `DEBUG` level via loguru

### Middleware Registration

**File:** `backend_api/main.py:122-130`

```python
if _get_audit_config().db_backend == DatabaseBackend.POSTGRES:
    app.add_middleware(AuditMiddleware)
```

`QueryLoggingMiddleware` checks the backend at request time.

---

## 12. Data Flow Diagrams

### 12.1 Dataset Generation Flow

```
┌──────┐   POST /datasets/    ┌─────────┐  submit()   ┌────────────────┐
│ User │──────────────────────▶│ Datasets │────────────▶│ ThreadPool     │
│      │                      │ Router   │             │ Executor       │
└──────┘                      └─────────┘             │ (4 workers)    │
                                   │                   └───────┬────────┘
                              INSERT INTO                      │
                              datasets                         │
                              (status=generating)              ▼
                                                    ┌──────────────────┐
                                                    │ run_dataset_gen()│
                                                    │                  │
                                                    │ 1. Resolve creds │
                                                    │ 2. Select sats   │
                                                    │ 3. Enrich (UCS/  │
                                                    │    GCAT)         │
                                                    │ 4. Query UDL obs │
                                                    │ 5. SatNOGS RF?  │
                                                    │ 6. ILRS valid?  │
                                                    │ 7. Downsample?  │
                                                    │ 8. Simulate?    │
                                                    └────────┬─────────┘
                                                             │
                                                             ▼
                                               ┌──────────────────────┐
                                               │ Database Persistence │
                                               │                      │
                                               │ UPDATE datasets      │
                                               │ INSERT dataset_obs   │
                                               │ INSERT dataset_refs  │
                                               │ status='available'   │
                                               └──────────────────────┘
```

### 12.2 UCTP Pipeline Flow

```
┌──────────┐    ┌─────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐
│  Ingest   │───▶│ Cluster │───▶│    IOD    │───▶│  Refine  │───▶│  Output  │
│           │    │         │    │           │    │          │    │          │
│ JSON/DB/  │    │ Angular │    │ Per-      │    │ Optional │    │ Format   │
│ DataFrame │    │ DBSCAN  │    │ cluster   │    │ BLS/EKF/ │    │ to UCTP  │
│           │    │         │    │ Gauss IOD │    │ UKF      │    │ JSON     │
│ Normalize │    │ Feature │    │           │    │          │    │          │
│ columns,  │    │ build + │    │ Full or   │    │ Iterate  │    │ Save to  │
│ sort by   │    │ scale + │    │ simplified│    │ until    │    │ file +   │
│ time      │    │ DBSCAN  │    │           │    │ converge │    │ uctp_runs│
└──────────┘    └─────────┘    └───────────┘    └──────────┘    └──────────┘
     │               │               │                │               │
     ▼               ▼               ▼                ▼               ▼
 DataFrame     Dict[cluster_id   IODResult       IODResult      List[Dict]
               → obs_ids]        per cluster     (refined)      UCTP format
```

### 12.3 ML Training Flow

```
┌───────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Datasets  │──▶│ Feature Prep  │──▶│ PyTorch      │──▶│ uctp_models  │
│  (from DB) │    │               │    │ Training     │    │  (DB table)  │
│            │    │ Clustering:   │    │              │    │              │
│ dataset_ids│    │  7-dim vector │    │ Adam optim   │    │ model_path   │
│            │    │               │    │ Early stop   │    │ train_loss   │
│            │    │ Propagation:  │    │ 80/20 split  │    │ val_loss     │
│            │    │  sliding      │    │ CE or MSE    │    │ best_f1      │
│            │    │  windows of 6 │    │              │    │ version      │
└───────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 12.4 Submission Evaluation Flow

```
┌──────┐  POST /submissions/   ┌────────────┐  submit()  ┌─────────────────┐
│ User │──────────────────────▶│ Submissions│──────────▶│ ThreadPool       │
│      │  + UCTP JSON file     │ Router     │           │ run_evaluation() │
└──────┘                       └────────────┘           └────────┬──────────┘
                                                                 │
                                                                 ▼
                                                    ┌──────────────────────┐
                                                    │  1. Load submission  │
                                                    │  2. Load truth from  │
                                                    │     dataset_obs      │
                                                    │  3. orbitAssociation │
                                                    │  4. binaryMetrics    │
                                                    │     (TP/FP/FN/P/R/F1)│
                                                    │  5. stateMetrics     │
                                                    │     (pos/vel RMS)    │
                                                    │  6. INSERT INTO      │
                                                    │     submission_results│
                                                    │  7. UPDATE submission │
                                                    │     status=completed │
                                                    └──────────────────────┘
                                                                 │
                                                                 ▼
                                                    ┌──────────────────────┐
                                                    │  Leaderboard         │
                                                    │  (ranked by F1 DESC) │
                                                    └──────────────────────┘
```

### 12.5 Credential Resolution Flow

```
resolve("udl")
     │
     ├─ 1. Query DB: SELECT encrypted_primary FROM credentials
     │       WHERE service_name = 'udl' AND is_configured = TRUE
     │
     │   Found + encryption available?
     │   ├─ YES → Fernet.decrypt(encrypted_primary) → return ("token", None, "database")
     │   └─ NO  ↓
     │
     ├─ 2. Query ENV: os.environ.get("UDL_TOKEN")
     │
     │   Found?
     │   ├─ YES → return ("token_from_env", None, "environment")
     │   └─ NO  ↓
     │
     └─ 3. return (None, None, "none")
```

---

## 13. Foreign Key Relationships

### Complete Relationship Map

DuckDB enforces these at the application level. PostgreSQL enforces them with database constraints (defined in `001_initial_schema.sql:700-782`).

```
users
  ├── datasets.created_by → users.id
  ├── submissions.created_by → users.id
  ├── uctp_runs.created_by → users.id
  ├── audit_log.user_id → users.id
  ├── api_call_log.user_id → users.id
  ├── query_log.user_id → users.id
  └── credential_access_log.user_id → users.id

satellites
  ├── observations.sat_no → satellites.sat_no (application-enforced)
  ├── state_vectors.sat_no → satellites.sat_no
  ├── element_sets.sat_no → satellites.sat_no
  ├── dataset_references.sat_no → satellites.sat_no
  ├── events.primary_sat_no → satellites.sat_no
  └── events.secondary_sat_no → satellites.sat_no

data_sources
  └── observations.source_id → data_sources.id

datasets
  ├── datasets.parent_id → datasets.id (self-referential versioning)
  ├── dataset_observations.dataset_id → datasets.id
  ├── dataset_references.dataset_id → datasets.id
  ├── submissions.dataset_id → datasets.id
  └── uctp_runs.dataset_id → datasets.id

observations
  ├── dataset_observations.observation_id → observations.id
  └── event_observations.observation_id → observations.id

state_vectors
  └── dataset_references.state_vector_id → state_vectors.id

element_sets
  └── dataset_references.element_set_id → element_sets.id

event_types
  └── events.event_type_id → event_types.id

events
  └── event_observations.event_id → events.id

jobs
  └── submissions.job_id → jobs.id

submissions
  └── submission_results.submission_id → submissions.id (UNIQUE)
```

### PostgreSQL Constraint Names

| Constraint | Table | FK Column(s) | Referenced |
|------------|-------|--------------|------------|
| `fk_obs_source` | observations | source_id | data_sources(id) |
| `fk_sv_satellite` | state_vectors | sat_no | satellites(sat_no) |
| `fk_elset_satellite` | element_sets | sat_no | satellites(sat_no) |
| `fk_datasets_parent` | datasets | parent_id | datasets(id) |
| `fk_datasets_created_by` | datasets | created_by | users(id) |
| `fk_dsobs_dataset` | dataset_observations | dataset_id | datasets(id) |
| `fk_dsobs_observation` | dataset_observations | observation_id | observations(id) |
| `fk_dsref_dataset` | dataset_references | dataset_id | datasets(id) |
| `fk_dsref_satellite` | dataset_references | sat_no | satellites(sat_no) |
| `fk_dsref_sv` | dataset_references | state_vector_id | state_vectors(id) |
| `fk_dsref_elset` | dataset_references | element_set_id | element_sets(id) |
| `fk_sub_dataset` | submissions | dataset_id | datasets(id) |
| `fk_sub_job` | submissions | job_id | jobs(id) |
| `fk_sub_created_by` | submissions | created_by | users(id) |
| `fk_subres_submission` | submission_results | submission_id | submissions(id) |
| `fk_event_type` | events | event_type_id | event_types(id) |
| `fk_event_primary` | events | primary_sat_no | satellites(sat_no) |
| `fk_event_secondary` | events | secondary_sat_no | satellites(sat_no) |
| `fk_evobs_event` | event_observations | event_id | events(id) |
| `fk_evobs_observation` | event_observations | observation_id | observations(id) |
| `fk_uctp_run_dataset` | uctp_runs | dataset_id | datasets(id) |
| `fk_uctp_run_created_by` | uctp_runs | created_by | users(id) |
| `fk_audit_user` | audit_log | user_id | users(id) |
| `fk_apicall_user` | api_call_log | user_id | users(id) |
| `fk_query_user` | query_log | user_id | users(id) |
| `fk_credaccess_user` | credential_access_log | user_id | users(id) |

---

## 14. Configuration Reference

### Environment Variables

| Variable | Default | When Needed | Description |
|----------|---------|-------------|-------------|
| `DB_BACKEND` | `duckdb` | Always | Database backend: `duckdb` or `postgres` |
| `DATABASE_PATH` | `data/database/uct_benchmark.duckdb` | DuckDB | Path to DuckDB file |
| `DATABASE_URL` | — | PostgreSQL | PostgreSQL connection URL |
| `SUPABASE_DB_URL` | — | PostgreSQL | Alternative to DATABASE_URL |
| `SUPABASE_URL` | — | PostgreSQL + Auth | Supabase project URL |
| `SUPABASE_ANON_KEY` | — | Frontend auth | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | — | Backend auth | Supabase service role key |
| `SUPABASE_JWT_SECRET` | — | Auth enabled | JWT verification secret (HS256) |
| `AUTH_ENABLED` | `false` | Auth | Enable JWT authentication |
| `CREDENTIAL_ENCRYPTION_KEY` | — | DB credentials | Fernet encryption key |
| `UDL_TOKEN` | — | Dataset generation | UDL API Bearer token |
| `ESA_TOKEN` | — | Dataset generation | ESA DiscoSweb Bearer token |
| `NASA_EARTHDATA_TOKEN` | — | ILRS validation | NASA Earthdata JWT |
| `SPACETRACK_USER` | — | Space-Track access | Space-Track.org username |
| `SPACETRACK_PASS` | — | Space-Track access | Space-Track.org password |
| `OREKIT_DATA_PATH` | `./orekit-data-main` | Orbit propagation | Path to Orekit data directory |
| `PG_POOL_MIN` | `2` | PostgreSQL | Min pool connections |
| `PG_POOL_MAX` | `10` | PostgreSQL | Max pool connections |
| `CORS_ORIGINS` | `localhost:3000,localhost:5173` | API | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Always | Logging level |
| `API_PORT` | `8000` | API server | FastAPI server port |

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (credentials, backend selection) |
| `.env.example` | Template with all configurable variables |
| `backend_api/config.py` | `AppConfig` dataclass, `get_config()` singleton |
| `uct_benchmark/settings.py` | Global settings (DATA_DIR, default satellite IDs) |
| `uct_benchmark/logging_config.py` | Loguru configuration |
| `uct_benchmark/uctp_lab/config.py` | `UCTPConfig` pipeline configuration dataclasses |
| `frontend/vite.config.ts` | Vite build/dev server configuration |
| `frontend/tsconfig.json` | TypeScript compiler options |
| `pyproject.toml` | Python project metadata and dependencies |

### API Route Summary

| Prefix | Router File | Description |
|--------|-------------|-------------|
| `/api/v1/datasets` | `routers/datasets.py` | Dataset CRUD + generation |
| `/api/v1/submissions` | `routers/submissions.py` | Algorithm submission upload |
| `/api/v1/results` | `routers/results.py` | Evaluation result retrieval |
| `/api/v1/leaderboard` | `routers/leaderboard.py` | Rankings by F1 score |
| `/api/v1/jobs` | `routers/jobs.py` | Background job status |
| `/api/v1/uctp` | `routers/uctp.py` | UCTP Lab pipeline execution |
| `/api/v1/credentials` | `routers/credentials.py` | Credential CRUD + test |
| `/api/v1/auth` | `routers/auth.py` | Authentication endpoints |
| `/` | `main.py` | Health check |
| `/health` | `main.py` | Detailed health check |

---

## Source File Index

| File | Lines | Purpose |
|------|-------|---------|
| `uct_benchmark/database/schema.sql` | 292 | DuckDB table definitions (v1.0.0) |
| `backend_api/db/migrations/001_initial_schema.sql` | 895 | PostgreSQL schema (v2.0.0) + FKs + RLS + seed data |
| `uct_benchmark/database/backend_interface.py` | 134 | Abstract backend + QueryResult wrapper |
| `uct_benchmark/database/duckdb_backend.py` | 147 | DuckDB thread-local implementation |
| `uct_benchmark/database/postgres_backend.py` | 212 | PostgreSQL psycopg3 pool implementation |
| `uct_benchmark/database/connection.py` | 412 | DatabaseManager with 6 lazy-loaded repositories |
| `uct_benchmark/database/repository.py` | 1618 | 6 repository classes (Satellite, Observation, StateVector, ElementSet, Dataset, Event) |
| `uct_benchmark/api/apiIntegration.py` | ~2600 | Core dataset generation (UDL/ESA queries) |
| `uct_benchmark/api/open_sources.py` | ~600 | SatNOGS, GCAT, ILRS, UCS connectors |
| `uct_benchmark/api/data_source_manager.py` | ~300 | Satellite enrichment orchestrator |
| `uct_benchmark/uctp_lab/pipeline.py` | 325 | UCTP pipeline orchestrator |
| `uct_benchmark/uctp_lab/config.py` | 177 | Pipeline configuration dataclasses |
| `uct_benchmark/uctp_lab/ingest.py` | 151 | Observation data ingestion |
| `uct_benchmark/uctp_lab/output.py` | 126 | UCTP JSON output formatting |
| `uct_benchmark/uctp_lab/clustering/angular_clustering.py` | 123 | Angular DBSCAN implementation |
| `uct_benchmark/uctp_lab/iod/gauss_iod.py` | 169 | Gauss IOD (full + simplified) |
| `uct_benchmark/uctp_lab/ml/models.py` | 132 | ClusteringMLP + PropagationLSTM |
| `uct_benchmark/uctp_lab/ml/trainer.py` | 176 | PyTorch training loop |
| `uct_benchmark/uctp_lab/ml/dataset_prep.py` | 143 | ML feature preparation |
| `backend_api/main.py` | 166 | FastAPI app, middleware, router registration |
| `backend_api/config.py` | 81 | Centralized AppConfig dataclass |
| `backend_api/services/credential_service.py` | 323 | Fernet encryption + resolution chain |
| `backend_api/services/audit_service.py` | 197 | Audit logging (4 functions, exception-safe) |
| `backend_api/auth/middleware.py` | 31 | JWT verification (python-jose, HS256) |
| `backend_api/auth/dependencies.py` | 104 | FastAPI auth dependencies (3 levels) |
| `backend_api/middleware/audit.py` | 89 | AuditMiddleware (mutation logging) |
| `backend_api/middleware/query_logging.py` | 49 | QueryLoggingMiddleware (slow request detection) |
| `backend_api/jobs/workers.py` | 703 | Background workers (dataset gen + evaluation) |
