# UCT Benchmark Database - Entity Relationship Diagram

## ERD (Mermaid)

```mermaid
erDiagram
    %% Core Entities
    satellites {
        INTEGER sat_no PK
        VARCHAR name
        VARCHAR cospar_id
        VARCHAR object_type
        DATE launch_date
        DATE decay_date
        DECIMAL mass_kg
        DECIMAL cross_section_m2
        DECIMAL drag_coeff
        DECIMAL srp_coeff
        VARCHAR orbital_regime
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    observations {
        VARCHAR id PK
        INTEGER sat_no FK
        TIMESTAMP ob_time
        DECIMAL ra
        DECIMAL declination
        DECIMAL range_km
        DECIMAL range_rate_km_s
        DECIMAL azimuth
        DECIMAL elevation
        VARCHAR sensor_name
        VARCHAR data_mode
        VARCHAR track_id
        BOOLEAN is_uct
        BOOLEAN is_simulated
        TIMESTAMP created_at
    }

    state_vectors {
        INTEGER id PK
        INTEGER sat_no FK
        TIMESTAMP epoch
        DECIMAL x_pos
        DECIMAL y_pos
        DECIMAL z_pos
        DECIMAL x_vel
        DECIMAL y_vel
        DECIMAL z_vel
        JSON covariance
        VARCHAR source
        VARCHAR data_mode
        TIMESTAMP created_at
    }

    element_sets {
        INTEGER id PK
        INTEGER sat_no FK
        VARCHAR line1
        VARCHAR line2
        TIMESTAMP epoch
        DECIMAL inclination
        DECIMAL raan
        DECIMAL eccentricity
        DECIMAL arg_perigee
        DECIMAL mean_anomaly
        DECIMAL mean_motion
        DECIMAL b_star
        DECIMAL semi_major_axis_km
        DECIMAL period_minutes
        VARCHAR source
        TIMESTAMP created_at
    }

    %% Dataset Entities
    datasets {
        INTEGER id PK
        VARCHAR name
        VARCHAR code
        INTEGER version
        INTEGER parent_id FK
        VARCHAR tier
        VARCHAR orbital_regime
        TIMESTAMP time_window_start
        TIMESTAMP time_window_end
        INTEGER observation_count
        INTEGER satellite_count
        DECIMAL avg_coverage
        DECIMAL avg_obs_count
        DECIMAL max_track_gap
        JSON generation_params
        VARCHAR status
        TIMESTAMP created_at
        TIMESTAMP updated_at
        VARCHAR json_path
        VARCHAR parquet_path
    }

    dataset_observations {
        INTEGER dataset_id FK
        VARCHAR observation_id FK
        INTEGER assigned_track_id
        INTEGER assigned_object_id
    }

    dataset_references {
        INTEGER dataset_id FK
        INTEGER sat_no FK
        INTEGER state_vector_id FK
        INTEGER element_set_id FK
        JSON grouped_obs_ids
    }

    %% Event Entities
    event_types {
        INTEGER id PK
        VARCHAR name
        VARCHAR description
    }

    events {
        INTEGER id PK
        INTEGER event_type_id FK
        TIMESTAMP event_time_start
        TIMESTAMP event_time_end
        INTEGER primary_sat_no FK
        INTEGER secondary_sat_no FK
        DECIMAL confidence
        VARCHAR detection_method
        VARCHAR source
        VARCHAR external_id
        VARCHAR labelled_by
        TIMESTAMP labelled_at
        VARCHAR notes
    }

    event_observations {
        INTEGER event_id FK
        VARCHAR observation_id FK
    }

    %% Submission & Evaluation Entities
    submissions {
        INTEGER id PK
        INTEGER dataset_id FK
        VARCHAR algorithm_name
        VARCHAR version
        VARCHAR description
        VARCHAR file_path
        VARCHAR status
        VARCHAR job_id FK
        VARCHAR error_message
        TIMESTAMP created_at
        TIMESTAMP completed_at
    }

    submission_results {
        INTEGER id PK
        INTEGER submission_id FK
        INTEGER true_positives
        INTEGER false_positives
        INTEGER false_negatives
        DECIMAL precision
        DECIMAL recall
        DECIMAL f1_score
        DECIMAL position_rms_km
        DECIMAL velocity_rms_km_s
        DECIMAL mahalanobis_distance
        DECIMAL ra_residual_rms_arcsec
        DECIMAL dec_residual_rms_arcsec
        JSON raw_results
        DECIMAL processing_time_seconds
        TIMESTAMP created_at
    }

    jobs {
        VARCHAR id PK
        VARCHAR job_type
        VARCHAR status
        INTEGER progress
        JSON result
        VARCHAR error
        JSON metadata
        TIMESTAMP created_at
        TIMESTAMP started_at
        TIMESTAMP completed_at
    }

    _schema_metadata {
        VARCHAR key PK
        VARCHAR value
        TIMESTAMP updated_at
    }

    %% Relationships
    satellites ||--o{ observations : "has"
    satellites ||--o{ state_vectors : "has"
    satellites ||--o{ element_sets : "has"
    satellites ||--o{ events : "primary_sat"
    satellites ||--o{ events : "secondary_sat"

    datasets ||--o{ dataset_observations : "contains"
    datasets ||--o{ dataset_references : "references"
    datasets ||--o| datasets : "parent_of"
    datasets ||--o{ submissions : "evaluated_by"

    observations ||--o{ dataset_observations : "included_in"
    observations ||--o{ event_observations : "linked_to"

    state_vectors ||--o{ dataset_references : "referenced_by"
    element_sets ||--o{ dataset_references : "referenced_by"

    event_types ||--o{ events : "categorizes"
    events ||--o{ event_observations : "has"

    submissions ||--o| submission_results : "produces"
    jobs ||--o{ submissions : "processes"
```

## Table Descriptions

### Core Entities

| Table | Description |
|-------|-------------|
| **satellites** | Catalog of space objects (satellites, debris) with physical and orbital properties |
| **observations** | Individual sensor measurements (angular, range, radar) of satellites |
| **state_vectors** | Position/velocity vectors in Cartesian coordinates at specific epochs |
| **element_sets** | Two-Line Element (TLE) sets with Keplerian orbital elements |

### Dataset Management

| Table | Description |
|-------|-------------|
| **datasets** | Benchmark datasets with configurable difficulty tiers and time windows |
| **dataset_observations** | Junction table linking observations to datasets with track assignments |
| **dataset_references** | Ground truth references linking datasets to satellites and their states |

### Event Tracking

| Table | Description |
|-------|-------------|
| **event_types** | Categorization of space events (maneuvers, conjunctions, fragmentations) |
| **events** | Detected or labeled space events with confidence scores |
| **event_observations** | Junction table linking observations to events |

### Evaluation & Jobs

| Table | Description |
|-------|-------------|
| **submissions** | Algorithm submissions for benchmark evaluation |
| **submission_results** | Evaluation metrics (precision, recall, F1, residuals) for submissions |
| **jobs** | Async job tracking for long-running operations |

### System

| Table | Description |
|-------|-------------|
| **_schema_metadata** | Database schema versioning and configuration |

## Key Relationships

1. **Satellites → Observations**: One satellite can have many observations over time
2. **Satellites → State Vectors**: Multiple state solutions per satellite at different epochs
3. **Satellites → Element Sets**: Multiple TLE sets per satellite (updated periodically)
4. **Datasets → Observations**: Many-to-many via `dataset_observations` junction table
5. **Datasets → Reference Data**: Links to ground truth states via `dataset_references`
6. **Events → Observations**: Many-to-many via `event_observations` junction table
7. **Submissions → Results**: One-to-one evaluation results per submission
8. **Jobs → Submissions**: Jobs process submission evaluations asynchronously
