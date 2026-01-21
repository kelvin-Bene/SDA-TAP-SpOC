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
    EnhancedDatasetCode,
    load_dataset_config,
    save_dataset_config,
    config_to_dataset_code,
    generate_config_hash,
    generate_run_id,
    generate_dataset_metadata,
    save_dataset_metadata,
    verify_reproducibility,
    create_sample_config,
    get_downsampling_config_for_tier,
    validate_dataset_code,
)

__all__ = [
    'EnhancedDatasetCode',
    'load_dataset_config',
    'save_dataset_config',
    'config_to_dataset_code',
    'generate_config_hash',
    'generate_run_id',
    'generate_dataset_metadata',
    'save_dataset_metadata',
    'verify_reproducibility',
    'create_sample_config',
    'get_downsampling_config_for_tier',
    'validate_dataset_code',
]
