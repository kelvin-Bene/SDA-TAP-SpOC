from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file if it exists
load_dotenv()

# Paths
PROJ_ROOT = Path(__file__).resolve().parents[1]
logger.info(f"PROJ_ROOT path is: {PROJ_ROOT}")

DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

MODELS_DIR = PROJ_ROOT / "models"

REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# If tqdm is installed, configure loguru with tqdm.write
# https://github.com/Delgan/loguru/issues/135
try:
    from tqdm import tqdm

    # Remove all existing handlers safely (handler IDs may not start at 0)
    try:
        logger.remove()
    except ValueError:
        pass
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
except ModuleNotFoundError:
    pass


# === Legacy Configuration from src/libraries/config.py ===

# Calibration Satellites
satIDs = [
    1328,
    5398,
    7646,
    8820,
    16908,
    19751,
    20026,
    22195,
    22314,
    22824,
    23613,
    24876,
    25544,
    26360,
    27566,
    27944,
    32711,
    36508,
    39070,
    39086,
    39504,
    40730,
    41240,
    41335,
    42915,
    43476,
    43477,
    43873,
    46826,
    48859,
]

## --- Dataset Codes: Define thresholds --- ##
# Define size of orbital regime by semimajor axis in km
semiMajorAxis_LEO = 8378  # LEO is less than this (correponds to mean altitude <2000km)
semiMajorAxis_GEO = 42164  # GEO is greater than or equal to this
# MEO is defined as not LEO or GEO

# Define highly eccentric orbit (HEO) threshold
eccentricity_HEO = 0.7  # a HEO object has eccentricity greater than or equal to this value

# =============================================================================
# OBJECT TYPE FILTERING THRESHOLDS (per Louis's Documentation)
# =============================================================================

# High Area-to-Mass Ratio (HAMR) threshold
# Objects with A/M ratio above this are considered HAMR
# Per Louis's documentation: HAMR objects have A/M > 0.1 m²/kg
HAMR_THRESHOLD = 1.0  # m^2/kg - objects above this are HAMR (per Louis's documentation: A/M > 1 m²/kg)

# =============================================================================
# ORBITAL COVERAGE THRESHOLDS (per Louis's Benchmarking Documentation)
# =============================================================================
# These thresholds define what is considered "LOW" orbital coverage for each regime
# Calculated using convex polygon on circumscribed circle approach
# Values represent fraction of orbit covered (not percentage)

COVERAGE_THRESHOLDS = {
    "LEO": 0.000213,   # < 0.0213% orbital arc is LOW coverage (as fraction)
    "MEO": 0.000449,   # < 0.0449% orbital arc is LOW coverage (as fraction)
    "GEO": 0.41656,    # < 41.656% orbital arc is LOW coverage (as fraction)
}

# =============================================================================
# TRACK GAP THRESHOLDS (per Louis's Documentation)
# =============================================================================
# "Long" track gap = gap > 2 orbital periods between tracks

TRACK_GAP_LONG_MULTIPLIER = 2.0  # "Long" = > 2 orbital periods

# =============================================================================
# OBSERVATION COUNT THRESHOLDS (per Louis's Documentation)
# =============================================================================
# Thresholds for observation count per 3-day span

OBS_COUNT_LOW_THRESHOLD = 50     # < 50 observations per 3 days = "Low"
OBS_COUNT_STANDARD_MIN = 50      # 50-150 observations per 3 days = "Standard"
OBS_COUNT_STANDARD_MAX = 150

# =============================================================================
# A/S/N QUALITY RANGES (per Louis's Specification)
# =============================================================================
# A/S/N refers to percentage of objects that have LOW quality metrics
# A (All/sparse): >90% of objects have LOW quality (sparse/hard dataset)
# S (Standard): 40-60% of objects have LOW quality (mixed dataset)
# N (None/dense): <10% of objects have LOW quality (dense/easy dataset)

QUALITY_RANGES = {
    'A': {'min_pct': 0.90, 'max_pct': 1.0},   # >90% have LOW quality (sparse)
    'S': {'min_pct': 0.40, 'max_pct': 0.60},  # 40-60% have LOW quality (mixed)
    'N': {'min_pct': 0.0, 'max_pct': 0.10},   # <10% have LOW quality (dense)
}

# =============================================================================
# TRUE NEGATIVES CONFIGURATION (per Louis's Documentation)
# =============================================================================
# Non-reference observations should have exactly 2 observations per satellite
# This makes IOD impossible (need minimum 3) so algorithm should NOT match them

NON_REF_OBS_PER_SATELLITE = 2  # Exactly 2 (impossible for IOD)

# =============================================================================
# ESA DISCOSWEB CONFIGURATION
# =============================================================================
import os
ESA_DISCOS_API_TOKEN = os.getenv("ESA_DISCOS_API_TOKEN", "")
ESA_DISCOS_API_URL = "https://discosweb.esoc.esa.int/api"

# Close Proximity thresholds — calibrated against Louis's authoritative
# UCT Labelling schema (provided-materials/UCT Benchmarking/Misc/UCT Labelling.xlsx,
# "Satellite Specific" column):
#     Close Relative Space:
#         Distance between sat < 10 km
#         Velocity between sat: < 10 m/s
#
# The angular threshold for "close apparent" is not in Louis's labelling
# sheet. We use 30 arcsec (~0.0083°) because it matches typical ground-based
# optical sensor seeing on a normal night per the team's Smear Explanation
# document (FWHM percentile chart, 50th percentile = 0.375 arcsec; objects
# within ~30 arcsec sit inside the cross-tag-confusion zone for a real UCTP).
# Previous values were 100 km / 100 m/s / 0.5° — 10× looser than Louis's
# spec on the physical thresholds and ~60× looser on angular separation.
PROXIMITY_ANGULAR_THRESHOLD_DEG = 30.0 / 3600.0  # 30 arcsec ≈ 0.00833°
PROXIMITY_DISTANCE_THRESHOLD_KM = 10.0           # km — per UCT Labelling.xlsx
PROXIMITY_VELOCITY_THRESHOLD_M_S = 10.0          # m/s — per UCT Labelling.xlsx

# Calibration satellites (well-known objects with good observations)
# These are satellites with well-determined orbits used for verification
CALIBRATION_SATELLITES = satIDs  # Uses the existing satIDs list

# Object type codes for dataset generation
OBJECT_TYPE_CODES = {
    "HAMR": "High Area-to-Mass Ratio objects",
    "PROX": "Close proximity objects",
    "CALIB": "Calibration satellites",
    "NORM": "Normal satellites",
    "DEBR": "Debris objects",
    "ALL": "All object types",
}

# percentage thresholds for what is high (A), standard (S), and low (N) percentage for orbital coverage, observation count, and track gap
# lower, target, and upper bounds in ascending order
# (set arbitrarily) #
highPercentage = (0.9, 0.95, 1.0)
standardPercentage = (0.4, 0.5, 0.6)
lowPercentage = (0.0, 0.05, 0.1)

# What is considered low orbital coverage (percentage), defined differently for LEO, MEO, and GEO
# Orbit coverage is taken over a timespan of 3 orbital periods
# Determined from taking bottom 25 percentile of orbit coverage from real observation data over a 10 day window
lowCoverage_LEO = 0.0213   # 2.13% as fraction
lowCoverage_MEO = 0.0449   # 4.49% as fraction
lowCoverage_GEO = 0.41656  # 41.656% as fraction
# orbital coverage below which is too small to include in datasets
# (set arbitrarily, arbitrarily assumed to be the same for all regimes) #
tooLowtoInclude = 0.001

# What is considered a long track gap (longest duration between tracks in units of orbital period)
# This value was specified by Major Allen
longTrackGap = 2

# What is considered a low or high observation count (number of observations per 3 days)
# Link to paper providing justification for these values in documentation
lowObsCount = 50
highObsCount = 150

# Define high (H), standard (S), and low (L) object count to put in each dataset
# Values determined from conversation with LSAS regarding expected number of objects fit for real UCT data
highObjectCount = 80
standardObjectCount = 40
lowObjectCount = 10

## --- Window Selection: Batch Size for pulling data --- ##
# (set arbitrarily) #
batchSizeMultiplier = 5
batchSizeDecayRate = 0.01

# Set slide resolution to zero if point by point (slow) window selection is desired
slide_resolution = 0.1

# Create target thresholds list of arbitrary length for dataset checking of a specific iteration
# Per Louis's spec: T5 = "Impossible" (criteria cannot be met)
thresholds = ["T1", "T2", "T2", "T3", "T3", "T3", "T4", "T4", "T4", "T4", "T5"]

## --- Propagator Model --- ##
#  Define default parameters for solar radiation pressure and atmospheric drag
# (set arbitrarily, need to alter with justification) #
solarRadPresCoef = 1.5
dragCoef = 2.5

# Define default number of monte carlo sample points used to propagate covariance
# (set arbitrarily, can also change propagation function to propagate covariance with STM to not need MC)
monteCarloPoints = 100

## --- Simulation Parameters --- ##
# Noise added to simulated observations is gaussian in position and angular position (RA/dec)
# Covariance for each is identity scaled by the factor below. Position is in units of km and angular position is in units of radians
# (set arbitrarily)
positionNoise = 0.01
# 1 arcsecond expressed in degrees (RA/Dec are in degrees)
angularNoise = 1.0 / 3600.0

## --- Downsampling Configuration --- ##
# Parameters for T1/T2 downsampling to reduce data quality to target levels
# p_bounds: (min%, max%) of satellites to apply downsampling to
# Coverage target: fraction of orbit to target (lower = less coverage)
# Gap target: max track gap in orbital periods (higher = larger gaps)
# Obs max: maximum observations per satellite per 3 days

# Orbital coverage downsampling
downsample_coverage_bounds = (0.3, 0.5, 0.7)  # (min%, target%, max%) of sats to downsample
downsample_coverage_target = (0.15, 0.05)  # (max, min) orbital coverage threshold

# Track gap downsampling
downsample_gap_bounds = (0.3, 0.5, 0.7)  # (min%, target%, max%) of sats to downsample
downsample_gap_target = 2.0  # Target max gap (2 orbital periods)

# Observation count downsampling
downsample_obs_bounds = (0.3, 0.5, 0.7)  # (min%, target%, max%) of sats to downsample
downsample_obs_max = 50  # Max observations per sat per 3 days

# Minimum observations to keep per satellite (safety threshold)
downsample_min_obs = 5

## --- T3 Simulation Configuration --- ##
# Parameters for T3 simulation to increase data quality by adding synthetic observations

# Time bins per orbital period for epoch selection
# Higher = finer granularity but more computation
simulation_bins_per_period = 10

# Minimum observations per bin to consider "covered"
simulation_min_obs_per_bin = 1

# Maximum ratio of simulated observations to total (prevents over-simulation)
simulation_max_ratio = 0.5

# Target increase in observation count (percentage)
simulation_target_increase = 0.5  # 50% more observations

# Observations per simulated track (realistic grouping)
# Real observations come in tracks of 3-5 obs within minutes
simulation_track_size = 3

# Seconds between observations in a track
simulation_track_spacing = 30

# Minimum observations required before simulation is worthwhile
simulation_min_existing_obs = 3


# =============================================================================
# ENHANCED CONFIGURATION DATACLASSES
# =============================================================================

# --- API Configuration ---


@dataclass
class APIConfig:
    """Configuration for UDL API access and optimization."""

    # Rate limiting
    base_rate_limit_sec: float = 0.1  # Base delay between requests
    max_concurrent_requests: int = 10  # Max concurrent async requests

    # Batch sizing by orbital regime (timedelta for time window)
    batch_sizes: Dict[str, timedelta] = field(
        default_factory=lambda: {
            "LEO": timedelta(hours=6),  # High obs density
            "MEO": timedelta(hours=12),  # Medium density
            "GEO": timedelta(days=1),  # Low density
            "HEO": timedelta(hours=8),  # Variable density
        }
    )

    # Count-first thresholds
    count_first_threshold: int = 10000  # Use count endpoint if expected > this
    max_results_per_query: int = 10000  # Max records per single query

    # Caching
    enable_cache: bool = True
    cache_max_size: int = 1000
    cache_ttl_seconds: int = 900  # 15 minutes

    # Retry configuration
    max_retries: int = 3
    retry_backoff_factor: float = 2.0

    # Available UDL services
    observation_services: List[str] = field(
        default_factory=lambda: [
            "eoobservation",
            "radarobservation",
            "rfobservation",
            "sarobservation",
            "passiveradarobservation",
            "gnssobservationset",
        ]
    )

    state_services: List[str] = field(
        default_factory=lambda: [
            "statevector",
            "elset",
            "ephemeris",
            "ephemerisset",
            "orbitdetermination",
        ]
    )

    catalog_services: List[str] = field(
        default_factory=lambda: [
            "onorbit",
            "onorbitdetails",
            "onorbitlist",
            "onorbitevent",
            "onorbitassessment",
        ]
    )

    event_services: List[str] = field(
        default_factory=lambda: [
            "conjunction",
            "maneuver",
            "launchevent",
            "launchdetection",
            "closelyspacedobjects",
        ]
    )


# --- Downsampling Configuration ---


@dataclass
class DownsampleConfig:
    """Configuration for physics-based downsampling."""

    # Coverage targets (fraction of orbit)
    target_coverage: float = 0.05
    coverage_tolerance: float = 0.02

    # Track gap targets (orbital periods)
    target_gap: float = 2.0
    gap_tolerance: float = 0.5

    # Observation count targets
    max_obs_per_sat: int = 50
    min_obs_per_sat: int = 5

    # Track structure
    preserve_track_boundaries: bool = True
    min_obs_per_track: int = 3

    # Sensor preferences (ordered by priority)
    sensor_priority: Optional[List[str]] = None

    # Randomization
    seed: Optional[int] = None


# Regime-specific downsampling profiles
DOWNSAMPLING_PROFILES: Dict[str, Dict] = {
    "LEO": {
        "min_coverage_pct": 0.02,  # 2% orbital arc
        "max_coverage_pct": 0.15,  # 15% orbital arc
        "min_track_gap_periods": 1.5,  # Gap in orbital periods
        "max_track_gap_periods": 5.0,
        "obs_per_track": (3, 10),  # Min/max obs per track
        "track_duration_periods": 0.1,  # Track spans 10% of period
    },
    "MEO": {
        "min_coverage_pct": 0.03,
        "max_coverage_pct": 0.20,
        "min_track_gap_periods": 1.0,
        "max_track_gap_periods": 3.0,
        "obs_per_track": (5, 15),
        "track_duration_periods": 0.15,
    },
    "GEO": {
        "min_coverage_pct": 0.05,
        "max_coverage_pct": 0.30,
        "min_track_gap_periods": 0.5,
        "max_track_gap_periods": 2.0,
        "obs_per_track": (10, 30),
        "track_duration_periods": 0.25,
    },
    "HEO": {
        "min_coverage_pct": 0.01,
        "max_coverage_pct": 0.10,
        "min_track_gap_periods": 2.0,
        "max_track_gap_periods": 8.0,
        "obs_per_track": (3, 8),
        "track_duration_periods": 0.05,
    },
}


# --- Simulation Configuration ---


@dataclass
class SimulationConfig:
    """Configuration for physics-based observation simulation."""

    # Physics models
    apply_atmospheric_refraction: bool = True
    apply_velocity_aberration: bool = True
    apply_sensor_noise: bool = True
    sensor_model: str = "GEODSS"

    # Timing
    timing_noise_ms: float = 1.0

    # Photometry
    simulate_magnitude: bool = True
    default_albedo: float = 0.2

    # Coverage
    target_coverage_increase: float = 0.5  # 50% more coverage
    max_synthetic_ratio: float = 0.5  # 50% max synthetic

    # Track generation
    obs_per_synthetic_track: int = 5
    track_duration_minutes: float = 10.0

    # Minimum elevation for observation
    min_elevation_deg: float = 6.0

    # Seed
    seed: Optional[int] = None


# Sensor-specific noise models
SENSOR_NOISE_MODELS: Dict[str, Dict] = {
    "GEODSS": {
        "angular_noise_arcsec": 0.5,
        "timing_noise_ms": 1.0,
        "mag_noise": 0.3,
        "systematic_bias": {"az": 0.1, "el": 0.05},
        "sensor_type": "optical",
    },
    "SBSS": {
        "angular_noise_arcsec": 0.3,
        "timing_noise_ms": 0.5,
        "mag_noise": 0.2,
        "systematic_bias": {"az": 0.05, "el": 0.02},
        "sensor_type": "optical",
    },
    "Commercial_EO": {
        "angular_noise_arcsec": 1.0,
        "timing_noise_ms": 5.0,
        "mag_noise": 0.5,
        "systematic_bias": {"az": 0.2, "el": 0.1},
        "sensor_type": "optical",
    },
    "Radar": {
        "range_noise_m": 10.0,
        "range_rate_noise_m_s": 0.01,
        "angular_noise_deg": 0.01,
        "timing_noise_ms": 0.1,
        "sensor_type": "radar",
    },
    "RF": {
        "angular_noise_deg": 0.1,
        "timing_noise_ms": 10.0,
        "sensor_type": "rf",
    },
}


# --- Dataset Configuration ---


@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""

    # Dataset naming
    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    # Satellite selection
    regimes: List[str] = field(default_factory=lambda: ["LEO"])
    object_types: List[str] = field(default_factory=lambda: ["NORM"])
    min_observations: int = 50
    target_count: int = 40

    # Time window
    duration_days: int = 7
    start_date: Optional[str] = None  # ISO format, None = auto-select

    # Data sources
    primary_source: str = "eoobservation"
    secondary_sources: List[str] = field(default_factory=list)

    # Quality targets
    tier: str = "T2"
    coverage_min: float = 0.02
    coverage_max: float = 0.10
    track_gap_min_periods: float = 1.5
    track_gap_max_periods: float = 4.0
    observation_count_min: int = 10
    observation_count_max: int = 50

    # Processing
    enable_downsampling: bool = True
    preserve_tracks: bool = True
    enable_simulation: bool = False

    # Output
    output_format: str = "json"
    include_covariance: bool = True
    anonymize: bool = True

    # Reproducibility
    seed: Optional[int] = None


# Enhanced dataset code schema components
DATASET_CODE_COMPONENTS = {
    "object_types": {
        "HAMR": "High area-to-mass ratio objects",
        "PROX": "Proximity operations objects",
        "NORM": "Normal (typical) satellites",
        "DEBR": "Debris objects",
    },
    "regimes": {
        "LEO": "Low Earth Orbit",
        "MEO": "Medium Earth Orbit",
        "GEO": "Geosynchronous/Geostationary Orbit",
        "HEO": "Highly Eccentric Orbit",
        "ALL": "All regimes",
    },
    "events": {
        "NRM": "Normal operations",
        "MAN": "Maneuver event",
        "BRK": "Breakup event",
        "PRX": "Proximity event",
    },
    "sensors": {
        "EO": "Electro-optical only",
        "RA": "Radar only",
        "RF": "RF only",
        "MX": "Mixed/multi-phenomenology",
    },
    "quality_tiers": {
        "T1H": "Tier 1 High quality",
        "T1S": "Tier 1 Standard quality",
        "T2H": "Tier 2 High quality",
        "T2S": "Tier 2 Standard quality",
        "T3L": "Tier 3 Low quality (simulation)",
        "T4L": "Tier 4 Low quality (full simulation)",
    },
}


# --- Logging Configuration ---


@dataclass
class LoggingConfig:
    """Configuration for enhanced logging."""

    # Log directory
    log_dir: Path = field(default_factory=lambda: Path("logs"))

    # Log levels
    console_level: str = "INFO"
    file_level: str = "DEBUG"
    api_level: str = "INFO"

    # Log rotation
    rotation_size_mb: int = 10
    retention_days: int = 30

    # API call logging
    log_api_calls: bool = True
    log_api_responses: bool = False  # Can be verbose

    # Performance metrics
    collect_metrics: bool = True


# --- Metrics Collection ---


@dataclass
class DatasetMetrics:
    """Metrics collected during dataset generation."""

    run_id: str = ""
    config_hash: str = ""
    start_time: str = ""
    end_time: str = ""

    # API metrics
    total_api_calls: int = 0
    total_records_fetched: int = 0
    api_errors: int = 0

    # Data metrics
    satellites_processed: int = 0
    observations_raw: int = 0
    observations_final: int = 0
    synthetic_observations: int = 0

    # Quality metrics
    tier_distribution: Dict[str, int] = field(default_factory=dict)
    coverage_stats: Dict[str, float] = field(default_factory=dict)
    gap_stats: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# LEGACY 16-CHARACTER DATASET CODE MAPPINGS (Louis's Documentation)
# =============================================================================

# Legacy Object Type mapping (Position 1: 1 character)
# H=HAMR, C=Close, A=Apparent, U=Unspecified, N=Calibration
LEGACY_OBJECT_TYPE_MAP = {
    "H": "HAMR",   # High Area-to-Mass Ratio
    "C": "PROX",   # Close physical proximity
    "A": "APRX",   # Apparent (angular) proximity
    "U": "NORM",   # Unspecified/Normal
    "N": "CALIB",  # Calibration satellites
}
LEGACY_OBJECT_TYPE_REVERSE = {v: k for k, v in LEGACY_OBJECT_TYPE_MAP.items()}

# Legacy Target Percentage (Positions 2-3: 2 characters)
# Percentage of target objects in the dataset
LEGACY_TARGET_PERCENTAGE_VALUES = ["50", "10", "01", "UN"]

# Legacy Orbital Regime (Positions 4-6: 3 characters)
LEGACY_REGIME_VALUES = [
    "LEO", "MEO", "GEO", "HEO", "ALL",
    "LMO",  # LEO + MEO
    "LMG",  # LEO + MEO + GEO
    "MGH",  # MEO + GEO + HEO
]

# Legacy Event Type mapping (Positions 7-8: 2 characters)
# MB=Maneuver Between, BU=Breakup, LL=Long Low-thrust, NE=No Events
LEGACY_EVENT_MAP = {
    "MB": "MAN",  # Maneuver between observations
    "BU": "BRK",  # Breakup event
    "LL": "LLT",  # Long-duration/Low-thrust maneuver
    "NE": "NRM",  # No events (normal)
}
LEGACY_EVENT_REVERSE = {v: k for k, v in LEGACY_EVENT_MAP.items()}

# Legacy Sensor Type mapping (Positions 9-10: 2 characters)
# OP=Optical, RA=Radar, RF=RF, FU=Fusion, OR=Optical+Radar, RO=Radar+Optical, RR=Radar+RF
LEGACY_SENSOR_MAP = {
    "OP": "EO",     # Optical only
    "RA": "RA",     # Radar only
    "RF": "RF",     # RF only
    "FU": "MX",     # Fusion (all sensors)
    "OR": "EO_RA",  # Optical primary, radar secondary
    "RO": "RA_EO",  # Radar primary, optical secondary
    "RR": "RA_RF",  # Radar + RF
}
LEGACY_SENSOR_REVERSE = {v: k for k, v in LEGACY_SENSOR_MAP.items()}

# Legacy Quality Level values (Positions 11-13: A/S/N each)
# Per Louis's Benchmarking Documentation, A/S/N refer to percentage of objects with LOW quality:
# A = All/sparse = >90% of objects have LOW quality (harder dataset for algorithms)
# S = Standard = 40-60% of objects have LOW quality (mixed dataset)
# N = None/dense = <10% of objects have LOW quality (easier dataset for algorithms)
LEGACY_QUALITY_LEVELS = ["A", "S", "N"]

# Quality level thresholds for coverage, track gap, and observation count
# Maps A/S/N to (min, max) percentage of OBJECTS that should have LOW quality
# Per Louis's documentation - CORRECT semantics:
# A = All/sparse = >90% of objects have LOW quality (harder dataset for algorithms)
# S = Standard = 40-60% of objects have LOW quality (mixed dataset)
# N = None/dense = <10% of objects have LOW quality (easier dataset for algorithms)
QUALITY_LEVEL_THRESHOLDS = {
    "coverage": {
        "A": (0.90, 1.00),   # >90% of objects have LOW coverage (sparse dataset)
        "S": (0.40, 0.60),   # 40-60% of objects have LOW coverage (mixed)
        "N": (0.00, 0.10),   # <10% of objects have LOW coverage (dense dataset)
    },
    "track_gap": {
        "A": (0.90, 1.00),   # >90% of objects have LONG track gaps (sparse)
        "S": (0.40, 0.60),   # 40-60% of objects have LONG track gaps (mixed)
        "N": (0.00, 0.10),   # <10% of objects have LONG track gaps (dense)
    },
    "observation_count": {
        "A": (0.90, 1.00),   # >90% of objects have LOW obs count (sparse)
        "S": (0.40, 0.60),   # 40-60% of objects have LOW obs count (mixed)
        "N": (0.00, 0.10),   # <10% of objects have LOW obs count (dense)
    },
}

# Legacy Object Count mapping (Position 14: 1 character)
# H=High (80), S=Standard (40), L=Low (10)
OBJECT_COUNT_MAP = {
    "H": highObjectCount,      # 80 objects
    "S": standardObjectCount,  # 40 objects
    "L": lowObjectCount,       # 10 objects
}
OBJECT_COUNT_REVERSE = {v: k for k, v in OBJECT_COUNT_MAP.items()}

# Fitspan range (Positions 15-16: 2 digits, 01-14 days)
LEGACY_FITSPAN_MIN = 1
LEGACY_FITSPAN_MAX = 14

# Downsampling configuration based on coverage level (A/S/N)
# Per Louis's documentation:
# A = want most objects to have LOW coverage → aggressive downsampling (remove more data)
# N = want few objects to have LOW coverage → minimal downsampling (keep more data)
LEGACY_COVERAGE_DOWNSAMPLE = {
    "A": {  # Most objects should have LOW coverage → aggressive downsampling
        "target_coverage": 0.02,
        "coverage_tolerance": 0.01,
    },
    "S": {  # Mixed coverage → moderate downsampling
        "target_coverage": 0.05,
        "coverage_tolerance": 0.02,
    },
    "N": {  # Few objects should have LOW coverage → minimal downsampling (keep more data)
        "target_coverage": 0.15,
        "coverage_tolerance": 0.05,
    },
}


# Default configuration instances
api_config = APIConfig()
downsample_config = DownsampleConfig()
simulation_config = SimulationConfig()
logging_config = LoggingConfig()
