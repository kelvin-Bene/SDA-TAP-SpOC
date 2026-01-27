"""
Pydantic models for the UCTP Lab API.

Defines request/response schemas for algorithm runs, ML models,
and API connectivity testing.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# ENUMS
# ============================================================


class UCTPRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class UCTPModelStatus(str, Enum):
    TRAINING = "training"
    READY = "ready"
    ARCHIVED = "archived"


class UCTPModelType(str, Enum):
    CLUSTERING_NN = "clustering_nn"
    PROPAGATION_ML = "propagation_ml"
    HYBRID = "hybrid"


class ConnectivityStatus(str, Enum):
    CONNECTED = "connected"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNAUTHORIZED = "unauthorized"
    NOT_INSTALLED = "not_installed"


class ClusteringMethodEnum(str, Enum):
    ANGULAR_DBSCAN = "angular_dbscan"
    STONESOUP_MHT = "stonesoup_mht"
    STONESOUP_GNN = "stonesoup_gnn"


class IODMethodEnum(str, Enum):
    GAUSS = "gauss"
    ORBDETPY_LAPLACE = "orbdetpy_laplace"
    OREKIT_GOODING = "orekit_gooding"


class RefinementMethodEnum(str, Enum):
    NONE = "none"
    BATCH_LEAST_SQUARES = "batch_least_squares"
    EKF = "ekf"
    UKF = "ukf"


# ============================================================
# ALGORITHM RUN MODELS
# ============================================================


class ClusteringConfigRequest(BaseModel):
    method: ClusteringMethodEnum = ClusteringMethodEnum.ANGULAR_DBSCAN
    eps_deg: float = Field(default=0.5, ge=0.01, le=10.0)
    min_samples: int = Field(default=3, ge=2, le=50)
    time_weight: float = Field(default=0.1, ge=0.0, le=1.0)
    max_time_gap_hours: float = Field(default=24.0, ge=0.1, le=168.0)
    use_angular_rate: bool = True
    rate_weight: float = Field(default=0.05, ge=0.0, le=1.0)


class IODConfigRequest(BaseModel):
    method: IODMethodEnum = IODMethodEnum.GAUSS
    min_observations: int = Field(default=3, ge=3, le=20)
    angular_separation_lower_deg: float = Field(default=1.0, ge=0.1, le=10.0)
    angular_separation_upper_deg: float = Field(default=30.0, ge=5.0, le=90.0)
    max_iterations: int = Field(default=100, ge=10, le=1000)
    convergence_tol: float = Field(default=1e-5, ge=1e-10, le=1e-1)
    cull_states: bool = True
    cull_sigma: float = Field(default=0.25, ge=0.1, le=3.0)


class RefinementConfigRequest(BaseModel):
    method: RefinementMethodEnum = RefinementMethodEnum.NONE
    max_iterations: int = Field(default=50, ge=1, le=500)
    convergence_tol: float = Field(default=1e-8, ge=1e-12, le=1e-3)
    process_noise_pos_km: float = Field(default=0.01, ge=0.0, le=10.0)
    process_noise_vel_km_s: float = Field(default=0.001, ge=0.0, le=1.0)


class UCTPRunCreate(BaseModel):
    """Request to start a new UCTP pipeline run."""
    dataset_id: int = Field(..., description="Dataset to process")
    algorithm_name: str = Field(
        default="Custom Pipeline",
        min_length=1,
        max_length=100,
        description="Name for this algorithm configuration",
    )
    clustering: ClusteringConfigRequest = Field(default_factory=ClusteringConfigRequest)
    iod: IODConfigRequest = Field(default_factory=IODConfigRequest)
    refinement: RefinementConfigRequest = Field(default_factory=RefinementConfigRequest)


class UCTPRunMetrics(BaseModel):
    """Metrics from a completed pipeline run."""
    f1_score: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    position_rms_km: Optional[float] = None
    velocity_rms_km_s: Optional[float] = None
    clusters_found: Optional[int] = None
    objects_resolved: Optional[int] = None
    total_observations: Optional[int] = None
    noise_observations: Optional[int] = None
    iod_success_rate: Optional[float] = None
    elapsed_seconds: Optional[float] = None


class UCTPRunSummary(BaseModel):
    """Summary of a UCTP pipeline run."""
    id: int
    dataset_id: int
    algorithm_name: str
    status: UCTPRunStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: UCTPRunMetrics = Field(default_factory=UCTPRunMetrics)
    created_at: datetime
    job_id: Optional[str] = None

    class Config:
        from_attributes = True


class UCTPRunDetail(UCTPRunSummary):
    """Detailed view of a UCTP pipeline run."""
    config: Dict[str, Any] = {}
    output_path: Optional[str] = None
    log_output: Optional[str] = None
    error_message: Optional[str] = None


class UCTPRunComparison(BaseModel):
    """Comparison of multiple runs."""
    runs: List[UCTPRunSummary]
    config_diffs: Dict[str, Any] = {}


# ============================================================
# ML MODEL MODELS
# ============================================================


class UCTPModelTrainRequest(BaseModel):
    """Request to start model training."""
    name: str = Field(..., min_length=1, max_length=100)
    model_type: UCTPModelType = UCTPModelType.CLUSTERING_NN
    description: Optional[str] = None
    training_dataset_ids: List[int] = Field(..., min_length=1)
    training_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "epochs": 50,
            "batch_size": 32,
            "learning_rate": 0.001,
        }
    )


class UCTPModelSummary(BaseModel):
    """Summary of a trained ML model."""
    id: int
    name: str
    model_type: UCTPModelType
    version: str
    description: Optional[str] = None
    status: UCTPModelStatus
    best_f1_score: Optional[float] = None
    best_position_rms_km: Optional[float] = None
    training_epochs: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UCTPModelDetail(UCTPModelSummary):
    """Detailed view of a trained ML model."""
    training_dataset_ids: List[int] = []
    training_config: Dict[str, Any] = {}
    training_loss: Optional[float] = None
    validation_loss: Optional[float] = None
    model_path: Optional[str] = None


# ============================================================
# CONNECTIVITY MODELS
# ============================================================


class ConnectorStatusResponse(BaseModel):
    """Status of a single API connector."""
    service_name: str
    status: ConnectivityStatus
    response_time_ms: Optional[float] = None
    last_checked: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConnectivityTestRequest(BaseModel):
    """Request to test a specific API connection."""
    service_name: str = Field(..., description="Service to test: spacetrack|udl|satnogs|celestrak|orekit|orbdetpy")


class ConnectivityReport(BaseModel):
    """Report of all API connection tests."""
    services: List[ConnectorStatusResponse]
    tested_at: datetime
    total_connected: int = 0
    total_failed: int = 0


# ============================================================
# DASHBOARD MODELS
# ============================================================


class UCTPDashboardStats(BaseModel):
    """Overview statistics for the UCTP Lab dashboard."""
    total_runs: int = 0
    completed_runs: int = 0
    best_f1_score: Optional[float] = None
    best_algorithm: Optional[str] = None
    total_models: int = 0
    ready_models: int = 0
    api_health_pct: float = 0.0  # Percentage of APIs connected
    recent_runs: List[UCTPRunSummary] = []


# ============================================================
# ALGORITHM OPTIONS
# ============================================================


class AlgorithmOptions(BaseModel):
    """Available algorithm configuration options."""
    clustering_methods: List[Dict[str, str]] = [
        {"value": "angular_dbscan", "label": "Angular DBSCAN", "description": "DBSCAN on angular features with great-circle distance"},
        {"value": "stonesoup_mht", "label": "Stone Soup MHT", "description": "Multi-hypothesis tracking via Stone Soup (requires stonesoup)"},
        {"value": "stonesoup_gnn", "label": "Stone Soup GNN", "description": "Global nearest neighbor via Stone Soup (requires stonesoup)"},
    ]
    iod_methods: List[Dict[str, str]] = [
        {"value": "gauss", "label": "Gauss IOD", "description": "Classical Gauss angles-only IOD"},
        {"value": "orbdetpy_laplace", "label": "orbdetpy Laplace", "description": "Laplace IOD via orbdetpy (requires orbdetpy)"},
        {"value": "orekit_gooding", "label": "Orekit Gooding", "description": "Gooding IOD via Orekit (requires Orekit JVM)"},
    ]
    refinement_methods: List[Dict[str, str]] = [
        {"value": "none", "label": "None", "description": "No refinement, use IOD result directly"},
        {"value": "batch_least_squares", "label": "Batch Least-Squares", "description": "Batch LS via orbdetpy (requires orbdetpy)"},
        {"value": "ekf", "label": "Extended Kalman Filter", "description": "EKF via orbdetpy (requires orbdetpy)"},
        {"value": "ukf", "label": "Unscented Kalman Filter", "description": "UKF via orbdetpy (requires orbdetpy)"},
    ]
