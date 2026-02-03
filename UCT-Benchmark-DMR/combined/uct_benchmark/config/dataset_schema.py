# -*- coding: utf-8 -*-
"""
Dataset configuration schema and YAML loading.

Provides:
- YAML configuration file loading
- Enhanced dataset code parsing
- Configuration validation
- Metadata generation

Created for UCT Benchmarking Enhancement.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import yaml

from uct_benchmark.settings import (
    DATASET_CODE_COMPONENTS,
    DatasetConfig,
    DatasetMetrics,
    DownsampleConfig,
    LEGACY_OBJECT_TYPE_MAP,
    LEGACY_OBJECT_TYPE_REVERSE,
    LEGACY_TARGET_PERCENTAGE_VALUES,
    LEGACY_REGIME_VALUES,
    LEGACY_EVENT_MAP,
    LEGACY_EVENT_REVERSE,
    LEGACY_SENSOR_MAP,
    LEGACY_SENSOR_REVERSE,
    LEGACY_QUALITY_LEVELS,
    QUALITY_LEVEL_THRESHOLDS,
    OBJECT_COUNT_MAP,
    OBJECT_COUNT_REVERSE,
    LEGACY_FITSPAN_MIN,
    LEGACY_FITSPAN_MAX,
    LEGACY_COVERAGE_DOWNSAMPLE,
)

# =============================================================================
# ENHANCED DATASET CODE SCHEMA
# =============================================================================

# Format: {OBJ}_{REG}_{EVT}_{SEN}_{QTY}_{WIN}_{VER}
# Example: HAMR_LEO_MAN_EO_T2S_07D_001


@dataclass
class EnhancedDatasetCode:
    """Enhanced dataset code with full component breakdown."""

    object_type: str = "NORM"  # HAMR, PROX, NORM, DEBR
    regime: str = "LEO"  # LEO, MEO, GEO, HEO, ALL
    event: str = "NRM"  # NRM, MAN, BRK, PRX
    sensor: str = "EO"  # EO, RA, RF, MX
    quality_tier: str = "T2S"  # T1H, T1S, T2H, T2S, T3L, T4L
    time_window_days: int = 7  # 01D-99D
    version: str = "001"  # Version number

    def to_code(self) -> str:
        """Generate the full dataset code string."""
        return (
            f"{self.object_type}_{self.regime}_{self.event}_"
            f"{self.sensor}_{self.quality_tier}_{self.time_window_days:02d}D_{self.version}"
        )

    @classmethod
    def from_code(cls, code: str) -> "EnhancedDatasetCode":
        """Parse a dataset code string into components."""
        # Try enhanced format first: OBJ_REG_EVT_SEN_QTY_WIN_VER
        enhanced_pattern = (
            r"^([A-Z]{4})_([A-Z]{3})_([A-Z]{3})_([A-Z]{2})_([A-Z0-9]{3})_(\d{2})D_(\d{3})$"
        )
        match = re.match(enhanced_pattern, code)

        if match:
            return cls(
                object_type=match.group(1),
                regime=match.group(2),
                event=match.group(3),
                sensor=match.group(4),
                quality_tier=match.group(5),
                time_window_days=int(match.group(6)),
                version=match.group(7),
            )

        # Try legacy 16-char format
        if len(code) == 16:
            return cls._parse_legacy_code(code)

        raise ValueError(f"Cannot parse dataset code: {code}")

    @classmethod
    def _parse_legacy_code(cls, code: str) -> "EnhancedDatasetCode":
        """Parse legacy 16-character dataset code."""
        # Legacy format: RROOTTTQQQSSNNND
        # RR = regime, O = object, T = tier threshold, Q = quality
        # SS = sensor count, NNN = number, D = days
        try:
            regime_code = code[0:2]
            regime_map = {"LE": "LEO", "ME": "MEO", "GE": "GEO", "HE": "HEO"}
            regime = regime_map.get(regime_code, "LEO")

            # Extract other components with sensible defaults
            return cls(
                object_type="NORM",
                regime=regime,
                event="NRM",
                sensor="EO",
                quality_tier="T2S",
                time_window_days=7,
                version="001",
            )
        except Exception:
            return cls()

    def get_tier_number(self) -> int:
        """Extract tier number (1-4) from quality tier."""
        if self.quality_tier and len(self.quality_tier) >= 2:
            return int(self.quality_tier[1])
        return 2

    def get_quality_level(self) -> str:
        """Extract quality level (H, S, L) from quality tier."""
        if self.quality_tier and len(self.quality_tier) >= 3:
            return self.quality_tier[2]
        return "S"


# =============================================================================
# LEGACY 16-CHARACTER DATASET CODE SCHEMA (Louis's Documentation)
# =============================================================================

# Format: OTTRRREWSSCSNS##
# Position | Length | Component
# 1        | 1      | Object Type: H, C, A, U, N
# 2-3      | 2      | Target %: 50, 10, 01, UN
# 4-6      | 3      | Orbital Regime: LEO, MEO, GEO, HEO, ALL, etc.
# 7-8      | 2      | Event: MB, BU, LL, NE
# 9-10     | 2      | Sensor: OP, RA, RF, FU, OR, RO, RR
# 11       | 1      | Orbit Coverage: A, S, N
# 12       | 1      | Track Gap: A, S, N
# 13       | 1      | Observation Count: A, S, N
# 14       | 1      | Object Count: H, S, L
# 15-16    | 2      | Fitspan Days: 01-14

# Example: H50LEONEOPSSSS07 = HAMR, 50% target, LEO, No Events, Optical, Standard metrics, Standard count, 7 days


@dataclass
class LegacyDatasetCode:
    """
    Legacy 16-character dataset code format from Louis's documentation.

    This format encodes all dataset parameters in a compact 16-character string.
    """

    object_type: str = "U"         # H, C, A, U, N
    target_percentage: str = "50"  # 50, 10, 01, UN
    orbital_regime: str = "LEO"    # LEO, MEO, GEO, HEO, ALL, combos
    event: str = "NE"              # MB, BU, LL, NE
    sensor_type: str = "OP"        # OP, RA, RF, FU, OR, RO, RR
    orbit_coverage: str = "S"      # A, S, N
    track_gap: str = "S"           # A, S, N
    observation_count: str = "S"   # A, S, N
    object_count: str = "S"        # H, S, L
    fitspan_days: int = 7          # 01-14

    def to_code(self) -> str:
        """
        Generate the 16-character dataset code string.

        Returns:
            16-character code string, e.g., "H50LEONEOPSSSS07"
        """
        return (
            f"{self.object_type}"
            f"{self.target_percentage}"
            f"{self.orbital_regime}"
            f"{self.event}"
            f"{self.sensor_type}"
            f"{self.orbit_coverage}"
            f"{self.track_gap}"
            f"{self.observation_count}"
            f"{self.object_count}"
            f"{self.fitspan_days:02d}"
        )

    @classmethod
    def from_code(cls, code: str) -> "LegacyDatasetCode":
        """
        Parse a 16-character dataset code string into components.

        Args:
            code: 16-character dataset code string

        Returns:
            LegacyDatasetCode instance

        Raises:
            ValueError: If code is invalid or cannot be parsed
        """
        if len(code) != 16:
            raise ValueError(f"Legacy code must be exactly 16 characters, got {len(code)}: '{code}'")

        try:
            return cls(
                object_type=code[0],
                target_percentage=code[1:3],
                orbital_regime=code[3:6],
                event=code[6:8],
                sensor_type=code[8:10],
                orbit_coverage=code[10],
                track_gap=code[11],
                observation_count=code[12],
                object_count=code[13],
                fitspan_days=int(code[14:16]),
            )
        except (ValueError, IndexError) as e:
            raise ValueError(f"Failed to parse legacy code '{code}': {e}")

    def to_enhanced(self) -> "EnhancedDatasetCode":
        """
        Convert legacy code to enhanced format.

        Returns:
            EnhancedDatasetCode with mapped values
        """
        # Map object type
        object_type = LEGACY_OBJECT_TYPE_MAP.get(self.object_type, "NORM")

        # Regime stays the same
        regime = self.orbital_regime if self.orbital_regime in ["LEO", "MEO", "GEO", "HEO", "ALL"] else "LEO"

        # Map event
        event = LEGACY_EVENT_MAP.get(self.event, "NRM")

        # Map sensor
        sensor_mapped = LEGACY_SENSOR_MAP.get(self.sensor_type, "EO")
        # Simplify multi-sensor to MX for enhanced format
        sensor = sensor_mapped if sensor_mapped in ["EO", "RA", "RF", "MX"] else "MX"

        # Determine quality tier from coverage level
        # Per Louis's documentation:
        # A = >90% objects have LOW quality (sparse dataset) → lower tier, L suffix
        # S = 40-60% objects have LOW quality (mixed) → mid tier, S suffix
        # N = <10% objects have LOW quality (dense/high quality dataset) → higher tier, H suffix
        tier_map = {"A": "T3", "S": "T2", "N": "T1"}
        tier_num = tier_map.get(self.orbit_coverage, "T2")
        # Map quality levels: A->L (sparse/low), S->S (standard), N->H (dense/high)
        quality_suffix = {"A": "L", "S": "S", "N": "H"}.get(self.orbit_coverage, "S")
        quality_tier = f"{tier_num}{quality_suffix}"

        return EnhancedDatasetCode(
            object_type=object_type,
            regime=regime,
            event=event,
            sensor=sensor,
            quality_tier=quality_tier,
            time_window_days=self.fitspan_days,
            version="001",
        )

    @classmethod
    def from_enhanced(cls, enhanced: "EnhancedDatasetCode") -> "LegacyDatasetCode":
        """
        Convert enhanced format to legacy code.

        Args:
            enhanced: EnhancedDatasetCode instance

        Returns:
            LegacyDatasetCode with reverse-mapped values
        """
        # Reverse map object type
        object_type = LEGACY_OBJECT_TYPE_REVERSE.get(enhanced.object_type, "U")

        # Default target percentage
        target_percentage = "50"

        # Regime
        orbital_regime = enhanced.regime if enhanced.regime in LEGACY_REGIME_VALUES else "LEO"

        # Reverse map event
        event = LEGACY_EVENT_REVERSE.get(enhanced.event, "NE")

        # Reverse map sensor
        sensor_type = LEGACY_SENSOR_REVERSE.get(enhanced.sensor, "OP")

        # Determine quality levels from tier
        # Per Louis's documentation:
        # H (high quality in enhanced) → N (dense, <10% low quality in legacy)
        # S (standard quality) → S (mixed, 40-60% low quality)
        # L (low quality in enhanced) → A (sparse, >90% low quality in legacy)
        quality_level = enhanced.get_quality_level()  # H, S, L
        quality_map = {"H": "N", "S": "S", "L": "A"}
        quality_code = quality_map.get(quality_level, "S")

        # Use same quality for all three metrics by default
        orbit_coverage = quality_code
        track_gap = quality_code
        observation_count = quality_code

        # Object count from quality level (separate mapping for H/S/L counts)
        object_count = {"H": "H", "S": "S", "L": "L"}.get(quality_level, "S")

        return cls(
            object_type=object_type,
            target_percentage=target_percentage,
            orbital_regime=orbital_regime,
            event=event,
            sensor_type=sensor_type,
            orbit_coverage=orbit_coverage,
            track_gap=track_gap,
            observation_count=observation_count,
            object_count=object_count,
            fitspan_days=enhanced.time_window_days,
        )

    def get_object_count_value(self) -> int:
        """Get the numeric object count from the H/S/L code."""
        return OBJECT_COUNT_MAP.get(self.object_count, 40)

    def get_coverage_thresholds(self) -> Tuple[float, float]:
        """Get (min, max) coverage thresholds from the A/S/N code."""
        return QUALITY_LEVEL_THRESHOLDS["coverage"].get(self.orbit_coverage, (0.40, 0.60))

    def get_track_gap_thresholds(self) -> Tuple[float, float]:
        """Get (min, max) track gap thresholds from the A/S/N code."""
        return QUALITY_LEVEL_THRESHOLDS["track_gap"].get(self.track_gap, (0.40, 0.60))

    def get_obs_count_thresholds(self) -> Tuple[float, float]:
        """Get (min, max) observation count thresholds from the A/S/N code."""
        return QUALITY_LEVEL_THRESHOLDS["observation_count"].get(self.observation_count, (0.40, 0.60))

    def get_downsample_config(self) -> Dict[str, float]:
        """Get downsampling configuration based on coverage level."""
        return LEGACY_COVERAGE_DOWNSAMPLE.get(self.orbit_coverage, LEGACY_COVERAGE_DOWNSAMPLE["S"])

    def describe(self) -> str:
        """Return a human-readable description of the dataset code."""
        obj_desc = {
            "H": "HAMR (High Area-to-Mass Ratio)",
            "C": "Close physical proximity",
            "A": "Apparent angular proximity",
            "U": "Unspecified/Normal",
            "N": "Calibration satellites",
        }.get(self.object_type, "Unknown")

        event_desc = {
            "MB": "Maneuver between observations",
            "BU": "Breakup event",
            "LL": "Long-duration/Low-thrust",
            "NE": "No events",
        }.get(self.event, "Unknown")

        sensor_desc = {
            "OP": "Optical",
            "RA": "Radar",
            "RF": "RF",
            "FU": "Fusion (multi-sensor)",
            "OR": "Optical+Radar",
            "RO": "Radar+Optical",
            "RR": "Radar+RF",
        }.get(self.sensor_type, "Unknown")

        # Per Louis's documentation, A/S/N refer to % of objects with LOW quality:
        # A = >90% objects have LOW quality (sparse dataset)
        # S = 40-60% objects have LOW quality (mixed)
        # N = <10% objects have LOW quality (dense/high-quality dataset)
        coverage_desc = {
            "A": "Sparse (>90% objects have low coverage)",
            "S": "Mixed (40-60% objects have low coverage)",
            "N": "Dense (<10% objects have low coverage)",
        }
        gap_desc = {
            "A": "Sparse (>90% objects have long gaps)",
            "S": "Mixed (40-60% objects have long gaps)",
            "N": "Dense (<10% objects have long gaps)",
        }
        obs_desc = {
            "A": "Sparse (>90% objects have few obs)",
            "S": "Mixed (40-60% objects have few obs)",
            "N": "Dense (<10% objects have few obs)",
        }
        count_desc = {"H": "80", "S": "40", "L": "10"}

        return (
            f"Dataset Code: {self.to_code()}\n"
            f"  Object Type: {obj_desc}\n"
            f"  Target %: {self.target_percentage}%\n"
            f"  Regime: {self.orbital_regime}\n"
            f"  Event: {event_desc}\n"
            f"  Sensor: {sensor_desc}\n"
            f"  Orbit Coverage: {coverage_desc.get(self.orbit_coverage, 'Unknown')}\n"
            f"  Track Gap: {gap_desc.get(self.track_gap, 'Unknown')}\n"
            f"  Obs Count: {obs_desc.get(self.observation_count, 'Unknown')}\n"
            f"  Object Count: {count_desc.get(self.object_count, 'Unknown')}\n"
            f"  Fitspan: {self.fitspan_days} days"
        )


def validate_legacy_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a 16-character legacy dataset code.

    Args:
        code: 16-character dataset code string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(code) != 16:
        return False, f"Code must be 16 characters, got {len(code)}"

    errors = []

    # Position 1: Object Type
    if code[0] not in LEGACY_OBJECT_TYPE_MAP:
        errors.append(f"Invalid object type '{code[0]}' at position 1. Valid: H, C, A, U, N")

    # Position 2-3: Target Percentage
    if code[1:3] not in LEGACY_TARGET_PERCENTAGE_VALUES:
        errors.append(f"Invalid target percentage '{code[1:3]}' at positions 2-3. Valid: 50, 10, 01, UN")

    # Position 4-6: Orbital Regime
    if code[3:6] not in LEGACY_REGIME_VALUES:
        errors.append(f"Invalid regime '{code[3:6]}' at positions 4-6. Valid: {', '.join(LEGACY_REGIME_VALUES)}")

    # Position 7-8: Event
    if code[6:8] not in LEGACY_EVENT_MAP:
        errors.append(f"Invalid event '{code[6:8]}' at positions 7-8. Valid: MB, BU, LL, NE")

    # Position 9-10: Sensor Type
    if code[8:10] not in LEGACY_SENSOR_MAP:
        errors.append(f"Invalid sensor '{code[8:10]}' at positions 9-10. Valid: OP, RA, RF, FU, OR, RO, RR")

    # Position 11: Orbit Coverage
    if code[10] not in LEGACY_QUALITY_LEVELS:
        errors.append(f"Invalid orbit coverage '{code[10]}' at position 11. Valid: A, S, N")

    # Position 12: Track Gap
    if code[11] not in LEGACY_QUALITY_LEVELS:
        errors.append(f"Invalid track gap '{code[11]}' at position 12. Valid: A, S, N")

    # Position 13: Observation Count
    if code[12] not in LEGACY_QUALITY_LEVELS:
        errors.append(f"Invalid observation count '{code[12]}' at position 13. Valid: A, S, N")

    # Position 14: Object Count
    if code[13] not in ["H", "S", "L"]:
        errors.append(f"Invalid object count '{code[13]}' at position 14. Valid: H, S, L")

    # Position 15-16: Fitspan Days
    try:
        fitspan = int(code[14:16])
        if not (LEGACY_FITSPAN_MIN <= fitspan <= LEGACY_FITSPAN_MAX):
            errors.append(f"Fitspan {fitspan} out of range at positions 15-16. Valid: {LEGACY_FITSPAN_MIN:02d}-{LEGACY_FITSPAN_MAX:02d}")
    except ValueError:
        errors.append(f"Invalid fitspan '{code[14:16]}' at positions 15-16. Must be 2-digit number")

    if errors:
        return False, "; ".join(errors)

    return True, None


def detect_code_format(code: str) -> str:
    """
    Detect whether a code is in legacy (16-char) or enhanced (underscore) format.

    Args:
        code: Dataset code string

    Returns:
        "legacy" or "enhanced" or "unknown"
    """
    if "_" in code:
        return "enhanced"
    elif len(code) == 16:
        return "legacy"
    else:
        return "unknown"


def parse_any_code(code: str) -> Union[LegacyDatasetCode, EnhancedDatasetCode]:
    """
    Parse a dataset code in either legacy or enhanced format.

    Args:
        code: Dataset code string (16-char legacy or underscore-separated enhanced)

    Returns:
        LegacyDatasetCode or EnhancedDatasetCode instance

    Raises:
        ValueError: If code cannot be parsed
    """
    format_type = detect_code_format(code)

    if format_type == "legacy":
        return LegacyDatasetCode.from_code(code)
    elif format_type == "enhanced":
        return EnhancedDatasetCode.from_code(code)
    else:
        raise ValueError(f"Cannot detect format of code: '{code}'")


def validate_dataset_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a dataset code string in either legacy or enhanced format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    format_type = detect_code_format(code)

    # Handle legacy 16-character format
    if format_type == "legacy":
        return validate_legacy_code(code)

    # Handle enhanced underscore-separated format
    if format_type == "enhanced":
        try:
            parsed = EnhancedDatasetCode.from_code(code)

            # Validate components
            if parsed.object_type not in DATASET_CODE_COMPONENTS["object_types"]:
                return False, f"Invalid object type: {parsed.object_type}"

            if parsed.regime not in DATASET_CODE_COMPONENTS["regimes"]:
                return False, f"Invalid regime: {parsed.regime}"

            if parsed.event not in DATASET_CODE_COMPONENTS["events"]:
                return False, f"Invalid event: {parsed.event}"

            if parsed.sensor not in DATASET_CODE_COMPONENTS["sensors"]:
                return False, f"Invalid sensor: {parsed.sensor}"

            if parsed.quality_tier not in DATASET_CODE_COMPONENTS["quality_tiers"]:
                return False, f"Invalid quality tier: {parsed.quality_tier}"

            if not 1 <= parsed.time_window_days <= 99:
                return False, f"Invalid time window: {parsed.time_window_days}"

            return True, None

        except ValueError as e:
            return False, str(e)

    return False, f"Unknown code format: '{code}'. Expected 16-char legacy or underscore-separated enhanced format."


# =============================================================================
# YAML CONFIGURATION LOADING
# =============================================================================


def load_dataset_config(config_path: Union[str, Path]) -> DatasetConfig:
    """
    Load dataset configuration from a YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        DatasetConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        yaml_data = yaml.safe_load(f)

    return _parse_yaml_config(yaml_data)


def _parse_yaml_config(data: Dict) -> DatasetConfig:
    """Parse YAML data into DatasetConfig."""
    # Extract sections
    metadata = data.get("metadata", {})
    satellite_selection = data.get("satellite_selection", {})
    time_window = data.get("time_window", {})
    data_sources = data.get("data_sources", {})
    quality_targets = data.get("quality_targets", {})
    processing = data.get("processing", {})
    output = data.get("output", {})
    reproducibility = data.get("reproducibility", {})

    # Build config
    config = DatasetConfig(
        name=metadata.get("name", ""),
        version=metadata.get("version", "1.0.0"),
        description=metadata.get("description", ""),
        regimes=satellite_selection.get("regimes", ["LEO"]),
        object_types=satellite_selection.get("object_types", ["NORM"]),
        min_observations=satellite_selection.get("min_observations", 50),
        target_count=satellite_selection.get("target_count", 40),
        duration_days=time_window.get("duration_days", 7),
        start_date=time_window.get("start_date"),
        primary_source=data_sources.get("primary", "eoobservation"),
        secondary_sources=data_sources.get("secondary", []),
        tier=quality_targets.get("tier", "T2"),
        coverage_min=quality_targets.get("coverage", {}).get("min", 0.02),
        coverage_max=quality_targets.get("coverage", {}).get("max", 0.10),
        track_gap_min_periods=quality_targets.get("track_gaps", {}).get("min_periods", 1.5),
        track_gap_max_periods=quality_targets.get("track_gaps", {}).get("max_periods", 4.0),
        observation_count_min=quality_targets.get("observation_count", {}).get("min", 10),
        observation_count_max=quality_targets.get("observation_count", {}).get("max", 50),
        enable_downsampling=processing.get("downsampling", {}).get("enabled", True),
        preserve_tracks=processing.get("downsampling", {}).get("preserve_tracks", True),
        enable_simulation=processing.get("simulation", {}).get("enabled", False),
        output_format=output.get("format", "json"),
        include_covariance=output.get("include_covariance", True),
        anonymize=output.get("anonymize", True),
        seed=reproducibility.get("seed"),
    )

    return config


def save_dataset_config(config: DatasetConfig, output_path: Union[str, Path]) -> None:
    """
    Save a DatasetConfig to a YAML file.

    Args:
        config: DatasetConfig instance
        output_path: Path for output YAML file
    """
    output_path = Path(output_path)

    # Build YAML structure
    yaml_data = {
        "metadata": {
            "name": config.name,
            "version": config.version,
            "description": config.description,
        },
        "satellite_selection": {
            "regimes": config.regimes,
            "object_types": config.object_types,
            "min_observations": config.min_observations,
            "target_count": config.target_count,
        },
        "time_window": {
            "duration_days": config.duration_days,
            "start_date": config.start_date,
        },
        "data_sources": {
            "primary": config.primary_source,
            "secondary": config.secondary_sources,
        },
        "quality_targets": {
            "tier": config.tier,
            "coverage": {
                "min": config.coverage_min,
                "max": config.coverage_max,
            },
            "track_gaps": {
                "min_periods": config.track_gap_min_periods,
                "max_periods": config.track_gap_max_periods,
            },
            "observation_count": {
                "min": config.observation_count_min,
                "max": config.observation_count_max,
            },
        },
        "processing": {
            "downsampling": {
                "enabled": config.enable_downsampling,
                "preserve_tracks": config.preserve_tracks,
            },
            "simulation": {
                "enabled": config.enable_simulation,
            },
        },
        "output": {
            "format": config.output_format,
            "include_covariance": config.include_covariance,
            "anonymize": config.anonymize,
        },
        "reproducibility": {
            "seed": config.seed,
        },
    }

    with open(output_path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)


def config_to_dataset_code(config: DatasetConfig) -> str:
    """
    Generate an enhanced dataset code from a DatasetConfig.

    Args:
        config: DatasetConfig instance

    Returns:
        Enhanced dataset code string
    """
    # Determine components from config
    regime = config.regimes[0] if config.regimes else "LEO"
    object_type = config.object_types[0] if config.object_types else "NORM"

    # Determine quality tier from tier setting
    tier_map = {"T1": "T1S", "T2": "T2S", "T3": "T3L", "T4": "T4L"}
    quality_tier = tier_map.get(config.tier, "T2S")

    # Determine sensor from sources
    sensor = "EO"
    if "radar" in config.primary_source.lower():
        sensor = "RA"
    elif "rf" in config.primary_source.lower():
        sensor = "RF"
    elif config.secondary_sources:
        sensor = "MX"

    code = EnhancedDatasetCode(
        object_type=object_type,
        regime=regime,
        event="NRM",
        sensor=sensor,
        quality_tier=quality_tier,
        time_window_days=config.duration_days,
        version="001",
    )

    return code.to_code()


# =============================================================================
# METADATA GENERATION
# =============================================================================


def generate_config_hash(config: DatasetConfig) -> str:
    """Generate a hash of the configuration for reproducibility tracking."""
    config_str = json.dumps(asdict(config), sort_keys=True, default=str)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def generate_run_id() -> str:
    """Generate a unique run ID based on timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def generate_dataset_metadata(
    config: DatasetConfig, run_id: str = None, metrics: DatasetMetrics = None
) -> Dict[str, Any]:
    """
    Generate comprehensive metadata for a dataset.

    Args:
        config: DatasetConfig used to generate the dataset
        run_id: Optional run ID (generated if not provided)
        metrics: Optional DatasetMetrics with generation stats

    Returns:
        Metadata dictionary
    """
    if run_id is None:
        run_id = generate_run_id()

    metadata = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "config_hash": generate_config_hash(config),
        "dataset_code": config_to_dataset_code(config),
        "configuration": {
            "name": config.name,
            "version": config.version,
            "description": config.description,
            "tier": config.tier,
            "regimes": config.regimes,
            "object_types": config.object_types,
            "duration_days": config.duration_days,
            "target_satellite_count": config.target_count,
            "seed": config.seed,
        },
        "quality_targets": {
            "coverage_range": [config.coverage_min, config.coverage_max],
            "track_gap_range": [config.track_gap_min_periods, config.track_gap_max_periods],
            "observation_count_range": [config.observation_count_min, config.observation_count_max],
        },
        "processing": {
            "downsampling_enabled": config.enable_downsampling,
            "simulation_enabled": config.enable_simulation,
            "track_preservation": config.preserve_tracks,
        },
        "output_settings": {
            "format": config.output_format,
            "anonymized": config.anonymize,
            "covariance_included": config.include_covariance,
        },
    }

    # Add metrics if provided
    if metrics:
        metadata["metrics"] = {
            "total_api_calls": metrics.total_api_calls,
            "total_records_fetched": metrics.total_records_fetched,
            "api_errors": metrics.api_errors,
            "satellites_processed": metrics.satellites_processed,
            "observations_raw": metrics.observations_raw,
            "observations_final": metrics.observations_final,
            "synthetic_observations": metrics.synthetic_observations,
            "tier_distribution": metrics.tier_distribution,
            "coverage_stats": metrics.coverage_stats,
            "gap_stats": metrics.gap_stats,
        }

    return metadata


def save_dataset_metadata(metadata: Dict[str, Any], output_path: Union[str, Path]) -> None:
    """Save dataset metadata to a JSON file."""
    output_path = Path(output_path)

    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def verify_reproducibility(
    config: DatasetConfig, previous_metadata_path: Union[str, Path]
) -> Tuple[bool, Optional[str]]:
    """
    Verify that a configuration matches a previous run.

    Args:
        config: Current DatasetConfig
        previous_metadata_path: Path to previous run's metadata.json

    Returns:
        Tuple of (matches, difference_description)
    """
    previous_metadata_path = Path(previous_metadata_path)

    if not previous_metadata_path.exists():
        return False, "Previous metadata file not found"

    with open(previous_metadata_path, "r") as f:
        prev_metadata = json.load(f)

    current_hash = generate_config_hash(config)
    previous_hash = prev_metadata.get("config_hash", "")

    if current_hash == previous_hash:
        return True, None

    # Find differences
    differences = []
    prev_config = prev_metadata.get("configuration", {})

    if config.seed != prev_config.get("seed"):
        differences.append(f"seed: {prev_config.get('seed')} -> {config.seed}")
    if config.duration_days != prev_config.get("duration_days"):
        differences.append(
            f"duration_days: {prev_config.get('duration_days')} -> {config.duration_days}"
        )
    if config.regimes != prev_config.get("regimes"):
        differences.append(f"regimes: {prev_config.get('regimes')} -> {config.regimes}")

    return False, "; ".join(differences) if differences else "Configuration hashes differ"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_sample_config(output_path: Union[str, Path] = None) -> DatasetConfig:
    """
    Create a sample dataset configuration.

    Args:
        output_path: Optional path to save YAML file

    Returns:
        Sample DatasetConfig
    """
    config = DatasetConfig(
        name="Sample_LEO_Dataset",
        version="1.0.0",
        description="Sample LEO observation dataset for testing",
        regimes=["LEO"],
        object_types=["NORM"],
        min_observations=50,
        target_count=40,
        duration_days=7,
        start_date=None,
        primary_source="eoobservation",
        secondary_sources=[],
        tier="T2",
        coverage_min=0.02,
        coverage_max=0.10,
        track_gap_min_periods=1.5,
        track_gap_max_periods=4.0,
        observation_count_min=10,
        observation_count_max=50,
        enable_downsampling=True,
        preserve_tracks=True,
        enable_simulation=False,
        output_format="json",
        include_covariance=True,
        anonymize=True,
        seed=42,
    )

    if output_path:
        save_dataset_config(config, output_path)

    return config


def get_downsampling_config_for_tier(tier: str) -> DownsampleConfig:
    """
    Get appropriate DownsampleConfig based on quality tier.

    Args:
        tier: Quality tier (T1, T2, T3, T4)

    Returns:
        DownsampleConfig tuned for the tier
    """
    tier_configs = {
        "T1": DownsampleConfig(
            target_coverage=0.15,
            coverage_tolerance=0.05,
            target_gap=1.0,
            gap_tolerance=0.3,
            max_obs_per_sat=100,
            min_obs_per_sat=20,
        ),
        "T2": DownsampleConfig(
            target_coverage=0.05,
            coverage_tolerance=0.02,
            target_gap=2.0,
            gap_tolerance=0.5,
            max_obs_per_sat=50,
            min_obs_per_sat=5,
        ),
        "T3": DownsampleConfig(
            target_coverage=0.02,
            coverage_tolerance=0.01,
            target_gap=4.0,
            gap_tolerance=1.0,
            max_obs_per_sat=30,
            min_obs_per_sat=3,
        ),
        "T4": DownsampleConfig(
            target_coverage=0.01,
            coverage_tolerance=0.005,
            target_gap=6.0,
            gap_tolerance=2.0,
            max_obs_per_sat=20,
            min_obs_per_sat=3,
        ),
    }

    return tier_configs.get(tier, tier_configs["T2"])
