# -*- coding: utf-8 -*-
"""
Tests for dataset configuration and metadata generation.

Tests:
- Enhanced dataset code parsing
- YAML configuration loading/saving
- Metadata generation
"""

import tempfile

import pytest


class TestEnhancedDatasetCode:
    """Tests for enhanced dataset code parsing."""

    def test_create_code(self):
        """Test creating a dataset code."""
        from uct_benchmark.config.dataset_schema import EnhancedDatasetCode

        code = EnhancedDatasetCode(
            object_type="NORM",
            regime="LEO",
            event="NRM",
            sensor="EO",
            quality_tier="T2S",
            time_window_days=7,
            version="001",
        )

        code_str = code.to_code()
        assert code_str == "NORM_LEO_NRM_EO_T2S_07D_001"

    def test_parse_code(self):
        """Test parsing a dataset code string."""
        from uct_benchmark.config.dataset_schema import EnhancedDatasetCode

        code_str = "HAMR_GEO_MAN_MX_T3L_14D_002"
        parsed = EnhancedDatasetCode.from_code(code_str)

        assert parsed.object_type == "HAMR"
        assert parsed.regime == "GEO"
        assert parsed.event == "MAN"
        assert parsed.sensor == "MX"
        assert parsed.quality_tier == "T3L"
        assert parsed.time_window_days == 14
        assert parsed.version == "002"

    def test_get_tier_number(self):
        """Test extracting tier number."""
        from uct_benchmark.config.dataset_schema import EnhancedDatasetCode

        code = EnhancedDatasetCode(quality_tier="T2S")
        assert code.get_tier_number() == 2

        code = EnhancedDatasetCode(quality_tier="T3L")
        assert code.get_tier_number() == 3

    def test_get_quality_level(self):
        """Test extracting quality level."""
        from uct_benchmark.config.dataset_schema import EnhancedDatasetCode

        code = EnhancedDatasetCode(quality_tier="T2S")
        assert code.get_quality_level() == "S"

        code = EnhancedDatasetCode(quality_tier="T1H")
        assert code.get_quality_level() == "H"

    def test_validate_valid_code(self):
        """Test validating a valid code."""
        from uct_benchmark.config.dataset_schema import validate_dataset_code

        is_valid, error = validate_dataset_code("NORM_LEO_NRM_EO_T2S_07D_001")
        assert is_valid
        assert error is None

    def test_validate_invalid_regime(self):
        """Test validating code with invalid regime."""
        from uct_benchmark.config.dataset_schema import validate_dataset_code

        is_valid, error = validate_dataset_code("NORM_XXX_NRM_EO_T2S_07D_001")
        assert not is_valid
        assert "regime" in error.lower()


class TestYAMLConfig:
    """Tests for YAML configuration loading and saving."""

    def test_save_and_load_config(self):
        """Test saving and loading a configuration."""
        from uct_benchmark.config import DatasetConfig
        from uct_benchmark.config.dataset_schema import load_dataset_config, save_dataset_config

        config = DatasetConfig(
            name="Test Dataset",
            version="1.0.0",
            regimes=["LEO", "MEO"],
            duration_days=14,
            seed=42,
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            save_dataset_config(config, f.name)
            loaded = load_dataset_config(f.name)

        assert loaded.name == config.name
        assert loaded.version == config.version
        assert loaded.regimes == config.regimes
        assert loaded.duration_days == config.duration_days
        assert loaded.seed == config.seed

    def test_load_missing_file(self):
        """Test loading non-existent file raises error."""
        from uct_benchmark.config.dataset_schema import load_dataset_config

        with pytest.raises(FileNotFoundError):
            load_dataset_config("/nonexistent/path/config.yaml")

    def test_create_sample_config(self):
        """Test creating a sample configuration."""
        from uct_benchmark.config.dataset_schema import create_sample_config

        config = create_sample_config()

        assert config.name == "Sample_LEO_Dataset"
        assert config.seed == 42


class TestMetadataGeneration:
    """Tests for metadata generation."""

    def test_generate_config_hash(self):
        """Test config hash generation."""
        from uct_benchmark.config import DatasetConfig
        from uct_benchmark.config.dataset_schema import generate_config_hash

        config = DatasetConfig(name="Test", seed=42)
        hash1 = generate_config_hash(config)

        # Same config should produce same hash
        hash2 = generate_config_hash(config)
        assert hash1 == hash2

        # Different config should produce different hash
        config.seed = 43
        hash3 = generate_config_hash(config)
        assert hash1 != hash3

    def test_generate_run_id(self):
        """Test run ID generation."""
        from uct_benchmark.config.dataset_schema import generate_run_id

        run_id = generate_run_id()

        # Should be timestamp format
        assert len(run_id) == 15  # YYYYMMDD_HHMMSS
        assert "_" in run_id

    def test_generate_dataset_metadata(self):
        """Test dataset metadata generation."""
        from uct_benchmark.config import DatasetConfig
        from uct_benchmark.config.dataset_schema import generate_dataset_metadata

        config = DatasetConfig(
            name="Test Dataset",
            version="1.0.0",
            tier="T2",
            seed=42,
        )

        metadata = generate_dataset_metadata(config, run_id="test_run_001")

        assert metadata["run_id"] == "test_run_001"
        assert "generated_at" in metadata
        assert "config_hash" in metadata
        assert "dataset_code" in metadata
        assert metadata["configuration"]["name"] == "Test Dataset"
        assert metadata["configuration"]["seed"] == 42

    def test_config_to_dataset_code(self):
        """Test generating dataset code from config."""
        from uct_benchmark.config import DatasetConfig
        from uct_benchmark.config.dataset_schema import config_to_dataset_code

        config = DatasetConfig(
            regimes=["LEO"],
            object_types=["NORM"],
            tier="T2",
            duration_days=7,
        )

        code = config_to_dataset_code(config)

        assert "NORM" in code
        assert "LEO" in code
        assert "T2" in code
        assert "07D" in code

    def test_get_downsampling_config_for_tier(self):
        """Test getting downsampling config by tier."""
        from uct_benchmark.config.dataset_schema import get_downsampling_config_for_tier

        t1_config = get_downsampling_config_for_tier("T1")
        t4_config = get_downsampling_config_for_tier("T4")

        # T1 should have more coverage than T4
        assert t1_config.target_coverage > t4_config.target_coverage
        # T4 should have larger gaps than T1
        assert t4_config.target_gap > t1_config.target_gap


class TestLoggingConfig:
    """Tests for logging configuration."""

    def test_metrics_collector(self):
        """Test metrics collector."""
        from uct_benchmark.logging_config import MetricsCollector

        collector = MetricsCollector(run_id="test_001")

        collector.log_api_call(
            service="eoobservation",
            params={"satNo": "25544"},
            records=100,
            elapsed_ms=500,
        )

        summary = collector.get_summary()
        assert summary["run_id"] == "test_001"
        assert summary["api_calls"] == 1
        assert summary["api_errors"] == 0

    def test_performance_timer(self):
        """Test performance timer."""
        import time

        from uct_benchmark.logging_config import PerformanceTimer

        with PerformanceTimer("test_operation") as timer:
            time.sleep(0.1)

        assert timer.elapsed_seconds >= 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
