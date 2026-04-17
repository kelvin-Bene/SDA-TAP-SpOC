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
    """Dataset complexity tier.

    T1-T4: Increasingly complex requirements.
    T5: Impossible criteria detected (e.g., GEO track gap requirements
        that cannot be met per Aug 2025 transcript).
    """

    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"


class SensorType(str, Enum):
    """Observation sensor type.

    Per Jan 22 transcript: Louis lists "data fusion, a combination of all of the above".
    """

    OPTICAL = "optical"
    RADAR = "radar"
    RF = "rf"
    FUSION = "fusion"


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
# LEGACY 16-CHARACTER CODE ENUMS (Louis's Documentation)
# ============================================================


class LegacyObjectType(str, Enum):
    """Object type in legacy 16-char dataset code (Position 1)."""

    HAMR = "H"          # High Area-to-Mass Ratio objects
    CLOSE = "C"         # Close physical proximity
    APPARENT = "A"      # Apparent angular proximity
    UNSPECIFIED = "U"   # Unspecified/Normal
    CALIBRATION = "N"   # Calibration satellites


class TargetPercentage(str, Enum):
    """Target percentage in legacy code (Positions 2-3)."""

    FIFTY = "50"        # 50% target objects
    TEN = "10"          # 10% target objects
    ONE = "01"          # 1% target objects
    UNSPECIFIED = "UN"  # Unspecified


class LegacyEventType(str, Enum):
    """Event type in legacy code (Positions 7-8)."""

    MANEUVER_BETWEEN = "MB"  # Maneuver between observations
    BREAKUP = "BU"           # Breakup event
    LONG_LOW_THRUST = "LL"   # Long-duration/Low-thrust maneuver
    NO_EVENTS = "NE"         # No events (normal)


class LegacySensorType(str, Enum):
    """Sensor type in legacy code (Positions 9-10)."""

    OPTICAL = "OP"           # Optical only
    RADAR = "RA"             # Radar only
    RF = "RF"                # RF only
    FUSION = "FU"            # Fusion (all sensors)
    OPTICAL_RADAR = "OR"     # Optical + Radar
    RADAR_OPTICAL = "RO"     # Radar + Optical
    RADAR_RF = "RR"          # Radar + RF


class QualityLevel(str, Enum):
    """Quality level for coverage, track gap, obs count (Positions 11-13).

    Per Louis's documentation, A/S/N refer to % of objects with LOW quality:
    A = >90% objects have LOW quality (sparse dataset)
    S = 40-60% objects have LOW quality (mixed)
    N = <10% objects have LOW quality (dense/high-quality dataset)
    """

    ALL = "A"       # >90% of objects have LOW quality (sparse dataset)
    STANDARD = "S"  # 40-60% of objects have LOW quality (mixed)
    NONE = "N"      # <10% of objects have LOW quality (dense dataset)


class ObjectCountLevel(str, Enum):
    """Object count level in legacy code (Position 14)."""

    HIGH = "H"      # 80 objects
    STANDARD = "S"  # 40 objects
    LOW = "L"       # 10 objects


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
    # Non-reference observations for True Negative calculation (per Louis's spec)
    include_non_ref_obs: bool = Field(
        default=False,
        description="Include observations from non-reference satellites for True Negative calculation",
    )
    non_ref_ratio: float = Field(
        default=0.1,
        ge=0.01,
        le=0.5,
        description="Ratio of non-reference observations to add (e.g., 0.1 = 10% of reference obs count)",
    )
    # Object type and event codes (per Louis's 16-character code spec)
    object_type_code: str = Field(
        default="U",
        description="Object type code: H=HAMR, C=Close, A=Apparent, U=Unspecified, N=Calibration",
    )
    event_code: str = Field(
        default="NE",
        description="Event code: MB=Maneuver, BU=Breakup, LL=LongThrust, NE=NoEvents",
    )
    # Window selection algorithm (per Louis's bisecting search spec)
    use_window_selection: bool = Field(
        default=True,
        description="Use bisecting window selection algorithm to find optimal time window and tier (Louis's spec)",
    )
    # Target percentage enforcement (positions 2-3 of 16-char code)
    target_percentage: str = Field(
        default="UN",
        description="Target percentage from 16-char code: 50=50%, 10=10%, 01=1%, UN=Unspecified",
    )
    # TrackTLE output generation (per Louis's spec for UCTPs requiring trackTLE input)
    output_tracktle: bool = Field(
        default=False,
        description="Generate TrackTLE (TLEs from single-pass observations) for UCTP compatibility",
    )
    # CTF poor sensor calibration challenge (SDA TAP Lab UCT challenge #10
    # from "Need for UCT Benchmarking" paper). When 'poor', the worker draws
    # a per-sensor systematic bias from a uniform [-3, +3] arcsec distribution
    # and applies it virtually at download/eval time so the shared
    # observations table stays pristine.
    calibration_quality: str = Field(
        default="standard",
        description=(
            "Sensor calibration quality. 'standard' applies no synthetic "
            "bias (default). 'poor' applies a per-sensor systematic bias "
            "drawn from a uniform [-3, +3] arcsec distribution per axis, "
            "simulating miscalibrated sensors per the SDA TAP Lab UCT "
            "challenge #10."
        ),
    )
    # CTF maneuvering-during-gap challenge (UCT challenge #6).
    # When True, ~20% of satellites perform a synthetic delta-V maneuver
    # during a 6-hour coverage gap at the dataset midpoint. The post-maneuver
    # state vector becomes the canonical truth for those satellites — a
    # UCTP that fails to detect the maneuver scores zero on them.
    maneuver_during_gap: bool = Field(
        default=False,
        description=(
            "When True, ~20% of satellites in the dataset will perform a "
            "synthetic delta-V maneuver during a 6-hour sensor coverage "
            "gap at the midpoint of the dataset's time window. The "
            "maneuver is drawn from a uniform [1, 50] m/s distribution "
            "per axis. The post-maneuver state vector is recorded as the "
            "canonical truth, so a UCTP that fails to detect the maneuver "
            "will score zero on those satellites. Implements SDA TAP Lab "
            "UCT challenge #6 (objects maneuvering during long sensor "
            "coverage gaps)."
        ),
    )


class LegacyDatasetCreate(BaseModel):
    """
    Request schema for creating a dataset using legacy 16-character code format.

    Format: OTTRRREWSSCSNS##
    Example: H50LEONEOPSSSS07 = HAMR, 50% target, LEO, No Events, Optical, Standard metrics, Standard count, 7 days
    """

    # Option 1: Provide the complete 16-char code
    legacy_code: Optional[str] = Field(
        default=None,
        min_length=16,
        max_length=16,
        description="Complete 16-character dataset code (e.g., 'H50LEONEOPSSSS07')",
    )

    # Option 2: Provide individual components
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Optional custom name (auto-generated if not provided)",
    )
    object_type: LegacyObjectType = Field(
        default=LegacyObjectType.UNSPECIFIED,
        description="Object type: H=HAMR, C=Close, A=Apparent, U=Unspecified, N=Calibration",
    )
    target_percentage: TargetPercentage = Field(
        default=TargetPercentage.FIFTY,
        description="Target percentage: 50, 10, 01, or UN",
    )
    orbital_regime: OrbitalRegime = Field(
        default=OrbitalRegime.LEO,
        description="Orbital regime: LEO, MEO, GEO, HEO",
    )
    event: LegacyEventType = Field(
        default=LegacyEventType.NO_EVENTS,
        description="Event type: MB=Maneuver, BU=Breakup, LL=LongThrust, NE=NoEvents",
    )
    sensor_type: LegacySensorType = Field(
        default=LegacySensorType.OPTICAL,
        description="Sensor type: OP, RA, RF, FU, OR, RO, RR",
    )
    orbit_coverage: QualityLevel = Field(
        default=QualityLevel.STANDARD,
        description="Orbit coverage: A=Sparse (>90% low), S=Mixed, N=Dense (<10% low)",
    )
    track_gap: QualityLevel = Field(
        default=QualityLevel.STANDARD,
        description="Track gap: A=Sparse (>90% long gaps), S=Mixed, N=Dense (<10% long gaps)",
    )
    observation_count: QualityLevel = Field(
        default=QualityLevel.STANDARD,
        description="Obs count: A=Sparse (>90% few obs), S=Mixed, N=Dense (<10% few obs)",
    )
    object_count_level: ObjectCountLevel = Field(
        default=ObjectCountLevel.STANDARD,
        description="Object count: H=80, S=40, L=10",
    )
    fitspan_days: int = Field(
        default=7,
        ge=1,
        le=14,
        description="Fitspan in days (01-14)",
    )

    # Additional options
    start_date: Optional[datetime] = None
    description: Optional[str] = None

    def to_legacy_code(self) -> str:
        """Generate the 16-character legacy code from components."""
        if self.legacy_code:
            return self.legacy_code
        return (
            f"{self.object_type.value}"
            f"{self.target_percentage.value}"
            f"{self.orbital_regime.value}"
            f"{self.event.value}"
            f"{self.sensor_type.value}"
            f"{self.orbit_coverage.value}"
            f"{self.track_gap.value}"
            f"{self.observation_count.value}"
            f"{self.object_count_level.value}"
            f"{self.fitspan_days:02d}"
        )


class LegacyCodeValidation(BaseModel):
    """Response for legacy code validation."""

    code: str
    is_valid: bool
    format_type: str  # "legacy" or "enhanced"
    error_message: Optional[str] = None
    components: Optional[Dict[str, Any]] = None


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
    # Legacy code fields
    legacy_code: Optional[str] = None
    code: Optional[str] = None  # Enhanced format code
    # Non-reference observations (for True Negative calculation)
    non_ref_observation_count: int = 0
    include_non_ref_obs: bool = False
    # Version tracking (per Louis's transcript.md requirement)
    version: int = 1
    parent_id: Optional[str] = None
    # Error message for failed datasets
    error_message: Optional[str] = None
    # Eval-readiness: true iff dataset_references rows exist for this dataset.
    # Frontend uses this to gate the Submit dropdown so users cannot submit
    # against legacy / partially-generated datasets that would fail with
    # "no reference state vectors persisted" (QA_PROD_RUN_2026-04-17 C1).
    has_reference_orbits: bool = False

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
    # Legacy code component fields
    object_type_code: Optional[str] = None
    target_percentage: Optional[str] = None
    event_code: Optional[str] = None
    sensor_code: Optional[str] = None
    coverage_level: Optional[str] = None
    track_gap_level: Optional[str] = None
    obs_count_level: Optional[str] = None
    object_count_level: Optional[str] = None
    fitspan_days: Optional[int] = None
    # Generation provenance
    actual_satellite_ids: List[int] = []
    performance_metadata: Optional[Dict[str, Any]] = None
    downsampling_applied: bool = False
    simulation_applied: bool = False
    simulated_obs_count: int = 0
    downsampling_config: Optional[Dict[str, Any]] = None
    simulation_config: Optional[Dict[str, Any]] = None


class DatasetObservation(BaseModel):
    """Single observation from a dataset.

    Per Feb 19, 2026 transcript: all UDL fields must be available to UCTP consumers.
    "Cannot arbitrarily remove fields as unknown processors may need them."
    """

    id: str
    ob_time: datetime
    ra: Optional[float] = None
    declination: Optional[float] = None
    # Radar fields
    azimuth: Optional[float] = None
    elevation: Optional[float] = None
    range_km: Optional[float] = None
    # Sensor metadata
    sensor_id: Optional[str] = None
    sensor_name: Optional[str] = None
    data_mode: Optional[str] = None
    type_optical: Optional[str] = None
    # Sensor location
    send_lat: Optional[float] = None
    send_long: Optional[float] = None
    send_alt: Optional[float] = None
    # Track association
    track_id: Optional[str] = None
    # Flags
    is_simulated: Optional[bool] = None
    # Full EO observation fields (per Benchmarking Documentation)
    classification_marking: Optional[str] = None
    id_on_orbit: Optional[str] = None
    task_id: Optional[str] = None
    orig_object_id: Optional[str] = None
    orig_sensor_id: Optional[str] = None
    sen_x: Optional[float] = None
    sen_y: Optional[float] = None
    sen_z: Optional[float] = None
    exp_duration: Optional[float] = None
    mag: Optional[float] = None
    mag_unc: Optional[float] = None
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None
    geo_alt: Optional[float] = None
    geo_range: Optional[float] = None


# ============================================================
# SUBMISSION MODELS
# ============================================================


class SubmissionCreate(BaseModel):
    """Request schema for creating a new submission."""

    dataset_id: str
    algorithm_name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(default="1.0", max_length=50)
    description: Optional[str] = None
    # Per Feb 19 transcript: "classification marking = just a label (organization that created output)"
    classification_marking: Optional[str] = Field(
        default=None,
        description="Classification marking label identifying the organization that created this output",
    )


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
    rank: Optional[int] = None

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
    """Binary classification metrics.

    Per Louis's documentation:
    - TP: Observation correctly matched to reference satellite
    - TN: Non-reference observation correctly NOT matched
    - FP: Observation incorrectly matched to wrong satellite
    - FN: Reference observation not matched
    """

    true_positives: int
    true_negatives: int = 0  # Requires non-reference observations in dataset
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float = 0.0  # (TP+TN)/(TP+TN+FP+FN)
    specificity: float = 0.0  # TN/(TN+FP)


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
    true_negatives: int = 0  # Requires non-reference observations in dataset
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0  # (TP+TN)/(TP+TN+FP+FN)
    specificity: float = 0.0  # TN/(TN+FP)

    # State metrics
    position_rms_km: float = 0.0
    velocity_rms_km_s: float = 0.0
    mahalanobis_distance: Optional[float] = None

    # Residual metrics
    ra_residual_rms_arcsec: Optional[float] = None
    dec_residual_rms_arcsec: Optional[float] = None

    # Composite scoring — Louis Feb 19: rank by the weighted combination of
    # binary/state/residual, not F1 alone. composite_breakdown carries the
    # per-component contributions so the UI can show *why* a score dropped.
    composite_score: Optional[float] = None
    train_composite_score: Optional[float] = None
    val_composite_score: Optional[float] = None
    test_composite_score: Optional[float] = None
    composite_breakdown: Optional[Dict[str, Any]] = None
    split_breakdowns: Optional[Dict[str, Any]] = None

    # Per-satellite breakdown
    satellite_results: List[SatelliteResult] = []

    # Histogram data for visualization (from raw_results)
    ra_residual_histogram: Optional[Dict[str, Any]] = None
    dec_residual_histogram: Optional[Dict[str, Any]] = None
    position_error_histogram: Optional[Dict[str, Any]] = None

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
    # Headline composite score used for the leaderboard rank. Sourced from
    # test_composite_score when present, falling back to the legacy
    # whole-dataset composite_score and then f1_score (see leaderboard.py
    # ORDER BY clause for the COALESCE chain).
    composite_score: Optional[float] = None
    # CTF train/validation/test sub-scores. Test is the only one that
    # cannot be cheated by reading the truth in the download.
    train_composite_score: Optional[float] = None
    val_composite_score: Optional[float] = None
    test_composite_score: Optional[float] = None
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


# ============================================================
# ORBIT VISUALIZATION (3D globe)
# ============================================================


class OrbitPosition(BaseModel):
    """Single time-sampled position in EME2000 ECI frame (km)."""

    time: str  # ISO8601 UTC
    x: float
    y: float
    z: float


class OrbitSatellite(BaseModel):
    """One satellite's time-sampled track for the 3D globe."""

    id: str
    name: str
    regime: OrbitalRegime
    positions: List[OrbitPosition]
    color: Optional[str] = None


class ReferenceOrbitsResponse(BaseModel):
    """Response for GET /datasets/{id}/reference-orbits.

    Reference orbits are the dataset answer key. Endpoint is gated to the
    dataset owner and admins only (see datasets.py ownership check).
    """

    dataset_id: str
    start_time: str
    end_time: str
    satellites: List[OrbitSatellite]


class SubmissionPredictionsResponse(BaseModel):
    """Response for GET /submissions/{id}/predictions."""

    submission_id: str
    predicted: List[OrbitSatellite]
    reference: Optional[List[OrbitSatellite]] = None
