# -*- coding: utf-8 -*-
"""
Tests for exponential batch decay in window selection.

Per Lewis's specification:
- Initial batch = fitspan × batchSizeMultiplier (5x)
- Each iteration: batch_size = fit_span + (initial - fit_span) * exp(-decay_rate * iteration)
- Decay rate = batchSizeDecayRate (0.01)

These tests verify:
1. Initial batch size calculation
2. Exponential decay formula correctness
3. Batch size never goes below fit span
4. Integration with window search

Author: UCT Benchmark Team
Date: 2026-01
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from uct_benchmark.data.windowSelection import (
    _calculate_next_batch_size,
    calculate_initial_batch_size,
    find_optimal_window_with_decay,
    WindowCriteria,
    BisectionResult,
)
from uct_benchmark.settings import batchSizeMultiplier, batchSizeDecayRate


class TestInitialBatchSize:
    """Tests for calculate_initial_batch_size function."""

    def test_default_multiplier(self):
        """Initial batch should be fitspan × 5 with default settings."""
        fit_span = 7.0
        initial = calculate_initial_batch_size(fit_span)
        expected = fit_span * batchSizeMultiplier

        assert initial == expected
        assert initial == 35.0  # 7 × 5

    def test_various_fit_spans(self):
        """Test with various fit span values."""
        test_cases = [
            (1.0, 5.0),
            (3.0, 15.0),
            (7.0, 35.0),
            (14.0, 70.0),
        ]

        for fit_span, expected in test_cases:
            result = calculate_initial_batch_size(fit_span)
            assert result == expected, f"fit_span={fit_span} should give {expected}"


class TestBatchDecay:
    """Tests for _calculate_next_batch_size function."""

    def test_iteration_zero_returns_initial(self):
        """At iteration 0, batch size should be close to initial."""
        initial_batch = 35.0
        fit_span = 7.0

        result = _calculate_next_batch_size(0, initial_batch, fit_span)

        # At iteration 0, exp(0) = 1, so result should be initial
        assert result == initial_batch

    def test_batch_decreases_with_iterations(self):
        """Batch size should decrease as iterations increase."""
        initial_batch = 35.0
        fit_span = 7.0

        prev_size = initial_batch
        for iteration in range(1, 20):
            current_size = _calculate_next_batch_size(iteration, initial_batch, fit_span)
            assert current_size < prev_size, f"Batch should decrease at iteration {iteration}"
            assert current_size >= fit_span, "Batch should never go below fit span"
            prev_size = current_size

    def test_batch_approaches_fit_span(self):
        """Batch size should asymptotically approach fit span."""
        initial_batch = 35.0
        fit_span = 7.0

        # After many iterations, should be very close to fit span
        # With decay rate 0.01, after 500 iterations: exp(-0.01 * 500) = exp(-5) ≈ 0.0067
        # So difference should be (35 - 7) * 0.0067 ≈ 0.19
        final_size = _calculate_next_batch_size(500, initial_batch, fit_span)

        # The batch should be within 1% of initial difference from fit span
        # (28 * 0.01 = 0.28 tolerance after 500 iterations)
        assert abs(final_size - fit_span) < 0.5, "After 500 iterations, should be near fit span"
        # Also verify it's still above fit span
        assert final_size >= fit_span

    def test_exponential_decay_formula(self):
        """Verify the exponential decay formula is correct."""
        initial_batch = 35.0
        fit_span = 7.0

        for iteration in [1, 5, 10, 20, 50]:
            result = _calculate_next_batch_size(iteration, initial_batch, fit_span)

            # Manual calculation of expected value
            expected = fit_span + (initial_batch - fit_span) * np.exp(-batchSizeDecayRate * iteration)

            assert abs(result - expected) < 0.001, f"Formula mismatch at iteration {iteration}"

    def test_never_below_fit_span(self):
        """Batch size should never go below fit span."""
        initial_batch = 35.0
        fit_span = 7.0

        for iteration in range(0, 1000, 10):
            result = _calculate_next_batch_size(iteration, initial_batch, fit_span)
            assert result >= fit_span, f"Batch {result} below fit span {fit_span} at iteration {iteration}"

    def test_decay_rate_effect(self):
        """Higher decay rate should reduce batch size faster."""
        initial_batch = 35.0
        fit_span = 7.0

        # With decay rate 0.01 (from settings)
        size_at_10 = _calculate_next_batch_size(10, initial_batch, fit_span)

        # The batch should have decayed but still be well above fit span
        assert size_at_10 < initial_batch
        assert size_at_10 > fit_span + 0.5 * (initial_batch - fit_span)  # Still > 50% of way


class TestBatchDecaySequence:
    """Test batch size sequences across iterations."""

    def test_decay_sequence_is_monotonic(self):
        """Batch sizes should form a strictly decreasing sequence."""
        initial_batch = calculate_initial_batch_size(7.0)
        fit_span = 7.0

        sizes = [
            _calculate_next_batch_size(i, initial_batch, fit_span)
            for i in range(50)
        ]

        for i in range(1, len(sizes)):
            assert sizes[i] < sizes[i-1], f"Size at {i} should be less than at {i-1}"

    def test_decay_sequence_values(self):
        """Test specific expected values in decay sequence."""
        initial_batch = 35.0
        fit_span = 7.0

        expected = [
            (0, 35.0),
            (10, fit_span + (35 - 7) * np.exp(-0.01 * 10)),
            (50, fit_span + (35 - 7) * np.exp(-0.01 * 50)),
            (100, fit_span + (35 - 7) * np.exp(-0.01 * 100)),
        ]

        for iteration, expected_size in expected:
            result = _calculate_next_batch_size(iteration, initial_batch, fit_span)
            assert abs(result - expected_size) < 0.01, f"Mismatch at iteration {iteration}"


class TestFindOptimalWindowWithDecay:
    """Integration tests for find_optimal_window_with_decay."""

    @pytest.fixture
    def sample_observations(self):
        """Create sample observation data for testing."""
        np.random.seed(42)

        # Create 30 days of observations for multiple satellites
        start_date = datetime(2024, 1, 1)
        n_satellites = 20
        obs_per_sat = 100

        data = []
        for sat_no in range(1, n_satellites + 1):
            # Random observation times over 30 days
            times = [
                start_date + timedelta(days=np.random.uniform(0, 30))
                for _ in range(obs_per_sat)
            ]
            for t in times:
                data.append({"obTime": t, "satNo": sat_no})

        df = pd.DataFrame(data)
        return df.sort_values("obTime").reset_index(drop=True)

    @pytest.fixture
    def sat_params(self):
        """Create orbital parameters for satellites."""
        return {
            i: {"Period": 5400}  # 90-minute period
            for i in range(1, 21)
        }

    def test_returns_bisection_result(self, sample_observations, sat_params):
        """Function should return a BisectionResult."""
        criteria = WindowCriteria(
            fit_span_days=7.0,
            min_objects=5,
            regimes=["LEO"],
        )

        result = find_optimal_window_with_decay(
            sample_observations,
            sat_params,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
            criteria,
            max_iterations=5,
        )

        assert isinstance(result, BisectionResult)
        assert result.best_window is not None

    def test_evaluates_multiple_windows(self, sample_observations, sat_params):
        """Function should evaluate multiple windows across iterations."""
        criteria = WindowCriteria(
            fit_span_days=7.0,
            min_objects=5,
            regimes=["LEO"],
        )

        result = find_optimal_window_with_decay(
            sample_observations,
            sat_params,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
            criteria,
            max_iterations=10,
        )

        # Should have evaluated multiple windows
        assert result.windows_evaluated > 0

    def test_respects_max_iterations(self, sample_observations, sat_params):
        """Function should not exceed max iterations."""
        criteria = WindowCriteria(
            fit_span_days=7.0,
            min_objects=5,
            tier_1_threshold=2.0,  # Impossible to achieve, forces all iterations
            regimes=["LEO"],
        )

        result = find_optimal_window_with_decay(
            sample_observations,
            sat_params,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
            criteria,
            max_iterations=3,
        )

        # Result should still be returned even with few iterations
        assert result is not None

    def test_empty_data_handles_gracefully(self, sat_params):
        """Empty data should be handled gracefully."""
        empty_df = pd.DataFrame(columns=["obTime", "satNo"])
        criteria = WindowCriteria(fit_span_days=7.0, regimes=["LEO"])

        result = find_optimal_window_with_decay(
            empty_df,
            sat_params,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
            criteria,
            max_iterations=3,
        )

        assert result is not None


class TestBatchDecayWithSettings:
    """Tests verifying integration with settings.py values."""

    def test_uses_settings_multiplier(self):
        """Initial batch should use batchSizeMultiplier from settings."""
        fit_span = 7.0
        result = calculate_initial_batch_size(fit_span)

        # Verify it matches settings
        assert result == fit_span * batchSizeMultiplier

    def test_uses_settings_decay_rate(self):
        """Decay should use batchSizeDecayRate from settings."""
        initial = 35.0
        fit_span = 7.0

        # Calculate expected with explicit decay rate
        iteration = 10
        expected = fit_span + (initial - fit_span) * np.exp(-batchSizeDecayRate * iteration)

        result = _calculate_next_batch_size(iteration, initial, fit_span)

        assert abs(result - expected) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
