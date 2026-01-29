"""
Shared Pydantic models for the UCT Benchmark API.

These models define the request/response schemas that are shared
across multiple routers and match the frontend TypeScript types.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ============================================================
# ENUMS
# ============================================================


class OrbitalRegime(str, Enum):
    """Orbital regime classification."""

    LEO = "LEO"
    MEO = "MEO"
    GEO = "GEO"
    HEO = "HEO"


class DataTier(str, Enum):
    """Dataset complexity tier."""

    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


class SensorType(str, Enum):
    """Observation sensor type."""

    OPTICAL = "optical"
    RADAR = "radar"
    RF = "rf"


class DatasetStatus(str, Enum):
    """Status of a dataset."""

    CREATED = "created"
    GENERATING = "generating"
    AVAILABLE = "available"
    COMPLETE = "complete"  # Alias used in Supabase
    FAILED = "failed"


class SubmissionStatus(str, Enum):
    """Status of a submission."""

    QUEUED = "queued"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatusEnum(str, Enum):
    """Status of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchStrategy(str, Enum):
    """Strategy for fetching observation data from UDL API."""

    FAST = "fast"  # Single query per satellite, full time range
    WINDOWED = "windowed"  # Fixed time windows, sequential (reference code)
    HYBRID = "hybrid"  # Count-first with dynamic chunking


# ============================================================
# DOWNSAMPLING & SIMULATION OPTIONS
# ============================================================


class DownsamplingOptions(BaseModel):
    """Options for observation downsampling."""

    enabled: bool = Field(
        default=False, description="Enable downsampling to reduce observation quality"
    )
    target_coverage: float = Field(
        default=0.05,
        ge=0.01,
        le=1.0,
        description="Target orbital coverage fraction (lower = less coverage)",
    )
    target_gap: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="Target track gap in orbital periods (higher = larger gaps)",
    )
    max_obs_per_sat: int = Field(
        default=50, ge=5, le=500, description="Maximum observations per satellite"
    )
    preserve_tracks: bool = Field(
        default=True, description="Preserve track boundaries during thinning"
    )
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")


class SimulationOptions(BaseModel):
    """Options for gap-filling simulation."""

    enabled: bool = Field(default=False, description="Enable simulation to fill observation gaps")
    fill_gaps: bool = Field(default=True, description="Fill gaps with synthetic observations")
    sensor_model: str = Field(
        default="GEODSS",
        description="Sensor model for noise characteristics (GEODSS, SBSS, Commercial_EO)",
    )
    apply_noise: bool = Field(
        default=True, description="Apply realistic sensor noise to simulated observations"
    )
    max_synthetic_ratio: float = Field(
        default=0.5, ge=0.0, le=0.9, description="Maximum ratio of synthetic to total observations"
    )
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")


# ============================================================
# DATASET MODELS
# ============================================================


class DatasetCreate(BaseModel):
    """Request schema for creating a new dataset."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    regime: OrbitalRegime
    tier: DataTier = DataTier.T1
    object_count: int = Field(default=10, ge=1, le=1000)
    timeframe: int = Field(default=7, ge=1, le=90)
    timeunit: str = Field(default="days")
    satellites: Optional[List[int]] = None
    sensors: List[SensorType] = Field(default=[SensorType.OPTICAL])
    coverage: str = Field(default="standard")  # high, standard, low, mixed
    include_hamr: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    # Downsampling and simulation options
    downsampling: Optional[DownsamplingOptions] = Field(
        default=None, description="Options for downsampling observations to reduce quality"
    )
    simulation: Optional[SimulationOptions] = Field(
        default=None, description="Options for simulating observations to fill gaps"
    )
    # Search strategy for data fetching
    search_strategy: SearchStrategy = Field(
        default=SearchStrategy.HYBRID,
        description="Strategy for fetching data: 'fast', 'windowed', 'hybrid'",
    )
    window_size_minutes: Optional[int] = Field(
        default=10, ge=1, le=60, description="Window size for windowed strategy (default 10 min)"
    )


class DatasetSummary(BaseModel):
    """Summary response for a dataset (list view)."""

    id: str
    name: str
    description: Optional[str] = None
    regime: OrbitalRegime
    tier: DataTier
    status: DatasetStatus
    created_at: datetime
    observation_count: int = 0
    satellite_count: int = 0
    coverage: float = 0.0
    size_bytes: int = 0
    sensor_types: List[SensorType] = []
    job_id: Optional[str] = None

    class Config:
        from_attributes = True


class DatasetDetail(DatasetSummary):
    """Detailed response for a single dataset."""

    satellites: List[int] = []
    parameters: Dict[str, Any] = {}
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    avg_obs_count: float = 0.0
    max_track_gap: float = 0.0
    json_path: Optional[str] = None


class DatasetObservation(BaseModel):
    """Single observation from a dataset."""

    id: str
    ob_time: datetime
    ra: float
    declination: float
    sensor_name: Optional[str] = None
    track_id: Optional[str] = None


# ============================================================
# SUBMISSION MODELS
# ============================================================


class SubmissionCreate(BaseModel):
    """Request schema for creating a new submission."""

    dataset_id: str
    algorithm_name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(default="1.0", max_length=50)
    description: Optional[str] = None


class SubmissionSummary(BaseModel):
    """Summary response for a submission (list view)."""

    id: str
    dataset_id: str
    dataset_name: Optional[str] = None
    algorithm_name: str
    version: str
    status: SubmissionStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    score: Optional[float] = None
    job_id: Optional[str] = None
    queue_position: Optional[int] = None

    class Config:
        from_attributes = True


class SubmissionDetail(SubmissionSummary):
    """Detailed response for a single submission."""

    file_path: Optional[str] = None
    error_message: Optional[str] = None


# ============================================================
# RESULTS MODELS
# ============================================================


class BinaryMetrics(BaseModel):
    """Binary classification metrics."""

    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float


class StateMetrics(BaseModel):
    """Orbit state estimation metrics."""

    position_rms_km: float
    velocity_rms_km_s: float
    mahalanobis_distance: Optional[float] = None


class ResidualMetrics(BaseModel):
    """Observation residual metrics."""

    ra_residual_rms_arcsec: float
    dec_residual_rms_arcsec: float


class SatelliteResult(BaseModel):
    """Per-satellite result breakdown."""

    satellite_id: str
    status: str  # TP, FP, FN
    observations_used: int
    total_observations: int
    position_error_km: Optional[float] = None
    velocity_error_km_s: Optional[float] = None
    confidence: Optional[float] = None


class SubmissionResults(BaseModel):
    """Complete results for a submission."""

    submission_id: str
    dataset_id: str
    algorithm_name: str
    status: SubmissionStatus
    completed_at: Optional[datetime] = None

    # Binary metrics
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    # State metrics
    position_rms_km: float = 0.0
    velocity_rms_km_s: float = 0.0
    mahalanobis_distance: Optional[float] = None

    # Residual metrics
    ra_residual_rms_arcsec: Optional[float] = None
    dec_residual_rms_arcsec: Optional[float] = None

    # Per-satellite breakdown
    satellite_results: List[SatelliteResult] = []

    # Rank info
    rank: Optional[int] = None
    previous_rank: Optional[int] = None

    # Processing info
    processing_time_seconds: Optional[float] = None

    class Config:
        from_attributes = True


class ResultSummary(BaseModel):
    """Lightweight summary for results list view."""

    submission_id: str
    dataset_id: str
    dataset_name: Optional[str] = None
    algorithm_name: str
    version: str
    status: SubmissionStatus
    completed_at: Optional[datetime] = None

    # Key metrics
    f1_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    position_rms_km: float = 0.0

    # Ranking
    rank: Optional[int] = None

    class Config:
        from_attributes = True


# ============================================================
# LEADERBOARD MODELS
# ============================================================


class LeaderboardEntry(BaseModel):
    """Single entry on the leaderboard."""

    rank: int
    algorithm_name: str
    team: Optional[str] = None
    version: str
    f1_score: float
    precision: float
    recall: float
    position_rms_km: float
    submission_id: str
    submitted_at: datetime
    is_current_user: bool = False


class LeaderboardResponse(BaseModel):
    """Complete leaderboard response."""

    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    last_updated: datetime
    total_entries: int
    entries: List[LeaderboardEntry]


# ============================================================
# JOB MODELS
# ============================================================


class JobResponse(BaseModel):
    """Response for a background job."""

    id: str
    job_type: str
    status: JobStatusEnum
    progress: int = Field(ge=0, le=100)
    stage: Optional[str] = None  # Current stage description for progress display
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


# ============================================================
# COMMON RESPONSE MODELS
# ============================================================


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""

    message: str
    data: Optional[Any] = None
