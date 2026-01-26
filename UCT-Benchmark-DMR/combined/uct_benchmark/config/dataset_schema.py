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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import yaml

from uct_benchmark.settings import (
    DATASET_CODE_COMPONENTS,
    DatasetConfig,
    DatasetMetrics,
    DownsampleConfig,
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


def validate_dataset_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a dataset code string.

    Returns:
        Tuple of (is_valid, error_message)
    """
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
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


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
        "generated_at": datetime.utcnow().isoformat() + "Z",
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
