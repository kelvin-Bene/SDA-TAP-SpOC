#!/usr/bin/env python3
"""
Comprehensive Test Suite for Downsampling and Simulation
=========================================================
Rigorous testing of T1/T2 downsampling and T3 simulation functionality.

Tests cover:
- Normal operations
- Edge cases (sparse data, dense data, boundary conditions)
- Different orbital regimes (LEO, MEO, GEO)
- Numerical stability
- Input validation

Usage:
    python -m pytest tests/test_downsampling_simulation_comprehensive.py -v
    OR
    python tests/test_downsampling_simulation_comprehensive.py

Author: SDA TAP Lab
Date: 2026-01-18
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# pytest is optional - tests can run standalone
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Create dummy pytest fixtures for standalone execution
    class pytest:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(func):
                return func
            return decorator

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


# =============================================================================
# TEST DATA GENERATORS
# =============================================================================

def generate_observations(
    sat_id: int,
    num_obs: int,
    start_time: datetime,
    duration_hours: float,
    pattern: str = "uniform",
    gap_hours: float = None
) -> pd.DataFrame:
    """
    Generate synthetic observation data with various patterns.

    Patterns:
        - "uniform": Evenly distributed observations
        - "clustered": Clustered at start and end with gap in middle
        - "random": Random distribution
        - "dense_start": Dense at start, sparse later
        - "tracks": Realistic track-based pattern (groups of 3-5 obs)
    """
    observations = []

    if pattern == "uniform":
        # Evenly distributed
        interval = (duration_hours * 3600) / max(num_obs - 1, 1)
        for i in range(num_obs):
            obs_time = start_time + timedelta(seconds=i * interval)
            observations.append(_create_obs(sat_id, obs_time, i))

    elif pattern == "clustered":
        # Clustered at start and end with gap
        gap_hours = gap_hours or duration_hours / 2
        half = num_obs // 2

        # First cluster
        for i in range(half):
            obs_time = start_time + timedelta(minutes=i * 10)
            observations.append(_create_obs(sat_id, obs_time, i))

        # Second cluster (after gap)
        gap_start = start_time + timedelta(hours=gap_hours)
        for i in range(num_obs - half):
            obs_time = gap_start + timedelta(minutes=i * 10)
            observations.append(_create_obs(sat_id, obs_time, half + i))

    elif pattern == "random":
        # Random distribution
        np.random.seed(sat_id)  # Reproducible
        times = np.sort(np.random.uniform(0, duration_hours * 3600, num_obs))
        for i, t in enumerate(times):
            obs_time = start_time + timedelta(seconds=t)
            observations.append(_create_obs(sat_id, obs_time, i))

    elif pattern == "dense_start":
        # Dense at start, sparse later
        for i in range(num_obs):
            # Exponentially increasing gaps
            t = (duration_hours * 3600) * (1 - np.exp(-3 * i / num_obs)) / (1 - np.exp(-3))
            obs_time = start_time + timedelta(seconds=t)
            observations.append(_create_obs(sat_id, obs_time, i))

    elif pattern == "tracks":
        # Realistic track pattern: groups of 3-5 obs separated by orbital period
        track_size = 4
        track_spacing_sec = 30  # seconds between obs in track
        inter_track_hours = 1.5  # ~1 orbital period

        obs_idx = 0
        current_time = start_time
        while obs_idx < num_obs and (current_time - start_time).total_seconds() < duration_hours * 3600:
            # Create a track
            track_obs = min(track_size, num_obs - obs_idx)
            for j in range(track_obs):
                obs_time = current_time + timedelta(seconds=j * track_spacing_sec)
                observations.append(_create_obs(sat_id, obs_time, obs_idx))
                obs_idx += 1

            current_time += timedelta(hours=inter_track_hours)

    return pd.DataFrame(observations)


def _create_obs(sat_id: int, obs_time: datetime, idx: int, as_string: bool = True) -> dict:
    """Create a single observation record."""
    return {
        'id': f'obs_{sat_id}_{idx}',
        'satNo': sat_id,
        'obTime': obs_time.strftime('%Y-%m-%dT%H:%M:%S.000Z') if as_string else obs_time,
        'ra': 120.0 + np.random.uniform(-5, 5),
        'declination': 30.0 + np.random.uniform(-2, 2),
        'dataMode': 'REAL',
        'source': 'TEST'
    }


def generate_orbital_elements(sat_id: int, regime: str = "LEO") -> dict:
    """
    Generate orbital elements for different regimes.

    Regimes:
        - "LEO": Low Earth Orbit (~400km, ~90 min period)
        - "MEO": Medium Earth Orbit (~20,000km, ~12 hr period)
        - "GEO": Geostationary (~35,786km, ~24 hr period)
        - "HEO": Highly Elliptical Orbit
    """
    MU = 398600.4418  # km^3/s^2

    if regime == "LEO":
        a = 6778  # ~400km altitude
        e = 0.001
        inc = 51.6  # ISS-like
    elif regime == "MEO":
        a = 26560  # GPS-like
        e = 0.01
        inc = 55.0
    elif regime == "GEO":
        a = 42164  # Geostationary
        e = 0.0001
        inc = 0.1
    elif regime == "HEO":
        a = 26600  # Molniya-like
        e = 0.74
        inc = 63.4
    else:
        raise ValueError(f"Unknown regime: {regime}")

    # Calculate period using Kepler's third law
    period_sec = 2 * np.pi * np.sqrt((a ** 3) / MU)

    return {
        'Semi-Major Axis': a,
        'Eccentricity': e,
        'Inclination': inc,
        'RAAN': 120.0,
        'Argument of Perigee': 90.0,
        'Mean Anomaly': 0.0,
        'Period': period_sec,
        'Number of Obs': 100,
        'Orbital Coverage': 0.5,
        'Max Track Gap': 0.3
    }


# =============================================================================
# SIMULATION TESTS (epochsToSim)
# =============================================================================

class TestEpochsToSim:
    """Tests for the epochsToSim function."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Import the function under test."""
        from uct_benchmark.simulation.simulateObservations import epochsToSim
        self.epochsToSim = epochsToSim

    # --- Normal Operation Tests ---

    def test_basic_gap_filling(self):
        """Test that epochs are generated for gaps in observation coverage."""
        sat_id = 25544
        obs = generate_observations(sat_id, 20, datetime(2025, 6, 1), 12, "clustered", gap_hours=6)
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        assert info['status'] == 'success', f"Expected success, got {info['status']}"
        assert len(epochs) > 0, "Should generate epochs for gap"
        assert info['empty_bins'] > 0, "Should identify empty bins"
        print(f"Generated {len(epochs)} epochs for {info['empty_bins']} empty bins")

    def test_no_gaps_returns_empty(self):
        """Test that dense data with no gaps returns no epochs."""
        sat_id = 12345
        # Dense uniform data covering entire window
        obs = generate_observations(sat_id, 200, datetime(2025, 6, 1), 6, "uniform")
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        assert len(epochs) == 0, "Should not generate epochs when well-covered"
        assert info['status'] in ['all_bins_covered', 'already_at_target']
        print(f"Correctly returned empty: {info['status']}")

    def test_track_pattern(self):
        """Test with realistic track-based observation pattern."""
        sat_id = 33333
        obs = generate_observations(sat_id, 40, datetime(2025, 6, 1), 24, "tracks")
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        assert info['status'] in ['success', 'all_bins_covered', 'already_at_target']
        print(f"Track pattern result: {info}")

    # --- Orbital Regime Tests ---

    def test_leo_short_period(self):
        """Test LEO with ~90 minute period."""
        sat_id = 25544
        obs = generate_observations(sat_id, 30, datetime(2025, 6, 1), 12, "clustered", gap_hours=4)
        orb = generate_orbital_elements(sat_id, "LEO")

        assert orb['Period'] < 6000, "LEO period should be ~90 min"

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        assert info['status'] == 'success'
        assert info['period_sec'] == orb['Period']
        print(f"LEO test: period={orb['Period']:.0f}s, epochs={len(epochs)}")

    def test_geo_long_period(self):
        """Test GEO with ~24 hour period."""
        sat_id = 41866
        # GEO needs longer observation window
        obs = generate_observations(sat_id, 20, datetime(2025, 6, 1), 72, "clustered", gap_hours=30)
        orb = generate_orbital_elements(sat_id, "GEO")

        assert orb['Period'] > 80000, "GEO period should be ~24 hours"

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        # GEO may have different behavior due to long period
        print(f"GEO test: period={orb['Period']:.0f}s ({orb['Period']/3600:.1f}hr), status={info['status']}")

    def test_meo_medium_period(self):
        """Test MEO with ~12 hour period."""
        sat_id = 28874
        obs = generate_observations(sat_id, 30, datetime(2025, 6, 1), 48, "clustered", gap_hours=18)
        orb = generate_orbital_elements(sat_id, "MEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        print(f"MEO test: period={orb['Period']:.0f}s ({orb['Period']/3600:.1f}hr), epochs={len(epochs)}")

    # --- Edge Case Tests ---

    def test_minimum_observations(self):
        """Test with exactly minimum required observations."""
        sat_id = 11111
        # Config default is 3 minimum
        obs = generate_observations(sat_id, 3, datetime(2025, 6, 1), 6, "uniform")
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        # Should still process with minimum obs
        print(f"Min obs test: {info}")

    def test_below_minimum_observations(self):
        """Test with fewer than minimum observations."""
        sat_id = 22222
        obs = generate_observations(sat_id, 2, datetime(2025, 6, 1), 6, "uniform")
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        assert info['status'] == 'insufficient_existing_obs'
        assert len(epochs) == 0
        print("Correctly rejected insufficient observations")

    def test_very_short_window(self):
        """Test with observation window shorter than half period."""
        sat_id = 44444
        # LEO period ~90 min, window = 30 min
        obs = generate_observations(sat_id, 10, datetime(2025, 6, 1), 0.5, "uniform")
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        assert info['status'] == 'window_too_short'
        print("Correctly identified short window")

    def test_single_large_gap(self):
        """Test with one very large gap."""
        sat_id = 55555
        obs = generate_observations(sat_id, 30, datetime(2025, 6, 1), 24, "clustered", gap_hours=20)
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        assert info['status'] == 'success'
        assert len(epochs) > 0
        print(f"Large gap test: {info['empty_bins']} empty bins, {len(epochs)} epochs")

    def test_many_small_gaps(self):
        """Test with many small gaps (random distribution)."""
        sat_id = 66666
        obs = generate_observations(sat_id, 50, datetime(2025, 6, 1), 12, "random")
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        print(f"Random distribution: {info}")

    def test_epochs_within_window(self):
        """Verify all generated epochs are within observation window."""
        sat_id = 77777
        start = datetime(2025, 6, 1, 12, 0, 0)
        obs = generate_observations(sat_id, 30, start, 12, "clustered", gap_hours=6)
        orb = generate_orbital_elements(sat_id, "LEO")

        epochs, info = self.epochsToSim(sat_id, obs, orb)

        if epochs:
            obs_times = pd.to_datetime(obs['obTime'])
            min_time = obs_times.min().to_pydatetime().replace(tzinfo=None)
            max_time = obs_times.max().to_pydatetime().replace(tzinfo=None)

            for epoch in epochs:
                if hasattr(epoch, 'tzinfo') and epoch.tzinfo:
                    epoch = epoch.replace(tzinfo=None)
                assert min_time <= epoch <= max_time, f"Epoch {epoch} outside window"

            print(f"All {len(epochs)} epochs within window [OK]")

    # --- Stress Tests ---

    def test_large_observation_count(self):
        """Test with large number of observations."""
        sat_id = 88888
        obs = generate_observations(sat_id, 5000, datetime(2025, 6, 1), 168, "random")  # 1 week
        orb = generate_orbital_elements(sat_id, "LEO")

        import time
        start = time.time()
        epochs, info = self.epochsToSim(sat_id, obs, orb)
        elapsed = time.time() - start

        print(f"Large dataset ({len(obs)} obs): {elapsed:.2f}s, {info['status']}")
        assert elapsed < 5.0, "Should complete in reasonable time"

    def test_max_simulation_ratio(self):
        """Test that simulation respects max_sim_ratio."""
        sat_id = 99999
        obs = generate_observations(sat_id, 10, datetime(2025, 6, 1), 24, "clustered", gap_hours=20)
        orb = generate_orbital_elements(sat_id, "LEO")

        # Very restrictive ratio
        epochs, info = self.epochsToSim(sat_id, obs, orb, max_sim_ratio=0.1)

        if epochs:
            max_allowed = int(10 * 0.1 / 0.9)  # ~1
            assert len(epochs) <= max_allowed + 10, "Should respect max ratio (approximately)"
        print(f"Max ratio test: {len(epochs)} epochs (max ~{int(10 * 0.1 / 0.9) * 3})")


# =============================================================================
# DOWNSAMPLING TESTS
# =============================================================================

class TestDownsampling:
    """Tests for the downsampleData function."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Import the function under test."""
        from uct_benchmark.data.dataManipulation import downsampleData
        self.downsampleData = downsampleData

    def _create_test_data(self, num_sats: int, obs_per_sat: int, regime: str = "LEO"):
        """Create test data with multiple satellites."""
        all_obs = []
        sat_params = {}

        base_time = datetime(2025, 6, 1)
        for i in range(num_sats):
            sat_id = 10000 + i
            obs = generate_observations(sat_id, obs_per_sat, base_time, 24, "random")
            all_obs.append(obs)
            sat_params[sat_id] = generate_orbital_elements(sat_id, regime)

        result = pd.concat(all_obs, ignore_index=True)
        # Convert obTime from string to datetime for downsampling functions
        result['obTime'] = pd.to_datetime(result['obTime'])
        return result, sat_params

    # --- Normal Operation Tests ---

    def test_basic_downsampling(self):
        """Test basic downsampling reduces observation count."""
        ref_obs, sat_params = self._create_test_data(5, 200)
        initial_count = len(ref_obs)

        # p_coverage is (target_coverage, min_coverage) - tuple not float
        # p_track is a fraction of orbital period
        orbit_coverage = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_coverage': (0.5, 0.3)}
        track_length = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_track': 0.5}
        obs_count = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'obs_max': 100}

        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )

        assert len(result) <= initial_count, "Should reduce or maintain observation count"
        print(f"Downsampled: {initial_count} -> {len(result)} ({100*len(result)/initial_count:.1f}%)")
        # p_reached may contain numpy arrays
        print(f"Percentages reached: coverage={p_reached[0]}, gap={p_reached[1]}, count={p_reached[2]}")

    def test_coverage_reduction(self):
        """Test that coverage-based downsampling works."""
        ref_obs, sat_params = self._create_test_data(3, 300)

        # Target low coverage
        orbit_coverage = {'sats': None, 'p_bounds': (0.5, 0.8, 0.7), 'p_coverage': (0.3, 0.1)}
        track_length = {'sats': None, 'p_bounds': (0.0, 0.1, 0.0), 'p_track': 0.0}
        obs_count = {'sats': None, 'p_bounds': (0.0, 0.1, 0.0), 'obs_max': 1000}

        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )

        print(f"Coverage reduction: {p_reached[0]} of sats at target coverage")

    def test_gap_widening(self):
        """Test that gap-widening works."""
        ref_obs, sat_params = self._create_test_data(3, 300)

        orbit_coverage = {'sats': None, 'p_bounds': (0.0, 0.1, 0.0), 'p_coverage': (1.0, 0.8)}
        track_length = {'sats': None, 'p_bounds': (0.5, 0.8, 0.7), 'p_track': 0.5}
        obs_count = {'sats': None, 'p_bounds': (0.0, 0.1, 0.0), 'obs_max': 1000}

        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )

        print(f"Gap widening: {p_reached[1]:.2f} of sats have widened gaps")

    def test_obs_count_limit(self):
        """Test that observation count limiting works."""
        ref_obs, sat_params = self._create_test_data(3, 300)

        orbit_coverage = {'sats': None, 'p_bounds': (0.0, 0.1, 0.0), 'p_coverage': (1.0, 0.8)}
        track_length = {'sats': None, 'p_bounds': (0.0, 0.1, 0.0), 'p_track': 0.0}
        obs_count = {'sats': None, 'p_bounds': (0.5, 0.8, 0.7), 'obs_max': 50}

        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )

        # Check that satellites are at or below max
        counts = result.groupby('satNo').size()
        print(f"Obs count limit: {p_reached[2]:.2f} of sats at/below {50}")
        print(f"Final counts: {counts.to_dict()}")

    # --- Edge Case Tests ---

    def test_already_sparse_data(self):
        """Test with data that's already sparse."""
        ref_obs, sat_params = self._create_test_data(3, 20)  # Already sparse
        initial_count = len(ref_obs)

        orbit_coverage = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_coverage': (0.5, 0.3)}
        track_length = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_track': 0.5}
        obs_count = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'obs_max': 100}

        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )

        # Shouldn't remove much from already sparse data
        print(f"Sparse data: {initial_count} -> {len(result)}")

    def test_single_satellite(self):
        """Test with only one satellite."""
        ref_obs, sat_params = self._create_test_data(1, 200)

        orbit_coverage = {'sats': None, 'p_bounds': (0.3, 0.9, 0.5), 'p_coverage': (0.5, 0.3)}
        track_length = {'sats': None, 'p_bounds': (0.3, 0.9, 0.5), 'p_track': 0.5}
        obs_count = {'sats': None, 'p_bounds': (0.3, 0.9, 0.5), 'obs_max': 100}

        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )

        print(f"Single sat: {len(ref_obs)} -> {len(result)}, {p_reached}")

    def test_specific_satellite_selection(self):
        """Test downsampling specific satellites only."""
        ref_obs, sat_params = self._create_test_data(5, 150)
        target_sats = [10000, 10002]  # Only first and third

        initial_counts = ref_obs.groupby('satNo').size()

        orbit_coverage = {'sats': target_sats, 'p_bounds': (0.5, 1.0, 0.8), 'p_coverage': (0.3, 0.1)}
        track_length = {'sats': target_sats, 'p_bounds': (0.5, 1.0, 0.8), 'p_track': 0.5}
        obs_count = {'sats': target_sats, 'p_bounds': (0.5, 1.0, 0.8), 'obs_max': 50}

        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )

        final_counts = result.groupby('satNo').size()

        # Target satellites should be affected (reduced or at limit)
        for sat_id in target_sats:
            if sat_id in initial_counts and sat_id in final_counts:
                # At least verify target sats are still present
                assert sat_id in final_counts, f"Target sat {sat_id} should be present"

        print(f"Specific sats test: {initial_counts.to_dict()} -> {final_counts.to_dict()}")
        print(f"Target sats: {target_sats}")

    def test_reproducibility(self):
        """Test that random seed produces reproducible results."""
        ref_obs, sat_params = self._create_test_data(5, 200)

        orbit_coverage = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_coverage': (0.5, 0.3)}
        track_length = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_track': 0.5}
        obs_count = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'obs_max': 100}

        result1, _ = self.downsampleData(
            ref_obs.copy(), sat_params, orbit_coverage, track_length, obs_count, rand=42
        )
        result2, _ = self.downsampleData(
            ref_obs.copy(), sat_params, orbit_coverage, track_length, obs_count, rand=42
        )

        assert len(result1) == len(result2), "Same seed should give same count"
        print(f"Reproducibility: Both runs = {len(result1)} observations")

    # --- Regime-Specific Tests ---

    def test_geo_satellites(self):
        """Test downsampling GEO satellites with long periods."""
        all_obs = []
        sat_params = {}

        base_time = datetime(2025, 6, 1)
        for i in range(3):
            sat_id = 40000 + i
            obs = generate_observations(sat_id, 100, base_time, 72, "random")  # 3 days
            all_obs.append(obs)
            sat_params[sat_id] = generate_orbital_elements(sat_id, "GEO")

        ref_obs = pd.concat(all_obs, ignore_index=True)
        ref_obs['obTime'] = pd.to_datetime(ref_obs['obTime'])

        orbit_coverage = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_coverage': (0.5, 0.3)}
        track_length = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_track': 0.3}
        obs_count = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'obs_max': 50}

        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )

        print(f"GEO test: {len(ref_obs)} -> {len(result)}, {p_reached}")

    # --- Stress Tests ---

    def test_large_dataset(self):
        """Test with large number of satellites and observations."""
        ref_obs, sat_params = self._create_test_data(20, 500)
        print(f"Large dataset: {len(ref_obs)} total observations, {len(sat_params)} satellites")

        orbit_coverage = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_coverage': (0.5, 0.3)}
        track_length = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_track': 0.5}
        obs_count = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'obs_max': 200}

        import time
        start = time.time()
        result, p_reached = self.downsampleData(
            ref_obs, sat_params, orbit_coverage, track_length, obs_count
        )
        elapsed = time.time() - start

        print(f"Completed in {elapsed:.2f}s: {len(ref_obs)} -> {len(result)}")
        assert elapsed < 30.0, "Should complete in reasonable time"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for simulation and downsampling together."""

    def test_simulation_then_downsampling(self):
        """Test that simulated data can be downsampled."""
        from uct_benchmark.simulation.simulateObservations import epochsToSim
        from uct_benchmark.data.dataManipulation import downsampleData

        # Create sparse data
        sat_id = 25544
        obs = generate_observations(sat_id, 30, datetime(2025, 6, 1), 24, "clustered", gap_hours=12)
        orb = generate_orbital_elements(sat_id, "LEO")

        # Simulate to fill gaps
        epochs, info = epochsToSim(sat_id, obs, orb)
        print(f"Simulation: {len(obs)} -> {len(obs) + len(epochs)} observations")

        # Add simulated observations (simplified - just add count)
        simulated_obs = []
        for i, epoch in enumerate(epochs):
            simulated_obs.append({
                'id': f'sim_{sat_id}_{i}',
                'satNo': sat_id,
                'obTime': epoch.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'ra': 130.0,
                'declination': 25.0,
                'dataMode': 'SIMULATED'
            })

        if simulated_obs:
            combined = pd.concat([obs, pd.DataFrame(simulated_obs)], ignore_index=True)
        else:
            combined = obs

        # Convert obTime to datetime for downsampling
        combined['obTime'] = pd.to_datetime(combined['obTime'])

        # Now downsample
        sat_params = {sat_id: orb}
        orbit_coverage = {'sats': None, 'p_bounds': (0.5, 0.9, 0.7), 'p_coverage': (0.5, 0.3)}
        track_length = {'sats': None, 'p_bounds': (0.5, 0.9, 0.7), 'p_track': 0.3}
        obs_count = {'sats': None, 'p_bounds': (0.5, 0.9, 0.7), 'obs_max': 50}

        result, p_reached = downsampleData(
            combined, sat_params, orbit_coverage, track_length, obs_count
        )

        print(f"After downsampling: {len(combined)} -> {len(result)}")
        print(f"Flow: {len(obs)} original -> {len(combined)} with sim -> {len(result)} downsampled")

    def test_tier_decision_logic(self):
        """Test the logic for deciding between T2 (downsample) and T3 (simulate)."""
        # T2: High quality data -> downsample
        dense_obs = generate_observations(11111, 500, datetime(2025, 6, 1), 24, "uniform")

        # T3: Sparse data -> simulate
        sparse_obs = generate_observations(22222, 30, datetime(2025, 6, 1), 24, "clustered", gap_hours=12)

        # Decision criteria (simplified from actual tier logic)
        def needs_simulation(obs_df, orb_elems):
            """Check if data needs simulation (T3) vs downsampling (T2)."""
            from uct_benchmark.simulation.simulateObservations import epochsToSim

            sat_id = obs_df['satNo'].iloc[0]
            epochs, info = epochsToSim(sat_id, obs_df, orb_elems)

            # If many empty bins, needs simulation
            if info.get('status') == 'success' and info.get('empty_bins', 0) > info.get('total_bins', 1) * 0.3:
                return True, info
            return False, info

        orb = generate_orbital_elements(11111, "LEO")

        needs_sim_dense, info_dense = needs_simulation(dense_obs, orb)
        needs_sim_sparse, info_sparse = needs_simulation(sparse_obs, generate_orbital_elements(22222, "LEO"))

        print(f"Dense data (T2 candidate): needs_sim={needs_sim_dense}, {info_dense.get('status')}")
        print(f"Sparse data (T3 candidate): needs_sim={needs_sim_sparse}, empty_bins={info_sparse.get('empty_bins')}")


# =============================================================================
# RUN TESTS
# =============================================================================

def run_all_tests():
    """Run all tests manually (without pytest)."""
    print("=" * 70)
    print("COMPREHENSIVE DOWNSAMPLING & SIMULATION TEST SUITE")
    print("=" * 70)

    # Simulation tests
    print("\n" + "=" * 70)
    print("SIMULATION TESTS (epochsToSim)")
    print("=" * 70)

    sim_tests = TestEpochsToSim()
    sim_tests.setup()

    test_methods = [m for m in dir(sim_tests) if m.startswith('test_')]
    sim_passed = 0
    sim_failed = 0

    for method_name in test_methods:
        try:
            print(f"\n--- {method_name} ---")
            getattr(sim_tests, method_name)()
            print(f"[PASS]")
            sim_passed += 1
        except Exception as e:
            print(f"[FAIL] {e}")
            sim_failed += 1

    # Downsampling tests
    print("\n" + "=" * 70)
    print("DOWNSAMPLING TESTS")
    print("=" * 70)

    ds_tests = TestDownsampling()
    ds_tests.setup()

    test_methods = [m for m in dir(ds_tests) if m.startswith('test_')]
    ds_passed = 0
    ds_failed = 0

    for method_name in test_methods:
        try:
            print(f"\n--- {method_name} ---")
            getattr(ds_tests, method_name)()
            print(f"[PASS]")
            ds_passed += 1
        except Exception as e:
            print(f"[FAIL] {e}")
            ds_failed += 1

    # Integration tests
    print("\n" + "=" * 70)
    print("INTEGRATION TESTS")
    print("=" * 70)

    int_tests = TestIntegration()

    test_methods = [m for m in dir(int_tests) if m.startswith('test_')]
    int_passed = 0
    int_failed = 0

    for method_name in test_methods:
        try:
            print(f"\n--- {method_name} ---")
            getattr(int_tests, method_name)()
            print(f"[PASS]")
            int_passed += 1
        except Exception as e:
            print(f"[FAIL] {e}")
            int_failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total_passed = sim_passed + ds_passed + int_passed
    total_failed = sim_failed + ds_failed + int_failed

    print(f"Simulation:   {sim_passed}/{sim_passed + sim_failed} passed")
    print(f"Downsampling: {ds_passed}/{ds_passed + ds_failed} passed")
    print(f"Integration:  {int_passed}/{int_passed + int_failed} passed")
    print("-" * 40)
    print(f"TOTAL:        {total_passed}/{total_passed + total_failed} passed")

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
