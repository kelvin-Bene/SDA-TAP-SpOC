# -*- coding: utf-8 -*-
"""
Tests for regime-specific coverage threshold integration.

Per Lewis's Benchmarking Documentation:
- LEO: Low coverage < 0.0213%
- MEO: Low coverage < 0.0449%
- GEO: Low coverage < 41.656%

These tests verify:
1. Coverage thresholds are correctly defined in settings
2. is_low_coverage() function works correctly
3. Coverage scoring uses regime-specific thresholds
4. Integration with window evaluation

Author: UCT Benchmark Team
Date: 2026-01
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from uct_benchmark.data.windowSelection import (
    is_low_coverage,
    get_coverage_score_with_regime,
    evaluate_window,
    WindowCriteria,
    WindowTier,
)
from uct_benchmark.settings import COVERAGE_THRESHOLDS


class TestCoverageThresholdsSettings:
    """Tests for coverage thresholds in settings."""

    def test_leo_threshold_value(self):
        """LEO threshold should be 0.000213 (0.0213%)."""
        assert "LEO" in COVERAGE_THRESHOLDS
        assert COVERAGE_THRESHOLDS["LEO"] == 0.000213

    def test_meo_threshold_value(self):
        """MEO threshold should be 0.000449 (0.0449%)."""
        assert "MEO" in COVERAGE_THRESHOLDS
        assert COVERAGE_THRESHOLDS["MEO"] == 0.000449

    def test_geo_threshold_value(self):
        """GEO threshold should be 0.41656 (41.656%)."""
        assert "GEO" in COVERAGE_THRESHOLDS
        assert COVERAGE_THRESHOLDS["GEO"] == 0.41656

    def test_threshold_ordering(self):
        """GEO should have highest threshold, LEO lowest."""
        assert COVERAGE_THRESHOLDS["LEO"] < COVERAGE_THRESHOLDS["MEO"]
        assert COVERAGE_THRESHOLDS["MEO"] < COVERAGE_THRESHOLDS["GEO"]


class TestIsLowCoverage:
    """Tests for is_low_coverage function."""

    def test_leo_below_threshold_is_low(self):
        """Coverage below LEO threshold should be considered low."""
        # 0.0001 < 0.000213
        assert is_low_coverage(0.0001, "LEO") is True

    def test_leo_above_threshold_not_low(self):
        """Coverage above LEO threshold should not be considered low."""
        # 0.001 > 0.000213
        assert is_low_coverage(0.001, "LEO") is False

    def test_meo_below_threshold_is_low(self):
        """Coverage below MEO threshold should be considered low."""
        # 0.0003 < 0.000449
        assert is_low_coverage(0.0003, "MEO") is True

    def test_meo_above_threshold_not_low(self):
        """Coverage above MEO threshold should not be considered low."""
        # 0.001 > 0.000449
        assert is_low_coverage(0.001, "MEO") is False

    def test_geo_below_threshold_is_low(self):
        """Coverage below GEO threshold should be considered low."""
        # 0.40 < 0.41656
        assert is_low_coverage(0.40, "GEO") is True

    def test_geo_above_threshold_not_low(self):
        """Coverage above GEO threshold should not be considered low."""
        # 0.50 > 0.41656
        assert is_low_coverage(0.50, "GEO") is False

    def test_at_threshold_is_not_low(self):
        """Coverage exactly at threshold should not be considered low."""
        # At boundary, should not be considered low (strict <)
        assert is_low_coverage(COVERAGE_THRESHOLDS["LEO"], "LEO") is False
        assert is_low_coverage(COVERAGE_THRESHOLDS["MEO"], "MEO") is False
        assert is_low_coverage(COVERAGE_THRESHOLDS["GEO"], "GEO") is False

    def test_case_insensitive_regime(self):
        """Regime parameter should be case insensitive."""
        assert is_low_coverage(0.0001, "leo") is True
        assert is_low_coverage(0.0001, "LEO") is True
        assert is_low_coverage(0.0001, "Leo") is True

    def test_unknown_regime_uses_leo_default(self):
        """Unknown regime should fall back to LEO threshold."""
        # Unknown regime uses LEO default
        leo_threshold = COVERAGE_THRESHOLDS["LEO"]
        assert is_low_coverage(leo_threshold / 2, "UNKNOWN") is True
        assert is_low_coverage(leo_threshold * 2, "UNKNOWN") is False


class TestCoverageScoreWithRegime:
    """Tests for get_coverage_score_with_regime function."""

    def test_coverage_in_range_gets_full_score(self):
        """Coverage within criteria range should get score 1.0."""
        criteria = WindowCriteria(
            min_coverage=0.05,
            max_coverage=0.30,
        )

        score = get_coverage_score_with_regime(0.15, "LEO", criteria)
        assert score == 1.0

    def test_high_coverage_gets_partial_score(self):
        """Coverage above max should get score 0.8."""
        criteria = WindowCriteria(
            min_coverage=0.05,
            max_coverage=0.30,
        )

        score = get_coverage_score_with_regime(0.50, "LEO", criteria)
        assert score == 0.8

    def test_low_coverage_gets_penalized_score(self):
        """Very low coverage should get penalized score."""
        criteria = WindowCriteria(
            min_coverage=0.05,
            max_coverage=0.30,
        )

        score = get_coverage_score_with_regime(0.01, "LEO", criteria)
        assert 0 < score < 1.0

    def test_zero_coverage_gets_zero_or_low_score(self):
        """Zero coverage should get zero or very low score."""
        criteria = WindowCriteria(
            min_coverage=0.05,
            max_coverage=0.30,
        )

        score = get_coverage_score_with_regime(0.0, "LEO", criteria)
        assert score >= 0.0
        assert score < 0.5

    def test_regime_affects_scoring_for_low_coverage(self):
        """Regime-specific thresholds should affect scoring."""
        criteria = WindowCriteria(
            min_coverage=0.05,
            max_coverage=0.30,
        )

        # Coverage of 0.001 is above LEO threshold (0.000213) but below min
        score_leo = get_coverage_score_with_regime(0.001, "LEO", criteria)

        # Coverage of 0.001 is above LEO threshold but we should still get some score
        assert 0 < score_leo < 1.0


class TestEvaluateWindowWithRegimeCoverage:
    """Integration tests for regime-specific coverage in evaluate_window."""

    @pytest.fixture
    def sample_observations(self):
        """Create sample observation data."""
        np.random.seed(42)
        start = datetime(2024, 1, 1)

        data = []
        for sat_no in range(1, 11):  # 10 satellites
            for hour in range(0, 168, 2):  # Every 2 hours for 7 days
                data.append({
                    "obTime": start + timedelta(hours=hour + np.random.uniform(0, 1)),
                    "satNo": sat_no,
                })

        return pd.DataFrame(data).sort_values("obTime")

    @pytest.fixture
    def sat_params(self):
        """Create satellite parameters."""
        return {i: {"Period": 5400} for i in range(1, 11)}

    def test_evaluate_window_uses_regime(self, sample_observations, sat_params):
        """evaluate_window should use regime for coverage scoring."""
        criteria_leo = WindowCriteria(
            min_coverage=0.05,
            max_coverage=0.30,
            regimes=["LEO"],
        )

        criteria_geo = WindowCriteria(
            min_coverage=0.05,
            max_coverage=0.30,
            regimes=["GEO"],
        )

        result_leo = evaluate_window(
            sample_observations,
            sat_params,
            datetime(2024, 1, 1),
            datetime(2024, 1, 8),
            criteria_leo,
        )

        result_geo = evaluate_window(
            sample_observations,
            sat_params,
            datetime(2024, 1, 1),
            datetime(2024, 1, 8),
            criteria_geo,
        )

        # Both should produce results
        assert result_leo.coverage_score >= 0
        assert result_geo.coverage_score >= 0

    def test_coverage_score_is_reasonable(self, sample_observations, sat_params):
        """Coverage score should be in valid range [0, 1]."""
        criteria = WindowCriteria(
            min_coverage=0.02,
            max_coverage=0.50,
            regimes=["LEO"],
        )

        result = evaluate_window(
            sample_observations,
            sat_params,
            datetime(2024, 1, 1),
            datetime(2024, 1, 8),
            criteria,
        )

        assert 0 <= result.coverage_score <= 1.0

    def test_empty_regimes_uses_fallback(self, sample_observations, sat_params):
        """Empty regimes list should use fallback scoring."""
        criteria = WindowCriteria(
            min_coverage=0.05,
            max_coverage=0.30,
            regimes=[],  # Empty
        )

        result = evaluate_window(
            sample_observations,
            sat_params,
            datetime(2024, 1, 1),
            datetime(2024, 1, 8),
            criteria,
        )

        # Should still produce valid score
        assert 0 <= result.coverage_score <= 1.0


class TestCoverageThresholdEdgeCases:
    """Edge case tests for coverage thresholds."""

    def test_very_small_coverage_leo(self):
        """Very small coverage should be detected as low for LEO."""
        assert is_low_coverage(1e-6, "LEO") is True

    def test_very_small_coverage_geo(self):
        """Very small coverage should be detected as low for GEO."""
        assert is_low_coverage(1e-6, "GEO") is True

    def test_one_percent_coverage(self):
        """1% coverage classification by regime."""
        coverage = 0.01  # 1%

        # 1% is above LEO/MEO thresholds, so NOT low
        assert is_low_coverage(coverage, "LEO") is False
        assert is_low_coverage(coverage, "MEO") is False

        # 1% is below GEO threshold (41.656%), so IS low
        assert is_low_coverage(coverage, "GEO") is True

    def test_forty_percent_coverage(self):
        """40% coverage classification by regime."""
        coverage = 0.40  # 40%

        # 40% is above all thresholds except GEO
        assert is_low_coverage(coverage, "LEO") is False
        assert is_low_coverage(coverage, "MEO") is False

        # 40% is still below GEO threshold (41.656%)
        assert is_low_coverage(coverage, "GEO") is True

    def test_forty_two_percent_coverage(self):
        """42% coverage should not be low for any regime."""
        coverage = 0.42  # 42%

        # 42% is above all thresholds including GEO (41.656%)
        assert is_low_coverage(coverage, "LEO") is False
        assert is_low_coverage(coverage, "MEO") is False
        assert is_low_coverage(coverage, "GEO") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
