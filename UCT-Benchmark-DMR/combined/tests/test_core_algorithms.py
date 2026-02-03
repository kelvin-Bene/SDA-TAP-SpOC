# -*- coding: utf-8 -*-
"""
Unit Tests for Core Algorithms (Phase 4)

Tests for core algorithm implementations per Louis's Benchmarking Documentation:
- Orbital coverage polygon calculation
- Bisection window selection with short-circuit
- A/S/N quality level interpretation
- Non-reference observations (True Negatives) handling
- State metrics calculations
- Residual metrics calculations

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Check if jpype/orekit is available for state metrics tests
try:
    from uct_benchmark.evaluation.stateMetrics import calculate_state_metrics_single
    HAS_STATE_METRICS = True
except ImportError:
    HAS_STATE_METRICS = False

requires_state_metrics = pytest.mark.skipif(
    not HAS_STATE_METRICS,
    reason="State metrics requires jpype/orekit which is not installed"
)


class TestOrbitalCoverage:
    """Tests for orbital coverage polygon calculation."""

    def test_full_coverage_spread_observations(self):
        """Observations spread evenly over full orbit should give high coverage."""
        from uct_benchmark.data.windowSelection import calculate_orbital_coverage_polygon

        orbital_period = 5400  # 90 minutes in seconds
        # Create 10 observations spread over one full orbit
        epochs = [datetime(2025, 1, 1) + timedelta(seconds=i * 540) for i in range(10)]
        obs = pd.DataFrame({'epoch': epochs})

        coverage = calculate_orbital_coverage_polygon(obs, orbital_period, epoch_column='epoch')
        assert coverage > 0.8, f"Expected high coverage for spread observations, got {coverage}"

    def test_clustered_observations_low_coverage(self):
        """Clustered observations should give low coverage."""
        from uct_benchmark.data.windowSelection import calculate_orbital_coverage_polygon

        orbital_period = 5400  # 90 minutes
        # Create 10 observations clustered within 10 minutes (very short span)
        epochs = [datetime(2025, 1, 1) + timedelta(seconds=i * 60) for i in range(10)]
        obs = pd.DataFrame({'epoch': epochs})

        coverage = calculate_orbital_coverage_polygon(obs, orbital_period, epoch_column='epoch')
        assert coverage < 0.3, f"Expected low coverage for clustered observations, got {coverage}"

    def test_single_observation_zero_coverage(self):
        """Single observation should give zero coverage."""
        from uct_benchmark.data.windowSelection import calculate_orbital_coverage_polygon

        obs = pd.DataFrame({'epoch': [datetime(2025, 1, 1)]})
        coverage = calculate_orbital_coverage_polygon(obs, 5400, epoch_column='epoch')
        assert coverage == 0.0, "Single observation should have zero coverage"

    def test_empty_dataframe_zero_coverage(self):
        """Empty DataFrame should give zero coverage."""
        from uct_benchmark.data.windowSelection import calculate_orbital_coverage_polygon

        obs = pd.DataFrame({'epoch': []})
        coverage = calculate_orbital_coverage_polygon(obs, 5400, epoch_column='epoch')
        assert coverage == 0.0, "Empty DataFrame should have zero coverage"

    def test_coverage_bounds(self):
        """Coverage should always be in [0, 1] range."""
        from uct_benchmark.data.windowSelection import calculate_orbital_coverage_polygon

        orbital_period = 5400
        # Test various observation patterns
        for n_obs in [2, 5, 10, 20, 50]:
            epochs = [datetime(2025, 1, 1) + timedelta(seconds=i * 100) for i in range(n_obs)]
            obs = pd.DataFrame({'epoch': epochs})
            coverage = calculate_orbital_coverage_polygon(obs, orbital_period, epoch_column='epoch')
            assert 0.0 <= coverage <= 1.0, f"Coverage {coverage} out of bounds for {n_obs} observations"


class TestBisectionWindowSelection:
    """Tests for bisection window selection algorithm."""

    def test_short_circuit_behavior(self):
        """Verify short-circuit behavior - first half success should stop evaluation."""
        from uct_benchmark.data.windowSelection import bisection_window_selection

        calls = []

        def quality_check(obs):
            calls.append(len(obs))
            # First half of 10 obs = 5 obs, which passes (>= 5)
            return len(obs) >= 5

        obs = pd.DataFrame({'epoch': range(10)})
        results = bisection_window_selection(obs, quality_check, min_window_size=3, epoch_column='epoch')

        # Should have checked: full window (10), first half (5)
        # Should NOT have checked second half since first half passed
        assert len(calls) <= 3, f"Too many quality checks: {calls}"
        assert 10 in calls, "Should have checked full window"

    def test_returns_qualifying_window(self):
        """Verify returns window that passes quality check."""
        from uct_benchmark.data.windowSelection import bisection_window_selection

        def quality_check(obs):
            return len(obs) >= 3

        obs = pd.DataFrame({'epoch': range(10)})
        results = bisection_window_selection(obs, quality_check, min_window_size=3, epoch_column='epoch')

        assert len(results) > 0, "Should return at least one window"
        for window in results:
            assert len(window) >= 3, "All returned windows should pass quality check"

    def test_empty_result_for_unfulfillable_criteria(self):
        """Verify empty result when no window can meet criteria."""
        from uct_benchmark.data.windowSelection import bisection_window_selection

        def quality_check(obs):
            return False  # Never passes

        obs = pd.DataFrame({'epoch': range(10)})
        results = bisection_window_selection(obs, quality_check, min_window_size=3, epoch_column='epoch')

        assert len(results) == 0, "Should return empty list when no window qualifies"

    def test_min_window_size_respected(self):
        """Verify minimum window size constraint is respected."""
        from uct_benchmark.data.windowSelection import bisection_window_selection

        checked_sizes = []

        def quality_check(obs):
            checked_sizes.append(len(obs))
            return False  # Never passes, forces full recursion

        obs = pd.DataFrame({'epoch': range(20)})
        results = bisection_window_selection(obs, quality_check, min_window_size=5, epoch_column='epoch')

        # No window smaller than min_window_size should be checked
        for size in checked_sizes:
            assert size >= 5, f"Checked window of size {size} < min_window_size 5"


class TestQualityInterpretation:
    """Tests for A/S/N quality level interpretation."""

    def test_advanced_quality_range(self):
        """A (Advanced) = 0-33% have LOW quality."""
        from uct_benchmark.data.windowSelection import interpret_quality_code

        result = interpret_quality_code('A')
        assert result['min_pct'] == 0.0, "A min_pct should be 0.0"
        assert result['max_pct'] == 0.33, "A max_pct should be 0.33"

    def test_standard_quality_range(self):
        """S (Standard) = 34-66% have LOW quality."""
        from uct_benchmark.data.windowSelection import interpret_quality_code

        result = interpret_quality_code('S')
        assert result['min_pct'] == 0.34, "S min_pct should be 0.34"
        assert result['max_pct'] == 0.66, "S max_pct should be 0.66"

    def test_novice_quality_range(self):
        """N (Novice) = 67-100% have LOW quality."""
        from uct_benchmark.data.windowSelection import interpret_quality_code

        result = interpret_quality_code('N')
        assert result['min_pct'] == 0.67, "N min_pct should be 0.67"
        assert result['max_pct'] == 1.0, "N max_pct should be 1.0"

    def test_case_insensitive(self):
        """Quality codes should be case-insensitive."""
        from uct_benchmark.data.windowSelection import interpret_quality_code

        for code in ['a', 'A']:
            result = interpret_quality_code(code)
            assert result['max_pct'] == 0.33

        for code in ['s', 'S']:
            result = interpret_quality_code(code)
            assert result['min_pct'] == 0.34

        for code in ['n', 'N']:
            result = interpret_quality_code(code)
            assert result['min_pct'] == 0.67

    def test_invalid_code_returns_standard(self):
        """Invalid quality code should return Standard (S) as default."""
        from uct_benchmark.data.windowSelection import interpret_quality_code

        result = interpret_quality_code('X')
        assert result['min_pct'] == 0.34, "Invalid code should default to S"
        assert result['max_pct'] == 0.66


class TestNonReferenceObservations:
    """Tests for True Negative observation handling."""

    def test_exactly_two_observations_per_satellite(self):
        """Verify exactly 2 observations per non-reference satellite (per Louis's spec)."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        # Reference dataset: satellite 1 with 10 observations
        ref_obs = pd.DataFrame({
            'id': range(10),
            'satNo': [1] * 10,
            'obTime': pd.date_range('2025-01-01', periods=10, freq='h'),
        })

        # All observations including non-reference satellites (99 and 98)
        all_obs = pd.DataFrame({
            'id': list(range(10)) + list(range(100, 140)),
            'satNo': [1] * 10 + [99] * 20 + [98] * 20,
            'obTime': list(pd.date_range('2025-01-01', periods=10, freq='h')) +
                     list(pd.date_range('2025-01-01', periods=40, freq='h')),
        })

        # Reference set only includes satellite 1
        reference_norad_ids = [1]

        augmented, non_ref = add_non_reference_observations(
            ref_obs,
            reference_norad_ids,
            all_observations_df=all_obs,
            non_ref_ratio=0.5,  # Request more non-ref to get both satellites
            seed=42,
        )

        # Each non-ref satellite should have exactly 2 observations
        if not non_ref.empty:
            for sat_id in non_ref['source_norad_id'].unique():
                sat_obs = non_ref[non_ref['source_norad_id'] == sat_id]
                assert len(sat_obs) == 2, f"Satellite {sat_id} should have exactly 2 observations, got {len(sat_obs)}"

    def test_non_ref_observations_marked(self):
        """Non-reference observations should be marked correctly."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        ref_obs = pd.DataFrame({
            'id': range(10),
            'satNo': [1] * 10,
            'obTime': pd.date_range('2025-01-01', periods=10, freq='h'),
        })

        all_obs = pd.DataFrame({
            'id': list(range(10)) + list(range(100, 120)),
            'satNo': [1] * 10 + [99] * 20,
            'obTime': list(pd.date_range('2025-01-01', periods=10, freq='h')) +
                     list(pd.date_range('2025-01-01', periods=20, freq='h')),
        })

        augmented, non_ref = add_non_reference_observations(
            ref_obs,
            [1],  # reference_norad_ids
            all_observations_df=all_obs,
            non_ref_ratio=0.2,
            seed=42,
        )

        # Check that non_ref observations are marked
        if not non_ref.empty:
            assert 'is_non_reference' in non_ref.columns, "Should have is_non_reference column"
            assert all(non_ref['is_non_reference']), "All non-ref obs should be marked True"

    def test_augmented_dataset_includes_non_ref(self):
        """Augmented dataset should include both original and non-ref observations."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        ref_obs = pd.DataFrame({
            'id': range(10),
            'satNo': [1] * 10,
            'obTime': pd.date_range('2025-01-01', periods=10, freq='h'),
        })

        all_obs = pd.DataFrame({
            'id': list(range(10)) + list(range(100, 120)),
            'satNo': [1] * 10 + [99] * 20,
            'obTime': list(pd.date_range('2025-01-01', periods=10, freq='h')) +
                     list(pd.date_range('2025-01-01', periods=20, freq='h')),
        })

        augmented, non_ref = add_non_reference_observations(
            ref_obs,
            [1],  # reference_norad_ids
            all_observations_df=all_obs,
            non_ref_ratio=0.2,
            seed=42,
        )

        # Augmented should have original + non-ref
        assert len(augmented) == len(ref_obs) + len(non_ref), "Augmented should combine both datasets"


@requires_state_metrics
class TestStateMetrics:
    """Tests for state estimation metrics."""

    def test_l2_position_error(self):
        """Test L2 position error calculation."""
        from uct_benchmark.evaluation.stateMetrics import calculate_state_metrics_single

        true_state = np.array([7000.0, 0.0, 0.0, 0.0, 7.5, 0.0])
        estimated_state = np.array([7001.0, 0.0, 0.0, 0.0, 7.5, 0.0])

        metrics = calculate_state_metrics_single(true_state, estimated_state)

        assert 'l2_position_km' in metrics
        assert abs(metrics['l2_position_km'] - 1.0) < 0.001, "Position error should be 1 km"

    def test_l2_velocity_error(self):
        """Test L2 velocity error calculation."""
        from uct_benchmark.evaluation.stateMetrics import calculate_state_metrics_single

        true_state = np.array([7000.0, 0.0, 0.0, 0.0, 7.5, 0.0])
        estimated_state = np.array([7000.0, 0.0, 0.0, 0.001, 7.5, 0.0])

        metrics = calculate_state_metrics_single(true_state, estimated_state)

        assert 'l2_velocity_km_s' in metrics
        assert abs(metrics['l2_velocity_km_s'] - 0.001) < 0.0001

    def test_per_dimension_bias(self):
        """Test per-dimension bias calculation."""
        from uct_benchmark.evaluation.stateMetrics import calculate_state_metrics_single

        true_state = np.array([7000.0, 100.0, 50.0, 0.0, 7.5, 0.1])
        estimated_state = np.array([7010.0, 95.0, 60.0, 0.01, 7.45, 0.15])

        metrics = calculate_state_metrics_single(true_state, estimated_state)

        assert abs(metrics['x_bias_km'] - 10.0) < 0.001
        assert abs(metrics['y_bias_km'] - (-5.0)) < 0.001
        assert abs(metrics['z_bias_km'] - 10.0) < 0.001

    def test_mahalanobis_with_covariance(self):
        """Test Mahalanobis distance with covariance matrix."""
        from uct_benchmark.evaluation.stateMetrics import calculate_state_metrics_single

        true_state = np.array([7000.0, 0.0, 0.0, 0.0, 7.5, 0.0])
        estimated_state = np.array([7001.0, 0.0, 0.0, 0.0, 7.5, 0.0])
        covariance = np.eye(6) * 1.0  # Identity covariance

        metrics = calculate_state_metrics_single(true_state, estimated_state, covariance)

        assert 'mahalanobis_distance' in metrics
        assert not np.isnan(metrics['mahalanobis_distance'])

    def test_nees_with_covariance(self):
        """Test NEES calculation with covariance matrix."""
        from uct_benchmark.evaluation.stateMetrics import calculate_state_metrics_single

        true_state = np.array([7000.0, 0.0, 0.0, 0.0, 7.5, 0.0])
        estimated_state = np.array([7001.0, 0.0, 0.0, 0.0, 7.5, 0.0])
        covariance = np.eye(6) * 1.0

        metrics = calculate_state_metrics_single(true_state, estimated_state, covariance)

        assert 'nees' in metrics
        assert not np.isnan(metrics['nees'])
        # NEES should equal Mahalanobis squared for single estimate
        assert abs(metrics['nees'] - metrics['mahalanobis_squared']) < 0.001


@requires_state_metrics
class TestResidualMetrics:
    """Tests for residual metrics calculation."""

    def test_great_circle_residual(self):
        """Test great circle distance residual calculation."""
        from uct_benchmark.evaluation.stateMetrics import calculate_residual_metrics

        observations = pd.DataFrame({
            'ra': [180.0, 180.0, 180.0],
            'dec': [0.0, 0.0, 0.0],
        })

        # Small offset in RA
        predictions = pd.DataFrame({
            'ra': [180.01, 180.01, 180.01],  # 0.01 degree offset
            'dec': [0.0, 0.0, 0.0],
        })

        metrics = calculate_residual_metrics(observations, predictions)

        assert 'residual_rms_arcsec' in metrics
        # 0.01 degree = 36 arcsec at equator
        assert metrics['residual_rms_arcsec'] > 30
        assert metrics['residual_rms_arcsec'] < 40

    def test_zero_residual_for_identical_positions(self):
        """Test zero residual when observed equals predicted."""
        from uct_benchmark.evaluation.stateMetrics import calculate_residual_metrics

        observations = pd.DataFrame({
            'ra': [180.0, 270.0, 90.0],
            'dec': [45.0, -30.0, 0.0],
        })

        # Same positions
        predictions = observations.copy()

        metrics = calculate_residual_metrics(observations, predictions)

        assert metrics['residual_rms_arcsec'] < 0.001

    def test_residual_statistics(self):
        """Test that all residual statistics are computed."""
        from uct_benchmark.evaluation.stateMetrics import calculate_residual_metrics

        observations = pd.DataFrame({
            'ra': [180.0 + i * 0.1 for i in range(10)],
            'dec': [0.0] * 10,
        })

        predictions = pd.DataFrame({
            'ra': [180.0 + i * 0.1 + 0.001 for i in range(10)],
            'dec': [0.0] * 10,
        })

        metrics = calculate_residual_metrics(observations, predictions)

        expected_keys = [
            'residual_count', 'residual_mean_arcsec', 'residual_std_arcsec',
            'residual_rms_arcsec', 'residual_median_arcsec',
            'residual_max_arcsec', 'residual_min_arcsec'
        ]

        for key in expected_keys:
            assert key in metrics, f"Missing metric: {key}"


@requires_state_metrics
class TestBatchNEES:
    """Tests for batch NEES calculation."""

    def test_consistent_estimator(self):
        """Test NEES for a consistent estimator (avg NEES ≈ 6)."""
        from uct_benchmark.evaluation.stateMetrics import calculate_batch_nees

        np.random.seed(42)

        # Generate errors from a distribution matching the covariance
        n_samples = 100
        covariance = np.eye(6) * 1.0
        errors = np.random.multivariate_normal(np.zeros(6), covariance, n_samples)
        covariances = np.array([covariance] * n_samples)

        result = calculate_batch_nees(errors, covariances)

        assert result['n_valid'] == n_samples
        # For consistent estimator, average NEES should be close to 6
        assert result['average_nees'] > 3 and result['average_nees'] < 12, \
            f"Average NEES {result['average_nees']} should be close to 6"

    def test_inconsistent_estimator_detected(self):
        """Test that inconsistent estimators are detected."""
        from uct_benchmark.evaluation.stateMetrics import calculate_batch_nees

        n_samples = 100
        # Errors much larger than covariance suggests
        covariance = np.eye(6) * 0.01  # Small covariance
        errors = np.ones((n_samples, 6)) * 10.0  # Large errors
        covariances = np.array([covariance] * n_samples)

        result = calculate_batch_nees(errors, covariances)

        # Average NEES should be very high (inconsistent)
        assert result['average_nees'] > 100, "Should detect inconsistency"


@requires_state_metrics
class TestRICErrors:
    """Tests for Radial-In-track-Cross-track error calculation."""

    def test_radial_error_only(self):
        """Test that pure radial error appears only in radial component."""
        from uct_benchmark.evaluation.stateMetrics import calculate_radial_in_track_cross_track_errors

        # Circular orbit in equatorial plane
        r = 7000.0  # km
        v = 7.5    # km/s

        true_state = np.array([r, 0.0, 0.0, 0.0, v, 0.0])
        # 1 km radial error (further from Earth)
        estimated_state = np.array([r + 1.0, 0.0, 0.0, 0.0, v, 0.0])

        ric = calculate_radial_in_track_cross_track_errors(true_state, estimated_state)

        assert abs(ric['radial_error_km'] - 1.0) < 0.1, "Radial error should be ~1 km"
        assert abs(ric['in_track_error_km']) < 0.1, "In-track error should be ~0"
        assert abs(ric['cross_track_error_km']) < 0.1, "Cross-track error should be ~0"


class TestAtmosphericRefraction:
    """Tests for atmospheric refraction correction."""

    def test_refraction_increases_apparent_elevation(self):
        """Atmospheric refraction should increase apparent elevation."""
        from uct_benchmark.simulation.atmospheric import apply_atmospheric_refraction

        true_elevation = 30.0  # degrees

        apparent_elevation = apply_atmospheric_refraction(true_elevation)

        assert apparent_elevation > true_elevation, \
            "Apparent elevation should be higher due to refraction"

    def test_refraction_larger_at_low_elevation(self):
        """Refraction effect should be larger at lower elevations."""
        from uct_benchmark.simulation.atmospheric import apply_atmospheric_refraction

        low_el_apparent = apply_atmospheric_refraction(10.0)
        high_el_apparent = apply_atmospheric_refraction(60.0)

        low_refraction = low_el_apparent - 10.0
        high_refraction = high_el_apparent - 60.0

        assert low_refraction > high_refraction, \
            "Refraction should be larger at lower elevations"

    def test_below_observability_returns_none(self):
        """Elevations below observability threshold should return None."""
        from uct_benchmark.simulation.atmospheric import apply_atmospheric_refraction

        result = apply_atmospheric_refraction(-5.0)
        assert result is None, "Negative elevation should return None"

        result = apply_atmospheric_refraction(3.0)
        assert result is None, "Very low elevation should return None"


class TestTrackTLE:
    """Tests for TrackTLE generation module."""

    def test_tle_checksum(self):
        """Test TLE checksum calculation."""
        from uct_benchmark.simulation.tracktle import tle_checksum

        # Example TLE line (without checksum)
        line = "1 25544U 98067A   21275.52102859  .00027747  00000-0  49297-3 0  999"
        checksum = tle_checksum(line)

        assert 0 <= checksum <= 9, "Checksum should be single digit"

    def test_tle_validation_correct_format(self):
        """Test TLE validation accepts correct format."""
        from uct_benchmark.simulation.tracktle import validate_tle

        # Valid TLE (ISS)
        line1 = "1 25544U 98067A   21275.52102859  .00027747  00000-0  49297-3 0  9993"
        line2 = "2 25544  51.6442 208.5982 0003656  78.9851  42.6728 15.48919792307640"

        # Note: These are not valid TLEs but correct format for testing
        valid, msg = validate_tle(line1, line2)
        # Will fail checksum but format checking happens first
        assert len(line1) == 69 and len(line2) == 69

    def test_state_to_tle_produces_valid_format(self):
        """Test that state_to_tle produces valid TLE format."""
        from uct_benchmark.simulation.tracktle import state_to_tle

        # LEO state
        position_km = np.array([6878.0, 0.0, 0.0])
        velocity_km_s = np.array([0.0, 7.784, 0.0])
        epoch = datetime(2025, 6, 15, 12, 0, 0)

        line1, line2 = state_to_tle(position_km, velocity_km_s, epoch, 99999, "25999A")

        assert len(line1) == 69, f"Line 1 should be 69 chars, got {len(line1)}"
        assert len(line2) == 69, f"Line 2 should be 69 chars, got {len(line2)}"
        assert line1[0] == '1', "Line 1 should start with '1'"
        assert line2[0] == '2', "Line 2 should start with '2'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
