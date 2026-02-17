# -*- coding: utf-8 -*-
"""
Tests for API enhancements.

Tests:
- Response caching
- Regime detection
- Count-first query strategy
- Service wrappers
"""

import pandas as pd
import pytest

# Check if orekit/jpype is available - these tests require it for imports
try:
    from uct_benchmark.api.apiIntegration import QueryCache
    OREKIT_AVAILABLE = True
except (ImportError, ModuleNotFoundError, OSError, RuntimeError):
    OREKIT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not OREKIT_AVAILABLE,
    reason="orekit_jpype/jpype not available - required for apiIntegration imports"
)


class TestQueryCache:
    """Tests for the QueryCache class."""

    def test_cache_creation(self):
        """Test cache can be created with custom parameters."""
        from uct_benchmark.api.apiIntegration import QueryCache

        cache = QueryCache(max_size=100, ttl_seconds=60)
        assert cache._max_size == 100
        assert cache._ttl_seconds == 60

    def test_cache_set_get(self):
        """Test basic cache set and get operations."""
        from uct_benchmark.api.apiIntegration import QueryCache

        cache = QueryCache(max_size=10, ttl_seconds=300)

        # Set a value
        test_data = pd.DataFrame({"col": [1, 2, 3]})
        cache.set("eoobservation", {"satNo": "25544"}, test_data)

        # Get the value back
        result = cache.get("eoobservation", {"satNo": "25544"})
        assert result is not None
        assert len(result) == 3

    def test_cache_miss(self):
        """Test cache returns None for missing keys."""
        from uct_benchmark.api.apiIntegration import QueryCache

        cache = QueryCache()
        result = cache.get("nonexistent", {"param": "value"})
        assert result is None

    def test_cache_clear(self):
        """Test cache clear operation."""
        from uct_benchmark.api.apiIntegration import QueryCache

        cache = QueryCache()
        cache.set("service", {"p": 1}, pd.DataFrame({"a": [1]}))
        cache.clear()

        result = cache.get("service", {"p": 1})
        assert result is None


class TestRegimeDetection:
    """Tests for orbital regime detection."""

    def test_leo_detection(self):
        """Test LEO regime detection."""
        from uct_benchmark.api.apiIntegration import determine_orbital_regime

        # ISS altitude ~420 km, SMA ~6800 km
        regime = determine_orbital_regime(6800)
        assert regime == "LEO"

    def test_meo_detection(self):
        """Test MEO regime detection."""
        from uct_benchmark.api.apiIntegration import determine_orbital_regime

        # GPS altitude ~20200 km, SMA ~26560 km
        regime = determine_orbital_regime(26560)
        assert regime == "MEO"

    def test_geo_detection(self):
        """Test GEO regime detection."""
        from uct_benchmark.api.apiIntegration import determine_orbital_regime

        # GEO altitude ~35786 km, SMA ~42164 km
        regime = determine_orbital_regime(42164)
        assert regime == "GEO"

    def test_heo_detection(self):
        """Test HEO regime detection based on eccentricity."""
        from uct_benchmark.api.apiIntegration import determine_orbital_regime

        # Molniya orbit with high eccentricity
        regime = determine_orbital_regime(26560, eccentricity=0.74)
        assert regime == "HEO"

    def test_batch_size_for_regime(self):
        """Test regime-specific batch sizes."""
        from uct_benchmark.api.apiIntegration import get_batch_size_for_regime

        leo_batch = get_batch_size_for_regime("LEO")
        geo_batch = get_batch_size_for_regime("GEO")

        # GEO should have longer batch size due to lower obs density
        assert geo_batch > leo_batch


class TestAPIMetrics:
    """Tests for API call logging and metrics."""

    def test_log_api_call(self):
        """Test API call logging."""
        from uct_benchmark.api.apiIntegration import (
            _log_api_call,
            get_api_metrics,
            reset_api_metrics,
        )

        reset_api_metrics()

        _log_api_call("eoobservation", {"satNo": "25544"}, 100, 0.5)

        metrics = get_api_metrics()
        assert metrics["total_calls"] == 1
        assert metrics["total_records"] == 100
        assert metrics["total_errors"] == 0

    def test_log_api_error(self):
        """Test API error logging."""
        from uct_benchmark.api.apiIntegration import (
            _log_api_call,
            get_api_metrics,
            reset_api_metrics,
        )

        reset_api_metrics()

        _log_api_call(
            "eoobservation", {"satNo": "25544"}, 0, 0.5, success=False, error_msg="Test error"
        )

        metrics = get_api_metrics()
        assert metrics["total_errors"] == 1


class TestDatetimeConversion:
    """Tests for datetime conversion functions."""

    def test_datetime_to_udl(self):
        """Test datetime to UDL format conversion."""
        import datetime

        from uct_benchmark.api.apiIntegration import datetimeToUDL

        dt = datetime.datetime(2025, 1, 15, 12, 30, 45, 123456)
        result = datetimeToUDL(dt)

        assert "2025-01-15" in result
        assert "12:30:45" in result
        assert result.endswith("Z")

    def test_udl_to_datetime(self):
        """Test UDL format to datetime conversion."""
        from uct_benchmark.api.apiIntegration import UDLToDatetime

        udl_time = "2025-01-15T12:30:45.123456Z"
        result = UDLToDatetime(udl_time)

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
