"""
Unit tests for the compute_config_hash utility.

Run with: uv run pytest backend_api/tests/test_config_hash.py -v
"""

import pytest

from uct_benchmark.api.apiIntegration import compute_config_hash


class TestConfigHashDeterminism:
    """Test that compute_config_hash is deterministic."""

    def test_same_config_same_hash(self):
        """Same config always produces same hash."""
        config = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544, 28654],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "search_strategy": "hybrid",
            "sensors": ["optical"],
            "coverage": "standard",
            "include_hamr": False,
        }
        hash1 = compute_config_hash(config)
        hash2 = compute_config_hash(config)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_different_regime_different_hash(self):
        """Different regimes produce different hashes."""
        base = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        config2 = {**base, "regime": "GEO"}
        assert compute_config_hash(base) != compute_config_hash(config2)

    def test_different_tier_different_hash(self):
        """Different tiers produce different hashes."""
        base = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        config2 = {**base, "tier": "T2"}
        assert compute_config_hash(base) != compute_config_hash(config2)

    def test_different_satellites_different_hash(self):
        """Different satellite lists produce different hashes."""
        base = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        config2 = {**base, "satellites": [25544, 28654]}
        assert compute_config_hash(base) != compute_config_hash(config2)

    def test_different_timeframe_different_hash(self):
        """Different timeframes produce different hashes."""
        base = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        config2 = {**base, "timeframe": 14}
        assert compute_config_hash(base) != compute_config_hash(config2)


class TestConfigHashOrderIndependence:
    """Test that list ordering does not affect hash."""

    def test_satellite_order_independent(self):
        """Satellite list order doesn't affect hash."""
        config1 = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544, 28654, 43013],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        config2 = {**config1, "satellites": [43013, 25544, 28654]}
        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_sensor_order_independent(self):
        """Sensor list order doesn't affect hash."""
        config1 = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical", "radar"],
        }
        config2 = {**config1, "sensors": ["radar", "optical"]}
        assert compute_config_hash(config1) == compute_config_hash(config2)


class TestConfigHashEdgeCases:
    """Test edge cases for config hash."""

    def test_empty_satellites(self):
        """Empty satellite list produces valid hash."""
        config = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        result = compute_config_hash(config)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_missing_optional_keys(self):
        """Missing optional keys don't cause errors."""
        config = {
            "regime": "LEO",
            "tier": "T1",
            "timeframe": 7,
        }
        result = compute_config_hash(config)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_none_values_handled(self):
        """None values are handled gracefully."""
        config = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": None,
            "timeframe": 7,
            "timeunit": "days",
            "start_date": None,
            "end_date": None,
        }
        # Should not raise; satellites=None treated as empty list internally
        result = compute_config_hash(config)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_disabled_downsampling_ignored(self):
        """Disabled downsampling does not affect hash."""
        base = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        with_disabled_ds = {
            **base,
            "downsampling": {"enabled": False, "target_coverage": 0.5},
        }
        assert compute_config_hash(base) == compute_config_hash(with_disabled_ds)

    def test_enabled_downsampling_affects_hash(self):
        """Enabled downsampling changes the hash."""
        base = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        with_ds = {
            **base,
            "downsampling": {"enabled": True, "target_coverage": 0.5},
        }
        assert compute_config_hash(base) != compute_config_hash(with_ds)

    def test_disabled_simulation_ignored(self):
        """Disabled simulation does not affect hash."""
        base = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        with_disabled_sim = {
            **base,
            "simulation": {"enabled": False, "fill_gaps": True},
        }
        assert compute_config_hash(base) == compute_config_hash(with_disabled_sim)

    def test_enabled_simulation_affects_hash(self):
        """Enabled simulation changes the hash."""
        base = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "sensors": ["optical"],
        }
        with_sim = {
            **base,
            "simulation": {"enabled": True, "fill_gaps": True, "sensor_model": "GEODSS"},
        }
        assert compute_config_hash(base) != compute_config_hash(with_sim)

    def test_hash_is_hex_string(self):
        """Hash is a valid hex string."""
        config = {"regime": "LEO", "tier": "T1", "timeframe": 7}
        result = compute_config_hash(config)
        # Should be valid hex
        int(result, 16)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
