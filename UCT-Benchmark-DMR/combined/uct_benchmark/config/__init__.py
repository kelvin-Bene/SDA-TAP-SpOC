# -*- coding: utf-8 -*-
"""
UCT Benchmark Configuration Module.

Provides:
- Dataset configuration YAML loading/saving
- Enhanced dataset code parsing
- Metadata generation

Usage:
    from uct_benchmark.config.dataset_schema import (
        load_dataset_config,
        save_dataset_config,
        EnhancedDatasetCode,
        generate_dataset_metadata,
    )
"""

from uct_benchmark.config.dataset_schema import (
    DatasetConfig,
    DownsampleConfig,
    EnhancedDatasetCode,
    config_to_dataset_code,
    create_sample_config,
    generate_config_hash,
    generate_dataset_metadata,
    generate_run_id,
    get_downsampling_config_for_tier,
    load_dataset_config,
    save_dataset_config,
    save_dataset_metadata,
    validate_dataset_code,
    verify_reproducibility,
)

__all__ = [
    "DatasetConfig",
    "DownsampleConfig",
    "EnhancedDatasetCode",
    "load_dataset_config",
    "save_dataset_config",
    "config_to_dataset_code",
    "generate_config_hash",
    "generate_run_id",
    "generate_dataset_metadata",
    "save_dataset_metadata",
    "verify_reproducibility",
    "create_sample_config",
    "get_downsampling_config_for_tier",
    "validate_dataset_code",
]
