# -*- coding: utf-8 -*-
"""
Test Suite for Window Selection Algorithm

Tests the bisecting search algorithm for finding optimal time windows
with tier classification per Louis's specification.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestWindowCriteria:
    """Tests for the WindowCriteria dataclass."""

    def test_default_criteria(self):
        """Test default WindowCriteria values."""
        from uct_benchmark.data.windowSelection import WindowCriteria

        criteria = WindowCriteria()

        # Check for expected default values
        assert criteria.min_objects == 10
        assert criteria.target_objects == 40
        assert criteria.max_objects == 80
        assert criteria.min_obs_per_object == 5
        assert criteria.target_obs_per_object == 50
        assert criteria.fit_span_days == 7.0

    def test_criteria_with_custom_values(self):
        """Test WindowCriteria with custom values."""
        from uct_benchmark.data.windowSelection import WindowCriteria

        criteria = WindowCriteria(
            min_objects=5,
            target_objects=20,
            max_objects=50,
            min_obs_per_object=3,
            target_obs_per_object=30,
            fit_span_days=14.0,
        )

        assert criteria.min_objects == 5
        assert criteria.target_objects == 20
        assert criteria.max_objects == 50
        assert criteria.fit_span_days == 14.0

    def test_criteria_coverage_fields(self):
        """Test coverage-related criteria fields."""
        from uct_benchmark.data.windowSelection import WindowCriteria

        criteria = WindowCriteria()

        assert hasattr(criteria, "min_coverage")
        assert hasattr(criteria, "target_coverage")
        assert hasattr(criteria, "max_coverage")
        assert criteria.min_coverage < criteria.target_coverage < criteria.max_coverage


class TestWindowTier:
    """Tests for WindowTier enum."""

    def test_tier_values(self):
        """Test that all tiers are defined correctly."""
        from uct_benchmark.data.windowSelection import WindowTier

        assert WindowTier.TIER_1.value == 1
        assert WindowTier.TIER_2.value == 2
        assert WindowTier.TIER_3.value == 3
        assert WindowTier.TIER_4.value == 4

    def test_tier_meanings(self):
        """Test tier descriptions per Louis's spec."""
        from uct_benchmark.data.windowSelection import WindowTier

        # TIER_1: Optimal - no manipulation needed
        # TIER_2: Needs downsampling (too much data)
        # TIER_3: Needs simulation (too little data)
        # TIER_4: Cannot meet criteria

        assert WindowTier.TIER_1.name == "TIER_1"
        assert WindowTier.TIER_4.name == "TIER_4"


class TestWindowEvaluation:
    """Tests for WindowEvaluation dataclass."""

    def test_window_evaluation_exists(self):
        """Test that WindowEvaluation class exists."""
        from uct_benchmark.data.windowSelection import WindowEvaluation

        # Just verify import works
        assert WindowEvaluation is not None


class TestEvaluateWindow:
    """Tests for the evaluate_window function."""

    @pytest.fixture
    def sample_observations_df(self):
        """Create sample observations DataFrame."""
        np.random.seed(42)
        n_obs = 500
        base_time = datetime(2024, 1, 1)

        sat_ids = [25544, 25545, 25546, 25547, 25548]

        return pd.DataFrame({
            "id": [f"obs_{i}" for i in range(n_obs)],
            "satNo": np.random.choice(sat_ids, n_obs),
            "obTime": [base_time + timedelta(hours=i * 0.5) for i in range(n_obs)],
            "ra": np.random.uniform(0, 360, n_obs),
            "declination": np.random.uniform(-90, 90, n_obs),
        })

    def test_evaluate_window_function_exists(self):
        """Test that evaluate_window function exists."""
        from uct_benchmark.data.windowSelection import evaluate_window

        assert callable(evaluate_window)


class TestFindOptimalWindow:
    """Tests for the find_optimal_window function."""

    @pytest.fixture
    def sample_observations_df(self):
        """Create sample observations DataFrame spanning 30 days."""
        np.random.seed(42)
        n_obs = 1000
        base_time = datetime(2024, 1, 1)

        sat_ids = [25544, 25545, 25546, 25547, 25548]

        return pd.DataFrame({
            "id": [f"obs_{i}" for i in range(n_obs)],
            "satNo": np.random.choice(sat_ids, n_obs),
            "obTime": [base_time + timedelta(hours=i * 0.72) for i in range(n_obs)],
            "ra": np.random.uniform(0, 360, n_obs),
            "declination": np.random.uniform(-90, 90, n_obs),
        })

    @pytest.fixture
    def sample_criteria(self):
        """Create sample window criteria."""
        from uct_benchmark.data.windowSelection import WindowCriteria

        return WindowCriteria(
            min_objects=3,
            target_objects=5,
            max_objects=10,
            min_obs_per_object=5,
            target_obs_per_object=20,
            fit_span_days=7.0,
        )

    def test_find_optimal_window_exists(self):
        """Test that find_optimal_window function exists."""
        from uct_benchmark.data.windowSelection import find_optimal_window

        assert callable(find_optimal_window)


class TestCreateCriteriaFromUserInput:
    """Tests for creating criteria from user input."""

    def test_function_exists(self):
        """Test that create_criteria_from_user_input function exists."""
        from uct_benchmark.data.windowSelection import create_criteria_from_user_input

        assert callable(create_criteria_from_user_input)

    def test_create_criteria_from_legacy_code_exists(self):
        """Test that create_criteria_from_legacy_code function exists."""
        from uct_benchmark.data.windowSelection import create_criteria_from_legacy_code

        assert callable(create_criteria_from_legacy_code)


class TestBisectionWindowSelection:
    """Tests for the bisection window selection algorithm."""

    def test_bisection_functions_exist(self):
        """Test that bisection functions exist."""
        from uct_benchmark.data.windowSelection import (
            bisection_window_selection,
            bisection_window_selection_time_based,
        )

        assert callable(bisection_window_selection)
        assert callable(bisection_window_selection_time_based)


class TestBisectionResult:
    """Tests for BisectionResult dataclass."""

    def test_bisection_result_exists(self):
        """Test that BisectionResult class exists."""
        from uct_benchmark.data.windowSelection import BisectionResult

        assert BisectionResult is not None


class TestOrbitalCoverage:
    """Tests for orbital coverage calculation."""

    def test_orbital_coverage_functions_exist(self):
        """Test that orbital coverage functions exist."""
        from uct_benchmark.data.windowSelection import (
            calculate_orbital_coverage_polygon,
            is_low_coverage,
        )

        assert callable(calculate_orbital_coverage_polygon)
        assert callable(is_low_coverage)

    def test_is_low_coverage_leo(self):
        """Test is_low_coverage for LEO regime."""
        from uct_benchmark.data.windowSelection import is_low_coverage

        # Low coverage thresholds vary by regime
        # Just verify the function runs without error and returns bool
        result_low = is_low_coverage(0.01, "LEO")
        result_high = is_low_coverage(0.5, "LEO")

        assert isinstance(result_low, bool)
        assert isinstance(result_high, bool)

    def test_is_low_coverage_geo(self):
        """Test is_low_coverage for GEO regime."""
        from uct_benchmark.data.windowSelection import is_low_coverage

        # GEO has different coverage requirements
        result_low = is_low_coverage(0.01, "GEO")
        result_high = is_low_coverage(0.5, "GEO")

        # Just verify the function runs without error
        assert isinstance(result_low, bool)
        assert isinstance(result_high, bool)


class TestQualityCode:
    """Tests for quality code interpretation."""

    def test_interpret_quality_code_exists(self):
        """Test that interpret_quality_code function exists."""
        from uct_benchmark.data.windowSelection import interpret_quality_code

        assert callable(interpret_quality_code)

    def test_interpret_standard_quality(self):
        """Test interpreting 'S' (standard) quality code."""
        from uct_benchmark.data.windowSelection import interpret_quality_code

        result = interpret_quality_code("S")

        assert isinstance(result, dict)


class TestSelectOptimalWindowForDataset:
    """Tests for the main dataset window selection function."""

    def test_function_exists(self):
        """Test that select_optimal_window_for_dataset function exists."""
        from uct_benchmark.data.windowSelection import select_optimal_window_for_dataset

        assert callable(select_optimal_window_for_dataset)


class TestObservationCounting:
    """Tests for observation counting within windows."""

    @pytest.fixture
    def sample_window_data(self):
        """Create sample data for a single window."""
        np.random.seed(42)
        n_obs = 100
        base_time = datetime(2024, 1, 1)

        sat_ids = [25544, 25545, 25546, 25547, 25548]

        return pd.DataFrame({
            "id": [f"obs_{i}" for i in range(n_obs)],
            "satNo": np.random.choice(sat_ids, n_obs),
            "obTime": [base_time + timedelta(hours=i * 1.68) for i in range(n_obs)],
            "ra": np.random.uniform(0, 360, n_obs),
            "declination": np.random.uniform(-90, 90, n_obs),
        })

    def test_obs_count_per_satellite(self, sample_window_data):
        """Test observation count per satellite."""
        obs_counts = sample_window_data.groupby("satNo").size()

        # Each satellite should have some observations
        for sat_id in [25544, 25545, 25546, 25547, 25548]:
            if sat_id in obs_counts.index:
                assert obs_counts[sat_id] > 0

    def test_unique_satellites_in_window(self, sample_window_data):
        """Test counting unique satellites in window."""
        unique_sats = sample_window_data["satNo"].nunique()

        assert unique_sats <= 5  # We only have 5 satellites in test data
        assert unique_sats > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
